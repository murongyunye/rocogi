"""RocoPilot 兼容层：路径重定向 + 配置注入 + 依赖降级探测。

默认干跑：只 import 上游 config，枚举模板/模型，不启动游戏、不写任何文件。
被替换/注入的内容全部在内存中完成，上游源码保持零改动。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import repo_dir, run  # noqa: E402


def _probe(modules: list[str]) -> dict[str, bool]:
    return {m: importlib.util.find_spec(m) is not None for m in modules}


def body(result) -> None:
    repo = repo_dir("Makapic-RocoPilot")
    result.add("repo", True, str(repo.name))

    sys.path.insert(0, str(repo))
    try:
        import config  # type: ignore

        result.add("import_config", True, "config.py 导入成功（无第三方依赖）")
        base_dir = Path(config._base_dir())
        result.add(
            "base_dir_redirect",
            str(base_dir).startswith(str(repo)),
            f"templates 基准目录 -> {base_dir.relative_to(repo)}",
        )
    except Exception as exc:  # 上游结构变动时给出明确卡点
        result.add("import_config", False, f"{type(exc).__name__}: {exc}")
        result.block("RocoPilot config 无法导入，需检查上游目录结构")
        return

    templates = sorted(p.name for p in (repo / "templates").glob("**/*") if p.is_file())
    models = sorted(p.name for p in (repo / "models").glob("**/*") if p.is_file())
    result.add("templates", bool(templates), f"{len(templates)} 个模板资源")
    result.add("models", bool(models), f"{len(models)} 个模型文件: {', '.join(models)}")

    deps = _probe(["cv2", "numpy", "mss", "win32api", "interception", "keyboard"])
    result.contract.update(
        {
            "entrypoint": "main.py",
            "base_dir": "vendor/Makapic-RocoPilot",
            "templates": templates,
            "models": models,
            "dependencies": deps,
            "path_policy": "所有相对路径由 config._base_dir() 解析，运行前把 cwd 固定到仓库根目录",
        }
    )
    if not deps.get("cv2") or not deps.get("numpy"):
        result.block("缺 cv2/numpy：请用 suite/engines/vision 或 sift 的独立 venv 运行，不在本层安装")
    if not deps.get("interception"):
        result.contract["input_fallback"] = "interception 缺省时降级到 SendInput（rocogi backend-c/input.c 已有实现）"


if __name__ == "__main__":
    raise SystemExit(run("rocopilot", "Makapic-RocoPilot", body))
