"""Local SQLite persistence. No task execution, scheduling, or approval grants."""

import json
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from enum import StrEnum
from importlib.resources import files
from pathlib import Path

from orchestrator.contracts import TaskContract


class State(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    REVIEWING = "REVIEWING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    RETRY_PENDING = "RETRY_PENDING"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class StorageError(Exception):
    """Storage failure with a fixed message, excluding task or SQL payloads."""


class Conflict(StorageError):
    """A duplicate identity, stale version, or conflicting idempotency key."""


class SchemaError(StorageError):
    """The database needs explicit initialization or an unsupported migration."""


@dataclass(frozen=True)
class Task:
    id: str
    state: State
    version: int
    contract_json: str
    depends_on: tuple[str, ...]


@dataclass(frozen=True)
class Event:
    sequence: int
    event_id: str
    task_id: str
    kind: str
    from_state: str | None
    to_state: str
    version: int
    created_at: str


class Store:
    """One connection per owner. Use separate instances for concurrent workers."""

    def __init__(self, path: Path, *, initialize: bool = False) -> None:
        # mode=rw prevents accidental database creation when merely opening existing state.
        uri = path.resolve().as_uri() + ("?mode=rwc" if initialize else "?mode=rw")
        self._db = sqlite3.connect(uri, uri=True, isolation_level=None, timeout=5)
        self._db.row_factory = sqlite3.Row
        try:
            self._db.execute("PRAGMA foreign_keys = ON")
            with self._transaction():
                version = self._db.execute("PRAGMA user_version").fetchone()[0]
                if version == 0 and initialize:
                    if self._db.execute(
                        "SELECT 1 FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
                    ).fetchone():
                        raise SchemaError("Refusing to initialize an existing unversioned schema")
                    sql = files(__package__).joinpath("migrations/001.sql").read_text()
                    # executescript commits implicitly; execute complete statements individually.
                    statement = ""
                    for line in sql.splitlines(keepends=True):
                        statement += line
                        if sqlite3.complete_statement(statement):
                            self._db.execute(statement)
                            statement = ""
                    if statement.strip():
                        raise SchemaError("Incomplete schema migration")
                elif version != 1:
                    raise SchemaError("Unsupported schema; explicit reviewed migration required")
            if self._db.execute("PRAGMA journal_mode = WAL").fetchone()[0] != "wal":
                raise StorageError("WAL mode is required")
        except BaseException:
            self._db.close()
            raise

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        self._db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self._db.execute("COMMIT")
        except BaseException:
            self._db.execute("ROLLBACK")
            raise

    def create_tasks(self, contracts: Sequence[TaskContract]) -> None:
        """Atomically insert a complete task set, edges, and creation events."""
        try:
            with self._transaction():
                for contract in contracts:
                    self._db.execute(
                        "INSERT INTO tasks VALUES (?, ?, 'PENDING', 0)",
                        (contract.id, json.dumps(asdict(contract), sort_keys=True)),
                    )
                    self._db.execute(
                        "INSERT INTO events(event_id,task_id,kind,to_state,version) "
                        "VALUES (?, ?, 'created', 'PENDING', 0)",
                        ("created:" + contract.id, contract.id),
                    )
                for contract in contracts:
                    self._db.executemany(
                        "INSERT INTO dependencies VALUES (?, ?)",
                        [(contract.id, dep) for dep in contract.depends_on],
                    )
        except sqlite3.IntegrityError:
            raise Conflict("Task set violates identity or dependency constraints") from None

    def get_task(self, task_id: str) -> Task:
        with self._transaction():
            row = self._db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if row is None:
                raise StorageError("Task not found")
            dependencies = self._db.execute(
                "SELECT dependency_id FROM dependencies WHERE task_id = ? ORDER BY dependency_id",
                (task_id,),
            ).fetchall()
            return Task(
                row["id"],
                State(row["state"]),
                row["version"],
                row["contract_json"],
                tuple(item[0] for item in dependencies),
            )

    def events(self, task_id: str) -> tuple[Event, ...]:
        rows = self._db.execute(
            "SELECT * FROM events WHERE task_id = ? ORDER BY sequence",
            (task_id,),
        ).fetchall()
        return tuple(Event(**dict(row)) for row in rows)

    def transition(
        self,
        task_id: str,
        *,
        expected_version: int,
        state: State,
        event_id: str,
    ) -> Event:
        """CAS update plus audit event; the same request can be replayed safely.

        This primitive enforces concurrency, not the scheduler's allowed transition
        graph or human approval policy. Those checks belong to their later tickets.
        """
        if not event_id or event_id.startswith("created:"):
            raise ValueError("A nonempty event ID outside the creation namespace is required")
        if type(expected_version) is not int or expected_version < 0:
            raise ValueError("Expected version must be a nonnegative integer")
        state = State(state)
        try:
            with self._transaction():
                existing = self._db.execute(
                    "SELECT * FROM events WHERE event_id = ?",
                    (event_id,),
                ).fetchone()
                if existing is not None:
                    event = Event(**dict(existing))
                    if (
                        event.task_id != task_id
                        or event.to_state != state
                        or event.version != expected_version + 1
                        or event.kind != "transitioned"
                    ):
                        raise Conflict("Idempotency key belongs to a different request")
                    return event
                row = self._db.execute(
                    "SELECT state, version FROM tasks WHERE id = ?",
                    (task_id,),
                ).fetchone()
                if row is None or row["version"] != expected_version:
                    raise Conflict("Task is missing or its version has changed")
                self._db.execute(
                    "UPDATE tasks SET state = ?, version = version + 1 "
                    "WHERE id = ? AND version = ?",
                    (state, task_id, expected_version),
                )
                self._db.execute(
                    "INSERT INTO events(event_id,task_id,kind,from_state,to_state,version) "
                    "VALUES (?, ?, 'transitioned', ?, ?, ?)",
                    (event_id, task_id, row["state"], state, expected_version + 1),
                )
                result = self._db.execute(
                    "SELECT * FROM events WHERE event_id = ?",
                    (event_id,),
                ).fetchone()
                return Event(**dict(result))
        except sqlite3.IntegrityError:
            raise Conflict("Transition violates storage constraints") from None
