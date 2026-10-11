---
name: ship-plan
description: Land an implemented plan's branch — archive the plan, open or finish its PR, drive CI to green, merge, then clean up. Use when the user says "ship it", "ship the plan", or "merge the plan's branch" once implement-plan has committed its tasks. It merges without asking again, so invoke it only on the user's ask to ship; after it hands back a question, pass the user's answer as an argument.
argument-hint: "[<plan-slug>] [<answer to a hand-back>]"
context: fork
background: false
model: haiku
effort: medium
---

# Ship Plan

Take a plan whose tasks are committed the rest of the way: archived → ready PR → green CI → merged → cleaned up. Archiving comes first so its commit rides the PR's one CI run. Run it from the main checkout on the plan's branch.

This skill runs as a subagent: it sees the repo and its arguments, not the conversation, and it cannot ask the user. Being invoked is the go-ahead to merge. Where a step needs a decision or a code fix, **hand back** — stop, and return what you found plus the exact question or next action. The caller settles it and invokes `ship-plan <slug>` again, with the user's answer in the arguments; every step below resumes from the state it finds.

## Step 1: Resolve the plan

- Slug: the first argument, else the plan whose `Branch:` matches the current branch:
  `grep -rl --include=PLAN.md "^Branch: $(git branch --show-current)$" docs/artifacts/plans`
  A match under `archive/` means an earlier run archived it: skip Step 2.
- A dirty working tree would be left out of the PR: hand back with the `git status --porcelain` output, for the user to commit, stash or discard.

Done when: exactly one plan, the current branch is its `Branch:`, and `git status --porcelain` is empty.

## Step 2: Archive

Invoke `archive-plan <slug>`: it moves the plan, and commits the move on this branch when the plan is tracked.

Done when: it reported `archived=<slug>`, and a tracked plan's move is committed.

## Step 3: Ready PR

Check the tests first — `create-pr` repeats this, but the ready-PR path below pushes without it:

```bash
python3 ~/.claude/skills/tdd-plan/scripts/check_tests.py --final
```

`tdd=none` or `violations=0` → carry on. Any violation → hand back with it.

`gh pr view --json number,url,state,isDraft` on the current branch:

- No PR, or a draft → invoke `create-pr`. It opens the PR, or pushes the local commits and readies the draft `tdd-plan` opened. The plan's `VALIDATION.md` and `REVIEW.md` now live at the archive path.
- Open and ready → `git push` if the branch is ahead of its remote.
- Merged → skip to Step 6.
- Closed → hand back.

Done when: the PR is open, not a draft, and its head is the local `HEAD`.

## Step 4: Green CI

Watch the checks in the foreground with the longest timeout, running the command again if it times out before the checks finish: `gh pr checks <n> --watch --fail-fast`.

- **Green** (every check passed) → tick the acceptance criteria that were waiting on CI wherever a tick needs no push: the PR body's test plan (`gh pr edit`) and a gitignored archived `PLAN.md`. A tracked archive keeps its criteria as committed; the green check on the PR is their record.
- **No checks reported** → merge when the arguments say to merge without CI; otherwise hand back, asking whether to.
- **Red** → hand back. Fixing belongs to the caller: find the root cause with `gh run view <run-id> --log-failed`, then return this, filled in:
  ```
  CI is red on PR <url>: <check> failed — <root cause, with the log lines that show it>.
  Fix it on <branch>: reproduce with the repo's own gate (AGENTS.md names it), commit via create-commit as a `fix:`, push, then run `ship-plan <slug>` again.
  A fix that edits tests, the gate script or the CI workflow goes to the user before it is pushed; an approved test edit is its own `test(<scope>): amend …` commit.
  ```

Done when: every check on the PR's current head passed.

## Step 5: Merge

`gh pr merge <n> --merge`, with no `--delete-branch`. The merge commit keeps the per-task commits, so the local branch deletes cleanly with `git branch -d` in Step 6; `--delete-branch` would switch branches and delete it first.

- Behind the base (a strict required check) → `gh pr update-branch <n>`, `git pull --ff-only`, back to Step 4.
- Any other refusal (conflicts, a required review) → hand back with it verbatim.

Done when: `gh pr view <n> --json state,mergedAt` shows `MERGED`. A `Closes <ID>` line in the body closes the Linear issue.

## Step 6: Clean up

Invoke `archive-plan <slug> after-merge`: back to an up-to-date `staging`, delete the local branch, roll up Linear.

Done when: `git branch --show-current` prints `staging` and the branch-deletion outcome is known.

## Step 7: Report

One line each: the merged PR URL, the archive path, the branch-deletion outcome, Linear writes, and the next plan or phase.
