CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    contract_json TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('PENDING','READY','RUNNING','VERIFYING','REVIEWING',
        'AWAITING_APPROVAL','RETRY_PENDING','PAUSED','BLOCKED','FAILED','COMPLETED')),
    version INTEGER NOT NULL CHECK(version >= 0)
);
CREATE TABLE dependencies (
    task_id TEXT NOT NULL REFERENCES tasks(id),
    dependency_id TEXT NOT NULL REFERENCES tasks(id),
    PRIMARY KEY(task_id, dependency_id),
    CHECK(task_id != dependency_id)
);
CREATE TABLE events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    task_id TEXT NOT NULL REFERENCES tasks(id),
    kind TEXT NOT NULL CHECK(kind IN ('created','transitioned')),
    from_state TEXT,
    to_state TEXT NOT NULL,
    version INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE(task_id, version)
);
CREATE TRIGGER events_no_update BEFORE UPDATE ON events
BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
CREATE TRIGGER events_no_delete BEFORE DELETE ON events
BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
CREATE TABLE workspaces (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id),
    path TEXT NOT NULL UNIQUE,
    base_sha TEXT NOT NULL
);
CREATE TABLE runs (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id),
    workspace_id TEXT REFERENCES workspaces(id),
    executor TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT
);
CREATE TABLE approvals (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id),
    action TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected')),
    decided_at TEXT
);
CREATE TABLE executor_status (
    executor TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
PRAGMA user_version = 1;
