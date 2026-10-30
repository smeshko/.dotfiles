#!/usr/bin/env python3
"""Keep herdr tab and pane labels in step with what the panes run.

Subcommands:
  run     foreground loop (one per server, guarded by daemon.lock)
  start   detach and run, logging to daemon.log
  stop    SIGTERM the running daemon and wait for it to exit
  restart stop, then start
  resume  take the focused tab's and pane's current labels back as the plugin's own

Events and shell polls only mark panes and tabs dirty; a 1s tick names them and
renames at most once per 2s per target. Ownership (ownership.py) decides what may
be renamed, so labels set by hand are left alone.
"""
import fcntl
import json
import os
import signal
import socket
import sys
import time

from naming import pane_name
from ownership import Ownership

SOCK = os.environ.get("HERDR_SOCKET_PATH") or os.path.expanduser("~/.config/herdr/herdr.sock")
STATE_DIR = os.environ.get("HERDR_PLUGIN_STATE_DIR") or os.path.expanduser("~/.local/state/herdr-auto-name")
TICK = 1.0
DEBOUNCE = 2.0
POLL = 2.0
EVENTS = ["pane.created", "pane.closed", "pane.updated", "pane.moved", "pane.agent_detected",
          "tab.created", "tab.closed", "tab.renamed"]


def state_path(name):
    return os.path.join(STATE_DIR, name)


def log(line):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}", flush=True)


def request(method, params):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect(SOCK)
    s.sendall((json.dumps({"id": "auto-name", "method": method, "params": params}) + "\n").encode())
    buf = b""
    while b"\n" not in buf:
        chunk = s.recv(65536)
        if not chunk:
            break
        buf += chunk
    s.close()
    resp = json.loads(buf.decode().split("\n", 1)[0])
    if "error" in resp:
        raise RuntimeError(f"{method}: {json.dumps(resp['error'])}")
    return resp["result"]


class Client:
    """The herdr calls the daemon makes, so tests can swap in a fake."""

    def list_panes(self):
        return request("pane.list", {})["panes"]

    def list_tabs(self):
        return request("tab.list", {})["tabs"]

    def get_pane(self, pane_id):
        return request("pane.get", {"pane_id": pane_id})["pane"]

    def layout(self, pane_id):
        return request("pane.layout", {"pane_id": pane_id})["layout"]["panes"]

    def process_info(self, pane_id):
        return request("pane.process_info", {"pane_id": pane_id})["process_info"]

    def rename_pane(self, pane_id, label):
        request("pane.rename", {"pane_id": pane_id, "label": label})

    def rename_tab(self, tab_id, label):
        request("tab.rename", {"tab_id": tab_id, "label": label})


