"""统一的结构化输出与退出码：0=adapted，2=blocked。"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from typing import Any, Callable


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AdapterResult:
    adapter: str
    repo: str
    status: str = "adapted"
    checks: list[Check] = field(default_factory=list)
    contract: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str = "") -> "AdapterResult":
        self.checks.append(Check(name, ok, detail))
        return self

    def block(self, reason: str) -> "AdapterResult":
        self.status = "blocked"
        if reason not in self.blockers:
            self.blockers.append(reason)
        return self

    def as_dict(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "repo": self.repo,
            "status": self.status,
            "checks": [c.as_dict() for c in self.checks],
            "blockers": self.blockers,
            "contract": self.contract,
        }


def emit(result: AdapterResult, as_json: bool) -> int:
    payload = result.as_dict()
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"[{payload['status']}] {payload['repo']} -> {payload['adapter']}")
        for check in payload["checks"]:
            print(f"  {'OK ' if check['ok'] else 'FAIL'} {check['name']}: {check['detail']}")
        for reason in payload["blockers"]:
            print(f"  BLOCKED: {reason}")
        if payload["contract"]:
            print("  contract: " + json.dumps(payload["contract"], ensure_ascii=False)[:400])
    return 0 if result.status == "adapted" else 2


def run(adapter: str, repo: str, body: Callable[[AdapterResult], None], argv: list[str] | None = None) -> int:
    """标准入口：支持 --help / --json，默认干跑。"""
    args = sys.argv[1:] if argv is None else argv
    if "--help" in args or "-h" in args:
        print(f"adapter={adapter} repo={repo}")
        print("用法: python adapter.py [--json]")
        print("默认干跑，不写文件、不启动游戏、不安装依赖。")
        return 0
    result = AdapterResult(adapter=adapter, repo=repo)
    body(result)
    return emit(result, "--json" in args)
