#!/usr/bin/env python3
"""
Resolve the plan to review: slug, plan directory, recorded feature branch,
and base branch (from origin/HEAD).

Usage:
    resolve_plan.py [<slug>] [--root <path>]

Slug resolution mirrors archive-plan:
    1. If <slug> is passed, use it.
    2. Else match the current branch against each plan's `Branch:` field in
       PLAN.md. If exactly one matches, use it.
    3. Else fall back to "current branch ends in /<slug>" for plans missing
       a `Branch:` field. If exactly one matches, use it (warn to stderr).
    4. Else exit 1.

Prints, key=value per line:
    slug=<slug>
    plan_dir=<path-relative-to-repo-root>
    branch=<branch-from-PLAN.md, or current branch if unrecorded>
    base=<base-from-origin/HEAD, or (unknown)>

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

BRANCH_RE = re.compile(r"^Branch:\s*(\S+)\s*$")


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


def current_branch() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("error: could not determine current branch (not a git repo?)", file=sys.stderr)
        sys.exit(1)
    if out == "HEAD":
        print("error: detached HEAD", file=sys.stderr)
        sys.exit(1)
    return out


def read_plan_branch(plan_md: Path) -> str:
    for line in plan_md.read_text().splitlines():
        m = BRANCH_RE.match(line)
        if m:
            return m.group(1).strip()
    return ""


def origin_head_base() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "origin/HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out.removeprefix("origin/")
    except subprocess.CalledProcessError:
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


def resolve_slug(plans_dir: Path, branch: str) -> tuple[str, bool]:
    """Returns (slug, used_fallback)."""
    recorded_matches = []
    for slug, plan_md in iter_plans(plans_dir):
        if read_plan_branch(plan_md) == branch:
            recorded_matches.append(slug)

    if len(recorded_matches) == 1:
        return recorded_matches[0], False
    if len(recorded_matches) > 1:
        print(
            f"error: multiple plans recorded with branch '{branch}':",
            file=sys.stderr,
        )
        for s in recorded_matches:
            print(f"  - {s}", file=sys.stderr)
        print("Pass the slug explicitly.", file=sys.stderr)
        sys.exit(1)

    fallbacks = []
    for slug, plan_md in iter_plans(plans_dir):
        if read_plan_branch(plan_md):
            continue
        if branch.endswith("/" + slug):
            fallbacks.append(slug)

    if len(fallbacks) == 1:
        return fallbacks[0], True
    if len(fallbacks) > 1:
        print(
            f"error: multiple plans match branch suffix of '{branch}':",
            file=sys.stderr,
        )
        for s in fallbacks:
            print(f"  - {s}", file=sys.stderr)
        print("Pass the slug explicitly.", file=sys.stderr)
        sys.exit(1)

    print(
        f"error: no plan recorded with branch '{branch}'. "
        f"Pass the slug explicitly.",
        file=sys.stderr,
    )
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve plan context for review.")
    parser.add_argument("slug", nargs="?")
    parser.add_argument("--root")
    args = parser.parse_args()

    root = find_project_root(args.root)
    plans_dir = root / "docs" / "artifacts" / "plans"
    branch_now = current_branch()

    if args.slug:
        slug = args.slug
    else:
        slug, used_fallback = resolve_slug(plans_dir, branch_now)
        if used_fallback:
            print(
                f"warning: plan '{slug}' has no Branch: field — "
                f"matched via branch suffix '{branch_now}'",
                file=sys.stderr,
            )

    plan_dir = plans_dir / slug
    plan_md = plan_dir / "PLAN.md"
    if not plan_md.is_file():
        print(f"error: plan not found: {plan_md}", file=sys.stderr)
        return 1

    recorded_branch = read_plan_branch(plan_md) or branch_now
    base = origin_head_base() or "(unknown)"

    rel = plan_dir.relative_to(root)
    print(f"slug={slug}")
    print(f"plan_dir={rel}")
    print(f"branch={recorded_branch}")
    print(f"base={base}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
