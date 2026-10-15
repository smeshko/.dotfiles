# Stage brief

The prompt each stage subagent receives. The subagent starts cold: it knows only its brief, so the brief carries every fact it cannot find by looking.

Two parts:
- **Rules file.** The common blocks below, written once in Step 1 to `<scratchpad>/rules.md`. Every brief opens with "Read `<scratchpad>/rules.md` in full and follow it." A rule you change mid-run (a lock path, the tracker route, a deadline) is one edit there that reaches every later spawn. Tell the agents already running about it with SendMessage.
- **Stage brief.** The role, the lane, the hand-off, and the stage block for the stage being run. Keep it under about 60 lines.

Fill every `<placeholder>`; delete a line that does not apply.

## Common blocks (the rules file)

**Lanes.** Every lane: letter, phase, issue, worktree. Other lanes' worktrees are off-limits, and so is the main checkout's working tree (no checkout there).

**Base and branch.**
- The lane's base is `<base-sha>` (the head of `<base-branch>`). Branch from the worktree's current HEAD, never from the repo's default base; where the skill cuts a branch, pass `--base <base-branch>` or stay on the branch that already exists.
- Leave the base alone: no rebase, no merge of the default base.
- PRs target `<pr-target>`. When the lane is stacked on an unmerged PR, the PR body's first line says "Stacked on #<n>; only the commits after <base-sha> belong to this PR."
- Review scope is `<base-sha>..HEAD`. Give Codex and any reviewer subagent that base, never the repo's default base.

**Where things live.**
- Plan files live in `<main-checkout>/docs/` when `docs/` is gitignored; pass `--root <main-checkout>` to the skill's scripts. A `docs` symlink in the worktree exists only around the script call that needs it: test runners pick up plan drafts through it.
- Shared epic files: edit only this phase's own lines, with a narrow edit after re-reading the file. Scripts that rewrite the whole epic file race the other lanes.
- Before starting, read the repo's `AGENTS.md` (or `CLAUDE.md`) and glossary, then the project memory index and every entry that names your stage's skill, the test runner, hooks or shell quirks. Follow them.

**Autonomy.**
- The user is not available. Answer every question the skill would ask the user yourself, from the plan, the epic, the ADRs, the glossary and the code, and record each answer: in the plan's Decisions when it shapes the plan, and in your report always.
- Where a memory note records the user's past answer to the same question, take that answer.
- A step whose acceptance cannot be met stays unticked, with nothing partial committed; carry on with the steps that do not depend on it, and report what failed and what you tried.
- When context runs low, stop at a task boundary with a clean committed tree and report exactly where you stopped and what is red.
- **Stay live.** Your turn ends only when the stage is done or truly blocked. Poll every background run and every subagent you started yourself, reading its output file. When a wait passes its cap, kill what you waited on and carry on without it.
- **Codex:** run the companion directly, in the background, with its brief in a file. Kill it after 20 minutes with no new output. When your stage ends, kill this worktree's `app-server-broker` and its children: `ps -Ao pid,command | grep app-server-broker`, then `lsof -a -p <pid> -d cwd -Fn` to match the worktree, then `pkill -P <pid>; kill <pid>`.

