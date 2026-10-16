---
name: pstack-budget
description: Use for orchestrator implementation, debugging, and review with a subscription-conscious adaptation of pstack. Keep one agent, narrow context, and direct verification by default.
---

# Subscription-conscious engineering

This is a project-local adaptation, not the full Cursor pstack plugin. Read
`docs/pstack-workflow.md` only when selecting a different profile or updating this
skill. Follow AGENTS.md and the scoped ticket. Existing approval gates remain in force.

## Default loop

1. Name the ticket, observable acceptance criteria, relevant data shape, and smallest
   useful change. Use one working agent. Do not start panels, races, swarms, or
   competing implementations by default.
2. Read required repository instructions, then search for relevant symbols and read
   bounded sections. Do not reread whole specifications or dump directories/logs
   into context. Preserve mandatory task instructions even when they are lengthy.
3. Implement one verifiable unit at a time. Prefer existing structures and stdlib.
   Add behavior tests that fail when the contract breaks; avoid tests tied to private
   call order or redundant scaffolding.
4. Run targeted tests while editing. Before delivery, run the ticket's required
   checks and inspect the actual diff. Compilation alone is not functional evidence.
   Repeat checks only after changes or a new failure diagnosis warrants it.
5. On failure, capture the command, exit status, and relevant error excerpt. Test a
   concrete diagnosis. After two unsuccessful repair attempts for the same failure,
   pause that loop and report evidence and the unresolved premise; continue useful
   independent checks. Never silently expand retries or reduce acceptance criteria.
6. Report behavior changed, checks and counts, remaining limitations, and next step
   concisely. Record a short handoff only when pausing: ticket, branch/commit, changed
   files, commands/results, failure diagnosis, and next action. Never include secrets.

## Budget decisions

- Keep the current subscription-authenticated model. Do not assume model switching,
  Cursor model aliases, or reasoning settings are available in this host.
- Where the UI supports it, prefer low reasoning for mechanical edits and medium
  for routine tickets. Reserve higher reasoning for demonstrated design uncertainty,
  concurrency, or subtle defects. These are user-selectable preferences, not settings
  this Markdown file can enforce.
- Do not delegate just to shrink the main context: duplicated prompts and replies
  can increase total usage. If the user requests a second opinion, use at most one
  focused reviewer with file pointers, a small diff, and concrete questions. Do not
  fork the full conversation unless the review needs it. Respect host delegation rules.
- Never claim a token saving percentage without measurements. Count agent calls,
  attempts, and checks when useful; token/usage/cost telemetry is unknown when absent.
- On a provider usage limit, pause and save a compact handoff. Do not retry repeatedly,
  switch to a billed API, buy credits, or assume when the allowance resets.

## Provenance

Adapted from cursor/plugins pstack principles: Laziness Protocol (small changes),
Guard the Context Window (bounded scope), Prove It Works (direct evidence), and
Test Behavior, Not Implementation (observable contracts). See
`docs/pstack-workflow.md` for upstream links and deliberate deviations. No upstream
scripts or automation are executed by this skill.
