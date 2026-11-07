from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2

from .config import RUNTIME_DIR, load_settings, platform_capabilities
from .onedragon import load_plan, save_plan, ONEDRAGON_WORKFLOW_ID
from . import dex
from . import pvp
from . import harness_actions as contract_actions

HARNESS_DIR = RUNTIME_DIR / "harness"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _save(image, label: str = "latest") -> str:
    HARNESS_DIR.mkdir(parents=True, exist_ok=True)
    path = HARNESS_DIR / f"{label}.jpg"
    cv2.imwrite(str(path), image, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
    return f"/api/harness/artifact?label={label}&t={int(time.time() * 1000)}"


def _tool(name: str, description: str, params: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {"name": name, "description": description, "parameters": params},
    }


def tools_schema() -> List[Dict[str, Any]]:
    any_object = {"type": "object", "additionalProperties": True}
    return [
        _tool(
            "rocogi_observe",
            "Observe the current game screen: captures a screenshot, classifies the scene, returns location and sessions. Call this before acting.",
            {"type": "object", "properties": {"save": {"type": "boolean"}}},
        ),
        _tool(
            "rocogi_capture",
            "Capture a screenshot of the game target and return the saved artifact and frame summary.",
            {"type": "object", "properties": {}},
        ),
        _tool(
            "rocogi_press_key",
            "Press a key in the game window. Keys: x, 1-6, f, esc, space, enter.",
            {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "presses": {"type": "integer", "minimum": 1, "maximum": 20},
                    "interval": {"type": "number", "minimum": 0, "maximum": 2},
                },
                "required": ["key"],
            },
        ),
        _tool(
            "rocogi_click",
            "Click at client-area coordinates in the game window.",
            {
                "type": "object",
                "properties": {
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "button": {"type": "string", "enum": ["left", "right"]},
                },
                "required": ["x", "y"],
            },
        ),
        _tool(
            "rocogi_move",
            "Move the mouse relative to the current position.",
            {
                "type": "object",
                "properties": {
                    "dx": {"type": "integer"},
                    "dy": {"type": "integer"},
                },
            },
        ),
        _tool("rocogi_locate", "Locate the player on the world map using the configured position source (SIFT or mock).", {"type": "object", "properties": {}}),
        _tool(
            "rocogi_start_realtime",
            "Start the continuous real-time trigger loop (auto ball, battle response, party confirm).",
            {"type": "object", "properties": {"config": any_object}},
        ),
        _tool("rocogi_stop_realtime", "Stop the real-time trigger loop.", {"type": "object", "properties": {}}),
        _tool(
            "rocogi_start_tracker",
            "Start the SIFT map tracker and record a trail.",
            {"type": "object", "properties": {"config": any_object}},
        ),
        _tool("rocogi_stop_tracker", "Stop the SIFT map tracker.", {"type": "object", "properties": {}}),
        _tool("rocogi_list_workflows", "List available Rocogi workflows with id, name, tags and last run.", {"type": "object", "properties": {}}),
        _tool(
            "rocogi_run_workflow",
            "Start an existing workflow by id or name. Returns a run id for rocogi_run_status.",
            {
                "type": "object",
                "properties": {"workflowId": {"type": "string"}, "name": {"type": "string"}},
            },
        ),
        _tool(
            "rocogi_run_onedragon",
            "Run the all-in-one task plan. Optionally pass a plan with ordered tasks.",
            {"type": "object", "properties": {"plan": any_object}},
        ),
        _tool(
            "rocogi_run_status",
            "Get a run status, timeline events and summary. Omit runId for the latest run.",
            {"type": "object", "properties": {"runId": {"type": "string"}}},
        ),
        _tool("rocogi_stop_run", "Stop a running workflow or one-dragon run.", {"type": "object", "properties": {"runId": {"type": "string"}}, "required": ["runId"]}),
        _tool(
            "rocogi_battle_decision",
            "Ask the local NRC MCTS engine for the recommended battle action.",
            {"type": "object", "properties": {"simulations": {"type": "integer"}}},
        ),
        _tool(
            "rocogi_battle_simulate",
            "Simulate a battle between a player team and a preset team.",
            {
                "type": "object",
                "properties": {
                    "playerTeam": {"type": "array", "items": {"type": "object"}},
                    "aiTeam": {"type": "string"},
                    "simulations": {"type": "integer"},
                    "maxTurns": {"type": "integer"},
                },
            },
        ),
        _tool(
            "rocogi_dex_lookup",
            "Look up a pet or skill in the local Pokédex. Returns stats, ability, skills and evolution for a pet name, or matching skills for a query.",
            {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "query": {"type": "string"},
                    "kind": {"type": "string", "enum": ["pet", "skill"]},
                    "element": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                },
            },
        ),
        _tool(
            "rocogi_pvp_analyze",
            "Analyze a 6-pet PvP team: speed tier, bulk, physical/special balance, element diversity and skill coverage.",
            {
                "type": "object",
                "properties": {
                    "team": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
                },
                "required": ["team"],
            },
        ),
        _tool(
            "rocogi_pvp_matchup",
            "Run a deterministic 6v6 MCTS matchup against the toxic or wing preset team.",
            {
                "type": "object",
                "properties": {
                    "team": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
                    "opponent": {"type": "string", "enum": ["toxic", "wing"]},
                    "simulations": {"type": "integer", "minimum": 10, "maximum": 300},
                    "maxTurns": {"type": "integer", "minimum": 10, "maximum": 80},
                },
                "required": ["team"],
            },
        ),
        _tool("rocogi_get_state", "Get target, sessions, active runs, workflows, map and engine preset state.", {"type": "object", "properties": {}}),
        _tool(
            "rocogi_sequence",
            "Run multiple Rocogi actions in one call. Use for short observe-act-observe loops.",
            {
                "type": "object",
                "properties": {
                    "actions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"action": {"type": "string"}, "params": {"type": "object"}},
                            "required": ["action"],
                        },
                    }
                },
                "required": ["actions"],
            },
        ),
    ] + contract_actions.tools_schema()


