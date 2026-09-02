from __future__ import annotations

import base64
import ctypes
import hashlib
import hmac
import json
import logging
import os
import secrets
import sys

log = logging.getLogger("apexvault.crypto")

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAVE_CRYPTO = True
except ImportError:
    AESGCM = None
    HAVE_CRYPTO = False

try:
    import apex_crypto as _rust

    HAVE_RUST = hasattr(_rust, "gcm_encrypt")
except ImportError:
    _rust = None
    HAVE_RUST = False

def _rust_gcm_encrypt(key: bytes, plaintext: bytes) -> bytes:
    return _rust.gcm_encrypt(key, plaintext)

def _rust_gcm_decrypt(key: bytes, blob: bytes) -> bytes:
    return _rust.gcm_decrypt(key, blob)

PBKDF2_ITERATIONS = 600_000
SALT_BYTES = 16
KEY_BYTES = 32
NONCE_BYTES = 12

MAGIC = b"APXV"
FORMAT_VERSION = 1

class VaultCryptoError(Exception):
    pass

def hash_password(password: str) -> str:
    if not isinstance(password, str) or not password:
        raise ValueError("password must be a non-empty string")
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return f"{base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        salt_b64, hash_b64 = stored.split("$", 1)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
    except Exception:

        return hmac.compare_digest(str(stored), str(password or ""))

    candidate = hashlib.pbkdf2_hmac(
        "sha256", (password or "").encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return len(candidate) == len(expected) and hmac.compare_digest(candidate, expected)

class _DPAPI_BLOB(ctypes.Structure):

    _fields_ = [("cbData", ctypes.c_uint), ("pbData", ctypes.c_void_p)]

if sys.platform == "win32":
    _CryptProtectData = ctypes.windll.crypt32.CryptProtectData
    _CryptProtectData.argtypes = [
        ctypes.POINTER(_DPAPI_BLOB),
        ctypes.c_wchar_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.POINTER(_DPAPI_BLOB),
    ]
    _CryptProtectData.restype = ctypes.c_int

    _CryptUnprotectData = ctypes.windll.crypt32.CryptUnprotectData
    _CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DPAPI_BLOB),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.POINTER(_DPAPI_BLOB),
    ]
    _CryptUnprotectData.restype = ctypes.c_int
else:
    _CryptProtectData = None
    _CryptUnprotectData = None

def _local_free(ptr) -> None:
    if ptr:
        ctypes.windll.kernel32.LocalFree(ctypes.c_void_p(ptr))

def _dpapi_protect(data: bytes) -> bytes | None:
    if _CryptProtectData is None:
        return None

    buf = ctypes.create_string_buffer(bytes(data), len(data))
    blob_in = _DPAPI_BLOB(len(data), ctypes.cast(buf, ctypes.c_void_p))
    blob_out = _DPAPI_BLOB()
    ok = _CryptProtectData(
        ctypes.byref(blob_in), "ApexVault", None, None, None, 0,
        ctypes.byref(blob_out),
    )
    if not ok or not blob_out.pbData or not blob_out.cbData:
        return None
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        _local_free(blob_out.pbData)

def _dpapi_unprotect(data: bytes) -> bytes | None:
    if _CryptUnprotectData is None:
        return None

    buf = ctypes.create_string_buffer(bytes(data), len(data))
    blob_in = _DPAPI_BLOB(len(data), ctypes.cast(buf, ctypes.c_void_p))
    blob_out = _DPAPI_BLOB()
    descr = ctypes.c_void_p()
    ok = _CryptUnprotectData(
        ctypes.byref(blob_in), ctypes.byref(descr), None, None, None, 0,
        ctypes.byref(blob_out),
    )
    try:
        if not ok or not blob_out.pbData or not blob_out.cbData:
            return None
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        _local_free(blob_out.pbData)
        _local_free(descr.value)

def generate_master_key() -> bytes:
    if HAVE_RUST:
        return bytes(_rust.random_bytes(KEY_BYTES))
    return secrets.token_bytes(KEY_BYTES)

