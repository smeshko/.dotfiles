"""Which tab and pane labels are the plugin's to change.

A tab is owned while its label is all digits (herdr's default) or the last label
the plugin set; a pane while it has no label or the plugin's last label. A user
rename breaks the match, so the plugin lets go without separate pin state.
"""
import json
import os
import tempfile

KINDS = {"tab": "tabs", "pane": "panes"}


class Ownership:
    def __init__(self, path, labels=None):
        self.path = path
        self.labels = labels or {"tabs": {}, "panes": {}}

    @classmethod
    def load(cls, path):
        try:
            with open(path) as f:
                data = json.load(f)
            labels = {key: dict(data[key]) for key in KINDS.values()}
            if not all(isinstance(v, str) for d in labels.values() for v in d.values()):
                raise ValueError("labels must be strings")
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            labels = None
        return cls(path, labels)

    def owns_tab(self, tab_id, label):
        return (bool(label) and label.isdigit()) or self.recorded("tab", tab_id) == label

    def owns_pane(self, pane_id, label):
        return not label or self.recorded("pane", pane_id) == label

    def recorded(self, kind, id_):
        return self.labels[KINDS[kind]].get(id_)

    def record(self, kind, id_, label):
        self.labels[KINDS[kind]][id_] = label

    # Taking a label back is recording it as the plugin's own.
    resume = record

    def forget(self, kind, id_):
        self.labels[KINDS[kind]].pop(id_, None)

    def save(self):
        directory = os.path.dirname(self.path) or "."
        fd, tmp = tempfile.mkstemp(dir=directory, prefix=".labels-", suffix=".json")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(self.labels, f, indent=1, sort_keys=True)
            os.replace(tmp, self.path)
        except BaseException:
            os.unlink(tmp)
            raise
