"""路径重定向：所有适配器只认 vendor 内路径，禁止泄漏工作目录外的绝对路径。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

VENDOR_ROOT = Path(__file__).resolve().parents[2]
ROCOGI_ROOT = VENDOR_ROOT.parent
UPSTREAM_ROOT = ROCOGI_ROOT.parent / "upstream"


def repo_dir(name: str) -> Path:
    """返回 vendor/<repo> 目录；不存在时抛出明确错误。"""
    path = VENDOR_ROOT / name
    if not path.is_dir():
        raise FileNotFoundError(f"vendor 内缺少仓库目录: {path}")
    return path


def ensure_within_vendor(path: Path) -> Path:
    """校验路径位于 vendor 内，防止适配器越界写入。"""
    resolved = path.resolve()
    if VENDOR_ROOT.resolve() not in resolved.parents and resolved != VENDOR_ROOT.resolve():
        raise PermissionError(f"越界路径: {resolved}")
    return resolved


def venv_python(engine: str) -> Path | None:
    """复用 suite 引擎的独立 venv 解释器（只读调用，不安装、不修改）。"""
    exe = ROCOGI_ROOT / "suite" / "engines" / engine / ".venv" / "Scripts" / "python.exe"
    return exe if exe.is_file() else None


def node_exe() -> Path | None:
    path = ROCOGI_ROOT / ".toolchain" / "node" / "node.exe"
    return path if path.is_file() else None


def portable_python() -> Path | None:
    matches = list((ROCOGI_ROOT / ".toolchain" / "python").glob("*/python.exe"))
    return matches[0] if matches else Path(sys.executable)


def which(name: str) -> str | None:
    for base in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(base) / f"{name}.exe"
        if candidate.is_file():
            return str(candidate)
    return None
