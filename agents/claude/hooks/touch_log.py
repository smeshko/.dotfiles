#!/usr/bin/env python3
"""PostToolUse[Edit|Write]: record files this session has edited, so edit_guard skips them."""
import json, sys

try:
    data = json.load(sys.stdin)
    path = (data.get("tool_input") or {}).get("file_path", "")
    sid = data.get("session_id", "nosession")
    if path:
        with open(f"/tmp/claude-touched-{sid}.txt", "a") as f:
            f.write(path + "\n")
except Exception:
    pass
sys.exit(0)
