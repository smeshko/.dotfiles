import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from naming import command_name, pane_name, truncate  # noqa: E402

HOME = os.path.expanduser("~")


def shell(argvs, shell_pid=100, cwd="/src/sail"):
    procs = [{"pid": 200 + i, "name": os.path.basename(a[0]), "argv": a} for i, a in enumerate(argvs)]
    return {"shell_pid": shell_pid, "foreground_processes": procs}


class AgentPaneTest(unittest.TestCase):
    def test_uses_session_description(self):
        pane = {"agent": "claude", "terminal_title_stripped": "Failed runs analysis", "cwd": "/src/sail"}
        self.assertEqual(pane_name(pane, None), "Failed runs analysis")

    def test_generic_title_falls_back_to_agent_and_folder(self):
        for title in ["", None, "claude", "CLAUDE", "Claude Code"]:
            pane = {"agent": "claude", "terminal_title_stripped": title,
                    "foreground_cwd": "/src/sail", "cwd": "/elsewhere"}
            self.assertEqual(pane_name(pane, None), "claude · sail", title)

    def test_generic_title_uses_cwd_without_foreground_cwd(self):
        pane = {"agent": "codex", "terminal_title_stripped": "", "cwd": "/src/api"}
        self.assertEqual(pane_name(pane, None), "codex · api")

    def test_long_description_truncated(self):
        pane = {"agent": "claude", "terminal_title_stripped": "A very long session description here"}
        self.assertEqual(pane_name(pane, None), "A very long session des…")


class ShellPaneTest(unittest.TestCase):
    def test_idle_without_procs_is_folder(self):
        self.assertEqual(pane_name({"foreground_cwd": "/src/sail"}, None), "sail")

    def test_idle_shell_by_pid_or_name_is_folder(self):
        pane = {"foreground_cwd": "/src/sail", "cwd": "/x"}
        by_pid = {"shell_pid": 7, "foreground_processes": [{"pid": 7, "name": "whatever", "argv": ["whatever"]}]}
        self.assertEqual(pane_name(pane, by_pid), "sail")
        for name in ["zsh", "-zsh", "bash", "sh", "fish", "-fish"]:
            procs = {"shell_pid": 1, "foreground_processes": [{"pid": 9, "name": name, "argv": [name]}]}
            self.assertEqual(pane_name(pane, procs), "sail", name)
        self.assertEqual(pane_name(pane, {"shell_pid": 1, "foreground_processes": []}), "sail")

    def test_home_is_tilde(self):
        self.assertEqual(pane_name({"foreground_cwd": HOME}, None), "~")
        self.assertEqual(pane_name({"foreground_cwd": HOME + "/"}, None), "~")

    def test_running_command(self):
        pane = {"foreground_cwd": "/src/sail"}
        self.assertEqual(pane_name(pane, shell([["nvim", "plan.md"]])), "nvim plan.md")

    def test_pipeline_named_from_first_process(self):
        pane = {"foreground_cwd": "/src/sail"}
        self.assertEqual(pane_name(pane, shell([["tail", "-f", "log"], ["grep", "err"]])), "tail log")

    def test_group_leader_wins_over_its_short_lived_children(self):
        procs = {"shell_pid": 1, "foreground_process_group_id": 30, "foreground_processes": [
            {"pid": 61, "name": "git", "argv": ["git", "remote", "get-url", "origin"]},
            {"pid": 30, "name": "make", "argv": ["make", "watch"]},
        ]}
        self.assertEqual(pane_name({"foreground_cwd": "/src/sail"}, procs), "make watch")


class CommandNameTest(unittest.TestCase):
    def test_table(self):
        cases = [
            (["nvim", "plan.md"], "nvim plan.md"),
            (["/opt/homebrew/bin/nvim", "-p", "a.md"], "nvim a.md"),
            (["npm", "run", "dev"], "npm dev"),
            (["pnpm", "run", "dev"], "pnpm dev"),
            (["yarn", "run", "dev"], "yarn dev"),
            (["bun", "run", "dev"], "bun dev"),
            (["python3", "-m", "http.server"], "python3 http.server"),
            (["python3", "scripts/build.py", "--x"], "build.py"),
            (["node", "dist/index.js"], "index.js"),
            (["ssh", "-p", "22", "prod"], "ssh prod"),
            (["ssh", "-i", "~/.ssh/k", "-o", "A=b", "prod"], "ssh prod"),
            (["make"], "make"),
        ]
        for argv, want in cases:
            self.assertEqual(command_name(argv), want, argv)


class TruncateTest(unittest.TestCase):
    def test_short_unchanged(self):
        self.assertEqual(truncate("nvim plan.md"), "nvim plan.md")
        self.assertEqual(truncate("x" * 24), "x" * 24)

    def test_long_cut_to_limit_with_ellipsis(self):
        out = truncate("x" * 30)
        self.assertEqual(len(out), 24)
        self.assertEqual(out, "x" * 23 + "…")


if __name__ == "__main__":
    unittest.main()
