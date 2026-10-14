#!/bin/sh
# Usage: model_audit.sh <label>=<transcript> ...
# Counts which model produced each subagent's messages, from the transcript's
# metadata only (never its content). <transcript> is the output_file a spawn
# result names. A stage whose top model is not the one its skill asks for ran
# on the session's fallback subagent model.
for arg in "$@"; do
  label="${arg%%=*}"
  file="${arg#*=}"
  top=$(grep -oE '"model":"claude-[^"]+"' "$file" 2>/dev/null | sort | uniq -c | sort -rn \
    | awk '{gsub(/"model":|"/,"",$2); printf "%s %s, ", $2, $1}')
  echo "$label: ${top:-no model fields}"
done
