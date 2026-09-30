#!/usr/bin/env python3
"""
Append a new task to an existing plan.

Usage:
    add_task.py <slug> --type <impl|checklist> --title "<title>"
                       [--depends TASK-001[,TASK-002]] [--root <path>]

Creates:
    <root>/docs/artifacts/plans/<slug>/tasks/TASK-<NNN>-<title-slug>.md

Appends:
    "- [ ] TASK-<NNN>: <title>[ (depends on ...)]"  →  PLAN.md (end of file)

On success prints the assigned task id (e.g. TASK-003) on stdout.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REFERENCES = Path(__file__).resolve().parent.parent / "references"
TEMPLATES = {
    "impl": REFERENCES / "template-task-implementation.md",
    "checklist": REFERENCES / "template-task-checklist.md",
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


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


def render_task(template_path: Path, task_id: str, title: str, depends: str | None) -> str:
    body = template_path.read_text()
    body = body.replace("TASK-00X", task_id, 1)
    body = body.replace("<title>", title, 1)
    body = body.replace("TASK-00Y | None", depends or "None", 1)
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
    parser = argparse.ArgumentParser(description="Append a new task to an existing plan.")
    parser.add_argument("slug")
    parser.add_argument("--type", required=True, choices=sorted(TEMPLATES.keys()))
    parser.add_argument("--title", required=True)
    parser.add_argument("--depends", help="Comma-separated task ids, e.g. TASK-001,TASK-002")
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
    title_slug = slugify(args.title)
    if not title_slug:
        sys.exit(f"error: could not derive a filename slug from title {args.title!r}")

    task_path = tasks_dir / f"{task_id}-{title_slug}.md"
    if task_path.exists():
        sys.exit(f"error: task file already exists: {task_path}")

    task_path.write_text(render_task(TEMPLATES[args.type], task_id, args.title, args.depends))

    line = f"- [ ] {task_id}: {args.title}"
    if args.depends:
        line += f" (depends on {args.depends})"
    append_task_line(plan_dir / "PLAN.md", line)

    print(task_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
