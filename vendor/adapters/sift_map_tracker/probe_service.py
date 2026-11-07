"""sift-map-tracker service.exe 黑盒探测。

用途：确认 `sift-map-tracker/service/service.exe` 作为可选外部进程时：
  1) 能否启动、以什么参数启动；
  2) 握手协议（首条消息）是什么；
  3) 正常输出节奏、超时行为；
  4) 结束后是否残留进程。

不常驻：最多运行 --seconds 秒后强制终止，并校验无同名进程残留。
输出：JSON 报告到 stdout；用 --out 可落盘。

无游戏时可用 `--synthetic-minimap`：把 logic_map.png 裁成一张 255×235 的圆形
小地图显示在屏幕 (0,0)（即 region 区域），从而验证 found=true 与路线识别链路。
该模式需要 Pillow + Tk，窗口在探测结束后立即关闭。
"""
import argparse
import ctypes
import json
import os
import subprocess
import sys
import threading
import time

DEFAULT_EXE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "sift-map-tracker", "sift-map-tracker", "service", "service.exe",
)


def _reader(proc, sink, done):
    try:
        for raw in iter(proc.stdout.readline, b""):
            line = raw.decode("utf-8", "replace").strip()
            if line:
                sink.append((time.time(), line))
    finally:
        done.set()


def probe(exe, seconds, send_line, window=None):
    started = time.time()
    proc = subprocess.Popen(
        [exe],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(exe),
    )
    sink, done = [], threading.Event()
    threading.Thread(target=_reader, args=(proc, sink, done), daemon=True).start()

    if send_line:
        try:
            proc.stdin.write(send_line.encode("utf-8") + b"\n")
            proc.stdin.flush()
        except Exception as exc:  # noqa: BLE001
            sink.append((time.time(), f"__stdin_error__:{exc}"))

    deadline = started + seconds
    while time.time() < deadline and not done.is_set():
        time.sleep(0.2)

    alive = proc.poll() is None
    if alive:
        # PyInstaller onefile 会派生子进程，必须杀进程树，否则会残留 service.exe
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        )
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    messages, types, first_payload = [], {}, None
    frames_total = found_true = minimap_visible = 0
    first_found_frame = None
    for ts, line in sink:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            obj = {"_raw": line[:200]}
        msg_type = obj.get("type") if isinstance(obj, dict) else None
        types[msg_type] = types.get(msg_type, 0) + 1
        if msg_type == "frame":
            frames_total += 1
            found_true += 1 if obj.get("found") else 0
            minimap_visible += 1 if obj.get("minimap_visible") else 0
            if first_found_frame is None and obj.get("found"):
                first_found_frame = {
                    key: obj.get(key) for key in
                    ("found", "minimap_visible", "center_x", "center_y", "route_name",
                     "waypoint_index", "waypoint_total", "next_label", "tracking_source")
                }
        messages.append({"t": round(ts - started, 3), "type": msg_type, "line": line[:500]})
        if first_payload is None and msg_type == "ready":
            first_payload = obj

    stderr_tail = ""
    if proc.stderr is not None:
        try:
            stderr_tail = proc.stderr.read().decode("utf-8", "replace")[-400:]
        except Exception:  # noqa: BLE001
            pass

    return {
        "exe": os.path.abspath(exe),
        "seconds": seconds,
        "exit_code": proc.returncode,
        "killed_after_timeout": alive,
        "stderr_tail": stderr_tail,
        "message_count": len(messages),
        "type_histogram": types,
        "frames": {
            "total": frames_total,
            "found_true": found_true,
            "minimap_visible": minimap_visible,
        },
        "first_found_frame": first_found_frame,
        "ready_payload": first_payload,
        "sample_messages": messages[:6],
    }


def show_synthetic_minimap(exe_dir, center_x, center_y, crop_size):
    """在屏幕 (0,0) 放一张 255×235 的圆形小地图（由 logic_map.png 裁出）。

    仅用于无游戏时的自检：验证 service.exe 的 found=true / 路线识别链路。
    返回 tkinter root，调用方负责在探测结束后 destroy。
    """
    from PIL import Image, ImageDraw, ImageTk  # 仅需要 Pillow + Tk
    import tkinter as tk

    map_path = os.path.join(os.path.dirname(exe_dir), "assets", "logic_map.png")
    if not os.path.isfile(map_path):
        map_path = os.path.join(exe_dir, "assets", "logic_map.png")
    crop = Image.open(map_path).crop(
        (center_x - crop_size // 2, center_y - crop_size // 2,
         center_x + crop_size // 2, center_y + crop_size // 2)
    )
    crop = crop.convert("RGB").resize((220, 220), Image.BICUBIC)
    mask = Image.new("L", (220, 220), 0)
    ImageDraw.Draw(mask).ellipse((2, 2, 217, 217), fill=255)
    canvas = Image.new("RGB", (255, 235), (12, 14, 18))
    canvas.paste(crop, (17, 7), mask)
    ImageDraw.Draw(canvas).ellipse((17, 7, 237, 227), outline=(220, 220, 220), width=2)

    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    root = tk.Tk()
    root.overrideredirect(True)
    root.geometry("255x235+0+0")
    root.attributes("-topmost", True)
    photo = ImageTk.PhotoImage(canvas)
    tk.Label(root, image=photo, borderwidth=0).pack()
    root.update()
    root._photo = photo
    return root


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=DEFAULT_EXE)
    ap.add_argument("--seconds", type=float, default=12.0)
    ap.add_argument("--send-line", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--synthetic-minimap", action="store_true",
                    help="在屏幕 (0,0) 显示 logic_map 裁出的圆形小地图，用于无游戏时验证 found=true")
    ap.add_argument("--crop-size", type=int, default=256, help="合成小地图取图边长（地图像素）")
    ap.add_argument("--crop-center", default="4096,4096", help="合成小地图中心，格式 x,y")
    args = ap.parse_args()

    if not os.path.isfile(args.exe):
        print(json.dumps({"error": "exe_not_found", "exe": args.exe}, ensure_ascii=False, indent=2))
        return 2

    window = None
    if args.synthetic_minimap:
        cx, cy = (int(v) for v in args.crop_center.split(","))
        window = show_synthetic_minimap(os.path.dirname(os.path.abspath(args.exe)), cx, cy, args.crop_size)

    try:
        report = probe(args.exe, args.seconds, args.send_line, window)
    finally:
        if window is not None:
            try:
                window.destroy()
            except Exception:  # noqa: BLE001
                pass
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
