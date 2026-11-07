from __future__ import annotations

from typing import Any, Dict

from .adapters import detector, ocr, vision
from .adapters.window import ensure_foreground
from .config import TEMPLATE_DIR
from .engine_common import load_cli_settings, load_frame, save_image

ACTIONS = ("capture", "classify", "match", "observe", "templates", "sprites", "ocr", "foreground")


def dispatch(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    settings = load_cli_settings(params.get("settings") if isinstance(params.get("settings"), str) else None)
    if action == "foreground":
        target = settings.get("target", {})
        return ensure_foreground(
            str(params.get("title") or target.get("window_title") or ""),
            int(params.get("hwnd") or 0),
        )
    if action == "templates":
        names = sorted(path.name for path in TEMPLATE_DIR.glob("*.png"))
        return {"templates": names, "count": len(names), "dir": str(TEMPLATE_DIR)}

    frame = load_frame(params, settings)
    if action == "sprites":
        options = dict(settings.get("vision", {}))
        if params.get("model"):
            options["model"] = str(params.get("model"))
        return detector.detect_sprites(
            frame.image,
            options,
            roi=params.get("roi"),
            threshold=float(params.get("threshold") or settings["vision"].get("threshold", 0.35)),
            max_items=int(params.get("maxItems") or 12),
        )
    if action == "ocr":
        return ocr.read_text(
            frame.image,
            roi=params.get("roi"),
            engine=str(params.get("engine") or "auto"),
            min_confidence=float(params.get("minConfidence") or 0.45),
        )
    if action == "capture":
        path = save_image(frame.image, str(params.get("name") or "sense-capture.jpg"))
        return {"frame": frame.summary(), "image": path}

    if action == "classify":
        threshold = float(params.get("threshold") or settings["vision"].get("threshold", 0.5))
        scene = vision.classify_scene(
            frame,
            threshold=threshold,
            use_edges=bool(settings["vision"].get("use_edges", True)),
        )
        return {
            "scene": scene["kind"],
            "scores": scene["scores"],
            "details": list(scene["details"].values()),
            "frame": frame.summary(),
        }

    if action == "match":
        template = str(params.get("template") or params.get("name") or "")
        if not template:
            raise ValueError("match 需要 params.template")
        match = vision.match_template(
            frame,
            template,
            threshold=float(params.get("threshold") or settings["vision"].get("threshold", 0.5)),
            roi=params.get("roi") or "full",
            use_edges=bool(params.get("use_edges", settings["vision"].get("use_edges", True))),
            scale=float(params.get("scale") or 1.0),
        )
        return {"match": match, "frame": frame.summary()}

    if action == "observe":
        threshold = float(params.get("threshold") or settings["vision"].get("threshold", 0.5))
        scene = vision.classify_scene(frame, threshold=threshold)
        templates = params.get("templates") or ["elf_P.png", "exchange.png", "qiudaidai.png"]
        matches = [
            vision.match_template(frame, str(name), threshold=threshold, roi="center")
            for name in templates[:8]
        ]
        path = save_image(frame.image, str(params.get("name") or "sense-observe.jpg"))
        return {
            "scene": scene["kind"],
            "scores": scene["scores"],
            "matches": matches,
            "image": path,
            "frame": frame.summary(),
        }

    raise ValueError(f"未知感知动作: {action}")
