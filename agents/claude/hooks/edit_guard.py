#!/usr/bin/env python3
"""PreToolUse[Edit|Write]: protect Ivo's uncommitted manual edits from being clobbered.

Denies the FIRST edit to a file that (a) has uncommitted changes per git and
(b) was not touched by this session (touch-log kept by touch_log.py) and
(c) has not been acknowledged via ack_file.py. Fail-open on any error.
"""
import json, os, subprocess, sys

try:
    data = json.load(sys.stdin)
    path = (data.get("tool_input") or {}).get("file_path", "")
    sid = data.get("session_id", "nosession")
    if not path or not os.path.exists(path):
        sys.exit(0)  # new file — nothing to clobber
    log = f"/tmp/claude-touched-{sid}.txt"
    if os.path.exists(log) and path in open(log).read().splitlines():
        sys.exit(0)  # this session already owns changes to the file
    r = subprocess.run(["git", "status", "--porcelain", "--", path],
                       cwd=os.path.dirname(path) or ".", capture_output=True, text=True, timeout=5)
    if r.returncode == 0 and r.stdout.strip():
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"STOP: {path} has uncommitted changes this session did not make — likely Ivo's manual edits. "
                f"1) Run `git diff -- {path}` and read them. 2) Re-plan your edit to PRESERVE them. "
                f"3) Acknowledge with: python3 ~/.claude/scripts/hooks/ack_file.py {log} {path}  then retry.")}}))
except Exception:
    pass
sys.exit(0)