SYSTEM_PROMPT = """You are the playing brain of Rocogi, a local-first automation engine for the game Roco Kingdom: World.

Rules:
1. Always call rocogi_observe before deciding an action.
2. Use rocogi_press_key / rocogi_click for low-level game actions, and rocogi_run_workflow / rocogi_run_onedragon for complete tasks.
3. The engine is local. Do not assume cloud services. Screenshots and run data stay on the host.
4. Prefer short observe -> act -> observe loops. Inspect scene.kind before acting.
5. To catch a pet press x; to gather energy in battle press x; to escape press esc then click the yes button; to confirm party press f.
6. If a full task exists, use rocogi_run_workflow instead of reproducing its steps.
7. Use rocogi_dex_lookup to check pet stats, skills and evolution before building a battle team.
8. Use rocogi_pvp_analyze / rocogi_pvp_matchup to test a 6-pet composition before entering PvP.
9. Report what you did and the observed result using concise JSON.
"""


def manifest(app, base_url: str = "http://127.0.0.1:8787") -> Dict[str, Any]:
    db = app.state.db
    services = app.state.services
    settings = load_settings(db)
    target = services.target_info(settings)
    realtime = app.state.realtime.status()
    tracker = app.state.tracker.status()
    latest_runs = db.list_runs(limit=1)
    return {
        "name": "Rocogi",
        "version": "0.4.6",
        "kind": "game-automation-harness",
        "description": "Local-first automation engine for Roco Kingdom: World with screenshot vision, input, SIFT tracking, workflows, one-dragon tasks and MCTS battle.",
        "baseUrl": base_url,
        "protocol": "http-json",
        "auth": "none-local",
        "systemPrompt": SYSTEM_PROMPT,
        "quickstart": {
            "manifest": "GET /api/harness/manifest",
            "observe": "POST /api/harness/act {\"action\":\"observe\"}",
            "act": "POST /api/harness/act {\"action\":\"press_key\",\"params\":{\"key\":\"x\"}}",
            "fullTask": "POST /api/harness/act {\"action\":\"run_workflow\",\"params\":{\"name\":\"抓宠巡航 · 自动丢球\"}}",
            "status": "POST /api/harness/act {\"action\":\"run_status\"}",
        },
        "state": {
            "platform": platform_capabilities(),
            "target": target,
            "enginePreset": settings.get("engine", {}).get("preset", "demo"),
            "realtime": {"running": realtime["running"], "status": realtime["status"], "scene": realtime["scene"]},
            "tracker": {"running": tracker["running"], "status": tracker["status"], "anchor": tracker["anchor"]},
            "workflows": len(db.list_workflows()),
            "activeRuns": app.state.runs.active_count(),
            "latestRun": latest_runs[0] if latest_runs else None,
        },
        "capabilities": [
            "capture-and-classify-screen",
            "template-matching",
            "keyboard-mouse-input",
            "run-visual-workflow",
            "one-dragon-task-plan",
            "sift-map-tracking",
            "mcts-battle-decision",
            "run-evidence-and-screenshots",
            "pokedex-lookup",
            "pvp-team-analysis",
            "sprite-candidate-contract",
            "hud-ocr-contract",
            "map-points-and-route-contract",
            "vendor-adapter-status",
            "no-game-memory-reading",
        ],
        "endpoints": {
            "manifest": "/api/harness/manifest",
            "tools": "/api/harness/tools",
            "act": "/api/harness/act",
            "artifact": "/api/harness/artifact",
            "openapi": "/docs",
        },
        "tools": tools_schema(),
    }


