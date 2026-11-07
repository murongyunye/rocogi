"""Rocogi WebUI adapter + static server (stdlib only, no build step).

Serves work/rocogi/webui on 127.0.0.1:8800 and exposes /wapi/* that adapt the
real data sources: rocogi-suite runs/ logs/ CLI, components.toml, and the
Python 8787 / C 8788 backends. Read-only towards every source; it never writes
outside webui/.cache.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
import tomllib
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

WEBUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(WEBUI)                 # work/rocogi
WORK = os.path.dirname(ROOT)                  # work
SUITE = os.path.join(ROOT, "suite")
PYTHON = os.path.join(ROOT, ".toolchain", "python", "cpython-3.12.16-windows-x86_64-none", "python.exe")
CLI = os.path.join(SUITE, "kernel", "cli.py")
CACHE_DIR = os.path.join(WEBUI, ".cache")
ASSET_CACHE = os.path.join(CACHE_DIR, "assets_verify.json")
RELEASE_CACHE = os.path.join(CACHE_DIR, "release_sha.json")
VENDOR_MANIFEST = os.path.join(ROOT, "vendor", "manifest.json")
RELEASE_DIR = os.path.join(ROOT, "release")


def _read_version():
    try:
        with open(os.path.join(ROOT, "VERSION"), encoding="utf-8") as fh:
            return fh.read().strip() or "0.0.0"
    except OSError:
        return "0.0.0"


VERSION = _read_version()
RELEASE_DOC = os.path.join(ROOT, "docs", f"verify-release-{VERSION}.md")

PORT = 8800
HOST = "127.0.0.1"
PINNED_RUN = "side-live5"

ENGINE_LABELS = {
    "capture": ("截图", "截图引擎"),
    "vision": ("视觉", "视觉识别"),
    "input": ("输入", "输入引擎"),
    "sift": ("定位", "SIFT 定位"),
    "battle": ("对战", "对战引擎"),
    "scheduler": ("调度", "调度引擎"),
    "vendor": ("适配", "Vendor 适配引擎"),
}

# components.toml is authoritative; the suite only has these four actionable states.
COMPONENT_STATES = ("ready", "not-wired", "skipped", "blocked-vendor")
STATE_KEYS = {"ready": "ready", "not-wired": "notWired",
              "skipped": "skipped", "blocked-vendor": "blockedVendor"}

CHAINS = {
    "sift_locate": ("sift", "locate"),
    "sift_route": ("sift", "route"),
    "scheduler_fsm": ("scheduler", "fsm"),
    "battle_decide": ("battle", "responder"),
}

_cache_lock = threading.Lock()
_cache = {}


# --------------------------------------------------------------------- util
def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def read_toml(path):
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())


def upstream(port, path, timeout=8):
    url = f"http://127.0.0.1:{port}{path}"
    started = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return {"ok": True, "status": resp.status, "json": json.loads(raw),
                    "latencyMs": round((time.perf_counter() - started) * 1000, 1)}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": f"HTTP {exc.code} {path}", "latencyMs": None}
    except Exception as exc:  # noqa: BLE001 - backend may be down
        return {"ok": False, "status": None, "error": f"{type(exc).__name__}: {exc}", "latencyMs": None}


def cached(key, ttl, fn):
    with _cache_lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < ttl:
            return hit[1]
    value = fn()
    with _cache_lock:
        _cache[key] = (time.time(), value)
    return value


# --------------------------------------------------------- process inspection
def pid_alive(pid):
    if not pid:
        return False
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        handle = k32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        k32.CloseHandle(handle)
        return True
    except Exception:  # noqa: BLE001 - non-Windows / restricted environment
        return True


def _snapshot_processes():
    """Return {pid: (ppid, exe)} via Toolhelp32; empty when unavailable."""
    try:
        import ctypes
        from ctypes import wintypes

        class PROCESSENTRY32W(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                ("szExeFile", wintypes.WCHAR * 260),
            ]

        k32 = ctypes.windll.kernel32
        snap = k32.CreateToolhelp32Snapshot(0x2, 0)
        if not snap or snap == -1:
            return {}
        rows = {}
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = k32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            rows[int(entry.th32ProcessID)] = (int(entry.th32ParentProcessID), str(entry.szExeFile))
            ok = k32.Process32NextW(snap, ctypes.byref(entry))
        k32.CloseHandle(snap)
        return rows
    except Exception:  # noqa: BLE001
        return {}


def run_processes(engine_pids):
    """Count python processes in the supervisor tree (supervisor + engine mains + their workers)."""
    pids = [int(p) for p in engine_pids if p]
    if not pids:
        return None
    procs = _snapshot_processes()
    if not procs:
        return len(pids)
    children = {}
    for pid, (ppid, _name) in procs.items():
        children.setdefault(ppid, []).append(pid)
    root = procs.get(pids[0], (None, ""))[0]
    stack = [root] if root in procs else pids
    seen = set()
    while stack:
        pid = stack.pop()
        if pid in seen:
            continue
        seen.add(pid)
        stack.extend(children.get(pid, []))
    return sum(1 for pid in seen if procs.get(pid, (0, ""))[1].lower() in ("python.exe", "pythonw.exe"))


def sha256_file(path):
    size = os.path.getsize(path)
    stamp = int(os.path.getmtime(path))
    cache = read_json(RELEASE_CACHE, {}) or {}
    key = f"{os.path.basename(path)}:{size}:{stamp}"
    if key in cache:
        return cache[key]
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    value = digest.hexdigest()
    cache[key] = value
    write_json(RELEASE_CACHE, cache)
    return value


# ------------------------------------------------------------------- domain
def engine_meta(name):
    """Read one engine config leniently: a concurrently edited TOML must not break the UI."""
    path = os.path.join(SUITE, "config", "engines", f"{name}.toml")
    action, interval = name, 1.0
    try:
        data = read_toml(path).get("engine", {})
        action = data.get("action", action)
        interval = float(data.get("interval", interval))
    except (OSError, tomllib.TOMLDecodeError, KeyError, ValueError):
        try:
            text = open(path, encoding="utf-8").read()
        except OSError:
            text = ""
        m = re.search(r'^action\s*=\s*"([^"]+)"', text, re.M)
        action = m.group(1) if m else action
    venv_rel = f"engines/{name}/.venv"
    venv = os.path.join(SUITE, venv_rel, "Scripts", "python.exe")
    return action, interval, venv_rel, venv


def suite_meta():
    cfg = read_toml(os.path.join(SUITE, "config", "suite.toml"))
    registry = read_toml(os.path.join(SUITE, "config", "components.toml"))
    order = cfg["engines"]["order"]
    engines = []
    for name in order:
        action, interval, venv_rel, venv = engine_meta(name)
        comps = [c for c in registry["components"] if c["engine"] == name]
        label_short, label = ENGINE_LABELS.get(name, (name, name))
        engines.append({
            "name": name,
            "label": label,
            "short": label_short,
            "status": "ready" if os.path.exists(venv) else "not-wired",
            "action": action,
            "components": len(comps),
            "entry": f"rocogi-suite call {name} {action}",
            "venv": venv_rel,
        })
    return cfg, registry["components"], engines


def component_payload():
    cfg, registry, engines = suite_meta()
    usage = cached("usage", 30, lambda: upstream(8787, "/api/components", timeout=10).get("json") or {})
    usage_map = usage.get("usage", {}) if isinstance(usage, dict) else {}
    engine_status = {e["name"]: e["status"] for e in engines}
    groups = []
    stats = {"total": 0, "ready": 0, "notWired": 0, "skipped": 0, "blockedVendor": 0}
    for engine in engines:
        rows = []
        counts = {"total": 0, "ready": 0, "notWired": 0, "skipped": 0, "blockedVendor": 0}
        for comp in registry:
            if comp["engine"] != engine["name"]:
                continue
            declared = str(comp.get("status", "ready"))
            state = declared if declared in COMPONENT_STATES else "not-wired"
            reason = (comp.get("reason") or comp.get("note") or "").strip()
            if state == "ready" and engine_status[engine["name"]] != "ready":
                state = "not-wired"
                reason = reason or f"引擎 venv 缺失：{engine['venv']}"
            stats["total"] += 1
            counts["total"] += 1
            stats[STATE_KEYS[state]] += 1
            counts[STATE_KEYS[state]] += 1
            rows.append({
                "id": comp["id"],
                "declared": declared,
                "status": state,
                "reason": reason,
                "note": (comp.get("note") or "").strip(),
                "implemented": bool(comp.get("implemented", False)),
                "deps": comp.get("deps", []),
                "entry": comp.get("entry", ""),
                "config": comp.get("config", ""),
                "usedBy": usage_map.get(comp["id"], []),
            })
        groups.append({
            "engine": engine["name"],
            "label": engine["short"],
            "labelFull": engine["label"],
            "engineStatus": engine["status"],
            "counts": counts,
            "components": rows,
        })
    return {"groups": groups, "stats": stats, "states": list(COMPONENT_STATES),
            "sources": {"registry": "rocogi-suite/config/components.toml (0.4.0, 55 components)",
                        "usage": "8787 /api/components (usage map)"}}


RUN_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def run_summary(run_id):
    base = os.path.join(SUITE, "runs", run_id)
    manifest = read_json(os.path.join(base, "manifest.json"), {}) or {}
    metrics = read_json(os.path.join(base, "metrics.json"), {}) or {}
    events_path = os.path.join(base, "events.jsonl")
    events = 0
    if os.path.exists(events_path):
        with open(events_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.strip():
                    events += 1
    engines = metrics.get("engines", {})
    failed = [n for n, s in engines.items()
              if s.get("state") in ("failed", "timeout", "missing-venv")
              or (s.get("state") == "exited" and s.get("exitcode") not in (0, None))]
    running = [n for n, s in engines.items() if s.get("state") == "running"]
    running_pids = [s.get("pid") for n, s in engines.items() if s.get("state") == "running"]
    alive = [p for p in running_pids if pid_alive(p)]
    if not engines:
        status = "failed"
    elif failed:
        status = "failed"
    elif running and alive:
        status = "running"
    elif running:
        status = "stopped"
    else:
        status = "ok"
    mode = manifest.get("mode") or metrics.get("mode") or "unknown"
    if mode == "once":
        elapsed = [float(s.get("startup_seconds") or 0) + float(s.get("run_seconds") or 0)
                   for s in engines.values() if s.get("run_seconds") is not None]
        duration = round(max(elapsed), 2) if elapsed else None
    else:
        duration = metrics.get("duration")
    return {
        "run_id": run_id,
        "mode": mode,
        "started_at": manifest.get("started_at"),
        "duration": duration,
        "events": events,
        "status": status,
        "engineCount": len(engines),
        "runningEngines": len(running),
        "processes": run_processes(running_pids) if status == "running" else None,
        "pinned": run_id == PINNED_RUN,
        "failedEngines": failed,
        "engines": {n: s.get("state") for n, s in engines.items()},
    }


def list_runs(limit=60):
    runs_dir = os.path.join(SUITE, "runs")
    if not os.path.isdir(runs_dir):
        return []
    names = [n for n in os.listdir(runs_dir)
             if RUN_RE.match(n) and os.path.isdir(os.path.join(runs_dir, n))]
    names.sort(key=lambda n: os.path.getmtime(os.path.join(runs_dir, n)), reverse=True)
    out = []
    for name in names[:limit]:
        try:
            out.append(run_summary(name))
        except Exception:  # noqa: BLE001 - skip unreadable dirs
            continue
    return out


def read_jsonl_since(path, offset):
    if not os.path.exists(path):
        return {"lines": [], "nextOffset": 0, "size": 0}
    size = os.path.getsize(path)
    offset = max(0, min(int(offset or 0), size))
    lines = []
    with open(path, "rb") as fh:
        fh.seek(offset)
        chunk = fh.read()
    for raw in chunk.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            lines.append(json.loads(raw.decode("utf-8", "replace")))
        except json.JSONDecodeError:
            lines.append({"raw": raw.decode("utf-8", "replace")})
    return {"lines": lines, "nextOffset": size, "size": size}


def run_detail(run_id):
    base = os.path.join(SUITE, "runs", run_id)
    if not os.path.isdir(base):
        return None
    manifest = read_json(os.path.join(base, "manifest.json"), {}) or {}
    metrics = read_json(os.path.join(base, "metrics.json"), {}) or {}
    events = read_jsonl_since(os.path.join(base, "events.jsonl"), 0)["lines"]
    logs = []
    log_dir = os.path.join(SUITE, "logs", run_id)
    if os.path.isdir(log_dir):
        for name in sorted(os.listdir(log_dir)):
            if name.endswith(".jsonl"):
                path = os.path.join(log_dir, name)
                logs.append({"engine": name[:-6], "bytes": os.path.getsize(path)})
    snapshot = manifest.get("config", {}).get("snapshot", "")
    return {
        "run_id": run_id,
        "summary": run_summary(run_id),
        "manifest": {
            "schema_version": manifest.get("schema_version"),
            "mode": manifest.get("mode"),
            "started_at": manifest.get("started_at"),
            "config": {k: v for k, v in (manifest.get("config", {}) or {}).items() if k != "snapshot"},
            "configSnapshotBytes": len(snapshot),
            "engines": manifest.get("engines", {}),
            "components": manifest.get("components", []),
        },
        "metrics": metrics,
        "events": events,
        "logs": logs,
    }


def assets_payload():
    manifest = read_json(os.path.join(SUITE, "assets", "manifest.json"), {}) or {}
    verify = read_json(ASSET_CACHE)
    return {"manifest": manifest, "verify": verify}


def vendor_payload():
    """Repository-level resolution from vendor/manifest.json.

    This is deliberately a different vocabulary from suite component status:
    repo resolution (15 resolved / 1 partial / 0 blocked) is not the same axis
    as components.toml status (44 ready / 6 not-wired / 1 skipped / 4 blocked-vendor).
    """
    manifest = read_json(VENDOR_MANIFEST, {}) or {}
    repos = []
    resolved = partial = blocked = 0
    blocked_items, pending = [], []
    for repo in manifest.get("repos", []):
        resolution = repo.get("resolution") or {}
        declared = repo.get("status")
        if declared == "partial":
            state = "partial"
            partial += 1
        elif declared == "blocked":
            state = "blocked"
            blocked += 1
        else:
            state = "resolved"
            resolved += 1
        item = {
            "repo": repo.get("repo"),
            "declared": declared,
            "status": state,
            "license": repo.get("license"),
            "size": repo.get("size"),
            "languages": repo.get("languages"),
            "entrypoints": repo.get("entrypoints", []),
            "buildRequirements": repo.get("build_requirements", []),
            "verifiedAt": repo.get("verified_at"),
            "resolution": {
                "done": resolution.get("done"),
                "stillBlocked": resolution.get("still_blocked"),
                "note": resolution.get("note"),
                "toolchains": resolution.get("toolchains", []),
                "activationPendingReboot": bool(resolution.get("activation_pending_reboot")),
                "postRebootCheck": resolution.get("post_reboot_check"),
            },
        }
        if resolution.get("still_blocked"):
            blocked_items.append({"repo": repo.get("repo"), "status": state,
                                  "reason": resolution.get("still_blocked")})
        if resolution.get("activation_pending_reboot"):
            check = resolution.get("post_reboot_check") or {}
            pending.append({
                "repo": repo.get("repo"),
                "note": resolution.get("note"),
                "script": check.get("script"),
                "autoReboot": check.get("auto_reboot"),
                "preRebootResult": check.get("pre_reboot_result"),
            })
        repos.append(item)
    repos.sort(key=lambda r: (r["status"] != "partial", r["repo"] or ""))
    summary = {
        "total": len(repos), "resolved": resolved, "partial": partial, "blocked": blocked,
        "reposDeclared": (manifest.get("status_summary") or {}),
        "totalBytes": manifest.get("total_bytes"),
        "generatedAt": manifest.get("generated_at"),
        "sourceRoot": manifest.get("source_root"),
    }
    return {"summary": summary, "repos": repos, "blockedItems": blocked_items,
            "pendingReboot": pending,
            "note": "仓级 resolution 状态（15 resolved / 1 partial / 0 blocked）与 suite 组件的 "
                    "blocked-vendor 状态是两套口径，不可相加或混用。",
            "sources": {"manifest": "rocogi/vendor/manifest.json",
                        "components": "rocogi-suite/config/components.toml"}}


def release_payload():
    text = ""
    try:
        with open(RELEASE_DOC, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        pass
    verified_at = None
    m = re.search(r"- 时间：([^\n]+)", text)
    if m:
        verified_at = m.group(1).strip()
    doc_rows = {}
    for m in re.finditer(r"\| `release/(rocogi-[^`]+\.zip)` \| ([^|]+) \| ([0-9,]+) \| ([^|]+) \|", text):
        doc_rows[m.group(1)] = {
            "sizeLabel": m.group(2).strip(),
            "files": int(m.group(3).replace(",", "")),
            "contents": re.sub(r"\*\*|`", "", m.group(4)).strip(),
        }
    packages, others = [], []
    if os.path.isdir(RELEASE_DIR):
        for name in sorted(os.listdir(RELEASE_DIR)):
            if not name.endswith(".zip"):
                continue
            path = os.path.join(RELEASE_DIR, name)
            item = {"name": name, "bytes": os.path.getsize(path),
                    "sizeLabel": doc_rows.get(name, {}).get("sizeLabel"),
                    "files": doc_rows.get(name, {}).get("files"),
                    "contents": doc_rows.get(name, {}).get("contents")}
            if name.startswith(f"rocogi-{VERSION}-"):
                digest = sha256_file(path)
                item.update({"sha256": digest, "sha8": digest[:8]})
                packages.append(item)
            else:
                others.append(item)
    highlights = []
    if "python -m compileall suite backend" in text:
        highlights.append("两个包内 `python -m compileall suite backend` 均 exit 0")
    if "interception=false" in text:
        highlights.append(f"解压后后端 `/api/health` 200、version={VERSION}；interception=false（待重启）、sift=true")
    return {"version": VERSION, "docPath": f"docs/verify-release-{VERSION}.md",
            "verifiedAt": verified_at, "packages": packages, "otherPackages": others,
            "highlights": highlights,
            "sources": {"doc": f"rocogi/docs/verify-release-{VERSION}.md", "dir": "rocogi/release"}}


def run_assets_verify():
    script = os.path.join(SUITE, "assets", "verify.py")
    py = os.path.join(SUITE, "engines", "sift", ".venv", "Scripts", "python.exe")
    started = time.perf_counter()
    proc = subprocess.run([py, script], capture_output=True, text=True, timeout=180,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": (proc.stderr or proc.stdout or "verify failed")[-800:]}
    result["seconds"] = round(time.perf_counter() - started, 2)
    result["cachedAt"] = now_iso()
    write_json(ASSET_CACHE, result)
    return result


def last_json_object(text):
    """The supervisor prints a compact manifest line, then a pretty-printed result."""
    decoder = json.JSONDecoder()
    last, idx = None, 0
    while True:
        start = text.find("{", idx)
        if start < 0:
            return last
        try:
            obj, end = decoder.raw_decode(text[start:])
            last = obj
            idx = start + end
        except json.JSONDecodeError:
            idx = start + 1


def run_cli(args, timeout):
    cmd = [PYTHON, CLI] + args
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    started = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, creationflags=flags)
    return proc, round(time.perf_counter() - started, 2)


def trigger_chain(chain):
    if chain not in CHAINS and chain != "suite_run":
        return None, "unknown chain"
    if chain == "suite_run":
        run_id = "ui-" + time.strftime("%Y%m%d-%H%M%S")
        proc, seconds = run_cli(["run", "--once", "--timeout", "120", "--run-id", run_id], timeout=240)
        payload = last_json_object(proc.stdout) or {}
        if not payload.get("events"):
            return None, (proc.stderr or proc.stdout or "run failed")[-800:]
        return {
            "ok": proc.returncode == 0,
            "chain": chain,
            "run_id": run_id,
            "seconds": seconds,
            "events": payload.get("events"),
            "metrics": payload.get("metrics"),
            "summary": run_summary(run_id),
        }, None
    engine, action = CHAINS[chain]
    run_id = "call-" + time.strftime("%Y%m%d-%H%M%S")
    proc, seconds = run_cli(["call", engine, action, "--run-id", run_id, "--timeout", "240"], timeout=300)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None, (proc.stderr or proc.stdout or "call failed")[-800:]
    return {
        "ok": payload.get("status") == "ok",
        "chain": chain,
        "run_id": run_id,
        "engine": engine,
        "action": action,
        "status": payload.get("status"),
        "seconds": seconds,
        "result": payload.get("result"),
        "log": payload.get("log"),
        "error": payload.get("error"),
    }, None


def overview_payload():
    cfg, registry, engines = suite_meta()
    py_health = upstream(8787, "/api/health")
    c_health = upstream(8788, "/api/health")
    comp_stats = component_payload()["stats"]
    vendor = cached("vendor", 120, vendor_payload)
    release = cached("release", 900, release_payload)
    runs = list_runs(40)
    suite_runs = [r for r in runs if r["mode"] in ("once", "supervised")]
    pinned = next((r for r in runs if r["run_id"] == PINNED_RUN), None)
    latest = suite_runs[0] if suite_runs else (runs[0] if runs else None)
    current = pinned or latest
    py_json = py_health.get("json") or {}
    c_json = c_health.get("json") or {}
    summary = (f"{comp_stats['total']} 组件：{comp_stats['ready']} ready / "
               f"{comp_stats['notWired']} not-wired / {comp_stats['skipped']} skipped / "
               f"{comp_stats['blockedVendor']} blocked-vendor")
    return {
        "generatedAt": now_iso(),
        "backends": {
            "python": {"ok": py_health["ok"], "status": py_health.get("status"),
                       "port": 8787, "role": "Python 后端",
                       "latencyMs": py_health.get("latencyMs"),
                       "version": py_json.get("version"),
                       "activeRuns": py_json.get("activeRuns"),
                       "error": py_health.get("error")},
            "c": {"ok": c_health["ok"], "status": c_health.get("status"),
                  "port": 8788, "role": "C 核心",
                  "latencyMs": c_health.get("latencyMs"),
                  "version": c_json.get("version"),
                  "uptimeMs": c_json.get("uptime_ms"),
                  "error": c_health.get("error")},
            "suite": {"ok": True, "version": cfg["suite"]["version"],
                      "root": os.path.relpath(SUITE, WORK)},
        },
        "versions": {"suite": cfg["suite"]["version"],
                     "python": py_json.get("version"),
                     "c": c_json.get("version")},
        "engines": engines,
        "componentStats": comp_stats,
        "componentSummary": summary,
        "currentRun": current,
        "pinnedRun": pinned,
        "latestRun": latest,
        "runCount": len(runs),
        "recentRuns": suite_runs[:8],
        "vendor": {"summary": vendor["summary"], "blockedItems": vendor["blockedItems"],
                   "pendingReboot": vendor["pendingReboot"], "note": vendor["note"]},
        "release": {"version": release["version"], "docPath": release["docPath"],
                    "verifiedAt": release["verifiedAt"], "packages": release["packages"],
                    "highlights": release["highlights"]},
    }


# ------------------------------------------------------------------- routing
class Handler(BaseHTTPRequestHandler):
    server_version = "rocogi-webui/0.1"

    def log_message(self, fmt, *args):  # quieter console
        return

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path):
        if not os.path.isfile(path):
            self.send_json({"ok": False, "error": "not found"}, 404)
            return
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as fh:
            body = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text/") else ""))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        try:
            if path.startswith("/wapi/"):
                return self.handle_api(path, query, None)
            if path == "/":
                return self.send_file(os.path.join(WEBUI, "index.html"))
            rel = path.lstrip("/")
            target = os.path.normpath(os.path.join(WEBUI, rel))
            if not target.startswith(WEBUI):
                return self.send_json({"ok": False, "error": "forbidden"}, 403)
            return self.send_file(target)
        except BrokenPipeError:
            return
        except Exception as exc:  # noqa: BLE001
            return self.send_json({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}") if length else {}
        except json.JSONDecodeError:
            return self.send_json({"ok": False, "error": "invalid json"}, 400)
        try:
            return self.handle_api(parsed.path, parse_qs(parsed.query), body)
        except Exception as exc:  # noqa: BLE001
            return self.send_json({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 500)

    def handle_api(self, path, query, body):
        if path == "/wapi/overview":
            return self.send_json(overview_payload())
        if path == "/wapi/components":
            return self.send_json(component_payload())
        if path == "/wapi/vendor":
            return self.send_json(cached("vendor", 120, vendor_payload))
        if path == "/wapi/release":
            return self.send_json(cached("release", 900, release_payload))
        if path == "/wapi/workflows":
            flows = upstream(8787, "/api/workflows", timeout=10)
            nodes = upstream(8787, "/api/nodes", timeout=10)
            catalog = {}
            if nodes["ok"]:
                for node in nodes["json"].get("nodes", []):
                    catalog[node["type"]] = {k: node.get(k) for k in
                                             ("title", "category", "categoryLabel", "accent", "description")}
            if not flows["ok"]:
                return self.send_json({"ok": False, "error": flows.get("error"),
                                       "workflows": [], "nodeCatalog": {}}, 503)
            return self.send_json({"ok": True, "workflows": flows["json"], "nodeCatalog": catalog})
        if path == "/wapi/runs":
            limit = int(query.get("limit", ["60"])[0])
            return self.send_json({"runs": list_runs(limit)})
        match = re.match(r"^/wapi/runs/([A-Za-z0-9._-]+)(/.*)?$", path)
        if match:
            run_id, rest = match.group(1), match.group(2) or ""
            if rest == "":
                detail = run_detail(run_id)
                if detail is None:
                    return self.send_json({"ok": False, "error": f"run not found: {run_id}"}, 404)
                return self.send_json(detail)
            if rest == "/events":
                offset = int(query.get("offset", ["0"])[0])
                return self.send_json(read_jsonl_since(
                    os.path.join(SUITE, "runs", run_id, "events.jsonl"), offset))
            log = re.match(r"^/logs/([A-Za-z0-9._-]+)$", rest)
            if log:
                offset = int(query.get("offset", ["0"])[0])
                data = read_jsonl_since(
                    os.path.join(SUITE, "logs", run_id, f"{log.group(1)}.jsonl"), offset)
                data["engine"] = log.group(1)
                return self.send_json(data)
        if path == "/wapi/assets":
            return self.send_json(assets_payload())
        if path == "/wapi/assets/verify":
            if body is None:
                return self.send_json({"ok": False, "error": "POST required"}, 405)
            return self.send_json(run_assets_verify())
        if path == "/wapi/trigger":
            if body is None:
                return self.send_json({"ok": False, "error": "POST required"}, 405)
            result, error = trigger_chain(str((body or {}).get("chain")))
            if error:
                return self.send_json({"ok": False, "error": error}, 400)
            return self.send_json(result)
        if path == "/wapi/bridge":
            port = query.get("port", ["8787"])[0]
            target = query.get("path", ["/api/health"])[0]
            if port not in ("8787", "8788") or not target.startswith("/api/"):
                return self.send_json({"ok": False, "error": "port/path not allowed"}, 400)
            res = upstream(port, target, timeout=15)
            return self.send_json(res.get("json") if res["ok"] else res, 200 if res["ok"] else 502)
        return self.send_json({"ok": False, "error": f"unknown endpoint {path}"}, 404)


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("image/svg+xml", ".svg")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"rocogi webui on http://{HOST}:{PORT}  (suite={SUITE})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
