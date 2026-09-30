#!/usr/bin/env bash
#
# Verify a plan is in a reviewable state before running adversarial review.
#
# Usage: check_preconditions.sh <slug>
#
# Refuses with a clear reason and exit 1 if any of these fail:
#   - Working tree is dirty
#   - PLAN.md missing
#   - `Status:` is not `done`
#   - `Branch:` does not match the current branch
#   - Current branch is `staging` or `main`/`master`
#   - Any task checkbox under `## Tasks` is unchecked
#
# Exit codes:
#   0  all good
#   1  precondition violated
#   2  usage error

set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: check_preconditions.sh <slug>" >&2
    exit 2
fi

SLUG="$1"

if ! REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null); then
    echo "error: not inside a git repository" >&2
    exit 1
fi

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" = "HEAD" ]; then
    echo "error: detached HEAD — check out the plan's feature branch first" >&2
    exit 1
fi

if [ "$CURRENT_BRANCH" = "staging" ] || [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
    echo "error: refusing to review on protected branch '$CURRENT_BRANCH'" >&2
    exit 1
fi

PLAN_DIR="$REPO_ROOT/docs/artifacts/plans/$SLUG"
PLAN_MD="$PLAN_DIR/PLAN.md"

if [ ! -f "$PLAN_MD" ]; then
    echo "error: plan not found: $PLAN_MD" >&2
    exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
    echo "error: working tree is not clean. Stash, commit, or discard changes before review:" >&2
    git status --short >&2
    exit 1
fi

STATUS=$(grep -E '^Status:' "$PLAN_MD" | head -n1 | sed -E 's/^Status:[[:space:]]*//' | awk '{print $1}')
if [ "$STATUS" != "done" ]; then
    echo "error: plan status is '${STATUS:-unknown}', expected 'done'. Finish implement-plan first." >&2
    exit 1
fi

RECORDED_BRANCH=$(grep -E '^Branch:' "$PLAN_MD" | head -n1 | sed -E 's/^Branch:[[:space:]]*//' | awk '{print $1}')
if [ -z "$RECORDED_BRANCH" ]; then
    echo "error: plan '$SLUG' has no Branch: field in PLAN.md. Set it before reviewing." >&2
    exit 1
fi
if [ "$RECORDED_BRANCH" != "$CURRENT_BRANCH" ]; then
    echo "error: current branch '$CURRENT_BRANCH' does not match plan's recorded branch '$RECORDED_BRANCH'." >&2
    echo "  checkout the correct branch:  git checkout $RECORDED_BRANCH" >&2
    exit 1
fi

# Verify every checkbox in `## Tasks` is ticked.
UNCHECKED=$(python3 - "$PLAN_MD" <<'PY'
import re, sys
plan = open(sys.argv[1]).read().splitlines()
TASK = re.compile(r"^- \[(?P<box>[ xX])\]\s+(?P<id>TASK-\d+):\s+(?P<title>.+?)(?:\s+\(depends on [^)]+\))?\s*$")
in_tasks = False
unchecked = []
for line in plan:
    if line.startswith("## Tasks"):
        in_tasks = True
        continue
    if in_tasks and line.startswith("## "):
        break
    if not in_tasks:
        continue
    m = TASK.match(line)
    if m and m.group("box") == " ":
        unchecked.append(f"{m.group('id')}: {m.group('title').strip()}")
for u in unchecked:
    print(u)
PY
)

if [ -n "$UNCHECKED" ]; then
    echo "error: plan has unchecked tasks:" >&2
    echo "$UNCHECKED" | sed 's/^/  - /' >&2
    echo "Finish implement-plan before reviewing." >&2
    exit 1
fi

# Non-fatal: rounds prefer the Codex plugin; without it the skill falls back to
# a general-purpose subagent (see ~/.claude/skills/shared/adversarial-rounds.md).
if ! ls "$HOME"/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs >/dev/null 2>&1; then
    echo "warning: openai-codex plugin not found — /codex-local:adversarial-review will fail; use the subagent fallback" >&2
fi

exit 0
