"""capture engine - window/screenshot layer.

Integration source (MERGE_MAP): Auto-rocokingdom core/capture.py (PrintWindow + BitBlt).
Runs in its own venv / process. Does not import any other suite engine.

2026-11-06 local-hardware fixes (found during supervised play session):
1. find_window(): the old version returned hit[0] 鈥?on this machine an invisible
   0x0 ghost window shares the title, so capture silently produced 1x1 black
   frames. Now: require IsWindowVisible + not iconic + client >= min_client,
   then pick the LARGEST matching window.
2. D3D frames: PrintWindow/BitBlt against the WINDOW dc of a hardware-accelerated
   title returns a stale (frozen) or all-black surface 鈥?measured on
   NRC-Win64-Shipping.exe: 10 minutes of identical frames while the process
   burned 123% CPU. The DESKTOP dc cropped to the client rect is live (frame diff
   keeps moving). `window.backend` = auto|printwindow|screen selects the path;
   auto verifies the window-dc frame is not blank and falls back to screen dc.
3. Results now report mean/nonBlack/liveDiff so a blank or frozen frame is
   visible in the event stream instead of looking like "a static scene".
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

SUITE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.path.dirname(os.path.dirname(SUITE))
AUTO_ROOT = os.path.join(WORK, "rocogi", "vendor", "yorusacri-Auto-rocokingdom")
sys.path.insert(0, AUTO_ROOT)

ENGINE = "capture"

MIN_CLIENT = (400, 300)
SRCCOPY = 0x00CC0020
CAPTUREBLT = 0x40000000

COMPONENTS = ["capture.mock_window", "capture.windows_window", "capture.screen_dc",
              "capture.frame_digest", "capture.scene_switch", "capture.foreground"]


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


def find_window(title_keyword: str, min_client=MIN_CLIENT) -> dict:
    """Locate the real game window: visible, not minimized, big enough.

    Returns {"hwnd", "title", "client": [w, h], "rejected": [...]}; hwnd=0 if none.
    """
    out = {"hwnd": 0, "title": "", "client": [0, 0], "rejected": []}
    try:
        import win32gui

        hits = []

        def _cb(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
                return
            title = win32gui.GetWindowText(hwnd)
            if not title or title_keyword not in title:
                return
            l, t, r, b = win32gui.GetClientRect(hwnd)
            w, h = r - l, b - t
            if w < min_client[0] or h < min_client[1]:
                out["rejected"].append({"hwnd": hwnd, "client": [w, h], "why": "client too small"})
                return
            hits.append({"hwnd": hwnd, "title": title, "client": [w, h]})

        win32gui.EnumWindows(_cb, None)
        if hits:
            best = max(hits, key=lambda x: x["client"][0] * x["client"][1])
            out.update(best)
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def frame_digest(img) -> dict:
    import numpy as np

    h, w = img.shape[:2]
    return {"width": int(w), "height": int(h), "hash": hashlib.sha256(np.ascontiguousarray(img).tobytes()).hexdigest()[:16]}


def grab_screen_client(hwnd: int):
    """Live capture: desktop DC cropped to the window's client area.

    DWM always composites the desktop surface, so this stays live for D3D titles
    where a window-DC grab returns a frozen or blank surface.
    """
    import ctypes

    import numpy as np
    import win32gui

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    l, t, r, b = win32gui.GetClientRect(hwnd)
    cw, ch = r - l, b - t
    if cw <= 0 or ch <= 0:
        raise ValueError(f"empty client rect {cw}x{ch}")
    cx, cy = win32gui.ClientToScreen(hwnd, (0, 0))

    class _BIH(ctypes.Structure):
        _fields_ = [("biSize", ctypes.c_ulong), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
                    ("biPlanes", ctypes.c_ushort), ("biBitCount", ctypes.c_ushort),
                    ("biCompression", ctypes.c_ulong), ("biSizeImage", ctypes.c_ulong),
                    ("biXPelsPerMeter", ctypes.c_long), ("biYPelsPerMeter", ctypes.c_long),
                    ("biClrUsed", ctypes.c_ulong), ("biClrImportant", ctypes.c_ulong)]

    class _BI(ctypes.Structure):
        _fields_ = [("bmiHeader", _BIH)]

    sdc = user32.GetDC(0)
    cdc = gdi32.CreateCompatibleDC(ctypes.c_void_p(sdc))
    bmp = gdi32.CreateCompatibleBitmap(ctypes.c_void_p(sdc), cw, ch)
    gdi32.SelectObject(ctypes.c_void_p(cdc), ctypes.c_void_p(bmp))
    try:
        ok = gdi32.BitBlt(ctypes.c_void_p(cdc), 0, 0, cw, ch, ctypes.c_void_p(sdc), cx, cy,
                          SRCCOPY | CAPTUREBLT)
        if not ok:
            raise OSError("BitBlt from desktop DC failed")
        bi = _BI()
        bi.bmiHeader.biSize = ctypes.sizeof(_BIH)
        bi.bmiHeader.biWidth = cw
        bi.bmiHeader.biHeight = -ch
        bi.bmiHeader.biPlanes = 1
        bi.bmiHeader.biBitCount = 32
        buf = ctypes.create_string_buffer(cw * ch * 4)
        gdi32.GetDIBits(ctypes.c_void_p(cdc), ctypes.c_void_p(bmp), 0, ch, buf, ctypes.byref(bi), 0)
        img = np.frombuffer(buf.raw, dtype=np.uint8).reshape(ch, cw, 4)[..., :3].copy()
    finally:
        gdi32.DeleteObject(ctypes.c_void_p(bmp))
        gdi32.DeleteDC(ctypes.c_void_p(cdc))
        user32.ReleaseDC(0, ctypes.c_void_p(sdc))
    return img


def frame_stats(img) -> dict:
    import numpy as np

    gray = img.max(axis=2)
    return {"mean": round(float(img.mean()), 2), "nonBlackPct": round(float((gray > 8).mean()) * 100, 1)}


_LAST = {"hash": None, "scene": 0, "gray": None}


def scene_switch(digest: dict) -> dict:
    """capture.scene_switch - detect a scene change by frame digest."""
    changed = _LAST["hash"] is not None and digest["hash"] != _LAST["hash"]
    if changed:
        _LAST["scene"] += 1
    _LAST["hash"] = digest["hash"]
    return {"changed": changed, "sceneId": _LAST["scene"], "previous": None if not changed else "digest-mismatch"}


def liveness(img) -> float | None:
    """Mean abs diff of this frame vs the previous one (downscaled gray).

    ~0.00 while a static UI is up is fine; exactly 0.000 for minutes on a
    hardware-accelerated title means the surface is stale, not the scene static.
    """
    import numpy as np

    g = img[::8, ::8].max(axis=2).astype(np.float32)
    prev = _LAST.get("gray")
    _LAST["gray"] = g
    if prev is None or prev.shape != g.shape:
        return None
    return round(float(np.abs(g - prev).mean()), 3)


def save_png(img, path: str) -> str:
    import cv2

    os.makedirs(os.path.dirname(path), exist_ok=True)
    cv2.imencode(".png", img)[1].tofile(path)  # tofile: non-ASCII path safe
    return path


# 2026-11-06 local run fix: each engine is a separate process, so the vision
# engine only ever saw its synthetic black frame while capture had live frames
# (measured in run real-run-2: capture mean 105.4 / vision allScores 0.0).
# capture publishes the newest frame atomically here; vision picks it up when
# its mtime is fresh (see vision engine live_frame()).
LIVE_DIR = os.path.join(SUITE, ".live")


def publish_live(img, meta: dict) -> dict:
    """Atomically publish the newest real frame for the other engines."""
    try:
        import cv2

        os.makedirs(LIVE_DIR, exist_ok=True)
        tmp = os.path.join(LIVE_DIR, "frame.tmp.png")
        dst = os.path.join(LIVE_DIR, "frame.png")
        cv2.imencode(".png", img)[1].tofile(tmp)
        os.replace(tmp, dst)
        meta_path = os.path.join(LIVE_DIR, "frame.json")
        meta_tmp = meta_path + ".tmp"
        with open(meta_tmp, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False)
        os.replace(meta_tmp, meta_path)
        return {"published": True, "path": dst}
    except Exception as exc:  # noqa: BLE001
        return {"published": False, "error": f"{type(exc).__name__}: {exc}"}


def foreground(hwnd: int) -> dict:
    """capture.foreground - bring the game window to front (no injection involved).

    Windows refuses SetForegroundWindow for background processes, so this escalates:
    AttachThreadInput -> an ALT tap (resets the foreground lock) -> SwitchToThisWindow.
    """
    if not hwnd:
        return {"status": "unavailable", "reason": "no window handle (mock backend)"}
    try:
        import ctypes

        user32 = ctypes.windll.user32
        k32 = ctypes.windll.kernel32
        if int(user32.GetForegroundWindow()) == hwnd:
            return {"status": "ok", "hwnd": hwnd, "active": hwnd, "already": True}
        attempts = []
        this_tid = k32.GetCurrentThreadId()
        for step in ("attach", "alt-tap", "switch"):
            fg = int(user32.GetForegroundWindow())
            if fg == hwnd:
                break
            if step == "attach":
                fg_tid = int(user32.GetWindowThreadProcessId(fg, None)) if fg else 0
                tgt_tid = int(user32.GetWindowThreadProcessId(hwnd, None))
                attached = []
                for tid in (fg_tid, tgt_tid):
                    if tid and tid != this_tid and tid not in attached:
                        if user32.AttachThreadInput(this_tid, tid, True):
                            attached.append(tid)
                try:
                    user32.BringWindowToTop(hwnd)
                    user32.SetForegroundWindow(hwnd)
                    user32.SetFocus(hwnd)
                finally:
                    for tid in attached:
                        user32.AttachThreadInput(this_tid, tid, False)
            elif step == "alt-tap":
                # A synthetic ALT press is the documented way to drop the foreground
                # lock that makes SetForegroundWindow a silent no-op.
                VK_MENU = 0x12
                user32.keybd_event(VK_MENU, 0, 0, 0)
                user32.keybd_event(VK_MENU, 0, 2, 0)
                user32.SetForegroundWindow(hwnd)
            else:
                try:
                    user32.SwitchToThisWindow(hwnd, True)
                except Exception:  # noqa: BLE001
                    user32.SetForegroundWindow(hwnd)
            time.sleep(0.12)
            now = int(user32.GetForegroundWindow())
            attempts.append({"step": step, "foreground": now, "ok": now == hwnd})
            if now == hwnd:
                break
        active = int(user32.GetForegroundWindow())
        return {"status": "ok" if active == hwnd else "best-effort", "hwnd": hwnd,
                "active": active, "attempts": attempts}
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}

def client_rect(hwnd: int):
    """Return (left, top, right, bottom) of the window client area in screen pixels."""
    import ctypes

    user32 = ctypes.windll.user32
    rect = ctypes.create_string_buffer(16)
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    left, top, right, bottom = ctypes.cast(rect, ctypes.POINTER(ctypes.c_long * 4)).contents
    pt = ctypes.create_string_buffer(8)
    ctypes.memmove(pt, ctypes.byref(ctypes.c_long(left)), 4)
    ctypes.memmove(ctypes.byref(pt, 4), ctypes.byref(ctypes.c_long(top)), 4)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    sx, sy = ctypes.cast(pt, ctypes.POINTER(ctypes.c_long * 2)).contents
    return (int(sx), int(sy), int(sx) + int(right - left), int(sy) + int(bottom - top))


def occlusion(hwnd: int) -> dict:
    """capture.occlusion - is something else painted on top of the game client area?

    The desktop-DC backend copies whatever is on screen inside the client rect, so a
    covered window silently yields a screenshot of the covering app instead. Sample a
    few points and walk the window tree: only our hwnd or its descendants are "ours".
    """
    if not hwnd:
        return {"status": "unavailable", "reason": "no window handle"}
    import ctypes
    import ctypes.wintypes

    user32 = ctypes.windll.user32
    try:
        left, top, right, bottom = client_rect(hwnd)
        width, height = right - left, bottom - top
        points = [
            (left + width // 2, top + height // 2),
            (left + width // 4, top + height // 4),
            (left + 3 * width // 4, top + height // 4),
            (left + width // 4, top + 3 * height // 4),
            (left + 3 * width // 4, top + 3 * height // 4),
        ]
        covered = 0
        by = []
        for x, y in points:
            target = int(user32.WindowFromPoint(ctypes.wintypes.POINT(x, y)))
            root = int(user32.GetAncestor(target, 2)) if target else 0  # GA_ROOT=2
            mine = target == hwnd or root == hwnd or (target and int(user32.GetParent(target)) == hwnd)
            if mine:
                continue
            covered += 1
            title = ""
            if target:
                buf = ctypes.create_unicode_buffer(256)
                user32.GetWindowTextW(target, buf, 256)
                title = buf.value
            by.append({"hwnd": target, "title": title, "at": [x, y]})
        return {"status": "ok", "rect": [left, top, right, bottom], "samples": len(points),
                "covered": covered, "occluded": covered > 0, "by": by[:3]}
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}


def capture_once(cfg, action, save_path=None):
    from core.capture import capture_window_bgr

    active = cfg["minimap"]["active_profile"]
    profiles = {name: tuple(dim) for name, dim in cfg["minimap"]["profiles"].items()}
    minimap = profiles[active]
    frame_cfg = cfg.get("frame", {})
    width = int(frame_cfg.get("width", 1920))
    height = int(frame_cfg.get("height", 1080))

    window_cfg = cfg.get("window", {})
    backend_pref = str(window_cfg.get("backend", "auto"))
    min_client = tuple(window_cfg.get("min_client", list(MIN_CLIENT)))
    info = {"hwnd": 0, "title": "", "client": [0, 0], "rejected": []}
    hwnd = 0
    if window_cfg.get("enable_real_capture", False):
        info = find_window(window_cfg.get("title_keyword", ""), min_client)
        hwnd = info["hwnd"]

    # The screen backend copies whatever the desktop paints inside the client rect, so
    # a window sitting on top of the game would silently become the "game frame".
    # Check first, raise the game when needed, then check again.
    occ = {"status": "skipped", "reason": "mock capture"}
    raised = []
    if hwnd and backend_pref in ("auto", "screen", "window"):
        occ = occlusion(hwnd)
        for _ in range(3):
            if not occ.get("occluded"):
                break
            raised.append(foreground(hwnd))
            time.sleep(0.18)
            occ = occlusion(hwnd)

    attempts = []
    frame = None
    backend = "mock"
    if hwnd:
        order = ["printwindow", "screen"] if backend_pref == "auto" else [backend_pref]
        if backend_pref not in ("auto", "printwindow", "screen"):
            order = ["screen"]
        for name in order:
            try:
                if name == "printwindow":
                    cand = capture_window_bgr(hwnd)
                else:
                    cand = grab_screen_client(hwnd)
                if cand is None or cand.size == 0:
                    raise ValueError("empty frame")
                st = frame_stats(cand)
                attempts.append({"backend": name, "ok": True, **st})
                # auto: a window-DC frame that is almost entirely black is the
                # known D3D failure signature -> try the next backend instead
                if backend_pref == "auto" and name == "printwindow" and st["nonBlackPct"] < 5.0:
                    attempts[-1]["rejected"] = "blank window-DC surface"
                    continue
                frame, backend = cand, name
                break
            except Exception as exc:  # noqa: BLE001
                attempts.append({"backend": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
    if frame is None:
        import numpy as np

        frame = np.zeros((height, width, 3), dtype="uint8")
        backend = "mock"

    digest = frame_digest(frame)
    saved = None
    if save_path:
        saved = save_png(frame, save_path)
    live = {"published": False, "reason": "mock frame (no real window)"}
    if backend != "mock":
        if occ.get("occluded"):
            live = {"published": False,
                    "reason": "window is covered; refusing to publish a screenshot of the covering window",
                    "by": occ.get("by")}
        else:
            live = publish_live(frame, {
                "ts": round(time.time(), 3), "hwnd": hwnd, "backend": backend,
                "hash": digest.get("hash"), "status": "live",
                "rect": (occ.get("rect") or [0, 0, width, height]),
            })
    result = {
        "action": action,
        "backend": backend,
        "backendAttempts": attempts,
        "occlusion": occ,
        "raisedForeground": raised,
        "live": live,
        "hwnd": hwnd,
        "window": {"title": info.get("title", ""), "client": info.get("client", [0, 0]),
                   "rejected": info.get("rejected", [])},
        "frame": {**digest, **frame_stats(frame), "liveDiff": liveness(frame)},
        "configuredFrame": {"width": width, "height": height},
        "minimapProfile": {"name": active, "size": list(minimap)},
        "minimapProfiles": {k: list(v) for k, v in profiles.items()},
        "sceneSwitch": scene_switch(digest),
        "foreground": foreground(hwnd),
        "savedFrame": saved,
        "components": COMPONENTS,
    }
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--log", default="")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--action", default="capture")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--save-frame", default="")
    args = ap.parse_args()

    cfg = load_toml(args.config)
    emit(args.log, "ready", run_id=args.run_id, config=args.config, python=sys.version.split()[0],
         components=COMPONENTS)
    if not args.once:
        try:
            while True:
                emit(args.log, "result", result=capture_once(cfg, args.action, args.save_frame or None))
                time.sleep(max(0.1, args.interval))
        except KeyboardInterrupt:
            return 0

    try:
        emit(args.log, "result", result=capture_once(cfg, args.action, args.save_frame or None))
    except Exception as exc:  # noqa: BLE001
        emit(args.log, "error", error=f"{type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
