from __future__ import annotations

import json
import logging
import os
import sys
import threading

import webview

from core import face_auth, vault_storage, win_system
from ui.languages import DEFAULT_LANG, LANGUAGES, get as lang_get

log = logging.getLogger("apexvault.backend")

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")

class ApexVaultBackend:

    def __init__(self, data_dir: str | None = None):
        self.storage = vault_storage.VaultStorage(data_dir)
        self.window = None
        self.monitor = None
        self.tray = None

        self.current_lang = self._load_lang()
        self.lang = lang_get(self.current_lang)

    def _config_path(self) -> str:
        return os.path.join(self.storage.data_dir, "config.json")

    def _load_lang(self) -> str:
        try:
            with open(self._config_path(), "r", encoding="utf-8") as fh:
                name = json.load(fh).get("lang")
            if name in LANGUAGES:
                return name
        except Exception:
            pass
        return DEFAULT_LANG

    def set_window(self, window) -> None:
        self.window = window

    def minimize_window(self) -> None:
        if self.window:
            self.window.minimize()

    def close_window(self) -> None:
        log.info("close requested -> hide to tray/background")
        self._ensure_tray()
        if self.tray is not None:
            self.tray.notify_hidden()
        if self.window:
            try:
                self.window.hide()
            except Exception:
                log.exception("window hide failed")

    def quit_app(self) -> None:
        log.info("quit requested (full exit)")
        try:
            if self.tray is not None:
                self.tray.hide()
                self.tray = None
        except Exception:
            log.debug("tray removal failed", exc_info=True)
        if self.monitor:
            self.monitor.stop(timeout=1.0)
        if self.window:
            try:
                self.window.destroy()
            except Exception:
                log.exception("window destroy failed")

    def get_system_specs(self) -> dict:
        return {
            "os": win_system.get_os_label(),
            "device": os.environ.get("COMPUTERNAME", "") or "This PC",
            "cpu": win_system.get_cpu_name(),
            "ram": win_system.get_ram_gb(),
            "gpu": win_system.get_gpu_name(),
            "credit": self.lang["credit_msg"],
        }

    def get_vault_items(self) -> dict:
        rows = self.storage.list_items(self.lang["type_app"], self.lang["active"])
        apps, folders = self.storage.counts()
        return {"items": rows, "apps_count": apps, "folders_count": folders}

    def _pick_target(self, folder_mode: bool):
        fd = getattr(webview, "FileDialog", None)
        if fd is not None:
            dialog_type = fd.FOLDER if folder_mode else fd.OPEN
        else:
            dialog_type = webview.FOLDER_DIALOG if folder_mode else webview.OPEN_DIALOG

        file_types = () if folder_mode else ("Executables (*.exe)", "All files (*.*)")

        try:
            from System import Func, Type

            from webview.platforms import winforms as _wf

            owner = _wf.BrowserView.instances.get("master")
            if owner is not None:
                box: list = []

                def _create() -> None:
                    try:
                        box.append(
                            _wf.create_file_dialog(
                                dialog_type,
                                os.path.expanduser("~"),
                                False,
                                "",
                                file_types,
                                "master",
                            )
                        )
                    except Exception:
                        log.exception("native picker failed")

                owner.Invoke(Func[Type](_create))
                return box[0] if box else None
        except Exception:
            log.exception("UI-thread picker unavailable; using pywebview fallback")

        if self.window:
            return self.window.create_file_dialog(dialog_type, file_types=file_types)
        return None

    def lock_app(self) -> None:
        if not self.window:
            return
        result = self._pick_target(folder_mode=False)
        if result:
            path = result[0]
            self.window.evaluate_js(_js_show_setup(os.path.basename(path).lower(), path, "app"))

    def lock_folder(self) -> None:
        if not self.window:
            return
        result = self._pick_target(folder_mode=True)
        if result:
            path = os.path.abspath(result[0])
            self.window.evaluate_js(_js_show_setup(os.path.basename(path), path, "folder"))

    def setup_face_recognition(self, target_name: str) -> bool:
        if not hasattr(face_auth, "register_face"):
            return False
        ok = face_auth.register_face(target_name)
        if ok:
            log.info("face enrolled for %s", target_name[:32])
        return ok

    def save_protection(self, item_type: str, name: str, path: str,
                        password: str, face_id: bool = False) -> dict:
        if item_type not in ("app", "folder"):
            return {"success": False, "message": "bad type"}
        if not name or not path:
            return {"success": False, "message": self.lang["not_found"]}
        if not isinstance(password, str) or not password:
            return {"success": False, "message": self.lang["empty_pwd"]}
        try:
            self.storage.add_item(item_type, name, path, password, face_id)
            self._ensure_autostart()
        except Exception:
            log.exception("save_protection failed (%s)", name)
            return {"success": False, "message": self.lang["save_failed"]}
        self.refresh_ui()
        log.info("protection saved (%s): %s", item_type, name)
        return {"success": True}

    def remove_protection(self, item_type: str, name: str, path: str = "") -> dict:
        if item_type not in ("app", "folder"):

            item_type = "folder" if ("پوشه" in str(item_type) or "Folder" in str(item_type)) else "app"
        if item_type == "folder":

            key = path if path else name
            info = self.storage.get_folder(key)
            identifier = key
            face_key = info["name"] if info else name
        else:
            identifier = name.lower()
            face_key = identifier
        self.storage.remove_item(item_type, name, path)
        if hasattr(face_auth, "delete_face"):
            face_auth.delete_face(face_key)
        self.refresh_ui()
        log.info("protection removed (%s): %s", item_type, identifier)
        return {"success": True}

    def verify_unlock(self, key: str, input_password: str, is_folder: bool) -> dict:
        if not self.storage.check_password(key, input_password or "", is_folder):
            return {"success": False, "message": self.lang["error_pass"]}
        info = (
            self.storage.get_folder(key) if is_folder else self.storage.get_app(key)
        )
        if not info:
            return {"success": False, "message": self.lang["not_found"]}
        self._execute_unlock(key, key if is_folder else info["path"], is_folder)
        return {"success": True}

    def verify_face_unlock(self, key: str, is_folder: bool) -> dict:
        if not hasattr(face_auth, "verify_face"):
            return {"success": False, "message": "Face ID module unavailable"}
        identifier = os.path.basename(key) if is_folder else key
        if not face_auth.verify_face(identifier):
            return {"success": False, "message": "❌ چهره شناسایی نشد!"}
        info = (
            self.storage.get_folder(key) if is_folder else self.storage.get_app(key)
        )
        if not info:
            return {"success": False, "message": self.lang["not_found"]}
        self._execute_unlock(key, key if is_folder else info["path"], is_folder)
        return {"success": True}

    def gate_closed(self, key: str) -> dict:
        if self.monitor:
            self.monitor.mark_dialog_closed(key)
        return {"success": True}

    def set_language(self, lang_name: str) -> dict:
        if lang_name not in LANGUAGES:
            return {"success": False}
        self.current_lang = lang_name
        self.lang = lang_get(lang_name)
        try:
            with open(self._config_path(), "w", encoding="utf-8") as fh:
                json.dump({"lang": lang_name}, fh)
        except OSError:
            log.exception("could not persist language")
        self.refresh_ui()
        return {"success": True}

    def refresh_ui(self) -> None:
        _eval(self.window, "if(typeof refreshTable==='function')refreshTable();")

    def bring_to_front(self) -> None:
        if not self.window:
            return
        try:
            self.window.restore()
            self.window.show()
        except Exception:
            log.debug("window restore/show failed", exc_info=True)
        try:
            import ctypes

            from webview.platforms import winforms as _wf

            owner = _wf.BrowserView.instances.get("master")
            if owner is not None:

                hwnd = int(owner.Handle.ToInt64())
                user32 = ctypes.windll.user32
                user32.ShowWindow(hwnd, 9)
                user32.SetForegroundWindow(hwnd)
        except Exception:
            log.debug("SetForegroundWindow failed", exc_info=True)

    def _ensure_tray(self) -> None:
        if self.tray is not None:
            return
        try:
            from ui.tray_icon import ApexVaultTray

            self.tray = ApexVaultTray(
                on_restore=self.restore_window,
                on_quit=self.quit_app,
            )
            self.tray.show()
        except Exception:
            log.exception("tray icon unavailable (feature disabled)")
            self.tray = None

    def restore_window(self) -> None:
        self.bring_to_front()

    def _ensure_autostart(self) -> None:
        if self.storage.has_any():
            win_system.set_autostart(True)

    def _execute_unlock(self, key: str, path: str, is_folder: bool) -> None:
        if self.monitor is None:
            return
        if is_folder:
            with self.monitor._lock:
                self.monitor.folder_states[key] = "temp_open"
            win_system.open_path(key)
            threading.Thread(
                target=self.monitor.track_folder, args=(key,), daemon=True
            ).start()
        else:
            with self.monitor._lock:
                self.monitor.app_states[key] = "unlocked"
            win_system.open_path(path)

def _js_show_setup(name: str, path: str, item_type: str) -> str:
    name_js = json.dumps(name)
    path_js = json.dumps(path)
    return (
        f"if(typeof showPasswordSetupModal==='function')"
        f"showPasswordSetupModal({name_js},{path_js},'{item_type}');"
    )

def _eval(window, script: str) -> None:
    if window is None:
        return
    try:
        window.evaluate_js(script)
    except Exception:
        log.warning("evaluate_js skipped (window gone?)", exc_info=True)

def resource_path(relative: str) -> str:
    try:
        base = sys._MEIPASS
    except AttributeError:
        base = WEB_DIR
    return os.path.join(base, relative)
