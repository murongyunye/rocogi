"""One verification round: clean build -> assets -> 25 entries -> 3 chains -> frontend -> restart.

Writes docs/verify-round-N.md. Exit code 0 only when every check is green.
Usage: <toolchain python> probes/verify_round.py --round 1
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
import tomllib
import urllib.request

SUITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(SUITE)
PY = os.path.join(ROOT, ".toolchain", "python", "cpython-3.12.16-windows-x86_64-none", "python.exe")
UV = os.path.join(ROOT, ".toolchain", "uv", "uv.exe")
CLI = os.path.join(SUITE, "kernel", "cli.py")
ENGINES = os.path.join(SUITE, "engines")

results = []


def add(name: str, ok: bool, detail) -> bool:
    results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(("[PASS] " if ok else "[FAIL] ") + name + " :: " + json.dumps(detail, ensure_ascii=False)[:300])
    return ok


def run(cmd, timeout=600):
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    return proc


def step_clean():
    removed = {"logs": 0, "runs": 0, "pycache": 0}
    logs = os.path.join(SUITE, "logs")
    runs = os.path.join(SUITE, "runs")
    pruned = {".venv", "node_modules", "env", "auto-rocokingdom"}
    for root, dirs, files in os.walk(SUITE):
        rel_parts = set(os.path.relpath(root, SUITE).split(os.sep))
        if pruned & rel_parts:
            dirs[:] = []
            continue
        if "__pycache__" in dirs:
            shutil.rmtree(os.path.join(root, "__pycache__"), ignore_errors=True)
            removed["pycache"] += 1
            dirs.remove("__pycache__")
    if os.path.isdir(logs):
        for name in os.listdir(logs):
            p = os.path.join(logs, name)
            if os.path.isfile(p):
                os.remove(p)
                removed["logs"] += 1
    if os.path.isdir(runs):
        for name in os.listdir(runs):
            p = os.path.join(runs, name)
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
                removed["runs"] += 1
    return add("clean-state", True, removed)


def step_build():
    py = os.path.join(ENGINES, "sift", ".venv", "Scripts", "python.exe")
    proc = run([py, os.path.join(SUITE, "assets", "build.py")], timeout=900)
    ok = proc.returncode == 0
    tail = (proc.stdout or "").strip().splitlines()[-1:] or [""]
    return add("build-assets", ok, {"returncode": proc.returncode, "tail": tail[0][:200],
                                     "stderr": (proc.stderr or "").strip()[-200:]})


def step_compile():
    # Prune venvs / node_modules / probe envs at each os.walk level. compile_dir
    # would descend into Lib/site-packages and can exceed the timeout.
    code = """
import compileall, os, sys
suite = r'__SUITE__'
skip = {'.venv', 'node_modules', 'env', 'auto-rocokingdom', '__pycache__'}
bad = []
for root, dirs, files in os.walk(suite):
    dirs[:] = [d for d in dirs if d not in skip]
    for name in files:
        if not name.endswith('.py'):
            continue
        path = os.path.join(root, name)
        if not compileall.compile_file(path, quiet=1, force=True):
            bad.append(path)
