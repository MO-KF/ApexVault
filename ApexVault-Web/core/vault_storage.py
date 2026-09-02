from __future__ import annotations

import json
import logging
import os
import sys
import threading

from core import vault_crypto
from core.vault_crypto import VaultCryptoError, hash_password, verify_password

log = logging.getLogger("apexvault.storage")

class VaultStorage:

    def __init__(self, data_dir: str | None = None):
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        self.data_dir = data_dir or os.path.join(base, "ApexVault")
        os.makedirs(self.data_dir, exist_ok=True)

        self.data_file = os.path.join(self.data_dir, "vault_data.apx")
        self.legacy_file = os.path.join(self.data_dir, "vault_data.json")

        self._lock = threading.RLock()
        self._master_key: bytes | None = None
        self.db: dict = self._load_or_migrate()

    def _load_or_migrate(self) -> dict:
        if os.path.exists(self.data_file) and vault_crypto.looks_encrypted(self.data_file):
            try:
                data = vault_crypto.load_vault(self.data_file)
                log.info("encrypted vault loaded (%d apps, %d folders)",
                         len(data["apps"]), len(data["folders"]))
                return data
            except VaultCryptoError as exc:

                backup = self.data_file + ".orphan"
                try:
                    os.replace(self.data_file, backup)
                    log.error("vault unreadable (%s); backed up to %s", exc, backup)
                except OSError:
                    log.exception("vault unreadable and backup failed")
                fresh = {"apps": {}, "folders": {}}
                self._save(fresh)
                return fresh

        if os.path.exists(self.legacy_file):
            try:
                with open(self.legacy_file, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                data.setdefault("apps", {})
                data.setdefault("folders", {})

                for info in list(data["apps"].values()) + list(data["folders"].values()):
                    pwd = info.get("password")
                    if pwd is not None and "$" not in str(pwd):
                        info["password"] = hash_password(str(pwd))
                self._save(data)

                try:
                    os.remove(self.legacy_file)
                    log.info("legacy plaintext file removed after migration")
                except OSError:
                    log.exception("could not delete legacy vault file")
                log.warning(
                    "legacy plaintext vault migrated to encrypted format "
                    "(%d apps, %d folders)", len(data["apps"]), len(data["folders"])
                )
                return data
            except Exception as exc:

                log.warning("legacy vault not readable (%s: %s); starting clean vault",
                            exc.__class__.__name__, exc)
                backup = self.legacy_file + ".unreadable.bak"
                try:
                    os.replace(self.legacy_file, backup)
                    log.warning("unreadable legacy vault backed up to %s", backup)
                except OSError:
                    log.exception("could not back up unreadable legacy vault")

        return {"apps": {}, "folders": {}}

    def _save(self, db: dict) -> None:
        self._master_key = vault_crypto.save_vault(self.data_file, db, self._master_key)

    def save(self) -> None:
        with self._lock:
            self._save(self.db)

    def get_app(self, exe_name_lower: str) -> dict | None:
        with self._lock:
            return self.db["apps"].get(exe_name_lower)

    def get_folder(self, path: str) -> dict | None:
        with self._lock:
            return self.db["folders"].get(path)

    def get_folder_by_name(self, name: str) -> tuple[str, dict] | None:
        target = name.lower()
        with self._lock:
            for path, info in self.db["folders"].items():
                if info["name"].lower() == target:
                    return path, info
        return None

    def list_items(self, type_label: str, status_label: str) -> list[dict]:
        with self._lock:
            rows: list[dict] = []
            rows += [
                {
                    "name": app.lower(),
                    "type": type_label,
                    "item_type": "app",
                    "path": info["path"],
                    "status": status_label,
                }
                for app, info in self.db["apps"].items()
            ]
            rows += [
                {
                    "name": info["name"],
                    "type": type_label,
                    "item_type": "folder",
                    "path": path,
                    "status": status_label,
                }
                for path, info in self.db["folders"].items()
            ]
            return rows

    def counts(self) -> tuple[int, int]:
        with self._lock:
            return len(self.db["apps"]), len(self.db["folders"])

    def has_any(self) -> bool:
        with self._lock:
            return bool(self.db["apps"] or self.db["folders"])

    @staticmethod
    def _normalize(path: str) -> str:
        if sys.platform.startswith("win"):
            return os.path.abspath(path)
        return path

    def add_item(self, item_type: str, name: str, path: str,
                 password: str, face_id: bool) -> None:
        hashed = hash_password(password)
        with self._lock:
            if item_type == "app":
                self.db["apps"][name.lower()] = {
                    "path": self._normalize(path),
                    "password": hashed,
                    "face_id": bool(face_id),
                }
            else:
                self.db["folders"][self._normalize(path)] = {
                    "name": name,
                    "password": hashed,
                    "face_id": bool(face_id),
                }
            self._save(self.db)

    def remove_item(self, item_type: str, name: str, path: str) -> None:
        with self._lock:
            if item_type == "app":
                self.db["apps"].pop(name.lower(), None)
            else:
                self.db["folders"].pop(path, None)
            self._save(self.db)

    def check_password(self, key: str, password: str, is_folder: bool) -> bool:
        with self._lock:
            info = self.db["folders"].get(key) if is_folder else self.db["apps"].get(key)
        if not info:
            return False
        stored = info.get("password") or ""
        ok = verify_password(password, stored)
        if ok and "$" not in stored and password:

            try:
                with self._lock:
                    info["password"] = hash_password(password)
                    self._save(self.db)
            except Exception:
                log.exception("could not upgrade legacy password hash")
        return ok
