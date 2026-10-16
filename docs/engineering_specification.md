# Reading Adventure + Autonomous Coding Orchestrator

**Engineering specification v1.0**  
**Date:** 2026-10-09  
**Source:** Ten design rounds, 109 decisions, plus explicit child-safety and subscription-cost constraints.  
**Status:** Implementation baseline; live integrations subject to verification gates.

## 1. Executive summary

This project comprises two separate systems:

- **Reading Adventure:** A responsive browser-based literacy adventure for children ages 4–8, progressing from phonemic awareness to approximately second-grade reading. Features include structured literacy, adaptive mastery, mini-games, decodable stories, an adventure hub, optional speech, and a restricted story creator.
- **Agent Orchestrator:** A custom Python tool that builds Reading Adventure using dependency-aware task contracts, isolated Git worktrees, coding agents, tests, review, retries, approval gates, and durable state.

**Dual success criteria:** (1) A child can complete a useful, accessible early-reading session; (2) the orchestrator can deliver a verified code change through bounded, unattended execution.

### Non-negotiable requirements

1. The game remains playable without AI or network access to AI providers.
2. Children cannot access unrestricted general-purpose AI or enter freeform prompts; only predefined story choices are allowed.
3. Live story AI requires a verified, parent-authorized provider connection, server-side quota controls, moderation, deterministic decodability verification, and safe fallbacks.
4. Independently readable text contains only words decodable using currently permitted grapheme/phoneme patterns or explicitly mastered irregular words. Rich concepts may appear in a separate illustration/narration layer.
5. The curriculum engine, not an AI model, is authoritative for lessons, prerequisites, mastery, retention, and decodability.
6. Child data is minimized, access-controlled, and never exposed to coding agents.
7. Codex execution must use supported ChatGPT Plus subscription sign-in, **without automatically switching to separately billed API calls or purchasing credits**. On limits, queue and resume later.
8. Target incremental coding-agent charges: $0 beyond existing ChatGPT Plus. Initial game infrastructure/AI text target: under $10/month; optional speech services: under $5/month. These are targets, not guarantees.
9. Private family prototype first; public launch requires a separate compliance and security gate.

## 2. MVP and release scope

### First playable game vertical slice

- One polished, themed 2D adventure world with an avatar and simple interactive locations.
- Early phonemic awareness, letter-sound knowledge, and initial consonant-vowel-consonant (CVC) decoding, with a small curated, prerequisite-complete subset of skills.
- Short adaptive placement assessment and parent override.
- Three reusable mini-game patterns: sound match, word builder, and reading quest.
- Guided 5–15-minute sessions plus free play, with rewards, embedded review, and supportive error recovery.
- Versioned curriculum data, mastery and retention tracking, deterministic phonics/word validation.
- Decodable storybook and story creator interface with **mocked** text and illustration generation and curated assets.
- Basic parent progress dashboard, guest mode, substantial offline persistence, and defined cloud-sync contracts.
- Comprehensive accessibility, automated acceptance tests, and a supervised usability pilot with one child. This pilot does not establish educational efficacy.

### Deferred beyond MVP

Full 80-step curriculum content; live AI text/images; production speech assessment; public galleries; public release; advanced analytics; broad multi-agent concurrency; complex open-world gameplay. Design interfaces to support these later without enabling them prematurely.

### First orchestrator MVP

A CLI application that loads a structured task, validates its dependencies and permissions, allocates a Git worktree, invokes a deterministic mock executor, runs verification, persists events, handles classified failures, and recovers after interruption. Next, integrate one real subscription-authenticated Codex CLI agent.

## 3. System architecture

### Reading Adventure

- **Frontend:** Next.js + React + TypeScript, responsive desktop/tablet/phone PWA.
- **Rendering:** React for lessons, text, accessible navigation, stories, parent dashboard; Phaser for selected 2D adventure scenes.
- **Backend:** Modular monolith with explicit curriculum, gameplay, accounts, stories, AI, and sync boundaries.
- **Core:** Pure TypeScript curriculum/phonics/mastery packages, independent of UI and providers.
- **Database/auth:** Supabase PostgreSQL, Auth, Storage, row-level security (RLS).
- **Offline:** IndexedDB and versioned service-worker caches, append-only learning evidence, synchronization queue.
- **AI:** Server-side provider abstraction with a mocked first implementation; live connection only after authorization and safety gates.
- **Development:** Local first, cloud previews/CI later; production hosting deferred.
- **Tests:** Vitest, Playwright, axe-core, integration, adversarial/security, manual accessibility and child usability.

