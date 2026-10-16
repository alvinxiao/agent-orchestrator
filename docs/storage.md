# Local SQLite storage

ORCH-003 adds a Python API, not a scheduler or a database CLI command. It uses
stdlib SQLite, WAL mode, foreign keys, explicit transactions, and schema version 1.
No provider, worker, background service, or additional dependency is introduced.

After reviewing the bundled schema, initialize a new local database explicitly:

```python
from pathlib import Path
from orchestrator.contracts import load_contracts
from orchestrator.storage import State, Store

contracts = load_contracts(Path("examples/tasks/example.yaml"))
with Store(Path(".orchestrator/state.sqlite3"), initialize=True) as store:
    store.create_tasks(contracts)
    task = store.get_task("ORCH-002")
    event = store.transition(
        task.id, expected_version=task.version, state=State.READY,
        event_id="example-ready-1",
    )
```

Create the parent directory yourself. This example writes local state; run it only
when desired. Opening `Store(path)` requires an existing version-1 database and
never creates a missing file. `initialize=True` creates only an empty schema or
reopens version 1; it refuses nonempty unversioned databases and unknown versions.
Existing user databases are not upgraded automatically. Schema changes remain
subject to human review. The initial SQL lives inside the package at
`src/orchestrator/storage/migrations/001.sql` and is included in built wheels.

`create_tasks` inserts validated contracts, dependency edges, and one creation event
per task in one transaction. Supply complete prerequisite sets or dependencies
already in storage. Duplicate task IDs, duplicate edges, self-dependencies, and
unknown dependencies fail without partial inserts. Contract validation happens in
`load_contracts`; storage callers must pass validated contracts. Stored contracts
retain their JSON representation; dependency queries return sorted IDs.

`transition` requires the expected task version. Concurrent writers using separate
Store instances cannot both update the same version. A stale version raises
`Conflict`. The state update and audit insertion commit together or both roll back.
Use a unique event ID for each logical request; retrying that exact request returns
the original event without updating state again, even after later transitions.
Reusing its ID for a different request fails. The `created:` namespace is reserved.
SQLite event triggers reject UPDATE and DELETE through ordinary SQL connections.
This is not tamper protection against someone who can modify the database schema.

Each Store belongs to one thread; close it or use its context manager. Separate
workers must use separate instances/connections. SQLite waits up to five seconds
for locks; operational failures propagate without automatic retry. No lease expiry
or recovery scheduler is implemented. The storage primitive validates state names
and concurrency; it does not authorize transitions, verify approvals, or enforce
allowed state edges. Those remain ORCH-004/008/009 responsibilities.

Tables for runs, workspaces, approvals, and executor status establish foreign-keyed
storage shapes only. They have no public mutation APIs yet and confer no approval
or execution authority. Current audited APIs mutate tasks and dependencies only.
Do not write auxiliary tables directly as an application integration.

Storage emits no logs and does not print contract/SQL payloads. Event rows contain
identifiers, states, versions, and timestamps only. Caller-supplied identifiers and
contracts must never contain secrets or child data; contract JSON is retained in
the local database. No redaction service or encrypted storage is claimed.

Tests use disposable temporary databases to verify rollback, concurrency conflict,
idempotency, append-only events, version checks, initialization rollback, and actual
subprocess restart persistence. No existing user database is migrated by the suite.
