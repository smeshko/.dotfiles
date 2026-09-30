#!/usr/bin/env python3
"""
Report an epic's Linear/project linkage and phase-completion counts.

Usage:
    epic_status.py <epic> [--root <path>]

Args:
    <epic>   Epic id or slug: "13", "E13", "13-home-screen-redesign".
    --root   Project root. Defaults to the git toplevel; falls back to CWD.

Prints (key=value per line):
    epic=<NN>
    epic_slug=<NN>-<slug>
    linear_issue=<ID|none>          # the epic parent issue, from the `Linear:` header
    project=<slug|none>             # from the `Project:` header
    phases_total=<N>
    phases_done=<M>                 # phase blocks whose `**Plan**:` line says status: done
    all_phases_done=<yes|no>

Consumed by archive-plan to decide the roll-up: when all phases are done, the
epic parent issue can be closed; the caller then checks whether it was the last
epic in its project.
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


def header_field(text: str, field: str) -> str:
    m = re.search(rf"^{field}:\s*(.+)$", text, flags=re.MULTILINE)
    if not m:
        return "none"
    val = m.group(1).strip()
    # Keep just the identifier token (drop any "(url)" suffix) for Linear.
    return val.split()[0] if val and val != "none" else "none"


def main() -> int:
    parser = argparse.ArgumentParser(description="Report epic linkage + phase completion.")
    parser.add_argument("epic")
    parser.add_argument("--root")
    args = parser.parse_args()

    root = find_project_root(args.root)
    epics_dir = root / "docs" / "artifacts" / "epics"
    epic_path = resolve_epic_file(epics_dir, args.epic)
    if epic_path is None:
        print(f"error: could not resolve epic {args.epic!r} under {epics_dir}", file=sys.stderr)
        return 1

    text = epic_path.read_text()
    num_m = re.match(r"(\d+)-", epic_path.name)
    epic_num = f"{int(num_m.group(1)):02d}" if num_m else "??"

    # Each phase block: heading line, then its **Plan** line carries `status: <x>`.
    phase_headings = re.findall(r"^##\s+Phase\s+[\d.]+\b", text, flags=re.MULTILINE)
    total = len(phase_headings)
    done = len(re.findall(r"^\*\*Plan\*\*:.*status:\s*done\b", text, flags=re.MULTILINE))

    print(f"epic={epic_num}")
    print(f"epic_slug={epic_path.stem}")
    print(f"linear_issue={header_field(text, 'Linear')}")
    print(f"linear_milestone={header_field(text, 'Milestone')}")
    print(f"project={header_field(text, 'Project')}")
    print(f"phases_total={total}")
    print(f"phases_done={done}")
    print(f"all_phases_done={'yes' if total > 0 and done == total else 'no'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
