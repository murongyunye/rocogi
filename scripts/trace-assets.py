#!/usr/bin/env python3
"""自追溯：现场验证 manifest 里每条资产的来源是否真的可获取。

为什么要有这个脚本：仓库为了体积与合规把 vendor/、模型权重、构建产物挪出了
版本库。挪出去的前提是「能从上游重新拿到」——这个前提不能靠记忆，得每次现查。
脚本按 kind 用不同方式验证：

  git-repo         codeload tar.gz @ 固定 commit 是否 200
  repo-file        raw.githubusercontent @ commit/HEAD 上该文件是否 200
  built-artifact   本项目的重建脚本是否存在（不联网）
  generated        生成入口是否存在（不联网）
  local-only       只发二进制的发布包，没有公开源，仅本地留存
  rights-excluded  第三方游戏素材，永远排除，不探测

用法:
    python scripts/trace-assets.py --check           # 体检，只读
    python scripts/trace-assets.py --check --json > trace.json
    python scripts/trace-assets.py --fetch vendor/ColinHong10-NRC_AI
    python scripts/trace-assets.py --fetch all       # 按 fetched_by 逐条重建
    python scripts/trace-assets.py --report docs/reports/asset-trace.md
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "scripts" / "assets" / "manifest.json"
UA = {"User-Agent": "rocogi-asset-trace/1.0"}


def head(url: str, retries: int = 2) -> tuple[int, str]:
    """返回 (status, 说明)。404/410 表示上游确实没有，5xx 和超时单独标注。"""
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers=UA, method="HEAD")
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                return resp.status, ""
        except urllib.error.HTTPError as exc:
            if attempt == retries:
                return exc.code, f"HTTP {exc.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == retries:
                return 0, f"{exc.__class__.__name__}: {exc}"
        time.sleep(1.5)
    return 0, "unreachable"


def probe(entry: dict) -> dict:
    kind = entry["kind"]
    src = entry.get("source") or {}
    result = {"name": entry["name"], "kind": kind, "ok": None, "detail": "", "url": None}

    if kind == "git-repo":
        repo, commit = src.get("repo"), src.get("commit")
        if not repo or not commit:
            result.update(ok=False, detail="清单缺 repo/commit")
            return result
        url = f"https://codeload.github.com/{repo}/tar.gz/{commit}"
        status, note = head(url)
        result.update(ok=status == 200, url=url, detail=note or f"HTTP {status}")
        return result

    if kind == "repo-file":
        repo, path = src.get("repo"), src.get("path")
        ref = src.get("commit") or "HEAD"
        if not repo or not path:
            result.update(ok=False, detail="清单缺 repo/path")
            return result
        url = f"https://raw.githubusercontent.com/{repo}/{ref}/{urllib.parse.quote(path)}"
        status, note = head(url)
        result.update(ok=status == 200, url=url, detail=note or f"HTTP {status}")
        return result

    if kind in ("built-artifact", "generated"):
        # rebuild 里可能是一行命令，也可能是一句人话（例如「backend/app/adapters/
        # sift.py 首次定位时按 logic map 现算」）。两种都支持：先把里的脚本路径
        # 挑出来，任何一个存在就算这条能重建。
        cmd = src.get("rebuild") or ""
        candidates = []
        for token in cmd.replace("`", " ").split():
            cleaned = token.strip("（）()，,。；;:")
            if cleaned.endswith((".py", ".ps1", ".mjs", ".js", ".html", ".toml", ".json")):
                candidates.append(cleaned)
        hit = next((c for c in candidates if (ROOT / c.replace("\\", "/")).exists()), None)
        if hit:
            result.update(ok=True, detail=f"{cmd}（脚本 {hit} 在）")
        elif candidates:
            result.update(ok=False, detail=f"{cmd}（脚本 {'/'.join(candidates)} 都不在）")
        else:
            result.update(ok=False, detail="没有登记可执行的重建入口")
        return result

    if kind == "local-only":
        result.update(ok=None, detail="来自只发二进制的发布包，没有公开源；本地副本是唯一来源")
        return result

    result.update(ok=None, detail="第三方素材，按策略永久排除")
    return result


def fetch(entry: dict) -> int:
    cmd = entry.get("fetched_by")
    if not cmd:
        print(f"  {entry['name']}: 没有登记获取命令，跳过")
        return 1
    if cmd.endswith(".ps1 -Repo <name>"):
        name = entry["name"].split("/", 1)[1]
        cmd = cmd.replace("<name>", name)
    print(f"  {entry['name']}: {cmd}")
    if cmd.endswith(".ps1"):
        argv = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", cmd]
    else:
        argv = cmd.split()
    return subprocess.call(argv, cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="自追溯：验证资产来源是否可获取")
    parser.add_argument("--check", action="store_true", help="只体检（默认行为）")
    parser.add_argument("--fetch", metavar="NAME", help="按名字重建一条，或 all")
    parser.add_argument("--json", action="store_true", help="机器可读输出")
    parser.add_argument("--report", metavar="PATH", help="同时写一份 markdown 报告")
    args = parser.parse_args()

    if not MANIFEST.exists():
        print(f"找不到清单: {MANIFEST}", file=sys.stderr)
        return 2
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = manifest["entries"]

    if args.fetch:
        targets = entries if args.fetch == "all" else [e for e in entries if e["name"] == args.fetch]
        if not targets:
            print(f"清单里没有 {args.fetch}", file=sys.stderr)
            return 2
        failures = 0
        for entry in targets:
            failures += 1 if fetch(entry) else 0
        return 1 if failures else 0

    results = [probe(entry) for entry in entries]
    obtainable = [r for r in results if r["ok"] is True]
    blocked = [r for r in results if r["ok"] is False]
    excluded = [r for r in results if r["ok"] is None]

    if args.json:
        print(json.dumps({"manifest": str(MANIFEST), "results": results}, ensure_ascii=False, indent=2))
    else:
        print(f"资产追溯 -- {MANIFEST}")
        for r in results:
            tag = "[ ok ]" if r["ok"] else ("[skip]" if r["ok"] is None else "[miss]")
            print(f"{tag} {r['name']:<48} {r['detail']}")
        print()
        print(f"可获取 {len(obtainable)} / 不可获取 {len(blocked)} / 按策略排除 {len(excluded)}")

    if args.report:
        path = ROOT / args.report
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# 资产追溯报告",
            "",
            f"清单：`{MANIFEST.relative_to(ROOT).as_posix()}`（{len(entries)} 条）",
            "",
            "| 资产 | 类型 | 可获取 | 依据 |",
            "| --- | --- | --- | --- |",
        ]
        for r in results:
            state = "是" if r["ok"] else ("排除" if r["ok"] is None else "**否**")
            detail = (r["detail"] or "").replace("|", "\\|")
            lines.append(f"| `{r['name']}` | {r['kind']} | {state} | {detail} |")
        lines += ["", f"合计：可获取 {len(obtainable)}，不可获取 {len(blocked)}，排除 {len(excluded)}。", ""]
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"报告已写入 {path}")

    return 0 if not blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
