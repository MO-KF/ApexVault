# Building a standalone executable

## PyInstaller (Windows)

```bash
pip install pyinstaller

# from the project root:
pyinstaller --name ApexVault --noconfirm --clean \
  --windowed --icon assets/icon.ico \
  --add-data "web;web" --add-data "assets;assets" \
  main.py
```

Notes:

* The `--add-data` lines bundle the frontend (`web/`) and icons (`assets/`).
  The backend resolves them through `sys._MEIPASS` (see `ui/backend.py`,
  `resource_path` / `WEB_DIR`).
* Tray icons: pythonnet needs `System.Drawing` — PyInstaller usually picks
  it up through the `clr_loader` hooks; if the tray is missing in the exe,
  add `--collect-all clr_loader --collect-all pythonnet`.
* Face ID models are large; if you build WITH face support, also add
  `--collect-all face_recognition_models`.
* Output lands in `dist/ApexVault/`. Both `build/` and `dist/` are git-ignored.

The autostart entry points at the executable itself with `--hidden`
(see `core/win_system.py`), so the packaged exe works as the background
guardian out of the box.
