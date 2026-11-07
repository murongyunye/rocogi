# -*- coding: utf-8 -*-
"""Toolchain fallback：把便携 Python 落到 .toolchain，并下载 uv.exe。

仓库只带脚本、不带 toolchain（.toolchain/ 在 .gitignore 里）。这个脚本是
scripts/bootstrap.ps1 的兜底：优先从本机 DSH 运行时里的同版本 Python 复制
（离线可用），找不到就提示用户去装。

用法：
    python scripts/fetch_toolchain.py
    python scripts/fetch_toolchain.py --from "D:\\python312"   # 指定源目录

环境变量 ROCOGI_BUNDLED_PYTHON 可覆盖默认的 DSH 运行时路径。
"""
from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYDIR = ROOT / ".toolchain" / "python" / "cpython-3.12.16-windows-x86_64-none"
UVDIR = ROOT / ".toolchain" / "uv"
DEFAULT_BUNDLED = Path(
    os.environ.get(
        "ROCOGI_BUNDLED_PYTHON",
        r"C:\Users\13005\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python",
    )
)
UV_URL = "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "rocogi-toolchain"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        return resp.read()


def ensure_python(source: Path) -> bool:
    target = PYDIR / "python.exe"
    if target.exists():
        print(f"python 已就位: {target}")
    else:
        if not (source / "python.exe").exists():
            print(
                f"找不到可复制的 Python: {source}\n"
                "请用 --from 指定一个 Python 3.12 目录，或安装 Python 后重试。",
                file=sys.stderr,
            )
            return False
        print(f"复制 {source} -> {PYDIR}")
        PYDIR.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, PYDIR, dirs_exist_ok=True)
    out = subprocess.run([str(target), "-V"], capture_output=True, text=True)
    print("version:", out.stdout.strip() or out.stderr.strip())
    return True


def ensure_uv() -> bool:
    exe = UVDIR / "uv.exe"
    if not exe.exists():
        print("下载", UV_URL)
        buf = io.BytesIO(fetch(UV_URL))
        UVDIR.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
            for name in ("uv.exe", "uvx.exe"):
                src = next(
                    (n for n in names if n.replace("\\", "/").endswith("/" + name) or n == name),
                    None,
                )
                if src is None:
                    print("压缩包里没有", name, "前几项:", names[:10])
                    continue
                (UVDIR / name).write_bytes(zf.read(src))
    out = subprocess.run([str(exe), "--version"], capture_output=True, text=True)
    print("uv:", out.stdout.strip() or out.stderr.strip())
    return exe.exists()


def main() -> int:
    parser = argparse.ArgumentParser(description="准备便携 toolchain")
    parser.add_argument("--from", dest="source", default=str(DEFAULT_BUNDLED),
                        help="复制哪个 Python 目录（默认 DSH 运行时）")
    args = parser.parse_args()

    ok_py = ensure_python(Path(args.source))
    ok_uv = ensure_uv()
    print("TOOLCHAIN", "READY" if (ok_py and ok_uv) else "INCOMPLETE")
    return 0 if (ok_py and ok_uv) else 1


if __name__ == "__main__":
    raise SystemExit(main())
