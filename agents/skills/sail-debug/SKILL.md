---
name: sail-debug
description: Diagnose a sail run that failed, blocked, suspended, was refused, or a queue item that parked, from its run directory and events, then fix it and prove the fix at $0. Use when a `sail` command exits non-zero, a run id is reported broken, or the dashboard shows a failure, denial or parked item.
---

# Debugging a sail run

Every fact about a run is on disk in `.sail-runs/<run>/`, so read the evidence before you form a theory. The run directory is the **evidence**: `STATUS`, `summary.json`, `events.ndjson`, `journal.ndjson`, `run.json` (the roster: stages, permissions, budgets, versions), and one `NN-<stage>/call-N/` per call.

## Steps

### 1. Classify the stop

Read the exit code, or run `cat .sail-runs/<run>/STATUS` and `sail show <run>`. Find the row in the table below.

| Exit / status | Stop reason | Look at | Usual fix |
|---|---|---|---|
| 3, refused | — (no run dir) | the one `sail <cmd>: …` line | config, credentials, type errors (`sail check`), label or state (`--force`), leased branch |
| 1, failed | `workflow_failed` | the call before it: its `outcome` and `reason` | the agent said `blocked`, or a `run.fail` branch fired as designed: fix the prompt or the input, not the engine |
| 1, failed | `stage_error` | the call's `result.json` errors, plus `session.log` or `stderr.log` | a broken contract: invalid output after retry, missing produced file, unmapped exit code, step budget, harness error |
| 1, failed | `determinism_violation` | the workflow diff since the run started | the body branched on something besides results (the clock, the filesystem, randomness), or the workflow changed under a resume: start a new run |
| 1, failed | `stopped` | — | someone ran `sail stop` |
| 2, suspended | `until`, `interrupted`, `unwatched` | — | `sail resume <run>` |
| 4 | — | the stack | a bug in sail itself: report it, don't work around it |

Done when you can name the stop reason and the one call it points at, or the refusal's cause.

### 2. Read the failing call

In `NN-<stage>/call-N/`, where `NN` numbers the stages in the order they were first called and `call-N` is that stage's Nth call:
- `result.json` holds the outcome, output, the files with their sha256, and the contract errors.
- An agent call has `prompt.md` (what the agent was told) and `session.log` (what it did).
- A script call has `stdout.log` and `stderr.log`. The last line of stdout must be the JSON output.
- `in/` holds the materialised bindings.
- `try-2/` exists when an invalid output was retried.

For the run's history, `sail show <run> --events -vv` replays every event. Grep `events.ndjson` for `permission:denied` (it names the rule that refused), `output:invalid`, `error:*` and `budget:*`.

Done when you can quote the line of evidence that shows the cause: the validation error, the denied command and its rule, the exit code, the agent's blocked reason.

### 3. Fix at the cause

- A **denial** the step needed: widen that step's `permissions` by the narrowest pattern.
- **Invalid output**: tighten the prompt's description of the output, or loosen the schema only if the schema was wrong.
- A **wrong route**: fix the workflow's condition.

For writing or changing a stage, use `sail-workflow`.

### 4. Prove the fix at $0, then continue

Reproduce at $0 first:
- `sail stage run <stage-dir> --bind …` for a one-step stage.
- `sail run --from-run <run> --stage <stage>`, which reuses the calls before it.
- A fake run with an answer that reproduces the failure.

Then decide how to continue:
- **Suspended run**: `sail resume <run>`.
- **Failed run**: it is final. Start a seeded run with `sail run --from-run <run> --stage <stage> --continue`, which gets a new run id and replays the calls before the stage. Only start a fresh `sail <ticket>` with the user's go-ahead: it spends money, and the ticket may need `--force` because the first run claimed it.
- **Parked queue item**: `sail queue requeue <workflow> <item>` once the cause is fixed.

Done when the reproduction shows the corrected outcome. Don't rerun until it does.
