#!/usr/bin/env python3
"""
Link an epic to a project, both directions, in one call.

Usage:
    link_epic.py <project-slug> --epic <epic> [--root <path>]

Args:
    <project-slug>  The project charter slug (docs/artifacts/projects/<slug>.md).
    --epic          Epic id or slug: "13", "E13", "13-home-screen-redesign".
    --root          Project root. Defaults to the git toplevel; falls back to CWD.

Writes both sides of the link:
    - Epic file header: the `Project:` field becomes `Project: <project-slug>`
      (inserted after `Depends on:`/`Created:` if the field is absent).
    - Project charter: appends `- [<NN> — <epic title>](../epics/<NN>-<slug>.md)`
      under the `<!-- EPICS -->` marker (replacing the `_none yet_` placeholder),
      and bumps the Epics count in PROJECTS.md.

Idempotent: re-linking the same epic updates the field and does not duplicate the
charter row. Exits 1 if the project charter or the epic file is missing.
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


def resolve_epic_file(epics_dir: Path, token: str) -> Path | None:
    token = token.strip()
    m = re.fullmatch(r"[Ee]?0*(\d+)", token)
    if m:
        num = int(m.group(1))
        matches = sorted(epics_dir.glob(f"{num:02d}-*.md"))
        if matches:
            return matches[0]
    name = token[:-3] if token.endswith(".md") else token
    cand = epics_dir / f"{name}.md"
    if cand.is_file():
        return cand
    matches = [p for p in sorted(epics_dir.glob(f"*{name}*.md")) if p.name != "EPICS.md"]
    return matches[0] if len(matches) == 1 else None


def epic_title(text: str) -> str:
    m = re.search(r"^#\s+Epic\s+\d+\s+[—-]\s+(.+)$", text, flags=re.MULTILINE)
    if m:
        return m.group(1).strip()
    m = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    return m.group(1).strip() if m else "epic"


def set_epic_project_field(epic_path: Path, slug: str) -> None:
    text = epic_path.read_text()
    new_text, n = re.subn(
        r"^Project:.*$", f"Project: {slug}", text, count=1, flags=re.MULTILINE
    )
    if n == 0:
        # Insert after Depends on:, else after Created:, else after Status:.
        for anchor in (r"^(Depends on:.*)$", r"^(Created:.*)$", r"^(Status:.*)$"):
            new_text, n = re.subn(
                anchor, r"\1\n" + f"Project: {slug}", text, count=1, flags=re.MULTILINE
            )
            if n:
                break
        if n == 0:
            sys.exit(f"error: no Status/Created/Depends anchor for Project field in {epic_path}")
    epic_path.write_text(new_text)


def add_epic_to_charter(charter: Path, epic_num: int, etitle: str, epic_slug: str) -> None:
    text = charter.read_text()
    row = f"- [{epic_num:02d} — {etitle}](../epics/{epic_slug}.md)"
    if row in text:
        return  # idempotent

    marker = "<!-- EPICS -->"
    if marker not in text:
        sys.exit(f"error: '<!-- EPICS -->' marker not found in {charter}")

    # Drop the "_none yet_" placeholder if it directly follows the marker.
    text = re.sub(
        re.escape(marker) + r"\n(_none yet_\n)",
        marker + "\n",
        text,
        count=1,
    )
    text = text.replace(marker, f"{marker}\n{row}", 1)
    charter.write_text(text)


def bump_index_epic_count(index: Path, project_slug: str) -> None:
    if not index.is_file():
        return
    needle = f"](./{project_slug}.md)"
    out = []
    for line in index.read_text().splitlines():
        if line.lstrip().startswith("|") and needle in line:
            cells = line.split("|")
            # cells: ['', ' [title](./slug.md) ', ' epics ', ' linear ', ' status ', '']
            if len(cells) >= 3:
                m = re.search(r"\d+", cells[2])
                if m:
                    cells[2] = f" {int(m.group(0)) + 1} "
                    line = "|".join(cells)
        out.append(line)
    index.write_text("\n".join(out) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Link an epic to a project (both ways).")
    parser.add_argument("project")
    parser.add_argument("--epic", required=True)
    parser.add_argument("--root")
    args = parser.parse_args()

    root = find_project_root(args.root)
    projects_dir = root / "docs" / "artifacts" / "projects"
    epics_dir = root / "docs" / "artifacts" / "epics"

    charter = projects_dir / f"{args.project}.md"
    if not charter.is_file():
        print(f"error: project charter not found: {charter}", file=sys.stderr)
        return 1

    epic_path = resolve_epic_file(epics_dir, args.epic)
    if epic_path is None:
        print(f"error: could not resolve epic {args.epic!r} under {epics_dir}", file=sys.stderr)
        return 1

    num_m = re.match(r"(\d+)-", epic_path.name)
    if not num_m:
        print(f"error: epic filename {epic_path.name!r} is not NN-slug.md form", file=sys.stderr)
        return 1
    epic_num = int(num_m.group(1))
    epic_slug = epic_path.stem
    etitle = epic_title(epic_path.read_text())

    set_epic_project_field(epic_path, args.project)
    added = f"- [{epic_num:02d} — {etitle}](../epics/{epic_slug}.md)" not in charter.read_text()
    add_epic_to_charter(charter, epic_num, etitle, epic_slug)
    if added:
        bump_index_epic_count(projects_dir / "PROJECTS.md", args.project)

    print(f"linked epic '{epic_slug}' <-> project '{args.project}'")
    print(f"epic_file={epic_path.relative_to(root)}")
    print(f"charter={charter.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
