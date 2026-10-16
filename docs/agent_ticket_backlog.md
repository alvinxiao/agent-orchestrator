# Reading Adventure + Agent Orchestrator: Executable Ticket Backlog

Status: Planning baseline. Derived from 109 decisions across 10 grilling rounds and the v1 engineering specification. No implementation has been executed.

## Global execution policy

- Orchestrator is a separate Python 3.12+ repository; reading game is a separate Next.js/TypeScript repository.
- Initially run a deterministic mock executor. Integrate real Codex CLI only after subscription-based login and supported noninteractive execution are verified.
- Never use an API key, automatically purchase credits, or silently switch to paid API billing for coding agents.
- No access to production data, child records, or secrets. No autonomous merges, database migrations, destructive actions, security-policy changes, or deployments without human approval.
- Every task uses an isolated worktree when editing a Git repository. Worktrees alone are not OS sandboxes; real agents require an approved execution sandbox.
- Every task has explicit inputs, dependencies, scope, acceptance checks, failure handling, and output artifacts. The orchestrator must not trust agent self-reporting.
- Persist task state and audit events; stop safely on limits; resume without double dispatch.

## M1: Mock orchestrator (first shippable milestone)

### ORCH-001 — Bootstrap Python project
- Depends on: none
- Scope: pyproject.toml, src/orchestrator/, tests/, README.md, .gitignore, example config, CLI entrypoint.
- Build: installable Python 3.12+ package; `orchestrator --help`, `orchestrator doctor`, `orchestrator validate <path>` (validation may initially be a placeholder that reports unsupported); pytest, ruff, mypy configured; SQLite and Git available as optional capabilities detected by doctor.
- Acceptance: clean install; `pytest`, `ruff check .`, `mypy src` pass; CLI help exits 0; no network or API credentials required.
- Done when: reproducible local setup documented and CI runs tests.

### ORCH-002 — Task schema and strict validation
- Depends on: ORCH-001
- Scope: src/orchestrator/contracts/, tests/unit/test_contracts.py, examples/tasks/.
- Build: versioned YAML task schema with ID, repository, dependency IDs, scope/allowed paths, requirements, acceptance commands, risk, timeout, retries, permissions; reject unknown fields, malformed IDs, missing criteria, absolute/traversal paths, unsafe command structures, invalid durations, duplicate IDs. Validation does not execute commands.
- Acceptance: valid example parses; missing required fields, unexpected keys, `../` and absolute allowed paths, invalid retry/time budgets, and unsafe permission combinations rejected; deterministic machine-readable errors.
- Done when: `orchestrator validate examples/tasks/example.yaml` exits 0 and negative fixtures fail.

### ORCH-003 — SQLite persistence and append-only events
- Depends on: ORCH-001
- Scope: src/orchestrator/storage/, migrations/, tests/unit/test_storage.py.
- Build: SQLite WAL database with tasks, dependencies, runs, events, workspaces, approvals, and executor status; transactional state transitions, optimistic concurrency or leases, idempotent event recording; schema migration version.
- Acceptance: task creation/retrieval, duplicate rejection, transition atomicity, concurrent lease conflict, process restart persistence, migration test; no secrets in logs.
- Done when: all state changes have an auditable event and failed transactions roll back.

### ORCH-004 — Dependency DAG and ready-task scheduler
- Depends on: ORCH-002, ORCH-003
- Scope: src/orchestrator/scheduler/, tests/unit/test_scheduler.py.
- Build: validate missing dependencies and cycles; stable deterministic ready ordering; block tasks until prerequisites complete; reserve only one active real-executor task initially; policy checks for time window and executor availability.
- Acceptance: diamond DAG schedules correctly; cycle and unknown dependency rejected; failed dependency blocks descendants; repeated scheduling ticks never double-dispatch; deterministic ordering.
- Done when: mock-ready task list is reproducible after restart.

### ORCH-005 — Mock executor and deterministic fault injection
- Depends on: ORCH-002
- Scope: src/orchestrator/executors/, tests/unit/test_mock_executor.py.
- Build: executor Protocol and result types; MockExecutor scenarios success, test failure, transient error, timeout, auth unavailable, usage exhausted, invalid response; seed/config driven, no external calls.
- Acceptance: every scenario produces typed outcome and structured timestamps; deterministic under same inputs; timeout cancellation tested.
- Done when: can run task contract against mock without Codex or network.

### ORCH-006 — Git worktree manager
- Depends on: ORCH-002
- Scope: src/orchestrator/workspaces/, tests/integration/test_worktrees.py.
- Build: verify repository and base SHA, create unique branch/worktree, record metadata, prevent duplicate leases, constrain paths, detect symlink escape, preserve dirty/failed diffs, cleanup only safe completed worktrees. No agent runs in primary checkout.
- Acceptance: two tasks receive distinct worktrees; duplicate lease fails; bad base and path traversal fail; failed task preserves diff; cleanup refuses dirty worktree without explicit approval.
- Done when: worktree creation and cleanup are idempotent and auditable.

### ORCH-007 — Verification runner and reports
- Depends on: ORCH-005, ORCH-006
- Scope: src/orchestrator/verification/, tests/integration/test_verification.py.
- Build: execute allowlisted test commands with per-command timeouts and captured exit status; restrict environment, redact secrets, inspect changed paths, output structured JSON report; test output treated as data not instructions.
- Acceptance: passing, failing, timed-out, missing executable, and unauthorized path cases produce correct status; no successful verification if any required check fails.
- Done when: independent report is generated without relying on executor claims.

