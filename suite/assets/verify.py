"""S1 asset verification: hash every asset, count 9224 points, time feature mmap load.

stdlib + numpy (memmap timing). Run with:
  engines/sift/.venv/Scripts/python.exe assets/verify.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import time

SUITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(SUITE, "assets")

EXPECTED_POINTS = 9224
MMAP_BUDGET_S = 2.0


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_hashes(manifest: dict) -> dict:
    items = manifest.get("assets", [])
    checked = failed = 0
    failures = []
    for item in items:
        if "sha256" not in item:
            continue
        path = os.path.join(SUITE, item["path"])
        if item["path"].endswith(os.sep) or "count" in item:
            continue
        if not os.path.exists(path):
            failures.append({"path": item["path"], "error": "missing"})
            failed += 1
            continue
        actual = sha256(path)
        checked += 1
        if actual != item["sha256"]:
            failed += 1
            failures.append({"path": item["path"], "error": "sha256 mismatch", "expected": item["sha256"], "actual": actual})
    return {"checked": checked, "failed": failed, "failures": failures, "ok": failed == 0}


def check_points() -> dict:
    db = os.path.join(ASSETS, "map", "points.sqlite")
    con = sqlite3.connect(db, uri=True)
    total = con.execute("SELECT COUNT(*) FROM points").fetchone()[0]
    markers = con.execute("SELECT COUNT(*) FROM marker_types").fetchone()[0]
    meta = {k: v for k, v in con.execute("SELECT key, value FROM meta")}
    con.close()
    return {
        "pointCount": total,
        "expected": EXPECTED_POINTS,
        "ok": total == EXPECTED_POINTS,
        "markerTypes": markers,
        "canonicalMap": json.loads(meta.get("canonical_map", "{}")),
    }


def check_mmap() -> dict:
    meta_path = os.path.join(ASSETS, "features", "sift_075.meta.json")
    meta = json.load(open(meta_path, encoding="utf-8"))
    desc = meta["descriptor"]
    path = os.path.join(SUITE, desc["path"])
    import numpy as np

    started = time.perf_counter()
    arr = np.memmap(path, dtype=np.float16, mode="r", shape=tuple(desc["shape"]))
    elapsed = time.perf_counter() - started
    # touch first/last row so the load is real, still no full materialization
    _ = arr[0, :4].tolist()
    _ = arr[-1, -4:].tolist()
    del arr
    return {
        "path": desc["path"],
        "shape": desc["shape"],
        "bytes": desc["bytes"],
        "mmapSeconds": round(elapsed, 4),
        "budgetSeconds": MMAP_BUDGET_S,
        "ok": elapsed <= MMAP_BUDGET_S,
    }


def check_maps() -> dict:
    out = {}
    try:
        from PIL import Image

        for name in ("big_map.png", "base_map.jpg", "logic_map.png", "display_map.png"):
            path = os.path.join(ASSETS, "maps", name)
            with Image.open(path) as im:
                out[name] = {"size": list(im.size), "bytes": os.path.getsize(path)}
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
    base = out.get("big_map.png", {}).get("size")
    out["canonicalMatch"] = bool(base and base[0] == 6144 and base[1] == 5888)
    return out


def check_nrc() -> dict:
    db = os.path.join(ASSETS, "db", "nrc.db")
    # read-only, immutable: never create -wal/-shm next to the imported copy
    con = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True)
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    counts = {}
    for t in ("pokemon", "skill", "pokemon_skill"):
        if t in tables:
            counts[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    con.close()
    return {"tables": tables, "counts": counts, "ok": bool(counts)}


def main() -> int:
    manifest_path = os.path.join(ASSETS, "manifest.json")
    if not os.path.exists(manifest_path):
        print(json.dumps({"ok": False, "error": "assets/manifest.json missing; run assets/build.py first"}, ensure_ascii=False))
        return 2
    manifest = json.load(open(manifest_path, encoding="utf-8"))

    report = {
        "hashes": check_hashes(manifest),
        "points": check_points(),
        "mmap": check_mmap(),
        "maps": check_maps(),
        "nrc": check_nrc(),
    }
    ok = all(v.get("ok", False) for k, v in report.items() if k != "maps") and report["maps"].get("canonicalMatch", False)
    report["ok"] = ok
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
