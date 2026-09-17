# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — ApexVault-Python (PyQt6 desktop version)

Build with:
    pyinstaller build.spec --noconfirm --clean

Prerequisites:
  * Rust core compiled to ``apex_crypto.pyd`` at the project root
    (the GitHub Actions workflow does this automatically).
  * Dependencies installed: PyQt6, opencv-python, numpy, dlib,
    face-recognition, face-recognition-models, pyinstaller.
"""

import os
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

# --- Paths (spec-relative, so the build works from any machine) ---
ROOT = os.path.abspath(SPECPATH)

datas = [
    (os.path.join(ROOT, 'assets'), 'assets'),
]

binaries = []
hiddenimports = ['apex_crypto']

# --- Bundle the face-recognition model data (large!) ---
for pkg in ('face_recognition_models', 'face_recognition'):
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hidden
    except Exception as exc:  # package not installed — build continues
        print(f"[build.spec] WARNING: could not collect {pkg}: {exc}")

# --- OpenCV native libraries ---
try:
    binaries += collect_dynamic_libs('cv2')
except Exception as exc:
    print(f"[build.spec] WARNING: could not collect cv2 libs: {exc}")


a = Analysis(
    ['main.py'],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'PyQt5', 'PySide2', 'PySide6', 'matplotlib'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ApexVault-Python',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # keep UPX off: reduces antivirus false positives
    console=False,      # GUI app — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, 'assets', 'icon.ico'),
)