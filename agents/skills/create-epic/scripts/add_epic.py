#!/usr/bin/env python3
"""
Scaffold a new epic file under docs/artifacts/epics/ and add a row to EPICS.md.

Usage:
    add_epic.py --title "<title>" [--slug <slug>] [--depends "<deps>"]
                [--root <path>]

Args:
    --title    Epic title (required). Used to derive --slug when omitted.
    --slug     Override the auto-derived slug (without the NN- number prefix).
    --depends  Free-text dependency note, e.g. "Epic 03, Epic 05" or "none".
    --root     Project root. Defaults to the git toplevel; falls back to CWD.

Behaviour:
    - Creates docs/artifacts/epics/EPICS.md from the template if it is missing
      (project name = repo dir name). Run init_epics_index.py first to set a
      custom project name.
    - Assigns the next zero-padded epic number NN (max existing + 1, from 01).
    - Writes docs/artifacts/epics/<NN>-<slug>.md from template-epic.md.
    - Appends a row to the "## Epic status" table in EPICS.md (Phases starts 0;
      add_phase.py bumps it).

On success prints (key=value per line):
    epic=<N>                 # integer, no zero-pad — the token to pass elsewhere
    epic_num=<NN>            # zero-padded
    epic_slug=<NN>-<slug>
    file=docs/artifacts/epics/<NN>-<slug>.md
"""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

REFERENCES = Path(__file__).resolve().parent.parent / "references"
EPIC_TEMPLATE = REFERENCES / "template-epic.md"
INDEX_TEMPLATE = REFERENCES / "template-epics-index.md"


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


def ensure_index(epics_dir: Path, project: str) -> Path:
    index = epics_dir / "EPICS.md"
    if not index.is_file():
        epics_dir.mkdir(parents=True, exist_ok=True)
        index.write_text(INDEX_TEMPLATE.read_text().replace("<project>", project, 1))
    return index


def next_epic_number(epics_dir: Path) -> int:
    nums: list[int] = []
    for path in epics_dir.glob("[0-9][0-9]-*.md"):
        m = re.match(r"(\d+)-", path.name)
        if m:
            nums.append(int(m.group(1)))
    return (max(nums) + 1) if nums else 1


def append_index_row(index: Path, row: str) -> None:
    lines = index.read_text().splitlines()
    try:
        si = next(i for i, l in enumerate(lines) if l.strip() == "## Epic status")
    except StopIteration:
        sys.exit(f"error: '## Epic status' section not found in {index}")

    # First markdown table line after the heading is the header row; the next is
    # the |---| separator; data rows follow.
    i = si + 1
    while i < len(lines) and not lines[i].lstrip().startswith("|"):
        i += 1
    if i + 1 >= len(lines):
        sys.exit(f"error: malformed epic-status table in {index}")
    j = i + 2  # skip header + separator
    while j < len(lines) and lines[j].lstrip().startswith("|"):
        j += 1
    lines.insert(j, row)
    index.write_text("\n".join(lines) + "\n")


def render_epic(num: int, title: str, depends: str) -> str:
    body = EPIC_TEMPLATE.read_text()
    today = datetime.date.today().isoformat()
    body = body.replace("<NN>", f"{num:02d}", 1)   # heading
    body = body.replace("<title>", title, 1)
    body = body.replace("YYYY-MM-DD", today, 1)
    body = body.replace("<depends>", depends, 2)    # "Depends on:" line + bullet
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a new epic.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--slug")
    parser.add_argument("--depends", default="none")
    parser.add_argument("--root")
    args = parser.parse_args()

    slug = args.slug or slugify(args.title)
    if not slug:
        print(f"error: could not derive slug from title {args.title!r}", file=sys.stderr)
        return 1

    root = find_project_root(args.root)
    epics_dir = root / "docs" / "artifacts" / "epics"
    index = ensure_index(epics_dir, root.name)

    num = next_epic_number(epics_dir)
    epic_slug = f"{num:02d}-{slug}"
    epic_path = epics_dir / f"{epic_slug}.md"
    if epic_path.exists():
        print(f"error: epic file already exists: {epic_path}", file=sys.stderr)
        return 1

    epic_path.write_text(render_epic(num, args.title, args.depends))

    deps_cell = args.depends if args.depends and args.depends != "none" else "—"
    row = f"| {num} | [{args.title}](./{epic_slug}.md) | 0 | {deps_cell} | Planned |"
    append_index_row(index, row)

    print(f"epic={num}")
    print(f"epic_num={num:02d}")
    print(f"epic_slug={epic_slug}")
    print(f"file={epic_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
