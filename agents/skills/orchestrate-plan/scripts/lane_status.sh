#!/bin/sh
# Usage: lane_status.sh <lock-dir> <base-sha> <lane>=<worktree>[:<plan-dir>[:<transcript>]] ...
# One line per lane: branch, commits since base, unpushed commits, dirty files,
# ticked PLAN.md boxes, the latest commit's age and subject, and the age in
# minutes of the stage agent's transcript (its output file): a stale transcript
# with no running process for the lane is a stall. Then the verify lock holder,
# the load average, and every running test suite or push with its directory,
# so suites outside this run's worktrees show as foreign load.
lockdir="$1"
base="$2"
shift 2
now=$(date +%s)
for arg in "$@"; do
  lane="${arg%%=*}"
  rest="${arg#*=}"
  wt="${rest%%:*}"
  plan=""
  transcript=""
  if [ "$rest" != "$wt" ]; then
    rest="${rest#*:}"
    plan="${rest%%:*}"
    [ "$rest" != "$plan" ] && transcript="${rest#*:}"
  fi
  branch=$(git -C "$wt" rev-parse --abbrev-ref HEAD 2>/dev/null)
  ahead=$(git -C "$wt" rev-list --count "$base"..HEAD 2>/dev/null)
  unpushed=$(git -C "$wt" rev-list --count '@{u}..HEAD' 2>/dev/null || echo "no-upstream")
  dirty=$(git -C "$wt" status --short 2>/dev/null | grep -vc '^?? docs$')
  ticked="-"
  [ -n "$plan" ] && [ -f "$plan/PLAN.md" ] && ticked=$(grep -c '^- \[x\]' "$plan/PLAN.md")
  idle="-"
  if [ -n "$transcript" ] && [ -e "$transcript" ]; then
    idle="$(( (now - $(stat -L -f %m "$transcript" 2>/dev/null || stat -L -c %Y "$transcript")) / 60 ))m"
  fi
  last=$(git -C "$wt" log -1 --format='%cr | %s' 2>/dev/null | cut -c1-60)
  echo "$lane $branch +$ahead unpushed=$unpushed dirty=$dirty ticked=$ticked idle=$idle | $last"
done
echo "lock: $(cat "$lockdir/verify.lock/holder" 2>/dev/null || echo free)"
uptime | sed 's/.*load/load/'
for pid in $(pgrep -f 'git push|bun test|bun run (test|verify)|npm (run )?test|pytest'); do
  cwd=$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')
  echo "  $(ps -o etime= -p "$pid" | tr -d ' ') $cwd $(ps -o command= -p "$pid" | cut -c1-60)"
done | head -12
