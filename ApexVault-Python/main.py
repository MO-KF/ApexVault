import sys
import os
import ctypes
import socket
import threading
import gc

from core import face_auth
from core import monitor
from core import vault_storage
from core import win_system
from ui import dialogs
from ui import styles
from ui.languages import LANGUAGES

from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QTableWidget, QTableWidgetItem,
                            QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog, QHeaderView, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QPixmap, QCursor, QFont, QIcon

myappid = 'apexvault.app.v1'
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

def resource_path(relative_path):

    try:
        base_path = os.path.join(sys._MEIPASS, "assets")
    except Exception:
        base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    return os.path.join(base_path, relative_path)

class WorkerSignals(QObject):
    open_gate_signal = pyqtSignal(str, str, str, bool, bool)

class ApexVaultApp(QWidget):
    def __init__(self):
        super().__init__()
        self.current_lang = vault_storage.load_config()
        self.lang = LANGUAGES[self.current_lang]

        self.setWindowIcon(QIcon(resource_path("icon.ico")))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowSystemMenuHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background-color: transparent;")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.container = QWidget()
        self.container.setFixedSize(840, 530)
        self.container.setStyleSheet(styles.CONTAINER_BG)
        self.main_layout.addWidget(self.container, alignment=Qt.AlignmentFlag.AlignCenter)

        self.db = vault_storage.load_data()
        self.app_states = {app: "locked" for app in self.db["apps"]}
        self.folder_states = {folder: "locked" for folder in self.db["folders"]}
        self.active_dialogs = {}

        try:
            self.lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.lock_socket.bind(('127.0.0.1', 59422))
        except Exception:
            sys.exit(0)

        self.signals = WorkerSignals()
        self.signals.open_gate_signal.connect(self._open_gate_slot)
        self.create_gui()

        if "--startup" not in sys.argv:
            self.show()

        threading.Thread(target=self._monitor_thread, daemon=True).start()
        if self.db["apps"] or self.db["folders"]:
            vault_storage.manage_startup(True)

    def _monitor_thread(self):
        monitor.monitoring_loop(
            db_provider=lambda: self.db,
            state_provider=lambda: self,
            emit_gate=lambda key, pwd, path, is_folder, has_face:
                self.signals.open_gate_signal.emit(key, pwd, path, is_folder, has_face),
        )

    def hash_password(self, password: str) -> str:

        return vault_storage.hash_password(password)

    def _open_gate_slot(self, key, correct_pwd, path, is_folder, has_face):
        if key in self.active_dialogs:
            return
        self.active_dialogs[key] = True
        self._last_cancelled_path = path
        dialogs.open_gate(key, correct_pwd, path, is_folder, has_face, self.lang,
                          on_unlock_app=self._unlock_app,
                          on_unlock_folder=self._unlock_folder,
                          verify_pwd=vault_storage.verify_password,
                          on_cancel=(self._cancel_to_parent if is_folder else None))
        self.active_dialogs.pop(key, None)

    def _cancel_to_parent(self):

        import ntpath
        parent_dir = ntpath.dirname(self._last_cancelled_path) if hasattr(self, "_last_cancelled_path") else None
        try:
            if parent_dir and len(parent_dir) >= 3 and os.path.isdir(parent_dir):
                os.startfile(parent_dir)
        except OSError:
            pass

    def _unlock_app(self, key, path):
        self.app_states[key] = "unlocked"
        import subprocess
        subprocess.Popen([path], cwd=os.path.dirname(path))

    def _unlock_folder(self, path):
        self.folder_states[path] = "temp_open"
        os.startfile(path)
        threading.Thread(target=monitor.track_folder,
                         args=(path, self._folder_visible, self._relock_folder),
                         daemon=True).start()

    def _folder_visible(self, path):
        name_l = os.path.basename(path).lower()
        return any(name_l in t.lower() for _, t in win_system.get_explorer_windows())

    def _relock_folder(self, path):
        self.folder_states[path] = "locked"

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_pos') and event.buttons() == Qt.MouseButton.LeftButton:
            if not self.isMaximized():
                self.move(self.pos() + event.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = event.globalPosition().toPoint()

    def get_scaled_pixmap(self, filename):
        image_path = resource_path(filename)
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            screen = QApplication.primaryScreen()
            dpr = screen.devicePixelRatio() if screen else 1.0
            scaled = pixmap.scaled(int(840 * dpr), int(530 * dpr),
                                   Qt.AspectRatioMode.IgnoreAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            scaled.setDevicePixelRatio(dpr)
            return scaled
        return QPixmap()

    def show_info_box(self, title, message, is_warning=False):
        dialogs.show_message(self, title, message, False, is_warning)

    def create_gui(self):
        self.bg_label = QLabel(self.container)
        self.bg_label.setGeometry(0, 0, 840, 530)
        self.pix_main = self.get_scaled_pixmap("main_page.png")
        self.pix_pm = self.get_scaled_pixmap("first-page.jpg")
        self.bg_label.setPixmap(self.pix_main)

        self.btn_close = QPushButton("✕", self.container)
        self.btn_close.setGeometry(800, 10, 30, 30)
        self.btn_close.setStyleSheet(styles.TOP_BTN_RED)
        self.btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_close.clicked.connect(self.close)

        self.btn_max = QPushButton("🗖", self.container)
        self.btn_max.setGeometry(765, 9, 30, 30)
        self.btn_max.setStyleSheet(styles.TOP_BTN)
        self.btn_max.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_max.clicked.connect(self.toggle_maximize)

        self.btn_min = QPushButton("🗕", self.container)
        self.btn_min.setGeometry(730, 5, 30, 30)
        self.btn_min.setStyleSheet(styles.TOP_BTN)
        self.btn_min.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_min.clicked.connect(self.showMinimized)

        self.btn_lang = QPushButton("☰", self.container)
        self.btn_lang.setGeometry(695, 10, 30, 30)
        self.btn_lang.setStyleSheet(styles.TOP_BTN)
        self.btn_lang.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_lang.clicked.connect(self.open_settings)

        self.menu_font = QFont("Segoe UI", 10)
        self._make_menu_button("btn_menu_pm", "lbl_menu_pm", self.lang["nav_pm"], self.show_password_manager)
        self._make_menu_button("btn_menu_home", "lbl_menu_home", self.lang["nav_home"], self.show_home_page)
        self.lbl_menu_about = QLabel(self.lang["nav_about"], self.container)
        self.lbl_menu_about.setFont(self.menu_font)
        self.lbl_menu_about.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_menu_about = QPushButton("", self.container)
        self.btn_menu_about.setStyleSheet(styles.LOGO_HOVER)
        self.btn_menu_about.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_menu_about.clicked.connect(lambda: self.show_info_box("ApexVault", self.lang["credit_msg"]))

        self.setup_system_info_view()
        self.setup_password_manager_view()
        self.show_home_page()
        self.refresh_table()

    def _make_menu_button(self, btn_attr, lbl_attr, text, handler):
        lbl = QLabel(text, self.container)
        lbl.setFont(self.menu_font)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn = QPushButton("", self.container)
        btn.setStyleSheet(styles.LOGO_HOVER)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.clicked.connect(handler)
        setattr(self, btn_attr, btn)
        setattr(self, lbl_attr, lbl)

    def setup_system_info_view(self):
        self.specs_frame = QFrame(self.container)
        self.specs_frame.setGeometry(240, 70, 670, 400)
        self.specs_frame.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self.specs_frame)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.specs_title = QLabel(self.lang["sys_specs"])
        self.specs_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.specs_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.specs_title.setStyleSheet("color: #1c3d5a; margin-bottom: 15px;")
        layout.addWidget(self.specs_title)

        info_text = (f"🖥️  OS: {win_system.os_name()}\n\n"
                     f"💻  Device Name: {win_system.pc_name()}\n\n"
                     f"⚙️  CPU: {win_system.get_exact_cpu_name()}\n\n"
                     f"🧠  RAM: {win_system.get_system_ram_gb()}\n\n"
                     f"🎮  Graphics (GPU): {win_system.get_exact_gpu_name()}")

        self.specs_lbl = QLabel(info_text)
        self.specs_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.specs_lbl.setWordWrap(True)
        self.specs_lbl.setStyleSheet("color: #1c3d5a; line-height: 1.8;")
        self.specs_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.specs_lbl)

    def setup_password_manager_view(self):
        self.btn_app = QPushButton("", self.container)
        self.btn_app.setGeometry(240, 105, 276, 40)
        self.btn_app.setStyleSheet(styles.MAIN_BTN)
        self.btn_app.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_app.clicked.connect(self.add_app)

        self.btn_folder = QPushButton("", self.container)
        self.btn_folder.setGeometry(525, 105, 266, 40)
        self.btn_folder.setStyleSheet(styles.MAIN_BTN)
        self.btn_folder.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_folder.clicked.connect(self.add_folder)

        self.btn_remove = QPushButton("", self.container)
        self.btn_remove.setGeometry(234, 425, 558, 42)
        self.btn_remove.setStyleSheet(styles.MAIN_BTN)
        self.btn_remove.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_remove.clicked.connect(self.remove_item)

        self.lbl_capsule2 = QLabel(self.container)
        self.lbl_capsule2.setGeometry(35, 380, 170, 30)
        self.lbl_capsule2.setStyleSheet(styles.LABEL_LIGHT)

        self.lbl_capsule3 = QLabel(self.container)
        self.lbl_capsule3.setGeometry(35, 410, 170, 30)
        self.lbl_capsule3.setStyleSheet(styles.LABEL_LIGHT)

        self.table = QTableWidget(self.container)
        self.table.setGeometry(282, 195, 536, 240)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([self.lang["col_name"], self.lang["col_type"],
                                              self.lang["col_path"], self.lang["col_status"]])
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setStyleSheet(styles.TABLE_LIGHT)
        for col, w in ((0, 110), (1, 65), (2, 240), (3, 100)):
            self.table.setColumnWidth(col, w)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

    def show_home_page(self):
        if not self.pix_main.isNull():
            self.bg_label.setPixmap(self.pix_main)
        self.lbl_menu_pm.setGeometry(21, 98, 167, 25)
        self.btn_menu_pm.setGeometry(31, 97, 148, 29)
        self.lbl_menu_home.setGeometry(15, 154, 180, 25)
        self.btn_menu_home.setGeometry(32, 153, 146, 29)
        self.lbl_menu_about.setGeometry(25, 211, 166, 25)
        self.btn_menu_about.setGeometry(33, 210, 145, 29)
        self.specs_frame.show()
        for w in (self.btn_app, self.btn_folder, self.btn_remove, self.table,
                  self.lbl_capsule2, self.lbl_capsule3):
            w.hide()
        self.lbl_menu_home.setStyleSheet("color: #5a6e7f; background-color: transparent;")
        self.lbl_menu_pm.setStyleSheet("color: #00F0FF; background-color: transparent;")
        self.lbl_menu_about.setStyleSheet("color: #5a6e7f; background-color: transparent;")

    def show_password_manager(self):
        if not self.pix_pm.isNull():
            self.bg_label.setPixmap(self.pix_pm)
        self.lbl_menu_pm.setGeometry(25, 103, 166, 25)
        self.btn_menu_pm.setGeometry(31, 101, 155, 30)
        self.lbl_menu_home.setGeometry(25, 158, 166, 25)
        self.btn_menu_home.setGeometry(31, 156, 155, 30)
        self.lbl_menu_about.setGeometry(25, 213, 166, 25)
        self.btn_menu_about.setGeometry(31, 211, 155, 30)
        self.specs_frame.hide()
        for w in (self.btn_app, self.btn_folder, self.btn_remove, self.table,
                  self.lbl_capsule2, self.lbl_capsule3):
            w.show()
        self.lbl_menu_pm.setStyleSheet("color: #00F0FF; background-color: transparent;")
        self.lbl_menu_home.setStyleSheet("color: #5a6e7f; background-color: transparent;")
        self.lbl_menu_about.setStyleSheet("color: #5a6e7f; background-color: transparent;")

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.setStyleSheet("background-color: transparent;")
        else:
            self.showMaximized()
            self.setStyleSheet(styles.MAXIMIZED_LIGHT)

    def open_settings(self):
        new_lang = dialogs.select_language(self)
        if not new_lang or new_lang == self.current_lang:
            if new_lang == self.current_lang:
                self.show_info_box("ApexVault", LANGUAGES[new_lang]["lang_same"])
            return
        self.current_lang = new_lang
        self.lang = LANGUAGES[new_lang]
        vault_storage.save_config(new_lang)
        self.lbl_menu_pm.setText(self.lang["nav_pm"])
        self.lbl_menu_home.setText(self.lang["nav_home"])
        self.lbl_menu_about.setText(self.lang["nav_about"])
        self.specs_title.setText(self.lang["sys_specs"])
        self.refresh_table()

    def refresh_table(self):
        self.table.setRowCount(0)
        for app, info in self.db["apps"].items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(app))
            self.table.setItem(row, 1, QTableWidgetItem(self.lang["type_app"]))
            self.table.setItem(row, 2, QTableWidgetItem(info["path"]))
            self.table.setItem(row, 3, QTableWidgetItem(self.lang["active"]))

        for path, info in self.db["folders"].items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(info["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(self.lang["type_folder"]))
            self.table.setItem(row, 2, QTableWidgetItem(path))
            self.table.setItem(row, 3, QTableWidgetItem(self.lang["active"]))

        self.lbl_capsule2.setText(f"Locked Apps: {len(self.db['apps'])}")
        self.lbl_capsule3.setText(f"Locked Folders: {len(self.db['folders'])}")

    def add_app(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Executable", "", "Executables (*.exe)")
        if path:
            name = os.path.basename(path).lower()
            pwd, has_face = dialogs.ask_pwd_setup(self, name, self.lang, self.show_info_box)
            if pwd:
                self.db["apps"][name] = {"path": os.path.abspath(path), "password": pwd, "face_id": has_face}
                self.save_and_refresh()

    def add_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Secure Folder")
        if path:
            path = os.path.abspath(path)
            name = os.path.basename(path)
            pwd, has_face = dialogs.ask_pwd_setup(self, name, self.lang, self.show_info_box)
            if pwd:
                self.db["folders"][path] = {"name": name, "password": pwd, "face_id": has_face}
                self.folder_states[path] = "locked"
                self.save_and_refresh()

    def remove_item(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        item_name = self.table.item(row, 0).text()
        item_type = self.table.item(row, 1).text()
        item_path = self.table.item(row, 2).text()

        if item_type == self.lang["type_app"]:
            self.db["apps"].pop(item_name.lower(), None)
            vault_storage.remove_face_files(item_name.lower())
        else:
            self.db["folders"].pop(item_path, None)
            vault_storage.remove_face_files(os.path.basename(item_path))
        self.save_and_refresh()

    def save_and_refresh(self):
        vault_storage.save_data(self.db)
        self.refresh_table()
        vault_storage.manage_startup(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ApexVaultApp()
    window.show()
    sys.exit(app.exec())