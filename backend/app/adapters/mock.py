from __future__ import annotations

import math
import random
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..config import DATA_DIR, TEMPLATE_DIR
from .frame import Frame

WIDTH = 2560
HEIGHT = 1600

SCENE_SCRIPT = [
    ("field_pet", 4),
    ("battle_normal", 4),
    ("field", 8),
    ("battle_polluted", 4),
    ("field_pet", 3),
    ("party_confirm", 2),
    ("map", 2),
]

# Windows first: the mock frames are rendered on the player's machine, and
# ``ImageFont.load_default()`` falls back to a ~11px bitmap font that makes the
# HUD text unreadable for both humans and the built-in OCR templates.
_FONT_REGULAR = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhl.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

_FONT_BOLD = [
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
]


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path in (_FONT_BOLD + _FONT_REGULAR) if bold else _FONT_REGULAR:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:  # noqa: BLE001
                continue
    return ImageFont.load_default()


def _vertical_gradient(size, top: tuple, bottom: tuple) -> Image.Image:
    width, height = size
    base = Image.new("RGB", (1, height))
    for y in range(height):
        t = y / max(height - 1, 1)
        color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        base.putpixel((0, y), color)
    return base.resize((width, height), Image.BILINEAR)


def _paste_template(canvas: Image.Image, name: str, x: int, y: int, scale: float = 1.0) -> None:
    path = TEMPLATE_DIR / name
    if not path.exists():
        return
    icon = Image.open(path).convert("RGBA")
    if scale != 1.0:
        icon = icon.resize((int(icon.width * scale), int(icon.height * scale)), Image.LANCZOS)
    canvas.alpha_composite(icon, (int(x - icon.width / 2), int(y - icon.height / 2)))


def _draw_round_rect(draw: ImageDraw.ImageDraw, xy, radius: int, fill, outline=None, width: int = 1) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


