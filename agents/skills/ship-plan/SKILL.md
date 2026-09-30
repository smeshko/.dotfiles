---
name: ship-plan
description: Land an implemented plan's branch — archive the plan, open or finish its PR, drive CI to green, merge, then clean up. Use when the user says "ship it", "ship the plan", or "merge the plan's branch" once implement-plan has committed its tasks.
argument-hint: [<plan-slug>]
---

# Ship Plan

Take a plan whose tasks are committed the rest of the way: archived → ready PR → green CI → merged → cleaned up. Archiving comes first so its commit rides the PR's one CI run. Run it from the main checkout on the plan's branch. The user's ask to ship is the go-ahead to merge; reached without one — from another skill, or on your own read that the plan is done — confirm with the user before Step 5.

## Step 1: Resolve the plan

- Slug: the argument, else the plan whose `Branch:` matches the current branch:
  `grep -rl --include=PLAN.md "^Branch: $(git branch --show-current)$" docs/artifacts/plans`
  A match under `archive/` means an earlier run archived it: skip Step 2.
- A dirty working tree would be left out of the PR: ask the user to commit, stash or discard, and act on the answer.

Done when: exactly one plan, the current branch is its `Branch:`, and `git status --porcelain` is empty.

## Step 2: Archive

Invoke `archive-plan <slug>` and run its **Archive** section: the move, plus its commit on this branch when the plan is tracked.

Done when: the script printed `archived=<slug>`, and a tracked plan's move is committed.

## Step 3: Ready PR

Check the tests first — `create-pr` repeats this, but the ready-PR path below pushes without it:

```bash
python3 ~/.claude/skills/tdd-plan/scripts/check_tests.py --final
```

`tdd=none` or `violations=0` → carry on. Any violation → stop and report it.

`gh pr view --json number,url,state,isDraft` on the current branch:

- No PR, or a draft → invoke `create-pr`. It opens the PR, or pushes the local commits and readies the draft `tdd-plan` opened. The plan's `VALIDATION.md` and `REVIEW.md` now live at the archive path.
- Open and ready → `git push` if the branch is ahead of its remote.
- Merged → skip to Step 6.
- Closed → stop and report.

Done when: the PR is open, not a draft, and its head is the local `HEAD`.

## Step 4: Green CI

Watch the checks as a background task: `gh pr checks <n> --watch --fail-fast`.

- **Green** (every check passed) → tick the acceptance criteria that were waiting on CI wherever a tick needs no push: the PR body's test plan (`gh pr edit`) and a gitignored archived `PLAN.md`. A tracked archive keeps its criteria as committed; the green check on the PR is their record.
- **No checks reported** → ask the user whether to merge without CI.
- **Red** → one fix round:
  1. `gh run view <run-id> --log-failed` → the root cause. Reproduce it with the repo's own gate (AGENTS.md names it).
  2. Fix the cause, commit via `create-commit` as a `fix:`, push, watch again.
  3. A fix that edits tests, the gate script or the CI workflow to reach green goes to the user before it is pushed. An approved test edit is a test amendment: its own `test(<scope>): amend …` commit.

After three red rounds, stop and report each failure and what was tried.

Done when: every check on the PR's current head passed.

## Step 5: Merge

`gh pr merge <n> --merge`, with no `--delete-branch`. The merge commit keeps the per-task commits, so the local branch deletes cleanly with `git branch -d` in Step 6; `--delete-branch` would switch branches and delete it first.

- Behind the base (a strict required check) → `gh pr update-branch <n>`, `git pull --ff-only`, back to Step 4.
- Any other refusal (conflicts, a required review) → stop and report it verbatim.

Done when: `gh pr view <n> --json state,mergedAt` shows `MERGED`. A `Closes <ID>` line in the body closes the Linear issue.

## Step 6: Clean up

Run `archive-plan`'s **After the merge** section: back to an up-to-date `staging`, delete the local branch, roll up Linear.

Done when: `git branch --show-current` prints `staging` and the branch-deletion outcome is known.

## Step 7: Report

One line each: the merged PR URL, CI fix commits (or none), the archive path, the branch-deletion outcome, Linear writes, and the next plan or phase.
