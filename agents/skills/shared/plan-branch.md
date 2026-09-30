# Plan branch — shared reference

How a plan gets its feature branch. Shared by `tdd-plan`, which cuts it before writing tests, and `implement-plan`, which cuts it when `tdd-plan` was skipped. The branch is cut once: a skill that finds `Branch:` already set in `PLAN.md` switches to that branch instead.

1. **Pick a prefix** based on the plan's Goal and Scope. Common conventions:
   - `feature` — new user-facing capability
   - `bug` — fixing incorrect behaviour
   - `refactor` — restructuring without behaviour change
   - `chore` — tooling, deps, config
   - `docs` — documentation only
   - `perf` — performance work
   - `hotfix` — urgent production fix

   If the plan title or Goal makes the category obvious, pick silently and report it. If it's genuinely ambiguous (e.g. a refactor that also fixes a bug), ask the user via `AskUserQuestion`.

2. **Run the prep script.** If `PLAN.md` has a `Linear:` field with an issue id (not `none`), pass its lowercased identifier as the third argument so the branch embeds it and Linear links the issue automatically:
   ```bash
   bash ~/.claude/skills/implement-plan/scripts/prepare_branch.sh <slug> <prefix> [<linear-id>] [--base <branch>]
   ```
   For example, `Linear: ABC-45` → pass `abc-45`, yielding a branch like `feature/abc-45-<slug>`. Omit the third argument for standalone plans (`Linear: none`).

   This snapshots `docs/artifacts/plans/<slug>/`, stashes any other uncommitted changes (so the working tree is clean), delegates the actual checkout/pull/branch-create to the `create-branch` skill's script (`--base staging`, the default), then restores the plan directory onto the new branch. It is worktree-safe: if `staging` is checked out in another worktree, the branch is cut from `origin/staging` instead.

   The script's final stdout reports `branch=`, `base=`, `stashed=`, and (if applicable) `stash_ref=`. Report these back to the user — if `stashed=1`, mention how to recover the parked work.

3. **Record the branch in `PLAN.md`** so `archive-plan` and `check_tests.py` can resolve the plan↔branch link without relying on naming convention:
   ```bash
   python3 ~/.claude/skills/implement-plan/scripts/set_plan_branch.py <slug> <branch>
   ```

4. **Commit the plan onto the new branch** as its very first commit: stage `docs/artifacts/plans/<slug>/` and invoke `create-commit` with a `chore: add plan for <slug>` subject. Later commits then carry only their own change.

5. **Advance the linked epic phase** (only if `PLAN.md`'s `Epic:`/`Phase:` are not `none`):
   ```bash
   python3 ~/.claude/skills/create-epic/scripts/link_plan.py <NN> --phase <NN.M> --plan <slug> --status in-progress
   ```
   `<NN>` and `<NN.M>` come from the `Epic:`/`Phase:` fields. The final-validation task flips the phase to `done` later.

   **Linear (only if wired — see `~/.claude/skills/shared/linear-integration.md`):** set the phase *sub-issue* (the id from `PLAN.md`'s `Linear:` field) to **In Progress** via `mcp__linear-server__save_issue`, so the board reflects started work before the first push. Linear does not cascade to the parent, so if this is the epic's first phase to start, bump the **epic parent issue** to In Progress once (the parent id is the epic file's `Linear:` field). Optionally post the plan summary as a comment on the sub-issue.

Done when: the current branch is the one `prepare_branch.sh` reported, `PLAN.md`'s `Branch:` names it, and `chore: add plan for <slug>` is committed on it.
