from __future__ import annotations

import ctypes
import platform
import re
import socket
import subprocess
import sys
import os
import threading

try:
    import winreg
except ImportError:
    winreg = None

try:
    from ctypes import wintypes
except ImportError:
    wintypes = None

IS_WINDOWS = platform.system() == "Windows"

TH32CS_SNAPPROCESS = 0x00000002
WM_CLOSE = 0x0010
PROCESS_TERMINATE = 0x0001
WNDENUMPROC = None
if IS_WINDOWS and wintypes is not None:
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

SINGLE_INSTANCE_PORT = 59422
SHOW_REQUEST = b"apexvault-show\n"

class ProcessEntryW(ctypes.Structure):

    _fields_ = [
        ("dwSize", wintypes.DWORD if wintypes else ctypes.c_ulong),
        ("cntUsage", wintypes.DWORD if wintypes else ctypes.c_ulong),
        ("th32ProcessID", wintypes.DWORD if wintypes else ctypes.c_ulong),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", wintypes.DWORD if wintypes else ctypes.c_ulong),
        ("cntThreads", wintypes.DWORD if wintypes else ctypes.c_ulong),
        ("th32ParentProcessID", wintypes.DWORD if wintypes else ctypes.c_ulong),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD if wintypes else ctypes.c_ulong),
        ("szExeFile", ctypes.c_wchar * 260),
    ]

def get_running_processes() -> dict[str, list[int]]:
    if not IS_WINDOWS:
        return {}
    kernel32 = ctypes.windll.kernel32
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snapshot or snapshot == -1:
        return {}
    pe = ProcessEntryW()
    pe.dwSize = ctypes.sizeof(ProcessEntryW)
    pids: dict[str, list[int]] = {}
    try:
        if kernel32.Process32FirstW(snapshot, ctypes.byref(pe)):
            while True:
                exe_name = pe.szExeFile.lower()
                pids.setdefault(exe_name, []).append(pe.th32ProcessID)
                if not kernel32.Process32NextW(snapshot, ctypes.byref(pe)):
                    break
    finally:
        kernel32.CloseHandle(snapshot)
    return pids

def terminate_processes(pids: list[int]) -> int:
    killed = 0
    if not IS_WINDOWS:
        return killed
    kernel32 = ctypes.windll.kernel32
    for pid in pids:
        handle = None
        try:
            handle = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
            if handle:
                if kernel32.TerminateProcess(handle, 0):
                    killed += 1
        except Exception:
            continue
        finally:
            if handle:
                kernel32.CloseHandle(handle)
    return killed

def kill_app_everywhere(exe_name_lower: str) -> int:
    pids = get_running_processes().get(exe_name_lower, [])
    return terminate_processes(pids)

def get_explorer_windows() -> list[tuple[int, str]]:
    if not IS_WINDOWS or WNDENUMPROC is None:
        return []
    windows: list[tuple[int, str]] = []

    def enum_handler(hwnd, _lparam):
        user32 = ctypes.windll.user32
        if user32.IsWindow(hwnd):
            class_name = ctypes.create_unicode_buffer(260)
            user32.GetClassNameW(hwnd, class_name, 260)
            if class_name.value == "CabinetWClass":
                title = ctypes.create_unicode_buffer(260)
                user32.GetWindowTextW(hwnd, title, 260)
                windows.append((hwnd, title.value))
        return True

    ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_handler), 0)
    return windows

def close_explorer_window(hwnd: int) -> bool:
    if not IS_WINDOWS:
        return False
    try:
        ctypes.windll.user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        return True
    except Exception:
        return False

def title_matches_folder(title: str, folder_name: str) -> bool:
    t = (title or "").strip().lower()
    name = (folder_name or "").strip().lower()
    if not t or not name:
        return False
    for suffix in (" - file explorer", " - windows explorer"):
        if t.endswith(suffix):
            t = t[: -len(suffix)].strip()
            break

    return re.search(rf"(?:^|\\){re.escape(name)}(?:\\|$)", t) is not None

def close_folder_windows(folder_name: str) -> bool:
    hit = False
    for hwnd, title in get_explorer_windows():
        if title_matches_folder(title, folder_name):
            close_explorer_window(hwnd)
            hit = True
    return hit

def is_folder_open(folder_name: str) -> bool:
    for _, title in get_explorer_windows():
        if title_matches_folder(title, folder_name):
            return True
    return False

