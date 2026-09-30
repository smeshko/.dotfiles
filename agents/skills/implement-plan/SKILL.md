---
name: implement-plan
description: Execute a plan produced by create-plan end-to-end — walk its tasks in order, one commit per task, ticking PLAN.md checkboxes as it goes. Use when the user asks to "implement the plan", "work through the tasks", or "execute <plan-name>". Skip if no such plan exists yet — run create-plan first.
argument-hint: <plan-slug | task-id | path-to-PLAN.md-or-task-file>
---

# Implement Plan

Drive a plan created by `create-plan` to completion. Walk its tasks in order, implement each one, tick its checkbox in `PLAN.md`, invoke `create-commit`, and move on. Stop only on hard failures or after the final-validation task. Commits stay local — `create-pr` pushes them at ship time.

A plan that went through `tdd-plan` (a **TDD plan** — `PLAN.md` carries a `Tests-commit:`) arrives with its tests already written, red-proven and pending on the plan's branch. Its committed tests are the contract: each task strips its own stickers and makes those tests pass through production code.

## Task tracking: two layers, kept in sync

Task state lives in **two places**:

1. **The plan files** (`PLAN.md` checkboxes, plan `Status:`) — the persistent source of truth, committed to git, updated only via the scripts (`mark_task_done.py`, `set_plan_status.py`).
2. **The harness task tracker** — whatever live todo/task tools this session provides (e.g. `TaskCreate`/`TaskUpdate`, or `TodoWrite` in older harnesses) — an ephemeral in-session mirror that gives the user real-time visibility.

The sync rule, stated once: **every file-state change flips the matching tracker entry in the same step; exactly one tracker entry is in-progress at a time; on any disagreement the files win** — re-seed the tracker from `list_tasks.py`. Steps below marked *(sync)* are where this happens.

## Arguments

A single freeform argument — required. The user may pass any of:

- a plan slug (e.g. `add-departure-filters`)
- a fragment of a slug or title (e.g. `departure`)
- a path to a `PLAN.md` (e.g. `docs/artifacts/plans/add-departure-filters/PLAN.md`)
- a path to a task file (e.g. `docs/artifacts/plans/add-departure-filters/tasks/TASK-002-...md`)
- a bare task id (e.g. `TASK-002`) — only unambiguous if exactly one in-progress plan exists

Resolve it to a concrete `<slug>` in Phase 1.

## Workflow

### Phase 1 — Resolve the plan

1. List all plans:
   ```bash
   python3 ~/.claude/skills/implement-plan/scripts/list_plans.py
   ```
   Each line: `<slug>\t<status>\t<title>`.
2. Match the user's input against this list:
   - If the input is a path, extract the segment after `docs/artifacts/plans/` as the slug.
   - If the input equals a slug, use it.
   - Otherwise, match the input case-insensitively as a substring against slug **and** title.
   - If the input is a bare `TASK-NNN`, the slug must be inferred from the active plan; if more than one plan has status `ready`, `tests-ready` or `in-progress`, ask the user to disambiguate before continuing.
3. If 0 matches → tell the user no plan was found and stop.
4. If >1 matches → ask the user to choose between the matches via `AskUserQuestion`.
5. Read `PLAN.md` end-to-end so you understand Goal, Scope, Acceptance Criteria, and Decisions. Read `RESEARCH.md` and `DECISIONS.md` if present. On a TDD plan, also read `tdd/red.txt` — the red proof each task's RED step reproduces.

### Phase 2 — Prepare the branch

Branch by the plan's `Status:`:

- **`tests-ready`** — `tdd-plan` cut the branch, committed the tests and opened the draft PR. `git switch <branch>` to the branch `PLAN.md`'s `Branch:` names, if not already on it.
- **`in-progress`, on the branch `Branch:` names** — a re-entry; branch and status are already in place.
- **`draft` or `ready`** — no tests exist yet. On a `medium`, `large` or `high` risk plan, ask via `AskUserQuestion` whether to run `tdd-plan` first (recommended) or implement without it; on `tdd-plan`, hand off and stop. Otherwise cut the branch per `~/.claude/skills/shared/plan-branch.md`.

Unless re-entering, set the status to `in-progress` — the flip lands in the next task's commit:

```bash
python3 ~/.claude/skills/implement-plan/scripts/set_plan_status.py <slug> in-progress
```

On a TDD plan, now settle the draft PR's test comments (see "Test review comments" below).

