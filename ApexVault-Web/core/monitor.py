from __future__ import annotations

import gc
import json
import logging
import threading
import time

from core import win_system

log = logging.getLogger("apexvault.monitor")

TICK = 0.2
GC_INTERVAL = 30.0

APPEAR_GRACE = 8.0

def basename_lower(path: str) -> str:
    return path.rstrip("\\/").replace("\\", "/").rsplit("/", 1)[-1].lower()

class GuardianMonitor:

    def __init__(self, storage, on_gate_request, get_face_flag):
        self.storage = storage
        self.on_gate_request = on_gate_request
        self.get_face_flag = get_face_flag

        self.app_states: dict[str, str] = {}
        self.folder_states: dict[str, str] = {}

        with storage._lock:
            self.app_states = {a: "locked" for a in storage.db["apps"]}
            self.folder_states = {f: "locked" for f in storage.db["folders"]}

        self.active_dialogs: set[str] = set()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="apexvault-guardian", daemon=True
        )
        self._thread.start()
        log.info("guardian monitor started")

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def mark_dialog_closed(self, key: str) -> None:
        with self._lock:
            self.active_dialogs.discard(key)

    def _show_gate(self, key: str, path: str, is_folder: bool, has_face: bool):
        try:
            self.on_gate_request(key, path, is_folder, has_face)
        except Exception:
            log.exception("gate callback failed")

    def track_folder(self, path: str) -> None:
        name = basename_lower(path)
        deadline = time.monotonic() + APPEAR_GRACE
        while not self._stop.is_set() and time.monotonic() < deadline:
            if win_system.is_folder_open(name):
                break
            time.sleep(0.5)
        while not self._stop.is_set():
            if not win_system.is_folder_open(name):
                with self._lock:
                    self.folder_states[path] = "locked"
                log.info("folder re-locked: %s", path)
                break
            time.sleep(1.2)

    def _run(self) -> None:
        last_gc = time.monotonic()
        while not self._stop.is_set():
            started = time.monotonic()
            try:
                self._scan_apps()
                self._scan_folders()
            except Exception:
                log.exception("guardian scan error")
            if time.monotonic() - last_gc >= GC_INTERVAL:
                gc.collect()
                last_gc = time.monotonic()
            elapsed = time.monotonic() - started
            self._stop.wait(max(0.0, TICK - elapsed))

    def _scan_apps(self) -> None:
        pids_map = win_system.get_running_processes()
        with self.storage._lock:
            items = list(self.storage.db["apps"].items())

        for app, info in items:
            pids = pids_map.get(app)
            if not pids:
                with self._lock:
                    self.app_states[app] = "locked"
                continue

            with self._lock:
                locked = self.app_states.get(app, "locked") == "locked"
                dialog_open = app in self.active_dialogs

            if locked:
                killed = win_system.terminate_processes(pids)
                if killed:
                    log.info("killed %d process(es) of locked app %s", killed, app)
                if not dialog_open:
                    has_face = bool(info.get("face_id"))
                    with self._lock:
                        self.active_dialogs.add(app)
                    self._show_gate(app, info["path"], False, has_face)

    def _scan_folders(self) -> None:
        windows = win_system.get_explorer_windows()
        with self.storage._lock:
            items = list(self.storage.db["folders"].items())

        for path, info in items:
            with self._lock:
                state = self.folder_states.get(path, "locked")
                dialog_open = path in self.active_dialogs
            if state != "locked":
                continue

            name = info["name"].lower()
            hit = False
            for hwnd, title in windows:
                if win_system.title_matches_folder(title, name):
                    win_system.close_explorer_window(hwnd)
                    hit = True
            if hit and not dialog_open:
                has_face = bool(info.get("face_id"))
                with self._lock:
                    self.active_dialogs.add(path)
                self._show_gate(path, path, True, has_face)
