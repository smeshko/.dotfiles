#!/usr/bin/env bash
#
# Verify a plan is in a validatable state before running adversarial validation.
#
# Usage: check_preconditions.sh <slug>
#
# Refuses with a clear reason and exit 1 if any of these fail:
#   - Not inside a git repository
#   - PLAN.md missing
#   - `Status:` is `tests-ready`, `in-progress` or `done` (validation is a pre-tests step)
#   - Working tree is dirty (so applied edits are cleanly attributable to validation)
#
# Notes:
#   - Unlike review-plan, this script does NOT check the current branch.
#     Validation runs before implement-plan cuts a feature branch, so the user
#     is normally still on staging at this point.
#   - It does NOT check task checkboxes — implementation hasn't started.
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

PLAN_DIR="$REPO_ROOT/docs/artifacts/plans/$SLUG"
PLAN_MD="$PLAN_DIR/PLAN.md"

if [ ! -f "$PLAN_MD" ]; then
    echo "error: plan not found: $PLAN_MD" >&2
    exit 1
fi

# The plan dir itself is allowed to be dirty (it's the validation target — typically
# freshly created and untracked, or edited between validation rounds). What we refuse
# is unrelated edits elsewhere, so validation's applied edits stay attributable.
DIRTY=$(git status --porcelain -- . ":(exclude)docs/artifacts/plans/$SLUG" 2>/dev/null)
if [ -n "$DIRTY" ]; then
    echo "error: working tree has changes outside the plan dir. Stash, commit, or discard them so validation edits stay cleanly attributable:" >&2
    echo "$DIRTY" >&2
    exit 1
fi

STATUS=$(grep -E '^Status:' "$PLAN_MD" | head -n1 | sed -E 's/^Status:[[:space:]]*//' | awk '{print $1}')
case "$STATUS" in
    draft|ready)
        ;;
    tests-ready)
        echo "error: plan status is 'tests-ready'. tdd-plan already wrote tests against this plan;" >&2
        echo "  validation edits now would drift from them. Validate before tdd-plan runs." >&2
        exit 1
        ;;
    in-progress)
        echo "error: plan status is 'in-progress'. Validation is a pre-implementation step." >&2
        echo "  If you want a post-implementation review of the branch, use review-plan instead." >&2
        exit 1
        ;;
    done)
        echo "error: plan status is 'done'. Validation runs before implementation, not after." >&2
        echo "  If you want a post-implementation review of the branch, use review-plan instead." >&2
        exit 1
        ;;
    "")
        echo "error: PLAN.md is missing a Status: field" >&2
        exit 1
        ;;
    *)
        echo "error: unrecognised plan status '$STATUS' (expected draft or ready)" >&2
        exit 1
        ;;
esac

# Non-fatal: rounds prefer the Codex plugin; without it the skill falls back to
# a general-purpose subagent (see ~/.claude/skills/shared/adversarial-rounds.md).
if ! ls "$HOME"/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs >/dev/null 2>&1; then
    echo "warning: openai-codex plugin not found — /codex-local:adversarial-review will fail; use the subagent fallback" >&2
fi

exit 0