Suggested monorepo:

```text
reading-adventure/
  apps/web/{app,components,game,server,public}/
  packages/{curriculum,phonics,mastery,activities,story-engine,shared-types,accessibility}/
  content/{curriculum,lessons,words,stories,assets}/
  supabase/{migrations,seed}/
  tests/{integration,e2e,accessibility,adversarial}/
  docs/
```

### Agent Orchestrator

- Python 3.12+ CLI, SQLite persistence, pytest.
- Explicit task dependency graph and state machine.
- Provider-neutral `CodingExecutor` protocol: deterministic mock first, Codex CLI second.
- Separate Git repository from the game. Each task receives a separate worktree and branch.
- Restricted command execution; worktrees alone are **not** a security sandbox. Use restricted containers or equivalent isolation for unattended untrusted commands.
- Structured verification, review, approval, telemetry, and bounded retries.

Suggested repository:

```text
agent-orchestrator/
  src/orchestrator/{scheduler,state,executors,worktrees,verification,review,policies,telemetry}/
  tasks/
  tests/{unit,integration,fault_injection}/
  config/
  scripts/
  docs/
```

## 4. Curriculum structure and contracts

### Eight milestones, ten steps each

| Milestone | Steps | Focus |
|---|---|---|
| 1. Phonemic awareness | 1–10 | Recognize, blend, segment, manipulate spoken sounds |
| 2. Letter sounds | 11–20 | Grapheme/phoneme correspondence |
| 3. CVC decoding | 21–30 | Blend and decode regular unfamiliar words |
| 4. Decodable sentences and stories | 31–40 | Connected independent reading |
| 5. Advanced phonics | 41–50 | Digraphs, blends, silent-e, vowel teams |
| 6. First-grade reading | 51–60 | Irregular words, inflections, r-controlled vowels |
| 7. Second-grade transition | 61–70 | Syllables, affixes, multisyllabic words |
| 8. Fluency and comprehension | 71–80 | More fluent connected reading and meaning |

Milestones are organizational, not a rigid age sequence. Progression uses a directed acyclic prerequisite graph, adaptive review, and parent overrides. Full lesson sequences and lexicons require expert review before educational release.

```ts
type SkillDomain =
  | 'phonemic_awareness' | 'phonics' | 'spelling'
  | 'fluency' | 'vocabulary' | 'comprehension';

interface SkillDefinition {
  id: string;
  version: number;
  milestone: number;
  step: number;
  domain: SkillDomain;
  title: string;
  description: string;
  prerequisites: string[];
  graphemeIds: string[];
  phonemeIds: string[];
  lessonIds: string[];
  assessmentIds: string[];
  masteryPolicyId: string;
  reviewPolicyId: string;
}
```

Publication validation must reject unknown references, cycles, missing lessons/assessments, unsupported pronunciations, and nondecodable approved stories. Historical progress remains tied to the curriculum version under which it was earned; migrations must be explicit.

## 5. Learning evidence, mastery, and review

```ts
type SkillStatus = 'not_introduced' | 'learning' | 'practicing' | 'mastered';
interface ChildSkillState {
  childId: string;
  skillId: string;
  curriculumVersion: string;
  status: SkillStatus;
  masteryConfidence: number;
  retentionConfidence: number;
  firstIntroducedAt?: string;
  masteredAt?: string;
  lastPracticedAt?: string;
  nextReviewAt?: string;
  parentOverride?: { status: SkillStatus; reason?: string; changedAt: string };
}
interface LearningAttempt {
  id: string;
  childId: string;
  activityId: string;
  skillIds: string[];
  evidenceType: string;
  difficulty: number;
  correct: boolean;
  hintsUsed: number;
  attemptsInActivity: number;
  responseTimeMs?: number;
  assessmentSource: 'interaction' | 'speech' | 'parent';
  occurredAt: string;
}
```