print('compiled-first-party', 'bad=%d' % len(bad))
sys.exit(0 if not bad else 1)
""".replace("__SUITE__", SUITE)
    proc = run([PY, "-c", code], timeout=300)
    return add("compileall", proc.returncode == 0, {"returncode": proc.returncode,
                                                     "tail": (proc.stdout or '').strip()[-100:]})


def step_assets():
    py = os.path.join(ENGINES, "sift", ".venv", "Scripts", "python.exe")
    proc = run([py, os.path.join(SUITE, "assets", "verify.py")], timeout=600)
    try:
        rep = json.loads(proc.stdout)
    except json.JSONDecodeError:
        rep = {"ok": False, "parseError": (proc.stdout or proc.stderr or "")[:300]}
    detail = {
        "ok": rep.get("ok"),
        "hashesChecked": rep.get("hashes", {}).get("checked"),
        "hashesFailed": rep.get("hashes", {}).get("failed"),
        "points": rep.get("points", {}).get("pointCount"),
        "mmapSeconds": rep.get("mmap", {}).get("mmapSeconds"),
        "canonicalMap": rep.get("maps", {}).get("canonicalMatch"),
        "nrc": rep.get("nrc", {}).get("counts"),
    }
    return add("assets-verify", bool(rep.get("ok")), detail)


def step_entries():
    out = os.path.join(SUITE, "logs", "verify-raw.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    proc = run([PY, CLI, "engines", "--verify"], timeout=1800)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(proc.stdout)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return add("engines-verify", False, {"parseError": (proc.stdout or proc.stderr or "")[:300]})
    summary = data["verifySummary"]
    comps = data["components"]
    entries = data["entries"]
    expected = len(tomllib.load(open(os.path.join(SUITE, "config", "components.toml"), "rb"))["components"])
    detail = {"ok": summary["ok"], "failed": summary["failed"], "total": summary["total"],
              "failedEntries": summary["failedEntries"], "components": comps,
              "componentCountExpected": expected, "entryCount": entries["total"]}
    ok = summary["failed"] == 0 and comps["total"] == expected and entries["total"] >= 25
    return add("engines-verify", ok, detail)


def step_locks():
    rows = {}
    ok = True
    for name in ("capture", "vision", "input", "sift", "battle", "scheduler", "vendor"):
        py = os.path.join(ENGINES, name, ".venv", "Scripts", "python.exe")
        freeze = run([UV, "pip", "freeze", "--python", py], timeout=120).stdout
        lock_path = os.path.join(ENGINES, name, "requirements.lock")
        lock = open(lock_path, encoding="utf-8").read() if os.path.exists(lock_path) else ""
        if lock.startswith("#"):
            same = not [l for l in freeze.splitlines() if l.strip()]
        else:
            same = freeze.strip() == lock.strip()
        rows[name] = {"match": same, "packages": len([l for l in freeze.splitlines() if l.strip()])}
        ok = ok and same
    return add("requirements-lock", ok, rows)


def step_chains():
    chains = {}
    for engine, action in (("sift", "locate"), ("capture", "capture"), ("battle", "responder")):
        proc = run([PY, CLI, "call", engine, action, "--run-id", "chain-%s" % engine], timeout=300)
        try:
            res = json.loads(proc.stdout)
        except json.JSONDecodeError:
            res = {"status": "unparsable"}
        chains[engine] = {"status": res.get("status"), "action": res.get("action"),
                          "hasResult": res.get("result") is not None, "error": res.get("error")}
    ok = all(v["status"] == "ok" and v["hasResult"] for v in chains.values())
    return add("three-chains", ok, chains)


def _http(url):
    try:
        with urllib.request.urlopen(url, timeout=4) as resp:
            return resp.status, len(resp.read())
    except Exception as exc:  # noqa: BLE001
        return 0, f"{type(exc).__name__}: {exc}"


def step_frontend():
    probes = {"8787": _http("http://127.0.0.1:8787/api/health"),
              "8788": _http("http://127.0.0.1:8788/api/health"),
              "8800": _http("http://127.0.0.1:8800/"),
              "5173": _http("http://127.0.0.1:5173/")}
    ok = all(v[0] == 200 for v in probes.values())
    if not ok:
        return add("frontend-probes", False, {k: v[0] for k, v in probes.items()})
    # WebUI is read-only: verify it can see the new vendor components from components.toml
    expected = len(tomllib.load(open(os.path.join(SUITE, "config", "components.toml"), "rb"))["components"])
    try:
        with urllib.request.urlopen("http://127.0.0.1:8800/wapi/components", timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        detail = {k: v[0] for k, v in probes.items()}
        detail["componentsError"] = f"{type(exc).__name__}: {exc}"
        return add("frontend-probes", False, detail)
    groups = payload.get("groups", [])
    vendor = next((g for g in groups if g.get("engine") == "vendor"), None)
    total = payload.get("stats", {}).get("total")
    detail = {k: v[0] for k, v in probes.items()}
    detail.update({"statsTotal": total, "expectedTotal": expected,
                   "vendorGroup": bool(vendor), "vendorComponents": len(vendor["components"]) if vendor else 0})
    return add("frontend-probes", total == expected and bool(vendor), detail)


def _api(path):
    with urllib.request.urlopen("http://127.0.0.1:8800" + path, timeout=8) as resp:
        return json.loads(resp.read().decode("utf-8"))


def step_frontend_run():
    """After the restart run, the WebUI must expose that exact run and the new components."""
    try:
        runs = _api("/wapi/runs?limit=5")
        run_id = (runs.get("runs") or [{}])[0].get("run_id")
        detail = _api("/wapi/runs/verify-restart")
        manifest = detail.get("manifest", {})
        components = [c.get("id") for c in manifest.get("components", [])]
        engine_names = list((manifest.get("engines") or {}).keys())
        overview = _api("/wapi/overview")
        current = (overview.get("currentRun") or {}).get("run_id")
    except Exception as exc:  # noqa: BLE001
        return add("frontend-latest-run", False, {"error": f"{type(exc).__name__}: {exc}"})
    ok = (run_id == "verify-restart" and current == "verify-restart"
          and "vendor" in engine_names and any(c.startswith("vendor.") for c in components))
    return add("frontend-latest-run", ok, {"latestRun": run_id, "overviewCurrent": current,
                                           "engines": engine_names,
                                           "vendorComponents": [c for c in components if c.startswith("vendor.")], "count": len(components)})


def step_supervisor():
    proc = run([PY, CLI, "run", "--duration", "7", "--kill-after", "2", "--kill-engine", "vision",
                "--run-id", "verify-restart"], timeout=600)
    run_dir = os.path.join(SUITE, "runs", "verify-restart")
    metrics = json.load(open(os.path.join(run_dir, "metrics.json"), encoding="utf-8"))
    events = [json.loads(l) for l in open(os.path.join(run_dir, "events.jsonl"), encoding="utf-8")]
    restart_evs = [e for e in events if e.get("type") == "supervisor.restart"]
    vision = metrics["engines"]["vision"]
    ready = all(vision.get("restart_ready", []))
    took = max(vision.get("restart_seconds", [99]))
    others = {k: v for k, v in metrics["engines"].items() if k != "vision"}
    others_ok = all(v.get("restarts", 0) == 0 for v in others.values())
    seq_ok = all(e.get("seq") == i for i, e in enumerate(events, 1))
    monoto = all(events[i]["ts"] <= events[i + 1]["ts"] for i in range(len(events) - 1))
    manifest = json.load(open(os.path.join(run_dir, "manifest.json"), encoding="utf-8"))
    packages = {k: len(v.get("packages", [])) for k, v in manifest["engines"].items()}
    ok = bool(restart_evs) and ready and took <= 5 and others_ok and seq_ok and monoto
    detail = {"restartSeconds": took, "restartReady": vision.get("restart_ready"),
              "restartEvents": len(restart_evs), "otherEnginesUntouched": others_ok,
              "seqContiguous": seq_ok, "tsMonotonic": monoto, "manifestPackages": packages,
              "manifestSnapshotBytes": len(manifest["config"].get("snapshot", ""))}
    return add("supervisor-restart", ok, detail)


def write_doc(number: str, elapsed: float):
    green = all(r["ok"] for r in results)
    path = os.path.join(SUITE, "docs", "verify-round-%s.md" % number)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# verify round %s" % number,
        "",
        "- 时间：%s" % time.strftime("%Y-%m-%d %H:%M:%S"),
        "- 用时：%.1fs" % elapsed,
        "- 结论：**%s**" % ("全绿 PASS" if green else "失败 FAIL"),
        "",
        "| 检查项 | 结果 | 证据 |",
        "| --- | --- | --- |",
    ]
    for r in results:
        ev = json.dumps(r["detail"], ensure_ascii=False).replace("|", "\\|")
        lines.append("| %s | %s | `%s` |" % (r["name"], "PASS" if r["ok"] else "FAIL", ev[:600]))
    lines.append("")
    open(path, "w", encoding="utf-8").write("\n".join(lines))
    return green, path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", required=True)
    args = ap.parse_args()
    started = time.time()
    step_clean()
    step_build()
    step_compile()
    step_assets()
    step_entries()
    step_locks()
    step_chains()
    step_frontend()
    step_supervisor()
    step_frontend_run()
    green, path = write_doc(args.round, time.time() - started)
    print(json.dumps({"round": args.round, "green": green, "doc": path,
                      "failed": [r["name"] for r in results if not r["ok"]]}, ensure_ascii=False))
    return 0 if green else 1


if __name__ == "__main__":
    raise SystemExit(main())
