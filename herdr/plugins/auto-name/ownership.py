"""Which tab and pane labels are the plugin's to change.

A tab is owned while its label is all digits (herdr's default) or the last label
the plugin set; a pane while it has no label or the plugin's last label. A user
rename breaks the match, so the plugin lets go without separate pin state.

Both the daemon and the resume action write labels.json, so each save merges
its own changes into what is on disk under a lock on the state directory.
"""
import fcntl
import json
import os
import tempfile

KINDS = {"tab": "tabs", "pane": "panes"}


class Ownership:
    def __init__(self, path, labels=None):
        self.path = path
        self.labels = labels or {"tabs": {}, "panes": {}}
        self.changed = {}  # (kind key, id) -> label, None when forgotten

    @classmethod
    def load(cls, path):
        return cls(path, read_labels(path))

    def owns_tab(self, tab_id, label):
        return (bool(label) and label.isdigit()) or self.recorded("tab", tab_id) == label

    def owns_pane(self, pane_id, label):
        return not label or self.recorded("pane", pane_id) == label

    def recorded(self, kind, id_):
        return self.labels[KINDS[kind]].get(id_)

    def record(self, kind, id_, label):
        self.labels[KINDS[kind]][id_] = label
        self.changed[(KINDS[kind], id_)] = label

    # Taking a label back is recording it as the plugin's own.
    resume = record

    def forget(self, kind, id_):
        if self.labels[KINDS[kind]].pop(id_, None) is not None:
            self.changed[(KINDS[kind], id_)] = None

    def ids(self, kind):
        return set(self.labels[KINDS[kind]])

    def save(self):
        """Merge this process's changes into the file and adopt the result."""
        directory = os.path.dirname(self.path) or "."
        lock = os.open(directory, os.O_RDONLY)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX)
            labels = read_labels(self.path) or {"tabs": {}, "panes": {}}
            for (key, id_), label in self.changed.items():
                if label is None:
                    labels[key].pop(id_, None)
                else:
                    labels[key][id_] = label
            fd, tmp = tempfile.mkstemp(dir=directory, prefix=".labels-", suffix=".json")
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(labels, f, indent=1, sort_keys=True)
                os.replace(tmp, self.path)
            except BaseException:
                os.unlink(tmp)
                raise
        finally:
            os.close(lock)
        self.labels = labels
        self.changed = {}


def read_labels(path):
    """The labels in path, or None when it is missing or not a labels file."""
    try:
        with open(path) as f:
            data = json.load(f)
        labels = {key: dict(data[key]) for key in KINDS.values()}
        if not all(isinstance(v, str) for d in labels.values() for v in d.values()):
            raise ValueError("labels must be strings")
        return labels
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return None
