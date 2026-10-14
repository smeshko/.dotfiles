#!/bin/sh
# Usage: lane_status.sh <lock-dir> <base-sha> <lane>=<worktree>[:<plan-dir>] ...
# One line per lane: branch, commits since base, unpushed commits, dirty files,
# ticked PLAN.md boxes, and the latest commit's age and subject. Then the verify
# lock holder, the load average, and running test or push processes.
lockdir="$1"
base="$2"
shift 2
for arg in "$@"; do
  lane="${arg%%=*}"
  rest="${arg#*=}"
  wt="${rest%%:*}"
  plan=""
  [ "$rest" != "$wt" ] && plan="${rest#*:}"
  branch=$(git -C "$wt" rev-parse --abbrev-ref HEAD 2>/dev/null)
  ahead=$(git -C "$wt" rev-list --count "$base"..HEAD 2>/dev/null)
  unpushed=$(git -C "$wt" rev-list --count '@{u}..HEAD' 2>/dev/null || echo "no-upstream")
  dirty=$(git -C "$wt" status --short 2>/dev/null | grep -vc '^?? docs$')
  ticked="-"
  [ -n "$plan" ] && [ -f "$plan/PLAN.md" ] && ticked=$(grep -c '^- \[x\]' "$plan/PLAN.md")
  last=$(git -C "$wt" log -1 --format='%cr | %s' 2>/dev/null | cut -c1-70)
  echo "$lane $branch +$ahead unpushed=$unpushed dirty=$dirty ticked=$ticked | $last"
done
echo "lock: $(cat "$lockdir/verify.lock/holder" 2>/dev/null || echo free)"
uptime | sed 's/.*load/load/'
ps -axo etime,command | grep -E 'git push|bun (run )?(test|verify)|npm (run )?test|pytest' \
  | grep -v grep | cut -c1-110 | head -8
