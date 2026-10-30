# auto-name

A herdr plugin that names tabs and panes after what they run and keeps the names current.

## What it names

- **Agent pane**: the first two words of the agent's session description, lowercased and without filler words: `Sail workflows for this repo` becomes `sail workflows`. A generic or empty title becomes `claude · <folder>`, or just the folder when that is too long.
- **Shell pane running a command**: the command without its flags, e.g. `nvim plan.md`, `npm dev`, `http.server`, `build.py`, `ssh prod`.
- **Idle shell**: its folder name, or `~` for home.
- **Tab**: the name of its first pane in layout order.

Labels keep at most two words and 16 characters (the sidebar shows about 17), cut at a word boundary without `…`.

## Names set by hand are kept

The plugin renames a tab only while its label is its number (herdr's default) or the last label the plugin set. It renames a pane only while the pane has no label or has the plugin's last label. Renaming a tab or pane yourself breaks that match, so the plugin leaves it alone from then on.

## Actions

- **Restart auto-naming** (workspace, tab, pane): stops the daemon and starts a new one.
- **Resume auto-naming** (tab, pane): hands the focused tab's and pane's current labels back to the plugin, so it renames them again.

## How it runs

The startup hook runs `autoname.py start`, which detaches one daemon per server. A lock on `daemon.lock` keeps it to one. Title changes arrive as herdr events; shell commands are polled every 2s for the panes the plugin owns. A target is renamed at most once every 2s. The daemon exits when the herdr server goes away.

Linking the plugin mid-session does not run the startup hook. Run **Restart auto-naming** once instead.

State lives in `$HERDR_PLUGIN_STATE_DIR` (`~/.local/state/herdr/plugins/dotfiles.auto-name/`):

- `daemon.log`: one line per rename and per error
- `labels.json`: the labels the plugin set, by tab and pane id
- `daemon.lock`: the running daemon's pid

## Tests

```sh
python3 -m unittest discover -s herdr/plugins/auto-name/tests -v
```
