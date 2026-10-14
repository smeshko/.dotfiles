#!/bin/sh
# Usage: with-verify-lock.sh <lock-dir> <lane> <command...>
# Runs <command> while holding a machine-wide lock, so only one lane runs the
# full gate (or a push, whose hook runs it) at a time. Parallel full suites
# starve each other and turn timing-sensitive tests red.
LOCK="$1/verify.lock"
lane="$2"
shift 2
while ! mkdir "$LOCK" 2>/dev/null; do
  # a lock older than 25 minutes is stale: its holder died
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +25 2>/dev/null)" ]; then
    rm -rf "$LOCK"
    continue
  fi
  sleep 15
done
echo "$lane $(date +%H:%M:%S)" > "$LOCK/holder"
trap 'rm -rf "$LOCK"' EXIT INT TERM
"$@"
