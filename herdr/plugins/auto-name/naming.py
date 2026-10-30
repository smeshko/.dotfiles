"""What a pane should be called, from its info and its foreground processes."""
import os

LIMIT = 24
SHELLS = {"zsh", "bash", "sh", "fish"}
GENERIC_TITLES = {"", "claude code"}
# `npm run dev` → `npm dev`
RUNNERS = {"npm", "pnpm", "yarn", "bun"}
# Shown as the script's basename, or `<tool> <module>` with -m.
INTERPRETERS = {"python", "python3", "node", "bun", "deno", "ruby"}
# Flags whose value is a separate argument to drop as well.
VALUE_FLAGS = {"ssh": {"-p", "-i", "-l", "-o", "-F", "-J"}}


def truncate(text, limit=LIMIT):
    return text if len(text) <= limit else text[: limit - 1] + "…"


def folder_name(path):
    if not path:
        return ""
    path = os.path.normpath(path)
    if path == os.path.normpath(os.path.expanduser("~")):
        return "~"
    return os.path.basename(path) or path


def command_name(argv):
    tool = os.path.basename(argv[0])
    rest = list(argv[1:])
    if tool in RUNNERS and rest[:1] == ["run"]:
        rest = rest[1:]
    elif tool in INTERPRETERS or tool.startswith("python"):
        if "-m" in rest and rest.index("-m") + 1 < len(rest):
            return f"{tool} {rest[rest.index('-m') + 1]}"
        scripts = [a for a in rest if not a.startswith("-")]
        if scripts:
            return os.path.basename(scripts[0])
    value_flags = VALUE_FLAGS.get(tool, set())
    args, skip = [], False
    for arg in rest:
        if skip:
            skip = False
        elif arg in value_flags:
            skip = True
        elif not arg.startswith("-"):
            args.append(arg)
    return " ".join([tool] + args)


def is_shell(proc, shell_pid):
    return proc.get("pid") == shell_pid or proc.get("name", "").lstrip("-") in SHELLS


def pane_name(pane, procs):
    cwd = pane.get("foreground_cwd") or pane.get("cwd")
    agent = pane.get("agent")
    if agent:
        title = (pane.get("terminal_title_stripped") or "").strip()
        if title.lower() in GENERIC_TITLES | {agent.lower()}:
            return truncate(f"{agent} · {folder_name(cwd)}")
        return truncate(title)
    running = [p for p in (procs or {}).get("foreground_processes") or []
               if not is_shell(p, procs.get("shell_pid"))]
    if running and running[0].get("argv"):
        return truncate(command_name(running[0]["argv"]))
    return truncate(folder_name(cwd))
