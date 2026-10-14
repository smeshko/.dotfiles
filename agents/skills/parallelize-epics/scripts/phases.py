#!/usr/bin/env python3
"""
Inventory a repo's epic phases, each with its state, as the graph waves.py schedules.

Usage:
    phases.py [<epic>[,<epic>...] ...] [--running <phase>[,<phase>...]] [--out <path>] [--root <path>]

Args:
    <epic>      Epic numbers to schedule: "7,8,9", "7 8 9" or "all". Default: every
                epic with a phase that is not done.
    --running   Phases to count as in flight on top of the detected ones ("7.1,08.2").
    --out       Write the JSON here instead of stdout.
    --root      Project root. Default: the main checkout of the current repo, since
                docs/ may be gitignored and live only there.

State per phase:
    done        its **Plan** line says `status: done`
    in_flight   not done, and it has a linked plan, or a branch or worktree path
                carries its issue id (lowercased: adw-104), or --running names it
    todo        everything else

Prints JSON with every epic's phases, so dependencies outside the selection keep
their state:
    {"selected": [7, 8], "phases": {"7.1": {"epic": 7, "title": ..., "issue": ...,
     "state": ..., "selected": true, "file": ..., "epic_depends": ...}, ...}}
Each selected todo phase also gets the fields the agent fills in for waves.py:
    "deps": [], "why": {}, "conflicts": [], "reviewed": false

A one-line summary goes to stderr.

Exit codes:
    0  ok
    1  no epics directory, or an unknown epic or phase
    2  usage error
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

EPICS_REL = Path("docs") / "artifacts" / "epics"
PHASE_HEADING = re.compile(r"^##\s+Phase\s+0*(\d+)\.(\d+)\s*[—–-]+\s*(.+?)\s*$", re.MULTILINE)


def git(root: Path | None, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=root, stderr=subprocess.DEVNULL, text=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def find_root(explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit).resolve()
    candidates = []
    top = git(None, "rev-parse", "--show-toplevel").strip()
    if top:
        candidates.append(Path(top))
    # The first worktree listed is the main checkout.
    for line in git(None, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            candidates.append(Path(line[len("worktree "):]))
            break
    candidates.append(Path.cwd())
    for c in candidates:
        if (c / EPICS_REL).is_dir():
            return c.resolve()
    return None


def phase_id(token: str) -> str | None:
    m = re.fullmatch(r"\s*0*(\d+)\.0*(\d+)\s*", token)
    return f"{int(m.group(1))}.{int(m.group(2))}" if m else None


def split_list(values: list[str]) -> list[str]:
    return [t for v in values for t in re.split(r"[,\s]+", v) if t]


def parse_epic(path: Path) -> tuple[str, list[dict]]:
    text = path.read_text()
    dep_m = re.search(r"^Depends on:\s*(.+)$", text, flags=re.MULTILINE)
    epic_depends = dep_m.group(1).strip() if dep_m else "none"
    headings = list(PHASE_HEADING.finditer(text))
    phases = []
    for i, h in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        block = text[h.start():end]
        nxt = re.search(r"^##\s", block[2:], flags=re.MULTILINE)  # stop at the next H2
        if nxt:
            block = block[: nxt.start() + 2]
        plan_m = re.search(r"^\*\*Plan\*\*:\s*(.+)$", block, flags=re.MULTILINE)
        plan = plan_m.group(1) if plan_m else ""
        issue_m = re.search(r"^\*\*Linear\*\*:\s*([A-Z][A-Z0-9]*-\d+)", block, flags=re.MULTILINE)
        phases.append(
            {
                "id": f"{int(h.group(1))}.{int(h.group(2))}",
                "title": h.group(3),
                "issue": issue_m.group(1) if issue_m else None,
                "done": bool(re.search(r"status:\s*done\b", plan)),
                "plan_linked": bool(plan) and "not yet created" not in plan,
            }
        )
    return epic_depends, phases


def work_refs(root: Path) -> str:
    """Every branch name and worktree path, one per line, lowercased."""
    refs = git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes")
    worktrees = [
        line.split(" ", 1)[1]
        for line in git(root, "worktree", "list", "--porcelain").splitlines()
        if line.startswith(("worktree ", "branch "))
    ]
    return (refs + "\n" + "\n".join(worktrees)).lower()


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory epic phases for waves.py.")
    parser.add_argument("epics", nargs="*")
    parser.add_argument("--running", action="append", default=[])
    parser.add_argument("--out")
    parser.add_argument("--root")
    args = parser.parse_args()

    root = find_root(args.root)
    if root is None:
        print(f"error: no {EPICS_REL}/ in this repo or its main checkout", file=sys.stderr)
        return 1
    epics_dir = root / EPICS_REL

    epics = {}
    for path in sorted(epics_dir.glob("[0-9]*-*.md")):
        m = re.match(r"(\d+)-", path.name)
        if not m:
            continue
        num = int(m.group(1))
        depends, phases = parse_epic(path)
        epics[num] = {"file": str(path), "depends": depends, "phases": phases}

    tokens = [t.lower() for t in split_list(args.epics)]
    if tokens and tokens != ["all"]:
        selected = []
        for t in tokens:
            m = re.fullmatch(r"e?0*(\d+)", t)
            if not m or int(m.group(1)) not in epics:
                print(f"error: unknown epic {t!r} under {epics_dir}", file=sys.stderr)
                return 1
            selected.append(int(m.group(1)))
        selected = sorted(set(selected))
    else:
        selected = [n for n, e in sorted(epics.items()) if any(not p["done"] for p in e["phases"])]

    running = set()
    for t in split_list(args.running):
        pid = phase_id(t)
        if pid is None or not any(p["id"] == pid for e in epics.values() for p in e["phases"]):
            print(f"error: unknown phase {t!r} in --running", file=sys.stderr)
            return 1
        running.add(pid)

    refs = work_refs(root)
    out = {"selected": selected, "phases": {}}
    counts = {"done": 0, "in_flight": 0, "todo": 0}
    for num, e in sorted(epics.items()):
        for p in e["phases"]:
            issue = p["issue"]
            carried = bool(issue) and re.search(
                rf"(?<![a-z0-9]){re.escape(issue.lower())}(?![0-9])", refs
            )
            if p["done"]:
                state = "done"
            elif p["id"] in running or p["plan_linked"] or carried:
                state = "in_flight"
            else:
                state = "todo"
            entry = {
                "epic": num,
                "title": p["title"],
                "issue": issue,
                "state": state,
                "selected": num in selected,
                "file": e["file"],
                "epic_depends": e["depends"],
            }
            if state == "todo" and num in selected:
                entry.update({"deps": [], "why": {}, "conflicts": [], "reviewed": False})
            out["phases"][p["id"]] = entry
            if num in selected:
                counts[state] += 1

    text = json.dumps(out, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text)
    else:
        sys.stdout.write(text)
    in_flight = [pid for pid, p in out["phases"].items() if p["selected"] and p["state"] == "in_flight"]
    print(
        f"epics {','.join(map(str, selected)) or 'none'}: {counts['todo']} todo, "
        f"{counts['in_flight']} in flight ({', '.join(in_flight) or 'none'}), {counts['done']} done",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
