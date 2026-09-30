#!/usr/bin/env python3
"""
Read the Branch field from a plan's PLAN.md.

Usage:
    get_plan_branch.py <slug> [--root <path>]

Prints the value of `Branch:` from docs/artifacts/plans/<slug>/PLAN.md, or an empty
line if the field is absent. Exit 0 in both cases — caller decides what to do
with empty output. Exit 1 only if PLAN.md is missing.
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
    parser = argparse.ArgumentParser(description="Read Branch field from PLAN.md.")
    parser.add_argument("slug")
    parser.add_argument("--root")
    args = parser.parse_args()

    root = find_project_root(args.root)
    plan_md = root / "docs" / "artifacts" / "plans" / args.slug / "PLAN.md"
    if not plan_md.is_file():
        print(f"error: plan not found: {plan_md}", file=sys.stderr)
        return 1

    for line in plan_md.read_text().splitlines():
        m = re.match(r"^Branch:\s*(\S+)\s*$", line)
        if m:
            print(m.group(1).strip())
            return 0
    print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
