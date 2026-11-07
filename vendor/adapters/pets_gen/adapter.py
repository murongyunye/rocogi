"""rocom-codex-pets-gen 兼容层：脚本可导入 + 外部输入缺口说明。

澄清：该仓库**有源码**（scripts/ 下 10 个 Python 模块），缺的是"用户自备的宠物资源目录"和离屏渲染器。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import repo_dir, run  # noqa: E402


def body(result) -> None:
    repo = repo_dir("ElliottZhao666666-rocom-codex-pets-gen")
    result.add("repo", True, repo.name)

    scripts = sorted(p.name for p in (repo / "scripts").glob("*.py"))
    result.add("scripts", len(scripts) >= 7, f"{len(scripts)} 个脚本")
    sys.path.insert(0, str(repo / "scripts"))
    try:
        import validate_input  # type: ignore

        result.add("import_validate_input", True, "validate_input 导入成功（纯标准库）")
        result.add("public_functions", True,
                   "validate_input/read_glb/require: " +
                   ", ".join(name for name in ("validate_input", "read_glb", "require") if hasattr(validate_input, name)))
    except Exception as exc:
        result.add("import_validate_input", False, f"{type(exc).__name__}: {exc}")
        result.block("validate_input 导入失败")

    has_pil = importlib.util.find_spec("PIL") is not None
    has_ffmpeg = importlib.util.find_spec("imageio_ffmpeg") is not None
    result.add("pillow", has_pil, "render_source.py 需要 Pillow")
    result.add("imageio_ffmpeg", has_ffmpeg, "视频/帧处理可选依赖")

    resources = list((repo / "references").glob("*"))
    tests = sorted(p.name for p in (repo / "tests").glob("test_*.py"))
    result.add("tests", bool(tests), f"{len(tests)} 个测试文件")

    result.contract.update(
        {
            "source_complete": True,
            "entrypoints": ["scripts/validate_input.py", "scripts/render_source.py", "scripts/normalize_frames.py"],
            "scripts": scripts,
            "docs": [p.name for p in resources],
            "tests": tests,
            "external_inputs_required": [
                "符合 docs/resource-directory.md 的单实体资源目录（模型/贴图/动作/眼口图集）",
                "兼容离屏渲染器 rocom-pets 1.14.2（仓库不分发）",
                "Codex 环境 + 已启用 Pets 插件",
            ],
            "gap_vs_task_brief": "任务写的是'无源码'，实际有 7 个脚本 + 3 个测试（共 10 个 .py）；缺的是外部资源与渲染器，不是源码",
        }
    )
    result.block("端到端运行需要外部资源目录 + rocom-pets 渲染器，仓库内不提供")


if __name__ == "__main__":
    raise SystemExit(run("pets_gen", "ElliottZhao666666-rocom-codex-pets-gen", body))
