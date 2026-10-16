"""Observable validation behavior, entirely offline."""

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from orchestrator.contracts import ContractError, load_contracts

EXAMPLE = Path(__file__).resolve().parents[2] / "examples/tasks/example.yaml"


def write_task(tmp_path: Path, value: Any) -> Path:
    path = tmp_path / "task.yaml"
    path.write_text(yaml.safe_dump(value))
    return path


@pytest.fixture
def task() -> dict[str, Any]:
    value: dict[str, Any] = yaml.safe_load(EXAMPLE.read_text())
    return value


def test_valid_example() -> None:
    tasks = load_contracts(EXAMPLE)
    assert len(tasks) == 1
    assert tasks[0].id == "ORCH-002"
    assert tasks[0].commands == ("pytest tests/unit/test_contracts.py",)
    assert tasks[0].execution.max_attempts == 3
    assert tasks[0].execution.timeout_minutes == 30
    assert tasks[0].permissions.network == "disabled"
    assert tasks[0].permissions.may_merge is False
    assert tasks[0].required_tests == ("test_valid_example",)
    assert tasks[0].requirements == ("Reject malformed contracts without executing their commands",)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "bad"),
        ("repository", "../repo"),
        ("schema_version", True),
        ("schema_version", 2),
        ("title", ""),
        ("risk_level", "unknown"),
        ("requirements", []),
        ("depends_on", ["BAD"]),
    ],
)
def test_invalid_top_level(
    tmp_path: Path,
    task: dict[str, Any],
    field: str,
    value: Any,
) -> None:
    task[field] = value
    with pytest.raises(ContractError):
        load_contracts(write_task(tmp_path, task))


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("scope", "allowed_paths", ["/tmp/**"]),
        ("scope", "allowed_paths", ["../src"]),
        ("scope", "allowed_paths", ["src/../private"]),
        ("scope", "allowed_paths", ["C:\\temp"]),
        ("scope", "allowed_paths", ["src\\..\\private"]),
        ("acceptance", "commands", []),
        ("acceptance", "commands", ['"" arg']),
        ("acceptance", "commands", ["pytest && echo done"]),
        ("acceptance", "commands", ["echo $(whoami)"]),
        ("acceptance", "commands", ["echo `whoami`"]),
        ("acceptance", "commands", ["pytest\nwhoami"]),
        ("acceptance", "commands", ['pytest "']),
        ("acceptance", "commands", [{"run": "pytest"}]),
        ("acceptance", "required_tests", []),
        ("execution", "timeout_minutes", 0),
        ("execution", "timeout_minutes", -1),
        ("execution", "timeout_minutes", 1.5),
        ("execution", "timeout_minutes", True),
        ("execution", "max_attempts", 4),
        ("execution", "max_attempts", 0),
        ("execution", "executor", "shell"),
        ("permissions", "network", "unrestricted"),
        ("permissions", "production_access", True),
        ("permissions", "secrets_access", True),
        ("permissions", "may_merge", True),
        ("permissions", "may_deploy", "false"),
    ],
)
def test_invalid_nested_fields(
    tmp_path: Path,
    task: dict[str, Any],
    section: str,
    field: str,
    value: Any,
) -> None:
    task[section][field] = value
    with pytest.raises(ContractError):
        load_contracts(write_task(tmp_path, task))


@pytest.mark.parametrize("section", [None, "scope", "acceptance", "execution", "permissions"])
@pytest.mark.parametrize("change", ["missing", "unknown"])
def test_field_sets(
    tmp_path: Path,
    task: dict[str, Any],
    section: str | None,
    change: str,
) -> None:
    target = task if section is None else task[section]
    if change == "missing":
        target.pop(next(iter(target)))
    else:
        target["unexpected"] = "value"
    with pytest.raises(ContractError) as error:
        load_contracts(write_task(tmp_path, task))
    assert error.value.code == "fields"


def test_task_set(tmp_path: Path, task: dict[str, Any]) -> None:
    child = copy.deepcopy(task)
    child["id"] = "ORCH-003"
    child["depends_on"] = [task["id"]]
    assert [item.id for item in load_contracts(write_task(tmp_path, [child, task]))] == [
        "ORCH-003",
        "ORCH-002",
    ]


@pytest.mark.parametrize("kind", ["duplicate", "unknown", "cycle"])
def test_invalid_task_set(tmp_path: Path, task: dict[str, Any], kind: str) -> None:
    child = copy.deepcopy(task)
    if kind != "duplicate":
        child["id"] = "ORCH-003"
        child["depends_on"] = ["ORCH-002" if kind == "cycle" else "ORCH-999"]
    if kind == "cycle":
        task["depends_on"] = ["ORCH-003"]
    with pytest.raises(ContractError) as error:
        load_contracts(write_task(tmp_path, [task, child]))
    assert (
        error.value.code
        == {
            "duplicate": "duplicate_id",
            "unknown": "unknown_dependency",
            "cycle": "cycle",
        }[kind]
    )


@pytest.mark.parametrize(
    "text",
    [
        "",
        "[]",
        "id: ORCH-002\nid: ORCH-003",
        "x: &x [1]\ny: *x",
        '!!python/object/apply:os.system ["echo unsafe"]',
        "[",
        "1: invalid",
    ],
)
def test_bad_yaml(tmp_path: Path, text: str) -> None:
    path = tmp_path / "invalid.yaml"
    path.write_text(text)
    with pytest.raises(ContractError):
        load_contracts(path)


def test_file_limits(tmp_path: Path) -> None:
    with pytest.raises(ContractError) as error:
        load_contracts(tmp_path / "missing")
    assert error.value.code == "read_error"
    path = tmp_path / "large"
    path.write_bytes(b"x" * (1_048_576 + 1))
    with pytest.raises(ContractError) as error:
        load_contracts(path)
    assert error.value.code == "too_large"


def test_cli_json_and_no_execution(tmp_path: Path, task: dict[str, Any]) -> None:
    marker = tmp_path / "must-not-exist"
    task["acceptance"]["commands"] = [f"touch {marker}"]
    path = write_task(tmp_path, task)
    result = subprocess.run(
        [sys.executable, "-m", "orchestrator", "validate", str(path)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"valid": True, "task_ids": ["ORCH-002"]}
    assert result.stderr == ""
    assert not marker.exists()
    path.write_text("unexpected: value")
    failures = [
        subprocess.run(
            [sys.executable, "-m", "orchestrator", "validate", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        for _ in range(2)
    ]
    assert all(result.returncode == 2 for result in failures)
    assert failures[0].stdout == failures[1].stdout
    assert json.loads(failures[0].stdout)["errors"][0]["code"] == "fields"
