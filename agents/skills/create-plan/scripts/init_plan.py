#!/usr/bin/env python3
"""
Initialise a new plan directory with PLAN.md (and RESEARCH.md if risk warrants).

Usage:
    init_plan.py --title "<title>" --risk <tier> [--slug <slug>] [--root <path>]

Args:
    --title  Plan title (required). Used to derive --slug when omitted.
    --risk   One of: tiny, small, medium, large, high (required).
    --slug   Override the auto-derived slug.
    --root   Project root. Defaults to the git toplevel; falls back to CWD.

Creates:
    <root>/docs/artifacts/plans/<slug>/PLAN.md
    <root>/docs/artifacts/plans/<slug>/RESEARCH.md   (risk in {medium, large, high})
    <root>/docs/artifacts/plans/<slug>/tasks/

On success prints the created directory and the chosen slug.
"""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

VALID_RISKS = ("tiny", "small", "medium", "large", "high")
RESEARCH_REQUIRED = {"medium", "large", "high"}

REFERENCES = Path(__file__).resolve().parent.parent / "references"
PLAN_TEMPLATE = REFERENCES / "template-plan.md"
RESEARCH_TEMPLATE = REFERENCES / "template-research.md"


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


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


def render_plan(title: str, risk: str) -> str:
    body = PLAN_TEMPLATE.read_text()
    today = datetime.date.today().isoformat()
    body = body.replace("<title>", title, 1)
    body = body.replace("draft | ready | tests-ready | in-progress | done", "draft", 1)
    body = body.replace("tiny | small | medium | large | high", risk, 1)
    body = body.replace("YYYY-MM-DD", today, 1)
    return body


def render_research(title: str) -> str:
    body = RESEARCH_TEMPLATE.read_text()
    return body.replace("<plan-title>", title, 1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialise a new plan directory.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--risk", required=True, choices=VALID_RISKS)
    parser.add_argument("--slug")
    parser.add_argument("--root")
    args = parser.parse_args()

    slug = args.slug or slugify(args.title)
    if not slug:
        print(f"error: could not derive slug from title {args.title!r}", file=sys.stderr)
        return 1

    root = find_project_root(args.root)
    plan_dir = root / "docs" / "artifacts" / "plans" / slug
    if plan_dir.exists():
        print(f"error: plan directory already exists: {plan_dir}", file=sys.stderr)
        return 1

    plan_dir.mkdir(parents=True)
    (plan_dir / "tasks").mkdir()
    (plan_dir / "PLAN.md").write_text(render_plan(args.title, args.risk))

    research_created = False
    if args.risk in RESEARCH_REQUIRED:
        (plan_dir / "RESEARCH.md").write_text(render_research(args.title))
        research_created = True

    print(f"created: {plan_dir}")
    print(f"slug:    {slug}")
    print(f"risk:    {args.risk}")
    print(f"research: {'RESEARCH.md created' if research_created else 'skipped (risk below medium)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