def _workflow_by(db, params: Dict[str, Any]):
    workflow_id = params.get("workflowId")
    name = params.get("name")
    if workflow_id:
        return db.get_workflow(str(workflow_id))
    if name:
        for item in db.list_workflows():
            if item["name"] == name or name in item["name"]:
                return item
    return None


def execute(app, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params or {}
    services = app.state.services
    db = app.state.db
    runs = app.state.runs
    realtime = app.state.realtime
    tracker = app.state.tracker
    settings = load_settings(db)

    if action.startswith("rocogi_"):
        action = action[len("rocogi_") :]

    handled = contract_actions.dispatch(services, settings, action, params)
    if handled is not None:
        return handled

    if action == "get_state":
        return {"ok": True, "action": action, "result": manifest(app)["state"]}

    if action == "dex_lookup":
        name = str(params.get("name") or "").strip()
        query = str(params.get("query") or name).strip()
        kind = str(params.get("kind") or ("pet" if name else "skill"))
        element = str(params.get("element") or "")
        limit = int(params.get("limit") or 8)
        if kind == "pet" and name:
            detail = dex.pokemon_detail(name)
            if not detail:
                return {"ok": False, "action": action, "error": f"pet not found: {name}"}
            return {"ok": True, "action": action, "result": detail}
        if kind == "pet":
            return {"ok": True, "action": action, "result": dex.pokemon_list(query, element=element, limit=limit)}
        result = dex.skill_list(query, element=element, limit=limit)
        return {"ok": True, "action": action, "result": result}

    if action == "pvp_analyze":
        try:
            return {"ok": True, "action": action, "result": pvp.analyze(params.get("team") or [])}
        except ValueError as exc:
            return {"ok": False, "action": action, "error": str(exc)}

    if action == "pvp_matchup":
        try:
            return {
                "ok": True,
                "action": action,
                "result": pvp.matchup(
                    services.battle,
                    params.get("team") or [],
                    str(params.get("opponent") or "wing"),
                    int(params.get("simulations") or 40),
                    int(params.get("maxTurns") or 30),
                ),
            }
        except ValueError as exc:
            return {"ok": False, "action": action, "error": str(exc)}

    if action == "observe":
        frame = services.capture(settings)
        scene = services.classify_scene(frame, threshold=float(settings["vision"].get("threshold", 0.5)))
        position = services.position_for_frame(frame, {})
        from .adapters.vision import annotate_matches

        annotated = annotate_matches(frame, list(scene["details"].values()))
        cv2.putText(
            annotated,
            f"{scene['kind']}",
            (28, annotated.shape[0] - 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.1,
            (6, 40, 60),
            3,
        )
        cv2.putText(
            annotated,
            f"{scene['kind']}",
            (28, annotated.shape[0] - 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.1,
            (56, 189, 248),
            2,
        )
        screenshot = _save(annotated, "observe")
        return {
            "ok": True,
            "action": action,
            "result": {
                "timestamp": _now(),
                "scene": {"kind": scene["kind"], "scores": scene["scores"]},
                "position": position,
                "frame": frame.summary(),
                "screenshot": screenshot,
                "sessions": {
                    "realtime": realtime.status()["status"],
                    "tracker": tracker.status()["status"],
                },
            },
        }

    if action == "capture":
        frame = services.capture(settings)
        return {"ok": True, "action": action, "result": {"screenshot": _save(frame.image, "capture"), "frame": frame.summary()}}

    if action == "press_key":
        key = str(params.get("key") or "x")
        presses = int(params.get("presses") or 1)
        interval = float(params.get("interval") or 0.08)
        services.act(settings, "key", key=key, presses=presses, interval=interval)
        return {"ok": True, "action": action, "result": {"key": key, "presses": presses}}

    if action == "click":
        x = int(float(params.get("x") or 0))
        y = int(float(params.get("y") or 0))
        services.act(settings, "click", x=x, y=y, button=str(params.get("button") or "left"))
        return {"ok": True, "action": action, "result": {"x": x, "y": y}}

    if action == "move":
        services.act(settings, "move", dx=int(params.get("dx") or 0), dy=int(params.get("dy") or 0))
        return {"ok": True, "action": action, "result": {"dx": params.get("dx", 0), "dy": params.get("dy", 0)}}

    if action == "locate":
        frame = services.capture(settings)
        position = services.position_for_frame(frame, {})
        return {"ok": bool(position), "action": action, "result": {"position": position}}

    if action == "start_realtime":
        return {"ok": True, "action": action, "result": realtime.start(params.get("config") or {})}

    if action == "stop_realtime":
        return {"ok": True, "action": action, "result": realtime.stop()}

    if action == "start_tracker":
        return {"ok": True, "action": action, "result": tracker.start(params.get("config") or {})}

    if action == "stop_tracker":
        return {"ok": True, "action": action, "result": tracker.stop()}

    if action == "list_workflows":
        return {"ok": True, "action": action, "result": db.list_workflows()}

    if action == "run_workflow":
        workflow = _workflow_by(db, params)
        if not workflow:
            return {"ok": False, "action": action, "error": "workflow not found"}
        run = runs.start(workflow, trigger="harness")
        return {"ok": True, "action": action, "result": {"runId": run["id"], "workflowId": workflow["id"], "run": run}}

    if action == "run_onedragon":
        plan = save_plan(db, params["plan"]) if params.get("plan") else load_plan(db)
        workflow = db.get_workflow(ONEDRAGON_WORKFLOW_ID)
        if not workflow:
            return {"ok": False, "action": action, "error": "one-dragon workflow missing"}
        run = runs.start(workflow, trigger="harness")
        return {"ok": True, "action": action, "result": {"runId": run["id"], "plan": plan}}

    if action == "run_status":
        run_id = params.get("runId")
        if not run_id:
            latest = db.list_runs(limit=1)
            run_id = latest[0]["id"] if latest else None
        if not run_id:
            return {"ok": False, "action": action, "error": "no runs"}
        run = db.get_run(str(run_id))
        if not run:
            return {"ok": False, "action": action, "error": "run not found"}
        events = db.get_events(str(run_id))
        return {
            "ok": True,
            "action": action,
            "result": {
                "run": run,
                "events": events[-30:],
                "lastText": events[-1]["message"] if events else "",
            },
        }

    if action == "stop_run":
        run_id = str(params.get("runId") or "")
        if not run_id:
            return {"ok": False, "action": action, "error": "runId required"}
        stopped = runs.stop(run_id)
        return {"ok": stopped, "action": action, "result": {"runId": run_id, "stopping": stopped}}

    if action == "battle_decision":
        return {"ok": True, "action": action, "result": services.battle_decide(int(params.get("simulations") or 40))}

    if action == "battle_simulate":
        return {
            "ok": True,
            "action": action,
            "result": services.battle_simulate(
                params.get("playerTeam"),
                str(params.get("aiTeam") or "wing"),
                int(params.get("simulations") or 40),
                int(params.get("maxTurns") or 24),
            ),
        }

    if action == "sequence":
        steps = params.get("actions") or []
        results = []
        for step in steps[:12]:
            results.append(execute(app, str(step.get("action") or ""), step.get("params") or {}))
        return {"ok": True, "action": action, "result": {"steps": results}}

    return {"ok": False, "action": action, "error": f"unknown action: {action}", "tools": [t["function"]["name"] for t in tools_schema()]}
