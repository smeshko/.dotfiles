#!/usr/bin/env python3
"""
Schedule the selected todo phases of a phases.py graph into waves that run in parallel.

Usage:
    waves.py <graph.json> [--max <n>]

Reads the JSON phases.py wrote, once the agent has filled each selected todo phase's
`deps` (phase ids it waits for), `conflicts` (phase ids it must not share a wave
with) and set `reviewed: true`.

Rules:
    - A dep that is done is met. A dep in flight is met from wave 2: it runs
      alongside wave 1.
    - A dep scheduled in wave k is met from wave k+1.
    - Conflicting phases never share a wave. A phase that conflicts with one in
      flight waits for wave 2. Conflicts are symmetric: either side may list them.
    - A wave holds at most --max phases (default 5). In-flight phases don't count.
    - When more phases are ready than fit, the longest chain of dependents goes
      first, then phase order.
    - A selected phase waiting on a todo phase outside the selection, directly or
      through another phase, is listed as blocked instead of scheduled.

Prints Markdown: the in-flight line, the wave table, and the blocked line.

Exit codes:
    0  ok
    1  graph error: an unreviewed phase, an unknown id, a cycle
    2  usage error
"""

from __future__ import annotations

import argparse
import json
import sys
from functools import lru_cache
from pathlib import Path


def order(pid: str) -> tuple[int, ...]:
    return tuple(int(x) for x in pid.split("."))


def label(pid: str, phases: dict) -> str:
    issue = phases[pid].get("issue")
    return f"{pid} ({issue})" if issue else pid


def fail(msg: str) -> int:
    print(f"error: {msg}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Schedule phases into parallel waves.")
    parser.add_argument("graph")
    parser.add_argument("--max", type=int, default=5)
    args = parser.parse_args()
    if args.max < 1:
        parser.error("--max must be at least 1")

    graph = json.loads(Path(args.graph).read_text())
    phases: dict = graph["phases"]
    todo = sorted(
        (pid for pid, p in phases.items() if p["selected"] and p["state"] == "todo"), key=order
    )
    in_flight = sorted(
        (pid for pid, p in phases.items() if p["state"] == "in_flight"), key=order
    )

    unreviewed = [pid for pid in todo if not phases[pid].get("reviewed")]
    if unreviewed:
        return fail(f"not reviewed yet: {', '.join(unreviewed)}")
    conflicts: dict[str, set[str]] = {pid: set() for pid in phases}
    for pid in todo:
        p = phases[pid]
        for ref in [*p.get("deps", []), *p.get("conflicts", [])]:
            if ref not in phases:
                return fail(f"{pid} names unknown phase {ref}")
            if ref == pid:
                return fail(f"{pid} names itself")
        for other in p.get("conflicts", []):
            conflicts[pid].add(other)
            conflicts[other].add(pid)

    deps = {pid: [d for d in phases[pid].get("deps", []) if phases[d]["state"] != "done"] for pid in todo}

    # Cycles among todo phases.
    seen: dict[str, int] = {}

    def visit(pid: str, path: list[str]) -> list[str] | None:
        seen[pid] = 1
        for d in deps.get(pid, []):
            if d not in deps:
                continue
            if seen.get(d) == 1:
                return path + [pid, d]
            if d not in seen:
                cycle = visit(d, path + [pid])
                if cycle:
                    return cycle
        seen[pid] = 2
        return None

    for pid in todo:
        if pid not in seen:
            cycle = visit(pid, [])
            if cycle:
                start = cycle.index(cycle[-1])
                return fail(f"dependency cycle: {' → '.join(cycle[start:])}")

    # Blocked: waits on a todo phase outside the selection, or on a blocked phase.
    blocked: dict[str, list[str]] = {}
    changed = True
    while changed:
        changed = False
        for pid in todo:
            if pid in blocked:
                continue
            why = [
                d for d in deps[pid]
                if (phases[d]["state"] == "todo" and not phases[d]["selected"]) or d in blocked
            ]
            if why:
                blocked[pid] = why
                changed = True
    ready = [pid for pid in todo if pid not in blocked]

    dependents: dict[str, list[str]] = {pid: [] for pid in ready}
    for pid in ready:
        for d in deps[pid]:
            if d in dependents:
                dependents[d].append(pid)

    @lru_cache(maxsize=None)
    def chain(pid: str) -> int:
        return 1 + max((chain(c) for c in dependents[pid]), default=0)

    wave_of: dict[str, int] = {}
    waves: list[list[str]] = []
    while len(wave_of) < len(ready):
        w = len(waves) + 1
        if w > len(ready) + 2:
            return fail("could not place every phase; check deps and conflicts")

        def met(d: str) -> bool:
            state = phases[d]["state"]
            if state == "done":
                return True
            if state == "in_flight":
                return w >= 2
            return d in wave_of and wave_of[d] < w

        candidates = sorted(
            (pid for pid in ready if pid not in wave_of and all(met(d) for d in deps[pid])),
            key=lambda pid: (-chain(pid), order(pid)),
        )
        wave: list[str] = []
        for pid in candidates:
            if len(wave) == args.max:
                break
            if conflicts[pid] & set(wave):
                continue
            if w == 1 and conflicts[pid] & set(in_flight):
                continue
            wave.append(pid)
        for pid in wave:
            wave_of[pid] = w
        waves.append(sorted(wave, key=order))

    lines = []
    selected_in_flight = [pid for pid in in_flight if phases[pid]["selected"]]
    if selected_in_flight:
        lines += ["In flight: " + " · ".join(label(p, phases) for p in selected_in_flight), ""]
    if not todo:
        lines.append("Nothing left to schedule in the selected epics.")
    if waves:
        lines += ["| Wave | Phases |", "|---|---|"]
        for i, wave in enumerate(waves, 1):
            name = f"{i} (now)" if i == 1 else str(i)
            cells = " · ".join(label(p, phases) for p in wave) or "— (waits on the phases in flight)"
            lines.append(f"| {name} | {cells} |")
    if blocked:
        lines += [
            "",
            "Blocked outside the selection: "
            + " · ".join(f"{p} ← {', '.join(sorted(blocked[p], key=order))}" for p in sorted(blocked, key=order)),
        ]
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
