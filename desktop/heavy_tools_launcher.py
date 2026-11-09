"""Launch the Screenshot Lab without loading its image workspace in Vision."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import subprocess
import sys


LAB_TITLE = 'BDO Vision · Screenshot Lab'


def open_lab(process):
    if process is not None and process.poll() is None:
        user32 = ctypes.windll.user32
        user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
        user32.FindWindowW.restype = wintypes.HWND
        user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        hwnd = user32.FindWindowW(None, LAB_TITLE)
        pid = wintypes.DWORD()
        if hwnd and user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid)) and pid.value == process.pid:
            user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
            user32.SetForegroundWindow.argtypes = [wintypes.HWND]
            user32.ShowWindow(hwnd, 9)
            user32.SetForegroundWindow(hwnd)
        return process
    command = [sys.executable]
    if not getattr(sys, 'frozen', False):
        command.append(str(Path(__file__).with_name('app.py').resolve()))
    return subprocess.Popen([*command, '--heavy-tools'], creationflags=subprocess.CREATE_NO_WINDOW)