def open_path(path: str) -> bool:
    try:
        os.startfile(path)
        return True
    except Exception:
        return False

def get_cpu_name() -> str:
    if IS_WINDOWS and winreg is not None:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            return name.strip()
        except Exception:
            pass
    return platform.processor() or "Unknown CPU"

def get_gpu_name() -> str:
    if IS_WINDOWS:
        try:
            cmd = 'powershell -NoProfile -command "(Get-CimInstance Win32_VideoController).Name"'
            output = subprocess.check_output(
                cmd, shell=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            lines = [line.strip() for line in output.split("\n") if line.strip()]
            primary = [g for g in lines if "Standard" not in g and "Basic" not in g]
            if primary:
                return " / ".join(primary)
            if lines:
                return " / ".join(lines)
        except Exception:
            pass
    return platform.processor() or "Standard Display Adapter"

def get_ram_gb() -> str:
    if not IS_WINDOWS or wintypes is None:
        try:
            with open("/proc/meminfo", encoding="ascii") as fh:
                for line in fh:
                    if line.startswith("MemTotal"):
                        kb = int(line.split()[1])
                        return f"{round(kb / 1024**2)} GB"
        except Exception:
            pass
        return "-"
    kernel32 = ctypes.windll.kernel32

    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", wintypes.DWORD),
            ("dwMemoryLoad", wintypes.DWORD),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    stat = MemoryStatusEx()
    stat.dwLength = ctypes.sizeof(MemoryStatusEx)
    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
        return "-"
    return f"{round(stat.ullTotalPhys / (1024 ** 3))} GB"

def get_os_label() -> str:
    if not IS_WINDOWS:
        return f"{platform.system()} {platform.release()}"
    release = platform.release()
    build = platform.version().split(".")[-1] if platform.version() else ""
    label = f"Windows {release}" if release.isdigit() or release else "Windows"
    try:
        if int(build) >= 22000:
            label = "Windows 11"
    except ValueError:
        pass
    return label

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "ApexVaultGuardian"

def _autostart_command() -> str:

    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --hidden'
    script = os.path.abspath(sys.argv[0]) if sys.argv else ""
    python = os.path.abspath(sys.executable)

    pythonw = os.path.join(os.path.dirname(python), "pythonw.exe")
    launcher = pythonw if os.path.isfile(pythonw) else python
    return f'"{launcher}" "{script}" --hidden'

def set_autostart(enable: bool) -> bool:
    if not IS_WINDOWS or winreg is None:
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE
        )
        try:
            if enable:
                winreg.SetValueEx(
                    key, RUN_VALUE_NAME, 0, winreg.REG_SZ, _autostart_command()
                )
            else:
                try:
                    winreg.DeleteValue(key, RUN_VALUE_NAME)
                except FileNotFoundError:
                    pass
        finally:
            winreg.CloseKey(key)
        return True
    except Exception:
        return False

class SingleInstanceGuard:

    def __init__(self, port: int = SINGLE_INSTANCE_PORT):
        self.port = port
        self._sock = None
        self._show_callback = None

    def acquire(self) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("127.0.0.1", self.port))
            self._sock = sock
            return True
        except OSError:
            return False

    def start_show_listener(self, callback) -> None:
        if self._sock is None or callback is None:
            return
        self._show_callback = callback
        threading.Thread(
            target=self._listen_loop,
            name="apexvault-show-listener",
            daemon=True,
        ).start()

    def _listen_loop(self) -> None:
        try:
            self._sock.listen(2)
            self._sock.settimeout(1.0)
            while True:
                try:
                    conn, _addr = self._sock.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                with conn:
                    try:
                        if conn.recv(64).startswith(SHOW_REQUEST):
                            cb = self._show_callback
                            if cb:

                                threading.Thread(target=cb, daemon=True).start()
                    except OSError:
                        continue
        except Exception:
            pass

    def release(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

def request_show_previous_instance(port: int = SINGLE_INSTANCE_PORT) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.5) as conn:
            conn.sendall(SHOW_REQUEST)
            return True
    except OSError:
        return False

def run_detached_elevated(path: str) -> bool:
    if not IS_WINDOWS:
        return False
    try:
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", path, None, None, 1)
        return ret > 32
    except Exception:
        return False
