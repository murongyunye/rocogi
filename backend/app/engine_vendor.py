"""调用 suite 的 vendor 引擎，暴露上游适配器状态。

只读调用 ``suite/engines/vendor/engine_main.py``（rocogi 自己的引擎层），不修改
``vendor/`` 下的任何上游源码。vendor 引擎会实际执行
``vendor/adapters/<name>/adapter.py --json``；本模块只负责调用、解析事件与
归一化，不推测 adapter 状态。

如果 suite 引擎或其 venv 缺失，vendor 引擎会把错误写进 ``error`` 事件；本模块
原样返回 ``ok=false``，绝不伪造 ``adapted``。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "suite" / "engines" / "vendor" / "engine_main.py"

ACTIONS = (
    "status",
    "blocked",
    "rocopilot",
    "auto_rocokingdom",
    "luoke_location",
    "roco_map_tracker",
    "autocapture",
    "game_automation",
    "nrc_ai",
    "adolph_rules",
    "balance_lab",
)


def run_action(action: str, timeout: float = 300.0) -> Dict[str, Any]:
    """运行一次 vendor 引擎动作并返回其 ``result`` 事件。"""
    if action not in ACTIONS:
        raise ValueError(f"unknown vendor action: {action}")
    if not ENGINE.exists():
        raise RuntimeError(f"vendor engine not found: {ENGINE}")
    proc = subprocess.run(
        [sys.executable, str(ENGINE), "--config", "", "--action", action, "--once"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    result: Any = None
    error: str | None = None
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result":
            result = event.get("result")
        elif event.get("type") == "error":
            error = event.get("error")
    if result is None:
        detail = error or (proc.stderr or "").strip()[-400:] or f"vendor engine exit {proc.returncode}"
        return {"ok": False, "error": detail, "returncode": proc.returncode, "action": action}
    payload: Dict[str, Any] = dict(result) if isinstance(result, dict) else {"value": result}
    payload["ok"] = proc.returncode == 0
    payload["returncode"] = proc.returncode
    return payload