Evidence types: recognition, blending, segmentation, spelling, unfamiliar-word decoding, optional oral reading, and comprehension. Guessing, hinted answers, and repeated retries must not count as independent mastery.

**Initial configurable engineering thresholds**, subject to child testing and curriculum review: at least 85% independent accuracy over at least 8 eligible attempts, across 2 sessions and 2 applicable activity types, plus one successful delayed review. Hinted attempts and speech-only evidence cannot establish independent mastery. Use domain-specific policies where these thresholds are inappropriate.

Retention is tracked separately from historical mastery. A suggested initial review sequence is 1, 3, 7, 14, 30 days, adjusted for errors and elapsed time. Weakening retention schedules reinforcement and restricts affected future independent-reading content unless a parent overrides.

## 6. Deterministic decodability

The authoritative validator combines a versioned pronunciation lexicon, phonics-pattern analysis, permitted grapheme/phoneme inventory, mastered irregular words, and reviewed curriculum exceptions.

```ts
interface ReadingInventory {
  curriculumVersion: string;
  masteredGraphemeIds: string[];
  masteredPhonemeIds: string[];
  masteredIrregularWordIds: string[];
  restrictedSkillIds: string[];
}
interface WordValidation {
  token: string;
  normalizedToken: string;
  permitted: boolean;
  classification: 'decodable' | 'mastered_irregular' | 'not_permitted' | 'unknown';
  requiredSkillIds: string[];
  reasonCodes: string[];
}
interface StoryValidationResult {
  valid: boolean;
  words: WordValidation[];
  rejectedTokens: string[];
  curriculumVersion: string;
  inventoryFingerprint: string;
}
```

Unknown proper nouns, unsupported patterns, and unresolved ambiguous pronunciations fail closed. Explicit rules/tests are required for punctuation, contractions, inflections, compound words, and syllable boundaries.

**Two-layer stories:** The independent reading layer contains only validated words. Richer concepts may be conveyed via illustrations and optional narrated/supporting presentation, clearly distinguished from independent reading. Narration does not count as demonstrated decoding.

AI story pipeline: approved structured choices → server authorization/quota check → restricted generation → content moderation → deterministic decodability validation → bounded repair/revalidation → immutable approved story version. If any check fails, return a curated safe template. Never show unverified content.

## 7. Gameplay and story creator

Adventure hub: guided lessons, mini-games, storybook, story library, avatar customization, unlockable themed areas. A typical session welcomes the child, reviews a prior skill, teaches/practices a target, runs an activity, records evidence, rewards progress, and offers continued play or a break. Children may stop without penalty.

MVP activities:

1. **Sound Match:** Tap/select spoken sound or letter.
2. **Word Builder:** Drag-and-drop or accessible alternative to build/blend words.
3. **Reading Quest:** Select/sequence/respond using decodable content and basic comprehension.

Activities consume the central curriculum inventory and emit standardized evidence. Repeated errors trigger modeling, simpler alternatives, and gentle exits, not shame or punishment.

Story creator: guided visual wizard for young children and drag/drop event board for older children. Children choose only approved characters, settings, objects, actions, ordered events, and endings; no freeform prompt entry. The creator is available early even before live AI. Prebuilt templates and mock text/illustration adapters power MVP.

```ts
interface StoryDraft {
  id: string;
  childId: string;
  titleChoiceId?: string;
  characterIds: string[];
  settingId: string;
  events: Array<{
    id: string;
    actionId: string;
    characterIds: string[];
    objectIds: string[];
    order: number;
  }>;
  endingId?: string;
}
interface StoryVersion {
  id: string;
  storyId: string;
  version: number;
  curriculumVersion: string;
  readingInventoryFingerprint: string;
  pages: Array<{
    pageNumber: number;
    independentReadingText: string;
    illustrationAssetId: string;
    narrationAssetId?: string;
    comprehensionActivityId?: string;
  }>;
  validationStatus: 'approved' | 'rejected';
  createdAt: string;
}
```

Library supports favorites, progress, difficulty, reread history, and preserved versions. Older children may make advanced editions. Only approved versions display as independently readable. Parent-controlled export/print is allowed; public sharing is excluded.

