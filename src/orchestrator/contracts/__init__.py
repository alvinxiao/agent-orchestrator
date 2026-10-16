"""Strict, non-executing validation of versioned task contracts."""

import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

import yaml
from yaml.events import AliasEvent
from yaml.nodes import MappingNode

MAX_BYTES = 1_048_576
_ID = re.compile(r"[A-Z][A-Z0-9]*-[0-9]{3,}")
_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?")


@dataclass(frozen=True)
class ContractError(ValueError):
    """Stable error fields suitable for machine-readable CLI diagnostics."""

    code: str
    path: str
    message: str


@dataclass(frozen=True)
class Execution:
    """Declared execution limits, not authorization to run."""

    executor: str
    max_attempts: int
    timeout_minutes: int


@dataclass(frozen=True)
class Permissions:
    """Explicit permissions retained for later policy checks."""

    network: str
    production_access: bool
    secrets_access: bool
    may_merge: bool
    may_deploy: bool


@dataclass(frozen=True)
class TaskContract:
    """A validated v1 contract; command strings are data, never executed here."""

    schema_version: int
    id: str
    title: str
    repository: str
    depends_on: tuple[str, ...]
    allowed_paths: tuple[str, ...]
    commands: tuple[str, ...]
    requirements: tuple[str, ...]
    required_tests: tuple[str, ...]
    execution: Execution
    permissions: Permissions
    risk_level: str


class _Loader(yaml.SafeLoader):
    def construct_mapping(self, node: MappingNode, deep: bool = False) -> dict[Any, Any]:
        keys: set[str] = set()
        for key, _ in node.value:
            if key.tag != "tag:yaml.org,2002:str" or key.value in keys:
                raise ContractError("yaml_keys", "$", "Mapping keys must be unique strings")
            keys.add(key.value)
        return super().construct_mapping(node, deep=deep)


def _fail(path: str, message: str, code: str = "invalid_field") -> NoReturn:
    raise ContractError(code, path, message)


