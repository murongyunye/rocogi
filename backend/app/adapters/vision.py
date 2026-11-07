from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from ..config import TEMPLATE_DIR
from .frame import Frame

_TEMPLATE_CACHE: Dict[str, np.ndarray] = {}
_CACHE_LOCK = threading.Lock()

REFERENCE_WIDTH = 2560.0

REGIONS: Dict[str, List[float]] = {
    "full": [0.0, 0.0, 1.0, 1.0],
    "top-right": [0.55, 0.0, 0.45, 0.45],
    "bottom-right": [0.55, 0.55, 0.45, 0.45],
    "top": [0.3, 0.0, 0.4, 0.32],
    "center": [0.28, 0.28, 0.44, 0.44],
    "top-half": [0.0, 0.0, 1.0, 0.5],
}

SCENE_TEMPLATES = {
    "capture.png": "battle",
    "pollute_capture.png": "battle_polluted",
    "skill1.png": "battle_ui",
    "elf_P.png": "pet",
    "exchange.png": "exchange",
    "qiudaidai.png": "party_confirm",
    "yes.png": "dialog",
}


def load_template(name: str) -> Optional[np.ndarray]:
    name = Path(name).name
    with _CACHE_LOCK:
        if name in _TEMPLATE_CACHE:
            return _TEMPLATE_CACHE[name]
        path = TEMPLATE_DIR / name
        if not path.exists():
            return None
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            return None
        _TEMPLATE_CACHE[name] = image
        return image


def preprocess(image: np.ndarray, use_edges: bool = True) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    if use_edges:
        return cv2.Canny(gray, 90, 180)
    return cv2.GaussianBlur(gray, (3, 3), 0)


def resolve_roi(frame: Frame, roi: Any) -> Tuple[int, int, int, int]:
    if isinstance(roi, str) and roi in REGIONS:
        ratios = REGIONS[roi]
    elif isinstance(roi, (list, tuple)) and len(roi) == 4:
        ratios = [float(v) for v in roi]
    else:
        ratios = REGIONS["full"]
    # Accept either [l,t,w,h] ratios or pixel bounds when values exceed 1.
    if max(ratios) > 1.5:
        x1, y1, x2, y2 = [int(v) for v in ratios]
    else:
        x1 = int(ratios[0] * frame.width)
        y1 = int(ratios[1] * frame.height)
        x2 = int((ratios[0] + ratios[2]) * frame.width)
        y2 = int((ratios[1] + ratios[3]) * frame.height)
    x1 = max(0, min(frame.width - 1, x1))
    y1 = max(0, min(frame.height - 1, y1))
    x2 = max(x1 + 1, min(frame.width, x2))
    y2 = max(y1 + 1, min(frame.height, y2))
    return x1, y1, x2 - x1, y2 - y1


def match_template(
    frame: Frame,
    template_name: str,
    threshold: float = 0.5,
    roi: Any = "full",
    use_edges: bool = True,
    scale: float = 1.0,
) -> Dict[str, Any]:
    template = load_template(template_name)
    if template is None:
        return {"ok": False, "error": f"模板不存在: {template_name}", "score": 0.0, "matched": False}
    x, y, w, h = resolve_roi(frame, roi)
    crop = frame.image[y : y + h, x : x + w]
    if crop.size == 0:
        return {"ok": False, "error": "ROI 为空", "score": 0.0, "matched": False}

    frame_scale = frame.width / REFERENCE_WIDTH
    effective = max(0.15, frame_scale * (scale or 1.0))
    tpl = template
    if abs(effective - 1.0) > 0.01:
        tpl = cv2.resize(tpl, (max(8, int(tpl.shape[1] * effective)), max(8, int(tpl.shape[0] * effective))),
                         interpolation=cv2.INTER_AREA)
    if tpl.shape[0] > crop.shape[0] or tpl.shape[1] > crop.shape[1]:
        return {"ok": False, "error": "模板大于 ROI", "score": 0.0, "matched": False}

    haystack = preprocess(crop, use_edges)
    needle = preprocess(tpl, use_edges)
    result = cv2.matchTemplate(haystack, needle, cv2.TM_CCOEFF_NORMED)
    _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(result)
    score = float(max(0.0, min(1.0, max_val)))
    return {
        "ok": True,
        "template": template_name,
        "score": score,
        "matched": score >= float(threshold),
        "x": int(x + max_loc[0]),
        "y": int(y + max_loc[1]),
        "w": int(tpl.shape[1]),
        "h": int(tpl.shape[0]),
        "cx": int(x + max_loc[0] + tpl.shape[1] / 2),
        "cy": int(y + max_loc[1] + tpl.shape[0] / 2),
        "roi": [x, y, w, h],
    }


def annotate_matches(frame: Frame, matches: List[Dict[str, Any]]) -> np.ndarray:
    image = frame.image.copy()
    for item in matches:
        if not item.get("ok"):
            continue
        color = (94, 234, 212) if item.get("matched") else (120, 130, 150)
        x, y, w, h = item["x"], item["y"], item["w"], item["h"]
        cv2.rectangle(image, (x, y), (x + w, y + h), color, 3)
        label = f"{item.get('template', '')} {item.get('score', 0):.2f}"
        cv2.putText(image, label, (x, max(28, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (12, 18, 26), 3)
        cv2.putText(image, label, (x, max(28, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    return image


def classify_scene(frame: Frame, threshold: float = 0.5, use_edges: bool = True) -> Dict[str, Any]:
    scores: Dict[str, float] = {}
    details: Dict[str, Dict[str, Any]] = {}
    probes = [
        ("pollute_capture.png", "top-right"),
        ("capture.png", "top-right"),
        ("skill1.png", "bottom-right"),
        ("elf_P.png", "center"),
        ("exchange.png", "bottom-right"),
        ("qiudaidai.png", "center"),
    ]
    for name, roi in probes:
        match = match_template(frame, name, threshold=threshold, roi=roi, use_edges=use_edges)
        key = SCENE_TEMPLATES.get(name, name)
        scores[key] = match.get("score", 0.0)
        details[name] = match

    pollute = scores.get("battle_polluted", 0.0)
    battle = scores.get("battle", 0.0)
    skill = scores.get("battle_ui", 0.0)
    pet = max(scores.get("pet", 0.0), scores.get("exchange", 0.0) * 0.85)
    confirm = scores.get("party_confirm", 0.0)

    kind = "field"
    if pollute >= threshold and pollute >= battle:
        kind = "battle_polluted"
    elif battle >= threshold and (skill >= threshold * 0.6 or battle >= 0.62):
        kind = "battle_normal"
    elif confirm >= threshold:
        kind = "party_confirm"
    elif pet >= threshold:
        kind = "field_pet"

    return {"kind": kind, "scores": {k: round(v, 4) for k, v in scores.items()}, "details": details}