## 8. Optional speech assessment

Progression may include sounds, blending, words, sentences, and stories. Speech is optional supporting evidence; never the sole basis for mastery. Recognition uncertainty offers a supportive retry, touch interaction, or parent verification without penalty. Provider-neutral adapters must distinguish pronunciation assessment from simple transcription.

```ts
interface SpeechAssessmentResult {
  status: 'accepted' | 'retry' | 'uncertain' | 'unavailable';
  targetId: string;
  confidence?: number;
  phonemeFeedback?: Array<{ phonemeId: string; assessment: string }>;
  providerId: string;
  providerVersion: string;
}
```

Local-first, optional cloud only with appropriate parent controls. No raw audio retention by default. Production integration requires supervised child-voice reliability testing and data-handling review.

## 9. Accounts, parent controls, privacy

Guest play is supported; an account is required for cloud sync and live AI. Parent authentication options: Google, Apple, email. Each parent may manage multiple independent pseudonymous child profiles. Collect a nickname, avatar, broad age band, and necessary learning state, not legal names, exact birthdays, photos, or precise location.

Sensitive settings require parent reauthentication or a PIN: AI connection, quotas/spending, export/deletion, profile permissions, protected learning controls. A hidden menu is not sufficient authorization.

**Three distinct permissions:** app login, AI-provider authorization, and child-data processing consent. ChatGPT login/subscription is not automatically third-party AI API authorization. Do not collect ChatGPT passwords/cookies. Verify an actually supported provider authorization flow before enabling live AI.

Logical database tables:

- `parent_accounts`, `child_profiles`
- `curriculum_versions`, `skill_definitions`, `child_skill_states`
- `learning_attempts`, `review_schedule`, `game_progress`
- `story_drafts`, `stories`, `story_versions`, `reading_sessions`
- `ai_connections`, `ai_usage`, `audit_events`

Enforce parent-scoped RLS, server-derived identity, validated learning evidence, immutable story approvals, encrypted provider secrets, and controlled deletion/export. Service-role credentials must never reach the browser.

For a public launch, separately review COPPA and applicable privacy law, consent, notices, data retention, processor contracts, and security. No behavioral advertising or profiling of children.

## 10. Offline storage and sync

Cache versioned application assets, lessons, curriculum, and approved stories with a service worker; use IndexedDB for local profiles, attempts, skill states, progress, and pending operations.

```ts
interface SyncOperation {
  operationId: string;
  deviceId: string;
  childId: string;
  entityType: string;
  entityId: string;
  operationType: string;
  payloadVersion: number;
  payload: unknown;
  occurredAt: string;
  createdLocallyAt: string;
}
```

Conflict rules:

- Attempts: append-only, deduplicated by idempotency key.
- Mastery: recompute from accepted evidence and explicit parent overrides.
- Stories: immutable versions; preserve concurrent versions.
- Simple preferences: version-aware last writer.
- Rewards: derive from verified achievements when possible.
- Security settings and AI quotas: server authoritative.
- Curriculum-version conflicts: explicit migration, never silent merge.

Guest-to-account migration requires parent confirmation and correct child ownership. Shared-device offline data must be profile-isolated, with browser storage's security limitations acknowledged.

## 11. AI security and content gateway

Permitted task types only:

```ts
type AllowedAiTask =
  | 'generate_decodable_story'
  | 'repair_decodable_story'
  | 'generate_story_illustration';
```

The server builds trusted prompts from structured inputs. Reject unknown operations/fields, arbitrary browsing/tools/files, and general chat. Moderate inputs/outputs, parse strict schemas, validate decodability, enforce atomic quotas, and fail to approved offline templates. Provider output and stored story text are untrusted data, not instructions.

Threat controls cover prompt injection, unsafe generated content, quota bypass, cross-child access, stolen credentials, unauthorized parent changes, external links, uploads, and excessive retention. No child uploads or arbitrary external navigation in MVP.

Example API surface:

