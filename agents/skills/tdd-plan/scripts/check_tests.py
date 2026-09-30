#!/usr/bin/env python3
"""
Check that a plan's tests still match what tdd-plan committed.

Usage:
    check_tests.py [<slug>] [--final] [--root <path>]

The baseline is the `Tests-commit:` sha in PLAN.md. From there a test file
changes in exactly two ways: a sticker line (one containing TDD-PENDING) is
deleted, or a user-approved `test(<scope>): amend ...` commit rewrites it.
The working tree is what gets checked, so this runs before a commit as well
as before a push. Whitespace and trailing commas are ignored, so a formatter reflowing a file
after a sticker deletion passes.

Test files: every file the tests commit (and the test commits directly
before it) touched, plus every test-like path — test dirs, test_*.py,
*_test.*, *.test.*, *.spec.*, *Tests.swift and kin, and runner config.

Without <slug>, the plan is the one (archived ones included) whose `Branch:`
is the current branch.

Prints:
    tdd=none                      no plan on this branch, or no Tests-commit
  or
    tests_commit=<sha>
    amendments=<n>                then `  <sha> <subject>` per amend commit
    violations=<n>                then `  <kind>: <detail>` per violation

Violation kinds:
    edited    a test file changed beyond deleting sticker lines
    added     a test file appeared
    deleted   a test file disappeared
    sticker   a sticker line appeared that the baseline lacks
    pending   a done task still has stickers (with --final: any sticker)

Exit codes:
    0  clean, or tdd=none
    1  violations, or the plan/baseline could not be resolved
    2  usage error
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

STICKER = "TDD-PENDING"
STICKER_TASK = re.compile(r"TDD-PENDING (TASK-\d+)\b")
TEST_COMMIT = re.compile(r"^test(\([^)]*\))?!?:")
AMEND_COMMIT = re.compile(r"^test(\([^)]*\))?!?: amend\b")
TASK_LINE = re.compile(r"^- \[(?P<box>[ xX])\]\s+(?P<id>TASK-\d+):")
ARTIFACTS = "docs/artifacts/"
TEST_LIKE = re.compile(
    r"(^|/)(test|tests|__tests__|spec|specs|testdata|[\w.]*Tests?|[\w.]+\.Tests?)/"
    r"|(^|/)test_[^/]*\.py$"
    r"|_test\.\w+$"
    r"|\.(test|spec)\.\w+$"
    r"|(^|/)[A-Z]\w*Tests?\.(swift|kt|java|cs|m|mm)$"
    r"|(^|/)(conftest\.py|pytest\.ini|phpunit\.xml(\.dist)?|\.mocharc\.\w+)$"
    r"|(^|/)(jest|vitest|karma)\.conf(ig)?\.\w+$"
    r"|\.xctestplan$"
)


def git(root: Path, *args: str, check: bool = True) -> str:
    r = subprocess.run(["git", "-c", "core.quotePath=false", *args], cwd=root, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(f"error: git {' '.join(args)}: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return r.stdout


def find_project_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if r.returncode != 0:
        print("error: not inside a git repository", file=sys.stderr)
        sys.exit(1)
    return Path(r.stdout.strip())


def find_plan(root: Path, slug: str | None) -> Path | None:
    plans = root / "docs" / "artifacts" / "plans"
    if slug:
        direct = plans / slug / "PLAN.md"
        if direct.is_file():
            return direct
        archived = re.compile(rf"^\d{{4}}-\d{{2}}-\d{{2}}-{re.escape(slug)}(-\d+)?$")
        hits = sorted(p for p in plans.glob("archive/*/PLAN.md") if archived.match(p.parent.name))
        if hits:
            return hits[-1]
        print(f"error: plan not found: {slug}", file=sys.stderr)
        sys.exit(1)
    branch = git(root, "branch", "--show-current").strip()
    if not branch:
        return None
    line = re.compile(rf"^Branch:\s*{re.escape(branch)}\s*$", re.MULTILINE)
    hits = [p for p in sorted(plans.rglob("PLAN.md")) if line.search(p.read_text())]
    if len(hits) > 1:
        print(f"error: several plans name branch {branch}; pass the slug:", file=sys.stderr)
        for p in hits:
            print(f"  - {p.relative_to(root)}", file=sys.stderr)
        sys.exit(1)
    return hits[0] if hits else None


def plan_field(text: str, name: str) -> str | None:
    m = re.search(rf"^{name}:\s*(\S+)\s*$", text, re.MULTILINE)
    return m.group(1) if m else None


def done_tasks(text: str) -> set[str]:
    done, in_tasks = set(), False
    for line in text.splitlines():
        if line.startswith("## "):
            in_tasks = line.startswith("## Tasks")
            continue
        m = TASK_LINE.match(line) if in_tasks else None
        if m and m.group("box").lower() == "x":
            done.add(m.group("id"))
    return done


def changed_files(root: Path, sha: str) -> list[str]:
    return git(root, "diff-tree", "--no-commit-id", "--name-only", "--no-renames", "-r", sha).splitlines()


def test_commit_files(root: Path, tests_commit: str) -> set[str]:
    """Files touched by the tests commit and the test commits directly before it."""
    files: set[str] = set()
    log = git(root, "log", "--first-parent", "--format=%H%x09%s", tests_commit)
    for entry in log.splitlines():
        sha, _, subject = entry.partition("\t")
        if not TEST_COMMIT.match(subject):
            break
        files.update(changed_files(root, sha))
    return files


def amendments(root: Path, tests_commit: str) -> tuple[list[str], dict[str, str]]:
    """Amend commits after the baseline, oldest first, and each path's latest amend sha."""
    listed, latest = [], {}
    log = git(root, "log", "--format=%H%x09%s", f"{tests_commit}..HEAD")
    for entry in log.splitlines():  # newest first
        sha, _, subject = entry.partition("\t")
        if AMEND_COMMIT.match(subject):
            listed.append(f"{sha[:10]} {subject}")
            for path in changed_files(root, sha):
                latest.setdefault(path, sha)
    return list(reversed(listed)), latest


