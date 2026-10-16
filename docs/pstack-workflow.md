# pstack workflow within a subscription budget

Use the local [pstack-budget skill](../.agents/skills/pstack-budget/SKILL.md) for
coding and review. In hosts that discover `.agents/skills`, invoke `$pstack-budget`.
Otherwise read that file explicitly; AGENTS.md points agents to it. This integrates
selected pstack practices into agent instructions. It does not install Cursor's
plugin, change account billing, or implement runtime budget enforcement.

## Options

| Profile | Agent work | When to use |
| --- | --- | --- |
| Lean (default) | One agent; targeted reads; behavioral tests; self-review of diff | Routine scoped tickets, fixes, docs |
| Focused review (explicit request) | Lean plus one reviewer on a specific risk | Subtle algorithm or cross-module change |
| Broad exploration (separate explicit request) | Agree a bounded scope and call limit first | Unresolved architecture with evidence that one approach is insufficient |

Start with Lean. A reviewer adds usage; an inherited model or `auto` does not make
an extra agent free. Avoid pstack's default architect/arena/interrogate panels,
parallel implementation races, persistent orchestration, and unattended retry loops.
Do not automatically escalate profiles. A routine bug still needs a reproducer;
saving tokens does not justify skipping required verification or human review.

If reasoning controls exist in the current product, choose low for mechanical work,
medium for ordinary implementation, and higher effort only for demonstrated hard
reasoning. The local skill cannot set these controls. Do not copy Cursor-specific
model slugs into Codex or assume another model is included in the subscription.

## Context and verification

Give each ticket a small acceptance contract. Read required instructions, then use
symbol searches and relevant file sections. Save full logs outside the prompt and
read failure excerpts with exit status. Use targeted checks during iteration and
run all ticket-required checks before delivery. Keep a compact handoff for a new
session instead of replaying transcripts. Do not omit necessary safety constraints,
acceptance details, or failure evidence to meet an arbitrary prompt size.

The two-attempt repair-loop limit in the skill is a workflow stop condition, not a
provider-enforced quota. Existing task timeout/retry limits still apply when stricter.
A later runtime implementation belongs with ORCH-008 (retries), ORCH-009 (policy),
ORCH-010 (subscription adapter), and ORCH-012 (observed usage reporting). No real
executor or billing integration is enabled here.

## What the $20 plan means

Subscription price is not a fixed token allowance. Available usage can depend on
model, task size, product, and current plan limits. No saving percentage or guaranteed
number of tickets is promised. Consult the account's usage UI; if telemetry is not
exposed, report it as unknown. Pause on limits, keep a handoff, and resume when access
is available. Never fall back to API billing or purchase additional usage automatically.

## Upstream and deviations

Reviewed from [cursor/plugins pstack](https://github.com/cursor/plugins/tree/main/pstack)
on 2026-10-16. Upstream evolves; this is an independently maintained adaptation,
not a vendored copy or a promise of full pstack compatibility.

- [Laziness Protocol](https://github.com/cursor/plugins/blob/main/pstack/skills/principle-laziness-protocol/SKILL.md): smallest change and one source of truth.
- [Guard the Context Window](https://github.com/cursor/plugins/blob/main/pstack/skills/principle-guard-the-context-window/SKILL.md): bounded scope; this adaptation avoids automatic delegation because total usage matters too.
- [Prove It Works](https://github.com/cursor/plugins/blob/main/pstack/skills/principle-prove-it-works/SKILL.md): verify the actual artifact.
- [Test Behavior, Not Implementation](https://github.com/cursor/plugins/blob/main/pstack/skills/principle-test-behavior-not-implementation/SKILL.md): tests assert observable contracts.
- [setup-pstack](https://github.com/cursor/plugins/blob/main/pstack/skills/setup-pstack/SKILL.md): its small reasoning setting reduces effort, but panel sizes still multiply calls. This adaptation uses one agent by default instead.

Full poteto-mode also routes many tasks through additional skills, model panels,
and Cursor tooling. Those triggers are not imported. Automated shipping, broad
autonomy, external messaging, and upstream model defaults are not enabled. Existing
repository approvals, subscription-only constraints, and the no-auto-merge rule
continue to govern all work.
