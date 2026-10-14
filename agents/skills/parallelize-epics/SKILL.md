---
name: parallelize-epics
description: Plan which epic phases can run in parallel, as a table of waves of at most 5 phases, from phase-level dependencies and file collisions. Use when the user asks what can run in parallel, how to parallelize epics or phases, or for waves. It runs without the conversation, so pass as arguments the epic numbers and any phases already running.
argument-hint: "[<epic>,...] [--running <phase>,...] [--max <n>]"
context: fork
background: false
model: opus
effort: medium
---

# Parallelize Epics

Lay out the unfinished phases of a repo's epics (`docs/artifacts/epics/`, as `create-epic` writes them) in **waves**. A wave is a set of phases that can run at once, and it starts when the wave before it has landed. The result is one table, from which a wave goes straight to `orchestrate-plan`.

The scripts own the bookkeeping: states, ordering, the cap per wave. Your part is the judgment they can't make, which phases really wait on which and which really collide.

## Arguments

- `<epic>,...`: epic numbers, comma- or space-separated (`7,8,9,10`). None, or `all`: every epic with a phase not done.
- `--running <phase>,...`: phases in flight beyond the detected ones. Detection already counts a phase whose plan is linked, or whose issue id is on a branch or a worktree path.
- `--max <n>`: phases per wave, default 5.

## Step 1: Inventory

Pick a scratch directory outside the repo (the session's scratchpad when there is one, otherwise `mktemp -d`), then run:

```bash
python3 ~/.claude/skills/parallelize-epics/scripts/phases.py <epics> [--running <phases>] --out <scratch>/graph.json
```

It records every epic's phases as `done`, `in_flight` or `todo`, and marks the selected ones.

Done when: `graph.json` exists.

## Step 2: Dependencies

For every selected `todo` phase, read its whole block in the epic file (Goal, What to build, Acceptance criteria, Validation) and its epic's `Depends on:` line. Fill `deps` with the phase ids it waits for, and `why` with a few words per id.

- The epic's `Depends on:` is an **upper bound**. Narrow it to the phases whose work this one uses: the code it extends, the interface it calls, and the command, fixture or adapter its acceptance criteria and validation run. Name the earliest phase that delivers each.
- Hunt the **hidden edges** the header misses: a phase extending a module that another epic's phase creates, or a demonstration running a command that a later phase adds.
- Name `done` and `in_flight` phases freely. The scheduler knows their state.

Set `reviewed: true` once a phase's list is final, an empty list included.

Done when: every selected todo phase is reviewed, and every edge has its `why`.

## Step 3: Collisions

Two phases **collide** when both rework the same region of the same file: the same function, the same state machine, the same hand-edited fixture. Collect the hot spots from the phases' What to build lists, then open each file to confirm the region really is shared. `git log --stat` on it shows how often past phases met there.

- List a collision in either phase's `conflicts`, and the scheduler makes it mutual. In-flight phases count.
- Additive lines (a registry entry, a union member, a dependency) and committed files that a command regenerates (generated types, golden fixtures) are a **rebase**, which parallel phases absorb. Leave them out of `conflicts`.

Done when: every pair of selected todo phases touching one file is judged a collision or a rebase.

## Step 4: Schedule

```bash
python3 ~/.claude/skills/parallelize-epics/scripts/waves.py <scratch>/graph.json [--max <n>]
```

Exit 1 names what to fix: an unreviewed phase, an unknown id, or a cycle. A cycle means one edge is wrong, so re-read both phases before dropping it.

Done when: it exits 0.

## Step 5: Report

Return the script's output unchanged: the in-flight line, the wave table and, when there is one, the blocked line. Then add two lines:

```
Start a wave: /orchestrate-plan <its phases>
Edges and reasons: <scratch>/graph.json
```
