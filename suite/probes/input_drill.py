"""SendInput fallback drill.

Interception is a kernel driver and needs an interactive elevated session; the
elevated installer exits immediately here, so this drill validates the fallback
path instead: 10 real key presses accepted by SendInput, echoed by a scratch
Tk editor window, then that window is closed.
"""
from __future__ import annotations

import ctypes
import json
import sys
import time

KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1
user32 = ctypes.windll.user32


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class _U(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", ctypes.c_ulong), ("u", _U)]


def send(vk: int, flags: int = 0) -> int:
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki = KEYBDINPUT(vk, 0, flags, 0, None)
    return int(user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) or 0)


def main() -> int:
    import tkinter as tk

    keys = list("abcdefghij")
    root = tk.Tk()
    root.title("rocogi sendinput drill")
    root.geometry("360x120+80+80")
    text = tk.Text(root, height=4, width=30)
    text.pack()
    text.focus_force()
    root.update()

    hwnd = user32.GetParent(root.winfo_id())
    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    root.update()
    time.sleep(0.5)

    accepted = 0
    for k in keys:
        accepted += send(ord(k.upper())) + send(ord(k.upper()), KEYEVENTF_KEYUP)
        root.update()
        time.sleep(0.02)
    time.sleep(0.4)
    root.update()
    typed = text.get("1.0", "end-1c")
    root.destroy()

    report = {
        "ok": accepted == len(keys) * 2 and typed == "abcdefghij",
        "attempted": len(keys),
        "apiAccepted": accepted,
        "editorText": typed,
        "mechanism": "SendInput (foreground only)",
        "interception": "unavailable: kernel driver install needs interactive elevation",
    }
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
