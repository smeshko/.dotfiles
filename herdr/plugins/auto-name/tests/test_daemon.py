import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autoname import Daemon  # noqa: E402
from ownership import Ownership  # noqa: E402


class FakeClient:
    def __init__(self, panes, tabs, layouts, procs=None):
        self.panes = {p["pane_id"]: dict(p) for p in panes}
        self.tabs = {t["tab_id"]: dict(t) for t in tabs}
        self.layouts = layouts  # tab_id -> [pane_id, ...] in layout order
        self.procs = procs or {}
        self.renames = []
        self.polls = []
        self.fail_renames = False

    def list_panes(self):
        return [dict(p) for p in self.panes.values()]

    def list_tabs(self):
        return [dict(t) for t in self.tabs.values()]

    def get_pane(self, pane_id):
        return dict(self.panes[pane_id])

    def layout(self, pane_id):
        return [{"pane_id": p} for p in self.layouts[self.panes[pane_id]["tab_id"]]]

    def process_info(self, pane_id):
        self.polls.append(pane_id)
        return self.procs.get(pane_id, {"shell_pid": 1, "foreground_processes": []})

    def rename_pane(self, pane_id, label):
        if self.fail_renames:
            raise RuntimeError("boom")
        self.renames.append(("pane", pane_id, label))
        self.panes[pane_id]["label"] = label

    def rename_tab(self, tab_id, label):
        if self.fail_renames:
            raise RuntimeError("boom")
        self.renames.append(("tab", tab_id, label))
        self.tabs[tab_id]["label"] = label


def running(*argv):
    return {"shell_pid": 1, "foreground_processes": [{"pid": 5, "name": argv[0], "argv": list(argv)}]}


class DaemonTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.own = Ownership.load(os.path.join(self.dir.name, "labels.json"))
        self.client = FakeClient(
            panes=[
                {"pane_id": "p1", "tab_id": "t1", "agent": "claude", "terminal_title_stripped": "Fix the queue"},
                {"pane_id": "p2", "tab_id": "t1", "foreground_cwd": "/src/api"},
                {"pane_id": "p3", "tab_id": "t2", "foreground_cwd": "/src/web"},
            ],
            tabs=[{"tab_id": "t1", "label": "1"}, {"tab_id": "t2", "label": "watcher"}],
            layouts={"t1": ["p1", "p2"], "t2": ["p3"]},
            procs={"p3": running("npm", "run", "dev")},
        )
        self.daemon = Daemon(self.client, self.own, log=lambda line: None)
        self.daemon.snapshot()

    def tearDown(self):
        self.dir.cleanup()

    def test_owned_tab_named_from_first_pane(self):
        self.daemon.tick(100.0)
        self.assertEqual(self.client.tabs["t1"]["label"], "fix queue")
        self.assertEqual(self.client.panes["p1"]["label"], "fix queue")
        self.assertEqual(self.client.panes["p2"]["label"], "api")
        self.assertEqual(self.own.recorded("tab", "t1"), "fix queue")

    def test_manual_tab_label_untouched_but_its_panes_follow(self):
        self.daemon.tick(100.0)
        self.assertEqual(self.client.tabs["t2"]["label"], "watcher")
        self.assertNotIn(("tab", "t2", "npm dev"), self.client.renames)
        self.assertEqual(self.client.panes["p3"]["label"], "npm dev")

    def test_user_rename_after_plugin_rename_is_kept(self):
        self.daemon.tick(100.0)
        self.client.tabs["t1"]["label"] = "mine"
        self.daemon.handle({"type": "tab_renamed", "tab_id": "t1", "label": "mine"})
        self.daemon.handle({"type": "pane_updated", "pane": dict(self.client.panes["p1"], terminal_title_stripped="Other")})
        self.daemon.tick(110.0)
        self.assertEqual(self.client.tabs["t1"]["label"], "mine")
        self.assertEqual(self.client.panes["p1"]["label"], "other")

    def test_debounce_suppresses_second_rename_within_2s(self):
        self.daemon.tick(100.0)
        before = len(self.client.renames)
        self.daemon.handle({"type": "pane_updated", "pane": dict(self.client.panes["p1"], terminal_title_stripped="Second")})
        self.daemon.tick(101.0)
        self.assertEqual(len(self.client.renames), before)
        self.assertEqual(self.client.tabs["t1"]["label"], "fix queue")
        self.daemon.tick(102.5)  # still dirty, now past the window
        self.assertEqual(self.client.tabs["t1"]["label"], "second")
        self.assertEqual(self.client.panes["p1"]["label"], "second")

    def test_no_op_rename_skipped(self):
        self.daemon.tick(100.0)
        before = list(self.client.renames)
        self.daemon.handle({"type": "pane_updated", "pane": self.client.get_pane("p1")})
        self.daemon.handle({"type": "tab_renamed", "tab_id": "t1", "label": "fix queue"})
        self.daemon.tick(110.0)
        self.assertEqual(self.client.renames, before)

    def test_shell_pane_polled_for_its_command(self):
        self.daemon.tick(100.0)
        self.client.procs["p2"] = running("nvim", "plan.md")
        self.daemon.tick(101.0)  # poll interval not reached
        self.assertEqual(self.client.polls.count("p2"), 1)
        self.assertEqual(self.client.panes["p2"]["label"], "api")
        self.daemon.tick(102.0)
        self.assertEqual(self.client.panes["p2"]["label"], "nvim plan.md")

    def test_close_events_forget(self):
        self.daemon.tick(100.0)
        self.daemon.handle({"type": "pane_closed", "pane_id": "p2"})
        self.daemon.handle({"type": "tab_closed", "tab_id": "t1"})
        self.assertIsNone(self.own.recorded("pane", "p2"))
        self.assertIsNone(self.own.recorded("tab", "t1"))

    def test_tab_close_forgets_its_panes(self):
        # herdr sends no pane_closed for the panes of a closed tab.
        self.daemon.tick(100.0)
        self.daemon.handle({"type": "tab_closed", "tab_id": "t1"})
        self.assertIsNone(self.own.recorded("pane", "p1"))
        self.assertIsNone(self.own.recorded("pane", "p2"))
        self.assertEqual(self.own.recorded("pane", "p3"), "npm dev")

    def test_snapshot_prunes_unknown_ids(self):
        self.own.record("tab", "gone", "x")
        self.own.record("pane", "gone", "y")
        self.own.record("tab", "t2", "watcher")
        Daemon(self.client, self.own, log=lambda line: None).snapshot()
        self.assertIsNone(self.own.recorded("tab", "gone"))
        self.assertIsNone(self.own.recorded("pane", "gone"))
        self.assertEqual(self.own.recorded("tab", "t2"), "watcher")

    def test_failed_rename_keeps_previous_record(self):
        self.daemon.tick(100.0)
        self.client.fail_renames = True
        self.daemon.handle({"type": "pane_updated", "pane": dict(self.client.panes["p1"], terminal_title_stripped="New")})
        self.daemon.tick(110.0)
        self.assertEqual(self.own.recorded("tab", "t1"), "fix queue")
        self.assertTrue(self.own.owns_tab("t1", self.client.tabs["t1"]["label"]))

    def test_resume_reload_takes_label_back(self):
        self.daemon.tick(100.0)
        self.client.tabs["t2"]["label"] = "watcher"
        other = Ownership.load(self.own.path)
        other.resume("tab", "t2", "watcher")
        other.save()
        self.daemon.reload()
        self.daemon.tick(110.0)
        self.assertEqual(self.client.tabs["t2"]["label"], "npm dev")


if __name__ == "__main__":
    unittest.main()
