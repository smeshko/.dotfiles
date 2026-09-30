#!/usr/bin/env bash
#
# Archive a finished plan before its PR merges.
#
# Usage:
#   archive_plan.sh [<slug>]
#
# Behavior:
#   1. Resolve the slug: positional, else match current branch to a plan's
#      `Branch:` field in PLAN.md, else fall back to "branch ends in /<slug>".
#   2. Verify docs/artifacts/plans/<slug>/ exists.
#   3. Resolve the feature branch (Branch: field, or current branch fallback).
#   4. Tracked plans (docs/artifacts/plans not gitignored) must be archived on
#      the feature branch while its PR is unmerged, so the move lands with the
#      PR: refuse on any other branch, on staging/main/master, and when the
#      branch's PR is already merged. Gitignored plans are local-only and are
#      archived from any branch, merged or not.
#   5. Move plan dir to docs/artifacts/plans/archive/<YYYY-MM-DD>-<slug>/
#      (today, UTC; appends -2, -3, ... if the destination already exists).
#
# Output on success (stdout, parseable):
#   archived=<slug>
#   from=<plan-path>
#   to=<archive-path>
#   tracked=<yes|no>
#   branch=<feature-branch>
#
# Warnings go to stderr.
# Exit 0 on success, 1 on logical error, 2 on usage error.

set -euo pipefail

SLUG=""

while [ $# -gt 0 ]; do
    case "$1" in
        --)
            shift
            ;;
        --*)
            echo "error: unknown flag '$1'" >&2
            exit 2
            ;;
        *)
            if [ -n "$SLUG" ]; then
                echo "error: unexpected positional argument '$1'" >&2
                exit 2
            fi
            SLUG="$1"
            shift
            ;;
    esac
done

if ! REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null); then
    echo "error: not inside a git repository" >&2
    exit 1
fi

BASE_BRANCH="staging"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GET_PLAN_BRANCH="$SCRIPT_DIR/get_plan_branch.py"

PLANS_DIR="$REPO_ROOT/docs/artifacts/plans"

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" = "HEAD" ]; then
    echo "error: detached HEAD" >&2
    exit 1
fi

# --- Resolve slug ---

if [ -z "$SLUG" ]; then
    MATCHES=()
    if [ -d "$PLANS_DIR" ]; then
        for plan_dir in "$PLANS_DIR"/*/; do
            plan_dir="${plan_dir%/}"
            slug_candidate=$(basename "$plan_dir")
            [ "$slug_candidate" = "archive" ] && continue
            [ -f "$plan_dir/PLAN.md" ] || continue
            recorded=$(python3 "$GET_PLAN_BRANCH" "$slug_candidate" --root "$REPO_ROOT" 2>/dev/null || true)
            if [ -n "$recorded" ] && [ "$recorded" = "$CURRENT_BRANCH" ]; then
                MATCHES+=("$slug_candidate")
            fi
        done
    fi

    if [ "${#MATCHES[@]}" -eq 1 ]; then
        SLUG="${MATCHES[0]}"
    elif [ "${#MATCHES[@]}" -gt 1 ]; then
        echo "error: multiple plans recorded with branch '$CURRENT_BRANCH':" >&2
        for m in "${MATCHES[@]}"; do echo "  - $m" >&2; done
        echo "Pass the slug explicitly." >&2
        exit 1
    else
        # Fallback: branch ends in /<slug> for exactly one plan.
        FALLBACKS=()
        if [ -d "$PLANS_DIR" ]; then
            for plan_dir in "$PLANS_DIR"/*/; do
                plan_dir="${plan_dir%/}"
                slug_candidate=$(basename "$plan_dir")
                [ "$slug_candidate" = "archive" ] && continue
                [ -f "$plan_dir/PLAN.md" ] || continue
                if [[ "$CURRENT_BRANCH" == */"$slug_candidate" ]]; then
                    FALLBACKS+=("$slug_candidate")
                fi
            done
        fi
        if [ "${#FALLBACKS[@]}" -eq 1 ]; then
            SLUG="${FALLBACKS[0]}"
            echo "warning: plan '$SLUG' has no Branch: field — matched via branch suffix '$CURRENT_BRANCH'" >&2
        else
            echo "error: no plan recorded with branch '$CURRENT_BRANCH'. Pass the slug explicitly." >&2
            exit 1
        fi
    fi
fi

PLAN_DIR="$PLANS_DIR/$SLUG"
if [ ! -d "$PLAN_DIR" ]; then
    echo "error: plan directory not found: $PLAN_DIR" >&2
    echo "Gitignored plans exist only in the checkout that created them — run from there." >&2
    exit 1
fi

# --- Resolve feature branch ---

FEATURE_BRANCH=$(python3 "$GET_PLAN_BRANCH" "$SLUG" --root "$REPO_ROOT" 2>/dev/null || true)
if [ -z "$FEATURE_BRANCH" ]; then
    FEATURE_BRANCH="$CURRENT_BRANCH"
    echo "warning: plan '$SLUG' has no Branch: field — falling back to current branch '$FEATURE_BRANCH'" >&2
fi

# --- Tracked plans ride the PR: feature branch, PR unmerged ---

TRACKED="yes"
if git check-ignore -q "$PLAN_DIR"; then
    TRACKED="no"
fi

if [ "$TRACKED" = "yes" ]; then
    if [ "$FEATURE_BRANCH" = "$BASE_BRANCH" ] || [ "$FEATURE_BRANCH" = "main" ] || [ "$FEATURE_BRANCH" = "master" ]; then
        echo "error: refusing to archive a tracked plan against protected branch '$FEATURE_BRANCH'" >&2
        exit 1
    fi
    if [ "$CURRENT_BRANCH" != "$FEATURE_BRANCH" ]; then
        echo "error: plan '$SLUG' is tracked by git, so its archive move must be committed on '$FEATURE_BRANCH' to land with the PR." >&2
        echo "Check out '$FEATURE_BRANCH' first (currently on '$CURRENT_BRANCH')." >&2
        exit 1
    fi
    if ! command -v gh >/dev/null 2>&1; then
        echo "error: gh (GitHub CLI) is required to confirm the PR is not merged yet" >&2
        exit 1
    fi
    MERGED_JSON=$(gh pr list --head "$FEATURE_BRANCH" --state merged --json url --limit 1 2>/dev/null || echo '[]')
    if [ "$MERGED_JSON" != "[]" ] && [ -n "$MERGED_JSON" ]; then
        merged_url=$(echo "$MERGED_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["url"])')
        echo "error: the PR for '$FEATURE_BRANCH' is already merged ($merged_url), so an archive commit on it can't land." >&2
        echo "Archive before merging, or commit the move through a follow-up PR." >&2
        exit 1
    fi
fi

# --- Move plan dir ---

ARCHIVE_ROOT="$PLANS_DIR/archive"
mkdir -p "$ARCHIVE_ROOT"

ARCHIVE_BASE="$(date -u +%F)-$SLUG"
DEST="$ARCHIVE_ROOT/$ARCHIVE_BASE"
suffix=2
while [ -e "$DEST" ]; do
    DEST="$ARCHIVE_ROOT/$ARCHIVE_BASE-$suffix"
    suffix=$((suffix + 1))
done

mv "$PLAN_DIR" "$DEST"

# --- Report ---

FROM_REL="${PLAN_DIR#"$REPO_ROOT"/}"
TO_REL="${DEST#"$REPO_ROOT"/}"

echo "archived=$SLUG"
echo "from=$FROM_REL"
echo "to=$TO_REL"
echo "tracked=$TRACKED"
echo "branch=$FEATURE_BRANCH"
