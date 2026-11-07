"""SIFT-Map-Tracker 兼容层：二进制发布包校验 + 参数契约 + 与源码版 SIFTEngine 的差异。

结论：该包**没有运行时 Python 源码**，唯一 .py 是客户端设置页导出的 settings.py。
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import repo_dir, run  # noqa: E402


def _settings_constants(path: Path) -> dict[str, object]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                values[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, SyntaxError):
                continue
    return values


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def body(result) -> None:
    repo = repo_dir("sift-map-tracker")
    result.add("repo", True, repo.name)

    py_files = sorted(str(p.relative_to(repo)) for p in repo.rglob("*.py"))
    result.add("python_runtime_source", False, f"仅 {py_files}（客户端设置导出，不是运行时源码）")

    manifest = json.loads((repo / "build-manifest.json").read_text(encoding="utf-8"))
    missing, mismatched, ok = [], [], 0
    for entry in manifest.get("files", []):
        target = repo / entry["path"]
        if not target.is_file():
            missing.append(entry["path"])
            continue
        if target.stat().st_size != entry["bytes"] or _sha256(target) != entry["sha256"]:
            mismatched.append(entry["path"])
        else:
            ok += 1
    result.add("manifest_hash", ok == len(manifest.get("files", [])),
               f"通过 {ok}/{len(manifest.get('files', []))}；缺失 {len(missing)}；哈希不符 {len(mismatched)}")

    settings = _settings_constants(repo / "sift-map-tracker" / "settings.py")
    result.add("settings_parsed", bool(settings), f"{len(settings)} 个常量")

    # 与源码版 SIFTEngine 对齐：只读导入 tracker.models（纯标准库）。
    sys.path.insert(0, str(repo_dir("Wooziii-roco-map-tracker") / "roco-map-tracker"))
    from tracker.models import SIFTSettings  # type: ignore

    fields = set(SIFTSettings.__dataclass_fields__)
    comparable = {
        "refresh_rate_ms": settings.get("REFRESH_RATE_MS"),
        "clahe_limit": settings.get("CLAHE_LIMIT"),
        "match_ratio": settings.get("MATCH_RATIO"),
        "min_match_count": settings.get("MIN_MATCH_COUNT"),
        "ransac_threshold": settings.get("RANSAC_THRESHOLD"),
        "max_lost_frames": settings.get("MAX_LOST_FRAMES"),
        "local_search_radius": settings.get("LOCAL_SEARCH_RADIUS_PX"),
    }
    mapped = {k: v for k, v in comparable.items() if k in fields}
    result.add("param_mapping", len(mapped) == len(comparable), f"{mapped}")

    exes = sorted(p.name for p in repo.rglob("*.exe"))
    result.contract.update(
        {
            "runtime_source": False,
            "python_files": py_files,
            "binaries": exes,
            "declared_version": manifest.get("version"),
            "tracker_commit": manifest.get("tracker", {}).get("commit"),
            "client_commit": manifest.get("client", {}).get("commit"),
            "missing_from_package": missing,
            "mismatched": mismatched,
            "settings": settings,
            "mapped_to_source_engine": mapped,
            "replacement_relation": {
                "primary_source_engine": "vendor/Wooziii-roco-map-tracker/roco-map-tracker/tracker/engines/sift_engine.py",
                "binary_package_role": "参数/资源基准 + 可选外部进程（service.exe）",
                "differences": [
                    "二进制包只有 settings.py 与资产，无算法实现，无法在不调用 exe 的前提下复用逻辑",
                    "源码版 SIFTEngine 支持 hybrid/sift/sift_tracker/sift_v02 四种引擎，二进制包只暴露 sift",
                    "二进制包小地图 255x235 且带 150x150 旧档；源码版默认由调用方传入 ROI",
                    "二进制包的 local_search_radius=280、match_ratio=0.90，源码版默认 550、0.7x，需显式映射",
                ],
            },
            "process_contract": {
                "launch": "vendor/sift-map-tracker/sift-map-tracker/service/service.exe",
                "client": "vendor/sift-map-tracker/SiftMapTracker.Client.exe",
                "stdio": "JSON over stdin/stdout，UTF-8 字节级",
            },
        }
    )
    result.block("无运行时源码：算法只能通过 service.exe 外部进程调用，或改用 vendor 内 roco-map-tracker 的 SIFTEngine")


if __name__ == "__main__":
    raise SystemExit(run("sift_map_tracker", "sift-map-tracker", body))
