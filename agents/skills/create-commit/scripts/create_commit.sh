#!/bin/bash
# Creates a git commit with the provided message.
# Usage: create_commit.sh "<subject>" ["<body>"]
#
# Arguments:
#   $1 - Commit subject line (required)
#   $2 - Commit body (optional)

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: create_commit.sh \"<subject>\" [\"<body>\"]"
  exit 1
fi

SUBJECT="$1"
BODY="${2:-}"

if [ -n "$BODY" ]; then
  git commit -m "$SUBJECT" -m "$BODY"
else
  git commit -m "$SUBJECT"
fi
