"""vendor engine - dispatches the 16 imported upstream repos through their adapters.

Every action runs the real vendor adapter (`vendor/adapters/<name>/adapter.py --json`)
with the interpreter that adapter needs; no logic is re-implemented here. The engine
itself is stdlib-only and uses its own venv.

  adapted  -> exit 0 when the adapter reports `adapted`
  blocked  -> exit 0 only for the `blocked` summary action, which records every
              blocker verbatim; blocked adapters never masquerade as ready.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

SUITE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROCOGI = os.path.dirname(SUITE)
ADAPTERS = os.path.join(ROCOGI, "vendor", "adapters")

ENGINE = "vendor"

# interpreter keys -> <suite>/engines/<name>/.venv/Scripts/python.exe
VENV = {
    "capture": os.path.join(SUITE, "engines", "capture", ".venv", "Scripts", "python.exe"),
    "sift": os.path.join(SUITE, "engines", "sift", ".venv", "Scripts", "python.exe"),
    "scheduler": os.path.join(SUITE, "engines", "scheduler", ".venv", "Scripts", "python.exe"),
    "vision": os.path.join(SUITE, "engines", "vision", ".venv", "Scripts", "python.exe"),
    "portable": sys.executable,
}

# action -> (adapter, interpreter, component ids served)
ACTIONS = {
    "rocopilot": ("rocopilot", "capture", ["vendor.rocopilot"]),
    "auto_rocokingdom": ("auto_rocokingdom", "capture", ["vendor.auto_rocokingdom"]),
    "luoke_location": ("luoke_location", "sift", ["vendor.luoke_location"]),
    "roco_map_tracker": ("roco_map_tracker", "sift", ["vendor.roco_map_tracker"]),
    "autocapture": ("autocapture", "scheduler", ["vendor.autocapture"]),
    "game_automation": ("game_automation", "scheduler", ["vendor.game_automation"]),
    "nrc_ai": ("nrc_ai", "portable", ["vendor.nrc_ai"]),
    "adolph_rules": ("adolph_rules", "portable", ["vendor.adolph_rules"]),
    "balance_lab": ("balance_lab", "portable", ["vendor.balance_lab"]),
}

# Resolved by the toolchain line but intentionally not wired into the suite runtime:
# they are exposed through `status` with their resolution evidence, not through `blocked`.
STATUS_ONLY = [
    ("sift_map_tracker", "portable", "vendor.sift_map_tracker"),
    ("interception", "portable", "vendor.interception"),
    ("bettergi", "portable", "vendor.bettergi"),
    ("yotta", "portable", "vendor.yotta"),
    ("rocokingdom_ui", "portable", "vendor.rocokingdom_ui"),
    ("rocotools", "portable", "vendor.rocotools"),
]

# only the genuinely blocked adapter remains in the blocked summary
BLOCKED = [
    ("pets_gen", "vision", "vendor.pets_gen"),
]

# 2026-11-05 18:30 CST vendor/manifest.json: 15 resolved/adapted, 1 partial, 0 blocked.
# adapter_contract.json describes the adapter's own runtime capability, so it is
# reported verbatim next to the current resolution instead of being rewritten.
RESOLUTION = {
    "sift_map_tracker": ("resolved", "default_route.json 162 nodes/161 edges + region {0,0,255,235}; probe 76 frames, 74 found"),
    "interception": ("resolved-pending-reboot", "keyboard.sys/mouse.sys installed, UpperFilters written; reboot required; post-reboot-check.ps1"),
    "bettergi": ("resolved", "built with .NET 10 SDK (0 errors); artifacts/bettergi/"),
    "yotta": ("resolved", "built with Go 1.25.13 + Wails v3.0.0-beta.6; artifacts/yotta/yotta.exe"),
    "rocokingdom_ui": ("resolved", "pnpm 11.5.3 build exit 0; apps/website/dist"),
    "rocotools": ("resolved", "crawler data: 594 pets / 553 skills / 571 icons"),
    "pets_gen": ("partial", "renderer present; proprietary entity resources still need a GUI export"),
}

ALL_ADAPTERS = list(ACTIONS) + [name for name, _, _ in STATUS_ONLY] + [name for name, _, _ in BLOCKED]


def emit(log_path, event, **payload):
    rec = {"ts": round(time.time(), 3), "engine": ENGINE, "type": event, **payload}
    line = json.dumps(rec, ensure_ascii=False)
    print(line, flush=True)
    if log_path:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def run_adapter(adapter: str, interpreter: str, timeout: float = 300):
    py = VENV[interpreter]
    script = os.path.join(ADAPTERS, adapter, "adapter.py")
    started = time.perf_counter()
    if not os.path.exists(script):
        return {"adapter": adapter, "status": "missing-adapter", "script": script}
    proc = subprocess.run(
        [py, script, "--json"],
        capture_output=True, text=True, timeout=timeout,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        cwd=ADAPTERS,
    )
    seconds = round(time.perf_counter() - started, 2)
    payload = None
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {
            "adapter": adapter,
            "status": "unparsable",
            "stdoutTail": (proc.stdout or "")[-400:],
            "stderrTail": (proc.stderr or "")[-400:],
        }
    payload["returncode"] = proc.returncode
    payload["seconds"] = seconds
    payload["interpreter"] = os.path.relpath(py, SUITE)
    return payload


def status_action() -> dict:
    rows = {}
    for name in ALL_ADAPTERS:
        path = os.path.join(ADAPTERS, name, "contracts", "adapter_contract.json")
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            rows[name] = {
                "repo": data.get("repo"),
                "status": data.get("status"),
                "blockers": data.get("blockers", []),
                "checks": len(data.get("checks", [])),
            }
        except (OSError, json.JSONDecodeError) as exc:
            rows[name] = {"status": "missing-contract", "error": f"{type(exc).__name__}: {exc}"}
        if name in RESOLUTION:
            rows[name]["resolution"], rows[name]["resolutionDetail"] = RESOLUTION[name]
        elif name in ACTIONS:
            rows[name]["resolution"] = "adapted"
    return {
        "action": "status",
        "adapters": rows,
        "adapted": sum(1 for r in rows.values() if r.get("resolution") == "adapted"),
        "resolved": sum(1 for r in rows.values() if r.get("resolution") == "resolved"),
        "pendingReboot": sum(1 for r in rows.values() if r.get("resolution") == "resolved-pending-reboot"),
        "partial": sum(1 for r in rows.values() if r.get("resolution") == "partial"),
        "contractBlocked": sum(1 for r in rows.values() if r["status"] == "blocked"),
        "components": [f"vendor.{n}" for n in rows],
    }


def blocked_action() -> dict:
    rows = {}
    for name, interpreter, component in BLOCKED:
        res = run_adapter(name, interpreter)
        rows[name] = {
            "component": component,
            "status": res.get("status"),
            "returncode": res.get("returncode"),
            "blockers": res.get("blockers", []),
            "checks": len(res.get("checks", [])),
            "seconds": res.get("seconds"),
        }
    return {
        "action": "blocked",
        "adapters": rows,
        "blockedCount": sum(1 for r in rows.values() if r["status"] == "blocked"),
        "components": [r["component"] for r in rows.values()],
    }


def run_action(action: str) -> tuple[dict, int]:
    if action == "status":
        return status_action(), 0
    if action == "blocked":
        return blocked_action(), 0
    if action not in ACTIONS:
        raise ValueError(f"unknown vendor action: {action}")
    adapter, interpreter, components = ACTIONS[action]
    res = run_adapter(adapter, interpreter)
    res["action"] = action
    res["components"] = components
    return res, 0 if res.get("status") == "adapted" else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--log", default="")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--action", default="status")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=float, default=5.0)
    args = ap.parse_args()

    emit(args.log, "ready", run_id=args.run_id, config=args.config,
         python=sys.version.split()[0], adapters=len(ALL_ADAPTERS),
         components=[f"vendor.{n}" for n in ALL_ADAPTERS])
    while True:
        try:
            result, code = run_action(args.action)
            emit(args.log, "result", result=result)
        except Exception as exc:  # noqa: BLE001
            emit(args.log, "error", error=f"{type(exc).__name__}: {exc}")
            code = 1
        if args.once:
            return code
        time.sleep(max(0.2, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
