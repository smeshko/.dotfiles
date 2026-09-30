#!/usr/bin/env python3
"""
Scaffold a new project charter under docs/artifacts/projects/ and add a row to
PROJECTS.md.

Usage:
    init_project.py --title "<title>" [--slug <slug>] [--root <path>]

Args:
    --title   Project title (required). Used to derive --slug when omitted.
    --slug    Override the auto-derived slug.
    --root    Project root. Defaults to the git toplevel; falls back to CWD.

Behaviour:
    - Creates docs/artifacts/projects/PROJECTS.md from the template if absent
      (project name = repo dir name).
    - Writes docs/artifacts/projects/<slug>.md from template-project.md.
    - Appends a row to the "## Projects" table in PROJECTS.md (Epics starts 0,
      Linear "none"; link_epic.py / set_project_linear.py update them).

On success prints (key=value per line):
    project_slug=<slug>
    file=docs/artifacts/projects/<slug>.md
"""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

REFERENCES = Path(__file__).resolve().parent.parent / "references"
PROJECT_TEMPLATE = REFERENCES / "template-project.md"
INDEX_TEMPLATE = REFERENCES / "template-projects-index.md"


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


def ensure_index(projects_dir: Path, project: str) -> Path:
    index = projects_dir / "PROJECTS.md"
    if not index.is_file():
        projects_dir.mkdir(parents=True, exist_ok=True)
        index.write_text(INDEX_TEMPLATE.read_text().replace("<project>", project, 1))
    return index


def append_index_row(index: Path, row: str) -> None:
    lines = index.read_text().splitlines()
    try:
        si = next(i for i, l in enumerate(lines) if l.strip() == "## Projects")
    except StopIteration:
        sys.exit(f"error: '## Projects' section not found in {index}")

    i = si + 1
    while i < len(lines) and not lines[i].lstrip().startswith("|"):
        i += 1
    if i + 1 >= len(lines):
        sys.exit(f"error: malformed projects table in {index}")
    j = i + 2  # skip header + separator
    while j < len(lines) and lines[j].lstrip().startswith("|"):
        j += 1
    lines.insert(j, row)
    index.write_text("\n".join(lines) + "\n")


def render_project(title: str) -> str:
    body = PROJECT_TEMPLATE.read_text()
    today = datetime.date.today().isoformat()
    body = body.replace("<title>", title, 1)
    body = body.replace("YYYY-MM-DD", today, 1)
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a new project.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--slug")
    parser.add_argument("--root")
    args = parser.parse_args()

    slug = args.slug or slugify(args.title)
    if not slug:
        print(f"error: could not derive slug from title {args.title!r}", file=sys.stderr)
        return 1

    root = find_project_root(args.root)
    projects_dir = root / "docs" / "artifacts" / "projects"
    index = ensure_index(projects_dir, root.name)

    charter = projects_dir / f"{slug}.md"
    if charter.exists():
        print(f"error: project charter already exists: {charter}", file=sys.stderr)
        return 1

    charter.write_text(render_project(args.title))

    row = f"| [{args.title}](./{slug}.md) | 0 | none | Planned |"
    append_index_row(index, row)

    print(f"project_slug={slug}")
    print(f"file={charter.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