class Daemon:
    def __init__(self, client, ownership, log=log):
        self.client = client
        self.own = ownership
        self.log = log
        self.panes = {}
        self.tabs = {}
        self.procs = {}
        self.names = {}
        self.polled = {}
        self.renamed = {}
        self.dirty_panes = set()
        self.dirty_tabs = set()

    def snapshot(self):
        self.panes = {p["pane_id"]: p for p in self.client.list_panes()}
        self.tabs = {t["tab_id"]: t for t in self.client.list_tabs()}
        for tab_id in self.own.ids("tab") - set(self.tabs):
            self.own.forget("tab", tab_id)
        for pane_id in self.own.ids("pane") - set(self.panes):
            self.own.forget("pane", pane_id)
        self.dirty_panes = set(self.panes)
        self.dirty_tabs = set(self.tabs)
        self.log(f"startup: {len(self.tabs)} tabs, {len(self.panes)} panes")

    def reload(self):
        """Adopt labels another process saved (resume) and revisit what changed."""
        before = {kind: {i: self.own.recorded(kind, i) for i in self.own.ids(kind)} for kind in ("tab", "pane")}
        self.own.save()
        for kind, dirty in (("tab", self.dirty_tabs), ("pane", self.dirty_panes)):
            for id_ in self.own.ids(kind) | set(before[kind]):
                if self.own.recorded(kind, id_) != before[kind].get(id_):
                    dirty.add(id_)
                    self.renamed.pop((kind, id_), None)

    def mark_pane(self, pane):
        self.panes[pane["pane_id"]] = pane
        self.dirty_panes.add(pane["pane_id"])

    def handle(self, event):
        kind = event.get("type")
        if kind in ("pane_created", "pane_updated"):
            self.mark_pane(event["pane"])
        elif kind == "pane_moved":
            old, pane = event["previous_pane_id"], event["pane"]
            old_label = self.own.recorded("pane", old)
            self.drop_pane(old)
            if old_label is not None:
                self.own.record("pane", pane["pane_id"], old_label)
            self.dirty_tabs.add(event["previous_tab_id"])
            self.mark_pane(pane)
            self.dirty_tabs.add(pane["tab_id"])
        elif kind == "pane_agent_detected":
            self.mark_pane(self.client.get_pane(event["pane_id"]))
        elif kind == "pane_closed":
            tab_id = self.panes.get(event["pane_id"], {}).get("tab_id")
            self.drop_pane(event["pane_id"])
            if tab_id in self.tabs:
                self.dirty_tabs.add(tab_id)
        elif kind == "tab_created":
            self.tabs[event["tab"]["tab_id"]] = event["tab"]
            self.dirty_tabs.add(event["tab"]["tab_id"])
        elif kind == "tab_renamed":
            self.tabs.setdefault(event["tab_id"], {"tab_id": event["tab_id"]})["label"] = event["label"]
            self.dirty_tabs.add(event["tab_id"])
        elif kind == "tab_closed":
            # Its panes close with it, without pane_closed events.
            for pane_id in [p for p, info in self.panes.items() if info.get("tab_id") == event["tab_id"]]:
                self.drop_pane(pane_id)
            self.tabs.pop(event["tab_id"], None)
            self.dirty_tabs.discard(event["tab_id"])
            self.own.forget("tab", event["tab_id"])

    def drop_pane(self, pane_id):
        for table in (self.panes, self.procs, self.names, self.polled):
            table.pop(pane_id, None)
        self.dirty_panes.discard(pane_id)
        self.own.forget("pane", pane_id)

    def tick(self, now):
        self.poll_shells(now)
        for pane_id in list(self.dirty_panes):
            if self.name_pane(pane_id, now):
                self.dirty_panes.discard(pane_id)
        for tab_id in list(self.dirty_tabs):
            if self.name_tab(tab_id, now):
                self.dirty_tabs.discard(tab_id)
        if self.own.changed:
            self.own.save()

    def poll_shells(self, now):
        for pane_id, pane in list(self.panes.items()):
            if pane.get("agent") or now - self.polled.get(pane_id, -POLL) < POLL:
                continue
            tab = self.tabs.get(pane.get("tab_id"), {})
            if not (self.own.owns_pane(pane_id, pane.get("label"))
                    or self.own.owns_tab(tab.get("tab_id"), tab.get("label"))):
                continue
            self.polled[pane_id] = now
            try:
                self.procs[pane_id] = self.client.process_info(pane_id)
            except Exception as exc:
                self.log(f"process_info {pane_id}: {exc}")
                continue
            self.dirty_panes.add(pane_id)

    def compute(self, pane_id):
        pane = self.panes[pane_id]
        name = pane_name(pane, None if pane.get("agent") else self.procs.get(pane_id))
        if name != self.names.get(pane_id) and pane.get("tab_id") in self.tabs:
            self.dirty_tabs.add(pane["tab_id"])
        self.names[pane_id] = name
        return name

    def name_pane(self, pane_id, now):
        """Rename the pane if it is owned and stale; False to retry next tick."""
        if pane_id not in self.panes:
            return True
        pane = self.panes[pane_id]
        name = self.compute(pane_id)
        label = pane.get("label")
        if not self.own.owns_pane(pane_id, label) or name == label:
            return True
        return self.rename("pane", pane_id, label, name, now, self.client.rename_pane,
                           lambda: pane.__setitem__("label", name))

    def name_tab(self, tab_id, now):
        tab = self.tabs.get(tab_id)
        if tab is None:
            return True
        label = tab.get("label")
        if not self.own.owns_tab(tab_id, label):
            return True
        member = next((p for p, info in self.panes.items() if info.get("tab_id") == tab_id), None)
        if member is None:
            return True
        try:
            first = self.client.layout(member)[0]["pane_id"]
        except Exception as exc:
            self.log(f"layout {tab_id}: {exc}")
            return True
        if first not in self.panes:
            return True
        name = self.names.get(first) or self.compute(first)
        if name == label:
            return True
        return self.rename("tab", tab_id, label, name, now, self.client.rename_tab,
                           lambda: tab.__setitem__("label", name))

    def rename(self, kind, id_, label, name, now, send, apply):
        if now - self.renamed.get((kind, id_), -DEBOUNCE) < DEBOUNCE:
            return False
        previous = self.own.recorded(kind, id_)
        # Recorded first, so the echoed rename event matches and is ignored.
        self.own.record(kind, id_, name)
        self.renamed[(kind, id_)] = now
        try:
            send(id_, name)
        except Exception as exc:
            if previous is None:
                self.own.forget(kind, id_)
            else:
                self.own.record(kind, id_, previous)
            self.log(f"rename {kind} {id_}: {exc}")
            return True
        apply()
        self.log(f'{kind} {id_} "{label or ""}" -> "{name}"')
        return True


