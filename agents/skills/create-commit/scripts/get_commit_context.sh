#!/bin/bash
# Gathers context needed for crafting a commit message:
# - Current branch name
# - Extracted ticket number from branch naming convention
# - Staged files summary
# - Staged diff

set -euo pipefail

echo "=== BRANCH ==="
BRANCH=$(git branch --show-current)
echo "$BRANCH"

echo ""
echo "=== TICKET NUMBER ==="
# A Linear-tracked branch embeds the issue id as the first path segment after the
# prefix, e.g. feature/abc-45-home-shell. Linear links the issue via the branch
# and the PR's "Closes" line, so the id must stay OUT of the commit subject —
# otherwise every commit sprays a duplicate link onto the issue.
#
# The first segment is inspected for a <letters>-<digits> id. Planning/version
# tokens (epic-13, phase-2, v2, ...) share that shape but are NOT work items, so
# they are filtered out by a small blocklist.
FIRST_SEG=${BRANCH#*/}
WORKITEM=$(printf '%s' "$FIRST_SEG" | grep -oiE '^[a-z]+-[0-9]+' || true)
PREFIXWORD=$(printf '%s' "$WORKITEM" | sed -E 's/-[0-9]+$//' | tr '[:upper:]' '[:lower:]')
case "$PREFIXWORD" in
  epic|phase|plan|part|step|v|release) WORKITEM="" ;;
esac

if [ -n "$WORKITEM" ]; then
  UPPER_ID=$(printf '%s' "$WORKITEM" | tr '[:lower:]' '[:upper:]')
  echo "(linear: $UPPER_ID — already linked via the branch/PR; do NOT append a #ticket to the subject)"
else
  # Legacy numeric convention: parent-ticket/child-ticket_description.
  TICKET=$(echo "$BRANCH" | sed -n 's|^[0-9]*/\([0-9]*\).*|\1|p')
  if [ -n "$TICKET" ]; then
    echo "#$TICKET"
  else
    echo "(no ticket number found in branch name)"
  fi
fi

echo ""
echo "=== STAGED FILES ==="
STAGED=$(git diff --cached --name-status)
UNSTAGED=$(git diff --name-status)
UNTRACKED=$(git ls-files --others --exclude-standard)

if [ -z "$STAGED" ] && { [ -n "$UNSTAGED" ] || [ -n "$UNTRACKED" ]; }; then
  echo "(none)"
  echo ""
  echo "=== UNSTAGED CHANGES ==="
  if [ -n "$UNSTAGED" ]; then echo "$UNSTAGED"; else echo "(none)"; fi
  echo ""
  echo "=== UNTRACKED FILES ==="
  if [ -n "$UNTRACKED" ]; then echo "$UNTRACKED"; else echo "(none)"; fi
  echo ""
  echo "No staged changes. Stage the intended files explicitly (git add <paths>)"
  echo "and re-run this script. Never use git add -A / git add . — unstaged files"
  echo "may include manual edits that must not be swept into the commit."
  exit 3
fi

if [ -z "$STAGED" ]; then
  echo "(none)"
  echo ""
  echo "=== UNSTAGED CHANGES ==="
  if [ -n "$UNSTAGED" ]; then
    echo "$UNSTAGED"
  else
    echo "(none)"
  fi

  echo ""
  echo "=== UNTRACKED FILES ==="
  if [ -n "$UNTRACKED" ]; then
    echo "$UNTRACKED"
  else
    echo "(none)"
  fi

  echo ""
  echo "No staged, unstaged, or untracked changes found. Nothing to commit."
  exit 2
fi

echo "$STAGED"

echo ""
echo "=== UNSTAGED CHANGES ==="
UNSTAGED=$(git diff --name-status)
if [ -n "$UNSTAGED" ]; then
  echo "$UNSTAGED"
else
  echo "(none)"
fi

echo ""
echo "=== UNTRACKED FILES ==="
UNTRACKED=$(git ls-files --others --exclude-standard)
if [ -n "$UNTRACKED" ]; then
  echo "$UNTRACKED"
else
  echo "(none)"
fi

echo ""
echo "=== STAGED DIFF ==="
git diff --cached