| Route | Method | Purpose |
|---|---|---|
| `/api/profiles` | GET/POST | Authorized child profiles |
| `/api/profiles/:id` | PATCH/DELETE | Update/delete child |
| `/api/curriculum` | GET | Published curriculum |
| `/api/placement` | POST | Placement evidence |
| `/api/learning/sync` | POST | Validated operation sync |
| `/api/progress/:childId` | GET | Skill and game progress |
| `/api/stories` | GET/POST | Story drafts |
| `/api/stories/:id/versions` | GET | Approved versions |
| `/api/stories/generate` | POST | Restricted generation |
| `/api/parent/ai-settings` | GET/PATCH | Protected AI settings |

All writes require schema validation, auth, ownership, payload limits, and rate limits. The server retrieves the authoritative reading inventory; a client-provided fingerprint is not proof of mastery.

## 12. Orchestrator task contracts

Structured YAML contracts specify scope, dependencies, acceptance commands/tests, timeout, retry budget, risk, and permissions.

```yaml
id: GAME-003
title: Implement curriculum prerequisite validation
repository: reading-adventure
depends_on: [GAME-002]
scope:
  allowed_paths:
    - packages/curriculum/**
    - tests/**
requirements:
  - Reject prerequisite cycles
  - Reject unknown skill references
  - Preserve deterministic ordering
acceptance:
  commands:
    - pnpm --filter curriculum typecheck
    - pnpm --filter curriculum test
  required_tests:
    - rejects_self_cycle
    - rejects_multi_node_cycle
    - rejects_unknown_prerequisite
execution:
  executor: codex
  max_attempts: 3
  timeout_minutes: 30
permissions:
  network: restricted
  production_access: false
  secrets_access: false
  may_merge: false
  may_deploy: false
risk_level: low
```

Reject contracts with missing acceptance criteria, unknown dependencies, invalid path scopes, or permissions exceeding policy.

## 13. Orchestrator state machine and scheduler

States: `PENDING`, `READY`, `RUNNING`, `VERIFYING`, `REVIEWING`, `AWAITING_APPROVAL`, `RETRY_PENDING`, `PAUSED`, `BLOCKED`, `FAILED`, `COMPLETED`.

Transitions are atomic, logged, and persisted. A task becomes ready only after all prerequisites complete. The scheduler also checks workspace availability, execution window, usage budget, approvals, and policy. Initial real-agent concurrency is one. Reconcile interrupted processes/worktrees on restart; prevent double dispatch with durable reservations or leases.

```python
def scheduler_tick(state, policy):
    reconcile_running_tasks(state)
    if policy.time_window_exhausted():
        pause_runnable_tasks(state)
        return
    for task in state.tasks.ready_by_dependencies():
        if not policy.allows(task):
            state.block(task.id, 'POLICY_DENIED')
            continue
        if not policy.budget_allows(task):
            state.pause(task.id, 'BUDGET_LIMIT')
            continue
        if not state.resources_available(task):
            continue
        state.reserve(task.id)
        dispatch(task)
        break
```

## 14. Executor integration and cost policy

```python
from typing import Protocol

class CodingExecutor(Protocol):
    async def execute(
        self,
        task: 'TaskContract',
        workspace: 'Workspace',
        limits: 'ExecutionLimits',
    ) -> 'ExecutionResult': ...
```

**MockExecutor:** Deterministic success, failure, malformed output, timeout, usage-limit, and fault-injection cases.

**CodexCliExecutor:** Detect installation, verify supported subscription sign-in, use documented noninteractive execution, capture results and redacted logs, enforce timeout, classify auth/usage failures, and report provider usage where available. If a capability is not supported, fail clearly; do not invent it.

**Hard billing policy:** No separately billed OpenAI API fallback, automatic credit purchases, or silent plan upgrades. Pause and queue on limits. Unknown cost metrics are `unknown`, not $0. Usage limits and unattended CLI behavior require verification in the actual environment.

## 15. Worktrees, sandbox, verification, and approvals

Each task gets a separate branch/worktree from a recorded base commit. Prevent simultaneous access to the same worktree, unexpected path edits, symlink/path traversal, and access to production secrets. Preserve failed diffs. Worktrees isolate Git changes, **not** OS privileges; use a restricted execution environment for unattended commands.

Verification pipeline:

