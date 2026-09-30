#!/usr/bin/env bash
#
# Create a new git branch off a base branch.
#
# Usage:
#   create_branch.sh <branch-name> [--base <base-branch>]
#
# Behavior:
#   1. Validate the branch name with git check-ref-format.
#   2. Refuse if the branch already exists locally.
#   3. Resolve the base: --base if given, else the remote default (origin/HEAD).
#   4. Verify the base exists locally.
#   5. Refuse if the working tree is dirty.
#   6. Checkout the base, pull --ff-only, create and checkout the new branch.
#      If the base is checked out in another git worktree (plain checkout would
#      fail), fetch and branch directly off origin/<base> instead.
#
# Output on success (stdout):
#   branch=<new-branch-name>
#   base=<base-branch-name>
#
# Verbose git output goes to stderr. Non-zero exit on any failure.

set -euo pipefail

BRANCH_NAME=""
BASE_BRANCH=""

while [ $# -gt 0 ]; do
    case "$1" in
        --base)
            [ $# -ge 2 ] || { echo "error: --base requires a value" >&2; exit 2; }
            BASE_BRANCH="$2"
            shift 2
            ;;
        --)
            shift
            ;;
        --*)
            echo "error: unknown flag '$1'" >&2
            exit 2
            ;;
        *)
            if [ -n "$BRANCH_NAME" ]; then
                echo "error: unexpected positional argument '$1'" >&2
                exit 2
            fi
            BRANCH_NAME="$1"
            shift
            ;;
    esac
done

if [ -z "$BRANCH_NAME" ]; then
    echo "usage: create_branch.sh <branch-name> [--base <base-branch>]" >&2
    exit 2
fi

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
    echo "error: not inside a git repository" >&2
    exit 1
fi

if ! git check-ref-format --branch "$BRANCH_NAME" >/dev/null 2>&1; then
    echo "error: '$BRANCH_NAME' is not a valid branch name" >&2
    exit 1
fi

if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
    echo "error: branch '$BRANCH_NAME' already exists locally" >&2
    exit 1
fi

if [ -z "$BASE_BRANCH" ]; then
    if git rev-parse --verify --quiet origin/HEAD >/dev/null 2>&1; then
        BASE_BRANCH=$(git rev-parse --abbrev-ref origin/HEAD | sed 's|^origin/||')
    fi
    if [ -z "$BASE_BRANCH" ]; then
        echo "error: could not resolve default base branch (origin/HEAD not set). Pass --base explicitly." >&2
        exit 1
    fi
fi

if ! git show-ref --verify --quiet "refs/heads/$BASE_BRANCH"; then
    echo "error: base branch '$BASE_BRANCH' does not exist locally — fetch or create it first" >&2
    exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
    echo "error: working tree is not clean. Stash, commit, or discard changes before creating a branch." >&2
    exit 1
fi

# If the base branch is checked out in another worktree, `git checkout <base>`
# fails. Branch directly off the fresh remote tip instead.
if git worktree list --porcelain | awk -v ref="refs/heads/$BASE_BRANCH" -v top="$(git rev-parse --show-toplevel)" '
        /^worktree /{wt=substr($0,10)}
        /^branch /{if (substr($0,8)==ref && wt!=top) found=1}
        END{exit found?0:1}'; then
    git fetch origin "$BASE_BRANCH" >&2
    git checkout -b "$BRANCH_NAME" --no-track "origin/$BASE_BRANCH" >&2
    echo "note: base '$BASE_BRANCH' is checked out in another worktree — branched off origin/$BASE_BRANCH" >&2
else
    git checkout "$BASE_BRANCH" >&2
    git pull --ff-only >&2
    git checkout -b "$BRANCH_NAME" >&2
fi

echo "branch=$BRANCH_NAME"
echo "base=$BASE_BRANCH"
