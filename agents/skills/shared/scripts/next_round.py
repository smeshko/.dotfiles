#!/usr/bin/env python3
"""
Gate the next adversarial round of a plan against its risk tier's round cap.

Usage:
    next_round.py <slug> <validation|reviews> [--force] [--root <path>]

Counts the `round-<N>.md` files in the plan's round directory, reads `Risk:`
from PLAN.md, and refuses the next round once it would pass the cap from
~/.claude/skills/shared/adversarial-rounds.md:

    tiny / small            2
    medium / large / high   3

`--force` lets the round through. Pass it only after the user has said to
continue past the cap.

Prints, key=value per line:
    round=<N>     the round about to run
    cap=<M>
    risk=<tier>

Exit codes:
    0  the round may run
    1  the cap is reached, or the plan could not be resolved
    2  usage error
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

RISK_RE = re.compile(r"^Risk:\s*(\S+)\s*$", re.MULTILINE)
ROUND_RE = re.compile(r"^round-(\d+)\.md$")
CAPS = {"tiny": 2, "small": 2, "medium": 3, "large": 3, "high": 3}
DEFAULT_CAP = 3


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
        print("error: not inside a git repository", file=sys.stderr)
        sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate the next adversarial round against the cap.")
    parser.add_argument("slug")
    parser.add_argument("kind", choices=("validation", "reviews"))
    parser.add_argument("--force", action="store_true", help="the user said to continue past the cap")
    parser.add_argument("--root")
    args = parser.parse_args()

    root = find_project_root(args.root)
    plan_dir = root / "docs" / "artifacts" / "plans" / args.slug
    plan_md = plan_dir / "PLAN.md"
    if not plan_md.is_file():
        print(f"error: plan not found: {plan_md}", file=sys.stderr)
        return 1

    m = RISK_RE.search(plan_md.read_text())
    risk = m.group(1) if m else "(unknown)"
    cap = CAPS.get(risk, DEFAULT_CAP)

    rounds_dir = plan_dir / args.kind
    done = [int(r.group(1)) for p in rounds_dir.glob("round-*.md") if (r := ROUND_RE.match(p.name))]
    next_round = max(done, default=0) + 1

    print(f"round={next_round}")
    print(f"cap={cap}")
    print(f"risk={risk}")

    if next_round > cap and not args.force:
        print(
            f"error: round {next_round} would pass the cap of {cap} for a {risk} plan. "
            "Stop and take it to the user; rerun with --force once they say to continue.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
