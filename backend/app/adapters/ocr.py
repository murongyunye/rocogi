from __future__ import annotations

"""Constrained OCR for game HUD numbers.

The built-in backend is self-contained: it segments bright glyphs and matches
them against font-rendered digits (0-9, %, /, ., +, -). This covers HP,
energy, damage numbers and turn counters without shipping an OCR model. When
``pytesseract`` and the Tesseract binary are available, callers may request
``engine="tesseract"`` for general text (including Chinese, if the language
pack is installed).
"""

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

GLYPHS = "0123456789%/.-+"
_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/msyhbd.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]


def _font(size: int) -> ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:  # noqa: BLE001
                continue
    return ImageFont.load_default()


def _normalize(glyph: np.ndarray, size: int = 28) -> np.ndarray:
    height, width = glyph.shape[:2]
    if height == 0 or width == 0:
        return np.zeros((size, size), dtype=np.float32)
    scale = min(size / width, size / height)
    resized = cv2.resize(glyph, (max(1, int(width * scale)), max(1, int(height * scale))), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((size, size), dtype=np.uint8)
    y = (size - resized.shape[0]) // 2
    x = (size - resized.shape[1]) // 2
    canvas[y : y + resized.shape[0], x : x + resized.shape[1]] = resized
    return canvas.astype(np.float32) / 255.0


def _templates() -> Dict[str, np.ndarray]:
    templates: Dict[str, np.ndarray] = {}
    font = _font(64)
    for char in GLYPHS:
        image = Image.new("L", (96, 96), 0)
        draw = ImageDraw.Draw(image)
        bbox = draw.textbbox((0, 0), char, font=font)
        draw.text((-bbox[0] + 8, -bbox[1] + 8), char, font=font, fill=255)
        array = np.array(image)
        ys, xs = np.where(array > 0)
        if len(xs) == 0:
            continue
        glyph = array[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
        templates[char] = _normalize(glyph)
    return templates


_TEMPLATES: Optional[Dict[str, np.ndarray]] = None


def _get_templates() -> Dict[str, np.ndarray]:
    global _TEMPLATES
    if _TEMPLATES is None:
        _TEMPLATES = _templates()
    return _TEMPLATES


def _resolve_roi(image: np.ndarray, roi: Optional[Sequence[float]]) -> Sequence[float]:
    if roi and len(roi) == 4:
        return roi
    return [0, 0, 1, 1]


def _builtin(image: np.ndarray, roi: Optional[Sequence[float]], min_confidence: float) -> Dict[str, Any]:
    values = _resolve_roi(image, roi)
    height, width = image.shape[:2]
    x = max(0, min(int(values[0] * width), width - 1))
    y = max(0, min(int(values[1] * height), height - 1))
    w = max(1, min(int(values[2] * width), width - x))
    h = max(1, min(int(values[3] * height), height - y))
    crop = image[y : y + h, x : x + w]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    gray = cv2.resize(gray, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)
    _value, binary = cv2.threshold(gray, 175, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for contour in contours:
        bx, by, bw, bh = cv2.boundingRect(contour)
        if bh < 12 or bw < 4 or bw > bh * 1.8:
            continue
        boxes.append((bx, by, bw, bh))
    boxes.sort(key=lambda item: item[0])
    templates = _get_templates()
    chars: List[Dict[str, Any]] = []
    previous_right: Optional[int] = None
    text_parts: List[str] = []
    for bx, by, bw, bh in boxes:
        glyph = binary[by : by + bh, bx : bx + bw]
        normalized = _normalize(glyph)
        best_char = ""
        best_score = 0.0
        for char, template in templates.items():
            score = float(cv2.matchTemplate(normalized, template, cv2.TM_CCOEFF_NORMED)[0, 0])
            if score > best_score:
                best_score = score
                best_char = char
        if best_score < min_confidence:
            continue
        if previous_right is not None and bx - previous_right > bh * 0.55:
            text_parts.append(" ")
        text_parts.append(best_char)
        previous_right = bx + bw
        chars.append(
            {
                "char": best_char,
                "score": round(best_score, 3),
                "x": int(bx / 3 + x),
                "y": int(by / 3 + y),
                "w": int(bw / 3),
                "h": int(bh / 3),
            }
        )
    text = "".join(text_parts).strip()
    confidence = round(sum(item["score"] for item in chars) / len(chars), 3) if chars else 0.0
    return {"text": text, "confidence": confidence, "chars": chars, "source": "builtin", "roi": list(values)}


def _tesseract(image: np.ndarray, roi: Optional[Sequence[float]]) -> Optional[Dict[str, Any]]:
    if not shutil.which("tesseract"):
        return None
    try:
        import pytesseract  # type: ignore
    except Exception:  # noqa: BLE001
        return None
    values = _resolve_roi(image, roi)
    height, width = image.shape[:2]
    x = max(0, min(int(values[0] * width), width - 1))
    y = max(0, min(int(values[1] * height), height - 1))
    w = max(1, min(int(values[2] * width), width - x))
    h = max(1, min(int(values[3] * height), height - y))
    crop = image[y : y + h, x : x + w]
    rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB) if crop.ndim == 3 else crop
    text = pytesseract.image_to_string(rgb, config="--psm 7").strip()
    if not text:
        return None
    return {"text": text, "confidence": 1.0, "chars": [], "source": "tesseract", "roi": list(values)}


def read_text(
    image: np.ndarray,
    roi: Optional[Sequence[float]] = None,
    engine: str = "auto",
    min_confidence: float = 0.45,
) -> Dict[str, Any]:
    if engine in ("auto", "tesseract"):
        result = _tesseract(image, roi)
        if result:
            return result
        if engine == "tesseract":
            return {"text": "", "confidence": 0.0, "chars": [], "source": "unavailable", "roi": list(_resolve_roi(image, roi))}
    return _builtin(image, roi, min_confidence)