class MockGameTarget:
    """Deterministic synthetic game window used for headless demos and tests."""

    def __init__(self, settings: Dict[str, Any]) -> None:
        self.settings = settings
        self._lock = threading.RLock()
        self._random = random.Random(20261103)
        self._script_index = 0
        self._script_tick = 0
        self._forced_scene: Optional[str] = None
        self._tick = 0
        self._input_log: list[Dict[str, Any]] = []
        self._position = [3072.0, 2944.0]
        self._base_map: Optional[Image.Image] = None

    # ------------------------------------------------------------------ state
    def set_scene(self, scene: str | None) -> None:
        with self._lock:
            self._forced_scene = None if scene in (None, "", "auto") else scene
            self._script_index = 0
            self._script_tick = 0

    def info(self) -> Dict[str, Any]:
        return {
            "kind": "mock",
            "title": "洛克王国：世界（模拟窗口）",
            "width": WIDTH,
            "height": HEIGHT,
            "scene": self._current_scene(),
        }

    def _current_scene(self) -> str:
        if self._forced_scene:
            return self._forced_scene
        return SCENE_SCRIPT[self._script_index % len(SCENE_SCRIPT)][0]

    def _advance(self) -> str:
        scene = self._current_scene()
        if self._forced_scene:
            self._tick += 1
            return scene
        self._script_tick += 1
        if self._script_tick >= SCENE_SCRIPT[self._script_index % len(SCENE_SCRIPT)][1]:
            self._script_tick = 0
            self._script_index += 1
        self._tick += 1
        return scene

    # ------------------------------------------------------------------ capture
    def capture(self) -> Frame:
        with self._lock:
            scene = self._advance()
            self._position[0] += math.sin(self._tick / 6.0) * 6.0
            self._position[1] += math.cos(self._tick / 7.0) * 5.0
            image = self._render(scene)
            meta = {
                "scene": scene,
                "tick": self._tick,
                "source": "mock",
                "width": WIDTH,
                "height": HEIGHT,
                "position": {"x": round(self._position[0], 1), "y": round(self._position[1], 1)},
            }
            return Frame(image=image, meta=meta)

    def _render(self, scene: str) -> np.ndarray:
        if scene in ("battle_normal", "battle_polluted"):
            canvas = self._render_battle(scene)
        elif scene == "party_confirm":
            canvas = self._render_field(pet=True)
            self._draw_confirm(canvas)
        elif scene == "map":
            canvas = self._render_field(pet=False)
            self._draw_map_overlay(canvas)
        elif scene == "field_pet":
            canvas = self._render_field(pet=True)
        elif scene == "field":
            # 空视野：没有可捕捉精灵，也没有交换提示 —— 实时任务会走「视角搜索」分支
            canvas = self._render_field(pet=False)
        else:
            canvas = self._render_field(pet=True)
        self._draw_hud(canvas, scene)
        return np.array(canvas.convert("RGB"))[:, :, ::-1].copy()

    def _render_field(self, pet: bool = True) -> Image.Image:
        canvas = _vertical_gradient((WIDTH, HEIGHT), (124, 195, 232), (198, 230, 173)).convert("RGBA")
        draw = ImageDraw.Draw(canvas, "RGBA")

        draw.ellipse((-600, 980, 1300, 2200), fill=(96, 163, 91, 255))
        draw.ellipse((900, 1060, 3300, 2350), fill=(86, 152, 83, 255))
        draw.polygon([(0, 1180), (700, 1010), (1450, 1240), (2100, 1080), (2560, 1210), (2560, 1600), (0, 1600)],
                     fill=(100, 172, 92, 255))
        draw.polygon([(0, 1320), (800, 1210), (1700, 1410), (2560, 1290), (2560, 1600), (0, 1600)],
                     fill=(78, 146, 82, 255))
        draw.ellipse((1500, 300, 2300, 780), fill=(104, 160, 214, 160))
        draw.ellipse((1620, 360, 2180, 720), fill=(133, 190, 231, 190))

        for cx, cy, r in [(330, 1230, 74), (520, 1180, 58), (1080, 1300, 62), (2010, 1380, 70), (2440, 1240, 54)]:
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(45, 103, 58, 230))
            draw.ellipse((cx - r + 14, cy - r + 14, cx - r * 0.4, cy - r + 40), fill=(68, 134, 70, 230))
            draw.rectangle((cx - 8, cy + r - 8, cx + 8, cy + r + 34), fill=(84, 65, 48, 255))

        draw.line([(0, 1440), (900, 1310), (1800, 1430), (2560, 1340)], fill=(204, 185, 128, 200), width=46)
        draw.line([(1180, 1180), (1260, 1450), (1410, 1600)], fill=(207, 189, 131, 170), width=24)

        # catchable pet + exchange prompt
        if pet:
            self._draw_pet_scene(canvas, draw)
        return canvas

    def _draw_pet_scene(self, canvas: Image.Image, draw: ImageDraw.ImageDraw) -> None:
        cx, cy = 1180, 1030
        draw.ellipse((cx - 120, cy + 60, cx + 120, cy + 140), fill=(40, 80, 40, 70))
        for radius, alpha in [(120, 40), (92, 60), (66, 80)]:
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=(255, 236, 150, alpha), width=6)
        _paste_template(canvas, "elf_P.png", cx, cy, 1.0)
        _paste_template(canvas, "exchange.png", 2300, 1320, 1.0)
        draw.text((2120, 1400), "交易请求", font=_font(34), fill=(255, 255, 255, 230))

    def _render_battle(self, scene: str) -> Image.Image:
        polluted = scene == "battle_polluted"
        top = (28, 20, 46) if polluted else (24, 44, 74)
        bottom = (66, 30, 58) if polluted else (38, 76, 106)
        canvas = _vertical_gradient((WIDTH, HEIGHT), top, bottom).convert("RGBA")
        draw = ImageDraw.Draw(canvas, "RGBA")

        draw.ellipse((-300, 900, 2860, 2200), fill=(43, 54, 78, 255) if not polluted else (54, 38, 64, 255))
        draw.ellipse((120, 980, 2440, 1900), fill=(52, 66, 92, 255) if not polluted else (66, 45, 76, 255))
        for i in range(4):
            draw.ellipse((300 + i * 90, 1060 + i * 90, 2260 - i * 90, 1820 - i * 90),
                         outline=(120, 140, 180, 60) if not polluted else (160, 110, 170, 60), width=3)
        if polluted:
            for _ in range(90):
                x = self._random.randint(0, WIDTH)
                y = self._random.randint(150, 1250)
                r = self._random.randint(20, 90)
                draw.ellipse((x, y, x + r, y + r), fill=(123, 74, 160, 22))

        # arena combatants
        draw.ellipse((760, 870, 1180, 1290), fill=(214, 216, 232, 255))
        draw.ellipse((820, 930, 1120, 1230), fill=(132, 156, 204, 255))
        draw.ellipse((780, 900, 860, 980), fill=(96, 120, 170, 255))
        draw.ellipse((1080, 900, 1160, 980), fill=(96, 120, 170, 255))
        draw.ellipse((1700, 760, 2240, 1260), fill=(190, 128, 160, 255) if not polluted else (128, 84, 156, 255))
        draw.ellipse((1770, 830, 2170, 1190), fill=(236, 164, 188, 255) if not polluted else (176, 112, 214, 255))

        # enemy panel
        _draw_round_rect(draw, (120, 120, 980, 330), 26, (10, 16, 30, 190))
        draw.text((160, 150), "野生精灵", font=_font(44, True), fill=(245, 248, 255))
        draw.text((160, 214), "污染体" if polluted else "普通体", font=_font(32),
                  fill=(220, 170, 255) if polluted else (170, 220, 200))
        _draw_round_rect(draw, (160, 276, 940, 306), 14, (58, 64, 88, 255))
        _draw_round_rect(draw, (160, 276, 160 + int(780 * (0.62 if polluted else 0.86)), 306), 14,
                         (196, 88, 220, 255) if polluted else (104, 214, 160, 255))

        # battle templates
        _paste_template(canvas, "pollute_capture.png" if polluted else "capture.png", 1750, 360, 1.0)
        _paste_template(canvas, "skill1.png", 2160, 1370, 1.0)
        _paste_template(canvas, "yes.png", 1540, 800, 1.0)

        draw.text((120, 1420), "回合 3", font=_font(34), fill=(230, 238, 252, 220))
        draw.text((2200, 1220), "污染战斗" if polluted else "普通战斗", font=_font(38, True),
                  fill=(226, 178, 255) if polluted else (176, 232, 214))
        return canvas

    def _draw_confirm(self, canvas: Image.Image) -> None:
        layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer, "RGBA")
        _draw_round_rect(draw, (820, 620, 1740, 1060), 32, (16, 22, 38, 230), outline=(94, 234, 212, 200), width=3)
        draw.text((980, 670), "同行请求", font=_font(54, True), fill=(255, 255, 255))
        draw.text((960, 780), "按 F 确认重新同行", font=_font(38), fill=(190, 235, 228))
        _paste_template(layer, "qiudaidai.png", 1240, 950, 1.0)
        _paste_template(layer, "yes.png", 1480, 1000, 1.0)
        canvas.alpha_composite(layer)

    def _draw_map_overlay(self, canvas: Image.Image) -> None:
        layer = Image.new("RGBA", canvas.size, (8, 14, 22, 190))
        canvas.alpha_composite(layer)

    def _draw_hud(self, canvas: Image.Image, scene: str) -> None:
        draw = ImageDraw.Draw(canvas, "RGBA")
        _draw_round_rect(draw, (48, 44, 760, 150), 20, (10, 16, 28, 176), outline=(94, 234, 212, 90))
        draw.text((86, 66), "洛克王国：世界", font=_font(44, True), fill=(248, 252, 255))
        draw.text((88, 116), f"自动演示 · {scene}", font=_font(28), fill=(146, 226, 210))
        self._draw_minimap(canvas)
        # bottom-left hotkeys
        _draw_round_rect(draw, (48, 1460, 620, 1560), 18, (10, 16, 28, 170))
        draw.text((80, 1480), "F8 暂停   F12 分层   Esc 退出", font=_font(28), fill=(186, 202, 220))
        # party slots
        for i in range(6):
            x = 1760 + i * 120
            _draw_round_rect(draw, (x, 1490, x + 96, 1570), 16, (12, 20, 34, 200), outline=(120, 226, 205, 70))
            draw.ellipse((x + 14, 1502, x + 54, 1542), fill=(64, 190, 170, 200))
            draw.text((x + 20, 1548), str(i + 1), font=_font(20), fill=(210, 240, 235))
        draw.text((48, 1580), f"模拟窗口 {WIDTH}x{HEIGHT} · 帧 {self._tick}", font=_font(22), fill=(130, 148, 168))

    def _draw_minimap(self, canvas: Image.Image) -> None:
        if self._base_map is None:
            path = DATA_DIR / "map" / "base_map.jpg"
            if path.exists():
                self._base_map = Image.open(path).convert("RGB")
        size = 300
        mx, my = 2150, 44
        if self._base_map:
            map_w, map_h = self._base_map.size
            sx = self._position[0] * map_w / 6144
            sy = self._position[1] * map_h / 5888
            half = 80
            box = (int(sx - half), int(sy - half), int(sx + half), int(sy + half))
            box = (max(0, box[0]), max(0, box[1]), min(map_w, box[2]), min(map_h, box[3]))
            crop = self._base_map.crop(box).resize((size, size), Image.LANCZOS)
        else:
            crop = Image.new("RGB", (size, size), (30, 60, 50))
        mask = Image.new("L", (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, size - 1, size - 1), fill=255)
        canvas.paste(crop, (mx, my), mask)
        draw = ImageDraw.Draw(canvas, "RGBA")
        draw.ellipse((mx, my, mx + size, my + size), outline=(108, 240, 214, 200), width=4)
        draw.ellipse((mx + 138, my + 138, mx + 162, my + 162), fill=(255, 224, 130, 240), outline=(20, 30, 40, 220))
        draw.polygon([(mx + 150, my + 118), (mx + 136, my + 146), (mx + 164, my + 146)], fill=(255, 238, 170, 240))
        draw.text((mx + 60, my + 260), "罗盘定位 · SIFT", font=_font(20), fill=(174, 232, 222))


