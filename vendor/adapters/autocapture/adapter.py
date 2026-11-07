"""AutoCapture 兼容层：Linux/RK3588 采集与 NPU 检测在 Windows 上的降级适配。

不做源码改动，只在内存中覆盖配置：
- capture.device(/dev/video0) -> Windows 采集后端（mss / DXGI）
- detector.rknn_model -> detector.onnx（本机只有 onnx 与 .pt）
同时把 config.yaml 的路径全部解析到 vendor 内。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import repo_dir, run  # noqa: E402


def body(result) -> None:
    repo = repo_dir("Tsuann-RocoKingdom-AutoCapture")
    result.add("repo", True, repo.name)

    cfg_file = repo / "config.yaml"
    has_yaml = importlib.util.find_spec("yaml") is not None
    result.add("pyyaml_available", has_yaml, "读取 config.yaml 需要 PyYAML")
    config = {}
    if has_yaml:
        import yaml  # type: ignore

        config = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
        result.add("load_config", True, f"{len(config)} 个顶层配置段")
    else:
        result.add("load_config", False, "跳过解析：当前解释器无 PyYAML")
        result.block("缺 PyYAML：用 suite/engines/scheduler 的 venv 运行本适配器")

    capture_cfg = config.get("capture", {})
    detector_cfg = config.get("detector", {})
    models = sorted(p.name for p in (repo / "models").glob("*") if p.is_file())
    result.add("models", "sprite_detector.onnx" in models, f"models={models}")

    overrides = {
        "capture.backend": "windows-mss",
        "capture.device": 0,
        "detector.rknn_model": None,
        "detector.onnx_model": "models/sprite_detector.onnx",
        "detector.conf_threshold": detector_cfg.get("conf_threshold"),
        "capture.fps": capture_cfg.get("fps"),
    }
    result.add("platform_overrides", True, str(overrides))
    result.contract.update(
        {
            "entrypoints": ["main.py"],
            "modes": ["debug", "manual", "auto"],
            "modules": ["capture.py", "detector.py", "controller.py", "state_machine.py", "tracker.py"],
            "original_platform": "Linux RK3588 + HDMI /dev/video0 + USB HID gadget",
            "windows_overrides": overrides,
            "models": models,
            "templates": sorted(p.name for p in (repo / "templates").glob("*") if p.is_file()),
            "runtime_requirements": [
                "auto 模式在 Windows 上用 SendInput 替代 HID gadget",
                "rv1106/RKNN 模型缺失时只走 onnxruntime CPU",
            ],
        }
    )


if __name__ == "__main__":
    raise SystemExit(run("autocapture", "Tsuann-RocoKingdom-AutoCapture", body))
