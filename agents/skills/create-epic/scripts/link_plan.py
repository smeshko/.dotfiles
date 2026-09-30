#!/usr/bin/env python3
"""
Link a plan to an epic phase, both directions, in one call.

Usage:
    link_plan.py <epic> --phase <NN.M> --plan <plan-slug>
                 [--status planned|in-progress|done] [--root <path>]

Args:
    <epic>     Epic id or slug: "12", "E12", "12-retrieval", "12-retrieval.md".
    --phase    Phase id, e.g. "12.3".
    --plan     Plan slug (the directory name under docs/artifacts/plans/).
    --status   Phase status to record in the epic. Default: planned.
    --root     Project root. Defaults to the git toplevel; falls back to CWD.

Writes both sides of the link:
    - Epic file phase block: the `**Plan**:` line becomes
      `**Plan**: [<slug>](../plans/<slug>/PLAN.md) · status: <status>`
    - Plan PLAN.md metadata:
      `Epic:  <NN> — <epic title> ([epic](../../epics/<NN>-<slug>.md))`
      `Phase: <NN.M> — <phase title>`

Idempotent. Exits 1 if the epic, the phase heading, or PLAN.md is missing.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

VALID_STATUS = ("planned", "in-progress", "done")


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


def epic_title(text: str) -> str:
    m = re.search(r"^#\s+Epic\s+\d+\s+[—-]\s+(.+)$", text, flags=re.MULTILINE)
    if m:
        return m.group(1).strip()
    m = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    return m.group(1).strip() if m else "epic"


def update_epic_side(epic_path: Path, pid: str, plan_slug: str, status: str) -> str:
    """Set the phase's **Plan** line. Returns the phase title."""
    text = epic_path.read_text()
    # Capture the phase block: from its heading up to the next "## " heading or EOF.
    block_re = re.compile(
        rf"(^##\s+Phase\s+{re.escape(pid)}\b[^\n]*\n)(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = block_re.search(text)
    if not m:
        sys.exit(f"error: phase '{pid}' heading not found in {epic_path}")

    heading, body = m.group(1), m.group(2)
    title_m = re.search(r"[—-]\s+(.+?)\s*$", heading)
    phase_title = title_m.group(1).strip() if title_m else pid

    plan_line = f"**Plan**: [{plan_slug}](../plans/{plan_slug}/PLAN.md) · status: {status}"
    new_body, n = re.subn(r"^\*\*Plan\*\*:.*$", plan_line, body, count=1, flags=re.MULTILINE)
    if n == 0:
        # No Plan line yet — insert one right after the heading.
        new_body = plan_line + "\n\n" + body.lstrip("\n")

    epic_path.write_text(text[: m.start()] + heading + new_body + text[m.end():])
    return phase_title


def phase_linear_id(epic_text: str, pid: str) -> str:
    """Return the phase block's **Linear** identifier token, or 'none'."""
    block_re = re.compile(
        rf"^##\s+Phase\s+{re.escape(pid)}\b.*?(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = block_re.search(epic_text)
    if not m:
        return "none"
    lm = re.search(r"^\*\*Linear\*\*:\s*(.+)$", m.group(0), flags=re.MULTILINE)
    if not lm:
        return "none"
    val = lm.group(1).strip()
    return val.split()[0] if val and val != "none" else "none"


def set_field(text: str, field: str, value: str) -> tuple[str, int]:
    return re.subn(rf"^{field}:.*$", f"{field}: {value}", text, count=1, flags=re.MULTILINE)


def update_plan_side(plan_md: Path, epic_num: int, epic_slug: str,
                     etitle: str, pid: str, phase_title: str, linear: str) -> None:
    text = plan_md.read_text()
    epic_value = f"{epic_num:02d} — {etitle} ([epic](../../epics/{epic_slug}.md))"
    phase_value = f"{pid} — {phase_title}"

    text, ne = set_field(text, "Epic", epic_value)
    text, np = set_field(text, "Phase", phase_value)
    # Only overwrite the plan's Linear field when the phase actually carries an id.
    nl = 1
    if linear != "none":
        text, nl = set_field(text, "Linear", linear)

    # Older plans may predate the Epic:/Phase:/Linear: fields — insert after Created:.
    inserts = []
    if ne == 0:
        inserts.append(f"Epic: {epic_value}")
    if np == 0:
        inserts.append(f"Phase: {phase_value}")
    if nl == 0:
        inserts.append(f"Linear: {linear}")
    if inserts:
        block = "\n".join(inserts)
        text, n = re.subn(r"^(Created:.*)$", r"\1\n" + block, text, count=1, flags=re.MULTILINE)
        if n == 0:
            text, n = re.subn(r"^(Status:.*)$", r"\1\n" + block, text, count=1, flags=re.MULTILINE)
            if n == 0:
                sys.exit(f"error: no Status:/Created: line to anchor Epic/Phase in {plan_md}")
    plan_md.write_text(text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Link a plan to an epic phase (both ways).")
    parser.add_argument("epic")
    parser.add_argument("--phase", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--status", choices=VALID_STATUS, default="planned")
    parser.add_argument("--root")
    args = parser.parse_args()

    root = find_project_root(args.root)
    epics_dir = root / "docs" / "artifacts" / "epics"
    epic_path = resolve_epic_file(epics_dir, args.epic)
    if epic_path is None:
        print(f"error: could not resolve epic {args.epic!r} under {epics_dir}", file=sys.stderr)
        return 1

    plan_md = root / "docs" / "artifacts" / "plans" / args.plan / "PLAN.md"
    if not plan_md.is_file():
        print(f"error: plan not found: {plan_md}", file=sys.stderr)
        return 1

    etitle = epic_title(epic_path.read_text())
    num_m = re.match(r"(\d+)-", epic_path.name)
    if not num_m:
        print(f"error: epic filename {epic_path.name!r} is not NN-slug.md form", file=sys.stderr)
        return 1
    epic_num = int(num_m.group(1))
    epic_slug = epic_path.stem

    phase_title = update_epic_side(epic_path, args.phase, args.plan, args.status)
    linear = phase_linear_id(epic_path.read_text(), args.phase)
    update_plan_side(plan_md, epic_num, epic_slug, etitle, args.phase, phase_title, linear)

    print(f"linked plan '{args.plan}' <-> {epic_slug} phase {args.phase} (status: {args.status})")
    print(f"epic_file={epic_path.relative_to(root)}")
    print(f"plan_file={plan_md.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
