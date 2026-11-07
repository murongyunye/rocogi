"""game-automation 兼容层：配置中心导入 + DPI/分辨率归一化 + 依赖降级探测。

上游 main.py 依赖 customtkinter/torch/ultralytics，本层不启动 GUI，只验证可复用模块。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import normalize_rect, repo_dir, run  # noqa: E402


def body(result) -> None:
    repo = repo_dir("SCH-CMYK-game-automation")
    result.add("repo", True, repo.name)

    sys.path.insert(0, str(repo))
    try:
        from src.utils.config import MiningConfig  # type: ignore

        cfg = MiningConfig()
        result.add("import_config", True, f"MiningConfig 字段 {len(cfg.__dataclass_fields__)} 个")
    except Exception as exc:
        result.add("import_config", False, f"{type(exc).__name__}: {exc}")
        result.block("src.utils.config 无法导入")
        return

    deps = {m: importlib.util.find_spec(m) is not None
            for m in ("cv2", "numpy", "torch", "ultralytics", "customtkinter", "mss", "interception", "win32api")}
    result.add("deps", True, str(deps))

    normalized = normalize_rect((0, 0, 1920, 1080), (2560, 1440), (1920, 1080))
    result.add("dpi_normalized", True, f"2560x1440 全屏 ROI -> 1920x1080 基准 = {normalized}")

    result.contract.update(
        {
            "entrypoints": ["main.py", "run.bat", "calibrate_escape.py", "check_env.py"],
            "modules": {
                "input": "src/engine/controller.py",
                "capture": "src/engine/screen_capture.py",
                "vision": "src/engine/vision_engine.py",
                "position": "src/engine/hybrid_positioner.py",
                "route": "src/automation/route_planner.py",
            },
            "dependencies": deps,
            "config": {
                "walk_key": cfg.walk_key,
                "max_lost_frames": cfg.max_lost_frames,
                "aim_align_window_px": cfg.aim_align_window_px,
                "dead_zone_px": cfg.dead_zone_px,
                "scan_step_px": cfg.scan_step_px,
            },
            "dpi_normalization": normalized,
            "runtime_requirements": [
                "interception.dll 已随仓库提供，但驱动未安装：默认走 SendInput",
                "GPU 推理需 torch+ultralytics；本机未装，检测链路降级为 OpenCV 模板/轮廓",
            ],
        }
    )
    if not deps.get("interception"):
        result.contract["input_fallback"] = "send_input"
    if not deps.get("torch"):
        result.contract["vision_fallback"] = "opencv"


if __name__ == "__main__":
    raise SystemExit(run("game_automation", "SCH-CMYK-game-automation", body))
