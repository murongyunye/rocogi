from __future__ import annotations

import argparse
import importlib
import json
import sys
from typing import Any, Dict

from .components import build_registry

ENGINE_MODULES = {
    "sense": "app.engine_sense",
    "input": "app.engine_input",
    "sift": "app.engine_sift",
    "battle": "app.engine_battle",
    "flow": "app.engine_flow",
    "core": "app.engine_core",
}


def _parser(default_engine: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rocogi-engine",
        description="Rocogi headless engine: component groups as JSON-over-CLI executables.",
    )
    parser.add_argument("--engine", choices=sorted(ENGINE_MODULES), default=default_engine)
    parser.add_argument("--action", help="action name, e.g. capture / press / locate / analyze / run")
    parser.add_argument("--params", default="{}", help="JSON object with action parameters")
    parser.add_argument("--settings", help="optional settings JSON file")
    parser.add_argument("--stdin", action="store_true", help="read {engine,action,params} JSON from stdin")
    parser.add_argument("--list", action="store_true", help="print component library, groups and gaps")
    parser.add_argument("--pretty", action="store_true")
    return parser


def _read_stdin() -> Dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def main(default_engine: str = "core") -> int:
    parser = _parser(default_engine)
    args = parser.parse_args()
    engine = str(args.engine)
    action = str(args.action or "")
    params: Dict[str, Any] = {}

    try:
        payload = _read_stdin() if args.stdin else {}
        if not isinstance(payload, dict):
            raise ValueError("stdin 必须是 JSON object: {engine, action, params}")
        engine = str(payload.get("engine") or args.engine)
        action = str(payload.get("action") or args.action or "")
        if engine not in ENGINE_MODULES:
            raise ValueError(f"未知引擎: {engine}，可选: {', '.join(sorted(ENGINE_MODULES))}")
        raw_params = payload.get("params") or {}
        if not isinstance(raw_params, dict):
            raise ValueError("params 必须是 JSON object")
        params = dict(raw_params)
        if args.params and args.params != "{}":
            override = json.loads(args.params)
            if not isinstance(override, dict):
                raise ValueError("--params 必须是 JSON object")
            params = {**params, **override}
        if args.settings:
            params["settings"] = args.settings

        if args.list:
            engine = "core"
            action = "library"
        if action in ("library", "groups") and engine == "core":
            module = importlib.import_module(ENGINE_MODULES["core"])
            result = module.dispatch(action, params)
            output = {"ok": True, "engine": engine, "action": action, "result": result}
        elif args.list or action in ("library", "groups"):
            registry = build_registry()
            output = {
                "ok": True,
                "engine": engine,
                "action": action or "library",
                "result": {
                    "version": registry["version"],
                    "stats": registry["stats"],
                    "groups": registry["groups"],
                    "gaps": registry["gaps"],
                },
            }
        else:
            module = importlib.import_module(ENGINE_MODULES[engine])
            if not action:
                output = {
                    "ok": True,
                    "engine": engine,
                    "actions": list(getattr(module, "ACTIONS", [])),
                    "groups": build_registry()["groups"] if engine == "core" else None,
                }
            else:
                result = module.dispatch(action, params)
                output = {"ok": True, "engine": engine, "action": action, "result": result}
        print(json.dumps(output, ensure_ascii=False, indent=2 if args.pretty else None))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                {"ok": False, "engine": engine, "action": action, "error": str(exc)},
                ensure_ascii=False,
                indent=2 if args.pretty else None,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
