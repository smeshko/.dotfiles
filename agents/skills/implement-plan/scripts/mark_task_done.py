#!/usr/bin/env python3
"""
Check the box for a task in PLAN.md.

Usage:
    mark_task_done.py <slug> <task-id> [--root <path>]

Rewrites the matching `- [ ] TASK-NNN: ...` line to `- [x] TASK-NNN: ...`.
Idempotent: if the box is already checked, exits 0 without modification.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def find_project_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return Path(out.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd().resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Mark a task as done in PLAN.md.")
    parser.add_argument("slug")
    parser.add_argument("task_id")
    parser.add_argument("--root")
    args = parser.parse_args()

    if not re.match(r"^TASK-\d+$", args.task_id):
        print(f"error: task id must match TASK-NNN, got {args.task_id!r}", file=sys.stderr)
        return 1

    root = find_project_root(args.root)
    plan_md = root / "docs" / "artifacts" / "plans" / args.slug / "PLAN.md"
    if not plan_md.is_file():
        print(f"error: plan not found: {plan_md}", file=sys.stderr)
        return 1

    text = plan_md.read_text()
    pattern = re.compile(
        rf"^(- \[)(?P<box>[ xX])(\]\s+{re.escape(args.task_id)}:.*)$",
        re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        print(f"error: task {args.task_id} not found in {plan_md}", file=sys.stderr)
        return 1

    if match.group("box").lower() == "x":
        print(f"{args.task_id} already checked")
        return 0

    new_text = pattern.sub(r"\1x\3", text, count=1)
    plan_md.write_text(new_text)
    print(f"{args.task_id} checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
