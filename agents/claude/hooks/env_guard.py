#!/usr/bin/env python3
"""PreToolUse[Read]: deny reading .env secrets (allows .env.example/.sample/.template). Fail-open."""
import json, os, re, sys

try:
    data = json.load(sys.stdin)
    path = (data.get("tool_input") or {}).get("file_path", "")
    base = os.path.basename(path)
    if re.match(r"^\.env(\..+)?$", base) and not re.search(r"\.(example|sample|template|dist)$", base):
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "Blocked: never read .env files. Ask Ivo for the specific value you need."}}))
except Exception:
    pass
sys.exit(0)
