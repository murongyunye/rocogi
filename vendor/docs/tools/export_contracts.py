"""把各适配器的 contract 导出为静态 JSON，便于其他模块只读消费（不依赖运行时）。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

VENDOR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VENDOR / "docs" / "tools"))
from verify_import import ADAPTERS, interpreter  # noqa: E402


def main() -> None:
    written = []
    for adapter, (engine, _repo) in ADAPTERS.items():
        script = VENDOR / "adapters" / adapter / "adapter.py"
        proc = subprocess.run([str(interpreter(engine)), str(script), "--json"], capture_output=True, text=True, timeout=600)
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            print(f"skip {adapter}: exit={proc.returncode} {(proc.stderr or proc.stdout)[:120]}")
            continue
        target = VENDOR / "adapters" / adapter / "contracts"
        target.mkdir(parents=True, exist_ok=True)
        (target / "adapter_contract.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        written.append(adapter)
    print(json.dumps({"contracts": len(written), "adapters": written}, ensure_ascii=False))


if __name__ == "__main__":
    main()