1. Modified-path and repository-integrity checks.
2. Format, lint, typecheck.
3. Task-specific unit and applicable integration tests.
4. Security/curriculum invariants.
5. Machine-readable verification report.
6. Independent review of requirements, scope, regressions, tests, and security.

An agent's self-reported success is not acceptance. During the single-agent phase, deterministic checks plus human review may provide independent review; add a second AI reviewer only when safe and within subscription limits.

**Human approval required** for security-policy changes, credentials, database migrations, destructive actions, significant dependency risks, merging, and deployment. Agents cannot change their own approval/sandbox policy.

Failure classes and response:

| Class | Response |
|---|---|
| Transient process failure | Bounded retry/backoff |
| Test/typecheck failure | Return targeted report for repair |
| Review rejection | Repair with findings |
| Authentication or usage limit | Pause/queue; no paid fallback |
| Timeout | Terminate safely; preserve workspace |
| Policy violation/unexpected files | Stop, quarantine, human review |
| Persistent failure | Terminal failure and escalation |

Initial max attempts: 3, configurable. Retries do not reset global time/usage limits. Unattended execution window is configurable with a conservative default.

## 16. Orchestrator storage and telemetry

SQLite tables: `tasks`, `dependencies`, `runs`, `workspaces`, `events`, `verification_results`, `review_results`, `approvals`, `usage_records`, `executor_status`.

Track completion and verified integration rates, first-attempt success, retries, failure categories, wall-clock duration, approval waiting time, human interventions, test pass rate, review defects, provider usage, and incremental cost when known. Provide readable audit trails for all state transitions.

## 17. Definition of done

For every ticket: traceability to specification, passing typecheck and applicable tests, no unauthorized file edits, no new high-severity security findings, preserved curriculum invariants, accessibility validation for UI, reviewed migrations, updated contracts/docs, and completed review/approval gates.

### Educational acceptance tests

| ID | Scenario | Expected |
|---|---|---|
| EDU-001 | Cyclic prerequisites | Reject publication |
| EDU-002 | Unknown prerequisite | Reject publication |
| EDU-003 | Unmastered grapheme in word | Reject independent reading |
| EDU-004 | Mastered irregular word | Permit only under correct inventory |
| EDU-005 | AI story has unknown word | Reject or repair/revalidate |
| EDU-006 | Repair still invalid | Safe fallback |
| EDU-007 | Repeated hinted answers | No independent mastery |
| EDU-008 | Full mastery evidence | Mark mastered |
| EDU-009 | Failed delayed review | Reduce retention, schedule review |
| EDU-010 | Parent override | Preserve evidence and audit override |
| EDU-011 | Early placement completion | Return appropriate skill estimate |
| EDU-012 | Speech unavailable | Touch/parent fallback |
| EDU-013 | Repeated struggle | Demonstration and gentle exit |
| EDU-014 | Reread older story | Preserve original approved version |
| EDU-015 | Curriculum update | Historical evidence interpretable |

Include curated and property-based phonics tests for pronunciation ambiguity, unfamiliar regular words, contractions, inflections, and pattern boundaries.

### Security acceptance tests

| ID | Scenario | Expected |
|---|---|---|
| SEC-001 | Parent A accesses Parent B child | Denied |
| SEC-002 | Child changes AI quota | Denied |
| SEC-003 | Forged mastery state | Reject/recompute |
| SEC-004 | Unrestricted AI instruction | Reject before provider |
| SEC-005 | Unsafe AI output | Block/fallback |
| SEC-006 | Prompt injection in output | Never execute |
| SEC-007 | Quota exceeded | No provider invocation |
| SEC-008 | No provider authorization | Templates only |
| SEC-009 | Parent deletes profile | Apply retention/deletion policy |
| SEC-010 | Browser network/public assets | No server credentials |
| SEC-011 | Forged story approval | Denied |
| SEC-012 | Guest migration | Confirm ownership and parent intent |

### Offline and accessibility acceptance tests

