#!/usr/bin/env python3
"""按目录统计 git 跟踪体积，顺带列出最大的若干文件。

做体积决策时最怕凭印象。这个脚本直接问 index：每个顶层目录里跟踪了多少文件、
多少字节，最大的 20 个文件是谁。`--prefix` 可以下钻到子目录。

用法:
    python scripts/report-tree-size.py
    python scripts/report-tree-size.py --prefix datasets
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GIT = ROOT / ".toolchain" / "git" / "cmd" / "git.exe"


def git(*args: str) -> str:
    exe = str(GIT) if GIT.exists() else "git"
    return subprocess.run(
        [exe, "-c", "core.quotepath=false", *args],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    ).stdout


def rows() -> list[tuple[int, str]]:
    # 用 -z：上游有个文件名里带换行，按行切会把那条记录劈成两半。
    out = []
    for record in git("ls-tree", "-r", "-l", "-z", "HEAD").split("\0"):
        if not record:
            continue
        meta, path = record.split("\t", 1)
        out.append((int(meta.split()[3]), path))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="git 跟踪体积统计")
    parser.add_argument("--prefix", default="", help="只看某个前缀下的内容")
    parser.add_argument("--top", type=int, default=12, help="列出最大的 N 个文件")
    args = parser.parse_args()

    entries = rows()
    if args.prefix:
        prefix = args.prefix.rstrip("/") + "/"
        entries = [e for e in entries if e[1].startswith(prefix)]
        depth = len(prefix.split("/"))
        label = lambda p: "/".join(p.split("/")[: depth + 1])  # noqa: E731
    else:
        label = lambda p: p.split("/")[0]  # noqa: E731

    files, total = Counter(), Counter()
    for size, path in entries:
        files[label(path)] += 1
        total[label(path)] += size

    print(f"跟踪 {len(entries)} 个文件，合计 {sum(s for s, _ in entries) / 1048576:.1f} MB")
    for name, size in total.most_common():
        print(f"  {name:<40} {files[name]:>6} 个 {size / 1048576:>10.1f} MB")

    biggest = sorted(entries, key=lambda e: -e[0])[: args.top]
    if biggest:
        print(f"\n最大的 {len(biggest)} 个文件：")
        for size, path in biggest:
            print(f"  {size / 1048576:>9.2f} MB  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
