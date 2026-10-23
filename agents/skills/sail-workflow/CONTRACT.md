# sail stage contract reference

Exact types are in `~/Developer/Projects/sail/types/`. This file holds the rules the types don't show.

## Bindings (`consumes`)

| Binding | Supplied by | Arrives as |
|---|---|---|
| `file('spec.md')` | the workflow: a file an earlier call produced, as `result.files['spec.md']` or `run.intake.files['brief.md']` | a copy in `$STAGE_IN` |
| `value(Schema)` | the workflow: a value the schema parses, such as another call's `output` | `$STAGE_IN/<name>.json`, or `.txt` for a string |
| `gitDiff('origin/main...HEAD')` | the engine | a patch |
| `fromStep('describe').output('title')` / `.file('x')` | the engine, from an earlier step of the same `stage()` | as above |

`.optional()` makes a binding optional; the workflow may pass `undefined`, as in `feedback: iteration.previous`. A `stage()` declares every binding its steps take from the workflow, under the same name.

The intakes come from `sail/intakes`:
- `ticket` leaves `ticket.json` and `brief.md`, and `run.input` is `TicketInput`.
- `pr` leaves `pr.json`, `diff.patch` and `brief.md`, and `run.input` is `PrInput`.

Human-written strings in either are branded **untrusted**, and prompts wrap them as data.

## Outcomes and results

- An agent ends `done` (with `output` and `files`) or `blocked` (with `reason`). A script ends `passed` or `failed`, each with `output`. A multi-step `stage()` takes its outcome kind and output from its last step.
- `error` (contract broken, budget exceeded, unmapped exit code) fails the run with `stage_error`, unless the call passes `{ onError: 'return' }` as a third argument.
- An invalid output is retried once with the errors fed back (`onInvalidOutput: 'retry-once'`, the default), then becomes `error`.
- `run.loop(name, { max, feedback: Schema })` yields iterations. `iteration.fail(x)` ends the pass, and the next pass reads `x` as `iteration.previous`. `break` leaves the loop.

## `produces` and documents

`produces: { 'diff.patch': 'file' }` means the file must exist in `$STAGE_OUT` when the step ends. Each produced file is recorded with its sha256.

An agent's file can instead be a **document**:

```ts
'spec.md': doc('./templates/spec.md', [hasSections('Requirements', 'Tasks'), noPlaceholders(), countItems('Tasks', { min: 1, as: 'tasks' })])
```

The template is rendered into `$STAGE_OUT` before the session. The agent completes it in place, and the validators check the result afterwards. `checklist()` counts `- [ ]` items. A validator is an object `{ check, derives, validate(doc) → { problems, derived? } }`, so a repository can write its own.

## Prompt and template syntax

- `{{name}}` and `{{name.field}}` print a string: a string field of a `value()`, or a `file()` as its path in `$STAGE_IN`. An array or object has no text to print, and the call fails before the session starts. Walk an array with `#each`, or point the agent at the binding's JSON in `$STAGE_IN`. An unbound optional is null.
- `{{#if name}}…{{else}}…{{/if}}` and `{{#each list}}{{this}}{{/each}}` give branches and lists.
- A tag with a colon, `{{goal: one paragraph}}`, is a placeholder left for the agent to fill. `noPlaceholders()` fails while any remains.
- Any other tag is a render error.

## Permissions and budgets (agent steps)

```ts
permissions: { read: ['**'], write: ['src/**', 'test/**', '$STAGE_OUT/**'], commands: ['bun test*', 'git add *', 'git commit *'], tools?: ['WebFetch', 'linear:*'], network?: 'none' }
budget: { maxTurns: 40, maxUsd: 2, maxMinutes: 10 }
```

- Commands are matched per argv segment, after pipes, `&&`, redirections and `$(…)` are parsed.
- A built-in deny set is checked first: `rm -rf`, forced push, `git reset --hard`, `git clean -f`, `git branch -D`, `git checkout`, `git switch`, `sudo`, `curl | sh`, `git -c`, and `PATH`/`LD_*` overrides. Agents never switch branches; the run owns its branch.
- Tools not listed in `tools` are denied, MCP tools included. A denial is an event, and the agent carries on.
- `model` is an alias from `project.yaml`'s `models` and defaults to `default`. `sail check` refuses an alias the config doesn't define.

## Script steps

- `run: './run.sh'` is any executable, relative to the stage folder.
- `exitCodes` defaults to `{ passed: [0], failed: [1] }`, and any other code is `error`. Write `failed: []` when a failure can only be an error, as `open` does.
- `timeoutSeconds` defaults to 600. On timeout the engine kills the script's whole process group.
- The environment holds `RUN_ID STAGE CALL TRY STAGE_IN STAGE_OUT WORKSPACE BRANCH SAIL_CONFIG`, one `INPUT_<NAME>` per binding (the binding's name upper-cased, with non-alphanumerics turned into `_`, pointing at its file in `$STAGE_IN`), and `SAIL_BUN`, the Bun running the run. `sail` on `PATH` is the sail running the run.
- The working directory is the workspace. Write produced files into `$STAGE_OUT`.
- On the fake workspace, `$WORKSPACE` is `.sail-runs/<run>/workspace`, a copy of the repository's committed files only, and fake agents change no code. A script that runs the real tests therefore gives the same result on every pass. To exercise a fix loop on fakes, the script plays its reports by `$CALL` (fail on call 1, pass later), as the fixture's `stages/tests/run.sh` does.

## Fake answers (`.sail/fake/harness.json`)

Each key maps to a list of answers by **try**, and the last answer repeats:
- A call key (`implement#2`) answers that one call.
- A stage key (`spec`, or `stage/step` inside a `stage()`) answers every call of that stage.

```json
{
  "spec": [{ "outcome": "done", "output": { … }, "files": { "spec.md": "…" }, "turns": 4, "usage": { "inputTokens": 0, "cacheReadTokens": 0, "cacheWriteTokens": 0, "outputTokens": 0, "costUsd": 0.3 } }],
  "implement#1": [{ "outcome": "done", "output": { … } }],
  "describe": [{ "outcome": "blocked", "reason": "…" }]
}
```

An answer can also be `{ "outcome": "error", "message": "…" }`. To test `retry-once`, script an invalid output as try 1 and a valid one as try 2. The fake never checks `output` against the schema; the engine does.

The other seeds use the same format as the fixture repo's: `fake/tickets.json` (`ticketKey`, `title`, `description`, `state.type`, `labels`, `comments`, `links`, `attachments`) and `fake/prs.json`. Designation needs the `label` from `project.yaml`, and `state.type: unstarted`.
