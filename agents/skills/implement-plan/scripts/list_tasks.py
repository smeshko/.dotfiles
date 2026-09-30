#!/usr/bin/env python3
"""
List tasks in a plan with their checkbox state from PLAN.md and the
matching task file under tasks/.

Usage:
    list_tasks.py <slug> [--root <path>]

Prints one task per line, tab-separated:
    <task-id>\t<done|pending>\t<task-file-relative-path>\t<title>

Order matches the appearance order in PLAN.md's "## Tasks" section, which
is the dependency-respecting implementation order.
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


TASK_LINE = re.compile(r"^- \[(?P<box>[ xX])\]\s+(?P<id>TASK-\d+):\s+(?P<title>.+?)(?:\s+\(depends on [^)]+\))?\s*$")


def main() -> int:
    parser = argparse.ArgumentParser(description="List tasks for a plan.")
    parser.add_argument("slug")
    parser.add_argument("--root")
    args = parser.parse_args()

    root = find_project_root(args.root)
    plan_dir = root / "docs" / "artifacts" / "plans" / args.slug
    plan_md = plan_dir / "PLAN.md"
    if not plan_md.is_file():
        print(f"error: plan not found: {plan_md}", file=sys.stderr)
        return 1

    tasks_dir = plan_dir / "tasks"
    task_files: dict[str, Path] = {}
    if tasks_dir.is_dir():
        for path in tasks_dir.glob("TASK-*.md"):
            m = re.match(r"(TASK-\d+)-", path.name)
            if m:
                task_files[m.group(1)] = path

    in_tasks_section = False
    for line in plan_md.read_text().splitlines():
        if line.startswith("## Tasks"):
            in_tasks_section = True
            continue
        if in_tasks_section and line.startswith("## "):
            break
        if not in_tasks_section:
            continue
        m = TASK_LINE.match(line)
        if not m:
            continue
        task_id = m.group("id")
        done = "done" if m.group("box").lower() == "x" else "pending"
        title = m.group("title").strip()
        task_path = task_files.get(task_id)
        rel = task_path.relative_to(root) if task_path else ""
        print(f"{task_id}\t{done}\t{rel}\t{title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
