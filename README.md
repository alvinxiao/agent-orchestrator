# Agent Orchestrator

A Python-based, dependency-aware autonomous coding-agent orchestrator. Its first real-world workload is developing **Reading Adventure**, a separate browser-based structured-literacy learning game for children ages 4–8.

## Goals
- Structured agent-executable task contracts and dependency DAG
- Persistent SQLite state transitions and event history
- Isolated Git worktrees per task, then restricted execution sandboxing
- Provider-neutral mock executor first, then Codex CLI using supported ChatGPT subscription authentication
- Deterministic verification, bounded retries, recoverability, human approval gates
- No automatic usage of separately billed APIs or credit purchases

## Execution order
1. ORCH-001: Python project bootstrap, CLI, pytest
2. ORCH-002: Task schema validation
3. ORCH-003: SQLite persistence/event log
4. ORCH-004: Dependency scheduler
5. ORCH-005: Mock executor
6. ORCH-006: Git worktree manager
7. ORCH-007: Verification pipeline
8. ORCH-008: Retries, pause/resume, restart recovery
9. ORCH-009: Policy and approval controls
10. ORCH-010: Supported Codex CLI integration

The comprehensive engineering specification and agent ticket backlog were prepared in ChatGPT and should be placed under `docs/engineering_specification.md` and `docs/agent_ticket_backlog.md`. Do not claim those documents are present until uploaded.

See [AGENTS.md](AGENTS.md) for agent working rules.


## Local development (Python 3.12+)

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m orchestrator --help
orchestrator version
orchestrator doctor
```

The package uses PyYAML for safe YAML parsing. Installation downloads build/development
packages; installed CLI commands and tests run offline without API credentials.
`version` reports `0.1.0`. `doctor` reports Git and SQLite availability; both are
optional at this stage, so missing capabilities do not make the command fail.
`python -m orchestrator` and the installed `orchestrator` command share the same CLI.

```sh
pytest
ruff check .
mypy src
python -m compileall -q src
```

CI runs these checks on Python 3.12. Smoke tests cover package metadata, both CLI
entry points, argument errors, capability reporting, and strict contract validation.
`orchestrator validate <path>` validates a versioned YAML task or complete task list
and emits JSON (exit 0 for valid, 2 for invalid). See [task contracts](docs/task-contracts.md).
No executor, provider integration, scheduler or live agent is implemented. No services start,
network/API requests occur, or local state is created by CLI commands.

`config/example.toml` illustrates a future local state location; it is not loaded
by the bootstrap CLI. Local state, environments, logs, and Python caches are ignored.
SQLite persistence is available through the Python API; see [storage](docs/storage.md).
The next implementation ticket is ORCH-004 (dependency scheduling).

## Agent workflow and subscription usage

Agents use the local [pstack-budget skill](.agents/skills/pstack-budget/SKILL.md):
one agent by default, focused context, bounded repair loops, and required verification.
See [workflow options and limits](docs/pstack-workflow.md) for the Lean default and
optional focused review. This is a pstack adaptation, not a Cursor plugin install
or an enforced token quota. No paid API fallback or automatic merge is enabled.