def aes_gcm_encrypt(key: bytes, plaintext: bytes) -> bytes:
    if HAVE_RUST:
        return _rust_gcm_encrypt(key, plaintext)
    nonce = secrets.token_bytes(NONCE_BYTES)
    if HAVE_CRYPTO:
        return nonce + AESGCM(key).encrypt(nonce, plaintext, None)
    return nonce + _fallback_xor_stream(key, nonce, plaintext) + _fallback_tag(
        key, nonce, plaintext
    )

def aes_gcm_decrypt(key: bytes, blob: bytes) -> bytes:
    if len(blob) < NONCE_BYTES + 16:
        raise VaultCryptoError("vault container is truncated")
    if HAVE_RUST:
        try:
            return _rust_gcm_decrypt(key, blob)
        except Exception as exc:
            raise VaultCryptoError("decryption failed") from exc
    nonce, rest = blob[:NONCE_BYTES], blob[NONCE_BYTES:]
    ciphertext, tag = rest[:-16], rest[-16:]
    if HAVE_CRYPTO:
        try:
            return AESGCM(key).decrypt(nonce, ciphertext + tag, None)
        except Exception as exc:
            raise VaultCryptoError("decryption failed") from exc
    expected_tag = _fallback_tag(key, nonce, ciphertext)
    if not hmac.compare_digest(expected_tag, tag):
        raise VaultCryptoError("decryption failed")
    return _fallback_xor_stream(key, nonce, ciphertext)

def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])

def _fallback_xor_stream(key: bytes, nonce: bytes, data: bytes) -> bytes:
    ks = _keystream(key, nonce, len(data))
    return bytes(a ^ b for a, b in zip(data, ks))

def _fallback_tag(key: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
    return hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()[:16]

def save_vault(path: str, db: dict, master_key: bytes | None = None) -> bytes:
    plaintext = json.dumps(db, ensure_ascii=False, indent=2).encode("utf-8")
    if master_key is None:
        master_key = generate_master_key()

    protected = _dpapi_protect(master_key)
    if protected is not None:
        mode = b"D"
        wrapped = protected
    else:

        mode = b"R"
        wrap_key = hashlib.sha256(
            ("apexvault-local|" + os.path.expanduser("~")).encode()
        ).digest()
        wrapped = aes_gcm_encrypt(wrap_key, master_key)

    header = MAGIC + bytes([FORMAT_VERSION]) + mode + len(wrapped).to_bytes(2, "little")
    blob = aes_gcm_encrypt(master_key, plaintext)

    tmp_path = path + ".tmp"
    with open(tmp_path, "wb") as fh:
        fh.write(header + wrapped + blob)
    os.replace(tmp_path, path)
    return master_key

def load_vault(path: str) -> dict:
    with open(path, "rb") as fh:
        raw = fh.read()

    if raw[:4] != MAGIC:
        raise VaultCryptoError("not an ApexVault container")
    version = raw[4]
    if version != FORMAT_VERSION:
        raise VaultCryptoError(f"unsupported vault version {version}")
    mode = raw[5:6]
    wrapped_len = int.from_bytes(raw[6:8], "little")
    wrapped = raw[8:8 + wrapped_len]
    blob = raw[8 + wrapped_len:]

    if mode == b"D":
        master_key = _dpapi_unprotect(wrapped)
        if master_key is None:
            raise VaultCryptoError(
                "master key cannot be unwrapped on this user/machine"
            )
    elif mode == b"R":
        wrap_key = hashlib.sha256(
            ("apexvault-local|" + os.path.expanduser("~")).encode()
        ).digest()
        master_key = aes_gcm_decrypt(wrap_key, wrapped)
    else:
        raise VaultCryptoError("unknown key-wrap mode")

    data = json.loads(aes_gcm_decrypt(master_key, blob).decode("utf-8"))
    data.setdefault("apps", {})
    data.setdefault("folders", {})
    return data

def looks_encrypted(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            return fh.read(4) == MAGIC
    except OSError:
        return False
