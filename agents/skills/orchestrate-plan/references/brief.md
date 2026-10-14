# Stage brief

The prompt each stage subagent receives. The subagent starts cold: it knows only this brief, the plan dir and the branch, so the brief carries every fact it cannot find by looking. Assemble it from the **common blocks** below, then add the **stage block** for the stage being run. Fill every `<placeholder>`; delete a line that does not apply to this lane. Keep each brief under about 120 lines.

## Common blocks

**Role and stage.** "You are one stage of an autonomous <N>-lane pipeline on `<repo>`. Your stage: invoke the `<skill>` skill (Skill tool, skill "<skill>", args "<args>") and follow it to the end." Then state the stage's bounds (create-plan: plan only, no code, no branch, no commit; tdd-plan: tests and stubs only).

**Lane.** Lane letter, phase number and title, tracker issue id, risk tier (once known), plan dir as an absolute path, worktree as an absolute path, current branch and head sha, draft PR number and URL (once one exists).

**Hand-off from the previous stage.** Everything the previous stage's report said that this stage needs: decisions taken, plan corrections, tests that are fragile, gaps it left, amendments already on the branch, what is still red. A stage that stopped mid-plan gets the exact state: tasks done with their shas, what is uncommitted, what is red and why.

**Base and branch.**
- The lane's base is `<base-sha>` (the head of `<base-branch>`). Branch from the worktree's current HEAD, never from the repo's default base; where the skill cuts a branch, pass `--base <base-branch>` or stay on the branch that already exists.
- Leave the base alone: no rebase, no merge of the default base, no checkout in the main checkout.
- PRs target `<pr-target>`. When the lane is stacked on an unmerged PR, the PR body's first line says "Stacked on #<n>; only the commits after <base-sha> belong to this PR."
- Review scope is `<base-sha>..HEAD`. Give Codex and any reviewer subagent that base, never the repo's default base, whose diff includes commits that are not this lane's.

**Where things live.**
- Plan files live in `<main-checkout>/docs/` when `docs/` is gitignored; pass `--root <main-checkout>` to the skill's scripts or use a `docs` symlink in the worktree, which stays untracked.
- Shared epic files: edit only this phase's own lines, with a narrow edit after re-reading the file. Scripts that rewrite the whole epic file race the other lanes.
- Other lanes' worktrees are off-limits: name them.
- Before starting, read the repo's `AGENTS.md` (or `CLAUDE.md`) and glossary, then the project memory index and every entry that names this stage's skill, the test runner, hooks or shell quirks. Follow them.

**Autonomy.**
- The user is not available. Answer every question the skill would ask the user yourself, from the plan, the epic, the ADRs, the glossary and the code, and record each answer: in the plan's Decisions when it shapes the plan, and in your report always.
- Where a memory note records the user's past answer to the same question, take that answer.
- A step whose acceptance cannot be met stays unticked, with nothing partial committed; carry on with the steps that do not depend on it, and report what failed and what you tried.
- When context runs low, stop at a task boundary with a clean committed tree and report exactly where you stopped and what is red. A fresh agent continues from there.
- Poll a background run's output file yourself; your turn ends only when the stage is done or truly blocked. Agents that ended their turn to wait for a background notice have stalled for an hour.

**Gates the user set.** Copy from the battle plan: no live or paid runs (name the env flags that enable them), never read `.env` files, which tracker tools to use (when the primary tracker connector is unauthenticated, name the one that works).

**Test runs.**
- While working, run only the files the task touches and the files that test the sources it changes, with a junit or equivalent reporter, in the foreground with a timeout.
- Run every full gate and every `git push` through the lock: `~/.claude/skills/orchestrate-plan/scripts/with-verify-lock.sh <lock-dir> <lane> <command...>` from the worktree, with a timeout of at least 25 minutes.
- Classify each failure: a test that fails once, in a file this lane does not touch, differs per run and passes alone is a **flake**; a test that fails twice, or sits in files this lane touches or exercises, is **real**. Record the failures of every full run for the report.

**Commits and pushes.** Stage files by name. One commit per task, in the repo's commit format. An existing test whose expectation must change gets its own `test(<scope>): amend` commit with red-then-green evidence and the reason in its message; a weakened assertion is never the route to green. Pushes run the hook; `--no-verify` is allowed only for the tdd-plan push of stubs. PRs stay drafts. Ship, archive and create-pr skills belong to the user.

**Report.** "Your reply is read by the orchestrator, not the user: under 30 lines, plain facts." Then the stage's report fields below, and always: decisions made in the user's place, one line each; every test amended and why; anything unticked, unverified, flaky or blocked.

## Stage blocks

**create-plan.** Args: the epic and phase. Rate the risk tier honestly by the skill's table: later stages are gated on it. Name the dependencies on other lanes or on code missing at the base. Report: slug and plan path, tier with a one-line reason, tasks one per line, dependencies, decisions.

**tdd-plan.** The branch name the skill should cut from the worktree HEAD. Prove red: every new test fails on an assertion, none on a crash. Push with `--no-verify` and open the draft PR. Report: branch, commits, PR, test count per task, red proof (command and counts), suite state with stickers on, where drafts or states were saved.

**implement-plan.** Resume at the first pending task. Done means demonstrated: each task's evidence is real output, and the final gate is green. The opt-in live tasks the user owns stay unticked. Push normally when every other task is done and the gate is green. Report: tasks done of total with shas, each full gate run and what failed, the push and PR head, the runtime demonstration (command and what it showed).

**review-plan.** The lane's base for scope. Points to attack, taken from the implementer's report: guards it loosened, decisions it took, the riskiest behaviour change, fragile tests. Always:
- Audit every `test(...): amend` commit on the branch: each changed an expectation because of the phase's intended behaviour, and none dropped or weakened an assertion. Restore any that did.
- Approve fixes yourself with this bar: fix real defects in this phase's scope; defer what belongs to a later phase or is a policy choice for the user, filed in the tracker; reject what is wrong.
- Spawn the reviewer subagent with `model` and `effort` named, as the shared rounds protocol says.
- Cap at the protocol's rounds. When the last round still has fixes, apply the high and medium ones, file the rest, and say which fixes no reviewer has seen.

Report: reviewers that ran per round, findings with fixed, deferred and rejected counts, one line per fixed and deferred finding, the verdicts asked for, the final gate, push tries and PR head, what only a live run can confirm.
