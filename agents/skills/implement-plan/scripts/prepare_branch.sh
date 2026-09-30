#!/usr/bin/env bash
#
# Plan-specific orchestrator: prepare a clean branch for implementing a plan.
#
# Usage: prepare_branch.sh <slug> <prefix> [<linear-id>] [--base <branch>]
#
# When <linear-id> (e.g. "abc-42") is given, it is lowercased and embedded in the
# branch as <prefix>/<linear-id>-<slug> so Linear's GitHub integration links the
# issue (In Progress on push, Done on merge). Without it, the branch is the
# original <prefix>/<slug>.
#
# The base branch defaults to `staging`; pass --base to cut from a different
# integration branch.
#
# Steps:
#   1. Snapshot docs/artifacts/plans/<slug>/ to a tempdir so the plan survives the
#      branch swap (the stash in step 2 would otherwise sweep it up).
#   2. Stash any uncommitted/untracked changes with a labelled message, so
#      the working tree is clean for the create-branch skill.
#   3. Delegate branch creation to the create-branch skill's script, with
#      --base <resolved-base>.
#   4. Restore the plan directory from the snapshot onto the new branch.
#
# Final stdout on success:
#   branch=<prefix>/<slug>
#   base=<resolved-base>
#   stashed=<0|1>
#   stash_ref=stash@{N}                 # only when stashed=1
#
# On failure prints recovery hints (snapshot path, stash ref) to stderr.

set -euo pipefail

BASE_BRANCH=""
POSITIONAL=()
while [ $# -gt 0 ]; do
    case "$1" in
        --base)
            [ $# -ge 2 ] || { echo "error: --base requires a value" >&2; exit 2; }
            BASE_BRANCH="$2"
            shift 2
            ;;
        --*)
            echo "error: unknown flag '$1'" >&2
            exit 2
            ;;
        *)
            POSITIONAL+=("$1")
            shift
            ;;
    esac
done

if [ "${#POSITIONAL[@]}" -lt 2 ] || [ "${#POSITIONAL[@]}" -gt 3 ]; then
    echo "usage: prepare_branch.sh <slug> <prefix> [<linear-id>] [--base <branch>]" >&2
    exit 2
fi

SLUG="${POSITIONAL[0]}"
PREFIX="${POSITIONAL[1]}"
LINEAR_ID="${POSITIONAL[2]:-}"

if ! [[ "$PREFIX" =~ ^[a-z][a-z0-9-]*$ ]]; then
    echo "error: prefix must be lowercase letters/digits/hyphens, got '$PREFIX'" >&2
    exit 1
fi

if ! [[ "$SLUG" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
    echo "error: slug must be lowercase letters/digits/hyphens, got '$SLUG'" >&2
    exit 1
fi

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || {
    echo "error: not inside a git repository" >&2
    exit 1
}

BASE_BRANCH="${BASE_BRANCH:-staging}"

PLAN_DIR="$ROOT/docs/artifacts/plans/$SLUG"
if [ ! -d "$PLAN_DIR" ]; then
    echo "error: plan directory not found: $PLAN_DIR" >&2
    exit 1
fi

find_create_branch() {
    local candidates=(
        "$ROOT/.claude/skills/create-branch/scripts/create_branch.sh"
        "$HOME/.claude/skills/create-branch/scripts/create_branch.sh"
    )
    for c in "${candidates[@]}"; do
        if [ -x "$c" ]; then
            echo "$c"
            return 0
        fi
    done
    return 1
}

CREATE_BRANCH=$(find_create_branch) || {
    echo "error: create-branch skill script not found in project (.claude/skills/create-branch/) or user (~/.claude/skills/create-branch/)" >&2
    exit 1
}

BRANCH="$PREFIX/$SLUG"
if [ -n "$LINEAR_ID" ]; then
    # Lowercase so the team key matches Linear's case-sensitive branch linking.
    LINEAR_ID=$(printf '%s' "$LINEAR_ID" | tr '[:upper:]' '[:lower:]')
    if ! [[ "$LINEAR_ID" =~ ^[a-z][a-z0-9]*-[0-9]+$ ]]; then
        echo "error: linear-id must look like 'abc-42', got '$LINEAR_ID'" >&2
        exit 1
    fi
    # Embedding the issue identifier lets Linear's GitHub integration move the
    # issue to In Progress on push and Done on merge — no MCP call needed.
    BRANCH="$PREFIX/$LINEAR_ID-$SLUG"
fi

ORIGINAL_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || git rev-parse HEAD)
STASHED=0
STASH_REF=""
PLAN_SNAPSHOT=""

on_error() {
    local code=$?
    if [ -n "$PLAN_SNAPSHOT" ] && [ -d "$PLAN_SNAPSHOT" ]; then
        echo "" >&2
        echo "recovery: plan snapshot preserved at $PLAN_SNAPSHOT" >&2
    fi
    if [ "$STASHED" = "1" ]; then
        echo "recovery: your work is stashed at $STASH_REF" >&2
        echo "  restore with: git checkout $ORIGINAL_BRANCH && git stash pop $STASH_REF" >&2
    fi
    exit "$code"
}
trap on_error ERR

PLAN_SNAPSHOT=$(mktemp -d -t implement-plan.XXXXXX)
cp -R "$PLAN_DIR/." "$PLAN_SNAPSHOT/"

if [ -n "$(git status --porcelain)" ]; then
    DATE=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
    MSG="implement-plan: prep for $BRANCH @ $DATE"
    git stash push --include-untracked --message "$MSG" >/dev/null
    STASHED=1
    STASH_REF=$(git stash list --format='%gd %s' | grep -F "$MSG" | head -n1 | awk '{print $1}')
    echo "stashed: '$MSG' (recover with: git stash pop $STASH_REF)" >&2
fi

bash "$CREATE_BRANCH" "$BRANCH" --base "$BASE_BRANCH"

rm -rf "$PLAN_DIR"
mkdir -p "$(dirname "$PLAN_DIR")"
cp -R "$PLAN_SNAPSHOT/." "$PLAN_DIR/"
rm -rf "$PLAN_SNAPSHOT"
PLAN_SNAPSHOT=""

echo "branch=$BRANCH"
echo "base=$BASE_BRANCH"
echo "stashed=$STASHED"
if [ "$STASHED" = "1" ]; then
    echo "stash_ref=$STASH_REF"
fi
