---
name: create-pr
description: Open a GitHub pull request from the current branch via the gh CLI. Use when the user asks to open/create/submit a PR, raise a pull request, or push for review.
argument-hint: <--base <base-branch>> <--draft>
---

# Create Pull Request

Open a GitHub pull request from the current branch.

## Workflow

### Step 1: Gather context

```bash
bash ~/.claude/skills/create-pr/scripts/get_pr_context.sh
```

The script prints, in order:

- `BRANCH` — current branch
- `BASE` — base branch resolved from `origin/HEAD` (or `(unknown)` if not set — pass `--base` to step 3 in that case)
- `EXISTING PR` — URL of an open PR for this branch if one exists, else `(none)`
- `LINEAR ISSUE` — the issue id embedded in the branch name, else the `Linear:` field of the plan whose `Branch:` is this branch, else `(none — not a Linear-tracked branch)`. On `(none)`, a ticket id the user named in this conversation stands in for it.
- `COMMITS` — commits since base, oldest first (`<sha> <subject>`)
- `FILES` — files changed vs base
- `PUSH STATUS` — `unpushed | up-to-date | ahead (N) | behind-remote (N) | diverged`

**If `PUSH STATUS` is `behind-remote` or `diverged`, stop.** Ask the user to reconcile (pull/rebase) before opening the PR.

**Before anything is pushed, check the tests:**

```bash
python3 ~/.claude/skills/tdd-plan/scripts/check_tests.py --final
```

`tdd=none` → not a TDD plan; carry on. `violations=0` → carry on, keeping its `amendments` list for Step 2. Any violation → stop and show it to the user: a test changed outside a sticker deletion or an approved amendment, or a sticker is still pending.

**If `EXISTING PR` is not `(none)`:** check `gh pr view <url> --json isDraft`. If it's a draft for this branch (`tdd-plan` opens one per TDD plan), this skill's job is to *finish* it — push the local commits (`git push`), compose the real title/body (Step 2), apply with `gh pr edit <number> --title ... --body ...`, then flip with `gh pr ready <number>`, skipping Step 3. If it's a non-draft PR, stop and report the URL — don't create a duplicate.

### Step 2: Compose title and body

**Title:**
- Single commit since base → use its subject line verbatim
- Multiple commits → write a concise imperative summary (`<type>(<scope>): <description>` if the project uses Conventional Commits, otherwise plain imperative)

**Body** — resolved in this order:

1. If the repo has a PR template at `.github/pull_request_template.md` (or `.github/PULL_REQUEST_TEMPLATE.md`), read it and fill it in.
2. Otherwise, use the bundled template at `~/.claude/skills/create-pr/references/pr_template.md` (Summary + Test plan are required; Screenshots / Related / Breaking changes are optional — delete unused sections).

**Plan artifacts:** if the branch implements a plan whose dir carries `VALIDATION.md` and/or `REVIEW.md` (written by `validate-plan` / `review-plan`), paste each into its own body section (`## Plan validation`, `## Adversarial review`), and surface their `defer` items as a Known limitations / Follow-ups list. On a TDD plan, add a `## Test amendments` section listing each amend commit from the test check (sha + subject), or `None — the tests merged as tdd-plan wrote them.`

**Linear linking** (see `~/.claude/skills/shared/linear-integration.md`): with a `LINEAR ISSUE` id resolved, put it in the two places Linear reads a PR — the title and the body. Linear ignores ids in PR comments, and a bare id in the body links nothing.

- **Title:** end it with ` (<ID>)`, e.g. `feat(auth): add login (ABC-45)`.
- **Body:** `Closes <ID>` on its own line, in the Summary or the Related section — the closing magic word moves the issue to Done when the PR merges. Use `Part of <ID>` instead when this PR leaves the issue unfinished and more PRs will follow.

Skip both when the id is `(none)`.

### Step 3: Create the PR

```bash
bash ~/.claude/skills/create-pr/scripts/create_pr.sh "<title>" "<body>" [--base <base>] [--draft]
```

The script:
1. Pushes the branch if it has no upstream or is ahead of remote.
2. Invokes `gh pr create` with the title, body, and (optionally) base/draft flags.
3. Prints the PR URL on success.

### Step 4: Confirm the Linear link

Skip when no Linear id was resolved or Linear isn't wired (no `mcp__linear-server__*` tools).

`mcp__linear-server__get_issue <ID>` → the issue's `attachments` include the PR URL. Linear attaches within seconds of the PR opening or being edited, so one miss can be lag — check once more before acting on it. Still missing:

1. `gh pr view <number> --json title,body` lacks the id → `gh pr edit` it into the title and body per Step 2; Linear re-reads a PR on save. Check again.
2. The id is there and the attachment still isn't → Linear's GitHub integration isn't watching this repo. Report it; the `linear` skill's `add_pr_link.py <ID> <PR URL>` attaches the PR by hand.

Done when: the issue's attachments include the PR URL, or the miss is reported.

### Step 5: Report

Show the user the PR URL and the Linear link outcome. If the repo runs CI on PRs, offer to watch it
(`gh pr checks <number> --watch` as a background task) — on projects where CI is
the only build/test gate, a green run is what proves the plan's CI-pending
acceptance criteria (see `implement-plan`); tick them on the branch before
merging. For plan branches, `ship-plan` archives, watches CI, merges and cleans up; by hand, `archive-plan` runs before the merge.

## Behaviour Constraints

- **Don't duplicate.** If a PR already exists for the branch, surface it instead of opening a new one.
- **Don't push over divergence.** Behind-remote or diverged states need user attention first.
- **Link only a resolved Linear issue.** With no id resolved, impose no work-item linking, no required branch pattern, and no required verifications. Pre-commit hooks and CI handle quality gates.
- **Body is optional.** Pass an empty string `""` to omit; `gh pr create` opens with an empty body in that case.
