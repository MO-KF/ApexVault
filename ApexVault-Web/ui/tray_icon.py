from __future__ import annotations

import logging
import os
import threading

log = logging.getLogger("apexvault.tray")

ASSET_ICON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icon.ico"
)

class ApexVaultTray:

    def __init__(self, on_restore=None, on_quit=None, icon_path: str = ASSET_ICON):
        self._on_restore = on_restore
        self._on_quit = on_quit
        self._icon_path = icon_path
        self._ready = threading.Event()
        self._disposed = threading.Event()
        self._thread: threading.Thread | None = None
        self._icon = None
        self._form = None

    def show(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run, name="apexvault-tray", daemon=True
        )
        self._thread.start()
        if not self._ready.wait(timeout=3.0):
            log.warning("tray icon did not initialise in time")

    def hide(self) -> None:
        self._run_on_tray(self._dispose_sync)
        if self._disposed.wait(timeout=3.0) and self._thread is not None:
            self._thread.join(timeout=3.0)
        self._thread = None
        self._icon = None
        self._form = None

    def notify_hidden(self) -> None:
        self._run_on_tray(self._notify_sync)

    def _run(self) -> None:
        try:

            import clr

            clr.AddReference("System.Drawing")
            clr.AddReference("System.Windows.Forms")

            from System import EventHandler
            from System.Drawing import Icon
            from System.Windows.Forms import (
                ApplicationContext,
                Application,
                ContextMenu,
                Form,
                MenuItem,
                NotifyIcon,
            )
        except Exception:
            log.exception("WinForms NotifyIcon unavailable; no tray icon")
            return

        try:
            form = Form()
            form.ShowInTaskbar = False
            form.Text = "apexvault-tray-owner"
            self._form = form

            icon = Icon(self._icon_path) if os.path.isfile(self._icon_path) else None

            def _restore(*_a):
                cb = self._on_restore
                if cb:
                    cb()

            def _quit(*_a):
                cb = self._on_quit
                if cb:
                    cb()

            menu = ContextMenu()
            menu.MenuItems.Add(MenuItem("Open ApexVault", EventHandler(_restore)))
            menu.MenuItems.Add(MenuItem("-"))
            menu.MenuItems.Add(MenuItem("Exit", EventHandler(_quit)))

            ni = NotifyIcon()
            if icon is not None:
                ni.Icon = icon
            ni.Text = "ApexVault — guardian active"
            ni.Visible = True
            ni.ContextMenu = menu
            ni.DoubleClick += EventHandler(_restore)
            self._icon = ni
            log.info("tray icon ready")

            _ = form.Handle
            self._ready.set()

            Application.Run(ApplicationContext(form))
        except Exception:
            log.exception("tray icon loop failed")
        finally:
            self._disposed.set()

    def _notify_sync(self) -> None:
        try:
            if self._icon is not None:
                self._icon.BalloonTipTitle = "ApexVault"
                self._icon.BalloonTipText = (
                    "ApexVault is running in the background and the "
                    "guardian is active. Reopen the app from here."
                )
                self._icon.ShowBalloonTip(1500)
        except Exception:
            pass

    def _dispose_sync(self) -> None:
        try:
            if self._icon is not None:
                self._icon.Visible = False
                self._icon.Dispose()
                self._icon = None
        except Exception:
            pass
        finally:
            try:
                if self._form is not None:
                    self._form.Close()
            except Exception:
                pass
            self._disposed.set()

    def _run_on_tray(self, fn) -> None:
        thread = self._thread
        if thread is None or not thread.is_alive():
            return
        if not self._ready.wait(timeout=2.0):
            return
        try:
            from System import Func, Type
            from System.Windows.Forms import Control

            form = self._form
            if form is not None:
                if form.InvokeRequired:
                    form.Invoke(Func[Type](fn))
                    return
        except Exception:
            pass

        try:
            fn()
        except Exception:
            pass
