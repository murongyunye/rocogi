from __future__ import annotations

import ctypes
import os
import sys
from typing import Any, Dict

from .adapters.input import KEY_NAMES, create_input
from .adapters.window import ensure_foreground
from .engine_settings import load_cli_settings
from .hotkeys import parse_hotkey

ACTIONS = ("press", "click", "move", "sequence", "backend", "hotkey")
BACKENDS = ("mock", "windows", "interception")
BUTTONS = ("left", "right", "middle")


def _backend(settings: Dict[str, Any], params: Dict[str, Any]):
    requested = str(params.get("backend") or settings.get("input", {}).get("backend") or "mock")
    if requested not in BACKENDS:
        raise ValueError(f"未知输入后端: {requested}")
    return requested, create_input(requested)


def _find_window(user32: Any, title: str) -> int:
    hwnd = user32.FindWindowW(None, title)
    if hwnd:
        return int(hwnd)

    from ctypes import wintypes

    found: list[int] = []

    def _callback(handle, _lparam):
        length = user32.GetWindowTextLengthW(handle)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(handle, buffer, length + 1)
        if title.lower() in buffer.value.lower():
            found.append(int(handle))
            return False
        return True

    callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(_callback)
    user32.EnumWindows(callback, 0)
    return found[0] if found else 0


def _screen_point(x: int, y: int, settings: Dict[str, Any]) -> tuple[int, int]:
    """Convert client coordinates without importing the capture stack."""
    if not sys.platform.startswith("win"):
        return x, y
    title = str(settings.get("target", {}).get("window_title") or "")
    if not title:
        return x, y
    try:
        user32 = ctypes.windll.user32

        class Point(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        hwnd = _find_window(user32, title)
        if not hwnd:
            return x, y
        point = Point(x, y)
        if not user32.ClientToScreen(hwnd, ctypes.byref(point)):
            return x, y
        return int(point.x), int(point.y)
    except Exception:
        return x, y


def dispatch(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    settings = load_cli_settings(params.get("settings") if isinstance(params.get("settings"), str) else None)

    if action == "hotkey":
        raw_bindings = params.get("bindings") or settings.get("hotkeys") or {}
        if not isinstance(raw_bindings, dict):
            raise ValueError("hotkey.bindings 必须是对象")
        bindings = {
            str(name): str(value)
            for name, value in raw_bindings.items()
            if isinstance(value, str) and value.strip()
        }
        parsed = {}
        for name, value in bindings.items():
            modifiers, key = parse_hotkey(value)
            parsed[name] = {"modifiers": modifiers, "key": key}
        return {"supported": os.name == "nt", "bindings": bindings, "parsed": parsed}

    if action in ("press", "click", "move"):
        target = settings.get("target", {})
        if target.get("kind") == "windows" and target.get("force_foreground", False):
            ensure_foreground(str(target.get("window_title") or ""))

    backend_name, backend = _backend(settings, params)

    if action == "backend":
        return {"backend": backend_name, "platform": settings.get("target", {}).get("kind", "mock")}

    if action == "press":
        key = str(params.get("key") or "").strip().lower()
        if not key:
            raise ValueError("press 需要 params.key")
        if key not in KEY_NAMES:
            raise ValueError(f"未知按键: {key}")
        presses = max(1, min(int(params.get("presses") or 1), 50))
        interval = max(0.0, min(float(params.get("interval") or 0.08), 5.0))
        backend.key(key, presses, interval)
        return {"key": key, "presses": presses, "interval": interval, "backend": backend_name}

    if action == "click":
        x = int(float(params.get("x") or 0))
        y = int(float(params.get("y") or 0))
        button = str(params.get("button") or "left").lower()
        if button not in BUTTONS:
            raise ValueError(f"未知鼠标按键: {button}")
        if backend_name == "interception" and button != "left":
            raise ValueError("Interception 后端当前只支持左键")
        if not params.get("screen", False):
            x, y = _screen_point(x, y, settings)
        backend.click(x, y, button)
        return {"x": x, "y": y, "button": button, "screen": not params.get("screen", False)}

    if action == "move":
        dx = int(float(params.get("dx") or 0))
        dy = int(float(params.get("dy") or 0))
        backend.move(dx, dy)
        return {"dx": dx, "dy": dy}

    if action == "sequence":
        steps = params.get("actions") or []
        if not isinstance(steps, list):
            raise ValueError("sequence 需要 params.actions 数组")
        results = []
        for step in steps[:50]:
            if not isinstance(step, dict):
                raise ValueError("sequence.actions 的元素必须是 {action, params} 对象")
            results.append(dispatch(str(step.get("action") or ""), step.get("params") or {}))
        return {"steps": results}

    raise ValueError(f"未知输入动作: {action}")
