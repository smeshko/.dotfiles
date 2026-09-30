#!/usr/bin/env python3
"""
Append a phase to an existing epic file and bump its phase count in EPICS.md.

Usage:
    add_phase.py <epic> --title "<title>" [--goal "<goal>"] [--root <path>]

Args:
    <epic>    Epic id or slug: "12", "E12", "12-retrieval", or "12-retrieval.md".
    --title   Phase title (required).
    --goal    One-sentence goal (optional; placeholder if omitted).
    --root    Project root. Defaults to the git toplevel; falls back to CWD.

Behaviour:
    - Resolves the epic file under docs/artifacts/epics/.
    - Assigns the next phase number: <NN>.<M> where NN is the epic number and M
      is (existing phases + 1).
    - Inserts the phase block immediately before the <!-- PHASES --> marker
      (or before "## Epic-level acceptance criteria" if the marker is absent).
    - Increments the Phases cell for this epic's row in EPICS.md.

On success prints:
    phase=<NN>.<M>
    epic=<NN>
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


def epic_number(epic_path: Path) -> int:
    m = re.match(r"(\d+)-", epic_path.name)
    return int(m.group(1)) if m else 0


def bump_index_phase_count(index: Path, epic_filename: str) -> None:
    if not index.is_file():
        return
    out = []
    needle = f"](./{epic_filename})"
    for line in index.read_text().splitlines():
        if line.lstrip().startswith("|") and needle in line:
            cells = line.split("|")
            # cells: ['', ' N ', ' [title](...) ', ' phases ', ' deps ', ' status ', '']
            if len(cells) >= 4:
                m = re.search(r"\d+", cells[3])
                if m:
                    new_val = int(m.group(0)) + 1
                    cells[3] = f" {new_val} "
                    line = "|".join(cells)
        out.append(line)
    index.write_text("\n".join(out) + "\n")


PHASE_BLOCK = """## Phase {pid} — {title}

**Plan**: _not yet created_

**Linear**: none

**Goal**: {goal}

### What to build

- _fill in_

### Acceptance criteria

- [ ] _fill in_
- [ ] Lint and tests pass.

### Validation

_fill in_

---

"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Append a phase to an epic.")
    parser.add_argument("epic")
    parser.add_argument("--title", required=True)
    parser.add_argument("--goal", default="_fill in_")
    parser.add_argument("--root")
    args = parser.parse_args()

    root = find_project_root(args.root)
    epics_dir = root / "docs" / "artifacts" / "epics"
    epic_path = resolve_epic_file(epics_dir, args.epic)
    if epic_path is None:
        print(f"error: could not resolve epic {args.epic!r} under {epics_dir}", file=sys.stderr)
        return 1

    num = epic_number(epic_path)
    text = epic_path.read_text()
    existing = re.findall(rf"^##\s+Phase\s+{num}\.(\d+)\b", text, flags=re.MULTILINE)
    m = (max(int(x) for x in existing) + 1) if existing else 1
    pid = f"{num}.{m}"

    block = PHASE_BLOCK.format(pid=pid, title=args.title, goal=args.goal)

    marker = "<!-- PHASES -->"
    if marker in text:
        text = text.replace(marker, block + marker, 1)
    elif "## Epic-level acceptance criteria" in text:
        text = text.replace(
            "## Epic-level acceptance criteria",
            block + "## Epic-level acceptance criteria",
            1,
        )
    else:
        text = text.rstrip() + "\n\n" + block
    epic_path.write_text(text)

    bump_index_phase_count(epics_dir / "EPICS.md", epic_path.name)

    print(f"phase={pid}")
    print(f"epic={num:02d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
