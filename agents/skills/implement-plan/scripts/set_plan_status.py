#!/usr/bin/env python3
"""
Update the Status field at the top of PLAN.md.

Usage:
    set_plan_status.py <slug> <status> [--root <path>]

<status> must be one of: draft, ready, tests-ready, in-progress, done.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

VALID_STATUS = ("draft", "ready", "tests-ready", "in-progress", "done")


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
    parser = argparse.ArgumentParser(description="Set Status field in PLAN.md.")
    parser.add_argument("slug")
    parser.add_argument("status", choices=VALID_STATUS)
    parser.add_argument("--root")
    args = parser.parse_args()

    root = find_project_root(args.root)
    plan_md = root / "docs" / "artifacts" / "plans" / args.slug / "PLAN.md"
    if not plan_md.is_file():
        print(f"error: plan not found: {plan_md}", file=sys.stderr)
        return 1

    text = plan_md.read_text()
    new_text, n = re.subn(
        r"^Status:\s*.*$",
        f"Status: {args.status}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n == 0:
        print(f"error: no Status line found in {plan_md}", file=sys.stderr)
        return 1
    plan_md.write_text(new_text)
    print(f"Status: {args.status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