def _mapping(value: Any, fields: set[str], path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(path, "Expected a mapping")
    actual = set(value)
    if actual != fields:
        missing = ", ".join(sorted(fields - actual))
        unknown = ", ".join(sorted(actual - fields))
        _fail(path, f"Field mismatch; missing: [{missing}]; unknown: [{unknown}]", "fields")
    return dict(value)


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        _fail(path, "Expected nonempty text without NUL")
    return str(value)


def _texts(value: Any, path: str, *, nonempty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list) or (nonempty and not value):
        _fail(path, "Expected a list" + (" with at least one item" if nonempty else ""))
    items = tuple(_text(item, f"{path}[{i}]") for i, item in enumerate(value))
    if len(set(items)) != len(items):
        _fail(path, "Duplicate entries are not allowed", "duplicate")
    return items


def _identifier(value: Any, path: str) -> str:
    text = _text(value, path)
    if not _ID.fullmatch(text):
        _fail(path, "Expected a task ID such as ORCH-002")
    return text


def _task(value: Any, path: str) -> TaskContract:
    data = _mapping(
        value,
        {
            "schema_version",
            "id",
            "title",
            "repository",
            "depends_on",
            "scope",
            "requirements",
            "acceptance",
            "execution",
            "permissions",
            "risk_level",
        },
        path,
    )
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        _fail(path + ".schema_version", "Only integer schema version 1 is supported", "version")
    task_id = _identifier(data["id"], path + ".id")
    title = _text(data["title"], path + ".title")
    repository = _text(data["repository"], path + ".repository")
    if not _REPOSITORY.fullmatch(repository) or any(
        part in {".", ".."} for part in repository.split("/")
    ):
        _fail(path + ".repository", "Expected repository name or owner/name")
    dependencies = _texts(data["depends_on"], path + ".depends_on", nonempty=False)
    for dep in dependencies:
        _identifier(dep, path + ".depends_on")
    scope = _mapping(data["scope"], {"allowed_paths"}, path + ".scope")
    paths = _texts(scope["allowed_paths"], path + ".scope.allowed_paths")
    for item in paths:
        if (
            item.startswith("/")
            or "\\" in item
            or ":" in item
            or any(part in {"", ".", ".."} for part in item.split("/"))
        ):
            _fail(path + ".scope.allowed_paths", "Paths must be relative without traversal")
    requirements = _texts(data["requirements"], path + ".requirements")
    acceptance = _mapping(data["acceptance"], {"commands", "required_tests"}, path + ".acceptance")
    commands = _texts(acceptance["commands"], path + ".acceptance.commands")
    required_tests = _texts(acceptance["required_tests"], path + ".acceptance.required_tests")
    for command in commands:
        # Conservative command syntax, not a command-execution sandbox or allowlist.
        if any(char in command for char in "\n\r;&|<>`$\\"):
            _fail(path + ".acceptance.commands", "Shell operators and expansion are unsupported")
        try:
            argv = shlex.split(command)
        except ValueError:
            _fail(path + ".acceptance.commands", "Malformed command quoting")
        if not argv or not argv[0] or "=" in argv[0]:
            _fail(path + ".acceptance.commands", "Expected an executable and optional arguments")
    execution = _mapping(
        data["execution"],
        {
            "executor",
            "max_attempts",
            "timeout_minutes",
        },
        path + ".execution",
    )
    if execution["executor"] not in ("mock", "codex"):
        _fail(path + ".execution.executor", "Expected mock or codex; validation enables neither")
    for field in ("max_attempts", "timeout_minutes"):
        number = execution[field]
        if type(number) is not int or number <= 0:
            _fail(path + ".execution." + field, "Expected a positive integer")
    if execution["max_attempts"] > 3:
        _fail(path + ".execution.max_attempts", "At most three attempts are supported")
    permissions = _mapping(
        data["permissions"],
        {
            "network",
            "production_access",
            "secrets_access",
            "may_merge",
            "may_deploy",
        },
        path + ".permissions",
    )
    if permissions["network"] not in ("disabled", "restricted"):
        _fail(path + ".permissions.network", "Expected disabled or restricted network")
    for field in ("production_access", "secrets_access", "may_merge", "may_deploy"):
        if permissions[field] is not False:
            _fail(path + ".permissions." + field, "This permission must be false", "permission")
    if data["risk_level"] not in ("low", "medium", "high"):
        _fail(path + ".risk_level", "Expected low, medium, or high")
    return TaskContract(
        schema_version=1,
        id=task_id,
        title=title,
        repository=repository,
        depends_on=dependencies,
        allowed_paths=paths,
        commands=commands,
        requirements=requirements,
        required_tests=required_tests,
        execution=Execution(**execution),
        permissions=Permissions(**permissions),
        risk_level=data["risk_level"],
    )


def load_contracts(path: Path) -> tuple[TaskContract, ...]:
    """Load a complete task set with no external calls or command execution."""
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    except OSError:
        raise ContractError("read_error", "$", "Cannot read task file") from None
    if len(raw) > MAX_BYTES:
        raise ContractError("too_large", "$", "Task file exceeds 1 MiB")
    try:
        text = raw.decode("utf-8")
        if any(isinstance(event, AliasEvent) for event in yaml.parse(text, Loader=_Loader)):
            raise ContractError("yaml_alias", "$", "YAML aliases are unsupported")
        value = yaml.load(text, Loader=_Loader)
    except (yaml.YAMLError, UnicodeError, RecursionError):
        raise ContractError("yaml_error", "$", "Malformed or unsupported YAML") from None
    values = value if isinstance(value, list) else [value]
    if not values:
        raise ContractError("empty", "$", "Expected at least one task")
    tasks = tuple(_task(item, f"$[{i}]") for i, item in enumerate(values))
    seen: set[str] = set()
    for task in tasks:
        if task.id in seen:
            raise ContractError("duplicate_id", "$", f"Duplicate task ID: {task.id}")
        seen.add(task.id)
    for task in tasks:
        if any(dep not in seen for dep in task.depends_on):
            raise ContractError("unknown_dependency", "$", f"Unknown dependency for {task.id}")
    # Iterative elimination also rejects self-dependencies without recursion depth limits.
    pending = {task.id: set(task.depends_on) for task in tasks}
    while pending:
        ready = {name for name, deps in pending.items() if not deps}
        if not ready:
            raise ContractError("cycle", "$", "Task dependencies contain a cycle")
        pending = {name: deps - ready for name, deps in pending.items() if name not in ready}
    return tasks
