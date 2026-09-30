---
name: create-branch
description: Create a new git branch off a freshly fast-forward-pulled base (default: the remote's default branch). Use when the user asks to create/cut/start a branch, or when another skill needs one programmatically. Requires a clean working tree — the caller resolves dirty state first.
argument-hint: <branch-name> [--base <base-branch>]
---

# Create Branch

Create a new git branch off a fresh copy of a base branch.

## Workflow

### Step 1: Resolve inputs

Required:
- `<branch-name>` — any name accepted by `git check-ref-format` (e.g. `feature/add-search`, `hotfix/login-bug`, `refactor-router`).

Optional:
- `--base <base-branch>` — the branch to cut from. Defaults to the remote's default branch (`origin/HEAD`). Pass it explicitly when the desired base isn't the repo default (e.g. cutting hotfixes off `production`, cutting feature branches off `staging`).

If the user's request is ambiguous about either, ask before proceeding.

### Step 2: Ensure the working tree is clean

The script refuses to run on a dirty tree. If `git status --porcelain` shows any changes:
- ask the user how to proceed: stash, commit, or discard
- act on the answer
- only then continue to Step 3

This skill never stashes automatically — the caller decides.

### Step 3: Run the script

```bash
bash ~/.claude/skills/create-branch/scripts/create_branch.sh <branch-name> [--base <base-branch>]
```

The script:
1. Validates the branch name via `git check-ref-format`.
2. Refuses if the branch already exists locally.
3. Resolves the base (explicit `--base` or `origin/HEAD`).
4. Verifies the base exists locally.
5. Verifies the working tree is clean.
6. `git checkout <base>` → `git pull --ff-only` → `git checkout -b <branch>`.
   If the base is checked out in another git worktree (plain checkout would
   fail), it instead fetches and branches directly off `origin/<base>` —
   safe inside worktree-based pipelines.

On success stdout reports:

```
branch=<new-branch-name>
base=<base-branch-name>
```

Verbose git output goes to stderr.

### Step 4: Confirm

Report the new branch and the base it was cut from.

## Behaviour Constraints

- **Working tree must be clean.** Caller's responsibility.
- **No naming convention is enforced.** Pass any name `git check-ref-format` accepts.
- **Pull is fast-forward only.** If the base has diverged from its remote, the script aborts — diverged state is the user's to resolve.
- **No automatic upstream tracking on the new branch.** The new branch has no remote tracking until the first push.
