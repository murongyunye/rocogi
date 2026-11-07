"""Verify the extracted 0.4.1 package through its WebUI (one round).

Checks: four-tier component counts, /wapi/vendor, /wapi/release against the
actual zip files, and the per-port versions (8787 Python / 8788 C).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8800"


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def get_json(path):
    _, body = get(path)
    return json.loads(body)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Round:
    def __init__(self, number, root):
        self.number = number
        self.root = root
        self.items = []

    def check(self, name, fn):
        try:
            ok, detail = fn()
        except Exception as exc:  # noqa: BLE001 - report every failure
            ok, detail = False, f"error: {exc}"
        self.items.append({"check": name, "ok": bool(ok), "detail": detail})
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name} - {detail}", flush=True)

    def summary(self):
        passed = sum(1 for i in self.items if i["ok"])
        return passed, len(self.items)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--root", required=True, help="extracted package root")
    parser.add_argument("--base", default=None)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    global BASE
    if args.base:
        BASE = args.base
    root = args.root
    rnd = Round(args.round, root)

    def ui():
        status, body = get("/")
        return status == 200 and len(body) > 1000, f"HTTP {status}, {len(body)} bytes"

    def components():
        data = get_json("/wapi/components")
        stats = data.get("stats") or {}
        expected = {"total": 55, "ready": 44, "notWired": 6, "skipped": 1, "blockedVendor": 4}
        ok = all(stats.get(k) == v for k, v in expected.items())
        return ok, json.dumps(stats, ensure_ascii=False)

    def vendor():
        data = get_json("/wapi/vendor")
        repos = data.get("repos") or []
        blocked = data.get("blockedItems") or []
        pending = data.get("pendingReboot") or []
        has_pets = any("pets" in json.dumps(item, ensure_ascii=False).lower() for item in blocked)
        ok = len(repos) == 16 and has_pets and len(pending) >= 1
        return ok, f"repos={len(repos)} blocked={len(blocked)} pendingReboot={len(pending)} petsGen={has_pets}"

    def release():
        data = get_json("/wapi/release")
        problems = []
        if data.get("version") != "0.4.1":
            problems.append(f"version={data.get('version')}")
        if data.get("docPath") != "docs/verify-release-0.4.1.md":
            problems.append(f"docPath={data.get('docPath')}")
        packages = data.get("packages") or []
        by_name = {p.get("name"): p for p in packages}
        for name in ("rocogi-0.4.1-lite.zip", "rocogi-0.4.1-full.zip"):
            item = by_name.get(name)
            if not item:
                problems.append(f"missing {name}")
                continue
            path = os.path.join(root, "release", name)
            if not os.path.isfile(path):
                problems.append(f"no local file {name}")
                continue
            if item.get("bytes") != os.path.getsize(path):
                problems.append(f"bytes mismatch {name}")
            if item.get("sha256") != sha256(path):
                problems.append(f"sha256 mismatch {name}")
        ok = not problems
        detail = "; ".join(problems) if problems else f"{len(packages)} packages match bytes+sha256"
        return ok, detail

    def versions():
        data = get_json("/wapi/overview")
        versions = data.get("versions") or {}
        expected = {"suite": "0.4.1", "python": "0.4.1", "c": "0.2.0"}
        ok = all(versions.get(k) == v for k, v in expected.items())
        return ok, json.dumps(versions, ensure_ascii=False)

    def pinned():
        data = get_json("/wapi/overview")
        runs_dir = os.path.join(root, "suite", "runs")
        has_side = os.path.isdir(os.path.join(runs_dir, "side-live5"))
        current = data.get("currentRun") or {}
        if not has_side:
            return True, "n/a (no side-live5 in extracted runs)"
        return current.get("run_id") == "side-live5", f"currentRun={current.get('run_id')}"

    def health8787():
        with urllib.request.urlopen("http://127.0.0.1:8787/api/health", timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("version") == "0.4.1", f"version={data.get('version')}"

    def health8788():
        with urllib.request.urlopen("http://127.0.0.1:8788/api/health", timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("version") == "0.2.0", f"version={data.get('version')}"

    rnd.check("WebUI 首页 8800", ui)
    rnd.check("/wapi/components 四档 55/44/6/1/4", components)
    rnd.check("/wapi/vendor 16 仓 + pets-gen + 待重启", vendor)
    rnd.check("/wapi/release 包名/字节/sha256 与实包一致", release)
    rnd.check("/wapi/overview versions suite/python/c", versions)
    rnd.check("默认选中 side-live5（有该 run 时）", pinned)
    rnd.check("8787 /api/health version=0.4.1", health8787)
    rnd.check("8788 /api/health version=0.2.0", health8788)

    passed, total = rnd.summary()
    print(f"round {args.round}: {passed}/{total} PASS", flush=True)
    payload = {
        "round": args.round,
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "root": root,
        "base": BASE,
        "passed": passed,
        "total": total,
        "items": rnd.items,
    }
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
