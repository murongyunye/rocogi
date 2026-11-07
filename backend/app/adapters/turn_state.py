from __future__ import annotations

"""Structured battle turn-state reader.

Reads the visible battle HUD instead of guessing from scene labels alone:
enemy HP bar fill, turn counter (numeric OCR), skill availability and the
polluted/normal battle phase. All ROIs are normalized and can be overridden
through ``settings['battle']['rois']`` for real-game calibration.
"""

from typing import Any, Dict, List, Optional, Sequence

import cv2
import numpy as np

from .frame import Frame
from . import ocr, vision

DEFAULT_ROIS: Dict[str, List[float]] = {
    "enemy_panel": [0.0469, 0.0750, 0.3830, 0.2060],
    "enemy_hp": [0.0625, 0.1725, 0.3047, 0.0190],
    "turn": [0.0300, 0.8600, 0.2500, 0.0600],
    "skill_bar": [0.7800, 0.8200, 0.2000, 0.1600],
}


def _roi(frame: Frame, rois: Dict[str, List[float]], key: str) -> np.ndarray:
    values = rois.get(key, DEFAULT_ROIS[key])
    x1 = max(0, int(values[0] * frame.width))
    y1 = max(0, int(values[1] * frame.height))
    x2 = max(x1 + 1, min(frame.width, int((values[0] + values[2]) * frame.width)))
    y2 = max(y1 + 1, min(frame.height, int((values[1] + values[3]) * frame.height)))
    return frame.image[y1:y2, x1:x2]


def _bar_ratio(crop: np.ndarray) -> float:
    if crop.size == 0:
        return 0.0
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([0, 0, 140]), np.array([179, 255, 255]))
    column = (mask > 0).mean(axis=0)
    bright = np.where(column >= 0.35)[0]
    if bright.size == 0:
        return 0.0
    return round(float((bright[-1] + 1) / max(crop.shape[1], 1)), 3)


def _parse_int(text: str) -> Optional[int]:
    digits = "".join(char for char in text if char.isdigit())
    return int(digits) if digits else None


def read_turn_state(frame: Frame, settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    settings = settings or {}
    battle_settings = settings.get("battle", {})
    rois = {**DEFAULT_ROIS, **(battle_settings.get("rois") or {})}
    scene = str(frame.meta.get("scene") or "")
    if scene not in ("battle_normal", "battle_polluted"):
        classified = vision.classify_scene(frame, threshold=0.45, use_edges=True)
        scene = classified["kind"]
    polluted = "polluted" in scene
    if scene not in ("battle_normal", "battle_polluted"):
        return {
            "ok": True,
            "phase": "not_battle",
            "scene": scene,
            "polluted": polluted,
            "enemy": {"hpRatio": 0.0, "hpPercent": 0},
            "turn": None,
            "skills": [],
        }

    hp_ratio = _bar_ratio(_roi(frame, rois, "enemy_hp"))
    turn_ocr = ocr.read_text(frame.image, roi=rois["turn"], engine="auto")
    turn = _parse_int(turn_ocr.get("text", ""))
    name_ocr = ocr.read_text(frame.image, roi=rois["enemy_panel"], engine="tesseract")
    skill_match = vision.match_template(
        frame,
        "skill1.png",
        threshold=0.4,
        roi=rois["skill_bar"],
        use_edges=True,
    )
    skills: List[Dict[str, Any]] = [
        {
            "slot": 1,
            "name": "技能 1",
            "available": bool(skill_match.get("matched")),
            "score": round(float(skill_match.get("score", 0.0)), 3),
            "cx": int(skill_match.get("cx", 0)),
            "cy": int(skill_match.get("cy", 0)),
        }
    ]
    return {
        "ok": True,
        "phase": "battle",
        "scene": scene,
        "polluted": polluted,
        "turn": turn,
        "enemy": {
            "hpRatio": hp_ratio,
            "hpPercent": int(round(hp_ratio * 100)),
            "name": name_ocr.get("text") or None,
        },
        "skills": skills,
        "ocr": {
            "turn": {"text": turn_ocr.get("text"), "confidence": turn_ocr.get("confidence"), "source": turn_ocr.get("source")},
        },
        "rois": rois,
    }
