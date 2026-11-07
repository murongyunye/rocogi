"""Build Rocogi release archives.

Two packages are produced from the same source tree:

  rocogi-<version>-lite.zip   first-party suite/backend/frontend/docs/datasets (~42 MB)
  rocogi-<version>-full.zip   lite + the complete vendor/ source tree (~890 MB)

Both are ZIP64 (Python zipfile switches automatically when needed). Large binary
assets inside vendor/ (onnx/exe/db/images) are stored uncompressed to keep the
build in the minutes range; text and source are deflated. Alongside them the
builder writes ``checksums-v<version>.txt`` (sha256) for the published archives.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else "0.0.0"
# The prebuilt C core keeps its own version line; bump it in backend-c/CMakeLists.txt
# and keep this constant in sync so checksums point at the file we actually ship.
CORE_VERSION = "0.2.0"

CORE_DIRS = ("backend", "backend-c", "data", "frontend", "scripts", "packaging", "sdk", "docs", ".github", "suite",
             "webui", "game-data")
CORE_FILES = ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "CHANGELOG.md", "VERSION", ".gitignore",
              "start-all.ps1", "stop-all.ps1")
TOP_LEVEL_EXCLUDED = {".venv", "references", "optional", "build", "dist", "runtime", "release",
                      ".toolchain", "vendor", "runs", "logs"}

# datasets/ is not a CORE_DIR because most of it is not needed at runtime
# (models/upstream 239 MB, map/render 26 MB, map/poi+icons 9.7 MB, .cache dirs).
# Third-party game data (BWIKI dumps, community PvP datasets, map icons) is NOT
# redistributed in any archive: what ships is the provenance note plus the import
# scripts, so a download can rebuild the databases locally from its own sources.
SHIP_DATASETS = (
    "datasets/README.md",
    "datasets/bwiki/PROVENANCE.md",
    "datasets/pvp/PROVENANCE.md",
    "datasets/tools/bwiki/fetch_bwiki.py",
    "datasets/tools/bwiki/import_bwiki.py",
    "datasets/tools/bwiki/lua_literal.py",
    "datasets/tools/pvp/fetch_pvp.py",
    "datasets/tools/pvp/import_pvp.py",
)

# already-compressed / large binaries: store instead of deflate
STORE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".zip", ".7z", ".gz", ".xz",
                  ".exe", ".dll", ".pyd", ".so", ".onnx", ".pt", ".pth", ".db", ".sqlite", ".bin",
                  ".mp3", ".mp4", ".wav", ".ttf", ".otf", ".woff", ".woff2", ".pak"}


def _skip(path: Path) -> bool:
    parts = set(path.parts)
    if "node_modules" in parts or "__pycache__" in parts or ".pytest_cache" in parts:
        return True
    if ".venv" in parts or "env" in parts or ".git" in parts:
        return True
    if path.suffix in (".pyc", ".pyo", ".db-shm", ".db-wal"):
        return True
    return False


def _included_core(path: Path, with_docs: bool) -> bool:
    rel = path.relative_to(ROOT)
    if rel.parts[0] in TOP_LEVEL_EXCLUDED:
        return False
    if _skip(path):
        return False
    if rel.parts[0] == "suite" and len(rel.parts) > 2 and rel.parts[1] == "assets" \
            and rel.parts[2] in ("maps", "map", "features", "models", "db"):
        return False
    if rel.parts[0] == "suite":
        joined = "/".join(rel.parts)
        if joined.startswith("suite/logs/") or joined.startswith("suite/runs/"):
            return False
        if "auto-rocokingdom" in rel.parts:
            return False
    if rel.parts[:2] == ("backend-c", "build2"):
        # CMake build output (rocogi-core.exe + intermediates), already gitignored;
        # the prebuilt core ships as backend-c/rocogi-core-<version>.zip instead.
        return False
    if rel.parts[0] == "webui":
        # webui/.cache is a local probe/cache dir; probe_out holds 2.4 MB of samples
        if rel.parts[1:2] == (".cache",):
            return False
        if rel.parts[1:3] == ("scripts", "probe_out"):
            return False
    if rel.parts[0] == "game-data":
        joined = "/".join(rel.parts)
        if joined.startswith("game-data/incoming/"):
            return False
    if rel.parts[:3] == ("data", "map", "icons"):
        # in-game item icons for the resource map overlay: not redistributed
        return False
    if rel.parts[:2] == ("docs", "screenshots"):
        # In-game screenshots are local documentation artifacts: they show third-party
        # game art, so no archive redistributes them. Regenerate with make-shots.mjs.
        return False
    return True


def _included_vendor(path: Path) -> bool:
    rel = path.relative_to(ROOT / "vendor")
    repo, parts = rel.parts[0], rel.parts
    if _skip(path) or repo in ("__pycache__", ".cache"):
        return False
    # global intermediates / package caches (never ship 9.5 GB of toolchain or node_modules)
    if any(part in ("node_modules", "__pycache__", ".git", ".venv", ".pnpm-store", "obj", ".cache")
           for part in parts):
        return False
    if rel.suffix.lower() == ".zip" or rel.suffix.lower() == ".orig":
        return False
    if "bin" in parts and ("Debug" in parts or "Release" in parts):
        return False
    # .NET only: BetterGI's 1.13 GB bin/obj output is replaced by artifacts/BetterGI.*
    if repo == "babalae-better-genshin-impact" and ("bin" in parts or "obj" in parts):
        return False
    # PyInstaller dist of the old luoke GUI is a build product, not source/data
    if repo == "zh19990906-luoke_location" and parts[1:2] == ("dist",):
        return False
    # sift is resolved: ship the client (route re-recording), the service binary,
    # its SIFT assets and the generated default route. Only the duplicate service.exe
    # under screen-recognition/ and the regenerable resources/cache are dropped.
    if repo == "sift-map-tracker" and parts[1:2] in (("screen-recognition",),):
        return False
    if repo == "sift-map-tracker" and parts[1:3] == ("sift-map-tracker", "resources") and "cache" in parts:
        return False
    # 160 MB of per-pet web icons: optional media, the battle engine only reads nrc.db
    if repo == "ColinHong10-NRC_AI" and parts[1:3] == ("data", "spirit_icons"):
        return False
    # upstream delivery screenshots / old resumes
    if repo == "Wooziii-roco-map-tracker" and parts[1:2] == ("deliverables",):
        return False
    return True


def _write_artifacts(package: zipfile.ZipFile, counter: list[int]) -> None:
    """Resolved blocker builds live outside the source tree; ship their runnable entry."""
    bgi = (ROOT / "vendor" / "babalae-better-genshin-impact" / "BetterGenshinImpact" / "bin"
           / "Release" / "net10.0-windows10.0.22621.0")
    entries = [
        (ROOT / ".toolchain" / "build" / "yotta.exe", "artifacts/yotta/yotta.exe"),
        (bgi / "BetterGI.exe", "artifacts/bettergi/BetterGI.exe"),
        (bgi / "BetterGI.dll", "artifacts/bettergi/BetterGI.dll"),
        (bgi / "BetterGI.deps.json", "artifacts/bettergi/BetterGI.deps.json"),
        (bgi / "BetterGI.runtimeconfig.json", "artifacts/bettergi/BetterGI.runtimeconfig.json"),
    ]
    for path, arcname in entries:
        if path.exists():
            _write(package, path, arcname, counter)
    package.writestr("artifacts/README.txt", (
        f"Resolved blocker artifacts (Rocogi {VERSION})\n"
        "\n"
        "yotta/       yotta.exe from portable Go 1.25.13 + Wails v3.0.0-beta.6; GUI not auto-started.\n"
        "bettergi/    BetterGI.exe + primary assembly from portable .NET 10 SDK (0 errors).\n"
        "             The WPF app also needs the sibling runtime DLLs from the upstream\n"
        "             build output; only the runnable entry is bundled to keep the archive size bounded.\n"
        "\n"
        "rocokingdom-ui dist (49 files, 14.0 MB): vendor/rookie-orange-rocokingdom-ui/apps/website/dist/\n"
        "RocoTools data (594 pets, 553 skills, 571 icons): vendor/eachyczhang-RocoTools/data/\n"
        "sift: vendor/sift-map-tracker/SiftMapTracker.Client.exe (route recording),\n"
        "      vendor/sift-map-tracker/sift-map-tracker/service/service.exe + assets/ (runtime),\n"
        "      routes/default_route.json (162 nodes / 161 edges, generated placement),\n"
        "      runtime/settings_override.json (region 0,0,255,235), docs/evidence/sift_route_probe.json\n"
        "interception: vendor/tools/post-reboot-check.ps1 (run after reboot)\n"
    ))


def _write(package: zipfile.ZipFile, path: Path, arcname: str, counter: list[int]) -> None:
    if path.suffix.lower() in STORE_SUFFIXES:
        package.write(path, arcname, compress_type=zipfile.ZIP_STORED)
    else:
        package.write(path, arcname, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    counter[0] += 1
    if counter[0] % 500 == 0:
        print(f"  ... {counter[0]} files", flush=True)


def build_lite(output: Path, with_docs: bool) -> Path:
    target = output / f"rocogi-{VERSION}-lite.zip"
    counter = [0]
    last = ""
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as package:
        for name in CORE_FILES:
            path = ROOT / name
            if path.exists():
                _write(package, path, name, counter)
        for folder in CORE_DIRS:
            base = ROOT / folder
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if not path.is_file() or not _included_core(path, with_docs):
                    continue
                _write(package, path, str(path.relative_to(ROOT)), counter)
                last = path.name
        for rel in SHIP_DATASETS:
            path = ROOT / rel
            if path.exists():
                _write(package, path, rel, counter)
                last = path.name
    print(f"lite: {target.name} files={counter[0]} last={last}", flush=True)
    return target


def build_full(output: Path, with_docs: bool) -> Path:
    target = output / f"rocogi-{VERSION}-full.zip"
    counter = [0]
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as package:
        for name in CORE_FILES:
            path = ROOT / name
            if path.exists():
                _write(package, path, name, counter)
        for folder in CORE_DIRS:
            base = ROOT / folder
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if not path.is_file() or not _included_core(path, with_docs):
                    continue
                _write(package, path, str(path.relative_to(ROOT)), counter)
        for rel in SHIP_DATASETS:
            path = ROOT / rel
            if path.exists():
                _write(package, path, rel, counter)
        vendor = ROOT / "vendor"
        if not vendor.exists():
            raise SystemExit("vendor/ is missing; cannot build the full package")
        for path in vendor.rglob("*"):
            if not path.is_file() or not _included_vendor(path):
                continue
            _write(package, path, str(path.relative_to(ROOT)), counter)
        _write_artifacts(package, counter)
    print(f"full: {target.name} files={counter[0]}", flush=True)
    return target


def build_engine_bundle(output: Path) -> Path | None:
    dist = ROOT / "dist" / "engines"
    if not dist.exists():
        return None
    target = output / "rocogi-engine-linux-x64.zip"
    candidates = [dist / "RocogiEngine", dist / "README.txt", dist / "checksums.txt"]
    candidates = [path for path in candidates if path.exists()]
    if not candidates:
        return None
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for path in candidates:
            package.write(path, path.name)
    return target


def build_windows_bundle(output: Path) -> Path | None:
    dist = ROOT / "dist" / "engines"
    exes = sorted(dist.glob("*.exe")) if dist.exists() else []
    if not exes:
        return None
    target = output / "rocogi-engine-windows.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for path in exes:
            package.write(path, path.name)
        readme = dist / "README.txt"
        if readme.exists():
            package.write(readme, readme.name)
    return target


def build_sift_bundle(output: Path) -> Path | None:
    base = ROOT / "optional" / "sift-tracker"
    zips = sorted(base.glob("SIFT-Map-Tracker-*.zip")) if base.exists() else []
    if not zips:
        return None
    source = zips[0]
    version = source.stem.split("-v")[-1]
    target = output / f"rocogi-sift-tracker-{version}.zip"
    if target.exists():
        target.unlink()
    try:
        os.link(source, target)
    except OSError:
        shutil.copyfile(source, target)
    for name in ("README.md", "manifest.json", "CHECKSUM.txt"):
        path = base / name
        if path.exists():
            shutil.copyfile(path, output / f"rocogi-sift-tracker-{version}-{name}")
    return target


def write_checksums(output: Path, artifacts: list[Path]) -> Path | None:
    """Write ``checksums-v<version>.txt`` for the archives just built.

    The release script uploads this file next to the archives so a download can be
    verified with ``certutil -hashfile`` / ``sha256sum -c``. The prebuilt C core
    bundle ships inside the lite archive and is published separately, so hash it too.
    """
    import hashlib

    targets = [p for p in artifacts if p.suffix == ".zip" and p.exists()]
    core = ROOT / "backend-c" / f"rocogi-core-{CORE_VERSION}.zip"
    if core.exists():
        targets.append(core)
    if not targets:
        return None

    lines = []
    for path in sorted(targets, key=lambda p: p.name):
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        lines.append(f"{digest.hexdigest()}  {path.name}")
    out = output / f"checksums-v{VERSION}.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Rocogi release archives (lite + full).")
    parser.add_argument("--output", default=str(ROOT / "release"))
    parser.add_argument("--with-docs", action="store_true", help="include docs/screenshots")
    parser.add_argument("--mode", choices=("both", "lite", "full"), default="both")
    parser.add_argument("--with-engine", action="store_true", help="include Linux unified engine")
    parser.add_argument("--with-sift", action="store_true", help="include optional SIFT tracker bundle")
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    artifacts = []
    if args.mode in ("both", "lite"):
        artifacts.append(build_lite(output, args.with_docs))
    if args.mode in ("both", "full"):
        artifacts.append(build_full(output, args.with_docs))
    if args.with_engine:
        engine = build_engine_bundle(output)
        if engine:
            artifacts.append(engine)
    if args.with_sift:
        sift = build_sift_bundle(output)
        if sift:
            artifacts.append(sift)
    windows = build_windows_bundle(output)
    if windows:
        artifacts.append(windows)

    checksums = write_checksums(output, artifacts)
    if checksums:
        artifacts.append(checksums)

    for path in artifacts:
        size = path.stat().st_size
        print(f"{path.name}\t{size / 1024 / 1024:.1f} MB\t{size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
