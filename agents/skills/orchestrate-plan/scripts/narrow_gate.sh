#!/bin/sh
# Usage: narrow_gate.sh <base-sha> [timeout-ms]   (run from the lane's worktree)
# The local gate for repos whose full suite is CI's job: typecheck, lint, and only the
# test files the branch touches plus the test files mirroring each changed src/ file
# (src/a/b.ts -> test/a/b.test.ts). Prefer the repo's own narrow gate when AGENTS.md
# names one; this is the fallback. Prints one result line per step and exits non-zero
# on the first red step. Package scripts typecheck, lint and test are assumed (Bun);
# without them it prints the selection and exits 2.
base="$1"
timeout="${2:-60000}"
[ -n "$base" ] || { echo "usage: narrow_gate.sh <base-sha> [timeout-ms]" >&2; exit 64; }
files=$({
  git diff --name-only "$base"...HEAD -- 'test/*.test.ts'
  git diff --name-only "$base"...HEAD -- 'src/*.ts' | sed -e 's#^src/#test/#' -e 's#\.ts$#.test.ts#'
} | sort -u | while read -r f; do [ -f "$f" ] && echo "$f"; done)
count=$(printf '%s\n' "$files" | grep -c .)
echo "selected=$count test files"
for s in typecheck lint test; do
  grep -q "\"$s\":" package.json 2>/dev/null || { printf '%s\n' "$files"; echo "no package script '$s'" >&2; exit 2; }
done
bun run typecheck >/dev/null 2>&1; r=$?; echo "typecheck=$r"; [ $r -eq 0 ] || exit $r
bun run lint >/dev/null 2>&1; r=$?; echo "lint=$r"; [ $r -eq 0 ] || exit $r
if [ "$count" -eq 0 ]; then echo "tests=skipped (no affected test files)"; exit 0; fi
out=$(bun run test --timeout "$timeout" $files 2>&1); r=$?
printf '%s\n' "$out" | grep -E '^ *[0-9]+ (pass|fail)$|^\(fail\)' | head -20
echo "tests=$r"
exit $r
