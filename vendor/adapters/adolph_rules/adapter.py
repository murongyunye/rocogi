"""Adolph321 对战规则数据集兼容层：用 Node 验证数据集完整性，并导出规则索引契约。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import node_exe, repo_dir, run  # noqa: E402

BUNDLE = "battle-rules-1-200-20261007/battle-rules-1-200"


def body(result) -> None:
    repo = repo_dir("Adolph321-Adolph")
    result.add("repo", True, repo.name)
    bundle = repo / BUNDLE
    result.add("bundle", bundle.is_dir(), BUNDLE)

    node = node_exe()
    result.add("node", node is not None, str(node) if node else "未找到便携 node")
    if node:
        proc = subprocess.run(
            [str(node), "verify.js"], cwd=str(bundle), capture_output=True, text=True, timeout=180
        )
        result.add("verify_js", proc.returncode == 0, (proc.stdout or proc.stderr).strip().splitlines()[-1] if (proc.stdout or proc.stderr) else "")
    else:
        result.block("缺 Node，无法执行 verify.js")

    pets = json.loads((bundle / "data" / "pets.json").read_text(encoding="utf-8"))
    skills = json.loads((bundle / "data" / "skills.json").read_text(encoding="utf-8"))
    traits = json.loads((bundle / "data" / "traits.json").read_text(encoding="utf-8"))
    rule_index = json.loads((bundle / "rule-index.json").read_text(encoding="utf-8"))
    result.add("pets", len(pets) == 200, f"{len(pets)} 条")
    result.add("skills", len(skills) == 200, f"{len(skills)} 条")
    result.add("traits", len(traits) > 0, f"{len(traits)} 条")

    result.contract.update(
        {
            "bundle": BUNDLE,
            "counts": {"pets": len(pets), "skills": len(skills), "traits": len(traits)},
            "rule_index_keys": sorted(rule_index.keys()),
            "schema": {
                "pet": sorted(pets[0].keys()) if pets else [],
                "skill": sorted(skills[0].keys()) if skills else [],
            },
            "license": "GPL-3.0",
            "usage": "只作为 battle.damage_model 的规则数据源，按进程隔离使用，不与 GPL 代码静态链接",
        }
    )


if __name__ == "__main__":
    raise SystemExit(run("adolph_rules", "Adolph321-Adolph", body))
