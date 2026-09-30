#!/usr/bin/env python3
"""
Record a Linear project-milestone id on an epic (the epic maps to one milestone).

Usage:
    set_milestone.py <epic> --milestone <id> [--url <url>] [--root <path>]

Args:
    <epic>       Epic id or slug: "13", "E13", "13-home-screen-redesign".
    --milestone  The Linear project-milestone id returned by save_milestone.
    --url        Optional milestone URL, appended in parentheses.
    --root       Project root. Defaults to the git toplevel; falls back to CWD.

Writes the epic header `Milestone:` field (inserted after `Linear:`/`Project:`/
`Depends on:` if absent). Value is `<id>` or `<id> (<url>)`. Idempotent. Exits 1
if the epic file is missing.
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


def set_header(epic_path: Path, value: str) -> None:
    text = epic_path.read_text()
    new_text, n = re.subn(
        r"^Milestone:.*$", f"Milestone: {value}", text, count=1, flags=re.MULTILINE
    )
    if n == 0:
        for anchor in (r"^(Linear:.*)$", r"^(Project:.*)$", r"^(Depends on:.*)$", r"^(Created:.*)$"):
            new_text, n = re.subn(
                anchor, r"\1\n" + f"Milestone: {value}", text, count=1, flags=re.MULTILINE
            )
            if n:
                break
        if n == 0:
            sys.exit(f"error: no header anchor for Milestone field in {epic_path}")
    epic_path.write_text(new_text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a Linear milestone id on an epic.")
    parser.add_argument("epic")
    parser.add_argument("--milestone", required=True)
    parser.add_argument("--url")
    parser.add_argument("--root")
    args = parser.parse_args()

    root = find_project_root(args.root)
    epics_dir = root / "docs" / "artifacts" / "epics"
    epic_path = resolve_epic_file(epics_dir, args.epic)
    if epic_path is None:
        print(f"error: could not resolve epic {args.epic!r} under {epics_dir}", file=sys.stderr)
        return 1

    value = f"{args.milestone} ({args.url})" if args.url else args.milestone
    set_header(epic_path, value)
    print(f"epic Milestone: {value}")
    print(f"epic_file={epic_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
