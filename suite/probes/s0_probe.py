"""S0 baseline probe: start one upstream in its own venv, run one operation, write a log.

No accuracy checks. Contract only: can this upstream import its own core and
produce one structured output inside an isolated interpreter?
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback


def _emit(log_path, event, **payload):
    rec = {"ts": round(time.time(), 3), "event": event, **payload}
    line = json.dumps(rec, ensure_ascii=False)
    print(line, flush=True)
    if log_path:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def _load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- probes
def probe_roco_map_tracker(root, emit):
    sys.path.insert(0, root)
    cfg = _load_json(os.path.join(root, "config.json"))
    emit("config", engine_default=cfg.get("engine", {}).get("default"), keys=sorted(cfg))
    from tracker.config import load_config

    app_cfg = load_config(os.path.join(root, "config.json"))
    emit("config_loaded", engine=getattr(app_cfg.engine, "default", None))
    from tracker.engine_factory import build_engine

    name = getattr(app_cfg.engine, "default", "sift_v02")
    engine = build_engine(app_cfg, name)
    emit("engine_built", engine=name, cls=type(engine).__name__)
    return {"engine": name, "class": type(engine).__name__}


def probe_luoke_location(root, emit):
    sys.path.insert(0, root)
    import config as lk_config

    emit(
        "config",
        minimap=lk_config.MINIMAP,
        logic_map=lk_config.LOGIC_MAP_PATH,
        sift_refresh_ms=lk_config.SIFT_REFRESH_RATE,
        query_nfeatures=lk_config.SIFT_QUERY_NFEATURES,
        query_max_edge=lk_config.SIFT_QUERY_MAX_EDGE,
    )
    import map_mask

    emit("module_ok", module="map_mask", api=[n for n in dir(map_mask) if not n.startswith("_")][:8])
    import cv2
    import numpy as np

    sift = cv2.SIFT_create(nfeatures=lk_config.SIFT_QUERY_NFEATURES)
    img = np.zeros((224, 224, 3), dtype=np.uint8)
    cv2.circle(img, (112, 112), 80, (200, 200, 200), 3)
    cv2.line(img, (40, 40), (180, 180), (255, 255, 255), 2)
    kps, des = sift.detectAndCompute(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), None)
    emit("sift_probe", keypoints=len(kps), descriptor_shape=list(des.shape) if des is not None else None)
    return {"keypoints": len(kps), "opencv": cv2.__version__}


def probe_rocopilot(root, emit):
    sys.path.insert(0, root)
    import config as rp_config

    cfg = rp_config.CONFIG
    emit("config", window=cfg.window_title_keyword, ref=(cfg.ref_width, cfg.ref_height), poll=cfg.poll_interval_sec)
    import core.capture  # noqa: F401
    import core.vision as vision

    emit("module_ok", module="core.vision", api=[n for n in dir(vision) if not n.startswith("_")][:8])
    import cv2
    import numpy as np

    frame = np.zeros((cfg.ref_height, cfg.ref_width, 3), dtype=np.uint8)
    templates = vision.load_templates()
    emit("templates_loaded", count=len(templates), names=[t.name for t in templates])
    result = vision.best_match_score(vision.preprocess(frame), templates)
    emit("match_probe", best_score=float(result[0]), best_name=result[1], best_loc=list(result[2]))
    return {"templates": len(templates), "best_score": float(result[0])}


def probe_auto_rocokingdom(root, emit):
    sys.path.insert(0, root)
    import config as ar_config

    cfg = ar_config.CONFIG
    emit("config", window=cfg.window_title_keyword, ref=(cfg.ref_width, cfg.ref_height), poll=cfg.poll_interval_sec)
    import core.capture  # noqa: F401
    import core.vision as vision

    emit("module_ok", module="core.vision", api=[n for n in dir(vision) if not n.startswith("_")][:8])
    import cv2
    import numpy as np

    frame = np.zeros((cfg.ref_height, cfg.ref_width, 3), dtype=np.uint8)
    gray = vision.preprocess(frame)
    emit("preprocess_probe", shape=list(gray.shape), mean=float(np.mean(gray)))
    templates = vision.load_templates()
    emit("templates_loaded", count=len(templates), names=[t.name for t in templates])
    result = vision.best_match_score(gray, templates)
    emit("match_probe", best_score=float(result[0]), best_name=result[1], best_loc=list(result[2]))
    return {"templates": len(templates), "best_score": float(result[0])}


def probe_autocapture(root, emit):
    sys.path.insert(0, root)
    import yaml

    cfg = yaml.safe_load(open(os.path.join(root, "config.yaml"), "r", encoding="utf-8"))
    emit("config", capture=cfg.get("capture", {}), detector=cfg.get("detector", {}))
    import numpy as np

    import detector as det

    model_path = os.path.join(root, "models", "sprite_detector.onnx")
    emit("model_file", path=model_path, bytes=os.path.getsize(model_path))
    import onnxruntime as ort

    emit("onnxruntime", version=ort.__version__, providers=ort.get_available_providers())
    sess = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0]
    emit("onnx_session", input_name=inp.name, input_shape=inp.shape, outputs=[o.name for o in sess.get_outputs()])
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    outs = det.SpriteDetector(cfg) if hasattr(det, "SpriteDetector") else None
    emit("detector_class", cls=type(outs).__name__ if outs is not None else "n/a")
    return {"onnx": ort.__version__, "input_shape": inp.shape}


PROBES = {
    "roco-map-tracker": probe_roco_map_tracker,
    "luoke-location": probe_luoke_location,
    "rocopilot": probe_rocopilot,
    "auto-rocokingdom": probe_auto_rocokingdom,
    "autocapture": probe_autocapture,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, choices=sorted(PROBES))
    ap.add_argument("--root", required=True)
    ap.add_argument("--log", required=True)
    args = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
    started = time.time()

    def emit(event, **payload):
        _emit(args.log, event, name=args.name, **payload)

    emit("boot", python=sys.version.split()[0], executable=sys.executable, root=args.root)
    try:
        result = PROBES[args.name](args.root, emit)
    except Exception as exc:  # noqa: BLE001
        emit(
            "failed",
            error=f"{type(exc).__name__}: {exc}",
            trace=traceback.format_exc().splitlines()[-6:],
            elapsed_s=round(time.time() - started, 2),
        )
        return 1
    emit("ok", result=result, elapsed_s=round(time.time() - started, 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