| ID | Scenario | Expected |
|---|---|---|
| OFF-001 | Offline with cached lessons | Core lesson playable |
| OFF-002 | Activity completed offline | Attempt persists |
| OFF-003 | Reconnect | Sync exactly once |
| OFF-004 | Duplicate operation IDs | No duplicate evidence |
| OFF-005 | Concurrent device updates | Authoritative recomputation |
| OFF-006 | Old curriculum cache | Explicit version handling |
| A11Y-001 | Nonreader navigation | Audio instructions |
| A11Y-002 | No pointer | Essential activities operable |
| A11Y-003 | Reduced motion | Nonessential motion reduced |
| A11Y-004 | No sound | Suitable alternative where valid |
| A11Y-005 | Inaccessible Phaser interaction | Equivalent accessible control |

Automated accessibility tests must be supplemented by manual keyboard, touch, and assistive-technology tests. Alternatives must not invalidate the educational construct being assessed.

### Orchestrator acceptance tests

| ID | Scenario | Expected |
|---|---|---|
| ORCH-001 | Missing dependency | Remains pending |
| ORCH-002 | Dependency cycle | Reject graph |
| ORCH-003 | Mock success | Advances to verification |
| ORCH-004 | Transient failure | Bounded retry |
| ORCH-005 | Failed tests | Repair path |
| ORCH-006 | Retry exhausted | Fail/escalate |
| ORCH-007 | Mid-task crash | Recoverable state |
| ORCH-008 | Unauthorized file edits | Reject |
| ORCH-009 | Secret access attempt | Block/stop |
| ORCH-010 | Codex auth unavailable | Pause |
| ORCH-011 | Codex usage limit | Queue, no paid fallback |
| ORCH-012 | Time window exceeded | Safe pause |
| ORCH-013 | Database migration | Human approval |
| ORCH-014 | Tests pass, review fails | Not complete |
| ORCH-015 | Deployment request | Human approval |
| ORCH-016 | Worktree failure | No unsafe execution |
| ORCH-017 | Double dispatch | Prevented by lease |
| ORCH-018 | No usage telemetry | Record unknown |

**Real-agent demonstration:** Select a low-risk ready task; create worktree; invoke subscription-authenticated Codex; produce a change; run tests; preserve logs; stop at review/approval; resume after interruption. No production deployment needed.

## 18. Delivery milestones

| Milestone | Deliverable |
|---|---|
| M0 | Both repo skeletons, CI, test/schema foundations |
| M1 | Mock orchestrator: task contracts, SQLite, graph, worktrees, mock executor, verification, recovery |
| M2 | Real Codex adapter, subscription login, limits, bounded execution |
| M3 | Curriculum/phonics engine and decodability validator |
| M4 | Evidence, mastery, retention, placement |
| M5 | Adventure hub and three mini-game patterns |
| M6 | Storybook, mocked creator, parent dashboard |
| M7 | Supabase/RLS, offline persistence and synchronization |
| M8 | Security/accessibility hardening and one-child pilot |

Milestones may overlap when explicit ticket dependencies permit it.

### Initial dependency-aware ticket backbone

| Ticket | Deliverable | Dependencies |
|---|---|---|
| ORCH-001 | Python skeleton and pytest | None |
| ORCH-002 | Structured task schema | ORCH-001 |
| ORCH-003 | SQLite persistence | ORCH-001 |
| ORCH-004 | Dependency graph/scheduler | ORCH-002, ORCH-003 |
| ORCH-005 | Mock executor/fault injection | ORCH-002 |
| ORCH-006 | Worktree manager | ORCH-002 |
| ORCH-007 | Verification runner | ORCH-005, ORCH-006 |
| ORCH-008 | Retry/recovery/pause | ORCH-003, ORCH-004, ORCH-007 |
| ORCH-009 | Policy/approval engine | ORCH-008 |
| ORCH-010 | Codex CLI adapter | ORCH-009 |
| GAME-001 | Next.js monorepo | None |
| GAME-002 | Curriculum schemas | GAME-001 |
| GAME-003 | Prerequisite graph validation | GAME-002 |
| GAME-004 | Phonics lexicon/word validator | GAME-002 |
| GAME-005 | Story decodability | GAME-004 |
| GAME-006 | Learning evidence/mastery | GAME-002 |
| GAME-007 | Adaptive review | GAME-006 |
| GAME-008 | Activity contracts | GAME-002, GAME-006 |
| GAME-009 | First mini-game | GAME-008 |
| GAME-010 | Phaser adventure shell | GAME-001 |
| GAME-011 | Storybook/mock generator | GAME-005 |
| GAME-012 | Supabase schema/RLS | GAME-002 |
| GAME-013 | Offline/sync | GAME-006, GAME-012 |
| GAME-014 | Parent dashboard | GAME-006, GAME-012 |
| GAME-015 | Integrated vertical slice | GAME-009, GAME-010, GAME-011 |
| GAME-016 | Security/accessibility/pilot readiness | GAME-013, GAME-014, GAME-015 |

