"""rocokingdom-ui（TSX/前端）契约导出层：设计令牌 + 组件清单 + workspace 结构。

不构建（缺 pnpm 11.5.3 与 vite-plus catalog），只导出可被其他前端复用的令牌与组件契约。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import repo_dir, run  # noqa: E402


def body(result) -> None:
    repo = repo_dir("rookie-orange-rocokingdom-ui")
    result.add("repo", True, repo.name)

    pkg = json.loads((repo / "package.json").read_text(encoding="utf-8"))
    result.add("workspace", pkg.get("name") == "rocokingdom-ui-workspace", pkg.get("name", ""))
    result.add("package_manager", pkg.get("packageManager") == "pnpm@11.5.3", pkg.get("packageManager", ""))

    workspace_dirs = [p.name for p in (repo / "packages").iterdir() if p.is_dir()]
    result.add("packages", bool(workspace_dirs), ", ".join(workspace_dirs))

    tokens_index = repo / "packages" / "tokens" / "src" / "index.ts"
    exports = []
    token_values = 0
    if tokens_index.is_file():
        source = tokens_index.read_text(encoding="utf-8", errors="ignore")
        exports = re.findall(r"export\s+(?:const|type|interface)\s+(\w+)", source)
        token_values = len(re.findall(r"export\s+const\s+\w+\s*=\s*['\"#]", source))
    result.add("tokens", bool(exports), f"{len(exports)} 个导出，{token_values} 个颜色/尺寸常量")

    tsx = len(list(repo.rglob("*.tsx")))
    ts = len(list(repo.rglob("*.ts")))
    result.add("components", tsx > 100, f"{tsx} 个 .tsx / {ts} 个 .ts")

    ui_pkg = repo / "packages" / "ui" / "package.json"
    ui_meta = json.loads(ui_pkg.read_text(encoding="utf-8")) if ui_pkg.is_file() else {}

    result.contract.update(
        {
            "language": "TypeScript + TSX",
            "engine_node": pkg.get("engines", {}).get("node"),
            "package_manager": pkg.get("packageManager"),
            "packages": workspace_dirs,
            "tokens_exports": exports,
            "token_values": token_values,
            "token_files": sorted(p.name for p in (repo / "packages" / "tokens").rglob("*") if p.is_file()),
            "ui_package": ui_meta.get("name"),
            "counts": {"tsx": tsx, "ts": ts},
            "build_requirements": ["Node >=22.12", "pnpm 11.5.3", "vite-plus catalog 依赖"],
            "minimal_run_plan": "仅复用令牌时直接读 packages/tokens/src/index.ts；要跑站需 pnpm install + vp run website#dev",
        }
    )
    result.block("缺 pnpm 11.5.3 且 catalog 依赖未联网安装；只做令牌/组件契约导出，不构建")


if __name__ == "__main__":
    raise SystemExit(run("rocokingdom_ui", "rookie-orange-rocokingdom-ui", body))
