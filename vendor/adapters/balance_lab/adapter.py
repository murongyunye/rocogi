"""roco-balance-lab 兼容层：Node 侧模拟引擎直接 import 干跑。

engine.mjs / data.mjs 是纯 ESM，无浏览器依赖，可直接用便携 Node 验证。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import node_exe, repo_dir, run  # noqa: E402

PROBE = """
Promise.all([import('./src/engine.mjs'), import('./src/data.mjs')]).then(([e, d]) => {
  console.log(JSON.stringify({
    engine_exports: Object.keys(e).sort(),
    roster: Object.keys(d.ROSTER || {}).length,
    moves: Object.keys(d.MOVES || {}).length,
    data_version: d.DATA_VERSION,
    rule_version: d.RULE_VERSION
  }));
}).catch(err => { console.error(String(err)); process.exit(3); });
"""


def body(result) -> None:
    repo = repo_dir("Pacific-shark-roco-balance-lab")
    result.add("repo", True, repo.name)

    node = node_exe()
    result.add("node", node is not None, str(node) if node else "未找到便携 node")
    if not node:
        result.block("缺 Node，无法干跑 engine.mjs")
        return

    # node 输出恒为 UTF-8；不显式指定编码时 Windows 会用本地 ANSI 代码页（cp936）解码，
    # 遇到非 GBK 字节序列会让 _readerthread 抛 UnicodeDecodeError，导致 stdout/stderr 为 None。
    proc = subprocess.run(
        [str(node), "-e", PROBE],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    result.add("engine_import", proc.returncode == 0, (proc.stderr or proc.stdout or "").strip()[:200])
    payload = {}
    if proc.returncode == 0:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])

    result.contract.update(
        {
            "language": "JavaScript (ESM) + React",
            "entrypoints": ["server.mjs", "scripts/experiment.mjs", "src/engine.mjs"],
            "engine_exports": payload.get("engine_exports", []),
            "dataset": {k: payload.get(k) for k in ("roster", "moves", "data_version", "rule_version")},
            "build_requirements": ["Node >=22.12", "pnpm 11.25（仅前端）"],
            "minimal_run_plan": "模拟可直接 node scripts/experiment.mjs；前端需 pnpm install + vite dev --port 4197",
        }
    )


if __name__ == "__main__":
    raise SystemExit(run("balance_lab", "Pacific-shark-roco-balance-lab", body))
