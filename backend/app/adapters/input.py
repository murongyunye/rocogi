from __future__ import annotations

import ctypes
import os
import time
from typing import Any, Dict, List, Optional

from .frame import Frame


KEY_NAMES = {
    "esc": 0x1B,
    "escape": 0x1B,
    "space": 0x20,
    "enter": 0x0D,
    "return": 0x0D,
    "tab": 0x09,
    "shift": 0x10,
    "ctrl": 0x11,
    "alt": 0x12,
    "f": 0x46,
    "x": 0x58,
    "1": 0x31,
    "2": 0x32,
    "3": 0x33,
    "4": 0x34,
    "5": 0x35,
    "6": 0x36,
}
for _i in range(26):
    KEY_NAMES.setdefault(chr(ord("a") + _i), 0x41 + _i)


class MockInput:
    """Records actions so a headless run remains observable and testable."""

    def __init__(self) -> None:
        self.actions: List[Dict[str, Any]] = []

    def key(self, key: str, presses: int = 1, interval: float = 0.08) -> None:
        self.actions.append({"type": "key", "key": key, "presses": presses, "ts": time.time()})
        time.sleep(min(0.02 * presses, 0.05))

    def click(self, x: int, y: int, button: str = "left") -> None:
        self.actions.append({"type": "click", "x": int(x), "y": int(y), "button": button, "ts": time.time()})

    def move(self, dx: int, dy: int) -> None:
        self.actions.append({"type": "move", "dx": int(dx), "dy": int(dy), "ts": time.time()})

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self.actions[-limit:]


class WindowsInput:
    """SendInput based keyboard / mouse backend (Windows only)."""

    def __init__(self) -> None:
        if os.name != "nt":
            raise RuntimeError("WindowsInput 仅支持 Windows")
        from ctypes import wintypes

        self._wintypes = wintypes
        self._user32 = ctypes.windll.user32
        self.actions: List[Dict[str, Any]] = []

    def _send(self, *inputs: Any) -> None:
        from ctypes import wintypes

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [
                ("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
            ]

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
            ]

        class INPUT(ctypes.Structure):
            class _I(ctypes.Union):
                _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]

            _anonymous_ = ("i",)
            _fields_ = [("type", wintypes.DWORD), ("i", self._I)]

        events = []
        for kind, payload in inputs:
            if kind == "key":
                key_name = str(payload).lower()
                vk = KEY_NAMES.get(key_name)
                if vk is None:
                    raise ValueError(f"未知按键: {payload}")
                events.append(INPUT(type=1, ki=KEYBDINPUT(wVk=vk)))
                events.append(INPUT(type=1, ki=KEYBDINPUT(wVk=vk, dwFlags=0x0002)))
            elif kind == "click":
                x, y, button = payload
                flags = {
                    "left": (0x0002, 0x0004),
                    "right": (0x0008, 0x0010),
                    "middle": (0x0020, 0x0040),
                }
                if button not in flags:
                    raise ValueError(f"未知鼠标按键: {button}")
                down, up = flags[button]
                width = self._user32.GetSystemMetrics(0) or 1920
                height = self._user32.GetSystemMetrics(1) or 1080
                nx = int(x * 65535 / max(width, 1))
                ny = int(y * 65535 / max(height, 1))
                events.append(
                    INPUT(
                        type=0,
                        mi=MOUSEINPUT(dx=nx, dy=ny, dwFlags=0x0001 | 0x8000 | down),
                    )
                )
                events.append(
                    INPUT(
                        type=0,
                        mi=MOUSEINPUT(dx=nx, dy=ny, dwFlags=0x0001 | 0x8000 | up),
                    )
                )
            else:
                x, y = payload
                width = self._user32.GetSystemMetrics(0) or 1920
                height = self._user32.GetSystemMetrics(1) or 1080
                nx = int(x * 65535 / max(width, 1))
                ny = int(y * 65535 / max(height, 1))
                events.append(
                    INPUT(
                        type=0,
                        mi=MOUSEINPUT(dx=nx, dy=ny, dwFlags=0x0001 | 0x8000),
                    )
                )
        if events:
            arr = (INPUT * len(events))(*events)
            self._user32.SendInput(len(events), arr, ctypes.sizeof(INPUT))

    def key(self, key: str, presses: int = 1, interval: float = 0.08) -> None:
        for _ in range(max(1, int(presses))):
            self._send(("key", key))
            self.actions.append({"type": "key", "key": key, "presses": 1, "ts": time.time()})
            if interval:
                time.sleep(interval)

    def click(self, x: int, y: int, button: str = "left") -> None:
        self._send(("click", (x, y, button)))
        self.actions.append({"type": "click", "x": int(x), "y": int(y), "button": button, "ts": time.time()})

    def move(self, dx: int, dy: int) -> None:
        cur = self._wintypes.POINT()
        self._user32.GetCursorPos(ctypes.byref(cur))
        self._send(("move", (cur.x + dx, cur.y + dy)))
        self.actions.append({"type": "move", "dx": int(dx), "dy": int(dy), "ts": time.time()})


class InterceptionInput:
    """Driver-level input through the Interception kernel driver (Windows only).

    Requires the Interception driver plus the `interception-python` package.
    """

    def __init__(self) -> None:
        if os.name != "nt":
            raise RuntimeError("InterceptionInput 仅支持 Windows")
        try:
            import interception  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "未安装 interception-python，或 Interception 驱动未安装。"
                "请参考 README 的 Windows 输入章节。"
            ) from exc
        self._interception = interception
        interception.auto_capture_devices()
        self.actions: List[Dict[str, Any]] = []

    def key(self, key: str, presses: int = 1, interval: float = 0.08) -> None:
        for _ in range(max(1, int(presses))):
            self._interception.key_down(key, delay=0)
            time.sleep(max(0.03, interval / 2))
            self._interception.key_up(key, delay=0)
            self.actions.append({"type": "key", "key": key, "presses": 1, "ts": time.time()})
            if interval:
                time.sleep(interval)

    def click(self, x: int, y: int, button: str = "left") -> None:
        self._interception.click(int(x), int(y), delay=0.08)
        self.actions.append({"type": "click", "x": int(x), "y": int(y), "button": button, "ts": time.time()})

    def move(self, dx: int, dy: int) -> None:
        try:
            ctypes.windll.user32.mouse_event(0x0001, int(dx), int(dy), 0, 0)
        except Exception:
            pass
        self.actions.append({"type": "move", "dx": int(dx), "dy": int(dy), "ts": time.time()})


def create_input(backend: str) -> Any:
    if backend == "windows":
        return WindowsInput()
    if backend == "interception":
        return InterceptionInput()
    return MockInput()
