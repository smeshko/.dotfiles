#!/usr/bin/env python3
"""
Create the epics index at docs/artifacts/epics/EPICS.md if it does not exist.

Usage:
    init_epics_index.py [--project <name>] [--root <path>]

Args:
    --project  Project name to stamp into the index header. Defaults to the
               repo's top-level directory name.
    --root     Project root. Defaults to the git toplevel; falls back to CWD.

Creates:
    <root>/docs/artifacts/epics/EPICS.md   (only if absent)

Idempotent: if EPICS.md already exists, prints its path and exits 0 without
touching it. On creation prints the path.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REFERENCES = Path(__file__).resolve().parent.parent / "references"
INDEX_TEMPLATE = REFERENCES / "template-epics-index.md"


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
    parser = argparse.ArgumentParser(description="Initialise the epics index.")
    parser.add_argument("--project")
    parser.add_argument("--root")
    args = parser.parse_args()

    root = find_project_root(args.root)
    epics_dir = root / "docs" / "artifacts" / "epics"
    index = epics_dir / "EPICS.md"

    if index.is_file():
        print(f"exists: {index.relative_to(root)}")
        return 0

    project = args.project or root.name
    epics_dir.mkdir(parents=True, exist_ok=True)
    body = INDEX_TEMPLATE.read_text().replace("<project>", project, 1)
    index.write_text(body)
    print(f"created: {index.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
