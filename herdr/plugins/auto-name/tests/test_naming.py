import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from naming import command_name, pane_name, shorten  # noqa: E402

HOME = os.path.expanduser("~")


def shell(argvs, shell_pid=100, cwd="/src/sail"):
    procs = [{"pid": 200 + i, "name": os.path.basename(a[0]), "argv": a} for i, a in enumerate(argvs)]
    return {"shell_pid": shell_pid, "foreground_processes": procs}


class AgentPaneTest(unittest.TestCase):
    def test_uses_session_description(self):
        pane = {"agent": "claude", "terminal_title_stripped": "Failed runs analysis", "cwd": "/src/sail"}
        self.assertEqual(pane_name(pane, None), "failed runs")

    def test_generic_title_falls_back_to_agent_and_folder(self):
        for title in ["", None, "claude", "CLAUDE", "Claude Code"]:
            pane = {"agent": "claude", "terminal_title_stripped": title,
                    "foreground_cwd": "/src/sail", "cwd": "/elsewhere"}
            self.assertEqual(pane_name(pane, None), "claude · sail", title)

    def test_generic_title_in_long_folder_is_folder_only(self):
        pane = {"agent": "claude", "terminal_title_stripped": "", "cwd": "/src/project-scalpel"}
        self.assertEqual(pane_name(pane, None), "project-scalpel")

    def test_generic_title_uses_cwd_without_foreground_cwd(self):
        pane = {"agent": "codex", "terminal_title_stripped": "", "cwd": "/src/api"}
        self.assertEqual(pane_name(pane, None), "codex · api")

    def test_description_keeps_two_words_without_filler(self):
        cases = [
            ("Sail workflows for this repo", "sail workflows"),
            ("Fix the flaky queue", "fix flaky"),
            ("Herdr-auto-name plan implementation", "herdr-auto-name"),
            ("Internationalization-everywhere", "internationaliza"),
            ("The a of", "the a"),  # all filler: keep the words rather than nothing
        ]
        for title, want in cases:
            pane = {"agent": "claude", "terminal_title_stripped": title}
            self.assertEqual(pane_name(pane, None), want, title)


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
        self.assertEqual(pane_name(pane, shell([["git", "remote", "get-url", "origin"]])), "git remote")
        self.assertEqual(pane_name(pane, shell([["nvim", "a-very-long-file-name.md"]])), "nvim")

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
            (["python3", "-m", "http.server"], "http.server"),
            (["python3", "scripts/build.py", "--x"], "build.py"),
            (["node", "dist/index.js"], "index.js"),
            (["ssh", "-p", "22", "prod"], "ssh prod"),
            (["ssh", "-i", "~/.ssh/k", "-o", "A=b", "prod"], "ssh prod"),
            (["make"], "make"),
            (["git", "remote", "get-url", "origin"], "git remote get-url origin"),
        ]
        for argv, want in cases:
            self.assertEqual(command_name(argv), want, argv)


class ShortenTest(unittest.TestCase):
    def test_short_unchanged(self):
        self.assertEqual(shorten("nvim plan.md"), "nvim plan.md")
        self.assertEqual(shorten("x" * 16), "x" * 16)

    def test_at_most_two_words_within_limit(self):
        self.assertEqual(shorten("one two three"), "one two")
        self.assertEqual(shorten("project-scalpel review"), "project-scalpel")

    def test_long_word_cut_without_ellipsis(self):
        self.assertEqual(shorten("x" * 30), "x" * 16)


if __name__ == "__main__":
    unittest.main()
