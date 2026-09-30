#!/usr/bin/env python3
"""
List all plans under docs/artifacts/plans/ with their slug and Status field.

Usage:
    list_plans.py [--root <path>]

Prints one plan per line as tab-separated:
    <slug>\t<status>\t<title>

Use this to resolve a freeform user input (slug substring, title fragment)
to a concrete plan directory.
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


def parse_plan(plan_md: Path) -> tuple[str, str]:
    """Return (status, title) from a PLAN.md file."""
    status = "unknown"
    title = ""
    for line in plan_md.read_text().splitlines():
        if not title:
            m = re.match(r"#\s+Plan:\s+(.+)", line)
            if m:
                title = m.group(1).strip()
        m = re.match(r"Status:\s*(\S+)", line)
        if m:
            status = m.group(1).strip()
            break
    return status, title


def main() -> int:
    parser = argparse.ArgumentParser(description="List plans.")
    parser.add_argument("--root")
    args = parser.parse_args()

    root = find_project_root(args.root)
    plans_dir = root / "docs" / "artifacts" / "plans"
    if not plans_dir.is_dir():
        return 0

    for child in sorted(plans_dir.iterdir()):
        plan_md = child / "PLAN.md"
        if not plan_md.is_file():
            continue
        status, title = parse_plan(plan_md)
        print(f"{child.name}\t{status}\t{title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
