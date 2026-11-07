"""生成 vendor/manifest.json 与 vendor/docs/INVENTORY.md。

可重复执行：只读 upstream（取 commit）与 vendor（清点文件），只写 vendor/manifest.json
和 vendor/docs/INVENTORY.md 两个文件，不下载、不修改上游。
"""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

VENDOR = Path(__file__).resolve().parents[2]
UPSTREAM = VENDOR.parent.parent / "upstream"
GIT = VENDOR.parent / ".toolchain" / "git" / "cmd" / "git.exe"
EXCLUDE_DIRS = {".git", "__pycache__", ".venv"}

LICENSES = {
    "Adolph321-Adolph": "GPL-3.0",
    "babalae-better-genshin-impact": "GPL-3.0（子项目 Fischless.WindowsInput 为 MIT）",
    "ColinHong10-NRC_AI": "MIT",
    "eachyczhang-RocoTools": "CC BY-NC-SA 4.0",
    "ElliottZhao666666-rocom-codex-pets-gen": "MIT",
    "Makapic-RocoPilot": "MIT",
    "oblitum-Interception": "LGPL-3.0（非商用；商用需单独授权）",
    "Pacific-shark-roco-balance-lab": "MIT",
    "rookie-orange-rocokingdom-ui": "未声明（仓库无 LICENSE 文件）",
    "SCH-CMYK-game-automation": "CC BY-NC 4.0",
    "sift-map-tracker": "未声明（仅发布二进制，无 LICENSE 文件）",
    "Tsuann-RocoKingdom-AutoCapture": "未声明（仓库无 LICENSE 文件）",
    "Wooziii-roco-map-tracker": "未声明（README 声明第三方地图/图标权利保留）",
    "yorusacri-Auto-rocokingdom": "MIT",
    "yottaapp-yotta": "自定义非商用许可（个人/教育/研究免费，商用禁止）",
    "zh19990906-luoke_location": "未声明（README 要求遵守上游与原素材许可）",
}

ENTRYPOINTS = {
    "Adolph321-Adolph": ["battle-rules-1-200-20261007/battle-rules-1-200/verify.js", "battle-rules-1-200-20261007/battle-rules-1-200/index.js"],
    "babalae-better-genshin-impact": ["BetterGenshinImpact.sln", "BetterGenshinImpact/Program.cs"],
    "ColinHong10-NRC_AI": ["start.py", "run_web.py", "src/main.py", "src/server.py"],
    "eachyczhang-RocoTools": ["app/server/src/index.js", "app/client/src/main.js", "crawler"],
    "ElliottZhao666666-rocom-codex-pets-gen": ["scripts/validate_input.py", "scripts/render_source.py", "scripts/normalize_frames.py"],
    "Makapic-RocoPilot": ["main.py", "config.py"],
    "oblitum-Interception": ["library/interception.h", "samples"],
    "Pacific-shark-roco-balance-lab": ["server.mjs", "src/engine.mjs", "scripts/experiment.mjs"],
    "rookie-orange-rocokingdom-ui": ["package.json", "packages/tokens/src/index.ts", "packages/ui/src/index.ts"],
    "SCH-CMYK-game-automation": ["main.py", "run.bat", "src/engine/controller.py"],
    "sift-map-tracker": ["SiftMapTracker.Client.exe", "sift-map-tracker/service/service.exe", "sift-map-tracker/settings.py"],
    "Tsuann-RocoKingdom-AutoCapture": ["main.py", "config.yaml", "models/sprite_detector.onnx"],
    "Wooziii-roco-map-tracker": ["roco-map-tracker/main.py", "roco-map-tracker/service_main.py", "roco-map-tracker/tracker/engines/sift_engine.py"],
    "yorusacri-Auto-rocokingdom": ["main.py", "client_main.py", "core/engine.py"],
    "yottaapp-yotta": ["main.go", "cmd/node-catalog/main.go", "contracts/node/v2/builtin-catalog.json", "frontend/package.json"],
    "zh19990906-luoke_location": ["main_sift.py", "main_ai.py", "data/points_data.json"],
}

BUILD_REQUIREMENTS = {
    "Adolph321-Adolph": ["Node 22+（仅 verify.js）", "无编译产物"],
    "babalae-better-genshin-impact": [".NET 8 SDK", "NuGet 联网还原", "Windows 10/11 + WPF"],
    "ColinHong10-NRC_AI": ["Python 3.11+", "fastapi/uvicorn/pandas/openpyxl", "data/nrc.db（已随仓库）"],
    "eachyczhang-RocoTools": ["Node 20+ / npm", "better-sqlite3、sharp 预编译二进制", "实际图鉴数据（缺失）"],
    "ElliottZhao666666-rocom-codex-pets-gen": ["Python 3.11+", "Pillow>=11、imageio-ffmpeg", "外部资源目录 + rocom-pets 1.14.2"],
    "Makapic-RocoPilot": ["Python 3.11+", "opencv-python、numpy、mss、pygetwindow", "ultralytics(torch) 可选", "interception-python（缺驱动时回退 SendInput）"],
    "oblitum-Interception": ["MSVC 或 MinGW", "WDK 签名 + 管理员安装内核驱动"],
    "Pacific-shark-roco-balance-lab": ["Node >=22.12", "pnpm（仅前端）"],
    "rookie-orange-rocokingdom-ui": ["Node >=22.12", "pnpm 11.5.3", "vite-plus catalog 依赖"],
    "SCH-CMYK-game-automation": ["Python 3.11+", "torch/torchvision/ultralytics/kornia", "opencv-python、customtkinter、mss", "interception-python + 驱动"],
    "sift-map-tracker": ["Windows x64", "无构建（发布包已含 exe）"],
    "Tsuann-RocoKingdom-AutoCapture": ["Python 3.11+", "opencv-python、onnxruntime、PyYAML", "RKNN 仅 RK3588 需要"],
    "Wooziii-roco-map-tracker": ["Python 3.11+", "opencv-python、numpy、mss、Pillow、PySide6、requests"],
    "yorusacri-Auto-rocokingdom": ["Python 3.11+", "opencv-python、numpy、mss、pygetwindow(pywin32)"],
    "yottaapp-yotta": ["Go 1.25（go.mod 声明）", "Wails + WebView2", "Node 22.12+ / npm"],
    "zh19990906-luoke_location": ["Python 3.11+", "opencv-python、numpy、PySide6", "data 地图资源（已随仓库含 dist）"],
}

