#!/usr/bin/env python3
"""
Write the Branch field into a plan's PLAN.md.

Usage:
    set_plan_branch.py <slug> <branch> [--root <path>]

Inserts `Branch: <branch>` immediately after the Status line. If a Branch line
already exists, replaces it. Exits 1 if PLAN.md or the Status line is missing.
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
    parser = argparse.ArgumentParser(description="Set Branch field in PLAN.md.")
    parser.add_argument("slug")
    parser.add_argument("branch")
    parser.add_argument("--root")
    args = parser.parse_args()

    root = find_project_root(args.root)
    plan_md = root / "docs" / "artifacts" / "plans" / args.slug / "PLAN.md"
    if not plan_md.is_file():
        print(f"error: plan not found: {plan_md}", file=sys.stderr)
        return 1

    text = plan_md.read_text()
    new_branch_line = f"Branch: {args.branch}"

    new_text, n = re.subn(
        r"^Branch:\s*.*$",
        new_branch_line,
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n == 0:
        new_text, n = re.subn(
            r"(^Status:\s*.*$)",
            r"\1\n" + new_branch_line,
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if n == 0:
            print(f"error: no Status line found in {plan_md}", file=sys.stderr)
            return 1

    plan_md.write_text(new_text)
    print(f"Branch: {args.branch}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
