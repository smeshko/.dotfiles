#!/bin/bash
# Purge script: Remove all worktrees and delete all branches except main/staging

set -e

echo "=== Git Purge Script ==="
echo ""

# Check if we're in a git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Get the main worktree path
MAIN_WORKTREE=$(git rev-parse --show-toplevel)

echo "Main worktree: $MAIN_WORKTREE"
echo ""

# --- Remove Worktrees ---
echo "=== Removing Worktrees ==="

WORKTREES_REMOVED=0

# Get list of worktrees (excluding the main one)
git worktree list --porcelain | grep "^worktree " | cut -d' ' -f2- | while read -r worktree_path; do
    if [ "$worktree_path" != "$MAIN_WORKTREE" ]; then
        echo "Removing worktree: $worktree_path"
        git worktree remove --force "$worktree_path" 2>/dev/null || {
            echo "  Force removing with directory deletion..."
            rm -rf "$worktree_path"
            git worktree prune
        }
        ((WORKTREES_REMOVED++)) || true
    fi
done

# Prune any stale worktree references
git worktree prune
echo "Worktree cleanup complete."
echo ""

# --- Switch to safe branch ---
echo "=== Switching to safe branch ==="

CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")

# Determine which safe branch to use
if git show-ref --verify --quiet refs/heads/staging; then
    SAFE_BRANCH="staging"
elif git show-ref --verify --quiet refs/heads/main; then
    SAFE_BRANCH="main"
else
    echo "Warning: Neither 'main' nor 'staging' branch exists locally."
    echo "Creating 'main' branch from current HEAD..."
    git checkout -b main
    SAFE_BRANCH="main"
fi

if [ "$CURRENT_BRANCH" != "$SAFE_BRANCH" ]; then
    echo "Switching to $SAFE_BRANCH..."
    git checkout "$SAFE_BRANCH"
else
    echo "Already on $SAFE_BRANCH"
fi
echo ""

# --- Delete branches ---
echo "=== Deleting local branches ==="

BRANCHES_DELETED=0

# Get all local branches except main and staging
for branch in $(git branch --format='%(refname:short)'); do
    if [ "$branch" != "main" ] && [ "$branch" != "staging" ]; then
        echo "Deleting branch: $branch"
        git branch -D "$branch" 2>/dev/null && ((BRANCHES_DELETED++)) || {
            echo "  Warning: Could not delete $branch"
        }
    fi
done

echo ""
echo "=== Purge Complete ==="
echo "Branches deleted: $BRANCHES_DELETED"
echo ""
echo "Remaining branches:"
git branch --list
