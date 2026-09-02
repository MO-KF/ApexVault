# -*- coding: utf-8 -*-

import platform
import subprocess
import winreg
import ctypes
from ctypes import wintypes

TH32CS_SNAPPROCESS = 0x00000002
WM_CLOSE = 0x0010
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG), ("dwFlags", wintypes.DWORD),
                ("szExeFile", ctypes.c_wchar * 260)]

def get_running_processes():

    kernel32 = ctypes.windll.kernel32
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == -1 or snapshot == 0:
        return {}
    pe = PROCESSENTRY32W()
    pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    pids = {}
    if kernel32.Process32FirstW(snapshot, ctypes.byref(pe)):
        while True:
            exe_name = pe.szExeFile.lower()
            if exe_name not in pids:
                pids[exe_name] = []
            pids[exe_name].append(pe.th32ProcessID)
            if not kernel32.Process32NextW(snapshot, ctypes.byref(pe)):
                break
    kernel32.CloseHandle(snapshot)
    return pids

def get_explorer_windows():

    windows = []

    def enum_handler(hwnd, lParam):
        if ctypes.windll.user32.IsWindow(hwnd):
            class_name = ctypes.create_unicode_buffer(260)
            ctypes.windll.user32.GetClassNameW(hwnd, class_name, 260)
            if class_name.value == "CabinetWClass":
                title = ctypes.create_unicode_buffer(260)
                ctypes.windll.user32.GetWindowTextW(hwnd, title, 260)
                windows.append((hwnd, title.value))
        return True

    ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_handler), 0)
    return windows

def os_name():

    import platform
    return f"{platform.system()} {platform.release()}"

def pc_name():

    return platform.node()

def get_exact_cpu_name():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        winreg.CloseKey(key)
        return cpu_name.strip()
    except Exception:
        return platform.processor()

def get_exact_gpu_name():
    try:
        cmd = 'powershell -command "(Get-WmiObject Win32_VideoController).Name"'
        output = subprocess.check_output(cmd, shell=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        lines = [line.strip() for line in output.split('\n') if line.strip()]
        valid_gpus = [g for g in lines if "Standard" not in g and "Basic" not in g]
        if valid_gpus:
            return " / ".join(valid_gpus)
        elif lines:
            return " / ".join(lines)
    except Exception:
        pass
    return "Standard Display Adapter"

def get_system_ram_gb():
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
    total_ram = stat.ullTotalPhys / (1024 ** 3)
    if 14.5 < total_ram < 16.5:
        return "16 GB"
    elif 7.5 < total_ram < 8.5:
        return "8 GB"
    elif 31.5 < total_ram < 33.0:
        return "32 GB"
    return f"{round(total_ram)} GB"

def kill_process(pid):

    kernel32 = ctypes.windll.kernel32
    kernel32.TerminateProcess(kernel32.OpenProcess(1, False, pid), 0)

def close_window(hwnd):

    ctypes.windll.user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)