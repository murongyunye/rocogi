"""从现有清单生成 scripts/assets/manifest.json（资产来源总表）。

来源三处，都是本机已有的事实记录，不靠回忆：
  vendor/upstream_sources.json        16 个上游仓的 repo + commit + license
  datasets/models/upstream/MANIFEST.json   模型权重的 repo + path + sha256
  archive/sift-map-tracker/build-manifest.json  SIFT 客户端的构建身份

条目分五类 kind，决定 trace-assets.py 怎么验证：
  git-repo         codeload tar.gz @ commit 可取
  repo-file        raw.githubusercontent @ commit 可取
  built-artifact   本项目自己构建的产物，用 package-release.py 重建
  generated        本机从数据生成（SIFT 特征缓存、地图渲染），有生成脚本
  rights-excluded  第三方游戏素材，不可获取，永久排除
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "scripts" / "assets" / "manifest.json"


def load(path: Path, **kwargs):
    return json.loads(path.read_text(encoding="utf-8"), **kwargs)


def main() -> int:
    entries: list[dict] = []

    # --- 1. vendor 上游仓 ---------------------------------------------------
    sources = load(ROOT / "vendor" / "upstream_sources.json")
    skip = {"sift-map-tracker"}  # 只发布二进制、无 git 仓，单独处理
    for repo in sources["repos"]:
        name = repo["repo"]
        if name in skip:
            continue
        local = ROOT / "vendor" / name
        size = sum(p.stat().st_size for p in local.rglob("*") if p.is_file()) if local.exists() else 0
        entries.append({
            "name": f"vendor/{name}",
            "kind": "git-repo",
            "local": [f"vendor/{name}"],
            "source": {"repo": repo["upstream_url"].removeprefix("https://github.com/").removesuffix(".git"),
                       "commit": repo["commit"]},
            "license": repo.get("license"),
            "bytes": size,
            "fetched_by": "vendor/tools/fetch-upstream.ps1 -Repo <name>",
            "notes": repo.get("local_state", ""),
        })

    # --- 2. SIFT Map Tracker（上游只有二进制发布，无源码仓） ----------------
    sift_build = load(ROOT / "archive" / "sift-map-tracker" / "build-manifest.json", parse_constant=str)
    sift_local = ROOT / "archive" / "sift-map-tracker"
    sift_size = sum(p.stat().st_size for p in sift_local.rglob("*") if p.is_file()) if sift_local.exists() else 0
    entries.append({
        "name": "archive/sift-map-tracker",
        "kind": "rights-excluded",
        "local": ["archive/sift-map-tracker", "vendor/sift-map-tracker"],
        "source": {"repo": None, "commit": None,
                   "client_commit": sift_build.get("client", {}).get("commit"),
                   "tracker_commit": sift_build.get("tracker", {}).get("commit"),
                   "product_version": sift_build.get("version")},
        "license": "未声明（仅发布二进制，无 LICENSE）",
        "bytes": sift_size,
        "notes": "上游无公开源码仓，无 URL 可追溯；本地副本是唯一来源，因此保留",
    })

    # --- 3. 模型权重 -------------------------------------------------------
    weights = load(ROOT / "datasets" / "models" / "upstream" / "MANIFEST.json")
    for w in weights["weights"]:
        local = ROOT / "datasets" / "models" / "upstream" / w["file"]
        repo = w["repo"]
        # MANIFEST 里的 repo 有的是「SIFT-Map-Tracker v0.10.2 merged (...)」这种
        # 描述串，来自只发二进制的发布包，没有公开仓可查 —— 单独标 local-only，
        # 免得追溯脚本拿它去拼 URL。
        has_repo = repo.count("/") == 1 and " " not in repo and "(" not in repo
        path = w["path"].split(" ")[0]
        has_path = has_repo and path not in ("release", "")
        entries.append({
            "name": f"datasets/models/upstream/{w['file']}",
            "kind": "repo-file" if has_path else "local-only",
            "local": [f"datasets/models/upstream/{w['file']}"],
            "source": {"repo": repo if has_repo else None,
                       "commit": None,
                       "path": path if has_path else None,
                       "sha256": w.get("sha256_actual"), "bytes": w.get("bytes")},
            "license": w.get("license"),
            "bytes": local.stat().st_size if local.exists() else (w.get("bytes") or 0),
            "fetched_by": "datasets/tools/fetch_upstream.py weights" if has_path else None,
            "notes": w.get("desc", "") if has_path else f"来自发布包 {repo}，无公开源",
        })

    # --- 4. 本地生成 / 自己构建 -------------------------------------------
    entries.append({
        "name": "datasets/models/upstream/SIFT_features*.npz",
        "kind": "local-only",
        "local": ["datasets/models/upstream/SIFT_features.npz",
                  "datasets/models/upstream/SIFT_features_075.npz"],
        "source": {"repo": None, "commit": None, "path": None},
        "license": "未声明（随 SIFT-Map-Tracker v0.10.2 发布包分发）",
        "bytes": 0,
        "notes": "特征缓存来自只发二进制的发布包；suite/assets/build.py 只做拷贝与清单，不能凭空重算",
    })
    entries.append({
        "name": "archive/release",
        "kind": "built-artifact",
        "local": ["archive/release"],
        "source": {"rebuild": "python scripts/package-release.py --all"},
        "license": "本项目构建产物",
        "bytes": 0,
        "notes": "0.4.1 的 full 包分片，纯历史构建，脚本可重出",
    })
    entries.append({
        "name": "release/",
        "kind": "built-artifact",
        "local": ["release"],
        "source": {"rebuild": "python scripts/package-release.py --mode lite"},
        "license": "本项目构建产物",
        "bytes": 0,
    })
    entries.append({
        "name": "docs/screenshots",
        "kind": "built-artifact",
        "local": ["docs/screenshots"],
        "source": {"rebuild": "node scripts/verify/make-shots.mjs"},
        "license": "截图内含游戏画面，只本地留存",
        "bytes": 0,
    })
    entries.append({
        "name": "webui",
        "kind": "generated",
        "local": ["webui"],
        "source": {"rebuild": "webui/index.html 静态文件，无构建步骤；server.py 直接托管"},
        "license": "本项目（配色参考 vendor/rookie-orange-rocokingdom-ui，代码独立）",
        "bytes": 0,
    })

    # --- 5. 明确排除的第三方游戏素材 ---------------------------------------
    for name, paths, note in [
        ("datasets/map/icons", ["datasets/map/icons", "data/map/icons"], "游戏物品图标，权利不属本项目"),
        ("datasets/bwiki/*.db", ["datasets/bwiki"], "BWIKI 抓取数据，脚本可重建但不入库"),
        ("datasets/pvp/*.db", ["datasets/pvp"], "社区 PvP 数据集，脚本可重建但不入库"),
    ]:
        entries.append({
            "name": name, "kind": "rights-excluded", "local": paths,
            "source": {"rebuild": None}, "license": "第三方", "bytes": 0, "notes": note,
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "schema": 1,
        "generatedAt": "2026-11-08",
        "note": "本表只登记「从哪儿来、怎么验证」，不存内容。trace-assets.py 读它做现场探测。",
        "entries": entries,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT} with {len(entries)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
