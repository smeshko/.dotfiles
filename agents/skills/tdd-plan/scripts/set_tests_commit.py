#!/usr/bin/env python3
"""
Write the Tests-commit field into a plan's PLAN.md.

Usage:
    set_tests_commit.py <slug> <sha> [--root <path>]

Resolves <sha> to a full commit sha and writes `Tests-commit: <sha>` right
after the Branch line (or the Status line when there is no Branch line),
replacing an existing Tests-commit line. This is the baseline check_tests.py
holds every later commit to.
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
    parser = argparse.ArgumentParser(description="Set Tests-commit field in PLAN.md.")
    parser.add_argument("slug")
    parser.add_argument("sha")
    parser.add_argument("--root")
    args = parser.parse_args()

    root = find_project_root(args.root)
    plan_md = root / "docs" / "artifacts" / "plans" / args.slug / "PLAN.md"
    if not plan_md.is_file():
        print(f"error: plan not found: {plan_md}", file=sys.stderr)
        return 1

    r = subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"{args.sha}^{{commit}}"],
                       cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"error: not a commit: {args.sha}", file=sys.stderr)
        return 1
    new_line = f"Tests-commit: {r.stdout.strip()}"

    text = plan_md.read_text()
    new_text, n = re.subn(r"^Tests-commit:\s*.*$", new_line, text, count=1, flags=re.MULTILINE)
    for anchor in (r"^Branch:\s*.*$", r"^Status:\s*.*$"):
        if n:
            break
        new_text, n = re.subn(f"({anchor})", r"\1\n" + new_line, text, count=1, flags=re.MULTILINE)
    if n == 0:
        print(f"error: no Branch or Status line found in {plan_md}", file=sys.stderr)
        return 1

    plan_md.write_text(new_text)
    print(new_line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
