"""Auto-rocokingdom 兼容层：窗口/截图/模板路径重定向。

干跑只导入 config 与 core 模块，确认入口与资源齐备；不抓屏、不注入按键。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import repo_dir, run  # noqa: E402


def body(result) -> None:
    repo = repo_dir("yorusacri-Auto-rocokingdom")
    result.add("repo", True, str(repo.name))

    sys.path.insert(0, str(repo))
    try:
        import config  # type: ignore

        result.add("import_config", True, "config.py 导入成功")
        result.add(
            "base_dir_redirect",
            str(Path(config._base_dir())).startswith(str(repo)),
            "模板目录在 vendor 内解析",
        )
    except Exception as exc:
        result.add("import_config", False, f"{type(exc).__name__}: {exc}")
        result.block("config 无法导入")
        return

    core_files = sorted(p.name for p in (repo / "core").glob("*.py"))
    templates = sorted(p.name for p in (repo / "templates").glob("**/*") if p.is_file())
    deps = {m: importlib.util.find_spec(m) is not None for m in ("cv2", "numpy", "mss", "pygetwindow", "win32gui")}
    result.add("core_modules", len(core_files) >= 5, f"{len(core_files)} 个 core 模块")
    result.add("templates", bool(templates), f"{len(templates)} 个模板")

    result.contract.update(
        {
            "entrypoints": ["main.py", "client_main.py", "core/gui.py"],
            "modules": {
                "capture": "core/capture.py",
                "window": "core/window.py",
                "vision": "core/vision.py",
                "input": "core/input.py",
                "engine": "core/engine.py",
            },
            "templates": templates,
            "dependencies": deps,
        }
    )
    if not deps.get("cv2"):
        result.block("缺 cv2：用 suite/engines/capture 或 vision 的独立 venv 干跑")


if __name__ == "__main__":
    raise SystemExit(run("auto_rocokingdom", "yorusacri-Auto-rocokingdom", body))
