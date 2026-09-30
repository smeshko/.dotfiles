---
name: purge
description: Force remove all git worktrees and delete all local branches except main and staging. This skill should be used when users want to clean up their repository by removing worktrees and resetting branches to a clean state. (user)
---

# Purge

## Overview

Clean up a git repository by force-removing all worktrees and deleting all local branches except `main` and `staging`.

## Workflow

### Step 1: Confirm with User

Before executing the purge, confirm with the user that they want to proceed. This is a destructive operation that:
- Force removes ALL git worktrees
- Deletes ALL local branches except `main` and `staging`

### Step 2: Execute Purge Script

Run the purge script to perform the cleanup:

```bash
bash ~/.claude/skills/purge/scripts/purge.sh
```

The script will:
1. List and force-remove all worktrees (excluding the main working directory)
2. Switch to `main` or `staging` branch (whichever exists)
3. Delete all local branches except `main` and `staging`
4. Report what was removed

### Step 3: Report Results

After execution, report to the user:
- Number of worktrees removed
- List of branches deleted
- Any errors encountered
