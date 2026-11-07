"""input engine - key/mouse injection.

Integration source (MERGE_MAP): game-automation src/engine/controller.py (Interception based).
2026-11-06 (rev2): dual-backend per user directive 鈥?SendInput (software) and
Interception (kernel filter driver) coexist as input devices; dispatch order is
taken from config `backend_preference`, first ready backend wins, and the next
ready backend is used as fallback. Backend health is reported independently in
probe output. The SendInput path carries the corrected INPUT union (must include
MOUSEINPUT on x64 or SendInput silently rejects every packet 鈥?rocogi audit
critical #1). ACE note: SendInput strokes carry the LLMHF_INJECTED flag which
user-mode anti-cheat can observe; Interception is kernel-level but class filter
drivers may still be enumerated by ACE-BASE 鈥?no bypass is guaranteed.
Own venv / process. Injection is disabled unless config allows it.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import queue
import sys
import threading
import time

SUITE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.path.dirname(os.path.dirname(SUITE))
GAME_AUTOMATION = os.path.join(WORK, "rocogi", "vendor", "SCH-CMYK-game-automation")
sys.path.insert(0, GAME_AUTOMATION)

ENGINE = "input"

VK = {
    "f": 0x46, "x": 0x58, "c": 0x43, "z": 0x5A, "w": 0x57, "a": 0x41, "s": 0x53, "d": 0x44,
    "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34, "5": 0x35, "space": 0x20, "enter": 0x0D, "esc": 0x1B,
}


def emit(log_path, event, **payload):
    rec = {"ts": round(time.time(), 3), "engine": ENGINE, "type": event, **payload}
    line = json.dumps(rec, ensure_ascii=False)
    print(line, flush=True)
    if log_path:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def load_toml(path):
    import tomllib

    with open(path, "rb") as fh:
        return tomllib.load(fh)


# --- SendInput (software) backend -------------------------------------------


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_ushort),
        ("wParamH", ctypes.c_ushort),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT), ("hi", _HARDWAREINPUT)]


class _INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT), ("hi", _HARDWAREINPUT)]

    _anonymous_ = ("u",)
    _fields_ = [("type", ctypes.c_ulong), ("u", _U)]


# hard guard: on x64 the union is sizeof(MOUSEINPUT)+pointer = 40; without
# MOUSEINPUT in the union sizeof(INPUT) collapses to 32 and SendInput rejects
# every packet silently (critical #1 in the rocogi audit).
assert ctypes.sizeof(_INPUT) == ctypes.sizeof(_MOUSEINPUT) + ctypes.sizeof(ctypes.c_void_p), (
    f"INPUT union miscompiled: sizeof(INPUT)={ctypes.sizeof(_INPUT)}, "
    f"expected {ctypes.sizeof(_MOUSEINPUT) + ctypes.sizeof(ctypes.c_void_p)}"
)

_INPUT_KEYBOARD = 1
_KEYEVENTF_KEYUP = 0x0002
_INPUT_MOUSE = 0
_MOUSEEVENTF_MOVE = 0x0001
_MOUSEEVENTF_LEFTDOWN = 0x0002
_MOUSEEVENTF_LEFTUP = 0x0004
_MOUSEEVENTF_RIGHTDOWN = 0x0008
_MOUSEEVENTF_RIGHTUP = 0x0010
_MOUSEEVENTF_WHEEL = 0x0800
_MOUSEEVENTF_ABSOLUTE = 0x8000
_MOUSEEVENTF_VIRTUALDESK = 0x4000


class SendInputBackend:
    """input.sendinput - user32.SendInput software injection (driver-free)."""

    def __init__(self):
        self._send = ctypes.windll.user32.SendInput

    def _stroke(self, vk: int, up: bool) -> None:
        inp = _INPUT()
        inp.type = _INPUT_KEYBOARD
        inp.ki = _KEYBDINPUT(
            wVk=vk,
            wScan=0,
            dwFlags=_KEYEVENTF_KEYUP if up else 0,
            time=0,
            dwExtraInfo=None,
        )
        arr = (_INPUT * 1)(inp)
        sent = self._send(1, arr, ctypes.sizeof(_INPUT))
        if sent != 1:
            raise OSError(f"SendInput rejected packet (sent={sent})")

    def _mouse(self, flags: int, dx: int = 0, dy: int = 0, data: int = 0) -> None:
        inp = _INPUT()
        inp.type = _INPUT_MOUSE
        inp.mi = _MOUSEINPUT(dx=dx, dy=dy, mouseData=data & 0xFFFFFFFF, dwFlags=flags, time=0,
                             dwExtraInfo=None)
        arr = (_INPUT * 1)(inp)
        sent = self._send(1, arr, ctypes.sizeof(_INPUT))
        if sent != 1:
            raise OSError(f"SendInput rejected mouse packet (sent={sent})")

    def _abs(self, x: int, y: int):
        """Normalise screen pixels to the 0..65535 virtual-desktop space."""
        u32 = ctypes.windll.user32
        sw = u32.GetSystemMetrics(0) or 1
        sh = u32.GetSystemMetrics(1) or 1
        nx = int(round((x + 1) * 65535.0 / sw))
        ny = int(round((y + 1) * 65535.0 / sh))
        return max(0, min(65535, nx)), max(0, min(65535, ny))

    def key(self, name: str, hold: float = 0.08) -> None:
        vk = VK[name.lower()]
        hold = max(0.01, hold)
        self._stroke(vk, False)
        time.sleep(hold)
        self._stroke(vk, True)

    def position(self):
        import ctypes.wintypes as wintypes

        pt = wintypes.POINT()
        if not ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
            return None
        return (pt.x, pt.y)

    def move(self, x: int, y: int) -> None:
        nx, ny = self._abs(x, y)
        self._mouse(_MOUSEEVENTF_MOVE | _MOUSEEVENTF_ABSOLUTE | _MOUSEEVENTF_VIRTUALDESK, nx, ny)
        time.sleep(0.03)
        pos = self.position()
        if pos is None or abs(pos[0] - x) > 2 or abs(pos[1] - y) > 2:
            # ACE / a captured cursor can swallow the ABSOLUTE packet; try the
            # direct API once before declaring the path unusable.
            ctypes.windll.user32.SetCursorPos(int(x), int(y))
            time.sleep(0.02)
            pos = self.position()
        if pos is None or abs(pos[0] - x) > 2 or abs(pos[1] - y) > 2:
            raise OSError(f"cursor did not reach ({x},{y}); got {pos} - SendInput cursor moves "
                          f"appear blocked (anti-cheat); prefer the interception backend")

    def click(self, x: int, y: int, button: str = "left") -> None:
        down, up = ((_MOUSEEVENTF_LEFTDOWN, _MOUSEEVENTF_LEFTUP) if button != "right"
                    else (_MOUSEEVENTF_RIGHTDOWN, _MOUSEEVENTF_RIGHTUP))
        self.move(x, y)
        time.sleep(0.05)
        self._mouse(down)
        time.sleep(0.06)
        self._mouse(up)

    def scroll(self, amount: int, x: int = None, y: int = None) -> None:
        if x is not None and y is not None:
            self.move(x, y)
            time.sleep(0.05)
        self._mouse(_MOUSEEVENTF_WHEEL, data=int(amount))

    def down(self, button: str = "left") -> None:
        self._mouse(_MOUSEEVENTF_RIGHTDOWN if button == "right" else _MOUSEEVENTF_LEFTDOWN)

    def up(self, button: str = "left") -> None:
        self._mouse(_MOUSEEVENTF_RIGHTUP if button == "right" else _MOUSEEVENTF_LEFTUP)


# --- Interception (kernel filter driver) backend -----------------------------


class InterceptionBackend:
    """input.interception - kernel-level injection via the vendor Controller.

    Raises when the Interception driver is not installed / devices not open.
    """

    def __init__(self):
        from src.engine.controller import Controller

        self.ctl = Controller()

    def key(self, name: str, hold: float = 0.08) -> None:
        self.ctl.press(name, max(0.01, hold))

    def move(self, x: int, y: int) -> None:
        self.ctl.move_to(int(x), int(y), human_like=False)

    def click(self, x: int, y: int, button: str = "left") -> None:
        if button == "right":
            self.ctl.right_click(int(x), int(y))
        else:
            self.ctl.click(int(x), int(y), "left")

    def scroll(self, amount: int, x: int = None, y: int = None) -> None:
        self.ctl.scroll(int(amount), x, y)

    def down(self, button: str = "left") -> None:
        self.ctl.mouse_down(button)

    def up(self, button: str = "left") -> None:
        self.ctl.mouse_up(button)


BACKENDS = {
    "sendinput": SendInputBackend,
    "interception": InterceptionBackend,
}

COMPONENTS = ["input.mock", "input.sendinput", "input.interception", "input.key_queue", "input.hotkey",
              "input.window_lock"]


def _client_rect(hwnd: int):
    """Client area of hwnd in screen pixels: (left, top, right, bottom)."""
    import ctypes.wintypes as wt

    user32 = ctypes.windll.user32
    r = wt.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    tl = wt.POINT(0, 0)
    br = wt.POINT(int(r.right), int(r.bottom))
    user32.ClientToScreen(hwnd, ctypes.byref(tl))
    user32.ClientToScreen(hwnd, ctypes.byref(br))
    return (int(tl.x), int(tl.y), int(br.x), int(br.y))


def find_game_window(keyword: str, min_client=(400, 300)):
    """Largest visible, non-minimised top-level window whose title contains keyword."""
    if sys.platform != "win32" or not keyword:
        return (0, "")
    import ctypes.wintypes as wt

    user32 = ctypes.windll.user32
    hits = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def _cb(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf, 512)
        if keyword not in buf.value:
            return True
        rect = wt.RECT()
        user32.GetClientRect(hwnd, ctypes.byref(rect))
        w, h = int(rect.right), int(rect.bottom)
        if w < min_client[0] or h < min_client[1]:
            return True
        hits.append((w * h, int(hwnd), buf.value))
        return True

    try:
        user32.EnumWindows(_cb, 0)
    except Exception:  # noqa: BLE001
        return (0, "")
    if not hits:
        return (0, "")
    hits.sort(reverse=True)
    return (hits[0][1], hits[0][2])


def ensure_foreground(hwnd: int) -> dict:
    """Make hwnd the foreground window (AttachThreadInput unlocks SetForegroundWindow)."""
    if sys.platform != "win32" or not hwnd:
        return {"ok": False, "reason": "unavailable"}
    import ctypes.wintypes as wt

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    fg = int(user32.GetForegroundWindow())
    if fg == hwnd:
        return {"ok": True, "already": True, "foreground": fg}
    fg_thread = int(user32.GetWindowThreadProcessId(fg, None)) if fg else 0
    own_thread = int(kernel32.GetCurrentThreadId())
    attached = False
    try:
        if fg_thread and fg_thread != own_thread:
            attached = bool(user32.AttachThreadInput(own_thread, fg_thread, True))
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetFocus(hwnd)
        time.sleep(0.05)
    finally:
        if attached:
            user32.AttachThreadInput(own_thread, fg_thread, False)
    now = int(user32.GetForegroundWindow())
    return {"ok": now == hwnd, "foreground": now, "attached": attached, "hwnd": hwnd}


def game_window(cfg) -> dict:
    """input.window_lock - the game window and its client rect, or a reason we have none."""
    section = cfg["input"]
    keyword = section.get("window_title_keyword") or cfg.get("window", {}).get("title_keyword") or ""
    if sys.platform != "win32":
        return {"status": "unavailable", "reason": "windows only"}
    if not keyword:
        return {"status": "skipped", "reason": "no window_title_keyword configured"}
    min_client = tuple(section.get("min_client", [400, 300]))
    hwnd, title = find_game_window(keyword, min_client)
    if not hwnd:
        return {"status": "not-found", "keyword": keyword}
    rect = _client_rect(hwnd)
    user32 = ctypes.windll.user32
    fg = int(user32.GetForegroundWindow())
    fg_root = int(user32.GetAncestor(fg, 2)) if fg else 0
    return {"status": "ok", "hwnd": hwnd, "title": title, "client": list(rect),
            "foreground": fg == hwnd or fg_root == hwnd}


def _point_owner(x: int, y: int) -> dict:
    """Which top-level window actually receives a click at screen (x, y)?

    2026-11-06 local-hardware fix: the client-rect check alone let a click land on
    whatever window happened to sit above the game (measured: a click at a battle
    UI point activated the editor window, which then covered the game and the next
    capture returned the editor). The point owner is the only truthful answer.
    """
    import ctypes.wintypes as wt

    user32 = ctypes.windll.user32
    target = int(user32.WindowFromPoint(wt.POINT(int(x), int(y))))
    root = int(user32.GetAncestor(target, 2)) if target else 0  # GA_ROOT
    buf = ctypes.create_unicode_buffer(512)
    if root:
        user32.GetWindowTextW(root, buf, 512)
    return {"hwnd": target, "root": root, "title": buf.value}


def lock_guard(cfg, method, args) -> dict:
    """Enforce "only operate inside the game window" before any injection.

    Returns {"ok": True, "window": {...}} when the call may proceed, otherwise
    {"ok": False, "status": ..., "reason": ..., "window": {...}}.
    """
    section = cfg["input"]
    if not bool(section.get("lock_to_window", True)):
        return {"ok": True, "window": {"status": "lock-disabled"}}
    win = game_window(cfg)
    if win.get("status") != "ok":
        return {"ok": False, "status": "blocked",
                "reason": "game window not available; refusing to inject anywhere else",
                "window": win}
    if method in ("move", "click", "scroll", "down", "up") and args and args[0] is not None:
        x, y = int(args[0]), int(args[1])
        left, top, right, bottom = win["client"]
        if not (left <= x <= right and top <= y <= bottom):
            return {"ok": False, "status": "blocked",
                    "reason": f"({x},{y}) is outside the game client rect {win['client']}",
                    "window": win}
        cover = _point_owner(x, y)
        if cover["root"] != int(win["hwnd"]):
            return {"ok": False, "status": "blocked",
                    "reason": (f"another window covers ({x},{y}): hwnd {cover['root']} "
                               f"{cover['title']!r}; refusing to click through it"),
                    "window": {**win, "cover": cover}}
    if bool(section.get("require_foreground", True)) and not win["foreground"]:
        fg = ensure_foreground(win["hwnd"])
        win = {**win, "foreground": bool(fg.get("ok")), "refocus": fg}
        if not fg.get("ok"):
            return {"ok": False, "status": "blocked",
                    "reason": "game window is not foreground and could not be focused",
                    "window": win}
    return {"ok": True, "window": win}


def ready_backends(cfg):
    """Instantiate backends in preference order; return [(name, instance)] ready."""
    preference = cfg["input"].get("backend_preference", ["interception", "sendinput"])
    ready = []
    for name in preference:
        maker = BACKENDS.get(name)
        if maker is None:
            continue
        try:
            ready.append((name, maker()))
        except Exception:  # noqa: BLE001 - unhealthy backend falls out silently here
            continue
    return ready


class KeyQueue:
    """input.key_queue - serialised, background key dispatch (one worker per engine)."""

    def __init__(self, injector):
        self.q = queue.Queue()
        self.injector = injector
        self.sent = 0
        self.errors = []
        self.worker = threading.Thread(target=self._loop, name="key-queue", daemon=True)
        self.worker.start()

    def _loop(self):
        while True:
            item = self.q.get()
            if item is None:
                return
            try:
                self.injector.key(item, 0.02)
                self.sent += 1
            except Exception as exc:  # noqa: BLE001
                self.errors.append(f"{type(exc).__name__}: {exc}")
            finally:
                self.q.task_done()

    def drain(self, keys):
        for key in keys:
            self.q.put(key)
        self.q.join()
        return {"queued": len(keys), "sent": self.sent, "errors": self.errors}

    def stop(self):
        self.q.put(None)


def hotkey_selftest(cfg):
    """input.hotkey - real RegisterHotKey / message-pump round trip."""
    if sys.platform != "win32":
        return {"status": "unavailable", "reason": "windows only"}
    vk = int(cfg["input"].get("hotkey_vk", 0x46))
    mods = int(cfg["input"].get("hotkey_modifiers", 0x0001 | 0x0002))
    out = {"registered": False, "received": False}

    def worker():
        user32 = ctypes.windll.user32
        ok = user32.RegisterHotKey(None, 1, mods, vk)
        out["registered"] = bool(ok)
        if not ok:
            return
        deadline = time.time() + 0.3
        msg = ctypes.create_string_buffer(64)
        while time.time() < deadline:
            if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0x0001):
                out["received"] = True
            time.sleep(0.01)
        user32.UnregisterHotKey(None, 1)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join(1.0)
    return {"status": "ok" if out["registered"] else "failed", "vk": vk, "modifiers": mods, **out}


def probe(cfg):
    result = {"action": "probe", "backends": {}}
    preference = cfg["input"].get("backend_preference", ["interception", "sendinput"])
    # sendinput - software path, always compiled in
    try:
        SendInputBackend()
        result["backends"]["sendinput"] = {
            "status": "ready",
            "sizeof_INPUT": ctypes.sizeof(_INPUT),
            "capabilities": ["key", "move", "click", "scroll"],
            "note": "strokes carry LLMHF_INJECTED (visible to user-mode AC e.g. ACE)",
        }
    except Exception as exc:  # noqa: BLE001
        result["backends"]["sendinput"] = {
            "status": "skipped",
            "reason": f"{type(exc).__name__}: {exc}",
            "component": "input.sendinput",
        }
    # interception - kernel filter driver via vendor Controller
    try:
        backend = InterceptionBackend()
        result["backends"]["interception"] = {
            "status": "ready",
            "class": type(backend.ctl).__name__,
            "capabilities": ["key", "move", "click", "scroll", "down", "up"],
            "note": "kernel-level, no LLMHF_INJECTED; class filter may still be enumerated by ACE-BASE",
        }
        try:
            backend.ctl.release_lock()  # hygiene only; vendor raises if lock not held
        except Exception:  # noqa: BLE001 - upstream quirk, not a driver problem
            result["backends"]["interception"]["note"] += "; release_lock() no-op (vendor quirk)"
    except Exception as exc:  # noqa: BLE001
        result["backends"]["interception"] = {
            "status": "skipped",
            "reason": f"driver required: {type(exc).__name__}: {exc}",
            "component": "input.interception",
        }
    result["preference"] = preference
    result["selected"] = next((b for b in preference if result["backends"].get(b, {}).get("status") == "ready"),
                              None)
    result["injectionAllowed"] = bool(cfg["input"].get("allow_injection", False))
    result["components"] = COMPONENTS
    return result


def dispatch(cfg, method, payload, *args, **kwargs):
    """input.dispatch - run one backend call through the preference order.

    Returns the JSON-ready result dict; every attempted backend is reported so a
    degraded path is visible instead of silently swallowed.
    """
    allowed = bool(cfg["input"].get("allow_injection", False))
    if not allowed:
        return {"action": method, **payload, "status": "skipped",
                "reason": "allow_injection=false in config/engines/input.toml"}
    guard = lock_guard(cfg, method, args)
    if not guard["ok"]:
        return {"action": method, **payload, "status": guard["status"],
                "reason": guard["reason"], "window": guard["window"]}
    tried = []
    for be_name, backend in ready_backends(cfg):
        fn = getattr(backend, method, None)
        if fn is None:
            tried.append({"backend": be_name, "error": f"{method} not supported"})
            continue
        try:
            fn(*args, **kwargs)
            return {"action": method, **payload, "status": "sent", "backend": be_name,
                    "window": guard["window"], "fallbacks": tried}
        except Exception as exc:  # noqa: BLE001
            tried.append({"backend": be_name, "error": f"{type(exc).__name__}: {exc}"})
    return {"action": method, **payload, "status": "unavailable",
            "backends_tried": tried, "error": "no ready backend in preference order"}


def press(cfg, key_name=None, hold=None):
    name = key_name or cfg["input"].get("probe_key", "f")
    hold = float(hold if hold is not None else cfg["input"].get("hold", 0.08))
    return dispatch(cfg, "key", {"key": name, "hold": hold}, name, hold)


def move(cfg, x, y):
    return dispatch(cfg, "move", {"x": x, "y": y}, x, y)


def click(cfg, x, y, button="left"):
    return dispatch(cfg, "click", {"x": x, "y": y, "button": button}, x, y, button)


def scroll(cfg, amount, x=None, y=None):
    if x is not None and y is not None:
        return dispatch(cfg, "scroll", {"amount": amount, "x": x, "y": y}, amount, x, y)
    return dispatch(cfg, "scroll", {"amount": amount}, amount)


def queue_test(cfg):
    """input.key_queue - exercise the queue through the first ready backend."""
    allowed = bool(cfg["input"].get("allow_injection", False))
    if not allowed:
        return {"action": "queue", "status": "ready",
                "reason": "drained in dry-run mode; allow_injection=false",
                "components": ["input.key_queue"]}
    ready = ready_backends(cfg)
    if not ready:
        return {"action": "queue", "status": "unavailable",
                "error": "no ready backend in preference order",
                "components": ["input.key_queue"]}
    be_name, backend = ready[0]
    kq = KeyQueue(backend)
    res = kq.drain([cfg["input"].get("probe_key", "f")])
    kq.stop()
    return {"action": "queue", "status": "sent", "backend": be_name,
            "detail": res, "components": ["input.key_queue"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--log", default="")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--action", default="probe")
    ap.add_argument("--key", default=None)
    ap.add_argument("--x", type=int, default=None)
    ap.add_argument("--y", type=int, default=None)
    ap.add_argument("--button", default="left")
    ap.add_argument("--amount", type=int, default=-120)
    ap.add_argument("--hold", type=float, default=None)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=float, default=1.0)
    args = ap.parse_args()

    cfg = load_toml(args.config)
    emit(args.log, "ready", run_id=args.run_id, config=args.config, python=sys.version.split()[0],
         components=COMPONENTS)

    def run():
        if args.action in ("press", "hold"):
            return press(cfg, args.key, args.hold)
        if args.action == "queue":
            return queue_test(cfg)
        if args.action == "hotkey":
            return {"action": "hotkey", **hotkey_selftest(cfg), "components": ["input.hotkey"]}
        if args.action == "move":
            return move(cfg, args.x, args.y)
        if args.action == "click":
            return click(cfg, args.x, args.y, args.button)
        if args.action == "scroll":
            return scroll(cfg, args.amount, args.x, args.y)
        return probe(cfg)

    if not args.once:
        try:
            while True:
                emit(args.log, "result", result=run())
                time.sleep(max(0.1, args.interval))
        except KeyboardInterrupt:
            return 0

    try:
        emit(args.log, "result", result=run())
    except Exception as exc:  # noqa: BLE001
        emit(args.log, "error", error=f"{type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
