#!/usr/bin/env python3
"""
Append the final-validation task to an existing plan.

Usage:
    add_final_task.py <slug> [--root <path>]

Creates:
    <root>/docs/artifacts/plans/<slug>/tasks/TASK-<NNN>-final-validation.md

Appends:
    "- [ ] TASK-<NNN>: Final Validation"  →  PLAN.md (end of file)

The task id is the next sequential number after the highest existing
TASK-NNN in the tasks/ directory.

On success prints the assigned task id (e.g. TASK-005) on stdout.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REFERENCES = Path(__file__).resolve().parent.parent / "references"
FINAL_TEMPLATE = REFERENCES / "template-task-final-validation.md"


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


def next_task_number(tasks_dir: Path) -> int:
    nums: list[int] = []
    for path in tasks_dir.glob("TASK-*.md"):
        match = re.match(r"TASK-(\d+)-", path.name)
        if match:
            nums.append(int(match.group(1)))
    return (max(nums) + 1) if nums else 1


def render_final(task_id: str, slug: str) -> str:
    body = FINAL_TEMPLATE.read_text()
    body = body.replace("TASK-00N", task_id, 1)
    body = body.replace("<plan-slug>", slug)
    return body


def append_task_line(plan_md: Path, line: str) -> None:
    content = plan_md.read_text()
    if "## Tasks" not in content:
        sys.exit(f"error: '## Tasks' section not found in {plan_md}")
    content = content.rstrip() + "\n"
    last_line = content.rstrip("\n").rsplit("\n", 1)[-1]
    separator = "" if last_line.lstrip().startswith("- [") else "\n"
    plan_md.write_text(f"{content}{separator}{line}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Append the final-validation task to a plan.")
    parser.add_argument("slug")
    parser.add_argument("--root")
    args = parser.parse_args()

    root = find_project_root(args.root)
    plan_dir = root / "docs" / "artifacts" / "plans" / args.slug
    if not plan_dir.is_dir():
        sys.exit(f"error: plan directory does not exist: {plan_dir}")

    tasks_dir = plan_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)

    task_num = next_task_number(tasks_dir)
    task_id = f"TASK-{task_num:03d}"
    task_path = tasks_dir / f"{task_id}-final-validation.md"
    if task_path.exists():
        sys.exit(f"error: task file already exists: {task_path}")

    task_path.write_text(render_final(task_id, args.slug))
    append_task_line(plan_dir / "PLAN.md", f"- [ ] {task_id}: Final Validation")

    print(task_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
