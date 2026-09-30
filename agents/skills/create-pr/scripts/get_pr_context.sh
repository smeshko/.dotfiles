#!/usr/bin/env bash
#
# Gather context needed to compose a pull request from the current branch.
#
# Output (each section preceded by `=== SECTION ===`):
#   BRANCH         current branch name
#   BASE           base branch (origin/HEAD) or (unknown)
#   LINEAR ISSUE   issue id from the branch name or its plan's Linear: field, else (none)
#   EXISTING PR    URL of an existing open PR for this branch, else (none)
#   COMMITS        commits since base, oldest first
#   FILES          files changed vs base
#   PUSH STATUS    unpushed | up-to-date | ahead (N) | behind-remote (N) | diverged
#
# Exits 0 normally. Exits non-zero only if not in a git repo or gh is missing.

set -euo pipefail

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
    echo "error: not inside a git repository" >&2
    exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
    echo "error: gh (GitHub CLI) is required — install it from https://cli.github.com/" >&2
    exit 1
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "HEAD" ]; then
    echo "error: detached HEAD — check out a branch first" >&2
    exit 1
fi

echo "=== BRANCH ==="
echo "$BRANCH"

BASE=""
if git rev-parse --verify --quiet origin/HEAD >/dev/null 2>&1; then
    BASE=$(git rev-parse --abbrev-ref origin/HEAD | sed 's|^origin/||')
fi
echo ""
echo "=== BASE ==="
if [ -n "$BASE" ]; then
    echo "$BASE"
else
    echo "(unknown — pass --base to create_pr.sh)"
fi

echo ""
echo "=== LINEAR ISSUE ==="
# A Linear-tracked branch embeds the issue id as the first segment after the
# prefix (feature/abc-45-...). Surface it so the PR body can carry "Closes <ID>",
# which drives the issue to Done when the PR merges. Planning/version tokens
# (epic-13, phase-2, ...) share the shape but are not work items — filter them.
FIRST_SEG=${BRANCH#*/}
WORKITEM=$(printf '%s' "$FIRST_SEG" | grep -oiE '^[a-z]+-[0-9]+' || true)
PREFIXWORD=$(printf '%s' "$WORKITEM" | sed -E 's/-[0-9]+$//' | tr '[:upper:]' '[:lower:]')
case "$PREFIXWORD" in
  epic|phase|plan|part|step|v|release) WORKITEM="" ;;
esac
# A plan branch cut before its plan was linked carries no id in its name: fall
# back to the `Linear:` field of the plan whose `Branch:` is this branch.
if [ -z "$WORKITEM" ]; then
    PLANS_DIR="$(git rev-parse --show-toplevel)/docs/artifacts/plans"
    PLAN_FILE=$(grep -rlFx --include=PLAN.md "Branch: $BRANCH" "$PLANS_DIR" 2>/dev/null | head -1 || true)
    if [ -n "$PLAN_FILE" ]; then
        WORKITEM=$(sed -nE 's/^Linear: ([A-Za-z]+-[0-9]+)[[:space:]]*$/\1/p' "$PLAN_FILE" | head -1)
    fi
fi
if [ -n "$WORKITEM" ]; then
    printf '%s\n' "$WORKITEM" | tr '[:lower:]' '[:upper:]'
else
    echo "(none — not a Linear-tracked branch)"
fi

echo ""
echo "=== EXISTING PR ==="
EXISTING=$(gh pr view --json url --jq .url 2>/dev/null || true)
if [ -n "$EXISTING" ]; then
    echo "$EXISTING"
else
    echo "(none)"
fi

echo ""
echo "=== COMMITS ==="
if [ -n "$BASE" ]; then
    REF=""
    if git rev-parse --verify --quiet "origin/$BASE" >/dev/null 2>&1; then
        REF="origin/$BASE"
    elif git rev-parse --verify --quiet "$BASE" >/dev/null 2>&1; then
        REF="$BASE"
    fi
    if [ -n "$REF" ]; then
        OUT=$(git log --reverse --oneline "$REF..HEAD" || true)
        if [ -n "$OUT" ]; then
            echo "$OUT"
        else
            echo "(no commits since $REF)"
        fi
    else
        echo "(base ref not resolvable)"
    fi
else
    git log --oneline -10
fi

echo ""
echo "=== FILES ==="
if [ -n "${REF:-}" ]; then
    OUT=$(git diff --name-only "$REF...HEAD" || true)
    if [ -n "$OUT" ]; then
        echo "$OUT"
    else
        echo "(no file changes)"
    fi
else
    echo "(no base — files unknown)"
fi

echo ""
echo "=== PUSH STATUS ==="
if ! git rev-parse --verify --quiet "@{u}" >/dev/null 2>&1; then
    echo "unpushed"
else
    AHEAD=$(git rev-list --count "@{u}..HEAD")
    BEHIND=$(git rev-list --count "HEAD..@{u}")
    if [ "$AHEAD" -eq 0 ] && [ "$BEHIND" -eq 0 ]; then
        echo "up-to-date"
    elif [ "$AHEAD" -gt 0 ] && [ "$BEHIND" -eq 0 ]; then
        echo "ahead ($AHEAD)"
    elif [ "$AHEAD" -eq 0 ] && [ "$BEHIND" -gt 0 ]; then
        echo "behind-remote ($BEHIND)"
    else
        echo "diverged (+$AHEAD/-$BEHIND)"
    fi
fi