**Gates the user set.**
- Live or paid runs: allowed only for <lanes>, in <sandbox>; name the env flags that enable them.
- **Secrets:** source <the shell file that exports them>. Check a key by its length only, never by printing it. Never read `.env` files. Live suites need a per-test timeout of at least 60 s.
- **Tracker:** list every tracker write you would make (status, description, a deferred finding's title, one-paragraph body and labels) in your report. Never attempt the write: the orchestrator applies it.
- **Deadline:** <HH:MM, and the push cut-off>, when set.

**Test runs.**
- While working, run only the files the task touches and the files that test the sources it changes, with a junit or equivalent reporter, in the foreground with a timeout.
- Run every full gate and every `git push` through the lock: `<skill-dir>/scripts/with-verify-lock.sh <lock-dir> <lane> <command...>` from the worktree, with a timeout of at least 25 minutes.
- Classify each failure: a test that fails once, in a file this lane does not touch, differs per run and passes alone is a **flake**; a test that fails twice, or sits in files this lane touches or exercises, is **real**. Record the failures of every full run for the report.

**Commits and pushes.**
- Stage files by name. One commit per task, in the repo's commit format.
- An existing test whose expectation must change gets its own `test(<scope>): amend` commit, with red-then-green evidence and the reason in its message. A weakened assertion is never the route to green.
- Pushes run the hook. `--no-verify` is allowed for the tdd-plan push of stubs, and when `git push` exits 141 after a hook that passed on that exact sha. Record either in the report.
- PRs stay drafts. Ship, archive and create-pr skills belong to the user.

**Report.** "Your reply is read by the orchestrator, not the user: under 30 lines, plain facts." Then the stage's report fields below, and always:
- decisions made in the user's place, one line each
- every test amended and why
- anything unticked, unverified, flaky or blocked
- the tracker writes to apply

## Stage brief

**Role and stage.** "Your stage: invoke the `<skill>` skill (Skill tool, skill "<skill>", args "<args>") and follow it to the end." Then state the stage's bounds:
- create-plan: plan only, no code, no branch, no commit.
- tdd-plan: tests and stubs only.

**Lane.** Lane letter, phase number and title, tracker issue id, risk tier (once known), plan dir as an absolute path, worktree as an absolute path, current branch and head sha, draft PR number and URL (once one exists).

**Hand-off from the previous stage.** Everything the previous stage's report said that this stage needs: decisions taken, plan corrections, fragile tests, gaps it left, amendments already on the branch, what is still red, known flakes. A stage that stopped mid-plan gets the exact state: tasks done with their shas, what is uncommitted, what is red and why.

## Stage blocks

**create-plan.** Args: the epic and phase. Rate the risk tier honestly by the skill's table: later stages are gated on it. Name the dependencies on other lanes or on code missing at the base, and the files this phase shares with another lane. Report: slug and plan path, tier with a one-line reason, tasks one per line, dependencies, decisions.

**tdd-plan.** The branch name the skill should cut from the worktree HEAD. Prove red: every new test fails on an assertion, none on a crash. Push with `--no-verify` and open the draft PR. Report: branch, commits, PR, test count per task, red proof (command and counts), suite state with stickers on, where drafts or states were saved.

**implement-plan.** Resume at the first pending task. Done means demonstrated: each task's evidence is real output, and the final gate is green. Run the touched tests on the runtime version CI pins too (read it from the CI workflow), since a local-only green has hidden runtime bugs before. The opt-in live tasks stay unticked unless the live gate covers them. Push normally when every other task is done and the gate is green. Report: tasks done of total with shas, each full gate run and what failed, the push and PR head, the runtime demonstration (command and what it showed), the CI-version run.

**review-plan.** The lane's base for scope. Points to attack, taken from the implementer's report: guards it loosened, decisions it took, the riskiest behaviour change, fragile tests. Always:
- Audit every `test(...): amend` commit on the branch: each changed an expectation because of the phase's intended behaviour, and none dropped or weakened an assertion. Restore any that did.
- Approve fixes yourself with this bar: fix real defects in this phase's scope; defer what belongs to a later phase or is a policy choice for the user; reject what is wrong.
- Spawn the reviewer subagent with `model` and `effort` named, as the shared rounds protocol says.
- Cap at the protocol's rounds. When the last round still has fixes, apply the high and medium ones, defer the rest, and say which fixes no reviewer has seen.
- **Security lanes:** frame each reviewer's ask as correctness of the boundary — "find inputs the parser or guard misclassifies", "find a path the resolver lets out" — so the review starts in round 1, not after a refusal.

Report: reviewers that ran per round, findings with fixed, deferred and rejected counts, one line per fixed and deferred finding, the verdicts asked for, the final gate, push tries and PR head, what only a live run can confirm.

**Live run.** The granted sandbox, the keys' shell file, the fixture tickets per refusal path, and the phase's live demonstration from the epic's Validation. Run it, save the transcript as evidence, and check each refusal path against its fixture. Report: each scenario's command and outcome, the bugs found with the failing output, nothing fixed. Fixes go to a separate fix stage.
