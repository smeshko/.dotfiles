# TASK-001: Naming rules for panes

Depends on: None
Suggested commit: `feat(herdr): add auto-name naming rules`

## Goal

A pure function turns a pane's info and its foreground processes into the label it should have.

## Files

- `herdr/plugins/auto-name/naming.py` — `pane_name(pane, procs)`, `command_name(argv)`, `truncate(text, limit=24)`
- `herdr/plugins/auto-name/tests/test_naming.py` — unittest cases for each rule

## Acceptance

- [ ] Agent pane: `pane_name({"agent": "claude", "terminal_title_stripped": "Failed runs analysis", …}, None)` → `Failed runs analysis`
- [ ] Agent pane with an empty or generic title (empty, equal to the agent name ignoring case, `Claude Code`) → `claude · sail` (agent, `·`, basename of `foreground_cwd`, falling back to `cwd`)
- [ ] Idle shell (no procs, or the only foreground process is the shell: pid equals `shell_pid` or name in `zsh`, `bash`, `sh`, `fish`, with or without a leading `-`) → basename of `foreground_cwd`; `~` for the home directory
- [ ] `command_name`: `["nvim", "plan.md"]` → `nvim plan.md`; `["/opt/homebrew/bin/nvim", "-p", "a.md"]` → `nvim a.md`; `["npm", "run", "dev"]` → `npm dev` (same for `pnpm`, `yarn`, `bun`); `["python3", "-m", "http.server"]` → `python3 http.server`; `["python3", "scripts/build.py", "--x"]` → `build.py`; `["node", "dist/index.js"]` → `index.js`; `["ssh", "-p", "22", "prod"]` → `ssh prod`; `["make"]` → `make`
- [ ] `truncate` cuts to 24 characters including a trailing `…`; shorter text is unchanged
- [ ] A shell pane with several foreground processes (a pipeline) is named from the first one

Evidence: `python3 -m unittest discover -s herdr/plugins/auto-name/tests -v` output, pasted into the task commit's verification note.

## Steps

### RED
- [ ] Make this task's tests fail for the right reason — strip its pending stickers (plans through `tdd-plan`), or write non-vacuous failing tests first

### GREEN
- [ ] Implement smallest change that passes tests

### REFACTOR
- [ ] Clean up while keeping tests passing

## Notes

- `procs` is the `process_info` object from `pane.process_info` (`foreground_processes`, `shell_pid`), or `None` for agent panes, which are not polled.
- Flag skipping in `command_name`: drop arguments starting with `-`; for `ssh` also drop the value after `-p`, `-i`, `-l`, `-o`, `-F`, `-J`. Keep the rules a small table, not a parser per tool.
- Script interpreters (`python`, `python3`, `node`, `bun`, `deno`, `ruby`): with `-m` keep the module, otherwise show the script's basename only.
