import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ownership import Ownership  # noqa: E402


class OwnershipTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "labels.json")
        self.own = Ownership.load(self.path)

    def tearDown(self):
        self.dir.cleanup()

    def test_tab_owned_when_numeric_or_recorded(self):
        self.assertTrue(self.own.owns_tab("w1:t1", "1"))
        self.assertTrue(self.own.owns_tab("w1:t1", "12"))
        self.assertFalse(self.own.owns_tab("w1:t1", "watcher"))
        self.assertFalse(self.own.owns_tab("w1:t1", ""))
        self.own.record("tab", "w1:t1", "npm dev")
        self.assertTrue(self.own.owns_tab("w1:t1", "npm dev"))
        self.assertFalse(self.own.owns_tab("w1:t2", "npm dev"))

    def test_pane_owned_when_unset_or_recorded(self):
        self.assertTrue(self.own.owns_pane("p1", None))
        self.assertFalse(self.own.owns_pane("p1", "logs"))
        self.assertFalse(self.own.owns_pane("p1", "7"))
        self.own.record("pane", "p1", "logs")
        self.assertTrue(self.own.owns_pane("p1", "logs"))

    def test_user_rename_releases_until_resume(self):
        self.own.record("tab", "w1:t1", "npm dev")
        self.assertFalse(self.own.owns_tab("w1:t1", "api"))
        self.assertFalse(self.own.owns_tab("w1:t1", "api"))  # contents changed, still the user's
        self.own.resume("tab", "w1:t1", "api")
        self.assertTrue(self.own.owns_tab("w1:t1", "api"))

    def test_round_trip(self):
        self.own.record("tab", "w1:t1", "npm dev")
        self.own.record("pane", "p1", "nvim plan.md")
        self.own.save()
        again = Ownership.load(self.path)
        self.assertTrue(again.owns_tab("w1:t1", "npm dev"))
        self.assertTrue(again.owns_pane("p1", "nvim plan.md"))
        with open(self.path) as f:
            self.assertEqual(json.load(f), {"tabs": {"w1:t1": "npm dev"}, "panes": {"p1": "nvim plan.md"}})

    def test_load_missing_or_corrupt_starts_empty(self):
        missing = Ownership.load(os.path.join(self.dir.name, "nope.json"))
        self.assertFalse(missing.owns_pane("p1", "x"))
        for junk in ["{not json", "[]", '{"tabs": 3}']:
            with open(self.path, "w") as f:
                f.write(junk)
            own = Ownership.load(self.path)
            self.assertFalse(own.owns_tab("w1:t1", "x"), junk)
            own.record("tab", "w1:t1", "x")  # usable after a bad load
            self.assertTrue(own.owns_tab("w1:t1", "x"))

    def test_save_is_atomic(self):
        self.own.record("tab", "w1:t1", "a")
        with mock.patch("ownership.os.replace", wraps=os.replace) as replace:
            self.own.save()
        replace.assert_called_once()
        src, dst = replace.call_args.args
        self.assertEqual(dst, self.path)
        self.assertNotEqual(src, self.path)
        self.assertEqual(os.listdir(self.dir.name), ["labels.json"])

    def test_forget(self):
        self.own.record("tab", "w1:t1", "a")
        self.own.record("pane", "p1", "b")
        self.own.forget("tab", "w1:t1")
        self.own.forget("pane", "p1")
        self.own.forget("pane", "never-seen")
        self.assertFalse(self.own.owns_tab("w1:t1", "a"))
        self.assertFalse(self.own.owns_pane("p1", "b"))


if __name__ == "__main__":
    unittest.main()
