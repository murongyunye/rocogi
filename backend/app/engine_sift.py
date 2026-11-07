from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict

from .adapters.mapdata import MapData
from .adapters.position import SiftPositionSource, MockPositionSource
from .engine_common import load_cli_settings, load_frame

ACTIONS = ("locate", "meta", "points", "route", "anchors", "tracker_info", "tracker_prepare", "tracker_launch")

TRACKER_CLIENT = "SiftMapTracker.Client.exe"
TRACKER_SERVICE = "sift-map-tracker/service/service.exe"


def _tracker_dir() -> Path:
    override = os.environ.get("ROCOGI_SIFT_TRACKER_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates = [
            exe_dir / "optional" / "sift-tracker",
            exe_dir.parent / "optional" / "sift-tracker",
            exe_dir.parent.parent / "optional" / "sift-tracker",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]
    return Path(__file__).resolve().parents[2] / "optional" / "sift-tracker"


def _tracker_zip(base: Path) -> Path | None:
    override = os.environ.get("ROCOGI_SIFT_TRACKER_ZIP")
    if override:
        path = Path(override).expanduser().resolve()
        return path if path.exists() else None
    zips = sorted(base.glob("*.zip"))
    return zips[0] if zips else None


def _tracker_app(base: Path) -> Path:
    return base / "app"


def _safe_extract(archive: Path, dest: Path) -> int:
    count = 0
    with zipfile.ZipFile(archive) as package:
        for member in package.infolist():
            target = (dest / member.filename).resolve()
            if dest.resolve() not in target.parents and target != dest.resolve():
                raise ValueError(f"压缩包包含非法路径: {member.filename}")
            if member.is_dir():
                continue
            count += 1
        package.extractall(dest)
    return count


def _tracker_info() -> Dict[str, Any]:
    base = _tracker_dir()
    archive = _tracker_zip(base)
    app = _tracker_app(base)
    client = app / TRACKER_CLIENT
    service = app / TRACKER_SERVICE
    manifest = {}
    if (base / "manifest.json").exists():
        try:
            manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
        except Exception:
            manifest = {}
    return {
        "optionalDir": str(base),
        "archive": str(archive) if archive else None,
        "archiveBytes": archive.stat().st_size if archive else 0,
        "archiveExists": bool(archive),
        "extracted": app.exists(),
        "client": str(client),
        "clientExists": client.exists(),
        "service": str(service),
        "serviceExists": service.exists(),
        "platform": sys.platform,
        "launchable": sys.platform.startswith("win") and client.exists(),
        "manifest": manifest,
        "hint": "Windows WPF 客户端；Linux 只能解包与校验，不能启动。",
    }


def _tracker_prepare() -> Dict[str, Any]:
    base = _tracker_dir()
    archive = _tracker_zip(base)
    app = _tracker_app(base)
    if app.exists() and (app / TRACKER_CLIENT).exists():
        return {"ok": True, "already": True, **_tracker_info()}
    if not archive:
        raise ValueError(f"未找到 SIFT Map Tracker 压缩包: {base}")
    app.mkdir(parents=True, exist_ok=True)
    count = _safe_extract(archive, app)
    return {"ok": True, "already": False, "files": count, **_tracker_info()}


def _tracker_launch(params: Dict[str, Any]) -> Dict[str, Any]:
    if not sys.platform.startswith("win"):
        raise ValueError("SIFT Map Tracker 是 Windows WPF 客户端，当前平台不能启动")
    info = _tracker_info()
    if not info["clientExists"]:
        _tracker_prepare()
        info = _tracker_info()
    client = Path(info["client"])
    raw_args = params.get("args") or []
    if not isinstance(raw_args, list):
        raise ValueError("tracker_launch 的 args 必须是字符串数组")
    args = [str(item) for item in raw_args]
    process = subprocess.Popen([str(client), *args], cwd=str(client.parent))
    return {"pid": process.pid, "client": str(client), "args": args}


def dispatch(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if action == "tracker_info":
        return _tracker_info()
    if action == "tracker_prepare":
        return _tracker_prepare()
    if action == "tracker_launch":
        return _tracker_launch(params)

    settings = load_cli_settings(params.get("settings") if isinstance(params.get("settings"), str) else None)
    map_data = MapData()

    if action == "meta":
        return {"map": map_data.meta(), "settings": settings.get("map", {})}

    if action == "points":
        labels = {str(item) for item in params.get("labels") or []}
        categories = {str(item) for item in params.get("categories") or []}
        points = map_data.points
        if labels:
            points = [point for point in points if point.get("label") in labels]
        if categories:
            points = [point for point in points if point.get("category") in categories]
        limit = max(1, min(int(params.get("limit") or 50), 20000))
        return {"total": len(points), "points": points[:limit]}

    if action == "route":
        plan = map_data.plan_route(
            params.get("start") or {"x": 3072, "y": 2944},
            [str(item) for item in params.get("labels") or []],
            [str(item) for item in params.get("categories") or []],
            int(params.get("limit") or 15),
            bool(params.get("roundtrip", False)),
        )
        return {"route": plan}

    if action == "anchors":
        source = SiftPositionSource({**settings.get("map", {}), "cache_anchors": True})
        return {
            "anchors": int(len(source._keypoints)) if source._keypoints is not None else 0,  # noqa: SLF001
            "maxEdge": source.max_edge,
            "cached": source._cache_path.exists(),  # noqa: SLF001
            "cache": str(source._cache_path),  # noqa: SLF001
        }

    if action == "locate":
        frame = load_frame(params, settings)
        source = (
            SiftPositionSource(settings.get("map", {}))
            if settings.get("map", {}).get("position_source") == "sift"
            else MockPositionSource()
        )
        position = source.locate(frame, map_data)
        return {"position": position, "frame": frame.summary()}

    raise ValueError(f"未知定位动作: {action}")
