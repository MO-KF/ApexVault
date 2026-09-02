# -*- coding: utf-8 -*-

import base64
import os
import platform
import tempfile

MAGIC = b"AVX1"
SALT_B64 = "QXBleFZhdWx0"
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_KEY_FILE = os.path.join(_ROOT, "key.vault")

def _protect_key(raw: bytes) -> bytes:

    try:
        import win32crypt
        return win32crypt.CryptProtectData(raw, "ApexVaultKey", None, None, None, 0)
    except ImportError:
        import hashlib
        machine = platform.node() or "apexvault"
        mask = hashlib.sha256(machine.encode()).digest()
        return bytes(b ^ mask[i % len(mask)] for i, b in enumerate(raw))

def _unprotect_key(blob: bytes) -> bytes:
    try:
        import win32crypt
        out = win32crypt.CryptUnprotectData(blob, None, None, None, 0)
        return out[1]
    except ImportError:
        import hashlib
        machine = platform.node() or "apexvault"
        mask = hashlib.sha256(machine.encode()).digest()
        return bytes(b ^ mask[i % len(mask)] for i, b in enumerate(blob))

def load_or_create_key() -> bytes:

    if os.path.exists(_KEY_FILE):
        try:
            with open(_KEY_FILE, "rb") as f:
                key = _unprotect_key(f.read())
            if isinstance(key, bytes) and len(key) == 32:
                return key
        except Exception:
            pass
    key = os.urandom(32)
    tmp = _KEY_FILE + ".tmp"
    with open(tmp, "wb") as f:
        f.write(_protect_key(key))
    os.replace(tmp, _KEY_FILE)
    return key

def _rust_module():

    try:
        mod = __import__("apex_crypto")
        if hasattr(mod, "encrypt_file") and hasattr(mod, "decrypt_file"):
            return mod
    except Exception:
        pass
    return None

def _pyca_encrypt(key: bytes, plaintext: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = os.urandom(12)
    return MAGIC + nonce + AESGCM(key).encrypt(nonce, plaintext, None)

def _pyca_decrypt(key: bytes, blob: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if len(blob) < len(MAGIC) + 12 + 16:
        raise ValueError("ciphertext too short")
    if blob[:len(MAGIC)] != MAGIC:
        raise ValueError("bad magic header")
    nonce, ct = blob[len(MAGIC):len(MAGIC) + 12], blob[len(MAGIC) + 12:]
    return AESGCM(key).decrypt(nonce, ct, None)

def encrypt_bytes(data: bytes) -> bytes:

    key = load_or_create_key()
    rust = _rust_module()
    if rust is not None:
        fd, tmp_plain = tempfile.mkstemp(prefix="apexvault-", suffix=".tmp")
        os.close(fd)
        try:
            with open(tmp_plain, "wb") as f:
                f.write(data)
            rust.encrypt_file(tmp_plain, base64.b64encode(key).decode(), SALT_B64)
            with open(tmp_plain, "rb") as f:
                out = f.read()
            return MAGIC + out
        finally:
            if os.path.exists(tmp_plain):
                os.remove(tmp_plain)
    return _pyca_encrypt(key, data)

def decrypt_bytes(blob: bytes) -> bytes:

    key = load_or_create_key()
    if not blob.startswith(MAGIC):
        raise ValueError("not an encrypted vault file")
    body = blob[len(MAGIC):]
    try:
        return _pyca_decrypt(key, MAGIC + body)
    except Exception:
        pass
    rust = _rust_module()
    if rust is not None:
        fd, tmp_enc = tempfile.mkstemp(prefix="apexvault-", suffix=".tmp")
        os.close(fd)
        try:
            with open(tmp_enc, "wb") as f:
                f.write(body)
            rust.decrypt_file(tmp_enc, base64.b64encode(key).decode(), SALT_B64)
            with open(tmp_enc, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(tmp_enc):
                os.remove(tmp_enc)
    raise ValueError("decryption failed")