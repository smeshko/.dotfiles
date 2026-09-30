#!/usr/bin/env python3
"""PreToolUse[Bash]: deny sweep-staging (git add -A / --all / bare .). Fail-open."""
import json, re, sys

def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}}))
    sys.exit(0)

try:
    data = json.load(sys.stdin)
    cmd = (data.get("tool_input") or {}).get("command", "")
    # every `git add` segment in the command (handles && ; | chains)
    for m in re.finditer(r"\bgit\s+add\s+([^;&|]*)", cmd):
        args = m.group(1).split()
        if any(a in ("-A", "--all", ".") for a in args):
            deny("Blocked: sweep-staging (`git add -A/--all/.`) is banned — stage explicit paths only (git add <paths>).")
except Exception:
    pass
sys.exit(0)
