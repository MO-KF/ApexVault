from __future__ import annotations

import logging
import os
import sys

from ui.backend import WEB_DIR, ApexVaultBackend
from core import win_system
from core.monitor import GuardianMonitor

import webview

LOG_FILE = "apexvault.log"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(BASE_DIR, "assets", "icon.ico")

def setup_logging() -> None:
    base = os.environ.get("APPDATA", os.path.expanduser("~"))
    log_dir = os.path.join(base, "ApexVault")
    try:
        os.makedirs(log_dir, exist_ok=True)
        path = os.path.join(log_dir, LOG_FILE)
    except OSError:
        path = LOG_FILE

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(path, encoding="utf-8")],
    )

    if sys.stdout is not None:
        logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

def main() -> int:
    setup_logging()
    log = logging.getLogger("apexvault.main")
    hidden = "--hidden" in sys.argv[1:]
    log.info("starting ApexVault (hidden=%s)", hidden)

    guard = win_system.SingleInstanceGuard()
    if not guard.acquire():
        log.warning("another instance already running — asking it to show")
        win_system.request_show_previous_instance()
        return 0

    try:
        backend = ApexVaultBackend()

        monitor = GuardianMonitor(
            storage=backend.storage,
            on_gate_request=_make_gate_callback(backend),
            get_face_flag=lambda key, is_folder: _face_flag(backend, key, is_folder),
        )
        backend.monitor = monitor

        guard.start_show_listener(backend.bring_to_front)

        window = webview.create_window(
            "ApexVault",
            url=os.path.join(WEB_DIR, "index.html"),
            js_api=backend,
            width=840,
            height=560,
            frameless=True,
            transparent=False,
            hidden=hidden,
        )
        backend.set_window(window)

        backend._ensure_tray()

        if backend.storage.has_any():
            win_system.set_autostart(True)

        monitor.start()
        try:

            app_icon = ICON_PATH if os.path.isfile(ICON_PATH) else None
            webview.start(
                debug=os.environ.get("APEXVAULT_DEBUG") == "1",
                icon=app_icon,
            )
        finally:
            monitor.stop()
    finally:
        guard.release()
    return 0

def _face_flag(backend: ApexVaultBackend, key: str, is_folder: bool) -> bool:
    info = (
        backend.storage.get_folder(key) if is_folder else backend.storage.get_app(key)
    )
    return bool(info and info.get("face_id"))

def _make_gate_callback(backend: ApexVaultBackend):
    def on_gate_request(key: str, path: str, is_folder: bool, has_face: bool) -> None:
        key_js = __import__("json").dumps(str(key))
        face_js = "true" if has_face else "false"
        folder_js = "true" if is_folder else "false"
        from ui.backend import _eval

        backend.bring_to_front()
        script = (
            f"if(typeof showGateModal==='function')"
            f"showGateModal({key_js},{key_js},{folder_js},{face_js});"
        )
        _eval(backend.window, script)

    return on_gate_request

if __name__ == "__main__":
    sys.exit(main())
