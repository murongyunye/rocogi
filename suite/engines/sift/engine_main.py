"""sift engine - map localisation + route planning.

Integration sources (MERGE_MAP):
  SIFT localisation : roco-map-tracker tracker/engines/sift_engine.py (SIFTEngine, 6144x5888 space)
  route planning    : roco-map-tracker tracker/route_planner.py
  feature asset     : assets/features/sift_075.* (8192 space, cross-space needs 3-point affine)
Own venv / process, no imports from other suite engines.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sqlite3
import sys
import time

SUITE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.path.dirname(os.path.dirname(SUITE))
TRACKER_ROOT = os.path.join(WORK, "rocogi", "vendor", "Wooziii-roco-map-tracker", "roco-map-tracker")
sys.path.insert(0, TRACKER_ROOT)

ENGINE = "sift"
ASSETS = os.path.join(SUITE, "assets")
import cv2  # noqa: E402


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


_CACHE = {}
GLOBAL_CACHE = os.path.join(ASSETS, "features", "sift_6144_global_p{}_f32.npz")


def _cache_path(scale: float) -> str:
    return GLOBAL_CACHE.format(str(scale).replace(".", ""))


def _make_engine_class():
    """Subclass only to memoise the one-time global SIFT build; upstream code untouched."""
    from tracker.engines.sift_engine import SIFTEngine, SearchRegion
    import numpy as np

    class CachedSIFTEngine(SIFTEngine):
        def _build_search_region(self, image_bgr, *, offset_x, offset_y, scale, bounds=None):
            global_scale = getattr(self.settings, "global_downscale", 1.0)
            is_global = offset_x == 0 and offset_y == 0 and abs(scale - global_scale) < 1e-6
            path = _cache_path(scale)
            if is_global and os.path.exists(path):
                try:
                    with np.load(path, allow_pickle=False) as z:
                        kp = [cv2.KeyPoint(float(a), float(b), float(c), float(d), float(e), int(f), int(g))
                              for a, b, c, d, e, f, g in z["kp"]]
                        return SearchRegion(gray=z["gray"], keypoints=kp,
                                            descriptors=np.ascontiguousarray(z["des"], dtype=np.float32),
                                            offset_x=offset_x, offset_y=offset_y, scale=scale, bounds=bounds)
                except Exception:  # noqa: BLE001 - fall back to a fresh build
                    pass
            region = super()._build_search_region(image_bgr, offset_x=offset_x, offset_y=offset_y,
                                                 scale=scale, bounds=bounds)
            if is_global and region.keypoints:
                try:
                    kp = np.array([[k.pt[0], k.pt[1], k.size, k.angle, k.response, k.octave, k.class_id]
                                   for k in region.keypoints], dtype=np.float32)
                    np.savez_compressed(path, kp=kp, des=np.ascontiguousarray(region.descriptors, dtype=np.float32),
                                        gray=region.gray)
                except Exception:  # noqa: BLE001
                    pass
            return region

    return CachedSIFTEngine


def apply_tuning(settings, tuning):
    """Apply suite-side overrides and return ``(settings, applied)``.

    The upstream config ships gates calibrated for full-size minimap screenshots
    (8 inliers / 0.35 inlier ratio).  A 162x162 crop from the game HUD produces far
    fewer keypoints, so measurably-correct homographies were rejected - see
    `[sift.tuning]` in sift.toml.  ``TrackerSettings`` is a frozen dataclass, so the
    overrides are applied with ``dataclasses.replace``; nothing in the vendor tree is
    modified.
    """
    import dataclasses

    wanted = dict(tuning or {})
    applied = {}
    valid = {}
    for key, value in wanted.items():
        if hasattr(settings, key):
            valid[key] = value
        else:
            applied[key] = "unknown setting (skipped)"
    if not valid:
        return settings, applied
    try:
        settings = dataclasses.replace(settings, **valid)
        applied.update(valid)
    except Exception as exc:  # noqa: BLE001 - never let tuning break the engine
        applied["_error"] = str(exc)
    return settings, applied


def build_engine(cfg):
    if "engine" in _CACHE:
        return _CACHE["engine"]
    import cv2
    from tracker.config import load_config

    tracker_root = os.path.normpath(os.path.join(SUITE, cfg["sift"]["engine_repo"]))
    app_cfg = load_config(os.path.join(tracker_root, "config.json"))
    tuned_sift, tuning = apply_tuning(app_cfg.sift, cfg.get("sift", {}).get("tuning"))
    engine_cls = _make_engine_class()
    engine = engine_cls(logic_map_path=os.path.join(SUITE, cfg["sift"]["logic_map"]), settings=tuned_sift)
    _CACHE["engine"] = engine
    _CACHE["app_config"] = app_cfg
    _CACHE["trackerRoot"] = tracker_root
    _CACHE["tuning"] = tuning
    _CACHE["settings"] = tuned_sift
    return engine


def action_locate(cfg):
    import cv2

    engine = build_engine(cfg)
    profile = cfg["minimap"]["profiles"][cfg["minimap"]["active_profile"]]
    w, h = profile
    big = cv2.imread(os.path.join(ASSETS, "maps", "big_map.png"))
    # deterministic probe crop from a textured area; no accuracy claim - contract only
    cx, cy = cfg["sift"]["probe_center"]
    crop = big[max(0, cy - h // 2): cy + h // 2, max(0, cx - w // 2): cx + w // 2]
    crop = cv2.resize(crop, (w, h), interpolation=cv2.INTER_AREA)
    result = engine.step(crop)
    payload = dataclasses.asdict(result)
    return {"action": "locate", "mapSpace": {"width": 6144, "height": 5888},
            "minimap": {"name": cfg["minimap"]["active_profile"], "size": [w, h]},
            "result": payload}


def affine_from_three_points(src_pts, dst_pts):
    """Cross-space transfer is affine, never a pure scale: 6144x5888 and 8192x8192
    are two spaces with a translation component. Requires >= 3 correspondences."""
    import cv2
    import numpy as np

    if len(src_pts) < 3 or len(dst_pts) < 3:
        raise ValueError("3-point affine calibration needs at least 3 correspondences")
    src = np.array(src_pts[:3], dtype="float32").reshape(3, 1, 2)
    dst = np.array(dst_pts[:3], dtype="float32").reshape(3, 1, 2)
    return cv2.getAffineTransform(src, dst).round(6).tolist()


def action_meta(cfg):
    rel = cfg["sift"]["feature_asset"]
    meta = json.load(open(os.path.join(SUITE, rel), encoding="utf-8"))
    repo = cfg["sift"]["engine_repo"]
    return {"action": "meta", "featureAsset": meta,
            "featureAssetPath": rel,
            "engineRepo": repo,
            "mapSpaces": {"canonical": [6144, 5888], "alternate": [8192, 8192],
                          "note": "not related by scale alone - 3-point affine calibration required"},
            "spaceBridge": {"method": "3-point affine", "minPoints": 3,
                            "scalingOnly": False,
                            "status": "calibration required before cross-space use"}}


def action_route(cfg):
    from tracker.models import NormalizedPoint
    from tracker.route_planner import plan_route

    db = sqlite3.connect(os.path.join(ASSETS, "map", "points.sqlite"))
    rows = db.execute(
        "SELECT id, mark_type, title, x, y, icon, source, category, label FROM points WHERE mark_type IN "
        "(" + ",".join(str(int(m)) for m in cfg["route"]["collectible_mark_types"]) + ") LIMIT ?",
        (cfg["route"]["max_points"],),
    ).fetchall()
    db.close()
    points = [
        NormalizedPoint(id=r[0], mark_type=int(r[1] or 0), title=r[2] or "", lat=0.0, lng=0.0,
                        pixel_x=int(r[3]), pixel_y=int(r[4]), icon_path=r[5] or "",
                        source=r[6] or "", category=r[7] or "", label=r[8] or "")
        for r in rows
    ]
    plan = plan_route(
        points=points,
        enabled_mark_types=set(int(m) for m in cfg["route"]["collectible_mark_types"]),
        collectible_mark_types=set(int(m) for m in cfg["route"]["collectible_mark_types"]),
        start_mode="fixed_corner",
        current_position=None,
        map_height=5888,
    )
    payload = dataclasses.asdict(plan)
    return {"action": "route", "pointsUsed": len(points), "plan": {
        "planned_count": payload["planned_count"],
        "source_mode": payload["source_mode"],
        "pointIds": list(payload["point_ids"])[:10],
        "polylineHead": [list(p) for p in payload["polyline"][:5]],
        "waypointCount": len(payload["waypoints"]),
        "title": payload["title"],
    }}


def action_points(cfg):
    db = sqlite3.connect(os.path.join(ASSETS, "map", "points.sqlite"))
    total = db.execute("SELECT COUNT(*) FROM points").fetchone()[0]
    labels = db.execute("SELECT label, COUNT(*) FROM points GROUP BY label ORDER BY COUNT(*) DESC LIMIT 8").fetchall()
    db.close()
    return {"action": "points", "pointCount": total, "topLabels": [{"label": l, "count": c} for l, c in labels]}


ACTIONS = {"locate": action_locate, "route": action_route, "points": action_points, "meta": action_meta}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--log", default="")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--action", default="locate")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=float, default=1.0)
    args = ap.parse_args()

    cfg = load_toml(args.config)
    emit(args.log, "ready", run_id=args.run_id, config=args.config, python=sys.version.split()[0],
         components=["sift.minimap_region", "sift.features", "sift.anchor_index", "sift.homography",
                     "sift.trajectory", "sift.kalman_tracker", "sift.route_plan", "sift.external_tracker"])

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