def subscribe():
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect(SOCK)
    params = {"subscriptions": [{"type": t} for t in EVENTS]}
    s.sendall((json.dumps({"id": "auto-name-events", "method": "events.subscribe", "params": params}) + "\n").encode())
    return s


def read_events(sock, buf, timeout):
    """Events received within timeout, the leftover buffer, and whether the connection is open."""
    sock.settimeout(timeout)
    try:
        chunk = sock.recv(65536)
    except socket.timeout:
        return [], buf, True
    except OSError:
        return [], buf, False
    if not chunk:
        return [], buf, False
    buf += chunk
    events = []
    while b"\n" in buf:
        line, buf = buf.split(b"\n", 1)
        msg = json.loads(line)
        if "error" in msg:
            raise RuntimeError(f"events.subscribe: {json.dumps(msg['error'])}")
        if "event" in msg:
            events.append(msg["data"])
    return events, buf, True


def take_lock():
    """The open lock fd if this process is the daemon, else None."""
    os.makedirs(STATE_DIR, exist_ok=True)
    fd = os.open(state_path("daemon.lock"), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return None
    os.ftruncate(fd, 0)
    os.write(fd, f"{os.getpid()}\n".encode())
    return fd


def running_pid():
    """The daemon's pid if one holds the lock, else None."""
    try:
        fd = os.open(state_path("daemon.lock"), os.O_RDWR)
    except FileNotFoundError:
        return None
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
        return None
    except BlockingIOError:
        os.lseek(fd, 0, os.SEEK_SET)
        text = os.read(fd, 64).decode().strip()
        return int(text) if text.isdigit() else None
    finally:
        os.close(fd)


def run():
    lock = take_lock()
    if lock is None:
        log("already running")
        return 0
    flags = {"stop": False, "reload": False}
    signal.signal(signal.SIGTERM, lambda *_: flags.__setitem__("stop", True))
    signal.signal(signal.SIGHUP, lambda *_: flags.__setitem__("reload", True))
    own = Ownership.load(state_path("labels.json"))
    daemon = Daemon(Client(), own)
    log(f"started pid {os.getpid()}")
    try:
        events = subscribe()
        daemon.snapshot()
        buf, open_, next_tick = b"", True, 0.0
        while open_ and not flags["stop"]:
            batch, buf, open_ = read_events(events, buf, max(0.0, min(0.5, next_tick - time.monotonic())))
            for event in batch:
                try:
                    daemon.handle(event)
                except Exception as exc:
                    log(f"event {event.get('type')}: {exc}")
            if flags["reload"]:
                flags["reload"] = False
                daemon.reload()
                log("reloaded labels")
            now = time.monotonic()
            if now >= next_tick:
                daemon.tick(now)
                next_tick = now + TICK
        log("stopping: " + ("SIGTERM" if flags["stop"] else "event connection closed"))
    except Exception as exc:
        log(f"stopping: {exc}")
    finally:
        own.save()
    return 0


def start():
    sys.stdout.flush()  # or buffered output is written again by the forked daemon
    if os.fork():
        return 0
    os.setsid()
    if os.fork():
        os._exit(0)
    os.makedirs(STATE_DIR, exist_ok=True)
    out = os.open(state_path("daemon.log"), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    null = os.open(os.devnull, os.O_RDONLY)
    os.dup2(null, 0)
    os.dup2(out, 1)
    os.dup2(out, 2)
    os._exit(run())


def stop():
    pid = running_pid()
    if pid is None:
        print("not running")
        return 0
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 5
    while running_pid() is not None and time.monotonic() < deadline:
        time.sleep(0.1)
    print(f"stopped {pid}")
    return 0


def resume():
    own = Ownership.load(state_path("labels.json"))
    if os.environ.get("HERDR_TAB_ID"):
        tab = request("tab.get", {"tab_id": os.environ["HERDR_TAB_ID"]})["tab"]
        own.resume("tab", tab["tab_id"], tab["label"])
    if os.environ.get("HERDR_PANE_ID"):
        pane = request("pane.get", {"pane_id": os.environ["HERDR_PANE_ID"]})["pane"]
        if pane.get("label"):
            own.resume("pane", pane["pane_id"], pane["label"])
    own.save()
    pid = running_pid()
    if pid is not None:
        os.kill(pid, signal.SIGHUP)
    print("resumed auto-naming")
    return 0


def main(argv):
    commands = {"run": run, "start": start, "stop": stop, "resume": resume,
                "restart": lambda: stop() or start()}
    if len(argv) != 2 or argv[1] not in commands:
        print(f"usage: {argv[0]} {{{'|'.join(commands)}}}", file=sys.stderr)
        return 2
    return commands[argv[1]]()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
