# Adversarial round protocol — shared reference

The round/triage machinery shared by `validate-plan` (pre-implementation; the plan is the edit target) and `review-plan` (post-implementation; the code is the edit target). Each skill defines its own **action verb** (`apply` / `fix`), **edit targets**, **preconditions**, and **round focus text**; everything below is common to both. "Action row" below means a finding triaged with that skill's action verb, as opposed to `defer` / `reject`.

## Depth by risk

Read `Risk:` from `PLAN.md` before round 1 and spend review effort accordingly — don't pay three Codex rounds for a two-file change, and don't give a `high` plan a single pass:

| Plan risk | Round 1 reviewer(s) | Max rounds |
|---|---|---|
| `tiny` / `small` | one clean `general-purpose` subagent with the adversarial framing (skip Codex — save its quota) | 2 |
| `medium` | Codex (current default) | 3 |
| `large` / `high` | Codex **and** an independent subagent lens in parallel; merge and dedupe findings before triage | 3 |

Rounds 2+ always use a single reviewer (Codex when available). Record which reviewer ran in each round header.

## Running a round

1. Invoke `/codex-local:adversarial-review --wait <scope flags> <focus text>` in the foreground so the verbatim output flows back into the conversation. The focus text comes from the calling skill's phase.
2. Write `round-<N>.md` in the skill's round directory from its `references/round.md.tmpl`: header filled in, Codex output pasted **verbatim** under `## Codex output`, `## Triage` left empty for now.
3. **Review-only inside a round.** No edits while a round runs — the slash command is review-only by its own rules. Edits happen only in the skill's action loop.

**Codex unavailable** (plugin missing, or usage-limited): run the round with a clean `general-purpose` subagent given the same adversarial framing and focus text, record it identically, and note `reviewer: subagent` in the round header.

## Triage — a contract, not a note

Classify **every** finding before acting on any of them — severity and scope calls are clearer after reading the full round. The triage table is read by the next round of Codex, so it must be complete and in the skill's prescribed column shape.

- Borderline calls — a genuine design challenge with real merit — go to the user via `AskUserQuestion` (options: act now / defer / reject). Don't decide silently on judgement calls the user might want input on.
- `reject` needs grounding: it contradicts an explicit Decision in `PLAN.md`/`DECISIONS.md`, or the finding is demonstrably incorrect or pure taste.
- Fill the action column (`Applied to` / `Commit`) during the action loop, not during triage.
- If acting on a finding reveals it was deeper than expected, stop and reclassify the row with a note — don't silently expand scope.

## Rounds 2 and 3

Each subsequent round's focus text must reference the prior round file(s) by path — the diff alone is lossy; Codex needs the original framing and the triage verdicts to judge whether deferrals were reasonable. Ask it to: verify the actions taken are sufficient, push back on any defer/reject rationale it disagrees with, and surface anything new — especially problems the actions themselves introduced.

- Round 2 yields only `defer`/`reject` → done; write the summary file.
- Round 2 yields action rows → run the action loop, then round 3 with both prior rounds in focus.
- Round 3 still yields action rows → **stop and ask the user**. Three rounds of real findings is a structural signal, not something to grind out — offer act-and-stop, act-and-continue, or stepping back to the authoring skill. Never auto-run a fourth round.

## The summary file

Compose the skill's summary (`VALIDATION.md` / `REVIEW.md`) from its template: rounds run with per-round verdict counts, then every finding grouped by verdict — actions with where they landed, defers with rationale (these become known-limitation / follow-up hints in the PR body), rejects with rationale (so PR reviewers see what Codex pushed on and why we said no). `create-pr` pastes this file into the PR description; `archive-plan` carries it into the plan archive.
