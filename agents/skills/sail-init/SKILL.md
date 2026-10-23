---
name: sail-init
description: "Set up sail in a repository: `sail init`, config, fakes, a first workflow proven at $0, then the switch to Linear, GitHub, Claude Code and git worktrees."
disable-model-invocation: true
---

# Setting up sail in a repository

Each rung below ends on something that runs. Each rung costs no more than the next one up: fakes first, real adapters last. For CLI basics see `sail`, and for writing the workflow see `sail-workflow`.

## Steps

### 1. Preconditions

You need:
- the repository's root, a git clone (an `origin` on GitHub matters only from step 6)
- `sail --version` working (see the `sail` skill)
- no `.sail/` yet

`sail init` refuses outside git, in `$HOME`, and over an existing `.sail`.

Done when all three hold.

### 2. `sail init`

Run it at the root. It writes:
- `.sail/project.yaml`, with every port on `fake`
- `.sail/tsconfig.json`
- the two editor declarations
- three `.gitignore` lines

It writes no workflow.

Done when the command prints its `next:` line.

### 3. Fill in `project.yaml`

`sail init` writes `name`, `sail`, `label` and `adapters`. It leaves `models` and `budgets` out and `defaultWorkflow` commented. Ask the user for anything you can't infer.
- `name`: a slug, unique among this machine's watchers.
- `label`: the designation label for tickets and PRs, unique per ticket source. Defaults to `sail-<name>`.
- `models`: aliases to model ids. Agents default to `default`, so define at least `default` (and usually `deep`). `sail check` refuses an agent stage whose alias is missing.
- `budgets.run`: `{ maxUsd, maxMinutes }`.
- Optional:
  - `branchPrefix` (default `sail/`)
  - `conventions` (the files appended to every prompt, by default `AGENTS.md` and `CLAUDE.md`)
  - `defaultWorkflow`, once a workflow exists

Done when every field above is set or deliberately left at its default.

### 4. A first workflow on fakes

Write the workflow with `sail-workflow`, or start from the `workflows/` and `stages/` of `~/Developer/Projects/sail-sandbox-live/.sail/` and adapt them. Leave out its `project.yaml`, which is on real adapters. Seed the fakes:
- `.sail/fake/tickets.json`: at least one ticket with the `label` and `state.type: unstarted`
- `.sail/fake/harness.json`: an answer per agent stage

Copy their format from `~/Developer/Projects/sail/test/fixtures/repo/.sail/fake/`. Set `defaultWorkflow`.

Done when `sail check --list` exits 0 and `sail <FAKE-n>` completes. Show the user the `sail show <run>` table.

### 5. Commit `.sail/`

Commit `.sail/`, without the generated `sail.d.ts` and `sail-intakes.d.ts`, and the `.gitignore` change, on a branch and in the repository's own commit style. Check that `.sail-runs/` is ignored.

Done when `git status` is clean apart from ignored files.

### 6. Switch to the real adapters

The real adapters need the clone's `origin` on GitHub. A port that breaks is easier to find one at a time, so switch them one at a time:

| Port | `project.yaml` | Options | Credentials |
|---|---|---|---|
| ticketSource | `{ use: linear, team: ABC }` | `inReview`: the name of a started state, enabling `--state in-review` | `LINEAR_API_KEY` |
| codeHost | `{ use: github }` | `repository: owner/name` (default: from the remote), `remote`, `draft` | `SAIL_GITHUB_TOKEN` or `GITHUB_TOKEN`, with contents and pull-requests write |
| harness | `{ use: claude-code }` | none | `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` |
| workspace | `{ use: git-worktree }` | `remote`, `defaultBranch` | none |

Ask the user to export the keys; never read `.env` files. Make sure the `label` exists in the Linear team and is applied to one test ticket in an unstarted state.

To read a ticket safely, run `sail port ticket-source get <KEY>`. Then run `sail <KEY> --dry-run`, which checks everything a start checks and writes nothing.

Done when `--dry-run` exits 0 and prints the roster on the real adapters.

### 7. First real run (user's go-ahead)

A real run claims the ticket, spends agent money, pushes a branch and opens a PR. Ask before you start it. Use `--record <dir>` so its sessions can be replayed at $0 later. Use `--until <stage>` to stop after an early stage and inspect it. Follow it with `sail show <run> --follow` or `sail dashboard`.

Done when the run completes and the user has seen its PR. If it doesn't complete, hand over to `sail-debug`.

### 8. Optional: watching

Add `watch: { every: '5m' }` and `maxConcurrentRuns` to the workflow. Then `sail watch <workflow>` and `sail queue ls <workflow>`.

Done when the watcher picks up a labelled ticket on its own.
