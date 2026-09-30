---
name: archive-plan
description: Archive a finished plan before its PR merges — move the plan dir into the archive, committing the move on the plan's branch where plans are tracked — then, after the merge, return to staging, delete the local branch and roll up Linear. Use when the user says "archive the plan" or "merged, clean up".
argument-hint: [<plan-slug>]
---

# Archive Plan

Plan bookkeeping on both sides of the merge:

- **Archive**, before the merge: move the plan into `docs/artifacts/plans/archive/`. Where git tracks the plans, the move is committed on the plan's branch and lands with the PR, so the base branch never takes a direct push. Where plans are gitignored, the move is local.
- **After the merge**: return to `staging`, delete the local branch, roll up Linear.

`ship-plan` runs Archive as its first step, so the archive commit rides the PR's one CI run, and runs After the merge as its last.

## Archive

### Step 1: Run the script

```bash
bash ~/.claude/skills/archive-plan/scripts/archive_plan.sh [<slug>]
```

Slug resolution:

- If passed → use it.
- Else → the plan whose `Branch:` field in `PLAN.md` matches the current branch.
- Legacy plans without a `Branch:` field fall back to "current branch ends in `/<slug>`" — the script warns but proceeds.
- If resolution is ambiguous or empty, the script exits 1 asking for an explicit slug.

The script:

1. Resolves the slug and its feature branch.
2. Checks where the move can land:
   - **Tracked plans** need the feature branch checked out and its PR unmerged. It refuses `staging`/`main`/`master`, any other branch, and a merged PR, since a commit on a merged branch never reaches the base. For a plan whose PR already merged, commit the move through a follow-up PR.
   - **Gitignored plans** are archived from any branch, merged or not.
3. Moves `docs/artifacts/plans/<slug>/` → `docs/artifacts/plans/archive/<YYYY-MM-DD>-<slug>/`, dated today (UTC). If the destination already exists, appends `-2`, `-3`, …

On success stdout reports:

```
archived=<slug>
from=<plan-path-rel-to-repo>
to=<archive-path-rel-to-repo>
tracked=<yes|no>
branch=<feature-branch>
```

### Step 2: Commit the move

- `tracked=no` → nothing to commit; the archive is local.
- `tracked=yes` → `git add <from> <to>`, then commit via `create-commit` with the subject `chore: archive plan <slug>`. Uncommitted edits inside the plan dir, such as ticked checkboxes, go in the same commit. The next push carries it into the PR: `create-pr` pushes a new branch, otherwise `git push`.

Done when: the plan dir sits under `archive/`, and for a tracked plan `git status --porcelain -- docs/artifacts/plans` is empty.

## After the merge

Run from the main checkout once `gh pr view <branch> --json state` shows `MERGED`.

### Step 1: Return to staging and delete the branch

```bash
git checkout staging && git pull --ff-only origin staging
git branch -d <branch>
```

`<branch>` is the script's `branch=` value, or the `Branch:` field of the archived `PLAN.md`. A dirty tree blocks the checkout: ask the user to commit, stash or discard, and act on the answer. When `git branch -d` refuses (commonly a squash merge, whose commits aren't ancestors of `staging`), leave the branch and hand the user `git log staging..<branch>` to check, then `git branch -D <branch>` to run.

### Step 2: Linear roll-up (only if the plan was epic-linked and Linear is wired)

See `~/.claude/skills/shared/linear-integration.md` for the model. The merge already closed the **phase sub-issue** natively (via the branch id / the PR's `Closes` line); Linear does **not** cascade upward, so this step handles the parent tiers. Skip entirely for standalone plans (`Epic: none`) or when Linear is not wired.

1. Read the `Epic:` field from the archived `PLAN.md` (it names the epic number `NN`).
2. On the up-to-date `staging`, check whether that was the epic's final phase:
   ```bash
   python3 ~/.claude/skills/create-epic/scripts/epic_status.py <NN>
   ```
3. If `all_phases_done=yes` and `linear_issue` is not `none`, close the **epic parent issue** via `mcp__linear-server__save_issue` (state → Done). This is the one deliberate closing write in the whole flow. The epic's **milestone** completes on its own as the phase sub-issues close — no action needed.
4. If `all_phases_done=yes` and the epic has a `project=<slug>`, **post a project update** via `mcp__linear-server__save_status_update` (health `onTrack`): a short note that this epic is complete — how many phases merged and what the next epic is. Post at **epic** granularity only (one update per completed epic), never per phase. Skip if the epic has no project.
5. If this was the **last** epic in that project (all its member epics Done), **remind the user** to mark the Linear Project Completed — do not do it automatically. The project boundary is an editorial call (see `create-project`).

### Step 3: Report

Tell the user the archive path, the branch-deletion outcome, and the Linear writes made.

## Behaviour Constraints

- **Commits land through the PR.** This skill never pushes to `staging`.
- **The caller decides a dirty tree.** Ask; never stash on your own.
- **Remote branches belong to GitHub.** Its auto-delete-on-merge (or manual cleanup) handles them.
- **Archive is bookkeeping.** Tests, lint and CI belong to the caller; task checkboxes are archived as they stand.
