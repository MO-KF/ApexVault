# -*- coding: utf-8 -*-

import time

from core import win_system

def track_folder(path, is_folder_visible, on_relock):

    time.sleep(2.5)
    while is_folder_visible(path):
        time.sleep(1.2)
    on_relock(path)

def monitoring_loop(db_provider, state_provider, emit_gate):

    while True:
        try:
            db = db_provider()
            states = state_provider()
            pids = win_system.get_running_processes()
            wins = win_system.get_explorer_windows()

            for app, info in db["apps"].items():
                if app in pids:
                    if states.app_states.get(app, "locked") == "locked":
                        for pid in pids[app]:
                            win_system.kill_process(pid)
                        emit_gate(app, info["password"], info["path"], False, info.get("face_id", False))
                else:
                    states.app_states[app] = "locked"

            for path, info in db["folders"].items():
                current = states.folder_states.get(path, "locked")
                if current == "locked":
                    name_l = info["name"].lower()
                    for hwnd, title in wins:
                        t = title.lower()
                        if t == name_l or name_l in t:
                            win_system.close_window(hwnd)
                            emit_gate(path, info["password"], path, True, info.get("face_id", False))
        except Exception:
            pass
        time.sleep(0.2)