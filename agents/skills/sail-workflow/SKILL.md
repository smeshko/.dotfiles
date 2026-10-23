---
name: sail-workflow
description: "Write or change a sail workflow or stage under `.sail/`: `workflow.ts` composition, agent and script stages, prompts, output schemas, document templates, loops, parallel calls, fake answers. Use when creating a workflow, adding or editing a stage, or wiring stages together."
---

# Writing a sail workflow

A workflow is **composition**: plain TypeScript that calls stages and routes on their results. Every contract lives on a stage. The engine runs the workflow function again from the top after each call and replays the journaled calls, so the body is **deterministic**: it branches only on stage results and `run.input`, never on the clock, randomness, the filesystem or the network.

[`CONTRACT.md`](CONTRACT.md) is the reference for bindings, `produces`, documents, permissions, budgets, the script environment, prompt templates and fake answers. For exact signatures, read the SDK declarations in `~/Developer/Projects/sail/types/` (`workflow.d.ts`, `steps.d.ts`, `bindings.d.ts`, `documents.d.ts`, `intakes.d.ts`).

**Models to copy**:
- `~/Developer/Projects/sail-sandbox-live/.sail/`: the real `ticket-to-pr`, with spec (a document), implement, tests (a script), self-review, describe and open (which pushes and opens the PR through `sail port`).
- `~/Developer/Projects/sail/test/fixtures/repo/.sail/`: the same workflow on fakes, plus a `review` workflow that runs reviewers in parallel, and `fake/*.json` seeds.

## Layout

```
.sail/workflows/<workflow>/workflow.ts           default-exports workflow(...)
.sail/workflows/<workflow>/stages/<NN>-<stage>/  private: only this workflow's folder may import it
.sail/stages/<stage>/                            shared: any workflow may import it
<stage>/stage.ts  prompt.md  run.sh  templates/*.md
```

A stage is named after its folder, less any number prefix (`03-prove-tests` is `prove-tests`), and stage names are unique within a run. Put a stage under the workflow until a second workflow needs it, then move it to `.sail/stages/`.

Prefix every private stage folder with its two-digit position in the workflow, from `00-`, so a listing reads in run order: `00-setup`, `01-plan`, `02-write-tests`. A stage that runs more than once, in a loop or a later round, keeps the position of its first call. Inserting a stage renumbers the folders after it and their imports in `workflow.ts`. Shared stages under `.sail/stages/` take no prefix, since each workflow orders them differently.

## Steps

### 1. Shape the workflow

List the stages in order. For each one, record its kind, what it consumes, what it outputs, and what it leaves:
- **agent**: judgment work. Its outcome is `done` or `blocked`, and its verdicts travel in `output`.
- **script**: deterministic work. Its exit code decides `passed` or `failed`.

Name every routing decision. **Code decides, the model reports**: an agent emits findings with a severity, and the workflow filters them (`severity === 'high'`). The agent never says "must fix". Repeated work is a `run.loop(name, { max, feedback })`, and independent work is `run.all([...])`.

Done when every stage has a kind, its bindings, an output schema and its files, and every branch of the workflow is named.

### 2. Write the stages

For each stage, write `stage.ts` with `agent()`, `script()` or `stage()` (several steps sharing `$STAGE_OUT`). Then write its `prompt.md` or `run.sh`, and its `templates/`. Export each output schema and reuse it across stages (`TestReport`, `Finding`, `Feedback`) rather than redefining it.

- **Prompts** say what to do and what to submit. The engine appends the untrusted-input and finishing fragments, plus the repository's `AGENTS.md`/`CLAUDE.md`, so leave those out of the prompt.
- **Scripts** print their JSON output as their last stdout line, and send everything else to stderr. Make a script executable (`chmod +x`). It reaches tickets and the code host only through `sail port`, never through an API client.
- **Permissions** grant the least a step needs. `$STAGE_OUT/**` must be in `write` for an agent that produces files.

Done when each stage's folder holds its contract and its body.

### 3. Compose `workflow.ts`

Rule out `blocked` and `failed` before reading `.output` or `.files`, and write `return run.fail(...)`. A bare `run.fail(...)` doesn't narrow the result, because `run` is contextually typed. In `run.all(list.map(...))`, give each call tuple `as const`. A watched workflow declares both `watch: { every: '5m' }` and `maxConcurrentRuns`.

Done when `sail check --list` exits 0 and lists the workflow with every stage.

### 4. Prove it on fakes

Seed `.sail/fake/harness.json` with an answer for every agent stage (format in [`CONTRACT.md`](CONTRACT.md)). Drive each loop's failing branch at least once, either with an agent answer or with a script that plays its report by `$CALL` (see the fake workspace note there). Commit first: the fake workspace copies only committed files. Then run `sail <FAKE-n>` with every port on `fake`. Before each rerun, `rm -rf .sail-runs/fake`: every run claims its fake ticket, even one that fails.

Done when the fake run reaches the end you designed (completed, or the `run.fail` you meant). `sail show <run>` should list every stage, and each loop's iteration count should match the answers you seeded.

### 5. Prove a changed stage cheaply

To change one stage of a workflow that already runs, use `sail stage run <stage-dir> --bind …` for a one-step stage in isolation. To change a stage in place, use `sail run --from-run <run> --stage <stage> [--continue]`. Either replaces a full run.

Done when the changed stage's call shows the outcome and output you expected. Spend real money only after this passes, and only with the user's go-ahead.