class WindowsGameTarget:
    """Experimental GDI window capture + SendInput controller for Windows."""

    def __init__(self, settings: Dict[str, Any]) -> None:
        import os

        if os.name != "nt":
            raise RuntimeError("WindowsGameTarget 仅支持 Windows")
        self.settings = settings
        self.title_keyword = settings.get("window_title", "洛克王国：世界")
        self.force_foreground = bool(settings.get("force_foreground", False))
        self.hwnd = self._find_window(self.title_keyword)
        if not self.hwnd:
            raise RuntimeError(f"未找到窗口: {self.title_keyword}")

    @staticmethod
    def _find_window(keyword: str) -> int:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        found = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        def callback(hwnd, _lparam):
            length = user32.GetWindowTextLengthW(hwnd)
            if length:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                if keyword in buf.value:
                    found.append(hwnd)
            return True

        user32.EnumWindows(callback, 0)
        return found[0] if found else 0

    def info(self) -> Dict[str, Any]:
        return {"kind": "windows", "title": self.title_keyword, "hwnd": self.hwnd}

    def client_to_screen(self, x: int, y: int) -> tuple[int, int]:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        point = wintypes.POINT(int(x), int(y))
        user32.ClientToScreen(self.hwnd, ctypes.byref(point))
        return int(point.x), int(point.y)

    def capture(self) -> Frame:
        import ctypes
        from ctypes import wintypes

        import cv2

        if self.force_foreground:
            from .window import ensure_foreground

            ensure_foreground(title=self.title_keyword, hwnd=self.hwnd)
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        rect = wintypes.RECT()
        user32.GetClientRect(self.hwnd, ctypes.byref(rect))
        width, height = rect.right - rect.left, rect.bottom - rect.top
        hwnd_dc = user32.GetDC(self.hwnd)
        mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
        bmp = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
        gdi32.SelectObject(mem_dc, bmp)
        gdi32.BitBlt(mem_dc, 0, 0, width, height, hwnd_dc, 0, 0, 0x00CC0020)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD),
                ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD),
            ]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = width
        bmi.biHeight = -height
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        buffer = (ctypes.c_ubyte * (width * height * 4))()
        gdi32.GetDIBits(mem_dc, bmp, 0, height, buffer, ctypes.byref(bmi), 0)
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(self.hwnd, hwnd_dc)
        image = np.frombuffer(buffer, dtype=np.uint8).reshape(height, width, 4)
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        return Frame(image=image, meta={"scene": "window", "source": "windows", "hwnd": self.hwnd})
