---
name: validate-plan
description: Adversarially validate a freshly-authored plan before implementation — challenge it against the codebase and its own coherence, then apply the real findings by editing the plan in place. Use between create-plan and tdd-plan (or implement-plan) when the user says "validate the plan" or "sanity-check the plan". (Post-implementation hardening of the branch is review-plan, not this.)
argument-hint: [<plan-slug>]
---

# Validate Plan

Run an adversarial review on a plan **before** any code is written: have Codex challenge the plan, triage its findings, apply the real ones by editing the plan in place, and produce a `VALIDATION.md` summary that `create-pr` later pastes into the PR description alongside `REVIEW.md`.

This is the pre-implementation counterpart to `review-plan`. The key inversion: here the plan dir **is** the edit target, whereas `review-plan` is forbidden from touching it.

**Read `~/.claude/skills/shared/adversarial-rounds.md` before Phase 3.** It defines the round/triage protocol shared with `review-plan` — verbatim round capture, triage-as-contract, borderline-to-user, rounds 2–3 escalation, the 3-round cap, the Codex-unavailable fallback, and the summary-file shape. This skill adds only what is validation-specific.

## Arguments

A single optional positional `<plan-slug>`. If omitted, the slug is inferred from the unique plan whose `Status:` is `draft` or `ready`. If zero or more than one match, the script exits 1 asking for an explicit slug.

## Workflow

### Phase 1 — Resolve context

```bash
python3 ~/.claude/skills/validate-plan/scripts/resolve_plan.py [<slug>]
```

Prints, parseable as `key=value`: `slug=`, `plan_dir=`, `status=<draft|ready>`.

Then **read the plan dir in full** — `PLAN.md`, `RESEARCH.md` if present, `DECISIONS.md` if present, every file in `tasks/`. Triage needs the Decisions in particular, so Codex challenges that contradict an explicit Decision can be rejected.

### Phase 2 — Preconditions

```bash
bash ~/.claude/skills/validate-plan/scripts/check_preconditions.sh <slug>
```

Refuses with a clear reason and exit 1 if any of these fail:

- `PLAN.md` is missing
- `Status:` is `tests-ready`, `in-progress` or `done` (tests or code already build on the plan; use `review-plan` for a post-implementation pass)
- Working tree has changes **outside** `docs/artifacts/plans/<slug>/` (so applied edits stay cleanly attributable to validation). The plan dir itself is allowed to be dirty — typically it's freshly created and untracked, or edited between rounds.

On success, exits 0 silently. Then create the validation dir:

```bash
mkdir -p docs/artifacts/plans/<slug>/validation
```

### Phase 3 — Round 1

Run the round per the shared protocol, recording to `validation/round-1.md` from `references/round.md.tmpl`. Focus text:

```
/codex-local:adversarial-review --wait --scope working-tree Validate a plan, not a code change. The untracked work in this working tree is docs/artifacts/plans/<slug>/ — PLAN.md, RESEARCH.md (if present), DECISIONS.md (if present), and every file in tasks/. Read them in full, then read the referenced source files to ground your critique in current code.

Challenge the plan along two axes:
1. Vs. the codebase — are referenced file paths and symbols real and current? Do "follow existing pattern X" claims hold today? Has the code drifted since the planner's exploration?
2. Internal coherence — task dependencies sane? Acceptance criteria observable — each provable by a non-vacuous automated test or by named Evidence? Decisions consistent with the stated constraints? Risks have mitigations? Does the final-validation task cover every Acceptance Criterion in PLAN.md?

For each finding propose a verdict (apply/defer/reject) with a one-line rationale and — for apply — name the plan file(s) that would change.
```

### Phase 4 — Triage

Verdicts for this skill (`apply` is the action verb):

| Verdict | When to use |
|---|---|
| `apply` | Real plan defect — wrong file path, missing task or dependency, untestable acceptance, missing risk, scope gap |
| `defer` | Has merit but out of scope for this plan — record as known limitation or as a follow-up plan |
| `reject` | Contradicts an explicit Decision in `PLAN.md`/`DECISIONS.md`, or is taste/speculative/incorrect |

Triage per the shared protocol, plus two rules unique to validation:

- **"Vs. the request" check.** Codex can't see the original conversation that produced this plan. Before finalising the table, surface to the user via `AskUserQuestion` any finding that *could* indicate the plan misses what they asked for — whatever its verdict. Only the user can make that call.
- **Ungrounded `apply` findings → ask.** If applying a finding requires referencing a file or symbol Codex didn't ground in real code (you can't verify it exists by reading the repo), surface it to the user. A hallucinated structure baked into the plan is worse than an unapplied valid finding.

Table shape for `round-1.md`'s `## Triage`:

```
| # | Finding | Severity | Verdict | Rationale | Applied to |
|---|---------|----------|---------|-----------|------------|
| 1 | <one-line summary> | high/med/low | apply/defer/reject | <one sentence> | <plan-file:section or TASK-NNN or +TASK-NNN> |
```

