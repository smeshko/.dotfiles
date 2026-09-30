---
name: review-plan
description: Adversarial review of a completed plan's branch before opening a PR — triage Codex findings, fix the real bugs as separate commits, re-run to confirm. Use between implement-plan and create-pr when the user says "review the branch", "harden this before the PR", or wants an adversarial pass over the implementation. (Pre-implementation validation of the plan text is validate-plan, not this.)
argument-hint: [<plan-slug>]
---

# Review Plan

Run an adversarial review on a completed plan's branch, fix the real findings, and produce a `REVIEW.md` summary that `create-pr` pastes into the PR description.

This is the post-implementation counterpart to `validate-plan`. The key inversion: here the **code** is the edit target, and the plan dir is immutable.

**Read `~/.claude/skills/shared/adversarial-rounds.md` before Phase 3.** It defines the round/triage protocol shared with `validate-plan` — verbatim round capture, triage-as-contract, borderline-to-user, rounds 2–3 escalation, the 3-round cap, the Codex-unavailable fallback, and the summary-file shape. This skill adds only what is review-specific.

## Arguments

A single optional positional `<plan-slug>`. If omitted, the slug is inferred from the current branch by matching `Branch:` in each plan's `PLAN.md` — the same logic `archive-plan` uses.

## Workflow

### Phase 1 — Resolve context

```bash
python3 ~/.claude/skills/review-plan/scripts/resolve_plan.py [<slug>]
```

Prints, parseable as `key=value`: `slug=`, `plan_dir=`, `branch=<branch-from-PLAN.md>`, `base=<base-branch-from-origin/HEAD>` (or `(unknown)`).

Then **read `PLAN.md` end-to-end** — Goal, Scope, Decisions in particular. Triage needs this to reject Codex challenges that contradict an explicit Decision.

### Phase 2 — Preconditions

```bash
bash ~/.claude/skills/review-plan/scripts/check_preconditions.sh <slug>
```

Refuses with a clear reason and exit 1 if any of these fail:

- Working tree dirty (fixes must land in their own commits, not mixed with stray edits)
- `Status:` in `PLAN.md` is not `done`
- `Branch:` in `PLAN.md` does not match the current branch
- Any task checkbox in `## Tasks` is unchecked
- Current branch is `staging` or `main`/`master`

On success, exits 0 silently. Then create the reviews dir:

```bash
mkdir -p docs/artifacts/plans/<slug>/reviews
```

