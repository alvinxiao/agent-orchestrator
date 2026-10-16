"""SQLite behavior against real temporary files and independent connections."""

import json
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Barrier

import pytest

from orchestrator.contracts import load_contracts
from orchestrator.storage import Conflict, SchemaError, State, StorageError, Store

EXAMPLE = Path(__file__).resolve().parents[2] / "examples/tasks/example.yaml"


@pytest.fixture
def database(tmp_path: Path) -> Path:
    path = tmp_path / "state.sqlite3"
    with Store(path, initialize=True) as store:
        store.create_tasks(load_contracts(EXAMPLE))
    return path


def test_creation_and_restart(database: Path) -> None:
    with Store(database) as store:
        task = store.get_task("ORCH-002")
        assert task.state is State.PENDING
        assert task.version == 0
        assert json.loads(task.contract_json)["execution"]["max_attempts"] == 3
        assert [(event.kind, event.version) for event in store.events(task.id)] == [("created", 0)]
        store.transition(task.id, expected_version=0, state=State.READY, event_id="ready")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from pathlib import Path; from orchestrator.storage import Store; "
                "import sys; "
                "s=Store(Path(sys.argv[1])); t=s.get_task('ORCH-002'); "
                "print(t.state, t.version, len(s.events(t.id))); s.close()"
            ),
            str(database),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "READY 1 2\n"


def test_duplicate_creation_rolls_back_entire_batch(database: Path) -> None:
    contract = load_contracts(EXAMPLE)[0]
    new = replace(contract, id="ORCH-003")
    with Store(database) as store:
        with pytest.raises(Conflict):
            store.create_tasks([new, contract])
        assert store.events(new.id) == ()
        with pytest.raises(StorageError, match="Task not found"):
            store.get_task(new.id)
        assert len(store.events(contract.id)) == 1


def test_dependencies_are_durable(tmp_path: Path) -> None:
    contract = load_contracts(EXAMPLE)[0]
    dependent = replace(contract, id="ORCH-003", depends_on=(contract.id,))
    path = tmp_path / "deps.sqlite3"
    with Store(path, initialize=True) as store:
        store.create_tasks([dependent, contract])
    with Store(path) as store:
        assert store.get_task(dependent.id).depends_on == (contract.id,)


def test_unknown_dependency_rolls_back(database: Path) -> None:
    contract = replace(load_contracts(EXAMPLE)[0], id="ORCH-003", depends_on=("ORCH-999",))
    with Store(database) as store:
        with pytest.raises(Conflict):
            store.create_tasks([contract])
        assert store.events(contract.id) == ()


def test_idempotent_transition_and_conflicts(database: Path) -> None:
    with Store(database) as store:
        event = store.transition("ORCH-002", expected_version=0, state=State.READY, event_id="one")
        assert (
            store.transition(
                "ORCH-002",
                expected_version=0,
                state=State.READY,
                event_id="one",
            )
            == event
        )
        assert event.from_state == "PENDING" and event.to_state == "READY"
        for version, state, key in [(0, State.RUNNING, "one"), (0, State.READY, "two")]:
            with pytest.raises(Conflict):
                store.transition("ORCH-002", expected_version=version, state=state, event_id=key)
        assert store.get_task("ORCH-002").version == 1
        assert len(store.events("ORCH-002")) == 2


def test_audit_failure_rolls_back_state(database: Path) -> None:
    with sqlite3.connect(database) as db:
        db.execute(
            "CREATE TRIGGER fail_audit BEFORE INSERT ON events "
            "BEGIN SELECT RAISE(ABORT, 'test failure'); END"
        )
    with Store(database) as store:
        with pytest.raises(Conflict):
            store.transition("ORCH-002", expected_version=0, state=State.READY, event_id="one")
        assert store.get_task("ORCH-002").state is State.PENDING
        assert store.get_task("ORCH-002").version == 0
        assert len(store.events("ORCH-002")) == 1


def test_concurrent_workers_cannot_claim_same_version(database: Path) -> None:
    barrier = Barrier(2)

    def claim(key: str) -> str:
        with Store(database) as store:
            barrier.wait(timeout=10)
            try:
                store.transition("ORCH-002", expected_version=0, state=State.RUNNING, event_id=key)
            except Conflict:
                return "conflict"
            return "claimed"

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(claim, ["a", "b"]))
    assert sorted(results) == ["claimed", "conflict"]
    with Store(database) as store:
        assert store.get_task("ORCH-002").version == 1
        assert len(store.events("ORCH-002")) == 2


def test_events_cannot_be_rewritten(database: Path) -> None:
    with sqlite3.connect(database) as db:
        for statement in ("UPDATE events SET to_state='FAILED'", "DELETE FROM events"):
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                db.execute(statement)
        assert db.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


def test_schema_version_wal_and_tables(database: Path) -> None:
    with Store(database, initialize=True):
        pass  # Repeated initialization must preserve existing state and events.
    with sqlite3.connect(database) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1
        assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {
            "tasks",
            "dependencies",
            "runs",
            "events",
            "workspaces",
            "approvals",
            "executor_status",
        } <= tables
        assert db.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
        db.execute("PRAGMA user_version = 99")
    with pytest.raises(SchemaError):
        Store(database, initialize=True)
    with sqlite3.connect(database) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 99


def test_unversioned_schema_is_preserved(tmp_path: Path) -> None:
    path = tmp_path / "existing.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE precious (value TEXT)")
        db.execute("INSERT INTO precious VALUES ('keep')")
    with pytest.raises(SchemaError):
        Store(path, initialize=True)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT value FROM precious").fetchone()[0] == "keep"
        assert db.execute("PRAGMA user_version").fetchone()[0] == 0


def test_open_does_not_create_database(tmp_path: Path) -> None:
    path = tmp_path / "missing.db"
    with pytest.raises(sqlite3.OperationalError):
        Store(path)
    assert not path.exists()


def test_storage_does_not_log_contract_payloads(
    database: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    contract = replace(load_contracts(EXAMPLE)[0], id="ORCH-003", title="sensitive-fixture-marker")
    with Store(database) as store:
        store.create_tasks([contract])
        with pytest.raises(Conflict) as error:
            store.create_tasks([contract])
        assert "sensitive-fixture-marker" not in str(error.value)
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""
    assert caplog.text == ""


def test_failed_initialization_is_atomic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    resources = tmp_path / "resources"
    (resources / "migrations").mkdir(parents=True)
    (resources / "migrations/001.sql").write_text(
        "CREATE TABLE partial (id INTEGER);\nINVALID SQL;\n"
    )
    monkeypatch.setattr("orchestrator.storage.files", lambda _: resources)
    path = tmp_path / "failed.db"
    with pytest.raises(sqlite3.OperationalError):
        Store(path, initialize=True)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 0
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []


def test_replay_after_later_transition_does_not_rewind(database: Path) -> None:
    with Store(database) as store:
        original = store.transition(
            "ORCH-002",
            expected_version=0,
            state=State.READY,
            event_id="first",
        )
        store.transition("ORCH-002", expected_version=1, state=State.RUNNING, event_id="second")
        assert (
            store.transition(
                "ORCH-002",
                expected_version=0,
                state=State.READY,
                event_id="first",
            )
            == original
        )
        assert store.get_task("ORCH-002").state is State.RUNNING
        assert store.get_task("ORCH-002").version == 2
        assert len(store.events("ORCH-002")) == 3
