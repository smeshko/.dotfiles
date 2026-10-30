# TASK-003: Auto-name daemon

Depends on: TASK-001, TASK-002
Suggested commit: `feat(herdr): add auto-name daemon`

## Goal

A single long-running process keeps every owned pane and tab label in step with its contents, from herdr events plus a 2s poll of shell panes.

## Files

- `herdr/plugins/auto-name/autoname.py` — entrypoint with subcommands `run` (foreground loop), `start` (detach and run), `stop`, `resume`
- `herdr/plugins/auto-name/tests/test_daemon.py` — tests for the tick logic against a fake client

## Acceptance

- [ ] `autoname.py run` takes `fcntl.flock(LOCK_EX | LOCK_NB)` on `$HERDR_PLUGIN_STATE_DIR/daemon.lock` and writes its pid there; a second `run` exits 0 at once with "already running"
- [ ] On start it reads `pane.list` and `tab.list`, prunes ownership entries for ids not present, and marks everything dirty
- [ ] It subscribes on a second connection to `pane.created`, `pane.closed`, `pane.updated`, `pane.moved`, `pane.agent_detected`, `tab.created`, `tab.closed`, `tab.renamed`, and marks the affected pane, and its tab, dirty
- [ ] `tab_renamed` / pane label changes whose label differs from the recorded one are left alone (ownership decides); close events call `forget`
- [ ] Every 1s tick: for dirty panes compute `pane_name`; shell panes (no `agent`) that are owned or in an owned tab get `pane.process_info` every 2s; the tab's label comes from `pane.layout` `panes[0]`'s name
- [ ] A rename is sent only when owned, different from the current label, and ≥2s after the last rename of that target; the label is recorded in ownership before the request
- [ ] When the event connection closes or errors, the process saves state and exits 0; the lock is released by exit
- [ ] `start` double-forks (`os.fork` + `os.setsid`), points stdio at `$HERDR_PLUGIN_STATE_DIR/daemon.log`, and returns 0 to the caller
- [ ] `stop` sends SIGTERM to the pid in the lock file if the lock is held; SIGTERM saves state and exits
- [ ] `resume` reads `HERDR_TAB_ID` / `HERDR_PANE_ID`, records their current labels as owned in `labels.json`, then sends SIGHUP to the daemon, which reloads ownership and marks those targets dirty
- [ ] Tick-logic tests with a fake client cover: owned tab renamed from its first pane, manual tab label untouched, debounce suppresses a second rename within 2s, no-op rename skipped

Evidence: unittest output, plus `autoname.py run` started by hand in a terminal against the live server with its log showing the startup sweep and at least one rename.

## Steps

### RED
- [ ] Make this task's tests fail for the right reason — strip its pending stickers (plans through `tdd-plan`), or write non-vacuous failing tests first

### GREEN
- [ ] Implement smallest change that passes tests

### REFACTOR
- [ ] Clean up while keeping tests passing

## Notes

- Copy the socket `request()` pattern from `bin/herdr-equalize-panes` (one connection per request, read until newline); socket path from `HERDR_SOCKET_PATH`, default `~/.config/herdr/herdr.sock`. Keep one helper module-local; don't import from `bin/`.
- Read the subscription socket with a short timeout (≈0.5s) so the same thread can run ticks; no threads needed.
- Keep the herdr calls behind a small client object (`list_panes`, `list_tabs`, `layout`, `process_info`, `rename_pane`, `rename_tab`) so tests swap in a fake.
- Log one line per rename (`tab w22:t1 "1" -> "npm dev"`) and per error; never crash the loop on a single failed request.
