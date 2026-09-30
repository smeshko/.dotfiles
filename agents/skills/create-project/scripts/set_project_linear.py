#!/usr/bin/env python3
"""
Record a Linear Project id (and URL) on a project charter, and mirror it into the
PROJECTS.md index row.

Usage:
    set_project_linear.py <project-slug> --id <linear-project-id> [--url <url>]
                          [--root <path>]

Args:
    <project-slug>  The project charter slug (docs/artifacts/projects/<slug>.md).
    --id            The Linear Project id (UUID or slugId) returned by the MCP
                    create/save call.
    --url           Optional Linear Project URL, shown in the index row.
    --root          Project root. Defaults to the git toplevel; falls back to CWD.

Writes:
    - Charter header: `linear_project: <id>` (replaces the placeholder).
    - PROJECTS.md row: the Linear cell becomes `[link](<url>)` when --url is
      given, else the raw id.

Idempotent. Exits 1 if the charter is missing.
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


def set_index_linear_cell(index: Path, project_slug: str, cell: str) -> None:
    if not index.is_file():
        return
    needle = f"](./{project_slug}.md)"
    out = []
    for line in index.read_text().splitlines():
        if line.lstrip().startswith("|") and needle in line:
            cells = line.split("|")
            # cells: ['', ' [title](./slug.md) ', ' epics ', ' linear ', ' status ', '']
            if len(cells) >= 4:
                cells[3] = f" {cell} "
                line = "|".join(cells)
        out.append(line)
    index.write_text("\n".join(out) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Record Linear Project id on a charter.")
    parser.add_argument("project")
    parser.add_argument("--id", required=True)
    parser.add_argument("--url")
    parser.add_argument("--root")
    args = parser.parse_args()

    root = find_project_root(args.root)
    charter = root / "docs" / "artifacts" / "projects" / f"{args.project}.md"
    if not charter.is_file():
        print(f"error: project charter not found: {charter}", file=sys.stderr)
        return 1

    text = charter.read_text()
    new_text, n = re.subn(
        r"^linear_project:.*$",
        f"linear_project: {args.id}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n == 0:
        new_text, n = re.subn(
            r"^(Created:.*)$",
            r"\1\n" + f"linear_project: {args.id}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if n == 0:
            print(f"error: no linear_project/Created line to anchor in {charter}", file=sys.stderr)
            return 1
    charter.write_text(new_text)

    cell = f"[link]({args.url})" if args.url else args.id
    set_index_linear_cell(root / "docs" / "artifacts" / "projects" / "PROJECTS.md",
                          args.project, cell)

    print(f"linear_project: {args.id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
