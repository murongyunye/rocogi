"""RocoTools 契约导出层：图鉴字段模型 + REST 路由清单 + 数据缺口。

该仓库代码完整，但 data/pets、data/skills、data/elements 只有 .gitkeep，没有实际图鉴数据。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import repo_dir, run  # noqa: E402


def body(result) -> None:
    repo = repo_dir("eachyczhang-RocoTools")
    result.add("repo", True, repo.name)

    data_files = [p for p in (repo / "data").rglob("*") if p.is_file()]
    real_data = [p for p in data_files if p.suffix in {".json", ".sqlite", ".db", ".csv"}]
    result.add("data_present", bool(real_data), f"{len(real_data)} 个数据文件（其余为 .gitkeep/文档）")

    server = repo / "app" / "server"
    routes = sorted(p.stem for p in (server / "src" / "routes").glob("*.js"))
    result.add("rest_routes", bool(routes), ", ".join(routes))
    schema = (server / "src" / "db" / "schema.sql").read_text(encoding="utf-8", errors="ignore")
    tables = re.findall(r"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+([\w_]+)", schema, re.I)
    result.add("sqlite_schema", bool(tables), f"{len(tables)} 张表: {', '.join(tables)}")

    field_doc = repo / "data" / "FIELDS.md"
    result.add("field_model", field_doc.is_file(), field_doc.name if field_doc.is_file() else "缺失")

    client_pkg = json.loads((repo / "app" / "client" / "package.json").read_text(encoding="utf-8"))
    result.contract.update(
        {
            "language": "JavaScript/Vue + Node.js",
            "server_entry": "app/server/src/index.js",
            "client_entry": "app/client/src/main.js",
            "rest_routes": routes,
            "sqlite_tables": tables,
            "field_model_doc": "data/FIELDS.md",
            "data_gap": {
                "missing": ["data/pets", "data/skills", "data/elements"],
                "current_content": "只有 .gitkeep",
                "recoverable_from": [
                    "仓库 crawler/ 可重新抓取",
                    "app/server 的 import-data 脚本 + 外部 xlsx/json",
                    "NRC_AI nrc.db 可作为部分字段的替代来源",
                ],
            },
            "client_dependencies": client_pkg.get("dependencies", {}),
            "runtime_requirements": ["Node 20+", "npm install（better-sqlite3/sharp 需预编译二进制）", "实际图鉴数据"],
        }
    )
    result.block("缺实际图鉴数据（data 目录只有 .gitkeep），服务端无数据可导入")


if __name__ == "__main__":
    raise SystemExit(run("rocotools", "eachyczhang-RocoTools", body))
