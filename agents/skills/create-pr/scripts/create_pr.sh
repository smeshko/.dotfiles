#!/usr/bin/env bash
#
# Create a GitHub pull request from the current branch.
#
# Usage:
#   create_pr.sh "<title>" "<body>" [--base <base-branch>] [--draft]
#
# Pushes the branch if it has no upstream or is ahead of remote, then runs
# `gh pr create`. On success prints the PR URL.
#
# Body may be the empty string "" to omit (`gh pr create` will open with
# an empty body in that case).

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "usage: create_pr.sh \"<title>\" [\"<body>\"] [--base <base>] [--draft]" >&2
    exit 2
fi

TITLE="$1"
shift

BODY=""
if [ $# -gt 0 ] && [[ "$1" != --* ]]; then
    BODY="$1"
    shift
fi

BASE=""
DRAFT=0
while [ $# -gt 0 ]; do
    case "$1" in
        --base)
            [ $# -ge 2 ] || { echo "error: --base requires a value" >&2; exit 2; }
            BASE="$2"
            shift 2
            ;;
        --draft)
            DRAFT=1
            shift
            ;;
        *)
            echo "error: unknown argument '$1'" >&2
            exit 2
            ;;
    esac
done

if [ -z "$TITLE" ]; then
    echo "error: title is required" >&2
    exit 2
fi

if ! command -v gh >/dev/null 2>&1; then
    echo "error: gh (GitHub CLI) is required" >&2
    exit 1
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "HEAD" ]; then
    echo "error: detached HEAD" >&2
    exit 1
fi

if ! git rev-parse --verify --quiet "@{u}" >/dev/null 2>&1; then
    git push -u origin "$BRANCH" >&2
elif [ "$(git rev-list --count "@{u}..HEAD")" -gt 0 ]; then
    git push >&2
fi

ARGS=(pr create --title "$TITLE" --body "$BODY")
if [ -n "$BASE" ]; then
    ARGS+=(--base "$BASE")
fi
if [ "$DRAFT" = "1" ]; then
    ARGS+=(--draft)
fi

gh "${ARGS[@]}"
