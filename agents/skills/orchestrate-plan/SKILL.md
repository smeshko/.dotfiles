---
name: orchestrate-plan
description: Run several epic phases through create-plan, tdd-plan, implement-plan and review-plan in parallel, one worktree and one fresh subagent per stage, with a live progress board in the terminal. Stops before shipping.
argument-hint: "<phase|plan-slug>... [--until plan|tdd|implement|review]"
disable-model-invocation: true
model: opus
effort: high
---

# Orchestrate Plan

Drive N **lanes** at once. A lane is one epic phase taken from plan to reviewed draft PR in its own worktree. You are the orchestrator: you never write the lane's code. Each stage of each lane runs as a fresh subagent invoking that stage's skill. You assemble its **brief**, read its report, answer what it could not, keep the **board** current, and stop before `ship-plan`, which belongs to the user.

The user approves once, at the battle plan. After that you run autonomously and decide in their place, and the final report shows them every call you made.

## Step 1: Resolve the lanes

- Each argument is an epic phase (`7.1`) or a plan slug. For a phase, read its epic file under `docs/artifacts/epics/`: phase title, tracker issue, the epic's `Depends on:`, and any phase-level dependency.
- **Base:** when a dependency is merged, the base is the repo's default base, fetched fresh. When it sits on an unmerged branch, **stack**: the base is that branch's head sha, and the lane's PRs note it. Lanes that depend on each other run in sequence. Everything else runs in parallel.
- Check that the main checkout is clean (`git status`), and note whether `docs/` is gitignored, in which case plan files live only in the main checkout.
- Create one detached worktree per lane, as a sibling named `<repo-dir>-<issue-id-lowercased>`, at the base sha, and install dependencies in each.
- Pick a lock dir in the scratchpad for `~/.claude/skills/orchestrate-plan/scripts/with-verify-lock.sh`.

Done when: every lane has its phase, issue, base sha and worktree, and every worktree's install exited 0.

## Step 2: Battle plan, then wait

Show the user, in at most 15 lines:
- the lanes table (lane, phase, issue, worktree) and the base
- the pipeline and its gating rule (Step 3)
- what their ok covers: branch pushes, draft PRs to the PR target, tracker status updates and deferred-finding issues. Live or paid runs and secrets stay excluded unless they grant them.
- the stop before shipping

Then end your turn and wait for an explicit ok. This is the only stop. Their answer may change the gates; carry the changes into every brief.

## Step 3: Run the lanes

**Pipeline per lane:** create-plan → tdd-plan → implement-plan → review-plan. `--until` stops every lane after that stage.
- **tdd-plan:** run it when the plan's `Risk:` is `large` or `high`, the tiers create-plan recommends it for. Otherwise implement-plan cuts the branch.
- **review-plan:** runs for every tier. It scales its own depth by risk.

**Spawning a stage:**
- Use the Agent tool, `general-purpose`, in the background, with a brief built from [`references/brief.md`](references/brief.md).
- Name `model` and `effort` on every spawn, read from the stage skill's own frontmatter (`sed -n '1,12p' ~/.claude/skills/<skill>/SKILL.md`). A spawn without them runs on the session's fallback subagent model. A skill invoked inside a subagent does not switch to its frontmatter model. An unnamed model once ran a whole four-lane pipeline on Haiku.
- After the first spawn of each stage type, check its transcript: `~/.claude/skills/orchestrate-plan/scripts/model_audit.sh <label>=<output_file>`. A top model other than the requested one means stop and fix the spawn before launching more.

**Advancing:**
- When a stage reports, read it fully: done or not, gate result, decisions, amendments, gaps.
- Launch the lane's next stage right away, with a hand-off of everything the next stage needs.
- A stage that stopped mid-plan with no blocker ran out of context. Spawn a fresh agent of the same stage with the exact state (shas, what is uncommitted, what is red).
- A stage that reports a real blocker: decide it yourself when the sources answer it. Otherwise park the lane as blocked, keep the other lanes going, and carry the question to the final report.

Done when: every lane has finished its last stage, or is parked with its blocker named.

## Step 4: Keep the board current

Print the board after every stage transition, and whenever the user asks. Build it from the reports plus `~/.claude/skills/orchestrate-plan/scripts/lane_status.sh <lock-dir> <base> <lane>=<worktree>:<plan-dir> ...`:

```
<REPO> · <N> lanes · base <sha> · <HH:MM>
Lane  Phase   Risk   Plan     TDD          Impl     Review               Verify        PR
A     7.1 …   large  ✓ 12 t   ✓ 148 tests  ▶ 6/12   ·                    ·             #22 draft
Legend: ✓ done  ▶ running  · pending  skip  ✗ failed  ⏸ blocked
Last:   <the event that changed the board>
Next:   <what runs next, per lane>
```

- Mark task counts read from commit logs with `~`.
- An interim notice ("still waiting on its run") gets one line, not a board.
- Prose beyond the board stays short and plain-language. Surface only what changes the user's picture: a guard loosened, a departure from the epic, a lane at risk, an item they will own.

## Step 5: Watch for stalls and load

- **Stall:** a subagent ended its turn waiting on a background notice, and `lane_status.sh` shows no new commits, no running process for it and a free lock. Nudge it with SendMessage: read the run's output now, finish the remaining steps, report.
- **Retry loop:** a lane on its third full gate run. Ask it for the per-run failure list and the flake-or-real rule from the brief. Cap it at two more runs before it reports.
- **Load:** parallel full suites starve each other into timeout flakes. One full gate at a time, through the lock. Narrow per-task runs in between. When a lane can never get a clean run under load, run its gate yourself once the machine is quiet. On a quiet machine, a red result is more likely real than a flake.

## Step 6: Final report

Print the final board, then:
- **Model audit:** run `~/.claude/skills/orchestrate-plan/scripts/model_audit.sh` over every stage transcript and show a table of stage, requested model, model that ran.
- **Trust, per lane:** low, medium or high, with the reason, weighing:
  - which model wrote the code
  - review rounds and whether they still found new issues (a security boundary that yields new bypasses every round is low trust, and may need a different design)
  - fixes no reviewer re-checked
  - test amendments
  - guards loosened
  - live paths never run
- **Owed by the user:** live runs, policy decisions, locked-test sign-offs, the decisions you took that change behaviour against the epic.
- **Tracker:** the deferred-finding issues, as a range or list.
- **Worktrees:** what is left on disk.

Stop there. Shipping is the user's call: `ship-plan` per lane.
