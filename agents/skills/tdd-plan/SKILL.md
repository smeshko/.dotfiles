---
name: tdd-plan
description: Write a plan's tests before implementation — tight, non-vacuous tests proven red against stubs, committed as pending on the plan's branch, then a draft PR opened for review. Use between validate-plan and implement-plan when the user says "tdd the plan", "write the tests first", or names tdd-plan.
argument-hint: [<plan-slug>]
---

# TDD Plan

Write every test a plan needs before any implementation exists. The tests land on the plan's branch **red-proven** and **pending**: each carries one **sticker** line that keeps it skipped until its task starts. A draft PR then opens so the user reviews the tests while `implement-plan` runs. From here the committed tests are the contract — `implement-plan` strips a task's stickers and makes its tests pass through production code, and `check_tests.py` holds every later commit to that.

Every test is **non-vacuous** and **tight**, as `~/.claude/skills/shared/non-vacuous-tests.md` defines them.

## Step 1: Resolve the plan

```bash
python3 ~/.claude/skills/validate-plan/scripts/resolve_plan.py [<slug>]
```

Prints `slug=`, `plan_dir=`, `status=`. The status must be `draft` or `ready`; `tests-ready` or later means the tests already exist — stop and say so.

Read the plan dir in full: `PLAN.md`, `RESEARCH.md` and `DECISIONS.md` if present, every task file. Find the test command in `AGENTS.md`/`CLAUDE.md`. Where the project cannot build or run tests locally (CI is the only test gate), read `references/ci-gated.md` now — it reorders Steps 5–8.

Done when: the plan is read, it has at least one `impl` task (none → nothing to test; hand off to `implement-plan`), and the test command is known.

## Step 2: Cut the branch

Follow `~/.claude/skills/shared/plan-branch.md`.

Done when: its completion line holds.

## Step 3: Design the tests

Read `~/.claude/skills/shared/non-vacuous-tests.md` now. Then, for each `impl` task, map every Acceptance criterion to the fewest non-vacuous tests that prove it:

- A behaviour → tests named for the behaviour, each asserting an exact value.
- A behaviour change existing tests already cover → those tests, updated to the new expectation.
- A task that changes no behaviour (a pure refactor) → no new tests; the existing suite staying green proves it.
- A criterion only a screenshot, log or manual check can prove → no test; it stays Evidence for `implement-plan`.

Before writing, read `references/jev-review.md` and follow its advisory review: give each proposed test a concrete regression witness, check that the witness violates its criterion, then check whether the test would catch it. Compare competing tests across the retained suite. The agent resolves findings and owns selection; record the disposition or explicit manual fallback in the plan's `tdd/jev-review.md`.

Done when: every Acceptance criterion of every `impl` task maps to named tests, or to Evidence or none with a one-line reason; every proposed test has a reviewed witness and disposition, and every removed test names the retained coverage.

## Step 4: Write stubs and tests

- **Stubs** — every new symbol the tests call, with its final signature and a body returning a *wrong* value of the right type, chosen so every test fails on its assertion: a filter stub returns its input unfiltered, a sort stub returns its input unsorted. Existing symbols keep their current behaviour — for a changed behaviour, the current one is the wrong value.
- **Tests** — in the repo's existing test layout and style. Every new or changed test gets one sticker for its task, in the form `references/stickers.md` gives for the stack.

Reconcile the actual tests with the reviewed designs using `references/jev-review.md`: repeat mechanics checks for material differences or unresolved concerns, and update `tdd/jev-review.md`. Review the runnable body without its pending sticker; the existing stub is not the hypothetical regression.

Done when: the test target builds and every new or changed test matches its recorded review disposition.

## Step 5: Prove the stickers hold

Run the full suite.

Done when: it is green, with every stickered test reported as skipped.

## Step 6: Prove red

Stage the test files (`git add <paths>`) so the index holds the stickered version, then strip every sticker from the working tree and run the new tests:

```bash
python3 ~/.claude/skills/tdd-plan/scripts/strip_stickers.py
```

Every test must fail **on its assertion**. A compile error, a crash, or a test missing from the output means the test or its sticker is broken. A test that passes against the stubs has not proved red — inspect the assertion and the stub's relevance to its regression witness, sharpen the test or correct the stub, then return to Step 5. Failing against a stub proves sensitivity to that stub, not adequacy against every relevant regression; Jev's predictions do not waive this execution check.

Save the failures — test name plus assertion message, grouped by task — to `docs/artifacts/plans/<slug>/tdd/red.txt`, then restore the stickers from the index:

```bash
git checkout -- <test paths>
```

Done when: every stickered test failed on its assertion, `tdd/red.txt` records each one, and `git diff -- <test paths>` is empty.

## Step 7: Commit and record

Commit via `create-commit`, staging explicitly:

1. The stubs (skip when there are none): `chore(<scope>): add stubs for <slug>`.
2. The tests, fixtures and test config — nothing else: `test(<scope>): add pending tests for <slug>`. This is the **tests commit**.

Record it as the baseline and advance the status:

```bash
python3 ~/.claude/skills/tdd-plan/scripts/set_tests_commit.py <slug> $(git rev-parse HEAD)
python3 ~/.claude/skills/implement-plan/scripts/set_plan_status.py <slug> tests-ready
```

Append a `## Tests` section to each `impl` task file: its test files, its test names, `tdd/jev-review.md` as the design-review record, and `tdd/red.txt` as the red evidence — or `None — <reason>` from Step 3. Commit the plan dir via `create-commit` as `chore: record tests for <slug>`, then confirm the baseline:

```bash
python3 ~/.claude/skills/tdd-plan/scripts/check_tests.py <slug>
```

Done when: `check_tests.py` prints `violations=0` and `git status --porcelain` is empty.

## Step 8: Open the draft PR

```bash
git push -u origin <branch>
gh pr create --draft --title "<plan title>" --body "<body>"
```

The body says the PR carries the plan's tests for review, lists them per task, and notes that the implementation arrives when `ship-plan` pushes it. Leave out any `Closes <ID>` line — `create-pr` adds it when readying the PR.

Done when: `gh pr create` printed the draft PR's URL.

## Step 9: Report

```
Tests written for '<slug>': <N> tests across <M> tasks, red-proven and pending.
Review:     <draft PR URL>   (comment on the PR; implement-plan picks comments up)
Implement:  implement-plan <slug>
```

## Rules

- **Tight over many.** Every test proves one Acceptance behaviour; a test repeating another's proof is cut.
- **Stubs are signatures plus a wrong return value.** The logic is `implement-plan`'s.
- **One sticker per test, one task per sticker.** `implement-plan` strips them task by task.
- **Stage explicitly.** `git add <paths>` only.