Done when: the current branch is `PLAN.md`'s `Branch:`, `Status:` reads `in-progress`, and on a TDD plan every test comment is settled.

### Phase 3 — Walk the task list

1. List tasks with their checkbox state:
   ```bash
   python3 ~/.claude/skills/implement-plan/scripts/list_tasks.py <slug>
   ```
   Each line: `<task-id>\t<done|pending>\t<task-file>\t<title>`.
2. **Seed the task tracker** from this output *(sync)* — one entry per task, in listed order, content `<task-id>: <title>`, status mirroring the file state (`done` → completed, else pending). Include the final-validation task as the last entry.
3. Iterate through `pending` tasks in the listed order. Skip `done` ones silently.
4. The final-validation task (the last one, typically titled "Final Validation") is handled differently — see Phase 5.

For each pending non-final task, repeat Phase 4.

### Phase 4 — Implement one task

For the current task:

0. **Mark the task in-progress in the tracker** *(sync)* before doing anything else.
1. **Read the task file** in full. Pay attention to `Depends on`, `Goal`, `Files`, `Acceptance`, `Steps`, `Suggested commit`, and any `Notes`.
2. **Re-read the listed files** so your changes integrate with current code rather than the snapshot the planner saw.
3. **Execute the Steps**:
   - `impl` tasks on a TDD plan run RED → GREEN → REFACTOR against the committed tests:
     - RED — strip this task's stickers, run its tests, and confirm each fails as `tdd/red.txt` records:
       ```bash
       python3 ~/.claude/skills/tdd-plan/scripts/strip_stickers.py --task <task-id>
       ```
     - GREEN — change production code until the task's tests and the rest of the suite pass.
     - REFACTOR — production code only, tests staying green.
   - `impl` tasks on other plans use RED → GREEN → REFACTOR. Write failing tests first, each one non-vacuous and tight per `~/.claude/skills/shared/non-vacuous-tests.md`; implement the minimal change; clean up while keeping tests green.
   - `checklist` tasks are non-code work. Run the listed steps in order.
