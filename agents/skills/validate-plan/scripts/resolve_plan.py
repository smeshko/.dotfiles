#!/usr/bin/env python3
"""
Resolve the plan to validate: slug, plan directory, current status.

Usage:
    resolve_plan.py [<slug>] [--root <path>]

Slug resolution (no branch involved — validation runs before implement-plan
cuts a branch):

    1. If <slug> is passed, use it.
    2. Else scan docs/artifacts/plans/*/PLAN.md for plans whose Status: is `draft`
       or `ready`. If exactly one matches, use it. If zero or more than one,
       exit 1 asking for an explicit slug.

Prints, key=value per line:
    slug=<slug>
    plan_dir=<path-relative-to-repo-root>
    status=<draft|ready>

Exit codes:
    0  success
    1  resolution failed or PLAN.md missing
    2  usage error
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

STATUS_RE = re.compile(r"^Status:\s*(\S+)\s*$")
VALIDATABLE = {"draft", "ready"}


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


def read_plan_status(plan_md: Path) -> str:
    for line in plan_md.read_text().splitlines():
        m = STATUS_RE.match(line)
        if m:
            return m.group(1).strip()
    return ""


def iter_plans(plans_dir: Path):
    if not plans_dir.is_dir():
        return
    for child in sorted(plans_dir.iterdir()):
        if child.name == "archive":
            continue
        plan_md = child / "PLAN.md"
        if plan_md.is_file():
            yield child.name, plan_md


def resolve_slug(plans_dir: Path) -> str:
    matches = []
    for slug, plan_md in iter_plans(plans_dir):
        status = read_plan_status(plan_md)
        if status in VALIDATABLE:
            matches.append((slug, status))

    if len(matches) == 1:
        return matches[0][0]
    if len(matches) == 0:
        print(
            "error: no plan found with Status: draft or ready. "
            "Pass the slug explicitly, or run create-plan first.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("error: multiple validatable plans found:", file=sys.stderr)
    for slug, status in matches:
        print(f"  - {slug} ({status})", file=sys.stderr)
    print("Pass the slug explicitly.", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve plan context for validation.")
    parser.add_argument("slug", nargs="?")
    parser.add_argument("--root")
    args = parser.parse_args()

    root = find_project_root(args.root)
    plans_dir = root / "docs" / "artifacts" / "plans"

    slug = args.slug or resolve_slug(plans_dir)

    plan_dir = plans_dir / slug
    plan_md = plan_dir / "PLAN.md"
    if not plan_md.is_file():
        print(f"error: plan not found: {plan_md}", file=sys.stderr)
        return 1

    status = read_plan_status(plan_md) or "(unknown)"

    rel = plan_dir.relative_to(root)
    print(f"slug={slug}")
    print(f"plan_dir={rel}")
    print(f"status={status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