### Phase 5 — Apply loop

For each `apply` row, in table order, make the edit and record the location(s) in `Applied to` (e.g. `PLAN.md:Risks`, `TASK-003`, `+TASK-007`, `DECISIONS.md`). Typical patterns:

- **`PLAN.md`** — add or fix a Risk, expand Out-of-Scope, fix an Acceptance Criterion, correct a Decision summary.
- **`tasks/TASK-NNN-…md`** — fix a file path, add an acceptance check, add a missing dependency, clarify Steps.
- **New task** — invoke `create-plan`'s helper to assign the next sequential id and stamp out the file:
  ```bash
  python3 ~/.claude/skills/create-plan/scripts/add_task.py <slug> \
    --type <impl|checklist> --title "<task title>" [--depends TASK-NNN,...]
  ```
  If the final-validation task already exists, the new task lands *before* it numerically — that's expected. Renumbering is not supported and not needed; execution order is the `## Tasks` checkbox order in `PLAN.md`.
- **`DECISIONS.md`** — record a decision that emerged from the challenge. Create it from `create-plan`'s `references/template-decisions.md` if absent, and link it from `PLAN.md`'s `## Decisions` section.
- **Final-validation task** — if an `apply` adds or changes an Acceptance Criterion in `PLAN.md`, edit the final-validation task's Steps so its coverage stays complete.

**No git commits.** There's no branch yet — edits stay in the working tree, and the branch's first `chore: add plan for <slug>` commit (cut by `tdd-plan`, or `implement-plan` when tests are skipped) captures the validated state.

### Phases 6–7 — Rounds 2 and 3

Per the shared protocol. Round-2 focus text:

```
/codex-local:adversarial-review --wait --scope working-tree Second pass over the plan. Round-1 findings and triage are in docs/artifacts/plans/<slug>/validation/round-1.md (Codex output verbatim followed by a triage table marking each item apply/defer/reject with rationale and where it landed in the plan). Verify the applied edits are sufficient, push back on any defer or reject rationale you disagree with, and surface anything new — especially issues the plan edits themselves introduced (e.g. a new task creating a dependency cycle, an edited acceptance criterion no longer covered by the final-validation task).
```

Round-3 focus text (only if round 2 produced `apply` rows) references both prior round files the same way. If round 3 *still* produces `apply` rows, stop and ask the user — three rounds of real plan defects signals the plan needs a rewrite (`create-plan`), not more patching.

### Phase 8 — Write VALIDATION.md

Compose `docs/artifacts/plans/<slug>/VALIDATION.md` from `references/VALIDATION.md.tmpl`, per the shared summary-file rules (rounds with verdict counts; applies with locations; defers and rejects with rationale).

**File the defers in Linear (only if wired — see `~/.claude/skills/shared/linear-integration.md`).** Defers must not evaporate into a markdown file: for each `defer`, create a backlog issue via `mcp__linear-server__save_issue` — `title` = the finding one-liner, `description` = rationale + a link line `From validation of docs/artifacts/plans/<slug>` , same `project` as the epic when linked, state Backlog, always the `code-review` label (Source group) plus any other existing labels that fit — never create labels. Note each created id in VALIDATION.md next to its defer. Skip duplicates: search existing issues by title first. While there, check the phase sub-issue itself (the id in `PLAN.md`'s `Linear:` field, when not `none`): if it is not yet in **Todo** (or further along), move it there via `mcp__linear-server__save_issue` — a validated plan must not sit in Backlog.

**No commit** — same reason as Phase 5; it lands in the branch's first plan-commit.

### Phase 9 — Report

```
Plan validation complete: <N> rounds, <M> applied, <K> deferred, <J> rejected. Ready for /tdd-plan (or /implement-plan when the plan skips tests-first).
```

## Behaviour Constraints

- **The plan dir IS the edit target.** This is the inversion vs. `review-plan`. Validation's whole job is to improve the plan in place.
- **No git commits during validation.** No branch exists yet. Do not invoke `create-commit` from this skill.
- **Don't touch `Status:`.** Leave it as found (`draft` or `ready`); `tdd-plan` and `implement-plan` advance it later. There is no `validated` status value.
- **Use `create-plan`'s `add_task.py` for new tasks.** Never invent `TASK-NNN` ids manually.
- **Don't loosen the final-validation task without re-checking acceptance coverage.** If an `apply` adds or changes an Acceptance Criterion, the final-validation task's Steps must still cover every criterion.

## Directory Layout

After running, the plan directory looks like:

```
docs/artifacts/plans/<slug>/
  PLAN.md              # possibly edited
  RESEARCH.md          # possibly edited (if it existed before)
  DECISIONS.md         # possibly edited or newly created
  tasks/               # possibly edited / extended
  validation/
    round-1.md         # Codex verbatim + triage table
    round-2.md
    round-3.md         # only if needed
  VALIDATION.md        # paste-ready summary, parallels REVIEW.md
```