def blob(root: Path, sha: str, path: str) -> str | None:
    r = subprocess.run(["git", "show", f"{sha}:{path}"], cwd=root, capture_output=True)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def working(root: Path, path: str) -> str | None:
    p = root / path
    return p.read_bytes().decode("utf-8", "replace") if p.is_file() else None


def stickers(text: str) -> set[str]:
    return {line.strip() for line in text.splitlines() if STICKER in line}


def normalized(text: str) -> str:
    """Code minus sticker lines, whitespace and trailing commas — what a formatter may change."""
    code = re.sub(r"\s+", "", "".join(l for l in text.splitlines() if STICKER not in l))
    return re.sub(r",([)\]}])", r"\1", code)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a plan's tests against its Tests-commit.")
    parser.add_argument("slug", nargs="?")
    parser.add_argument("--final", action="store_true", help="also fail on any sticker left")
    parser.add_argument("--root")
    args = parser.parse_args()

    root = find_project_root(args.root)
    plan_md = find_plan(root, args.slug)
    plan_text = plan_md.read_text() if plan_md else ""
    tests_commit = plan_field(plan_text, "Tests-commit")
    if not tests_commit or tests_commit == "none":
        print("tdd=none")
        return 0
    if subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"{tests_commit}^{{commit}}"],
                      cwd=root, capture_output=True).returncode != 0:
        print(f"error: Tests-commit {tests_commit} not found — was the branch rebased or squashed?",
              file=sys.stderr)
        return 1

    locked = test_commit_files(root, tests_commit)
    amended, amend_base = amendments(root, tests_commit)
    changed = set(git(root, "diff", "--name-only", "--no-renames", tests_commit).splitlines())
    changed |= set(git(root, "ls-files", "--others", "--exclude-standard").splitlines())

    violations: list[str] = []
    for path in sorted(changed):
        if path.startswith(ARTIFACTS) or not (path in locked or TEST_LIKE.search(path)):
            continue
        base = blob(root, amend_base.get(path, tests_commit), path)
        cur = working(root, path)
        if base is None and cur is None:
            continue
        if base is None:
            violations.append(f"added: {path}")
        elif cur is None:
            violations.append(f"deleted: {path}")
        elif stickers(cur) - stickers(base):
            violations.append(f"sticker: {path}")
        elif normalized(cur) != normalized(base):
            violations.append(f"edited: {path}")

    done = done_tasks(plan_text)
    hits = git(root, "grep", "-n", "-I", "--untracked", "-F", STICKER, "--", ".",
               f":(exclude){ARTIFACTS}", check=False)
    for hit in hits.splitlines():
        path, lineno, content = (hit.split(":", 2) + ["", ""])[:3]
        m = STICKER_TASK.search(content)
        if args.final or (m and m.group(1) in done):
            violations.append(f"pending: {path}:{lineno} ({m.group(1) if m else 'no task id'})")

    print(f"tests_commit={tests_commit}")
    print(f"amendments={len(amended)}")
    for a in amended:
        print(f"  {a}")
    print(f"violations={len(violations)}")
    for v in violations:
        print(f"  {v}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
