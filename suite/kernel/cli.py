"""rocogi-suite CLI - run | engines | assets | evidence | call."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from suite import Suite, load_toml, tail_events  # noqa: E402

SUITE = Suite()


def jprint(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


# --------------------------------------------------------------------------
# component registry
# --------------------------------------------------------------------------
def entry_points() -> list[dict]:
    """Distinct executable entry per component registry: rocogi-suite call <engine> <action>."""
    seen: dict[tuple[str, str], dict] = {}
    for comp in SUITE.components():
        parts = str(comp.get("entry", "")).split()
        if len(parts) < 4 or parts[1] != "call":
            continue
        key = (parts[2], parts[3])
        row = seen.setdefault(key, {"engine": parts[2], "action": parts[3], "components": []})
        row["components"].append(comp["id"])
    return list(seen.values())


def cmd_engines(args) -> int:
    rows = SUITE.component_table()
    engines = []
    for name in SUITE.engine_names():
        cfg = SUITE.engine_cfg(name)
        comps = [r for r in rows if r["engine"] == name]
        engines.append(
            {
                "engine": name,
                "status": SUITE.engine_status(name),
                "action": cfg["engine"]["action"],
                "config": os.path.relpath(SUITE.engine_config(name), SUITE.root),
                "venv": cfg["engine"]["venv"],
                "python": os.path.relpath(SUITE.engine_python(name), SUITE.root),
                "components": len(comps),
                "entry": f"rocogi-suite call {name} {cfg['engine']['action']}",
            }
        )

    entries = entry_points()
    summary = {
        "engines": engines,
        "components": {
            "total": len(rows),
            "ready": sum(1 for r in rows if r["status"] == "ready"),
            "notWired": sum(1 for r in rows if r["status"] == "not-wired"),
            "skipped": sum(1 for r in rows if r["status"] == "skipped"),
            "blockedVendor": sum(1 for r in rows if r["status"] == "blocked-vendor"),
            "missingDeps": sum(1 for r in rows if r["status"] == "missing-deps"),
            "implemented": sum(1 for r in rows if r["implemented"]),
        },
        "entries": {
            "total": len(entries),
            "list": [f"{e['engine']} {e['action']}" for e in entries],
        },
    }

    if args.verify:
        # verify every distinct component entry, not just each engine's default action
        verified = []
        run_id = "verify-" + time.strftime("%H%M%S")
        for entry in entries:
            started = time.perf_counter()
            res = call_engine(entry["engine"], entry["action"], run_id=run_id, timeout=180)
            ok = res.get("status") == "ok" and res.get("result") is not None
            verified.append(
                {
                    "entry": f"{entry['engine']} {entry['action']}",
                    "components": entry["components"],
                    "ok": ok,
                    "seconds": round(time.perf_counter() - started, 2),
                    "status": res.get("status"),
                    "error": res.get("error"),
                    "resultTail": _tail(res.get("result")),
                }
            )
        failed = [v for v in verified if not v["ok"]]
        ready_without_entry = []
        summary["verify"] = verified
        summary["verifySummary"] = {
            "ok": len(verified) - len(failed),
            "failed": len(failed),
            "total": len(verified),
            "failedEntries": [v["entry"] for v in failed],
        }
        summary["engineStatus"] = {n: SUITE.engine_status(n) for n in SUITE.engine_names()}
        summary["unverifiedComponents"] = [
            r["id"] for r in rows if r["status"] == "ready" and r["engine"] not in SUITE.engine_names()
        ] + ready_without_entry

    if args.components or args.json:
        summary["componentTable"] = rows
    jprint(summary)
    if args.verify:
        return 0 if summary["verifySummary"]["failed"] == 0 else 1
    return 0


def _tail(result, limit: int = 1200):
    if result is None:
        return None
    text = json.dumps(result, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "..."


# --------------------------------------------------------------------------
# single engine call
# --------------------------------------------------------------------------
def call_engine(name: str, action: str | None, run_id: str, timeout: float = 180) -> dict:
    py = SUITE.engine_python(name)
    if not os.path.exists(py):
        return {"engine": name, "status": "missing-venv", "path": py}
    script = SUITE.engine_script(name)
    action = action or SUITE.engine_cfg(name)["engine"]["action"]
    log_dir = SUITE.log_dir(run_id)
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{name}.jsonl")
    cmd = [py, script, "--config", SUITE.engine_config(name), "--log", log_path,
           "--run-id", run_id, "--action", action, "--once"]
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    started = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, creationflags=flags)
    except subprocess.TimeoutExpired:
        return {"engine": name, "action": action, "status": "timeout", "timeout": timeout,
                "seconds": round(time.perf_counter() - started, 2), "log": log_path}

    seconds = round(time.perf_counter() - started, 3)
    events = tail_events(log_path, 4)
    result = None
    error = None
    for ev in events:
        if ev.get("type") == "result":
            result = ev.get("result")
        if ev.get("type") == "error":
            error = ev.get("error")
    return {
        "engine": name,
        "action": action,
        "status": "ok" if proc.returncode == 0 and error is None else "failed",
        "returncode": proc.returncode,
        "seconds": seconds,
        "log": os.path.relpath(log_path, SUITE.root),
        "result": result,
        "error": error or (proc.stderr.strip().splitlines()[-1] if proc.returncode and proc.stderr else None),
    }


def cmd_call(args) -> int:
    run_id = args.run_id or ("call-" + SUITE.new_run_id())
    res = call_engine(args.engine, args.action, run_id, timeout=args.timeout)
    jprint(res)
    return 0 if res["status"] == "ok" else 1


# --------------------------------------------------------------------------
# assets
# --------------------------------------------------------------------------
def cmd_assets(args) -> int:
    py = SUITE.engine_python("sift")
    script = SUITE.path("assets", "build.py" if args.action == "build" else "verify.py")
    if not os.path.exists(py):
        jprint({"ok": False, "error": "sift engine venv missing", "python": py})
        return 2
    proc = subprocess.run([py, script], capture_output=True, text=True, timeout=600)
    print(proc.stdout)
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
    return proc.returncode


# --------------------------------------------------------------------------
# evidence
# --------------------------------------------------------------------------
def _read_jsonl(path: str) -> list:
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _merge_events(run_id: str, path: str) -> int:
    """Merge supervisor + per-engine logs without truncating supervisor-only events.

    Previous implementation opened the target with "w" *before* reading it, which
    dropped supervisor.restart rows appended during the run.
    """
    collected = _read_jsonl(path)  # supervisor events written during the run
    for name in SUITE.engine_names():
        collected.extend(_read_jsonl(os.path.join(SUITE.log_dir(run_id), f"{name}.jsonl")))
    collected.sort(key=lambda ev: (float(ev.get("ts") or 0), str(ev.get("engine") or ""), str(ev.get("type") or "")))
    with open(path, "w", encoding="utf-8") as out:
        for seq, ev in enumerate(collected, 1):
            ev["seq"] = seq
            out.write(json.dumps(ev, ensure_ascii=False) + "\n")
    return len(collected)


def _log_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def _wait_ready(log_path: str, offset: int, deadline: float) -> bool:
    while time.time() < deadline:
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
                fh.seek(offset)
                for line in fh:
                    try:
                        ev = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if ev.get("type") == "ready":
                        return True
        time.sleep(0.05)
    return False


def cmd_run(args) -> int:
    run_id = args.run_id or SUITE.new_run_id()
    engines = [args.engine] if args.engine else SUITE.engine_names()
    os.makedirs(SUITE.run_dir(run_id), exist_ok=True)
    os.makedirs(SUITE.log_dir(run_id), exist_ok=True)

    runtime = SUITE.cfg["runtime"]
    startup_timeout = float(runtime.get("startup_timeout_sec", 60))
    restart_backoff = float(runtime.get("restart_backoff_sec", 0.5))

    manifest = SUITE.write_manifest(run_id, engines, "once" if args.once else "supervised",
                                    extra={"requested": {"engines": engines, "once": args.once,
                                                         "startup_timeout_sec": startup_timeout,
                                                         "restart_backoff_sec": restart_backoff}})
    print(json.dumps({"run_id": run_id, "manifest": os.path.relpath(os.path.join(SUITE.run_dir(run_id), "manifest.json"), SUITE.root),
                      "configSha256": manifest["config"]["sha256"], "engines": engines}, ensure_ascii=False))

    procs = {}
    metrics = {n: {"pid": None, "started_at": None, "startup_seconds": None, "restarts": 0,
                   "restart_seconds": [], "restart_ready": [], "state": "pending"} for n in engines}
    offsets = {}
    for name in engines:
        log_path = os.path.join(SUITE.log_dir(run_id), f"{name}.jsonl")
        offsets[name] = _log_size(log_path)
        spawned_at = time.time()
        spawned_perf = time.perf_counter()
        info = SUITE.spawn(name, run_id, once=args.once, action=args.action, interval=args.interval,
                           mode="once" if args.once else "supervised")
        if info["status"] == "started":
            procs[name] = info["proc"]
            metrics[name].update({"pid": info["pid"], "started_at": spawned_at, "state": "running"})
            ready = _wait_ready(log_path, offsets[name], time.time() + startup_timeout)
            metrics[name]["startup_seconds"] = round(time.perf_counter() - spawned_perf, 3)
            metrics[name]["startup_ready"] = ready
            if not ready and not args.once:
                metrics[name]["state"] = "startup-timeout"
        else:
            metrics[name]["state"] = info["status"]

    # WebUI reads runs/<id>/metrics.json; without it a live supervised run shows as
    # "failed". Write the startup snapshot immediately, then overwrite at the end.
    SUITE.write_json(os.path.join(SUITE.run_dir(run_id), "metrics.json"), {
        "run_id": run_id,
        "mode": "once" if args.once else "supervised",
        "duration": args.duration,
        "startup_timeout_sec": startup_timeout,
        "restart_backoff_sec": restart_backoff,
        "engines": {k: {kk: vv for kk, vv in v.items() if kk != "proc"} for k, v in metrics.items()},
        "eventsMerged": 0,
    })

    if args.once:
        for name, proc in procs.items():
            started = time.time()
            try:
                proc.wait(timeout=args.timeout)
                metrics[name]["state"] = "exited"
                metrics[name]["exitcode"] = proc.returncode
            except subprocess.TimeoutExpired:
                proc.kill()
                metrics[name]["state"] = "timeout"
            metrics[name]["run_seconds"] = round(time.time() - started, 3)
    else:
        deadline = time.time() + args.duration if args.duration else None
        loop_start = time.perf_counter()
        kill_done = False
        try:
            while True:
                if args.kill_after and not kill_done and time.perf_counter() - loop_start > args.kill_after:
                    target = args.kill_engine or engines[0]
                    victim = procs.get(target)
                    if victim and victim.poll() is None:
                        victim.kill()
                    kill_done = True
                for name in list(procs):
                    proc = procs[name]
                    if proc.poll() is None:
                        continue
                    metrics[name]["state"] = "exited"
                    metrics[name]["exitcode"] = proc.returncode
                    if metrics[name]["restarts"] >= SUITE.cfg["runtime"]["max_restarts"]:
                        continue
                    killed_at = time.time()
                    killed_perf = time.perf_counter()
                    time.sleep(restart_backoff)
                    log_path = os.path.join(SUITE.log_dir(run_id), f"{name}.jsonl")
                    offsets[name] = _log_size(log_path)
                    info = SUITE.spawn(name, run_id, once=False, action=args.action, interval=args.interval, mode="restart")
                    ready = _wait_ready(log_path, offsets[name], time.time() + startup_timeout)
                    took = round(time.perf_counter() - killed_perf, 3)
                    metrics[name]["restarts"] += 1
                    metrics[name]["restart_seconds"].append(took)
                    metrics[name]["restart_ready"].append(ready)
                    metrics[name].update({"pid": info.get("pid"), "state": "running"})
                    if info["status"] == "started":
                        procs[name] = info["proc"]
                    with open(os.path.join(SUITE.run_dir(run_id), "events.jsonl"), "a", encoding="utf-8") as fh:
                        fh.write(json.dumps({"ts": killed_at, "engine": name, "type": "supervisor.restart",
                                             "restarts": metrics[name]["restarts"], "ready": ready,
                                             "took_s": took, "backoff_s": restart_backoff},
                                            ensure_ascii=False) + "\n")
                if deadline and time.time() > deadline:
                    break
                time.sleep(float(SUITE.cfg["runtime"]["poll_sec"]))
        except KeyboardInterrupt:
            pass
        finally:
            for proc in procs.values():
                if proc.poll() is None:
                    proc.terminate()

    events = _merge_events(run_id, os.path.join(SUITE.run_dir(run_id), "events.jsonl"))
    metrics_out = {
        "run_id": run_id,
        "mode": "once" if args.once else "supervised",
        "duration": args.duration,
        "startup_timeout_sec": startup_timeout,
        "restart_backoff_sec": restart_backoff,
        "engines": {k: {kk: vv for kk, vv in v.items() if kk != "proc"} for k, v in metrics.items()},
        "eventsMerged": events,
    }
    SUITE.write_json(os.path.join(SUITE.run_dir(run_id), "metrics.json"), metrics_out)
    jprint({"run_id": run_id, "events": events, "metrics": os.path.relpath(os.path.join(SUITE.run_dir(run_id), "metrics.json"), SUITE.root)})
    return 0


def cmd_evidence(args) -> int:
    if args.run:
        run_id = args.run
    else:
        runs = sorted(os.listdir(SUITE.runs_dir)) if os.path.exists(SUITE.runs_dir) else []
        runs = [r for r in runs if os.path.isdir(SUITE.run_dir(r)) and not r.startswith("call-") and not r.startswith("verify-")]
        if not runs:
            jprint({"error": "no runs found"})
            return 2
        run_id = runs[-1]
    d = SUITE.run_dir(run_id)
    manifest = SUITE.load_json(os.path.join(d, "manifest.json"), {})
    metrics = SUITE.load_json(os.path.join(d, "metrics.json"), {})
    events_path = os.path.join(d, "events.jsonl")
    counts = {}
    seq_gaps = 0
    last_seq = 0
    for ev in _read_jsonl(events_path):
        key = f"{ev.get('engine')}:{ev.get('type')}"
        counts[key] = counts.get(key, 0) + 1
        seq = ev.get("seq")
        if isinstance(seq, int):
            if seq != last_seq + 1:
                seq_gaps += 1
            last_seq = seq
    jprint({
        "run_id": run_id,
        "dir": os.path.relpath(d, SUITE.root),
        "mode": manifest.get("mode"),
        "configSha256": manifest.get("config", {}).get("sha256"),
        "configSnapshotBytes": len(manifest.get("config", {}).get("snapshot", "")),
        "engineVersions": {k: v.get("python") for k, v in manifest.get("engines", {}).items()},
        "enginePackages": {k: len(v.get("packages", [])) for k, v in manifest.get("engines", {}).items()},
        "metrics": metrics.get("engines", {}),
        "eventsByType": counts,
        "eventSeqGaps": seq_gaps,
    })
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="rocogi-suite")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("engines", help="list engines + 39 component registry")
    p.add_argument("--json", action="store_true")
    p.add_argument("--components", action="store_true")
    p.add_argument("--verify", action="store_true", help="run every distinct component entry and check structured output")
    p.set_defaults(func=cmd_engines)

    p = sub.add_parser("call", help="call one engine action once")
    p.add_argument("engine")
    p.add_argument("action", nargs="?")
    p.add_argument("--run-id", default="")
    p.add_argument("--timeout", type=float, default=180)
    p.set_defaults(func=cmd_call)

    p = sub.add_parser("run", help="launch all engines under one supervisor")
    p.add_argument("--engine", default="")
    p.add_argument("--action", default=None)
    p.add_argument("--interval", type=float, default=None)
    p.add_argument("--once", action="store_true")
    p.add_argument("--duration", type=float, default=8.0)
    p.add_argument("--timeout", type=float, default=120)
    p.add_argument("--run-id", default="")
    p.add_argument("--kill-after", type=float, default=None, help="kill one engine mid-run to exercise restart")
    p.add_argument("--kill-engine", default="")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("assets", help="build or verify asset manifest")
    p.add_argument("action", choices=["build", "verify"])
    p.set_defaults(func=cmd_assets)

    p = sub.add_parser("evidence", help="summarise a run")
    p.add_argument("--run", default="")
    p.set_defaults(func=cmd_evidence)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
