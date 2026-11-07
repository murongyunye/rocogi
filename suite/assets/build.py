"""S1 asset pipeline: import upstream resources into assets/ and write manifest.json.

Sources (per vendor/MERGE_MAP; vendor is the read-only imported copy):
  nrc.db                      ColinHong10-NRC_AI/data/nrc.db
  SIFT features / maps        sift-map-tracker/sift-map-tracker/assets/   (8192x8192 space)
  points / icons / templates  rocogi/data/map, rocogi/data/templates      (6144x5888 canonical)
  sprite detector             Tsuann-RocoKingdom-AutoCapture/models/sprite_detector.onnx

Run with the sift engine venv (needs numpy):
  engines/sift/.venv/Scripts/python.exe assets/build.py
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import time

import numpy as np

SUITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROCogi = os.path.dirname(SUITE)
WORK = os.path.dirname(ROCogi)
UPSTREAM = os.path.join(ROCogi, "vendor")

ASSETS = os.path.join(SUITE, "assets")

SRC = {
    "nrc_db": os.path.join(UPSTREAM, "ColinHong10-NRC_AI", "data", "nrc.db"),
    "sift_npz": os.path.join(UPSTREAM, "sift-map-tracker", "sift-map-tracker", "assets", "SIFT_features_075.npz"),
    "display_map": os.path.join(UPSTREAM, "sift-map-tracker", "sift-map-tracker", "assets", "display_map.png"),
    "logic_map": os.path.join(UPSTREAM, "sift-map-tracker", "sift-map-tracker", "assets", "logic_map.png"),
    "map_dir": os.path.join(ROCogi, "data", "map"),
    "templates_dir": os.path.join(ROCogi, "data", "templates"),
    "onnx": os.path.join(UPSTREAM, "Tsuann-RocoKingdom-AutoCapture", "models", "sprite_detector.onnx"),
}

# canonical map space (luoke_location + roco-map-tracker are same-source)
CANONICAL = {"width": 6144, "height": 5888, "x_min": -12, "y_min": -11, "tile_size": 256, "zoom": 7}
DEDUP_GRID = 24


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure(path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def _rel(path: str) -> str:
    """Manifest must stay portable: never store an absolute path."""
    return os.path.relpath(path, SUITE).replace(os.sep, "/")


def copy(src: str, dst: str, bucket: list, kind: str) -> str:
    ensure(dst)
    if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(src):
        shutil.copy2(src, dst)
    bucket.append({"kind": kind, "path": os.path.relpath(dst, SUITE), "bytes": os.path.getsize(dst), "sha256": sha256(dst)})
    return dst


def build_sift_features(bucket: list) -> dict:
    npz = np.load(SRC["sift_npz"], allow_pickle=False)
    kp = np.ascontiguousarray(npz["keypoints"], dtype=np.float32)
    des = np.ascontiguousarray(npz["descriptors"], dtype=np.float16)
    map_w = int(npz["map_width"][0])
    map_h = int(npz["map_height"][0])
    count = int(kp.shape[0])

    f16 = ensure(os.path.join(ASSETS, "features", "sift_075_desc.f16"))
    kp_path = ensure(os.path.join(ASSETS, "features", "sift_075_kp.f32"))
    des.tofile(f16)
    kp.tofile(kp_path)
    meta = {
        "source": os.path.relpath(SRC["sift_npz"], WORK),
        "profile": "sift-map-tracker v0.10.2 / SIFT_features_075.npz",
        "featureCount": count,
        "descriptor": {"path": os.path.relpath(f16, SUITE), "dtype": "float16", "shape": [count, int(des.shape[1])], "bytes": os.path.getsize(f16)},
        "keypoints": {"path": os.path.relpath(kp_path, SUITE), "dtype": "float32", "shape": [count, int(kp.shape[1])], "bytes": os.path.getsize(kp_path)},
        "map": {"width": map_w, "height": map_h, "origin_x": -973, "origin_y": -1585, "space": "sift-map-tracker-8192"},
        "coordinateNote": "8192x8192 space with MAP_ORIGIN offset; NOT the canonical 6144x5888 space. "
                          "Cross-space use requires 3-point affine calibration (see MERGE_MAP 3.2).",
        "profileScale": float(npz["profile_scale"][0]),
    }
    meta_path = ensure(os.path.join(ASSETS, "features", "sift_075.meta.json"))
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    bucket.append({"kind": "sift-descriptor", "path": meta["descriptor"]["path"], "bytes": meta["descriptor"]["bytes"], "sha256": sha256(f16)})
    bucket.append({"kind": "sift-keypoints", "path": meta["keypoints"]["path"], "bytes": meta["keypoints"]["bytes"], "sha256": sha256(kp_path)})
    bucket.append({"kind": "sift-meta", "path": os.path.relpath(meta_path, SUITE), "bytes": os.path.getsize(meta_path), "sha256": sha256(meta_path)})
    return {"featureCount": count, "mapWidth": map_w, "mapHeight": map_h, "rawBytes": meta["descriptor"]["bytes"] + meta["keypoints"]["bytes"]}


def build_points_sqlite(bucket: list) -> dict:
    raw = []
    sources = {}
    for name in ("taptap.json", "easy_roco.json"):
        path = os.path.join(SRC["map_dir"], name)
        data = json.loads(open(path, encoding="utf-8").read())
        sources[name] = len(data)
        for item in data:
            raw.append(
                {
                    "id": str(item.get("id")),
                    "title": str(item.get("title") or ""),
                    "label": str(item.get("label") or "未分类"),
                    "category": str(item.get("category") or "其他"),
                    "mark_type": item.get("mark_type"),
                    "x": float(item.get("pixel_x") or 0),
                    "y": float(item.get("pixel_y") or 0),
                    "source": name.replace(".json", ""),
                    "icon": f"icons/{item.get('mark_type')}.png",
                }
            )

    seen = set()
    points = []
    for p in raw:
        key = (round(p["x"] / DEDUP_GRID), round(p["y"] / DEDUP_GRID), p["label"])
        if key in seen:
            continue
        seen.add(key)
        points.append(p)

    db_path = ensure(os.path.join(ASSETS, "map", "points.sqlite"))
    tmp = db_path + ".new"
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    con.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT)")
    con.execute(
        "CREATE TABLE points(id TEXT, title TEXT, label TEXT, category TEXT, mark_type INTEGER, "
        "x REAL, y REAL, source TEXT, icon TEXT)"
    )
    con.execute("CREATE TABLE marker_types(id INTEGER PRIMARY KEY, payload TEXT)")
    con.execute("CREATE INDEX idx_points_label ON points(label)")
    con.execute("CREATE INDEX idx_points_category ON points(category)")
    con.executemany(
        "INSERT INTO points VALUES (?,?,?,?,?,?,?,?,?)",
        [(p["id"], p["title"], p["label"], p["category"], p["mark_type"], p["x"], p["y"], p["source"], p["icon"]) for p in points],
    )

    marker_path = os.path.join(SRC["map_dir"], "marker_types.json")
    marker_types = json.loads(open(marker_path, encoding="utf-8").read()) if os.path.exists(marker_path) else []
    rows = []
    if isinstance(marker_types, list):
        for i, m in enumerate(marker_types):
            mid = m.get("mark_type", m.get("id", i)) if isinstance(m, dict) else i
            rows.append((int(mid) if str(mid).lstrip("-").isdigit() else i, json.dumps(m, ensure_ascii=False)))
    else:
        for k, v in marker_types.items():
            rows.append((int(k), json.dumps(v, ensure_ascii=False)))

    con.executemany("INSERT OR REPLACE INTO marker_types VALUES (?,?)", rows)
    con.executemany(
        "INSERT INTO meta VALUES (?,?)",
        [
            ("canonical_map", json.dumps(CANONICAL)),
            ("point_count", str(len(points))),
            ("raw_sources", json.dumps(sources)),
            ("dedup_grid", str(DEDUP_GRID)),
        ],
    )
    con.commit()
    con.close()

    if os.path.exists(db_path):
        os.remove(db_path)
    os.rename(tmp, db_path)
    bucket.append({"kind": "points-sqlite", "path": os.path.relpath(db_path, SUITE), "bytes": os.path.getsize(db_path), "sha256": sha256(db_path)})

    icons_src = os.path.join(SRC["map_dir"], "icons")
    icons_dst = os.path.join(ASSETS, "map", "icons")
    os.makedirs(icons_dst, exist_ok=True)
    icon_count = 0
    for name in sorted(os.listdir(icons_src)):
        if name.lower().endswith(".png"):
            shutil.copy2(os.path.join(icons_src, name), os.path.join(icons_dst, name))
            icon_count += 1

    return {"pointCount": len(points), "rawSources": sources, "markerTypes": len(rows), "icons": icon_count}


def build_templates(bucket: list) -> dict:
    dst_dir = os.path.join(ASSETS, "templates")
    os.makedirs(dst_dir, exist_ok=True)
    count = 0
    for name in sorted(os.listdir(SRC["templates_dir"])):
        if name.lower().endswith(".png"):
            shutil.copy2(os.path.join(SRC["templates_dir"], name), os.path.join(dst_dir, name))
            count += 1
    bucket.append({"kind": "templates", "path": os.path.relpath(dst_dir, SUITE), "bytes": sum(
        os.path.getsize(os.path.join(dst_dir, n)) for n in os.listdir(dst_dir)), "count": count})
    return {"templates": count}


def main() -> int:
    started = time.time()
    bucket: list = []
    stats: dict = {}

    os.makedirs(ASSETS, exist_ok=True)

    stats["nrc_db"] = _rel(copy(SRC["nrc_db"], os.path.join(ASSETS, "db", "nrc.db"), bucket, "battle-db"))
    stats["display_map"] = _rel(copy(SRC["display_map"], os.path.join(ASSETS, "maps", "display_map.png"), bucket, "map-display"))
    stats["logic_map"] = _rel(copy(SRC["logic_map"], os.path.join(ASSETS, "maps", "logic_map.png"), bucket, "map-logic"))
    stats["onnx"] = _rel(copy(SRC["onnx"], os.path.join(ASSETS, "models", "sprite_detector.onnx"), bucket, "sprite-model"))

    # canonical base map (6144x5888) from roco-map-tracker (same source as luoke_location)
    base_src = os.path.join(UPSTREAM, "Wooziii-roco-map-tracker", "roco-map-tracker", "assets", "maps", "big_map.png")
    base_dst = os.path.join(ASSETS, "maps", "big_map.png")
    stats["base_map"] = _rel(copy(base_src, base_dst, bucket, "map-base-6144"))
    # rocogi's small preview of the same map (2048x1963) kept as a lightweight thumbnail
    preview_src = os.path.join(SRC["map_dir"], "base_map.jpg")
    preview_dst = os.path.join(ASSETS, "maps", "base_map.jpg")
    copy(preview_src, preview_dst, bucket, "map-base-preview")

    stats["features"] = build_sift_features(bucket)
    stats["points"] = build_points_sqlite(bucket)
    stats["templates"] = build_templates(bucket)

    manifest = {
        "schema_version": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "canonicalMap": CANONICAL,
        "sources": {k: os.path.relpath(v, WORK) for k, v in SRC.items()},
        "stats": stats,
        "assets": bucket,
    }
    manifest_path = os.path.join(ASSETS, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    print(json.dumps({"ok": True, "elapsed_s": round(time.time() - started, 2), "stats": {
        "pointCount": stats["points"]["pointCount"],
        "featureCount": stats["features"]["featureCount"],
        "icons": stats["points"]["icons"],
        "markerTypes": stats["points"]["markerTypes"],
        "templates": stats["templates"]["templates"],
    }}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
