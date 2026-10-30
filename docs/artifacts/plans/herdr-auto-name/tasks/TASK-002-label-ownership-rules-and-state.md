# TASK-002: Label ownership rules and state

Depends on: None
Suggested commit: `feat(herdr): add auto-name label ownership`

## Goal

The plugin can tell whether a tab or pane label is its own to change, remember what it set across restarts, and take a label back on "resume".

## Files

- `herdr/plugins/auto-name/ownership.py` — `Ownership` class: `load(path)`, `owns_tab(tab_id, label)`, `owns_pane(pane_id, label)`, `record(kind, id, label)`, `resume(kind, id, label)`, `forget(kind, id)`, `save()`
- `herdr/plugins/auto-name/tests/test_ownership.py` — unittest cases

## Acceptance

- [ ] `owns_tab` is true for an all-digit label (`"1"`, `"12"`) and for the label last recorded for that tab; false for any other label (`"watcher"`)
- [ ] `owns_pane` is true for a missing/`None` label and for the label last recorded for that pane; false otherwise
- [ ] After `record("tab", "w1:t1", "npm dev")`, a user rename to `"api"` makes `owns_tab("w1:t1", "api")` false, and it stays false when contents change
- [ ] `resume("tab", "w1:t1", "api")` makes `owns_tab("w1:t1", "api")` true
- [ ] `save()` then `load()` round-trips the recorded labels; `load()` of a missing or corrupt file starts empty instead of raising
- [ ] `save()` writes atomically (temp file + `os.replace`)
- [ ] `forget` drops a closed tab's or pane's entry

Evidence: `python3 -m unittest discover -s herdr/plugins/auto-name/tests -v` output.

## Steps

### RED
- [ ] Make this task's tests fail for the right reason — strip its pending stickers (plans through `tdd-plan`), or write non-vacuous failing tests first

### GREEN
- [ ] Implement smallest change that passes tests

### REFACTOR
- [ ] Clean up while keeping tests passing

## Notes

- State file: `$HERDR_PLUGIN_STATE_DIR/labels.json`, shape `{"tabs": {id: label}, "panes": {id: label}}`. The path is passed in, so tests use a temp dir.
- Pane and tab ids are only unique within a server's lifetime, so stale entries are harmless but get dropped by `forget` on close events and by a prune of ids not in the startup snapshot (TASK-003).
