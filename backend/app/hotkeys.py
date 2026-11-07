from __future__ import annotations

"""Global hotkeys for realtime/tracker sessions (Windows only).

The manager registers system-wide hotkeys through ``RegisterHotKey`` in a
dedicated message-loop thread. On other platforms it reports
``supported: false`` and never starts a thread, so the rest of the app keeps
working in mock/Linux environments.
"""

import ctypes
import os
import threading
from typing import Any, Callable, Dict, Optional

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

VK_NAMES: Dict[str, int] = {
    "space": 0x20,
    "enter": 0x0D,
    "return": 0x0D,
    "tab": 0x09,
    "esc": 0x1B,
    "escape": 0x1B,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "insert": 0x2D,
    "delete": 0x2E,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
}
for _index in range(1, 25):
    VK_NAMES[f"f{_index}"] = 0x70 + _index - 1
for _index in range(10):
    VK_NAMES[str(_index)] = 0x30 + _index
for _index in range(26):
    VK_NAMES[chr(ord("a") + _index)] = 0x41 + _index

DEFAULT_BINDINGS = {"start": "f9", "stop": "f10", "tracker": "f11"}


def parse_hotkey(value: str) -> tuple[int, int]:
    """Return (modifiers, virtual-key) for strings like 'ctrl+shift+f9'."""
    parts = [part.strip().lower() for part in str(value).split("+") if part.strip()]
    if not parts:
        raise ValueError("快捷键为空")
    modifiers = 0
    key = ""
    for part in parts:
        if part in ("ctrl", "control"):
            modifiers |= MOD_CONTROL
        elif part in ("alt",):
            modifiers |= MOD_ALT
        elif part in ("shift",):
            modifiers |= MOD_SHIFT
        elif part in ("win", "meta"):
            modifiers |= MOD_WIN
        elif part in VK_NAMES:
            key = part
        else:
            raise ValueError(f"未知快捷键: {part}")
    if not key:
        raise ValueError(f"快捷键缺少主键: {value}")
    return modifiers, VK_NAMES[key]


class HotkeyManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._stop = threading.Event()
        self._bindings: Dict[str, str] = {}
        self._status = "idle"
        self._error = ""
        self._triggered: list[str] = []

    @property
    def supported(self) -> bool:
        return os.name == "nt"

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "supported": self.supported,
                "running": bool(self._thread and self._thread.is_alive()),
                "status": self._status,
                "error": self._error,
                "bindings": dict(self._bindings),
                "triggered": list(self._triggered[-10:]),
            }

    def start(self, bindings: Dict[str, str], callback: Callable[[str], None]) -> Dict[str, Any]:
        self.stop()
        if not self.supported:
            with self._lock:
                self._status = "unsupported"
                self._bindings = dict(bindings)
            return self.status()
        parsed = {action: parse_hotkey(value) for action, value in bindings.items() if value}
        with self._lock:
            self._bindings = dict(bindings)
            self._stop.clear()
            self._status = "starting"
            self._error = ""
        self._thread = threading.Thread(target=self._run, args=(parsed, callback), daemon=True, name="rocoflow-hotkeys")
        self._thread.start()
        return self.status()

    def stop(self) -> Dict[str, Any]:
        thread = self._thread
        if thread and thread.is_alive():
            self._stop.set()
            if self._thread_id:
                try:
                    ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
                except Exception:  # noqa: BLE001
                    pass
            thread.join(timeout=2)
        with self._lock:
            self._thread = None
            self._thread_id = None
            if self._status not in ("error", "unsupported"):
                self._status = "idle"
        return self.status()

    def _run(self, parsed: Dict[str, tuple[int, int]], callback: Callable[[str], None]) -> None:
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._thread_id = int(kernel32.GetCurrentThreadId())
        registered: list[int] = []
        actions = list(parsed.keys())
        try:
            for index, action in enumerate(actions, start=1):
                modifiers, key = parsed[action]
                if not user32.RegisterHotKey(None, index, modifiers, key):
                    raise RuntimeError(f"注册快捷键失败: {self._bindings.get(action)}")
                registered.append(index)
            with self._lock:
                self._status = "running"
            message = wintypes.MSG()
            while not self._stop.is_set():
                result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                if result == 0 or result == -1:
                    break
                if message.message == WM_HOTKEY:
                    identifier = int(message.wParam)
                    if 0 <= identifier - 1 < len(actions):
                        action = actions[identifier - 1]
                        with self._lock:
                            self._triggered.append(action)
                        try:
                            callback(action)
                        except Exception as exc:  # noqa: BLE001
                            with self._lock:
                                self._error = str(exc)
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self._status = "error"
                self._error = str(exc)
        finally:
            for identifier in registered:
                try:
                    user32.UnregisterHotKey(None, identifier)
                except Exception:  # noqa: BLE001
                    pass
            with self._lock:
                if self._status != "error":
                    self._status = "idle"
