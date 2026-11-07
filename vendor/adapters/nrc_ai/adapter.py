"""NRC_AI 兼容层：对战数据集契约 + 引擎入口。

nrc.db 是 SQLite，本层只用标准库读取，输出表结构与计数，作为 battle.engine 的数据契约。
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import repo_dir, run  # noqa: E402


def _table_stats(db: Path) -> tuple[list[str], dict[str, int]]:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        tables = [r[0] for r in conn.execute(
            "select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")]
        counts = {t: conn.execute(f'select count(*) from "{t}"').fetchone()[0] for t in tables}
    finally:
        conn.close()
    return tables, counts


def body(result) -> None:
    repo = repo_dir("ColinHong10-NRC_AI")
    result.add("repo", True, repo.name)

    db = repo / "data" / "nrc.db"
    result.add("nrc_db", db.is_file(), f"{db.stat().st_size / 1024:.1f} KB" if db.is_file() else "缺失")
    if db.is_file():
        tables, counts = _table_stats(db)
        result.add("sqlite_readable", True, f"{len(tables)} 张表")
        result.add("pokemon_count", counts.get("pokemon", 0) >= 400, f"pokemon={counts.get('pokemon', 0)}")
        result.contract["dataset"] = {"tables": tables, "counts": counts}

    modules = sorted(p.stem for p in (repo / "src").glob("*.py"))
    result.add("src_modules", len(modules) > 10, f"{len(modules)} 个模块")
    result.contract.update(
        {
            "entrypoints": ["start.py", "run_web.py", "src/main.py", "src/server.py"],
            "modules": modules,
            "engine": {
                "battle": "src/battle.py",
                "mcts": "src/mcts.py",
                "team_builder": "src/team_builder.py",
                "damage": "src/effect_engine.py",
            },
            "db_path_policy": "sqlite 以只读 URI 打开 vendor/ColinHong10-NRC_AI/data/nrc.db",
            "rules_dataset": "vendor/Adolph321-Adolph/battle-rules-1-200-20261007/battle-rules-1-200",
        }
    )


if __name__ == "__main__":
    raise SystemExit(run("nrc_ai", "ColinHong10-NRC_AI", body))
