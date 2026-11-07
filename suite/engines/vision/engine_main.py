"""vision engine - template / scene / ROI + sprite detection.

Integration sources (MERGE_MAP):
  template match / scene / ROI : Auto-rocokingdom core/vision.py
  sprite detector (ONNX)      : AutoCapture detector.py ONNXDetector + sprite_detector.onnx
Own venv / process, no imports from other suite engines.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

SUITE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.path.dirname(os.path.dirname(SUITE))
AUTO_ROOT = os.path.join(WORK, "rocogi", "vendor", "yorusacri-Auto-rocokingdom")
CAPTURE_ROOT = os.path.join(WORK, "rocogi", "vendor", "Tsuann-RocoKingdom-AutoCapture")
sys.path.insert(0, CAPTURE_ROOT)
sys.path.insert(0, AUTO_ROOT)

ENGINE = "vision"
ASSETS = os.path.join(SUITE, "assets")
ONNX_PATH = os.path.join(ASSETS, "models", "sprite_detector.onnx")
TEMPLATE_DIR = os.path.join(ASSETS, "templates")


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


def _vision():
    import config as ar_config
    import core.vision as v

    ar_config.CONFIG.template_dir = TEMPLATE_DIR
    if hasattr(v, "CONFIG"):
        v.CONFIG.template_dir = TEMPLATE_DIR
    return v


def synthetic_frame(cfg):
    import numpy as np

    h = cfg["frame"]["height"]
    w = cfg["frame"]["width"]
    return np.zeros((h, w, 3), dtype="uint8")


# 2026-11-06 local-hardware fix: every action used to analyse synthetic_frame(),
# i.e. a black 2560x1600 image — the engine could never look at the real game.
# `--frame <png>` (or vision.frame_file in toml) now supplies a real capture
# (written by the capture engine via --save-frame) and `--scale auto` matches
# the template reference resolution to the actual frame width.
_CTX = {"frame_path": "", "scale": "auto", "frame": None, "source": "", "live": {}}

# 2026-11-06 local-hardware fix #2: in supervised runs each engine is its own
# process, so vision never saw what capture grabbed (it analysed synthetic black
# frames while capture had live 1280x800 frames — measured in real-run-2).
# capture now publishes the newest real frame to <suite>/.live/frame.png and this
# engine consumes it when it is fresh; otherwise it falls back to --frame, then
# to the synthetic reference frame (keeps verify runs hermetic).
LIVE_DIR = os.path.join(SUITE, ".live")
LIVE_FRAME = os.path.join(LIVE_DIR, "frame.png")


def live_frame(cfg):
    """Newest frame published by the capture engine, if it is fresh enough."""
    limit = float(cfg.get("frame", {}).get("live_max_age_sec", 8.0))
    if not os.path.exists(LIVE_FRAME):
        return None, {"reason": "no live frame published"}
    age = time.time() - os.path.getmtime(LIVE_FRAME)
    if age > limit:
        return None, {"reason": f"stale live frame ({age:.1f}s > {limit:.0f}s)"}
    import cv2
    import numpy as np

    img = None
    try:
        with open(LIVE_FRAME, "rb") as fh:
            img = cv2.imdecode(np.frombuffer(fh.read(), dtype="uint8"), cv2.IMREAD_COLOR)
    except Exception as exc:  # noqa: BLE001
        return None, {"reason": f"unreadable live frame: {type(exc).__name__}: {exc}"}
    if img is None:
        return None, {"reason": "live frame decoded to None"}
    meta = {}
    try:
        with open(os.path.join(LIVE_DIR, "frame.json"), encoding="utf-8") as fh:
            meta = json.load(fh)
    except Exception:  # noqa: BLE001
        meta = {}
    return img, {"ageSec": round(age, 2), **meta}


def current_frame(cfg):
    """Real frame if one was supplied/live, otherwise the synthetic reference frame."""
    if _CTX["frame"] is not None:
        return _CTX["frame"]
    path = _CTX.get("frame_path") or ""
    if path:
        import cv2

        img = None
        try:  # cv2.imread cannot handle non-ASCII paths on Windows -> decode bytes
            import numpy as np

            with open(path, "rb") as fh:
                img = cv2.imdecode(np.frombuffer(fh.read(), dtype="uint8"), cv2.IMREAD_COLOR)
        except Exception:  # noqa: BLE001
            img = cv2.imread(path)
        if img is None:
            raise FileNotFoundError(f"cannot read frame: {path}")
        _CTX["frame"] = img
        _CTX["source"] = "file"
        return img
    if cfg.get("frame", {}).get("live", True):
        img, meta = live_frame(cfg)
        if img is not None:
            _CTX["source"] = "live"
            _CTX["live"] = meta
            return img
        _CTX["live"] = meta
    _CTX["source"] = "synthetic"
    return synthetic_frame(cfg)


def frame_source():
    """Reported alongside every action so a synthetic analysis is never silent."""
    return _CTX.get("source") or ("file" if _CTX["frame_path"] else "synthetic")


def frame_info():
    info = {"frameSource": frame_source()}
    if _CTX.get("live"):
        info["liveFrame"] = _CTX["live"]
    return info


def _as_score_dict(scores):
    """vendor returns [(name, score)]; normalise to {name: score} for reporting."""
    if isinstance(scores, dict):
        return {k: round(float(v), 4) for k, v in scores.items()}
    try:
        return {str(k): round(float(v), 4) for k, v in scores}
    except Exception:  # noqa: BLE001
        return {}


def template_scale(frame, cfg):
    """Templates are authored at the 2560x1600 reference; scale to this frame."""
    mode = _CTX.get("scale", "auto")
    if mode not in ("auto", None, ""):
        return float(mode)
    ref_w = int(cfg["frame"].get("width", 2560))
    return round(float(frame.shape[1]) / float(ref_w), 4)


def action_template_match(cfg):
    v = _vision()
    frame = current_frame(cfg)
    gray = v.preprocess(frame)
    templates = v.load_templates()
    scale = template_scale(frame, cfg)
    score, name, loc, scores = v.best_match_score(gray, templates, scale=scale)
    return {
        "action": "template_match",
        "frameSource": frame_source(),
        "templateScale": scale,
        "templatesLoaded": len(templates),
        "templateNames": [t.name for t in templates],
        "best": {"name": name, "score": round(float(score), 4), "loc": list(loc)},
        "allScores": _as_score_dict(scores),
        "frameGrayShape": list(gray.shape),
    }


def action_edge_preprocess(cfg):
    v = _vision()
    frame = current_frame(cfg)
    gray = v.preprocess(frame)
    return {"action": "edge_preprocess", "frameSource": frame_source(),
            "shape": list(gray.shape), "mean": float(gray.mean())}


def action_roi(cfg):
    v = _vision()
    frame = current_frame(cfg)
    roi = cfg.get("roi", {"left": 0.5, "top": 0.5, "width": 0.5, "height": 0.5})
    fn = getattr(v, "roi_pixels", None)
    if fn:
        rect = fn(frame, roi["left"], roi["top"], roi["width"], roi["height"])
        return {"action": "roi", "frameSource": frame_source(),
                "normalized": roi, "pixels": list(rect)}
    h, w = frame.shape[:2]
    return {"action": "roi", "frameSource": frame_source(),
            "normalized": roi, "pixels": [int(roi["left"] * w), int(roi["top"] * h),
                                          int(roi["width"] * w), int(roi["height"] * h)]}


def action_scene_classify(cfg):
    v = _vision()
    frame = current_frame(cfg)
    gray = v.preprocess(frame)
    templates = v.load_templates()
    scale = template_scale(frame, cfg)
    _, _, _, scores = v.best_match_score(gray, templates, scale=scale)
    table = _as_score_dict(scores)
    best = max(table.items(), key=lambda kv: kv[1]) if table else (None, 0.0)
    return {"action": "scene_classify", "frameSource": frame_source(),
            "templateScale": scale,
            "best": {"name": best[0], "score": round(float(best[1]), 4)},
            "scores": table}


def action_sprite_detector(cfg):
    import detector as det

    input_size = tuple(cfg["sprite"]["input_size"])
    model_path = os.path.normpath(os.path.join(SUITE, cfg["sprite"].get("model", "assets/models/sprite_detector.onnx")))
    model = det.ONNXDetector(model_path, input_size=input_size)
    frame = current_frame(cfg)
    boxes = model.detect(frame)
    return {
        "action": "sprite_detector",
        "frameSource": frame_source(),
        "model": os.path.relpath(model_path, SUITE),
        "modelBytes": os.path.getsize(model_path),
        "inputSize": list(input_size),
        "provider": "onnxruntime",
        "detections": len(boxes),
        "detectionsShape": (list(boxes[0].keys()) if boxes else []),
        "boxes": [{k: (round(float(v), 4) if isinstance(v, float) else v) for k, v in b.items()} for b in boxes[:10]],
        "frame": {"width": int(frame.shape[1]), "height": int(frame.shape[0])},
    }


def action_ocr(cfg):
    return {
        "action": "ocr",
        "status": "skipped",
        "reason": "OCR backend not installed in this engine venv (tesseract/easyocr absent by design)",
        "component": "vision.ocr",
    }


ACTIONS = {
    "template_match": action_template_match,
    "edge_preprocess": action_edge_preprocess,
    "roi": action_roi,
    "scene_classify": action_scene_classify,
    "sprite_detector": action_sprite_detector,
    "ocr": action_ocr,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--log", default="")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--action", default="template_match")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--frame", default="", help="PNG written by the capture engine (real frame)")
    ap.add_argument("--scale", default="auto", help="template scale: auto|0.5|1.0|...")
    args = ap.parse_args()

    cfg = load_toml(args.config)
    _CTX["frame_path"] = args.frame or str(cfg.get("vision", {}).get("frame_file", "") or "")
    _CTX["scale"] = args.scale or str(cfg.get("vision", {}).get("template_scale", "auto"))
    _CTX["source"] = ("file" if _CTX["frame_path"]
                      else ("live" if cfg.get("frame", {}).get("live", True) else "synthetic"))
    emit(args.log, "ready", run_id=args.run_id, config=args.config, python=sys.version.split()[0],
         frameSource=_CTX["source"], templateScale=_CTX["scale"], liveDir=LIVE_DIR,
         components=["vision.template_match", "vision.edge_preprocess", "vision.scene_classify",
                     "vision.roi", "vision.sprite_detector", "vision.ocr"])

    fn = ACTIONS.get(args.action)
    if fn is None:
        emit(args.log, "error", error=f"unknown action: {args.action}", actions=sorted(ACTIONS))
        return 2

    if not args.once:
        try:
            while True:
                emit(args.log, "result", result=fn(cfg))
                time.sleep(max(0.1, args.interval))
        except KeyboardInterrupt:
            return 0

    try:
        emit(args.log, "result", result=fn(cfg))
    except Exception as exc:  # noqa: BLE001
        emit(args.log, "error", error=f"{type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
