"""roco-map-tracker 兼容层：SIFTEngine 直接复用 + 路线规划 + 坐标系标定。

上游 tracker 包可直接 import（models/route_planner 纯标准库；sift_engine 需 cv2+numpy）。
本层提供 6144×5888 与 8192×8192 之间的 3 点仿射标定，禁止只做等比缩放。
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import MAP_SPACES, calibrate, repo_dir, run  # noqa: E402

TRACKER_DIR = "roco-map-tracker"


def body(result) -> None:
    repo = repo_dir("Wooziii-roco-map-tracker")
    result.add("repo", True, repo.name)

    inner = repo / TRACKER_DIR
    sys.path.insert(0, str(inner))
    try:
        from tracker.models import RouteConfig, SIFTSettings  # type: ignore

        result.add("import_models", True, "tracker.models 导入成功（纯标准库）")
    except Exception as exc:
        result.add("import_models", False, f"{type(exc).__name__}: {exc}")
        result.block("tracker.models 无法导入")
        return

    try:
        from tracker.route_planner import resolve_collectible_mark_types  # type: ignore

        result.add("import_route_planner", True, "route_planner 导入成功，可做最近邻路线")
    except Exception as exc:
        result.add("import_route_planner", False, f"{type(exc).__name__}: {exc}")

    has_cv2 = importlib.util.find_spec("cv2") is not None
    has_np = importlib.util.find_spec("numpy") is not None
    result.add("cv2_available", has_cv2, "SIFTEngine 需要 cv2+numpy")
    result.add("numpy_available", has_np, "")
    if has_cv2 and has_np:
        try:
            from tracker.engines.sift_engine import SIFTEngine  # type: ignore

            result.add("import_sift_engine", True, SIFTEngine.__name__)
        except Exception as exc:
            result.add("import_sift_engine", False, f"{type(exc).__name__}: {exc}")
            result.block("SIFTEngine 导入失败，检查 cv2 版本")
    else:
        result.add("import_sift_engine", False, "跳过：当前解释器缺 cv2/numpy，改用 suite/engines/sift 的 venv")
        result.block("SIFTEngine 需 cv2+numpy：用 suite/engines/sift/.venv/Scripts/python.exe 跑本适配器")

    # 3 点仿射示例：同一场景在 6144×5888 与 8192×8192 两套空间的对应点。
    pairs = [
        ((0.0, 0.0), (0.0, 0.0)),
        ((6144.0, 0.0), (8192.0, 0.0)),
        ((0.0, 5888.0), (0.0, 8192.0)),
    ]
    affine = calibrate("main_6144x5888", "world_8192x8192", pairs)
    result.add("affine_calibration", affine.residual([p[0] for p in pairs], [p[1] for p in pairs]) < 1e-6,
               json.dumps(affine.as_dict()["params"], ensure_ascii=False))
    result.add("affine_note", True, "平移/旋转场景必须显式给出 3 组物理对应点，不得用单点缩放替代")

    def _load_points(path: Path) -> object:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if text.lstrip().startswith("<"):
            raise ValueError("HTML 抓取残留，非 JSON")
        return json.loads(text)

    points_file = inner / "data" / "points.normalized.json"
    point_count = 0
    point_source = None
    try:
        payload = _load_points(points_file)
        point_count = len(payload) if isinstance(payload, list) else len(payload.get("points", []))
        point_source = "data/points.normalized.json"
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result.add("legacy_point_json_unusable", False, f"point.json 不可解析: {type(exc).__name__}")
    result.add("point_data", point_count > 0, f"{point_source or '缺失'} / {point_count} 条点位")

    result.contract.update(
        {
            "entrypoints": ["main.py", "main.pyw", "service_main.py"],
            "engine_module": "tracker/engines/sift_engine.py::SIFTEngine",
            "route_module": "tracker/route_planner.py",
            "map_spaces": MAP_SPACES,
            "affine_demo": affine.as_dict(),
            "sift_settings_fields": sorted(getattr(SIFTSettings, "__dataclass_fields__", {}).keys()),
            "route_config_fields": sorted(getattr(RouteConfig, "__dataclass_fields__", {}).keys()),
            "points": point_count,
            "point_source": point_source,
            "legacy_point_json": {
                "path": "roco-map-tracker/point.json",
                "usable": False,
                "reason": "实际是 biligame wiki 的 HTML 页面被错误保存为 .json，不是结构化点位数据",
            },
            "path_policy": "logic_map / point.json / hybrid_index.npz 一律从 vendor 内读取",
        }
    )


if __name__ == "__main__":
    raise SystemExit(run("roco_map_tracker", "Wooziii-roco-map-tracker", body))
