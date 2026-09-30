#!/usr/bin/env python3
"""
Delete TDD-PENDING sticker lines so pending tests run.

Usage:
    strip_stickers.py [--task TASK-NNN] [--root <path>]

Deletes every line containing `TDD-PENDING` — or, with --task, every line
containing `TDD-PENDING <task-id>` — from tracked and untracked (non-ignored)
files outside docs/artifacts/. Nothing else in the file changes, which is
exactly the edit check_tests.py allows.

Prints `stripped=<n>`, then `  <path>: <n>` per file changed.
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
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if r.returncode != 0:
        print("error: not inside a git repository", file=sys.stderr)
        sys.exit(1)
    return Path(r.stdout.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete TDD-PENDING sticker lines.")
    parser.add_argument("--task", help="only this task's stickers, e.g. TASK-003")
    parser.add_argument("--root")
    args = parser.parse_args()

    if args.task and not re.fullmatch(r"TASK-\d+", args.task):
        print(f"error: --task must look like TASK-003, got {args.task!r}", file=sys.stderr)
        return 2

    root = find_project_root(args.root)
    needle = f"TDD-PENDING {args.task}" if args.task else "TDD-PENDING"
    line_re = re.compile(rf"{re.escape(needle)}\b" if args.task else re.escape(needle))

    r = subprocess.run(
        ["git", "-c", "core.quotePath=false", "grep", "-l", "-I", "--untracked", "-F", needle, "--", ".", ":(exclude)docs/artifacts/"],
        cwd=root, capture_output=True, text=True,
    )
    if r.returncode not in (0, 1):
        print(f"error: git grep: {r.stderr.strip()}", file=sys.stderr)
        return 1

    total, report = 0, []
    for rel in r.stdout.splitlines():
        path = root / rel
        lines = path.read_bytes().decode("utf-8").splitlines(keepends=True)
        kept = [line for line in lines if not line_re.search(line)]
        removed = len(lines) - len(kept)
        if removed:
            path.write_bytes("".join(kept).encode("utf-8"))
            total += removed
            report.append(f"  {rel}: {removed}")

    print(f"stripped={total}")
    for line in report:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
