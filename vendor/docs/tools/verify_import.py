"""vendor 导入自检：逐仓文件比对、许可证存在性、绝对路径/令牌扫描、适配层干跑。

只读 vendor 与 upstream，输出 vendor/docs/import_selfcheck.json。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

VENDOR = Path(__file__).resolve().parents[2]
UPSTREAM = VENDOR.parent.parent / "upstream"
ROCOGI = VENDOR.parent
PORTABLE = next((ROCOGI / ".toolchain" / "python").glob("*/python.exe"))

EXCLUDE_DIRS = {".git", "__pycache__", ".venv"}
ADAPTERS = {
    "rocopilot": ("capture", "Makapic-RocoPilot"),
    "auto_rocokingdom": ("capture", "yorusacri-Auto-rocokingdom"),
    "luoke_location": ("sift", "zh19990906-luoke_location"),
    "roco_map_tracker": ("sift", "Wooziii-roco-map-tracker"),
    "autocapture": ("scheduler", "Tsuann-RocoKingdom-AutoCapture"),
    "game_automation": ("scheduler", "SCH-CMYK-game-automation"),
    "nrc_ai": ("portable", "ColinHong10-NRC_AI"),
    "pets_gen": ("vision", "ElliottZhao666666-rocom-codex-pets-gen"),
    "adolph_rules": ("portable", "Adolph321-Adolph"),
    "sift_map_tracker": ("portable", "sift-map-tracker"),
    "interception": ("portable", "oblitum-Interception"),
    "bettergi": ("portable", "babalae-better-genshin-impact"),
    "yotta": ("portable", "yottaapp-yotta"),
    "rocokingdom_ui": ("portable", "rookie-orange-rocokingdom-ui"),
    "rocotools": ("portable", "eachyczhang-RocoTools"),
    "balance_lab": ("portable", "Pacific-shark-roco-balance-lab"),
}
TEXT_EXTS = {".py", ".json", ".toml", ".yaml", ".yml", ".md", ".txt", ".ps1", ".sh", ".bat", ".ts", ".tsx", ".js", ".mjs", ".vue", ".cs", ".go", ".c", ".h", ".cpp"}
TOKEN_PATTERNS = [re.compile(p) for p in (r"ghp_[A-Za-z0-9]{20,}", r"github_pat_[A-Za-z0-9_]{20,}", r"sk-[A-Za-z0-9]{20,}", r"AKIA[0-9A-Z]{16}")]


def files(root: Path, skip: set[str] = EXCLUDE_DIRS) -> set[str]:
    return {
        str(p.relative_to(root))
        for p in root.rglob("*")
        if p.is_file() and not any(part in skip for part in p.relative_to(root).parts)
    }


def interpreter(engine: str) -> Path:
    if engine == "portable":
        return PORTABLE
    exe = ROCOGI / "suite" / "engines" / engine / ".venv" / "Scripts" / "python.exe"
    return exe if exe.exists() else PORTABLE


def main() -> None:
    report = {"file_compare": {}, "licenses": {}, "absolute_path_hits": [], "token_files": [], "adapters": {}}

    for repo in sorted(p.name for p in VENDOR.iterdir() if p.is_dir() and p.name not in {"adapters", "docs", "patches"}):
        v, u = files(VENDOR / repo), files(UPSTREAM / repo)
        report["file_compare"][repo] = {"missing": sorted(u - v), "extra": sorted(v - u), "upstream": len(u), "vendor": len(v)}
        lic = sorted(p.name for p in (VENDOR / repo).glob("*") if re.match(r"(LICEN[CS]E|COPYING)", p.name, re.I))
        report["licenses"][repo] = lic or []

    for repo_dir in [p for p in VENDOR.iterdir() if p.is_dir() and p.name not in {"adapters", "docs", "patches"}]:
        for path in repo_dir.rglob("*"):
            if not path.is_file() or path.stat().st_size > 5 * 1024 * 1024:
                continue
            if path.suffix.lower() not in TEXT_EXTS:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if re.search(r"C:\\Users\\[^\\\s\"']+", text) or re.search(r"C:\\Program Files", text):
                report["absolute_path_hits"].append(str(path.relative_to(VENDOR)))
            if any(pattern.search(text) for pattern in TOKEN_PATTERNS) or path.name.lower() in {".env", ".env.local", "credentials.json"}:
                report["token_files"].append(str(path.relative_to(VENDOR)))

    for adapter, (engine, repo) in ADAPTERS.items():
        script = VENDOR / "adapters" / adapter / "adapter.py"
        help_run = subprocess.run([str(interpreter(engine)), str(script), "--help"], capture_output=True, text=True, timeout=120)
        dry = subprocess.run([str(interpreter(engine)), str(script), "--json"], capture_output=True, text=True, timeout=600)
        payload = {}
        try:
            payload = json.loads(dry.stdout)
        except json.JSONDecodeError:
            payload = {"status": "error", "raw": (dry.stdout or dry.stderr)[:300]}
        report["adapters"][adapter] = {
            "repo": repo,
            "engine": engine,
            "help_ok": help_run.returncode == 0,
            "exit_code": dry.returncode,
            "status": payload.get("status", "error"),
            "checks": payload.get("checks", []),
            "blockers": payload.get("blockers", []),
        }

    out = VENDOR / "docs" / "import_selfcheck.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "repos_missing_any": sum(1 for v in report["file_compare"].values() if v["missing"]),
        "license_files": sum(1 for v in report["licenses"].values() if v),
        "absolute_path_hits": len(report["absolute_path_hits"]),
        "token_files": len(report["token_files"]),
        "adapters_adapted": sum(1 for v in report["adapters"].values() if v["status"] == "adapted"),
        "adapters_blocked": sum(1 for v in report["adapters"].values() if v["status"] == "blocked"),
        "adapters_error": sum(1 for v in report["adapters"].values() if v["status"] == "error"),
    }
    print(json.dumps(summary, ensure_ascii=False))
    print(str(out))


if __name__ == "__main__":
    main()
