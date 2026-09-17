from __future__ import annotations

import contextlib
import hashlib
import logging
import os
import time

log = logging.getLogger("apexvault.face")

FACE_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")), "ApexVault", "faces"
)
os.makedirs(FACE_DIR, exist_ok=True)

TOLERANCE = 0.45
DOWNSCALE = 0.25
REGISTER_TIMEOUT = 90.0
VERIFY_TIMEOUT = 20.0
REQUIRED_HITS = 3

try:
    import numpy as np
except ImportError:
    np = None

def _faceid_available() -> bool:
    try:
        import cv2
        import face_recognition
        return True
    except ImportError:
        return False

def _target_path(identifier: str) -> str:
    digest = hashlib.sha256(str(identifier).encode("utf-8")).hexdigest()
    return os.path.join(FACE_DIR, digest + ".npy")

def has_face(identifier: str) -> bool:
    return os.path.exists(_target_path(identifier))

def _grab_stable_frame(cap, timeout: float):
    import cv2
    import face_recognition

    deadline = time.time() + timeout
    while time.time() < deadline:
        ok, frame = cap.read()
        if not ok:
            return None
        small = cv2.resize(frame, (0, 0), fx=DOWNSCALE, fy=DOWNSCALE)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb)
        cv2.imshow("ApexVault Face ID", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            return None
        if cv2.getWindowProperty("ApexVault Face ID", cv2.WND_PROP_VISIBLE) < 1:
            return None
        if locations:
            return rgb, locations
    return None

def _release(cap=None):
    with contextlib.suppress(Exception):
        if cap is not None and cap.isOpened():
            cap.release()
    with contextlib.suppress(Exception):
        import cv2
        cv2.destroyAllWindows()

def register_face(identifier: str) -> bool:
    if not _faceid_available():
        log.warning("face_auth unavailable: cv2/face_recognition missing")
        return False

    import cv2
    import face_recognition
    import numpy as np

    cap = None
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            log.error("camera could not be opened")
            return False

        result = _grab_stable_frame(cap, REGISTER_TIMEOUT)
        if result is None:
            return False
        rgb, locations = result
        if len(locations) != 1:
            log.info("register aborted: %d faces in frame", len(locations))
            return False

        encoding = face_recognition.face_encodings(rgb, locations)
        if not encoding:
            return False

        path = _target_path(identifier)
        tmp = path + ".tmp"
        np.save(tmp, np.asarray(encoding[0], dtype=np.float64))
        os.replace(tmp + ".npy" if not tmp.endswith(".npy") else tmp,
                   path)
        log.info("face registered for %s", identifier[:32])
        return True
    except Exception:
        log.exception("register_face failed")
        return False
    finally:
        _release(cap)

def verify_face(identifier: str) -> bool:
    if not _faceid_available():
        log.warning("face_auth unavailable: cv2/face_recognition missing")
        return False

    path = _target_path(identifier)
    if not os.path.exists(path):
        log.info("no enrolled face for %s", identifier[:32])
        return False

    import cv2
    import face_recognition
    import numpy as np

    known = np.load(path, allow_pickle=False)

    cap = None
    hits = 0
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            log.error("camera could not be opened")
            return False

        deadline = time.time() + VERIFY_TIMEOUT
        while time.time() < deadline:
            ok, frame = cap.read()
            if not ok:
                return False
            small = cv2.resize(frame, (0, 0), fx=DOWNSCALE, fy=DOWNSCALE)
            rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            locations = face_recognition.face_locations(rgb)
            cv2.imshow("ApexVault Face ID", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                return False
            if cv2.getWindowProperty("ApexVault Face ID", cv2.WND_PROP_VISIBLE) < 1:
                return False
            if not locations:
                hits = 0
                continue

            encodings = face_recognition.face_encodings(rgb, locations)
            best = min(
                (
                    face_recognition.face_distance([known], enc)[0]
                    for enc in encodings
                ),
                default=1.0,
            )
            if best <= TOLERANCE:
                hits += 1
                if hits >= REQUIRED_HITS:
                    return True
            else:
                hits = 0
        return False
    except Exception:
        log.exception("verify_face failed")
        return False
    finally:
        _release(cap)

def delete_face(identifier: str) -> bool:
    path = _target_path(identifier)
    try:
        if os.path.exists(path):
            os.remove(path)
            return True
    except OSError:
        log.exception("delete_face failed")
    return False
