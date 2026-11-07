"""Fetch the community PvP datasets used by ``import_pvp.py``.

Three upstream repositories are pinned by commit so a rebuild is reproducible:

* ``180sans/roco-cal``      -- per-pet six stats, skill lists, trait rules
* ``s422346963/RokePvP-Calculator`` -- spirit/skill/type tables with damage knobs
* ``sduwcdd/RoCo-PVP``      -- public PvP usage statistics scraped from the game

Everything lands in ``datasets/pvp/.cache/`` (git ignored).  Run this first, then
``import_pvp.py`` which derives ``datasets/pvp/pvp_data.db`` from the cache.
"""

from __future__ import annotations

import io
import json
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "datasets" / "pvp" / ".cache"

RAW = "https://raw.githubusercontent.com"
CODELOAD = "https://codeload.github.com"

# owner/repo + commit + the files we care about.
RAW_SOURCES = [
    ("s422346963/RokePvP-Calculator", "624192b", [
        "data/spirits.js",
        "data/skills.js",
        "data/type.js",
        "data/spiritsPvP.js",
        "data/skillMult.js",
        "data/traitMult.js",
    ]),
    ("sduwcdd/RoCo-PVP", "c6886de", [
        "data/external/pokedex_pvp_usage.json",
        "data/external/pvp-community-20261029/popular-teams.raw.json",
    ]),
]

# roco-cal keeps one file per pet/trait; a tarball is cheaper than ~950 requests.
TARBALL_SOURCES = [
    ("180sans/roco-cal", "1c58ec8", "src-tauri/resources/rocodatebase/data/", [
        "skills_database/",
        "pets_w_skill_json/",
        "pets_trait_json/",
    ]),
]


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "rocogi-pvp-import"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def fetch_raw() -> None:
    for repo, ref, files in RAW_SOURCES:
        for rel in files:
            dest = CACHE / repo.split("/")[1] / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists() and dest.stat().st_size > 0:
                print(f"  cached  {rel} ({dest.stat().st_size} B)")
                continue
            data = _download(f"{RAW}/{repo}/{ref}/{rel}")
            dest.write_bytes(data)
            print(f"  fetched {rel} ({len(data)} B)")


def fetch_tarball() -> None:
    for repo, ref, prefix, wanted in TARBALL_SOURCES:
        out_dir = CACHE / repo.split("/")[1]
        marker = out_dir / ".done"
        if marker.exists():
            print(f"  cached  {repo} tarball")
            continue
        print(f"  fetching {repo}@{ref} tarball ...")
        blob = _download(f"{CODELOAD}/{repo}/tar.gz/{ref}")
        print(f"  downloaded {len(blob) / 1e6:.1f} MB")
        count = 0
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
            for member in tf:
                if not member.isfile():
                    continue
                name = member.name
                if prefix not in name:
                    continue
                rel = name.split(prefix, 1)[1]
                if not any(rel.startswith(part) for part in wanted):
                    continue
                dest = out_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                with tf.extractfile(member) as src, open(dest, "wb") as fh:
                    fh.write(src.read())
                count += 1
        marker.write_text(ref, encoding="utf-8")
        print(f"  extracted {count} files")


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    print(f"cache: {CACHE}")
    fetch_raw()
    fetch_tarball()
    counts = {
        "rokepvp": len(list((CACHE / "RokePvP-Calculator").rglob("*.js"))),
        "roco-cal": len(list((CACHE / "roco-cal").rglob("*.json"))),
        "rocopvp": len(list((CACHE / "RoCo-PVP").rglob("*.json"))),
    }
    print("fetched:", json.dumps(counts, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
