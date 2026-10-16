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
