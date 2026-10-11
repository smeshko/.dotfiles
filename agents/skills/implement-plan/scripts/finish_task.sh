#!/usr/bin/env bash
#
# Finish one plan task in a single call: check the tests (TDD plans), stage the
# task's files, tick its box in PLAN.md, stage PLAN.md, and commit.
#
# Usage: finish_task.sh <slug> <task-id> "<subject>" ["<body>"] -- [<path>...]
#
#   <subject>  Conventional Commits subject, normally the task's `Suggested commit:`.
#              The branch's ticket reference is appended by create-commit's rules
#              (get_commit_context.sh): `#<ticket>` on a legacy numeric branch,
#              nothing on a Linear-tracked branch.
#   <path>...  Every file this task changed, named explicitly. May be empty for a
#              checklist task that changed no files; PLAN.md is always staged.
#
# Safe to run again after a failed commit: the tick is idempotent.
#
# Prints the test check's output, then on success one line:
#   <task-id> done → <short-sha> <subject>
#
# Exit codes:
#   0  committed
#   1  test violations, a failed step, or nothing to commit
#   2  usage error

set -euo pipefail

usage() {
    echo 'usage: finish_task.sh <slug> <task-id> "<subject>" ["<body>"] -- [<path>...]' >&2
    exit 2
}

HEAD_ARGS=()
while [ "$#" -gt 0 ] && [ "$1" != "--" ]; do
    HEAD_ARGS+=("$1")
    shift
done
[ "${1:-}" = "--" ] || usage
shift
[ "${#HEAD_ARGS[@]}" -ge 3 ] && [ "${#HEAD_ARGS[@]}" -le 4 ] || usage

SLUG="${HEAD_ARGS[0]}"
TASK_ID="${HEAD_ARGS[1]}"
SUBJECT="${HEAD_ARGS[2]}"
BODY="${HEAD_ARGS[3]:-}"

for p in "$@"; do
    case "$p" in
        .|-A|--all)
            echo "error: name each path explicitly; '$p' would sweep-stage" >&2
            exit 2
            ;;
    esac
done

SKILLS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if ! REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null); then
    echo "error: not inside a git repository" >&2
    exit 1
fi
cd "$REPO_ROOT"

PLAN_MD="docs/artifacts/plans/$SLUG/PLAN.md"
if [ ! -f "$PLAN_MD" ]; then
    echo "error: plan not found: $PLAN_MD" >&2
    exit 1
fi

# Prints tdd=none on a plan without a Tests-commit; exits 1 on any violation.
python3 "$SKILLS/tdd-plan/scripts/check_tests.py" "$SLUG"

if [ "$#" -gt 0 ]; then
    git add -- "$@"
fi

python3 "$SKILLS/implement-plan/scripts/mark_task_done.py" "$SLUG" "$TASK_ID" >/dev/null

# A gitignored plan keeps its checkbox local; a tracked one rides the task's commit.
if ! git check-ignore -q -- "$PLAN_MD"; then
    git add -- "$PLAN_MD"
fi

# The ticket rules live in create-commit; read its verdict rather than restate them.
TICKET=$(bash "$SKILLS/create-commit/scripts/get_commit_context.sh" 2>/dev/null \
    | awk '!seen && /^=== TICKET NUMBER ===$/ { getline; print; seen = 1 }' || true)
case "$TICKET" in
    "#"*)
        case "$SUBJECT" in
            *"$TICKET"*) ;;
            *) SUBJECT="$SUBJECT $TICKET" ;;
        esac
        ;;
esac

if git diff --cached --quiet; then
    echo "error: nothing staged for $TASK_ID — name the files it changed after --" >&2
    exit 1
fi

if [ -n "$BODY" ]; then
    bash "$SKILLS/create-commit/scripts/create_commit.sh" "$SUBJECT" "$BODY" >/dev/null
else
    bash "$SKILLS/create-commit/scripts/create_commit.sh" "$SUBJECT" >/dev/null
fi

echo "$TASK_ID done → $(git rev-parse --short HEAD) $SUBJECT"