SOURCE_EXTS = {".py", ".c", ".h", ".cpp", ".hpp", ".cs", ".go", ".ts", ".tsx", ".js", ".mjs", ".vue", ".sh", ".ps1", ".bat"}


def files_under(root: Path, skip: set[str] = EXCLUDE_DIRS) -> list[Path]:
    out = []
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if any(part in skip for part in rel.parts):
            continue
        if path.is_file():
            out.append(rel)
    return out


def commit_of(repo: str) -> str | None:
    src = UPSTREAM / repo
    if not (src / ".git").exists() or not GIT.exists():
        return None
    proc = subprocess.run([str(GIT), "-C", str(src), "rev-parse", "HEAD"], capture_output=True, text=True)
    return proc.stdout.strip() or None


def language_summary(rels: list[Path]) -> dict[str, int]:
    counts = Counter(p.suffix.lower() for p in rels if p.suffix.lower() in SOURCE_EXTS)
    mapping = {".py": "Python", ".c": "C", ".h": "C/C++ header", ".cpp": "C++", ".cs": "C#", ".go": "Go",
               ".ts": "TypeScript", ".tsx": "TypeScript/TSX", ".js": "JavaScript", ".mjs": "JavaScript",
               ".vue": "Vue", ".sh": "Shell", ".ps1": "PowerShell", ".bat": "Batch"}
    merged: Counter = Counter()
    for ext, n in counts.items():
        merged[mapping.get(ext, ext)] += n
    return dict(merged.most_common())


def main() -> None:
    repos = sorted(p.name for p in VENDOR.iterdir() if p.is_dir() and p.name not in {"adapters", "docs", "patches"})
    imported_at = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    entries = []
    for repo in repos:
        vendor_dir = VENDOR / repo
        upstream_dir = UPSTREAM / repo
        vrels = files_under(vendor_dir)
        urels = files_under(upstream_dir) if upstream_dir.exists() else []
        missing = sorted(str(p) for p in set(urels) - set(vrels))
        extra = sorted(str(p) for p in set(vrels) - set(urels))
        size = sum((vendor_dir / p).stat().st_size for p in vrels)
        entries.append({
            "repo": repo,
            "commit": commit_of(repo),
            "license": LICENSES.get(repo, "未声明"),
            "languages": language_summary(vrels),
            "size": {"files": len(vrels), "bytes": size, "megabytes": round(size / 1024 / 1024, 2)},
            "entrypoints": ENTRYPOINTS.get(repo, []),
            "build_requirements": BUILD_REQUIREMENTS.get(repo, []),
            "imported_at": imported_at,
            "completeness": {
                "status": "complete" if not missing else "partial",
                "upstream_files": len(urels),
                "vendor_files": len(vrels),
                "missing": missing,
                "extra_generated": extra,
                "compared_excluding": sorted(EXCLUDE_DIRS),
            },
        })

    manifest = {
        "generated_at": imported_at,
        "source_root": "work/upstream",
        "vendor_root": "work/rocogi/vendor",
        "repo_count": len(entries),
        "total_bytes": sum(e["size"]["bytes"] for e in entries),
        "repos": entries,
    }
    (VENDOR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# vendor 上游源码清单",
        "",
        f"- 生成时间：{imported_at}",
        f"- 仓库数：{len(entries)}；总体积：{manifest['total_bytes'] / 1024 / 1024 / 1024:.2f} GB",
        "- 比对口径：排除 `.git`、`__pycache__`、`.venv`，逐文件路径比对",
        "",
        "| 仓库 | commit | 语言 | 许可证 | 文件数 | 体积 | 完整度 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for e in entries:
        langs = ", ".join(f"{k}({v})" for k, v in list(e["languages"].items())[:3]) or "-"
        lines.append(
            f"| {e['repo']} | `{(e['commit'] or 'n/a')[:7]}` | {langs} | {e['license']} | "
            f"{e['size']['files']} | {e['size']['megabytes']} MB | {e['completeness']['status']} |"
        )
    lines += ["", "## 入口与构建要求", ""]
    for e in entries:
        lines.append(f"### {e['repo']}")
        lines.append(f"- 入口：{', '.join(f'`{p}`' for p in e['entrypoints']) or '见 `build`/`package` 清单'}")
        lines.append(f"- 构建：{'; '.join(e['build_requirements'])}")
        if e["completeness"]["missing"]:
            lines.append(f"- 缺失：{', '.join(e['completeness']['missing'])}")
        lines.append("")
    (VENDOR / "docs" / "INVENTORY.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"repos": len(entries), "bytes": manifest["total_bytes"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
