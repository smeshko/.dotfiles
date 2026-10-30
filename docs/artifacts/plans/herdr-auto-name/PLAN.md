# Plan: herdr auto-name plugin

Status: in-progress
Branch: feature/herdr-auto-name
Risk: medium
Epic: none
Phase: none
Linear: none
Created: 2026-10-30

## Goal

herdr tabs and panes name themselves from what they are running, and keep the name current: an agent pane shows its session description, a shell shows its running command or its folder, and names the user set by hand are never overwritten.

## Scope

- A local herdr plugin at `herdr/plugins/auto-name/` (python3 stdlib only), linked on every machine by `install.sh`'s existing plugin loop (commit `712e12f`)
- Pane labels from each pane's own contents; tab labels from the tab's first pane in layout order
- A long-running daemon started by the plugin's startup hook, event-driven for titles and polling for shell commands
- Actions: "Restart auto-naming" and "Resume auto-naming" (for the focused tab and pane)
- Unit tests for the naming and ownership rules; a live demo in a scratch tab

## Out of Scope

- Workspace names
- Repo/branch names for idle shells (user chose folder name)
- A zsh `preexec` hook that sets the terminal title to make shells event-driven (polling is enough; revisit if polling cost shows up)
- Config file for the rules (constants in code until a second machine needs different values)
- Publishing to the herdr marketplace

## Research Summary

Verified against herdr 0.9.5 in this session:

- **Plugin shape** — a directory with `herdr-plugin.toml` (`id`, `name`, `version`, `min_herdr_version` required; `[[startup]]`, `[[actions]]` with argv `command`, no shell). Commands get `HERDR_SOCKET_PATH`, `HERDR_BIN_PATH`, `HERDR_PLUGIN_STATE_DIR`, `HERDR_PLUGIN_CONTEXT_JSON`, `HERDR_TAB_ID`, `HERDR_PANE_ID`, `HERDR_PLUGIN_ACTION_ID`. Docs: https://raw.githubusercontent.com/herdrdev/herdr/v0.9.5/docs/next/website/src/content/docs/plugins.mdx
- **Startup hooks are one-shot**, not supervised. They run after the server restores the session and again on live handoff, but not on `plugin link`/`enable`. A daemon has to detach itself and guard against duplicates.
- **Socket API** — newline-delimited JSON over the Unix socket, same as `bin/herdr-equalize-panes`'s `request()`. Request/response: `{"id","method","params"}` → `{"id","result"}` or `{"id","error"}`. Schema: `herdr api schema --output <path>`.
- **Events** — `events.subscribe` with `{"subscriptions":[{"type":"pane.updated"}, …]}` on a dedicated connection. First line `{"result":{"type":"subscription_started"}}`, then `{"event":"pane_updated","data":{"type":"pane_updated","pane":{…}}}`. Types used: `pane.created`, `pane.closed`, `pane.updated`, `pane.moved`, `pane.agent_detected`, `tab.created`, `tab.closed`, `tab.renamed`.
- **Title changes are evented** — an OSC 0 title set in a pane emitted `pane_updated` carrying the new `terminal_title` within a second (tested).
- **Command changes are not** — starting `sleep 4` in a shell emitted no event; `pane.process_info` reported it (`foreground_processes[].argv/cmdline/name/pid`, `shell_pid`). Shell panes must be polled.
- **Pane info** — `pane_id`, `tab_id`, `workspace_id`, `agent` (absent for shells), `agent_status`, `cwd`, `foreground_cwd`, `terminal_title`, `terminal_title_stripped` (Claude Code's session description, spinner glyph removed: `✳ Failed runs analysis` → `Failed runs analysis`), `label` (absent when unset).
- **Tab info** — `tab_id`, `label`, `number`, `pane_count`. An unnamed tab's label is its number as a string (`"1"`).
- **Layout** — `pane.layout` (`herdr pane layout --pane ID`) returns `layout.panes` in order; `panes[0]` is the tab's first pane.
- **Renames** — `pane.rename {pane_id, label|null}`, `tab.rename {tab_id, label}`. `tab_renamed` carries the new label but not who set it.

## Decisions

- **Rename panes and tabs; the tab takes its first pane's name** — user's choice. First pane in layout order is stable when focus moves.
- **Never overwrite manual names, without a pin list** — a tab is the plugin's to rename only while its label is all digits (herdr's default) or equals the last label the plugin set; a pane only while it has no label or the plugin's last label. A user rename breaks that match, so the plugin stops by itself. "Resume" records the current label as the plugin's own. One rule replaces separate pin state.
- **Idle shell = folder name** — user's choice; no git call per poll.
- **Python stdlib, raw socket** — matches `bin/herdr-equalize-panes`; no subprocess per call, no dependencies.
- **Tick loop instead of per-event renames** — events and polls only mark targets dirty; a 1s tick computes names and renames at most once per 2s per target. This debounces agent title churn and avoids rename storms on startup.
- **`fcntl.flock` lock, not a pid check** — the lock dies with the process, so a crashed daemon never blocks the next start.
- **Daemon exits when its event connection closes** — the server stopped; the next server's startup hook starts a fresh one.

## Risks

- **Rename feedback loop** — the plugin's own `tab.rename` emits `tab_renamed`. Mitigation: record the label in state before the request, so the echoed event matches and is ignored.
- **A user rename to exactly the plugin's current label** is indistinguishable from the plugin's own. Mitigation: accepted; the next content change renames it, and the user can rename again.
- **Polling cost** — one `pane.process_info` per shell pane every 2s. Mitigation: poll only panes that the plugin owns (or whose tab it owns) and that have no `agent`; measure in TASK-004's demo.
- **Duplicate daemons on live handoff** — the startup hook runs again. Mitigation: the flock; the second process exits at once.
- **herdr API drift** (pre-1.0) — Mitigation: `min_herdr_version = "0.9.5"`; requests fail loudly into the log rather than guessing.

## Acceptance Criteria

- [ ] An unnamed tab whose first pane runs Claude Code is labelled with the session description within ~2s of the title changing
- [ ] A shell pane running `nvim plan.md` is labelled `nvim plan.md`; when the command exits it becomes the folder name
- [ ] A tab or pane renamed by hand keeps that name while its contents change; "Resume auto-naming" brings auto-naming back
- [ ] Only one daemon runs after startup, a repeated startup hook, and "Restart auto-naming"
- [ ] `python3 -m unittest discover -s herdr/plugins/auto-name/tests` passes
- [ ] A fresh clone gets the plugin from `install.sh` with no extra step

## Tasks

Task state lives here. Tasks are appended by `scripts/add_task.py` and
`scripts/add_final_task.py`. Update the checkboxes as work progresses.

- [x] TASK-001: Naming rules for panes
- [x] TASK-002: Label ownership rules and state
- [ ] TASK-003: Auto-name daemon (depends on TASK-001,TASK-002)
- [ ] TASK-004: Plugin manifest, actions and live demo (depends on TASK-003)
- [ ] TASK-005: Final Validation