4. **Verify Acceptance with evidence**. Every checkbox under `## Acceptance` must be demonstrably satisfied per the task's `Evidence:` line — actually produce the artifact (run the test and capture its output, take the screenshot, pull the log excerpt) and include it in the task report. On a TDD plan the red run from RED and the green run from GREEN are the test evidence. Code that compiles or "looks right" is not evidence. If anything is unmet, fix it before continuing; do **not** mark a task done while acceptance fails. (On CI-gated projects, see "When CI is the test gate" below.)
5. **On a TDD plan, check the tests**:
   ```bash
   python3 ~/.claude/skills/tdd-plan/scripts/check_tests.py <slug>
   ```
   It must print `violations=0`. A violation means a test file changed beyond its stickers: restore it (`git restore --source=HEAD -- <path>`, then strip this task's stickers again) and reach green through production code — or, when the test itself is wrong, take the amendment path under Failure handling.
6. **Stage only the files this task changed.** `git add <specific paths>`. Never `git add -A`.
7. **Check the task box in PLAN.md**:
   ```bash
   python3 ~/.claude/skills/implement-plan/scripts/mark_task_done.py <slug> <task-id>
   ```
8. **Stage `PLAN.md` too** so the checkbox lands in the same commit as the task's code change.
9. **Commit via the `create-commit` skill.** Use the task's `Suggested commit:` line as the starting point for the subject; only override the suggested type/scope if the actual diff demands it.
10. **Mark the task completed in the tracker** *(sync)* — the same moment the `PLAN.md` checkbox is committed.
11. Briefly report: `TASK-NNN done → <commit hash> <subject>`. Then move to the next pending task.

#### Failure handling

- **Test won't pass / acceptance can't be met**: stop. Report what you tried, what failed, and the smallest follow-up the user should approve. Do not check the box, do not commit a partial result, do not skip to the next task. Leave the task's tracker entry in-progress so it reflects where work halted.
- **A committed test looks wrong** (TDD plans) — it asserts something the plan contradicts, or calls a signature the task can't provide: stop and show the user the test, the reason, and the exact change via `AskUserQuestion`. Approved → make only that change, commit it on its own via `create-commit` as `test(<scope>): amend <task-id> — <reason>`, then resume the task. Declined → the test stands, and production code satisfies it.
- **Files have drifted from the plan**: if the listed file no longer exists or the structure has changed, update your approach to match the current code and proceed. Note the divergence in your status update.
- **Task has unresolved dependency**: every dependency listed in `Depends on:` must already be `done`. If not, something is out of order — stop and ask.

#### Test review comments

On a TDD plan the user reviews the tests on the draft PR while this skill runs. Read its comments once on the branch (end of Phase 2) and again before final validation (Phase 5):

```bash
gh pr view --json number,comments,reviews
gh api "repos/{owner}/{repo}/pulls/<number>/comments" --jq '.[] | {path, line, created_at, body}'
```

Take each comment about a test that this run hasn't settled yet to the user via `AskUserQuestion`: amend the test as the comment asks, or keep it. An amend follows the amendment path under Failure handling.

#### When CI is the test gate

Some projects cannot build or run tests locally (platform-bound toolchains — check `CLAUDE.md`/`AGENTS.md`; e.g. a Windows-only UI framework on a macOS machine). There:

- Still produce the task's tests — strip its stickers on a TDD plan, write them otherwise; verify acceptance as far as static inspection allows. The task checkbox ticks when the implementation *and its tests* are in place — note each acceptance item that only CI can prove as **CI-pending** in your task report, and never claim a local build or test run happened.
- In Phase 5, run whatever does run locally, list every CI-pending acceptance criterion explicitly, and leave those criteria unchecked in `PLAN.md`.
- CI first judges the implementation when `ship-plan` pushes the branch; its green-CI step fixes red runs and ticks the CI-verified criteria.

### Phase 5 — Final validation

Once all non-final tasks are checked:

1. **On a TDD plan, settle new test review comments** (see above) — an amendment may send you back to a task.
2. **Mark the final-validation task in-progress in the tracker** *(sync)*, then read the final-validation task file.
3. Run every check listed under `## Steps` (analyzers, full test suite, manual smoke, acceptance-criteria walk, etc.) — or their CI-pending treatment on CI-gated projects.
4. If anything fails, stop and report. Do **not** mark the plan done. Leave the final-validation tracker entry in-progress.
5. If everything passes (or is explicitly CI-pending):
   ```bash
   python3 ~/.claude/skills/implement-plan/scripts/mark_task_done.py <slug> <final-task-id>
   python3 ~/.claude/skills/implement-plan/scripts/set_plan_status.py <slug> done
   ```
   Then **mark the final-validation tracker entry completed** *(sync)*.
6. Do **not** invoke `create-commit` for final validation — it produces no source change. (If `PLAN.md`'s final checkbox or Status flip is itself an uncommitted edit, fold it into a tiny `chore: finalize <slug>` commit at the end via `create-commit`.)
7. Report the outcome — tasks completed, commits created, plan `Status:` now `done`, any CI-pending criteria, and every test amendment (the `amendments` list from `check_tests.py`) — then point to the next step:
   ```
   Plan '<slug>' implemented: <N> tasks, <M> local commits, <K> test amendments.
   Harden it:  review-plan <slug>   (adversarial pass before the PR)
   Ship it:    ship-plan <slug>     (pushes, readies the PR, merges)
   ```

## Behaviour Constraints

- **One task → one commit.** Never bundle multiple tasks into one commit, and never split one task across multiple commits. A user-approved test amendment is the one extra commit — its own `test(<scope>): amend …`.
- **Commits stay local.** Pushing belongs to `create-pr`, at ship time.
- **The committed tests are the contract** (TDD plans). The only test-file change this skill makes is `strip_stickers.py` removing the current task's stickers; any other change to a test is a user-approved amendment.
- **Run continuously.** Don't pause between tasks for confirmation; only stop on hard failures or for the final completion report.
- **Respect the task order in `PLAN.md`.** It already encodes dependencies. Don't reorder.
- **Don't invent tasks.** If something is missing from the plan, stop and ask whether to extend the plan via `add_task.py` before doing the extra work.
- **Don't skip acceptance checks.** Marking a box without verifying is worse than failing the task — it silently lies about plan state.
- **Don't edit `RESEARCH.md`, `DECISIONS.md`, or task files** during implementation. They are the planning record. The only plan-directory file you mutate is `PLAN.md` (checkboxes and Status).
- **Use the `create-commit` skill** rather than calling git commit directly — it handles the project's Conventional Commits format and ticket handling.
- **Stage explicitly.** `git add <specific paths>` only — never `git add -A`/`.`.
- **Keep the two task layers in sync** per the rule under "Task tracking" — the *(sync)* markers in the workflow are the complete set of sync points.
