# -*- coding: utf-8 -*-

import os
import sys
import json
import hashlib
import hmac as _hmac
import winreg

from core import vault_crypto

APP_DATA_DIR = os.path.join(os.environ.get('APPDATA', 'C:\\'), 'ApexVault')
if not os.path.exists(APP_DATA_DIR):
    os.makedirs(APP_DATA_DIR)
DATA_FILE = os.path.join(APP_DATA_DIR, 'vault_data.json')
CONFIG_FILE = os.path.join(APP_DATA_DIR, 'config.json')

def load_config():

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f).get("lang", "English")
        except Exception:
            return "English"
    return "English"

def save_config(lang_code):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"lang": lang_code}, f)

def load_data():

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "rb") as f:
                raw = f.read()
            if raw.startswith(vault_crypto.MAGIC):
                return json.loads(vault_crypto.decrypt_bytes(raw).decode("utf-8"))
            data = json.loads(raw.decode("utf-8"))
            save_data(data)
            return data
        except Exception:
            pass
    return {"apps": {}, "folders": {}}

def save_data(db_obj):

    plaintext = json.dumps(db_obj, ensure_ascii=False, indent=4).encode("utf-8")
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "wb") as f:
        f.write(vault_crypto.encrypt_bytes(plaintext))
    os.replace(tmp, DATA_FILE)

def hash_password(password: str) -> str:

    salt = os.urandom(16).hex()
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000, 32)
    return f"pbkdf2_sha256$100000${salt}${key.hex()}"

def verify_password(stored_hash: str, password: str) -> bool:

    if not isinstance(stored_hash, str) or not stored_hash.startswith("pbkdf2_sha256$"):
        return False
    try:
        _, iterations, salt, stored_key = stored_hash.split("$")
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), int(iterations), 32)
        return _hmac.compare_digest(key.hex(), stored_key)
    except Exception:
        return False

def manage_startup(enable: bool):

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        if enable:
            exe_path = os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else sys.argv[0])
            winreg.SetValueEx(key, "ApexVaultGuardian", 0, winreg.REG_SZ, f'"{exe_path}" --startup')
        else:
            try:
                winreg.DeleteValue(key, "ApexVaultGuardian")
            except OSError:
                pass
        winreg.CloseKey(key)
    except OSError:
        pass

def remove_face_files(base_name: str):

    for ext in ('.npy', '.pkl'):
        face_file = os.path.join(APP_DATA_DIR, 'faces', f"{base_name}{ext}")
        if os.path.exists(face_file):
            try:
                os.remove(face_file)
            except OSError:
                pass