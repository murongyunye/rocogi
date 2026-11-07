"""Interception 兼容层：导出 C API 契约，不编译、不安装驱动。

驱动安装需要管理员权限与重启，且会改动系统，不在本轮范围。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import repo_dir, run  # noqa: E402


def body(result) -> None:
    repo = repo_dir("oblitum-Interception")
    result.add("repo", True, repo.name)

    header = repo / "library" / "interception.h"
    text = header.read_text(encoding="utf-8", errors="ignore")
    functions = re.findall(
        r"\bINTERCEPTION_API\s+(interception_\w+)\s*\(\s*([^;]*?)\s*\)\s*;|"
        r"\b[\w\s\*]+?\sINTERCEPTION_API\s+(interception_\w+)\s*\(\s*([^;]*?)\s*\)\s*;",
        text,
        re.S,
    )
    names = sorted({n for row in functions for n in (row[0], row[2]) if n})
    result.add("header", header.is_file() and bool(names), f"{len(names)} 个导出函数")

    enums = re.findall(r"enum\s+(Interception\w+)\s*\{", text)
    result.add("enums", bool(enums), ", ".join(enums))

    samples = sorted(p.name for p in (repo / "samples").iterdir() if p.is_dir())
    result.add("samples", True, ", ".join(samples))

    licenses = sorted(str(p.relative_to(repo)) for p in (repo / "licenses").rglob("*.txt"))
    result.add("license", bool(licenses), ", ".join(licenses))

    result.contract.update(
        {
            "exported_functions": names,
            "enums": enums,
            "samples": samples,
            "license": "LGPL-3.0（非商用）/ 商用需单独许可",
            "build_requirements": [".NET Framework 4.x 或 MSVC + Windowed driver kit", "WDK 签名与管理员安装"],
            "integration_plan": "保留 C 头文件供 backend-c 动态加载 interception.dll；驱动未安装时回退 SendInput",
        }
    )
    result.block("驱动安装需要管理员权限 + 重启 + 内核签名，本轮不执行；只导出 API 契约")


if __name__ == "__main__":
    raise SystemExit(run("interception", "oblitum-Interception", body))
