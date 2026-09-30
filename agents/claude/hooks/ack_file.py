#!/usr/bin/env python3
"""Acknowledge a manually-edited file after reading its diff: unlocks edit_guard for it."""
import sys
log, path = sys.argv[1], sys.argv[2]
with open(log, "a") as f:
    f.write(path + "\n")
print(f"acknowledged: {path}")
