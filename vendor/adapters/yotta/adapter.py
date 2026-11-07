"""yotta（Go + TS）契约导出层：Node Contract / Workflow / Evidence 结构。

不构建（本机无 Go 工具链），只把 contracts/node/v2 的 schema 与内置节点目录导出为契约 JSON。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import repo_dir, run  # noqa: E402


def body(result) -> None:
    repo = repo_dir("yottaapp-yotta")
    result.add("repo", True, repo.name)

    contracts = repo / "contracts" / "node" / "v2"
    catalog_file = contracts / "builtin-catalog.json"
    schema_file = contracts / "node-contract.schema.json"

    catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
    schema = json.loads(schema_file.read_text(encoding="utf-8"))
    nodes = catalog.get("nodes", [])
    result.add("node_contract_schema", bool(schema), schema.get("$id", schema.get("title", "schema ok")))
    result.add("builtin_nodes", len(nodes) > 0, f"{len(nodes)} 个内置节点")

    go_mod = (repo / "go.mod").read_text(encoding="utf-8", errors="ignore")
    module = re.search(r"^module\s+(\S+)", go_mod, re.M)
    go_version = re.search(r"^go\s+(\S+)", go_mod, re.M)
    go_files = len(list(repo.rglob("*.go")))
    result.add("go_sources", go_files > 500, f"{go_files} 个 .go")
    result.add("go_module", module is not None, f"{module.group(1) if module else '?'} / go {go_version.group(1) if go_version else '?'}")

    frontend = repo / "frontend"
    ts_files = len(list(frontend.rglob("*.ts"))) if frontend.exists() else 0
    vue_files = len(list(frontend.rglob("*.vue"))) if frontend.exists() else 0

    result.contract.update(
        {
            "language": "Go + TypeScript/Vue",
            "module": module.group(1) if module else None,
            "go_version": go_version.group(1) if go_version else None,
            "entrypoints": ["main.go", "cmd/node-catalog/main.go", "cmd/service-config/main.go"],
            "node_catalog": {
                "format": catalog.get("format"),
                "version": catalog.get("version"),
                "generatorVersion": catalog.get("generatorVersion"),
                "node_count": len(nodes),
                "node_type_ids": [n.get("nodeRef", {}).get("nodeTypeId") for n in nodes][:200],
                "entrypoints": sorted({n.get("implementation", {}).get("entrypoint") for n in nodes if n.get("implementation", {}).get("entrypoint")})[:60],
            },
            "contract_files": sorted(p.name for p in contracts.glob("*")),
            "frontend": {"ts": ts_files, "vue": vue_files},
            "build_requirements": ["Go 1.22+", "Wails/webview2（桌面壳）", "Node 22.12+ / npm"],
            "minimal_run_plan": [
                "1) 安装 Go 1.22+ 后 go build ./... 通过即可导出 node-catalog",
                "2) 仅要契约时无需构建：直接读 vendor 内 contracts/node/v2/*.json",
                "3) 桌面壳需要 Wails CLI + WebView2 Runtime",
            ],
        }
    )
    result.block("本机无 Go 工具链，未构建；契约已完整导出，构建需安装 Go 1.22+ 与 Wails")


if __name__ == "__main__":
    raise SystemExit(run("yotta", "yottaapp-yotta", body))