See `agent_ticket_backlog.md` for expanded task planning. First useful orchestrator implementation after skeleton: **ORCH-002**. First real Codex-driven game task after schemas: **GAME-003**.

## 19. Risks and release gates

| Risk | Severity | Mitigation / gate |
|---|---|---|
| Unsafe child-facing AI content | Critical | Moderation, strict inputs, validation, fallback; gate live AI |
| Incorrect educational rules | High | Curriculum review and comprehensive tests; gate child pilot |
| Cross-account child exposure | Critical | RLS and auth testing; gate cloud sync |
| Codex usage/auth changes | Medium | Adapter, capability checks, pause/resume; gate real-agent execution |
| Unsafe agent commands | High | Sandbox, policy, approvals; gate unattended execution |
| Offline sync corruption | High | Idempotency, append-only evidence, recomputation; gate multi-device sync |
| Phaser accessibility gaps | High | Accessible alternatives; gate MVP |
| Inaccurate speech assessment | High | Optional fallback and child pilot; gate speech |
| Unavailable AI authorization | Medium | Mock/templates; gate live AI |
| Budget overruns | Medium | Monitoring and quotas; gate paid provider/hosting |
| Child privacy compliance | Critical | Separate privacy/legal review; gate public launch |

**Gate A: Live AI** requires supported parent authorization, moderation, quotas, validation, privacy review.  
**Gate B: Live speech** requires suitable provider, consent, accuracy pilot, audio policy.  
**Gate C: Unattended Codex** requires working subscription login, documented automation interface, sandbox, policies, usage-limit handling, recovery.  
**Gate D: Public release** requires child privacy/compliance, security, accessibility, educational review, and operations.

## 20. Deferred implementation decisions

- Exact grapheme/phoneme teaching sequence and curated lesson content.
- Final mastery/retention thresholds, calibrated from testing.
- Visual world theme, character art, and polished asset production.
- Production hosting selection.
- Supported live story AI and image providers.
- Speech provider and evaluation methodology.
- Advanced multi-agent concurrency.
- Public launch date and compliance approval.

No agent may silently resolve a deferred question that changes security, privacy, billing, or educational correctness.

## 21. Requirements traceability

| Round | Decisions | Specification focus |
|---|---:|---|
| 1 Product foundation | 5 | Audience, game goals, platforms |
| 2 Learning engine | 7 | Mastery, assessment, adaptive progression |
| 3 Voice assessment | 8 | Optional speech and fallback |
| 4 Gameplay | 10 | Hub, mini-games, rewards, accessibility |
| 5 Story creation | 12 | Structured creator, two-layer stories, safety |
| 6 Accounts/security | 12 | Parents, privacy, consent, offline |
| 7 Curriculum engine | 12 | Versioning, phonics, evidence, validation |
| 8 Architecture | 13 | Next.js, Phaser, Supabase, monorepo |
| 9 MVP/orchestration | 15 | Vertical slice, agent workflow, cost |
| 10 Acceptance | 15 | Testing, approval gates, specification readiness |
| **Total** | **109** | **All represented** |

## 22. Acceptance authority and next action

The developer is the final authority for merging, deploying, enabling paid services, security-policy changes, and public release. Agents may propose code and evidence, not redefine acceptance criteria or bypass controls.

**Next action:** Expand the ticket backbone into machine-readable, dependency-aware task contracts and implement ORCH-001 followed by ORCH-002. The first meaningful demonstration is one safely bounded agent delivering one automatically verifiable feature. The orchestrator then becomes the delivery engine for Reading Adventure.