### ORCH-008 — Recovery, retries, and pause/resume
- Depends on: ORCH-003, ORCH-004, ORCH-007
- Scope: src/orchestrator/state/, tests/integration/test_recovery.py, CLI commands run/status/resume.
- Build: typed state machine with PENDING, READY, RUNNING, VERIFYING, REVIEWING, AWAITING_APPROVAL, RETRY_PENDING, PAUSED, BLOCKED, FAILED, COMPLETED; bounded classified retries; process restart reconciliation; configurable session window; safe stop and resume; usage-limit queue, no paid fallback.
- Acceptance: simulated crash/restart resumes without duplicate run; test failure routes to repair until max 3 attempts; usage limit pauses; policy violation blocks; completed task has verification evidence.
- Done when: an end-to-end mock task graph finishes, persists, and is replayable from events.

## M2: Real coding agent (gated)

### ORCH-009 — Policy and approval gates
- Depends on: ORCH-008
- Build: risk classifications, immutable audit, approvals for merge, deployment, migrations, secrets, destructive actions, policy changes. Reject privilege escalation.
- Acceptance: approval-required tasks cannot execute gated action without explicit approval.

### ORCH-010 — Subscription-authenticated Codex CLI adapter
- Depends on: ORCH-009
- Build: detect CLI and supported noninteractive flags; verify ChatGPT login; no API-key fallback; run in approved sandbox/worktree; classify usage exhaustion and auth failure; queue and resume.
- Acceptance: successful bounded low-risk task, verification report, safe pause on quota; demonstrably no separately billed API calls.
- Gate: manual verification of installed CLI authentication, sandbox capabilities, and plan usage behavior.

### ORCH-011 — Independent review and integration staging
- Depends on: ORCH-010
- Build: review report, diff summary, mandatory human merge approval, no auto-deploy.
- Acceptance: test-passing but review-failing task cannot complete; merge blocked pending approval.

### ORCH-012 — Metrics and reporting
- Depends on: ORCH-008
- Build: CLI dashboard/report for task success, retries, elapsed time, review defects, interventions, and provider usage if reported. Unknown cost is not zero.
- Acceptance: metrics derive from persisted events, not estimates presented as facts.

## Game tickets (initial backbone)

- GAME-001: Next.js/TypeScript/pnpm monorepo skeleton; strict typing, Vitest, Playwright, CI. Depends: none.
- GAME-002: Versioned curriculum JSON/TS schema for 8 milestones/80 steps, graph references, fixtures. Depends: GAME-001.
- GAME-003: Pure TypeScript prerequisite graph validator; reject cycles and missing IDs. Depends: GAME-002. **First recommended real Codex task.**
- GAME-004: Pronunciation lexicon and phonics pattern model; explicit irregular-word whitelist. Depends: GAME-002.
- GAME-005: Deterministic decodability validator; tokenize, handle ambiguity and inflections; fail closed. Depends: GAME-004.
- GAME-006: Evidence, mastery, retention and parent-override domain model; policy thresholds versioned. Depends: GAME-002.
- GAME-007: Adaptive spaced review and short placement logic. Depends: GAME-006.
- GAME-008: Shared mini-game activity and evidence contracts. Depends: GAME-002, GAME-006.
- GAME-009: Sound Match, Word Builder, Reading Quest accessible interactions. Depends: GAME-008.
- GAME-010: Responsive React shell and polished Phaser 2D world with accessible alternatives. Depends: GAME-001.
- GAME-011: Storybook, approved templates, structured tile creator, mocked AI/image adapters. Depends: GAME-005.
- GAME-012: Supabase schema, parent auth, RLS, child profiles and data deletion tests. Depends: GAME-002. Human approval required for migrations.
- GAME-013: IndexedDB offline progress, operation IDs, deduplication and authenticated sync. Depends: GAME-006, GAME-012.
- GAME-014: Parent dashboard and protected controls. Depends: GAME-006, GAME-012.
- GAME-015: Integrated playable vertical slice, one world, early CVC, three mini-games, storybook. Depends: GAME-009, GAME-010, GAME-011.
- GAME-016: Accessibility, child-safety, authorization, offline, and supervised one-child usability pilot. Depends: GAME-013, GAME-014, GAME-015.

## Release gates

- MVP: automated domain/security/accessibility tests pass and one child can complete a supervised reading session; no claim of proven educational effectiveness.
- Live AI: only after parent-authorized supported provider connection, moderation, strict structured input, deterministic decodability, server quotas, safe fallback, and privacy review.
- Live speech: only after reliability testing with children, parental authorization, privacy controls, and no default raw audio retention.
- Public release: only after separate child privacy/legal and security review.

## First execution sequence

1. Human creates two repositories; install local Python, Git, Node/pnpm as needed.
2. Implement ORCH-001 manually or with supervised Codex.
3. Implement ORCH-002 through ORCH-008 using mock executor and automated tests.
4. Run a complete mock dependency graph, including injected crash, timeout, usage limit, and verification failure.
5. Approve sandbox and subscription-authenticated Codex CLI integration, then implement ORCH-009/010.
6. Create GAME-001/002; assign GAME-003 as first bounded real Codex task.
7. Review resulting diff, tests, logs, usage, and approval gates before merging.