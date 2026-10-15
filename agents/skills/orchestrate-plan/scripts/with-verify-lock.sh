#!/bin/sh
# Usage: with-verify-lock.sh <lock-dir> <lane> <command...>
# Runs <command> while holding a machine-wide lock, so only one lane runs the
# full gate (or a push, whose hook runs it) at a time. Parallel full suites
# starve each other and turn timing-sensitive tests red.
# The lock is stale only when its holder's pid is dead: a gate under load can
# run for an hour, so an age rule breaks live locks. On exit it removes the
# lock only while it is still the holder.
LOCK="$1/verify.lock"
lane="$2"
shift 2
while ! mkdir "$LOCK" 2>/dev/null; do
  pid=$(cut -d' ' -f2 "$LOCK/holder" 2>/dev/null)
  case "$pid" in
    ''|*[!0-9]*)
      # a holder without a pid (an older copy of this script, or a holder
      # still writing its file): stale only after 90 minutes
      [ -n "$(find "$LOCK" -maxdepth 0 -mmin +90 2>/dev/null)" ] && { rm -rf "$LOCK"; continue; } ;;
    *)
      kill -0 "$pid" 2>/dev/null || { rm -rf "$LOCK"; continue; } ;;
  esac
  sleep 15
done
echo "$lane $$ $(date +%H:%M:%S)" > "$LOCK/holder"
release() {
  [ "$(cut -d' ' -f2 "$LOCK/holder" 2>/dev/null)" = "$$" ] && rm -rf "$LOCK"
}
trap release EXIT
# The command runs as a child so a TERM reaches the trap at once, stops the
# command, and frees the lock, instead of waiting for the command to finish.
"$@" &
child=$!
trap 'kill "$child" 2>/dev/null; exit 143' INT TERM
wait "$child"
