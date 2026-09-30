#!/usr/bin/env python3
"""
Record a Linear issue id on an epic or one of its phases.

Usage:
    # Epic parent issue -> the epic header `Linear:` field
    set_linear.py <epic> --issue <ID> [--url <url>] [--root <path>]

    # Phase sub-issue -> that phase block's `**Linear**:` line
    set_linear.py <epic> --phase <NN.M> --issue <ID> [--url <url>] [--root <path>]

Args:
    <epic>    Epic id or slug: "13", "E13", "13-home-screen-redesign".
    --issue   The Linear issue identifier (e.g. ABC-42). Required.
    --phase   When given, stamp that phase block instead of the epic header.
    --url     Optional Linear issue URL, appended in parentheses.
    --root    Project root. Defaults to the git toplevel; falls back to CWD.

Value written is `<ID>` or `<ID> (<url>)`. Idempotent — replaces any existing
value. Exits 1 if the epic file (or the named phase heading) is missing.
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


def set_epic_header(epic_path: Path, value: str) -> None:
    text = epic_path.read_text()
    new_text, n = re.subn(
        r"^Linear:.*$", f"Linear: {value}", text, count=1, flags=re.MULTILINE
    )
    if n == 0:
        for anchor in (r"^(Project:.*)$", r"^(Depends on:.*)$", r"^(Created:.*)$"):
            new_text, n = re.subn(
                anchor, r"\1\n" + f"Linear: {value}", text, count=1, flags=re.MULTILINE
            )
            if n:
                break
        if n == 0:
            sys.exit(f"error: no header anchor for Linear field in {epic_path}")
    epic_path.write_text(new_text)


def set_phase_line(epic_path: Path, pid: str, value: str) -> None:
    text = epic_path.read_text()
    block_re = re.compile(
        rf"(^##\s+Phase\s+{re.escape(pid)}\b[^\n]*\n)(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = block_re.search(text)
    if not m:
        sys.exit(f"error: phase '{pid}' heading not found in {epic_path}")

    heading, body = m.group(1), m.group(2)
    line = f"**Linear**: {value}"
    new_body, n = re.subn(
        r"^\*\*Linear\*\*:.*$", line, body, count=1, flags=re.MULTILINE
    )
    if n == 0:
        # Insert after the **Plan** line if present, else right after the heading.
        new_body, n = re.subn(
            r"^(\*\*Plan\*\*:.*$)", r"\1\n\n" + line, body, count=1, flags=re.MULTILINE
        )
        if n == 0:
            new_body = line + "\n\n" + body.lstrip("\n")

    epic_path.write_text(text[: m.start()] + heading + new_body + text[m.end():])


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a Linear issue id on an epic/phase.")
    parser.add_argument("epic")
    parser.add_argument("--issue", required=True)
    parser.add_argument("--phase")
    parser.add_argument("--url")
    parser.add_argument("--root")
    args = parser.parse_args()

    root = find_project_root(args.root)
    epics_dir = root / "docs" / "artifacts" / "epics"
    epic_path = resolve_epic_file(epics_dir, args.epic)
    if epic_path is None:
        print(f"error: could not resolve epic {args.epic!r} under {epics_dir}", file=sys.stderr)
        return 1

    value = f"{args.issue} ({args.url})" if args.url else args.issue

    if args.phase:
        set_phase_line(epic_path, args.phase, value)
        print(f"phase {args.phase} Linear: {value}")
    else:
        set_epic_header(epic_path, value)
        print(f"epic Linear: {value}")
    print(f"epic_file={epic_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
