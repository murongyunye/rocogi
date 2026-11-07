from __future__ import annotations

"""Window lookup and foreground/focus helpers.

Keeps GDI capture and SendInput from operating on a background or minimized
window. The implementation is ctypes-only and degrades to a structured
``supported: false`` result on non-Windows platforms.
"""

import os
from typing import Any, Dict

SW_RESTORE = 9
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_SHOWWINDOW = 0x0040
HWND_TOP = 0


def find_window(keyword: str) -> int:
    if os.name != "nt" or not keyword:
        return 0
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    exact = user32.FindWindowW(None, keyword)
    if exact:
        return int(exact)
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            if keyword.lower() in buffer.value.lower():
                found.append(int(hwnd))
                return False
        return True

    user32.EnumWindows(callback, 0)
    return found[0] if found else 0


def ensure_foreground(title: str = "", hwnd: int = 0) -> Dict[str, Any]:
    if os.name != "nt":
        return {
            "ok": False,
            "supported": False,
            "hwnd": 0,
            "reason": "窗口前台管理仅支持 Windows",
        }
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    handle = int(hwnd or find_window(title))
    if not handle:
        return {"ok": False, "supported": True, "hwnd": 0, "reason": f"未找到窗口: {title}"}
    restored = False
    if user32.IsIconic(handle):
        user32.ShowWindow(handle, SW_RESTORE)
        restored = True
    user32.BringWindowToTop(handle)
    user32.SetWindowPos(handle, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    activated = bool(user32.SetForegroundWindow(handle))
    if not activated:
        foreground = int(user32.GetForegroundWindow())
        current_thread = int(ctypes.windll.kernel32.GetCurrentThreadId())
        target_thread = int(user32.GetWindowThreadProcessId(foreground, None)) if foreground else 0
        if target_thread:
            user32.AttachThreadInput(current_thread, target_thread, True)
            user32.BringWindowToTop(handle)
            user32.SetForegroundWindow(handle)
            user32.AttachThreadInput(current_thread, target_thread, False)
    current = int(user32.GetForegroundWindow())
    return {
        "ok": current == handle,
        "supported": True,
        "hwnd": handle,
        "restored": restored,
        "foreground": current,
    }
