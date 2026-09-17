# -*- coding: utf-8 -*-

import os
import threading

from PyQt6.QtWidgets import (QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout,
                             QHBoxLayout, QFrame, QCheckBox, QWidget, QMessageBox, QApplication)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QCursor

from core import face_auth

def make_password_field():
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    entry = QLineEdit()
    entry.setEchoMode(QLineEdit.EchoMode.Password)
    entry.setStyleSheet("padding: 5px; background: #161925; border: 1px solid #23283D; color: white;")

    btn_eye = QPushButton("👁")
    btn_eye.setFixedSize(30, 28)
    btn_eye.setStyleSheet("background: #23283D; color: white; border: none; font-size: 14px; border-radius: 4px;")
    btn_eye.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def toggle_visibility():
        if entry.echoMode() == QLineEdit.EchoMode.Password:
            entry.setEchoMode(QLineEdit.EchoMode.Normal)
            btn_eye.setText("🚫")
        else:
            entry.setEchoMode(QLineEdit.EchoMode.Password)
            btn_eye.setText("👁")

    btn_eye.clicked.connect(toggle_visibility)
    layout.addWidget(entry)
    layout.addWidget(btn_eye)
    return entry, container

def _draggable_title_bar(dialog, on_close):
    title_bar = QFrame(dialog)
    title_bar.setFixedHeight(30)
    title_bar.setStyleSheet("background-color: #161925; border: none;")

    btn_close = QPushButton("✕", title_bar)
    btn_close.setGeometry(370, 0, 30, 30)
    btn_close.setStyleSheet("background: transparent; color: white; font-weight: bold; border: none; font-size: 12px;")
    btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    btn_close.clicked.connect(on_close)

    def mouse_press(event):
        if event.button() == Qt.MouseButton.LeftButton:
            dialog._drag_pos = event.globalPosition().toPoint() - dialog.pos()

    def mouse_move(event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            dialog.move(event.globalPosition().toPoint() - dialog._drag_pos)

    title_bar.mousePressEvent = mouse_press
    title_bar.mouseMoveEvent = mouse_move
    return title_bar

def ask_pwd_setup(parent, target, lang, info_box):
    dialog = QDialog(parent)
    dialog.setWindowTitle("Set Password")
    dialog.setFixedSize(400, 360)
    dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
    dialog.setStyleSheet("background-color: #0F111A; color: #E2E8F0; border: 1px solid #23283D;")
    dialog.move(200, 130)

    main_layout = QVBoxLayout()
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.addWidget(_draggable_title_bar(dialog, dialog.reject))

    content = QVBoxLayout()
    content.setContentsMargins(20, 10, 20, 20)

    lbl_title = QLabel(f"{lang['setup_msg']}\n{target}")
    lbl_title.setStyleSheet("color: #00F0FF; font-weight: bold; font-size: 14px; border: none;")
    lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    content.addWidget(lbl_title)

    content.addWidget(QLabel(lang["enter_pwd"]))
    entry1, c1 = make_password_field()
    content.addWidget(c1)

    content.addWidget(QLabel(lang["confirm_pwd"]))
    entry2, c2 = make_password_field()
    content.addWidget(c2)

    chk_face = QCheckBox("Enable Face ID (Optional)")
    chk_face.setStyleSheet("border: none; color: #E2E8F0; margin-top: 10px;")
    content.addWidget(chk_face)

    err_lbl = QLabel("")
    err_lbl.setStyleSheet("color: #FF3B30; border: none;")
    content.addWidget(err_lbl)

    btn_ok = QPushButton("OK")
    btn_ok.setStyleSheet("background-color: #00796B; color: white; padding: 8px; border-radius: 4px; margin-top: 10px;")
    btn_ok.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    content.addWidget(btn_ok)

    main_layout.addLayout(content)
    dialog.setLayout(main_layout)

    face_registered = [False]

    def on_face_check():
        if chk_face.isChecked():
            info_box("Face ID", "Please look at the camera to register your face.")
            if face_auth.register_face(target):
                face_registered[0] = True
            else:
                face_registered[0] = False
                chk_face.setChecked(False)
                info_box("Failed", "Face registration cancelled.", is_warning=True)
        else:
            face_registered[0] = False

    chk_face.clicked.connect(on_face_check)

    result = {"pwd": None, "face_id": False}

    def validate():
        p1, p2 = entry1.text(), entry2.text()
        if not p1:
            err_lbl.setText("Password cannot be empty!")
            return
        if p1 != p2:
            err_lbl.setText(lang["mismatch"])
        else:
            result["pwd"] = parent.hash_password(p1)
            result["face_id"] = face_registered[0]
            dialog.accept()

    btn_ok.clicked.connect(validate)

    if dialog.exec() == QDialog.DialogCode.Accepted:
        return result["pwd"], result["face_id"]
    return None, False

def open_gate(key, correct_pwd, path, is_folder, has_face, lang,
              on_unlock_app, on_unlock_folder, verify_pwd, on_cancel=None):
    dialog = QDialog()
    dialog.setWindowTitle("ApexGate")
    dialog.setFixedSize(400, 220)
    dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
    dialog.setStyleSheet("background-color: #0F111A; color: #E2E8F0; border: 1px solid #23283D;")

    screen_center = QApplication.primaryScreen().availableGeometry().center()
    dialog.move(screen_center.x() - dialog.width() // 2, screen_center.y() - dialog.height() // 2)

    btn_close = QPushButton("✕", dialog)
    btn_close.setGeometry(364, 0, 36, 32)
    btn_close.setStyleSheet(
        "QPushButton { background: transparent; color: white; font-weight: bold;"
        " border: none; font-size: 14px; }"
        " QPushButton:hover { background: #E81123; }")
    btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    btn_close.clicked.connect(dialog.reject)

    layout = QVBoxLayout()
    layout.setContentsMargins(20, 34, 20, 16)
    lbl_msg = QLabel(f"⚠️ {os.path.basename(path)}\n{lang['gate_msg']}")
    lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl_msg.setFont(QFont("Tahoma", 12))
    lbl_msg.setStyleSheet("border: none;")
    layout.addWidget(lbl_msg)

    err_lbl = QLabel("")
    err_lbl.setStyleSheet("color: #FF3B30; border: none;")
    err_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(err_lbl)

    entry, container = make_password_field()
    layout.addWidget(container)

    btn_layout = QHBoxLayout()

    btn_unlock = QPushButton("UNLOCK")
    btn_unlock.setStyleSheet("background-color: #00796B; color: white; padding: 10px; font-weight: bold; border-radius: 4px;")
    btn_unlock.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def do_unlock():
        if is_folder:
            on_unlock_folder(path)
        else:
            on_unlock_app(key, path)
        dialog.accept()

    def check_pwd():
        if verify_pwd(correct_pwd, entry.text()):
            do_unlock()
        else:
            err_lbl.setText(lang["error_pass"])
            entry.clear()

    btn_unlock.clicked.connect(check_pwd)
    btn_layout.addWidget(btn_unlock)

    if has_face:
        btn_face = QPushButton("📷 Face ID")
        btn_face.setStyleSheet("background-color: #00A3FF; color: white; padding: 10px; font-weight: bold; border-radius: 4px;")
        btn_face.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        def check_face():
            identifier = os.path.basename(key) if is_folder else key
            if face_auth.verify_face(identifier):
                do_unlock()
            else:
                err_lbl.setText("❌ Face not recognized!")

        btn_face.clicked.connect(check_face)
        btn_layout.addWidget(btn_face)

    layout.addLayout(btn_layout)
    dialog.setLayout(layout)
    dialog.rejected.connect(lambda: on_cancel() if on_cancel else None)
    dialog.exec()

def select_language(parent):
    dialog = QDialog(parent)
    dialog.setWindowTitle("Select Language")
    dialog.setFixedSize(300, 180)
    dialog.setStyleSheet("background-color: #EBF1F6; color: #1c3d5a;")

    layout = QVBoxLayout()
    lbl = QLabel("Select Language / انتخاب زبان")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setFont(QFont("Tahoma", 11))
    layout.addWidget(lbl)

    chosen = [None]

    def pick(code):
        chosen[0] = code
        dialog.accept()

    style = "padding: 8px; border-radius: 5px; border: 1px solid #cfe2f3; background-color: #FFFFFF;"
    for code, label in (("English", "English"), ("Persian", "پارسی")):
        b = QPushButton(label)
        b.setStyleSheet(style)
        b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        b.clicked.connect(lambda _, c=code: pick(c))
        layout.addWidget(b)

    dialog.setLayout(layout)
    dialog.exec()
    return chosen[0]

def show_message(parent, title, message, dark_mode=False, is_warning=False):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(QMessageBox.Icon.Warning if is_warning else QMessageBox.Icon.Information)
    msg.setStyleSheet("QMessageBox { background-color: #EBF1F6; color: #1c3d5a; } QLabel { color: #1c3d5a; font-size: 10pt; } QPushButton { background-color: #FFFFFF; color: #1c3d5a; padding: 6px 18px; border-radius: 4px; border: 1px solid #cfe2f3; font-weight: bold; }")
    msg.exec()
