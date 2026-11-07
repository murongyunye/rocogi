"""Import real game data from game-data/incoming into normalized products.

Read-only for incoming/; all outputs go to processed/ and import-report.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
import sys
import time
import tomllib
from pathlib import Path

try:
    import cv2
    import numpy as np
except ImportError as exc:  # pragma: no cover - environment check
    print(f"missing dependency: {exc}; run with suite/engines/sift/.venv/Scripts/python.exe", file=sys.stderr)
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parent
INCOMING = ROOT / "incoming"
PROCESSED = ROOT / "processed"
REPORT = ROOT / "import-report.md"
VALIDATOR = ROOT.parent / "vendor" / "ElliottZhao666666-rocom-codex-pets-gen" / "scripts" / "validate_input.py"

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
KNOWN_MAPS = {
    (8192, 8192): ("8192x8192", "8192 pixel world-map space"),
    (6144, 5888): ("6144x5888", "legacy 6144x5888 map space"),
}
COLOR_TYPES = {0: "gray", 2: "rgb", 3: "palette", 4: "gray+alpha", 6: "rgba"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_info(data: bytes) -> dict:
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("not a PNG file")
    pos = 8
    width = height = bit_depth = color_type = None
    dpi = None
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        chunk_type = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + length]
        if chunk_type == b"IHDR" and len(payload) >= 13:
            width, height, bit_depth, color_type, _comp, _filt, _inter = struct.unpack(">IIBBBBB", payload[:13])
        elif chunk_type == b"pHYs" and len(payload) >= 9:
            ppu_x, _ppu_y, unit = struct.unpack(">IIB", payload[:9])
            if unit == 1:
                dpi = round(ppu_x * 0.0254)
        pos += 12 + length
        if chunk_type == b"IEND":
            break
    if width is None or height is None:
        raise ValueError("PNG IHDR missing")
    return {
        "width": width,
        "height": height,
        "bitDepth": bit_depth,
        "colorType": COLOR_TYPES.get(color_type, str(color_type)),
        "dpi": dpi,
    }


def read_image(path: Path, flags=cv2.IMREAD_UNCHANGED):
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, flags)
    if image is None:
        raise ValueError("cv2 cannot decode image")
    return image


def write_image(path: Path, image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ext = path.suffix or ".png"
    ok, encoded = cv2.imencode(ext, image)
    if not ok:
        raise ValueError(f"cannot encode {ext}")
    encoded.tofile(str(path))


def parse_roi(value: str | None):
    if not value:
        return None
    parts = [int(x) for x in value.split(",")]
    if len(parts) != 4 or parts[2] <= 0 or parts[3] <= 0:
        raise argparse.ArgumentTypeError("--roi must be x,y,width,height with positive size")
    return tuple(parts)


def trim_transparent(image):
    if image.ndim == 3 and image.shape[2] == 4:
        mask = image[:, :, 3] > 0
    elif image.ndim == 3:
        corner = image[0, 0, :]
        mask = np.any(image != corner, axis=2)
    else:
        corner = image[0, 0]
        mask = image != corner
    ys, xs = np.where(mask)
    if len(xs) == 0:
        raise ValueError("image is fully transparent or a single uniform color")
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    return image[y0:y1 + 1, x0:x1 + 1], {"x": x0, "y": y0}


def self_match_score(image) -> float | None:
    bgr = image
    if image.ndim == 3 and image.shape[2] == 4:
        bgr = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    if np.all(bgr == bgr[0, 0]):
        return 1.0
    result = cv2.matchTemplate(bgr, bgr, cv2.TM_CCOEFF_NORMED)
    score = float(np.nanmax(result))
    return score if np.isfinite(score) else None


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


class Collector:
    def __init__(self):
        self.stats = {category: {"success": 0, "skipped": 0, "failed": 0}
                      for category in ("frames", "templates", "map", "pets")}
        self.details = {}

    def add(self, category: str, status: str, source: Path, reason: str) -> None:
        bucket = self.stats.setdefault(category, {"success": 0, "skipped": 0, "failed": 0})
        key = {"ok": "success", "skipped": "skipped", "pending-calibration": "skipped", "failed": "failed"}[status]
        bucket[key] += 1
        self.details.setdefault(category, []).append((status, rel(source), reason))


def import_frames(collector: Collector, roi) -> dict:
    out_dir = PROCESSED / "frames"
    out_dir.mkdir(parents=True, exist_ok=True)
    items, duplicates = [], []
    seen_hashes, seen_names = {}, {}
    for path in sorted((INCOMING / "frames").rglob("*.png")):
        try:
            data = path.read_bytes()
            info = png_info(data)
            digest = sha256_file(path)
        except (OSError, ValueError) as exc:
            collector.add("frames", "failed", path, f"unreadable PNG: {exc}")
            continue
        name_collision = seen_names.get(path.name)
        seen_names.setdefault(path.name, digest)
        if digest in seen_hashes:
            duplicates.append({"source": rel(path), "sha256": digest, "duplicateOf": seen_hashes[digest]})
            collector.add("frames", "skipped", path, f"duplicate sha256 of {seen_hashes[digest]}")
            continue
        seen_hashes[digest] = rel(path)
        entry = {
            "source": rel(path),
            "name": path.name,
            "sha256": digest,
            "bytes": len(data),
            "width": info["width"],
            "height": info["height"],
            "dpi": info["dpi"],
            "bitDepth": info["bitDepth"],
            "colorType": info["colorType"],
            "processedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "nameCollisionWith": name_collision,
        }
        if roi:
            x, y, w, h = roi
            if x + w > info["width"] or y + h > info["height"]:
                entry["roiError"] = f"ROI {roi} exceeds {info['width']}x{info['height']}"
                collector.add("frames", "failed", path, entry["roiError"])
                continue
            image = read_image(path)
            crop = image[y:y + h, x:x + w]
            crop_path = out_dir / f"{path.stem}-{digest[:8]}-roi.png"
            write_image(crop_path, crop)
            entry["roi"] = {"x": x, "y": y, "width": w, "height": h}
            entry["roiFile"] = rel(crop_path)
        items.append(entry)
        collector.add("frames", "ok", path,
                      f"{info['width']}x{info['height']} dpi={info['dpi'] if info['dpi'] is not None else 'unset'}")
    index = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "category": "frames",
        "sourceDir": "incoming/frames",
        "roi": roi,
        "items": items,
        "duplicates": duplicates,
    }
    (out_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return index


def import_templates(collector: Collector, max_size: int, self_check: bool) -> dict:
    out_dir = PROCESSED / "templates"
    out_dir.mkdir(parents=True, exist_ok=True)
    items, duplicates = [], []
    seen_hashes = {}
    for path in sorted((INCOMING / "templates").rglob("*.png")):
        try:
            info = png_info(path.read_bytes())
        except (OSError, ValueError) as exc:
            collector.add("templates", "failed", path, f"unreadable PNG: {exc}")
            continue
        if info["width"] > max_size or info["height"] > max_size:
            collector.add("templates", "failed", path,
                          f"{info['width']}x{info['height']} exceeds max {max_size}x{max_size}")
            continue
        try:
            image = read_image(path)
            trimmed, offset = trim_transparent(image)
        except (OSError, ValueError) as exc:
            collector.add("templates", "failed", path, f"cannot trim: {exc}")
            continue
        digest = hashlib.sha256(cv2.imencode(".png", trimmed)[1].tobytes()).hexdigest()
        if digest in seen_hashes:
            duplicates.append({"source": rel(path), "sha256": digest, "duplicateOf": seen_hashes[digest]})
            collector.add("templates", "skipped", path, f"duplicate trimmed sha256 of {seen_hashes[digest]}")
            continue
        seen_hashes[digest] = rel(path)
        out_path = out_dir / f"{path.stem}-{digest[:8]}.png"
        write_image(out_path, trimmed)
        score = self_match_score(trimmed) if self_check else None
        item = {
            "name": path.stem,
            "source": rel(path),
            "original": {"width": info["width"], "height": info["height"], "dpi": info["dpi"]},
            "trimmed": {
                "width": int(trimmed.shape[1]),
                "height": int(trimmed.shape[0]),
                "offsetX": offset["x"],
                "offsetY": offset["y"],
                "file": rel(out_path),
                "sha256": digest,
            },
            "suggestedRoi": {
                "x": 0,
                "y": 0,
                "width": int(trimmed.shape[1]),
                "height": int(trimmed.shape[0]),
                "note": "relative to a full frame; needs anchor calibration",
            },
            "selfMatch": {
                "checked": self_check,
                "score": score,
                "ok": None if score is None else score >= 0.99,
            },
            "processedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        items.append(item)
        collector.add("templates", "ok", path,
                      f"trimmed {item['trimmed']['width']}x{item['trimmed']['height']} selfMatch={score}")
    manifest = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "category": "templates",
        "sourceDir": "incoming/templates",
        "maxTemplateSize": max_size,
        "items": items,
        "duplicates": duplicates,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def import_maps(collector: Collector) -> dict:
    out_dir = PROCESSED / "map"
    out_dir.mkdir(parents=True, exist_ok=True)
    items = []
    for path in sorted((INCOMING / "map").rglob("*.png")):
        try:
            info = png_info(path.read_bytes())
            digest = sha256_file(path)
        except (OSError, ValueError) as exc:
            collector.add("map", "failed", path, f"unreadable PNG: {exc}")
            continue
        space = KNOWN_MAPS.get((info["width"], info["height"]))
        item = {
            "source": rel(path),
            "sha256": digest,
            "width": info["width"],
            "height": info["height"],
            "dpi": info["dpi"],
            "processedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        if space:
            item["space"] = space[0]
            item["spaceNote"] = space[1]
            item["status"] = "known-space"
            collector.add("map", "ok", path, f"recognized {space[0]}")
        else:
            item["space"] = "unknown"
            item["status"] = "needs-calibration"
            calibration = {
                "status": "needs-calibration",
                "source": rel(path),
                "width": info["width"],
                "height": info["height"],
                "requiredControlPoints": 3,
                "controlPoints": None,
                "knownSpaces": [{"name": f"{w}x{h}", "width": w, "height": h} for w, h in KNOWN_MAPS],
                "instruction": "Do not auto-fit. Provide 3 source pixels and 3 target coordinates, then rerun with a calibration file.",
            }
            cal_path = out_dir / f"calibration-{path.stem}.json"
            cal_path.write_text(json.dumps(calibration, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            item["calibrationFile"] = rel(cal_path)
            collector.add("map", "pending-calibration", path,
                          f"{info['width']}x{info['height']} needs 3-point affine calibration")
        items.append(item)
    index = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "category": "map",
        "sourceDir": "incoming/map",
        "knownSpaces": [k[0] for k in KNOWN_MAPS],
        "items": items,
    }
    (out_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return index


def check_pet_files(pet_root: Path) -> list[str]:
    problems = []
    for name in ("entity.json", "manifest.toml", "model.glb"):
        if not (pet_root / name).is_file():
            problems.append(f"missing {name}")
    forms = sorted(pet_root.glob("forms/*"))
    if not forms:
        problems.append("missing forms/<asset>/")
    if not list(pet_root.glob("forms/*/anim.rka")):
        problems.append("missing forms/<asset>/anim.rka")
    if not list(pet_root.glob("forms/*/tex/*.png")):
        problems.append("missing forms/<asset>/tex/*.png")
    entity_path = pet_root / "entity.json"
    if entity_path.is_file():
        try:
            entity = json.loads(entity_path.read_text(encoding="utf-8"))
            if entity.get("schema") != "rkpet2.entity.v1":
                problems.append("entity.json schema is not rkpet2.entity.v1")
        except (json.JSONDecodeError, OSError) as exc:
            problems.append(f"entity.json unreadable: {exc}")
    manifest_path = pet_root / "manifest.toml"
    if manifest_path.is_file():
        try:
            tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            problems.append(f"manifest.toml unreadable: {exc}")
    glb = pet_root / "model.glb"
    if glb.is_file():
        try:
            data = glb.read_bytes()
            magic, version, length = struct.unpack_from("<4sII", data)
            if magic != b"glTF" or version != 2 or length != len(data):
                problems.append("model.glb is not a valid glTF 2.0 GLB")
        except (OSError, struct.error) as exc:
            problems.append(f"model.glb unreadable: {exc}")
    for anim in pet_root.glob("forms/*/anim.rka"):
        if anim.stat().st_size <= 0:
            problems.append(f"empty anim.rka: {rel(anim)}")
    for tex in pet_root.glob("forms/*/tex/*.png"):
        try:
            png_info(tex.read_bytes())
        except (OSError, ValueError) as exc:
            problems.append(f"invalid texture {rel(tex)}: {exc}")
    return problems


def import_pets(collector: Collector) -> dict:
    out_dir = PROCESSED / "pets"
    out_dir.mkdir(parents=True, exist_ok=True)
    items = []
    pets_root = INCOMING / "pets"
    if (pets_root / "entity.json").is_file():
        candidates = [pets_root]
    else:
        candidates = [p for p in sorted(pets_root.iterdir()) if p.is_dir()] if pets_root.exists() else []
    for pet_root in candidates:
        problems = check_pet_files(pet_root)
        validator = {"ran": False}
        if VALIDATOR.is_file():
            json_out = out_dir / f"{pet_root.name}-validator.json"
            cmd = [sys.executable, str(VALIDATOR), "--input", str(pet_root), "--json-out", str(json_out)]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                                      errors="replace", timeout=120)
                validator = {
                    "ran": True,
                    "exitCode": proc.returncode,
                    "interpreter": sys.executable,
                    "resultFile": rel(json_out) if json_out.is_file() else None,
                    "stderrTail": (proc.stderr or "").strip().splitlines()[-3:],
                }
                if json_out.is_file():
                    validator["result"] = json.loads(json_out.read_text(encoding="utf-8"))
                if proc.returncode != 0:
                    problems.append(f"validate_input.py exit {proc.returncode}")
            except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
                problems.append(f"validate_input.py failed: {exc}")
                validator = {"ran": True, "error": str(exc)}
        else:
            problems.append(f"validator not found: {VALIDATOR}")
        status = "ok" if not problems else "failed"
        item = {
            "source": rel(pet_root),
            "name": pet_root.name,
            "status": status,
            "problems": problems,
            "validator": validator,
            "processedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        items.append(item)
        collector.add("pets", status, pet_root, "; ".join(problems) if problems else "all required files present")
    report = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "category": "pets",
        "sourceDir": "incoming/pets",
        "items": items,
    }
    (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def write_report(collector: Collector) -> None:
    order = ["frames", "templates", "map", "pets"]
    lines = [
        "# Game data import report",
        "",
        f"- Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Incoming: `{rel(INCOMING)}` (read-only)",
        f"- Processed: `{rel(PROCESSED)}`",
        "",
        "| Category | Success | Skipped | Failed |",
        "| --- | ---: | ---: | ---: |",
    ]
    for category in order:
        stats = collector.stats.get(category, {"success": 0, "skipped": 0, "failed": 0})
        lines.append(f"| {category} | {stats['success']} | {stats['skipped']} | {stats['failed']} |")
    total = {k: sum(collector.stats.get(c, {}).get(k, 0) for c in order) for k in ("success", "skipped", "failed")}
    lines.append(f"| **total** | **{total['success']}** | **{total['skipped']}** | **{total['failed']}** |")
    lines.append("")
    for category in order:
        lines.append(f"## {category}")
        if not collector.details.get(category):
            lines.append("- (empty)")
        for status, source, reason in collector.details.get(category, []):
            lines.append(f"- [{status}] `{source}` — {reason}")
        lines.append("")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize game-data/incoming into game-data/processed")
    parser.add_argument("--roi", type=parse_roi, help="optional frame crop: x,y,width,height")
    parser.add_argument("--max-template-size", type=int, default=2048, help="max template width/height")
    parser.add_argument("--no-self-check", action="store_true", help="skip template self-match check")
    args = parser.parse_args()

    for path in (INCOMING / "frames", INCOMING / "templates", INCOMING / "map", INCOMING / "pets", PROCESSED):
        path.mkdir(parents=True, exist_ok=True)

    collector = Collector()
    import_frames(collector, args.roi)
    import_templates(collector, args.max_template_size, not args.no_self_check)
    import_maps(collector)
    import_pets(collector)
    write_report(collector)

    summary = {
        "ok": all(v["failed"] == 0 for v in collector.stats.values()),
        "stats": collector.stats,
        "report": rel(REPORT),
        "processed": rel(PROCESSED),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
