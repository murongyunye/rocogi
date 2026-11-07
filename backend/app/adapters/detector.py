from __future__ import annotations

"""Lightweight sprite candidate detector.

The detector prefers an ONNX model when one is provided
(``ROCOGI_SPRITE_MODEL`` or ``data/models/sprite_detector.onnx``) and falls
back to a saliency/contour pass so the capability works without shipping any
third-party weights. The fallback is intentionally conservative: it looks
inside a configurable ROI and returns a small number of candidate boxes for
the realtime capture state machine to aim at.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from ..config import DATA_DIR

MODEL_ENV = "ROCOGI_SPRITE_MODEL"
DEFAULT_MODEL = DATA_DIR / "models" / "sprite_detector.onnx"
DEFAULT_ROI = [0.28, 0.34, 0.44, 0.46]


def _resolve_roi(image: np.ndarray, roi: Optional[Sequence[float]]) -> Tuple[np.ndarray, Tuple[int, int], Tuple[int, int]]:
    height, width = image.shape[:2]
    values = list(roi or DEFAULT_ROI)
    if len(values) != 4:
        values = DEFAULT_ROI
    x = max(0, min(int(float(values[0]) * width), width - 1))
    y = max(0, min(int(float(values[1]) * height), height - 1))
    w = max(1, min(int(float(values[2]) * width), width - x))
    h = max(1, min(int(float(values[3]) * height), height - y))
    return image[y : y + h, x : x + w], (x, y), (w, h)


def _nms(boxes: List[Tuple[int, int, int, int]], scores: List[float], threshold: float = 0.45) -> List[int]:
    if not boxes:
        return []
    return cv2.dnn.NMSBoxes(boxes, scores, 0.0, threshold).flatten().tolist()


class SpriteDetector:
    def __init__(self, settings: Optional[Dict[str, Any]] = None) -> None:
        self.settings = settings or {}
        configured = self.settings.get("model") or os.environ.get(MODEL_ENV)
        self.model_path = Path(configured).expanduser() if configured else DEFAULT_MODEL
        self._net = None
        self.load_error = ""
        if self.model_path.exists():
            try:
                self._net = cv2.dnn.readNetFromONNX(str(self.model_path))
            except Exception as exc:  # noqa: BLE001
                self.load_error = str(exc)

    @property
    def source(self) -> str:
        return "onnx" if self._net is not None else "saliency"

    def detect(
        self,
        image: np.ndarray,
        roi: Optional[Sequence[float]] = None,
        threshold: float = 0.35,
        max_items: int = 12,
    ) -> Dict[str, Any]:
        crop, offset, size = _resolve_roi(image, roi)
        if crop.size == 0:
            return {"count": 0, "sprites": [], "source": self.source, "roi": list(roi or DEFAULT_ROI)}
        items = self._detect_onnx(crop, threshold) if self._net is not None else []
        relative = True
        if not items:
            templates = self._detect_templates(image, roi, threshold)
            if templates:
                items = templates
                relative = False
        if not items:
            items = self._detect_saliency(crop, threshold)
        for item in items:
            if relative:
                item["x"] += offset[0]
                item["y"] += offset[1]
                item["cx"] += offset[0]
                item["cy"] += offset[1]
        items.sort(key=lambda item: item["score"], reverse=True)
        items = items[: max(1, int(max_items))]
        return {
            "count": len(items),
            "sprites": items,
            "source": self.source,
            "roi": [round(float(value), 4) for value in (roi or DEFAULT_ROI)],
            "model": str(self.model_path) if self._net is not None else None,
        }

    # ---------------------------------------------------------------- ONNX
    def _detect_onnx(self, crop: np.ndarray, threshold: float) -> List[Dict[str, Any]]:
        try:
            height, width = crop.shape[:2]
            blob = cv2.dnn.blobFromImage(crop, 1 / 255.0, (640, 640), swapRB=True, crop=False)
            self._net.setInput(blob)
            output = self._net.forward()
            rows = self._parse_yolo(output)
            boxes: List[Tuple[int, int, int, int]] = []
            scores: List[float] = []
            for cx, cy, bw, bh, score in rows:
                if score < threshold:
                    continue
                scale_x = width / 640.0
                scale_y = height / 640.0
                w = max(2, int(bw * scale_x))
                h = max(2, int(bh * scale_y))
                x = max(0, int(cx * scale_x - w / 2))
                y = max(0, int(cy * scale_y - h / 2))
                boxes.append((x, y, min(w, width - x), min(h, height - y)))
                scores.append(float(score))
            keep = _nms(boxes, scores)
            return [
                {
                    "x": boxes[index][0],
                    "y": boxes[index][1],
                    "w": boxes[index][2],
                    "h": boxes[index][3],
                    "cx": boxes[index][0] + boxes[index][2] // 2,
                    "cy": boxes[index][1] + boxes[index][3] // 2,
                    "score": round(scores[index], 3),
                    "label": "sprite",
                }
                for index in keep
            ]
        except Exception as exc:  # noqa: BLE001
            self.load_error = str(exc)
            return []

    @staticmethod
    def _parse_yolo(output: np.ndarray) -> List[Tuple[float, float, float, float, float]]:
        data = np.array(output)
        if data.ndim == 3:
            data = data[0]
        if data.ndim != 2:
            raise ValueError(f"不支持的 ONNX 输出维度: {data.shape}")
        if data.shape[0] < data.shape[1]:
            data = data.T
        if data.shape[1] < 5:
            raise ValueError(f"不支持的 ONNX 输出列数: {data.shape}")
        rows = []
        for row in data:
            cx, cy, bw, bh = (float(value) for value in row[:4])
            scores = row[4:]
            score = float(scores.max()) if scores.size else 0.0
            if scores.size > 1 and float(row[4]) > 1.0:
                score = float(row[4]) * score
            rows.append((cx, cy, bw, bh, score))
        return rows

    # ------------------------------------------------------------ templates
    @staticmethod
    def _detect_templates(image: np.ndarray, roi: Optional[Sequence[float]], threshold: float) -> List[Dict[str, Any]]:
        """Fallback for catchable pets when no generic model is available."""
        from . import vision
        from .frame import Frame

        match = vision.match_template(
            Frame(image=image),
            "elf_P.png",
            threshold=threshold,
            roi=list(roi or DEFAULT_ROI),
            use_edges=True,
        )
        if not match.get("matched"):
            return []
        return [
            {
                "x": int(match["x"]),
                "y": int(match["y"]),
                "w": int(match["w"]),
                "h": int(match["h"]),
                "cx": int(match["cx"]),
                "cy": int(match["cy"]),
                "score": round(float(match["score"]), 3),
                "label": "sprite",
            }
        ]

    # ------------------------------------------------------------ saliency
    def _detect_saliency(self, crop: np.ndarray, threshold: float) -> List[Dict[str, Any]]:
        height, width = crop.shape[:2]
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([0, 45, 110]), np.array([179, 255, 255]))
        mask = cv2.medianBlur(mask, 5)
        kernel = np.ones((7, 7), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        area_total = float(width * height)
        items = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < area_total * 0.0015 or area > area_total * 0.4:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            if w < width * 0.04 or h < height * 0.04:
                continue
            aspect = w / max(h, 1)
            if aspect < 0.25 or aspect > 4.0:
                continue
            perimeter = cv2.arcLength(contour, True)
            circularity = 4 * np.pi * area / max(perimeter * perimeter, 1)
            score = min(0.95, 0.35 + 0.25 * min(1.0, area / (area_total * 0.05)) + 0.2 * min(1.0, circularity))
            if score < threshold:
                continue
            items.append(
                {
                    "x": int(x),
                    "y": int(y),
                    "w": int(w),
                    "h": int(h),
                    "cx": int(x + w / 2),
                    "cy": int(y + h / 2),
                    "score": round(float(score), 3),
                    "label": "sprite",
                }
            )
        return items


def detect_sprites(
    image: np.ndarray,
    settings: Optional[Dict[str, Any]] = None,
    roi: Optional[Sequence[float]] = None,
    threshold: float = 0.35,
    max_items: int = 12,
) -> Dict[str, Any]:
    return SpriteDetector(settings).detect(image, roi=roi, threshold=threshold, max_items=max_items)
