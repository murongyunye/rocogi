#!/usr/bin/env python3
"""把「能自构建的东西」从版本库摘出去，只留源码与出处。

设计原则（对应 scripts/assets/manifest.json）：

  * 上游仓库（vendor/ 下 15 个）：`vendor/tools/fetch-upstream.ps1` 按固定 commit
    现取 → 不进版本库。
  * 构建产物（archive/release、release/）：`scripts/package-release.py` 重出
    → 不进版本库，本地也不留（省 1.8 GB）。
  * 第三方数据（bwiki / pvp 库、地图图标、游戏截图）：脚本能重建，且本来就不该
    随仓库分发 → 不进版本库，本地保留一份方便直接跑。
  * 取不回来的（sift-map-tracker 发布包、poi_legacy 快照）：**留在版本库里**，
    这是「资产保守」的落点 —— 删了就真没了。

跑法：`python scripts/trim-buildable.py --apply`（不带 --apply 只打印计划）。
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GIT = ROOT / ".toolchain" / "git" / "cmd" / "git.exe"

# 上游仓库：与 vendor/upstream_sources.json 的 repo 一一对应，拉取脚本能补齐。
UPSTREAM_REPOS = [
    "Adolph321-Adolph",
    "babalae-better-genshin-impact",
    "ColinHong10-NRC_AI",
    "eachyczhang-RocoTools",
    "ElliottZhao666666-rocom-codex-pets-gen",
    "Makapic-RocoPilot",
    "oblitum-Interception",
    "Pacific-shark-roco-balance-lab",
    "rookie-orange-rocokingdom-ui",
    "SCH-CMYK-game-automation",
    "Tsuann-RocoKingdom-AutoCapture",
    "Wooziii-roco-map-tracker",
    "yorusacri-Auto-rocokingdom",
    "yottaapp-yotta",
    "zh19990906-luoke_location",
]

# 从 index 摘掉、但工作树保留：直接能跑，需要时脚本重建。
UNTRACK_KEEP = [f"vendor/{name}" for name in UPSTREAM_REPOS] + [
    "datasets/bwiki/bwiki_battle.db",
    "datasets/bwiki/bwiki_battle.json",
    "datasets/bwiki/wiki",
    "datasets/bwiki/raw",
    "datasets/pvp/pvp_data.db",
    "datasets/map/icons",
    "docs/screenshots",
]

# 从 index 摘掉、工作树也删：脚本一秒重出，占 1.8 GB。
UNTRACK_DELETE = ["archive/release", "release"]


def git(*args: str) -> int:
    exe = str(GIT) if GIT.exists() else "git"
    return subprocess.run([exe, "-c", "core.quotepath=false", *args], cwd=ROOT).returncode


def dir_size(path: Path) -> float:
    if not path.exists():
        return 0.0
    if path.is_file():
        return path.stat().st_size / 1048576
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) / 1048576


def main() -> int:
    parser = argparse.ArgumentParser(description="摘掉可自构建的资产")
    parser.add_argument("--apply", action="store_true", help="真的执行（默认 dry-run）")
    args = parser.parse_args()

    targets = UNTRACK_KEEP + UNTRACK_DELETE
    freed = 0.0
    print("计划：")
    for rel in targets:
        path = ROOT / rel
        size = dir_size(path)
        action = "摘除并删除工作树" if rel in UNTRACK_DELETE else "摘除，保留工作树"
        freed += size if rel in UNTRACK_DELETE else 0
        print(f"  {size:>8.1f} MB  {action}  {rel}")
    print(f"\n删除后可释放 {freed:.1f} MB")

    if not args.apply:
        print("\n（dry-run；加 --apply 执行）")
        return 0

    for rel in targets:
        code = git("rm", "-r", "-q", "--cached", "--ignore-unmatch", "--", rel)
        print(f"  git rm --cached {rel} -> exit {code}")
    for rel in UNTRACK_DELETE:
        path = ROOT / rel
        if path.exists():
            subprocess.run(["attrib", "-R", "-S", "-H", "/S", "/D"], cwd=ROOT, capture_output=True)
            shutil.rmtree(path, ignore_errors=True)
            print(f"  删除 {rel}: {'还在' if path.exists() else '已删除'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
