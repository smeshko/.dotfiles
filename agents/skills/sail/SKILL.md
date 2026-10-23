---
name: sail
description: "Operate the sail CLI in a repository with a `.sail/`: start a run from a ticket or pull request, inspect, resume, stop or seed runs, watch workflows, manage queues, open the dashboard, or call a port. Use when the user mentions sail, a run id, `.sail-runs/`, or `sail <command>`."
---

# sail

sail turns a ticket (or a pull request) into a pull request (or merged code) along a workflow the repository writes in `.sail/`. Each run is journaled: the workflow function re-runs from the top after every call, and journaled calls return instantly, so a run can stop and **resume** anywhere.

`sail --help` is the source of truth for commands and flags; read it rather than guessing. This skill holds what `--help` doesn't say.

Related skills: writing or changing workflows and stages is `sail-workflow`; a run that failed, blocked, suspended or was refused is `sail-debug`; setting up a new repository is `sail-init`.

## Getting `sail`

`sail` comes from the checkout at `~/Developer/Projects/sail`; it is never on npm. If `command -v sail` finds nothing, run `bun install && npm link` in the checkout. A missing-module error at startup also means `bun install` there.

Every command except `sail dashboard` runs from inside a clone that holds `.sail/project.yaml`.

## The $0 ladder

Climb it in order. Each rung costs more than the one below, so a change is proven on the cheapest rung that can show it.

1. `sail check --list`: type-checks `.sail/` and lists the workflows and stages. Every run does this first and refuses on any error.
2. `sail stage run <stage-dir> --bind name=value`: one one-step stage, with its whole contract. A `file()` binding takes a path, a `value()` binding takes JSON.
3. **Fakes**: every port on `use: fake` in `project.yaml`. The run is real but no outside system is touched. Agent answers come from `.sail/fake/harness.json`, or from `playback: <dir>` of a recording.
4. `sail <ticket> --dry-run`: runs every check a start runs on the real adapters, prints the roster and writes nothing.
5. `sail run --from-run <run> --stage <stage> [--continue]`: reruns one stage on another run's earlier calls, so the stages before it cost nothing.
6. A real run: `sail <ticket>`. **Confirm with the user first**: it claims the ticket in Linear, spends agent money, pushes a branch and opens a PR.

`--record <dir>` on a real run saves each agent session. `harness: { use: fake, playback: <dir> }` then replays them at $0.

## Runs

- **Lifecycle**: `sail <ticket>` ends **completed** (exit 0), **failed** (1) or **suspended** (2), or is **refused** (3) before any run directory exists. Exit 4 is a bug in sail itself. A suspended run (`--until <stage>`, Ctrl-C, unwatched) keeps its worktree and branch lease until `sail resume <run>` takes it to its end.
- **Refusals**: a ticket must carry the repository's `label` and be unstarted. A pull request must be open, not a draft, and labelled. `--force` overrides this and records the override.
- **Fakes keep state**: the fakes persist claims and PRs in `.sail-runs/fake/`. A second `sail FAKE-1` is refused as already claimed. `rm -rf .sail-runs/fake` resets them; `--force` runs past the claim.
- **Where a run lives**: `.sail-runs/<KEY>-<ulid>/`, in the clone, gitignored. `sail runs` lists them and `sail show <run>` prints the call table, with `--events` (replay) and `--follow` (tail live). `-q`, `-v` and `-vv` set verbosity on runs, resumes and shows.
- **Workspace**: on `git-worktree`, a run works in a detached worktree under its run directory, starting from `origin/<default>`. The clone's own checkout and uncommitted edits are never touched. A branch can hold one run at a time, machine-wide.
- **Stopping**: `sail stop <run>` fails the run (`stopped`) at its next call boundary and releases its lease.

## Watching

- A workflow is watchable when its `workflow()` declares both `watch: { every }` and `maxConcurrentRuns`.
- `sail watch a b` starts this repository's watcher in the foreground. In another terminal, `sail watch c` and `sail unwatch c` change the live watcher's watch set. The watch set is never remembered: a restarted watcher watches only what it was named.
- Ctrl-C stops polling and dispatch. Dispatched runs carry on detached.
- `sail queue ls|poll|add|requeue|drop <workflow> …` acts through the watcher, so a watcher must be running.
- A parked item failed repeatedly: diagnose it with `sail-debug`, then `requeue` it.
- `sail dashboard` is one read-only page on localhost for every watcher and run on the machine. It has no controls; act through the CLI.

## Ports from a shell

`sail port ticket-source …` and `sail port codehost …` run the configured adapter and print one line of JSON. Run either with no operation to list its operations. Reads (`get`, `links`, `get-pull-request`, `checks`, `list-designated`) are safe. Writes (`comment`, `update`, `push`, `open-pull-request`, `merge`, labels) reach real systems on real adapters, so confirm before running one by hand.

## Credentials

The real adapters read the environment only:
- `linear`: `LINEAR_API_KEY`
- `github`: `SAIL_GITHUB_TOKEN` or `GITHUB_TOKEN`
- `claude-code`: `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`

A missing key is a refusal (exit 3) that names it. Ask the user to export it; never read `.env` files.
