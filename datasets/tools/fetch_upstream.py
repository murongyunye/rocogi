#!/usr/bin/env python3
"""Fetch third-party training tools and model weights that are NOT redistributed
in this repository, directly from their upstream sources.

Why fetch instead of vendoring:
  * Tsuann/RocoKingdom-AutoCapture has NO license file (all rights reserved by
    default) -- its scripts may not be redistributed here, so we fetch them
    verbatim from the upstream repo instead.
  * SCH-CMYK/game-automation is license NOASSERTION (custom/nonstandard).
  * Model weights (.pt/.onnx) are large binary artifacts; upstream convention
    in this ecosystem is to keep them out of git and download on demand.

Everything fetched lands under datasets/tools/{tsuann,sch}/ and
datasets/models/upstream/ respectively. Integrity is checked against the
recorded sizes/sha256 in datasets/models/upstream/MANIFEST.json when available.

Usage:
    python fetch_upstream.py tools     # Tsuann + SCH scripts
    python fetch_upstream.py weights   # all model weights (may be slow)
    python fetch_upstream.py all

Requires: Python 3.10+, a GitHub token in ~/.rocogi/github_token (optional for
public repos, recommended for rate limits), internet access.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]  # datasets/tools -> datasets -> repo root
DATASETS = REPO_ROOT / "datasets"
MODELS = DATASETS / "models" / "upstream"
MANIFEST = MODELS / "MANIFEST.json"

TSUANN_REPO = "Tsuann/RocoKingdom-AutoCapture"
SCH_REPO = "SCH-CMYK/game-automation"
SCH_RELEASE_TAG = "v1.0"

# Tsuann training pipeline scripts (12, as of 2026-11): fetched, not redistributed.
TSUANN_SCRIPTS = [
    "train_model.py", "incremental_train.py", "auto_label.py", "extract_frames.py",
    "augment_dataset.py", "capture_dataset.py", "capture_screenshots.py",
    "split_output_convert.py", "crawl_sprites.py", "fix_onnx_quant.py",
    "label_tool.py", "record_region.ps1",
]
# SCH tooling (4): fetched, not redistributed.
SCH_FILES = ["label_tool.py", "trainer.py", "download_models.py"]
SCH_YAML = ["datasets/default/data.yaml"]

TOKEN_PATH = Path.home() / ".rocogi" / "github_token"


def gh_headers(raw: bool = False) -> dict:
    h = {"User-Agent": "rocogi-datasets-fetch", "Accept":
         "application/vnd.github.raw" if raw else "application/vnd.github+json"}
    if TOKEN_PATH.exists():
        h["Authorization"] = f"Bearer {TOKEN_PATH.read_text().strip()}"
    return h


def gh_get(url: str, raw: bool = False) -> bytes:
    req = urllib.request.Request(url, headers=gh_headers(raw))
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def fetch_repo_files(repo: str, paths: list[str], dest: Path, ref: str = "HEAD") -> int:
    dest.mkdir(parents=True, exist_ok=True)
    ok = 0
    for p in paths:
        url = f"https://api.github.com/repos/{repo}/contents/{p}?ref={ref}"
        out = dest / Path(p).name
        try:
            data = gh_get(url, raw=True)
            out.write_bytes(data)
            print(f"  ok   {repo}/{p} -> {out.relative_to(REPO_ROOT)} ({len(data)} B)")
            ok += 1
        except Exception as e:  # noqa: BLE001 - report every failure, keep going
            print(f"  FAIL {repo}/{p}: {e}")
    return ok


def fetch_tools() -> None:
    print(f"[tools] Tsuann scripts -> datasets/tools/tsuann/")
    n1 = fetch_repo_files(TSUANN_REPO, TSUANN_SCRIPTS, DATASETS / "tools" / "tsuann")
    print(f"[tools] SCH files -> datasets/tools/sch/")
    n2 = fetch_repo_files(SCH_REPO, SCH_FILES + SCH_YAML, DATASETS / "tools" / "sch")
    print(f"[tools] done: tsuann {n1}/{len(TSUANN_SCRIPTS)}, sch {n2}/{len(SCH_FILES) + len(SCH_YAML)}")


def fetch_weights() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    entries = manifest.get("weights", [])
    if not entries:
        print(f"[weights] no weights[] in {MANIFEST}")
        sys.exit(2)
    MODELS.mkdir(parents=True, exist_ok=True)
    for e in entries:
        name = e.get("file")
        if not name:
            print(f"  SKIP (manifest entry missing file): {e.get('path')}")
            continue
        out = MODELS / name
        if out.exists() and out.stat().st_size == e.get("bytes"):
            print(f"  have {name} ({out.stat().st_size} B)")
        else:
            src = e.get("repo", "")
            path = e.get("path", "").replace(" (git-lfs)", "").replace("release v1.0", "")
            if path.startswith("release"):
                path = ""
            if src and path:
                url = f"https://api.github.com/repos/{src}/contents/{path}"
                # git-lfs pointers: resolve through the media endpoint
                data = gh_get(url, raw=True)
                if data.lstrip().startswith(b"version https://git-lfs"):
                    oid = json.loads(gh_get(f"https://api.github.com/repos/{src}/contents/{path}").decode())["lfs"]["oid"]
                    url = f"https://media.githubusercontent.com/media/{src}/main/{path.rsplit('/', 1)[-1]}"
                    data = gh_get(url, raw=True)  # LFS media endpoint (public repos: no token needed)
                out.write_bytes(data)
            else:
                print(f"  SKIP {name}: release asset -- get it from https://github.com/{src}/releases")
                continue
        expect = e.get("sha256") or e.get("sha256_actual")
        if expect:
            digest = hashlib.sha256(out.read_bytes()).hexdigest()
            mark = "OK " if digest == expect else "BAD"
            print(f"  {mark}  sha256 {name}")
            if mark == "BAD":
                print(f"        expected {expect}\n        got      {digest}")


def main() -> None:
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("tools", "all"):
        fetch_tools()
    if what in ("weights", "all"):
        fetch_weights()


if __name__ == "__main__":
    main()