**Linear (only if wired — see `~/.claude/skills/shared/linear-integration.md`):** move the phase sub-issue (the id in `PLAN.md`'s `Linear:` field, when not `none`) to **In Review** via `mcp__linear-server__save_issue`, so the board shows the phase under review rather than still In Progress. Skip if the team has no In Review state.

### Phase 3 — Round 1

Run the round per the shared protocol, recording to `reviews/round-1.md` from `references/round.md.tmpl`:

```
/codex-local:adversarial-review --wait --scope branch --base <base> Besides bugs, hunt for production code shaped to its tests rather than to the behaviour — special-cased test inputs, hardcoded expected values — and for test changes that weaken an assertion, including `test(...): amend` commits.
```

### Phase 4 — Triage

Verdicts for this skill (`fix` is the action verb):

| Verdict | When to use |
|---|---|
| `fix` | Real bug — correctness, regression, security, performance cliff, missing edge case |
| `defer` | Has merit but out of scope for this branch — file as a follow-up |
| `reject` | Contradicts an explicit Decision in `PLAN.md`, or is taste/speculative/incorrect |

Triage per the shared protocol. Table shape for `round-1.md`'s `## Triage`:

```
| # | Finding | Severity | Verdict | Rationale | Commit |
|---|---------|----------|---------|-----------|--------|
| 1 | <one-line summary> | high/med/low | fix/defer/reject | <one sentence> | <sha> |
```

### Phase 5 — Fix loop

For each `fix` row, in order:

1. Make the change.
2. Stage only the files this fix touches: `git add <paths>` — never `git add -A`.
3. Invoke the `create-commit` skill. Commit subject should reference the finding briefly, e.g. `fix(<scope>): handle null cursor in pagination (review #1.3)`.
4. Run the project's fast feedback check if `AGENTS.md` or `CLAUDE.md` defines one (lint + typecheck minimum; fast unit tests if quick). Skip slow integration suites — round 2 plus CI cover those.
5. Record the resulting commit SHA in the `Commit` column of `round-1.md`'s triage table.

### Phases 6–7 — Rounds 2 and 3

Per the shared protocol. Round-2 focus text:

```
/codex-local:adversarial-review --wait --scope branch --base <base> Second pass. Round-1 findings and triage are in docs/artifacts/plans/<slug>/reviews/round-1.md (Codex's verbatim output followed by a triage table marking each item fix/defer/reject with rationale and the fix commit SHA). Verify the fixes are sufficient, push back on any deferral or rejection rationale you disagree with, and surface anything new — especially regressions introduced by the fixes themselves.
```

Round-3 focus text (only if round 2 produced `fix` rows) references both prior round files the same way. If round 3 *still* produces `fix` rows, stop and ask the user — three rounds with real bugs each signals deeper trouble (a brittle area, missing test coverage, wrong abstraction), not something to grind out.

### Phase 8 — Write REVIEW.md

Compose `docs/artifacts/plans/<slug>/REVIEW.md` from `references/REVIEW.md.tmpl`, per the shared summary-file rules (rounds with verdict counts; fixes with commit SHAs; defers and rejects with rationale).

**File the defers in Linear (only if wired — see `~/.claude/skills/shared/linear-integration.md`).** Defers must not evaporate into a PR-body line: for each `defer`, create a backlog issue via `mcp__linear-server__save_issue` — `title` = the finding one-liner, `description` = rationale + `From review of docs/artifacts/plans/<slug> (branch <branch>)`, same `project` as the epic when linked, state Backlog, always the `code-review` label (Source group) plus any other existing labels that fit — never create labels. Note each created id in REVIEW.md next to its defer. Skip duplicates: search existing issues by title first.

Commit the new `reviews/` files and `REVIEW.md` via `create-commit` with subject `chore(<slug>): record adversarial review`. Stage explicitly: `git add docs/artifacts/plans/<slug>/reviews docs/artifacts/plans/<slug>/REVIEW.md`.

### Phase 9 — Report

```
Review complete: <N> rounds, <M> fixes (<sha-range>), <K> deferred, <J> rejected. Ready for /create-pr.
```

## Behaviour Constraints

- **One commit per logical fix.** Same discipline as `implement-plan`. Don't batch unrelated fixes; don't split one fix across commits.
- **A fix that edits a test is a test amendment.** The user approves it first, and it lands as its own `test(<scope>): amend …` commit — `check_tests.py` rejects any other test edit on a TDD plan.
- **Stage explicitly.** `git add <paths>` only — never `git add -A`/`.`. Fixes must not pick up unrelated working-tree state.
- **Don't amend task commits.** Review fixes are new commits on top of the plan's task commits, not edits to them. Preserves the plan↔commit mapping for PR review.
- **Don't touch `PLAN.md`, `RESEARCH.md`, `DECISIONS.md`, or task files.** Review artifacts live in `reviews/` and `REVIEW.md`. The plan record is immutable from here on.
- **Don't run slow suites between fixes.** Lint + typecheck + fast unit tests max. Round 2 and CI cover integration.

## Directory Layout

After running, the plan directory looks like:

```
docs/artifacts/plans/<slug>/
  PLAN.md
  RESEARCH.md          # if it existed before
  DECISIONS.md         # if it existed before
  tasks/
  reviews/
    round-1.md         # Codex verbatim + triage table
    round-2.md
    round-3.md         # only if needed
  REVIEW.md            # summary, paste-ready for PR description
```
