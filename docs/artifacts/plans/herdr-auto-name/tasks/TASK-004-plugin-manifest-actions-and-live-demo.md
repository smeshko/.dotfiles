# TASK-004: Plugin manifest, actions and live demo

Depends on: TASK-003
Suggested commit: `feat(herdr): register the auto-name plugin`

## Goal

herdr starts the daemon on its own and offers restart and resume actions, demonstrated end to end in a scratch tab.

## Files

- `herdr/plugins/auto-name/herdr-plugin.toml` — manifest
- `herdr/plugins/auto-name/README.md` — what it names, the ownership rule, the actions, where the log is

## Acceptance

- [ ] Manifest: `id = "dotfiles.auto-name"`, `min_herdr_version = "0.9.5"`, `platforms = ["macos", "linux"]`; `[[startup]] command = ["python3", "autoname.py", "start"]`
- [ ] Action `restart` ("Restart auto-naming", contexts `workspace`, `tab`, `pane`): runs `autoname.py stop` then `start`
- [ ] Action `resume` ("Resume auto-naming", contexts `tab`, `pane`): runs `autoname.py resume`
- [ ] Running `install.sh`'s plugin block (as in commit `712e12f`'s test) links the plugin; `herdr plugin list` shows it enabled
- [ ] Live demo in a scratch tab (`herdr tab create --workspace <current> --no-focus`), labels read with `herdr tab get` / `herdr pane get` after each step:
  1. fresh tab, idle shell → tab and pane named after the folder
  2. `send-text "nvim plan.md"` → `nvim plan.md` within ~3s; quit → folder name again
  3. `herdr tab rename <tab> keep-me`, then run a command → tab stays `keep-me`, pane still follows
  4. run the `resume` action for that tab → tab follows the pane again
  5. run the startup command a second time → log shows "already running"; `pgrep -f autoname.py` shows one process
- [ ] An existing Claude Code tab with a numeric label shows its session description
- [ ] Scratch tab closed after the demo

Evidence: the demo's transcript (commands and printed labels) and a `daemon.log` excerpt, pasted into the task's verification note.

## Steps

### RED
- [ ] Make this task's tests fail for the right reason — strip its pending stickers (plans through `tdd-plan`), or write non-vacuous failing tests first

### GREEN
- [ ] Implement smallest change that passes tests

### REFACTOR
- [ ] Clean up while keeping tests passing

## Notes

- herdr runs plugin commands from `HERDR_PLUGIN_ROOT` with argv, no shell; check the cwd assumption and use an absolute path from `HERDR_PLUGIN_ROOT` if relative `autoname.py` fails.
- Linking mid-session does not run startup hooks: after linking, start it with the `restart` action (or `herdr plugin action` — see `herdr plugin action --help`).
- This task has no unit tests of its own; RED is the demo failing before the manifest exists (plugin not listed, labels unchanged).
