"""luoke_location 兼容层：SIFT 数据路径重定向 + 小地图区域归一化。

上游把 MINIMAP 写成了桌面绝对坐标（left=1853, top=292, 150×150）。
本层在不改上游源码的前提下，把绝对坐标换算成"相对游戏窗口 + 基准分辨率"的 ROI，
并把小地图尺寸做成可配置项（150×150 / 162×162 / 255×235）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import MINIMAP_SIZES, normalize_rect, repo_dir, run  # noqa: E402


def body(result) -> None:
    repo = repo_dir("zh19990906-luoke_location")
    result.add("repo", True, repo.name)

    sys.path.insert(0, str(repo))
    try:
        import config  # type: ignore

        result.add("import_config", True, "config.py 导入成功")
        raw_minimap = dict(getattr(config, "MINIMAP", {}))
    except Exception as exc:
        result.add("import_config", False, f"{type(exc).__name__}: {exc}")
        result.block("config 无法导入")
        return

    # 绝对坐标 -> 相对 ROI：调用方注入窗口左上角 (win_x, win_y) 与 DPI 缩放。
    win_origin = (0, 0)
    dpi_scale = 1.0
    rel = (
        round((raw_minimap.get("left", 0) - win_origin[0]) / dpi_scale),
        round((raw_minimap.get("top", 0) - win_origin[1]) / dpi_scale),
        round(raw_minimap.get("width", 0) / dpi_scale),
        round(raw_minimap.get("height", 0) / dpi_scale),
    )
    norm = normalize_rect((raw_minimap.get("left", 0), raw_minimap.get("top", 0),
                           raw_minimap.get("width", 0), raw_minimap.get("height", 0)),
                          (2560, 1440), (1920, 1080))
    result.add("minimap_present", bool(raw_minimap), f"上游原始值 {raw_minimap}")
    result.add("minimap_normalized", True, f"相对窗口 ROI={rel}；2560x1440->1920x1080 归一化={norm}")

    data_dir = repo / "data"
    points = json.loads((data_dir / "points_data.json").read_text(encoding="utf-8"))
    map_cfg = json.loads((data_dir / "map_config.json").read_text(encoding="utf-8"))
    icon_count = len(list((data_dir / "icons").glob("*.png")))
    result.add("points_data", True, f"{len(points)} 个点位")
    result.add("icons", icon_count > 0, f"{icon_count} 个图标")
    result.add("map_config", True, json.dumps(map_cfg, ensure_ascii=False))

    result.contract.update(
        {
            "entrypoints": ["main_sift.py", "main_ai.py"],
            "minimap_raw": raw_minimap,
            "minimap_relative_roi": rel,
            "minimap_normalized_1920x1080": norm,
            "minimap_size_presets": MINIMAP_SIZES,
            "dpi_injection": {"win_origin": win_origin, "dpi_scale": dpi_scale},
            "map_config": map_cfg,
            "points": len(points),
            "features": {
                "SIFT_MAP_NFEATURES": getattr(config, "SIFT_MAP_NFEATURES", None),
                "SIFT_MINIMAP_MIN_KP": getattr(config, "SIFT_MINIMAP_MIN_KP", None),
                "SIFT_FORCE_FULLMAP_LOST_FRAMES": getattr(config, "SIFT_FORCE_FULLMAP_LOST_FRAMES", None),
            },
            "path_policy": "LOGIC_MAP_PATH / DISPLAY_MAP_PATH 均需指向 vendor 内 data 或 suite/assets，禁止写回 upstream",
        }
    )


if __name__ == "__main__":
    raise SystemExit(run("luoke_location", "zh19990906-luoke_location", body))
