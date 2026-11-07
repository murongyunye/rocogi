from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from .. import __version__
from ..config import (
    ENGINE_PRESETS,
    apply_engine_preset,
    load_settings,
    platform_capabilities,
    save_settings,
)
from ..components import build_registry
from ..contracts import catalog
from .. import capability_contract
from .. import dex
from .. import pvp
from ..engine.compiler import compile_graph
from ..onedragon import load_plan, save_plan, TASK_CATALOG, ONEDRAGON_WORKFLOW_ID
from ..sessions import LIVE_DIR, TRACKER_DIR
from .. import harness

router = APIRouter(prefix="/api")


def _svc(request: Request):
    return request.app.state.services


def _db(request: Request):
    return request.app.state.db


# --------------------------------------------------------------------- meta
@router.get("/health")
def health(request: Request):
    return {
        "ok": True,
        "version": __version__,
        "service": "rocoflow",
        "platform": platform_capabilities(),
        "activeRuns": request.app.state.runs.active_count(),
    }


@router.get("/meta")
def meta(request: Request):
    services = _svc(request)
    db = _db(request)
    settings = load_settings(db)
    return {
        "version": __version__,
        "platform": platform_capabilities(),
        "target": services.target_info(settings),
        "settings": settings,
        "workflowCount": len(db.list_workflows()),
        "runCount": len(db.list_runs(limit=200)),
        "map": services.map.meta(),
        "resources": len(db.list_resources()),
        "activeRuns": request.app.state.runs.active_count(),
        "realtime": {"running": request.app.state.realtime.status()["running"]},
        "tracker": {"running": request.app.state.tracker.status()["running"]},
    }


@router.get("/nodes")
def nodes_catalog():
    return capability_contract.nodes_document()


@router.get("/actions")
def actions_catalog():
    return capability_contract.actions_document()


# --------------------------------------------------------------------- workflows
@router.get("/workflows")
def list_workflows(request: Request):
    return _db(request).list_workflows()


@router.post("/workflows")
def create_workflow(request: Request, payload: Dict[str, Any] = Body(...)):
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "工作流名称不能为空")
    graph = payload.get("graph") or {"nodes": [], "edges": [], "subgraphs": {}, "variables": {}}
    compiled = compile_graph(graph)
    if not compiled.ok:
        raise HTTPException(400, {"message": "工作流校验失败", "issues": [i.__dict__ for i in compiled.issues]})
    return _db(request).create_workflow(
        name,
        str(payload.get("description") or ""),
        graph,
        tags=[str(t) for t in payload.get("tags") or []],
        target_slot=str(payload.get("targetSlot") or "nrc-game"),
    )


@router.get("/workflows/{workflow_id}")
def get_workflow(request: Request, workflow_id: str):
    workflow = _db(request).get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(404, "工作流不存在")
    compiled = compile_graph(workflow["graph"])
    workflow["issues"] = [i.__dict__ for i in compiled.issues]
    return workflow


@router.put("/workflows/{workflow_id}")
def update_workflow(request: Request, workflow_id: str, payload: Dict[str, Any] = Body(...)):
    current = _db(request).get_workflow(workflow_id)
    if not current:
        raise HTTPException(404, "工作流不存在")
    graph = payload.get("graph", current["graph"])
    compiled = compile_graph(graph)
    if not compiled.ok:
        raise HTTPException(400, {"message": "工作流校验失败", "issues": [i.__dict__ for i in compiled.issues]})
    updated = _db(request).update_workflow(workflow_id, {**current, **payload})
    return updated


@router.delete("/workflows/{workflow_id}")
def delete_workflow(request: Request, workflow_id: str):
    ok = _db(request).delete_workflow(workflow_id)
    if not ok:
        raise HTTPException(404, "工作流不存在")
    return {"ok": True}


@router.post("/workflows/{workflow_id}/duplicate")
def duplicate_workflow(request: Request, workflow_id: str):
    workflow = _db(request).get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(404, "工作流不存在")
    copy = _db(request).create_workflow(
        f"{workflow['name']} 副本",
        workflow["description"],
        workflow["graph"],
        tags=workflow["tags"],
        target_slot=workflow["targetSlot"],
    )
    return copy


@router.post("/validate")
def validate_graph(payload: Dict[str, Any] = Body(...)):
    compiled = compile_graph(payload.get("graph") or payload)
    return {
        "ok": compiled.ok,
        "issues": [issue.__dict__ for issue in compiled.issues],
    }


@router.post("/workflows/{workflow_id}/run")
def run_workflow(request: Request, workflow_id: str, payload: Dict[str, Any] = Body(default={})):
    workflow = _db(request).get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(404, "工作流不存在")
    try:
        run = request.app.state.runs.start(workflow, trigger=str(payload.get("trigger") or "manual"))
    except ValueError as exc:
        compiled = compile_graph(workflow["graph"])
        raise HTTPException(400, {
            "message": str(exc),
            "issues": [issue.__dict__ for issue in compiled.issues],
        }) from exc
    return run


# --------------------------------------------------------------------- runs
@router.get("/runs")
def list_runs(request: Request, limit: int = 30, workflowId: Optional[str] = None):
    return _db(request).list_runs(limit=max(1, min(limit, 200)), workflow_id=workflowId)


@router.get("/runs/{run_id}")
def get_run(request: Request, run_id: str):
    run = _db(request).get_run(run_id)
    if not run:
        raise HTTPException(404, "运行不存在")
    return run


@router.get("/runs/{run_id}/events")
def run_events(request: Request, run_id: str, after: int = 0, limit: int = 2000):
    return _db(request).get_events(run_id, after=after, limit=max(1, min(limit, 5000)))


@router.post("/runs/{run_id}/stop")
def stop_run(request: Request, run_id: str):
    run = _db(request).get_run(run_id)
    if not run:
        raise HTTPException(404, "运行不存在")
    ok = request.app.state.runs.stop(run_id)
    return {"ok": ok, "status": "stopping" if ok else run["status"]}


@router.get("/runs/{run_id}/artifacts/{filename}")
def run_artifact(request: Request, run_id: str, filename: str):
    from ..config import RUNTIME_DIR

    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(400, "非法文件名")
    path = RUNTIME_DIR / "runs" / run_id / filename
    if not path.exists():
        raise HTTPException(404, "文件不存在")
    return FileResponse(path, media_type="image/jpeg")


# --------------------------------------------------------------------- resources
@router.get("/resources")
def list_resources(request: Request, kind: Optional[str] = None):
    return _db(request).list_resources(kind)


@router.get("/assets/{path:path}")
def asset(path: str):
    from ..config import resolve_asset

    try:
        target = resolve_asset(path)
    except ValueError as exc:
        raise HTTPException(400, "非法路径") from exc
    if not target.exists() or not target.is_file():
        raise HTTPException(404, "资源不存在")
    return FileResponse(target)


# --------------------------------------------------------------------- map
@router.get("/map/meta")
def map_meta(request: Request):
    return _svc(request).map.meta()


@router.get("/map/points")
def map_points(
    request: Request,
    labels: Optional[str] = None,
    categories: Optional[str] = None,
    limit: int = 20000,
):
    label_list = [s for s in (labels or "").split(",") if s]
    category_list = [s for s in (categories or "").split(",") if s]
    points = _svc(request).map.points
    if label_list:
        points = [p for p in points if p["label"] in label_list]
    if category_list:
        points = [p for p in points if p["category"] in category_list]
    limit = max(1, min(limit, 20000))
    return {"total": len(points), "points": points[:limit]}


@router.post("/map/route")
def map_route(request: Request, payload: Dict[str, Any] = Body(...)):
    start = payload.get("start") or {"x": 3072, "y": 2944}
    labels = [str(v) for v in payload.get("labels") or []]
    categories = [str(v) for v in payload.get("categories") or []]
    plan = _svc(request).plan_route(
        start,
        labels=labels,
        categories=categories,
        limit=int(payload.get("limit") or 15),
        roundtrip=bool(payload.get("roundtrip", False)),
    )
    return plan


@router.post("/map/position")
def map_position(request: Request):
    services = _svc(request)
    settings = load_settings(_db(request))
    frame = services.capture(settings)
    position = services.position_for_frame(frame, {})
    return {"ok": bool(position), "position": position, "frame": frame.summary()}


# --------------------------------------------------------------------- battle
@router.get("/battle/pokemon")
def battle_pokemon(request: Request, q: str = "", limit: int = 40):
    return _svc(request).battle.pokemon_list(q, limit)


@router.get("/battle/pokemon/{name}/skills")
def battle_skills(request: Request, name: str):
    return _svc(request).battle.skills_for(name)


@router.get("/battle/presets")
def battle_presets(request: Request):
    return _svc(request).battle.presets()


@router.get("/battle/presets/{key}")
def battle_preset_team(request: Request, key: str):
    return _svc(request).battle.preset_team(key)


@router.post("/battle/simulate")
def battle_simulate(request: Request, payload: Dict[str, Any] = Body(...)):
    result = _svc(request).battle_simulate(
        payload.get("playerTeam"),
        str(payload.get("aiTeam") or "wing"),
        int(payload.get("simulations") or 60),
        int(payload.get("maxTurns") or 30),
    )
    return result


@router.post("/battle/decide")
def battle_decide(request: Request, payload: Dict[str, Any] = Body(default={})):
    return _svc(request).battle_decide(int(payload.get("simulations") or 60))


# --------------------------------------------------------------------- bwiki (preferred battle data)
@router.get("/bwiki/catalog")
def bwiki_catalog(request: Request):
    return _svc(request).bwiki.catalog()


@router.get("/bwiki/pets")
def bwiki_pets(request: Request, q: str = "", limit: int = 40):
    return _svc(request).bwiki.pets(q, limit)


@router.get("/bwiki/pets/{name}")
def bwiki_pet(request: Request, name: str):
    return _svc(request).bwiki.pet(name)


@router.get("/bwiki/skills")
def bwiki_skills(request: Request, q: str = "", element: str = "", category: str = "", limit: int = 40):
    return _svc(request).bwiki.skills(q, element, category, limit)


@router.get("/bwiki/type-chart")
def bwiki_type_chart(request: Request, element: Optional[str] = None):
    return _svc(request).bwiki.type_chart(element)


@router.get("/bwiki/best-skill")
def bwiki_best_skill(request: Request, pet: str, enemy: str = "", energy: Optional[int] = None):
    enemy_types = [t for t in (enemy or "").replace(" ", "").split(",") if t]
    return _svc(request).bwiki.best_skill(pet, enemy_types, energy)


# --------------------------------------------------------------------- settings / demo
@router.get("/settings")
def get_settings(request: Request):
    settings = load_settings(_db(request))
    return {"settings": settings, "target": _svc(request).target_info(settings)}


@router.put("/settings")
def put_settings(request: Request, payload: Dict[str, Any] = Body(...)):
    settings = save_settings(_db(request), payload)
    return {"settings": settings, "target": _svc(request).target_info(settings)}


@router.get("/demo/scene")
def get_demo_scene(request: Request):
    settings = load_settings(_db(request))
    return {"scene": settings.get("demo", {}).get("scene", "auto"), "target": _svc(request).target_info(settings)}


@router.post("/demo/scene")
def set_demo_scene(request: Request, payload: Dict[str, Any] = Body(...)):
    scene = str(payload.get("scene") or "auto")
    _svc(request).set_scene(scene)
    settings = save_settings(_db(request), {"demo": {"scene": scene}})
    return {"ok": True, "scene": scene, "settings": settings}


# --------------------------------------------------------------------- live sessions
@router.get("/realtime/status")
def realtime_status(request: Request):
    return request.app.state.realtime.status()


@router.post("/realtime/start")
def realtime_start(request: Request, payload: Dict[str, Any] = Body(default={})):
    return request.app.state.realtime.start(payload.get("config") or payload or {})


@router.post("/realtime/stop")
def realtime_stop(request: Request):
    return request.app.state.realtime.stop()


@router.get("/live/artifact")
def live_artifact():
    path = LIVE_DIR / "latest.jpg"
    if not path.exists():
        raise HTTPException(404, "还没有实时截图")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.get("/tracker/status")
def tracker_status(request: Request):
    return request.app.state.tracker.status()


@router.post("/tracker/start")
def tracker_start(request: Request, payload: Dict[str, Any] = Body(default={})):
    return request.app.state.tracker.start(payload.get("config") or payload or {})


@router.post("/tracker/stop")
def tracker_stop(request: Request):
    return request.app.state.tracker.stop()


@router.post("/tracker/anchors/rebuild")
def tracker_rebuild(request: Request):
    return request.app.state.tracker.rebuild_anchors()


@router.get("/tracker/artifact")
def tracker_artifact():
    path = TRACKER_DIR / "latest.jpg"
    if not path.exists():
        raise HTTPException(404, "还没有追踪截图")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.get("/onedragon/plan")
def onedragon_plan(request: Request):
    return {"plan": load_plan(_db(request)), "tasks": TASK_CATALOG, "workflowId": ONEDRAGON_WORKFLOW_ID}


@router.put("/onedragon/plan")
def onedragon_save(request: Request, payload: Dict[str, Any] = Body(...)):
    return {"plan": save_plan(_db(request), payload.get("plan") or payload), "tasks": TASK_CATALOG}


@router.post("/onedragon/run")
def onedragon_run(request: Request, payload: Dict[str, Any] = Body(default={})):
    db = _db(request)
    plan = save_plan(db, payload.get("plan") or load_plan(db)) if payload.get("plan") else load_plan(db)
    workflow = db.get_workflow(ONEDRAGON_WORKFLOW_ID)
    if not workflow:
        raise HTTPException(404, "一条龙工作流不存在")
    # 模拟目标：每轮从场景脚本头部开始，演示结果可复现（实机目标不受影响）
    services = _svc(request)
    if services.settings().get("target", {}).get("kind") == "mock":
        services.set_scene("auto")
    run = request.app.state.runs.start(workflow, trigger="onedragon")
    return {"runId": run["id"], "workflowId": ONEDRAGON_WORKFLOW_ID, "plan": plan}


# --------------------------------------------------------------------- engines
@router.get("/engines")
def engines(request: Request):
    db = _db(request)
    settings = load_settings(db)
    target = _svc(request).target_info(settings)
    tracker = request.app.state.tracker.status()
    applied = settings.get("engine", {}).get("preset", "demo")
    return {
        "applied": applied,
        "presets": [
            {
                "id": key,
                "name": preset["name"],
                "description": preset["description"],
                "tag": preset["tag"],
                "settings": preset["settings"],
            }
            for key, preset in ENGINE_PRESETS.items()
        ],
        "current": {
            "target": target,
            "capture": settings["target"],
            "input": settings["input"],
            "vision": settings["vision"],
            "map": settings["map"],
            "engine": settings["engine"],
            "battle": settings["battle"],
            "realtime": settings.get("realtime", {}),
            "tracker": settings.get("tracker", {}),
        },
        "status": {
            "capture": {"ok": "error" not in target, "detail": target.get("title") or target.get("error")},
            "vision": {"ok": True, "templates": len(_db(request).list_resources("template"))},
            "input": {
                "ok": settings["input"]["backend"] == "mock" or platform_capabilities()["windows"],
                "backend": settings["input"]["backend"],
            },
            "sift": {
                "ok": platform_capabilities()["sift"],
                "anchors": tracker["anchor"]["points"],
                "cached": tracker["anchor"]["cached"],
            },
            "battle": {"ok": platform_capabilities()["battle_ai"]},
            "realtime": request.app.state.realtime.status(),
            "tracker": {"running": tracker["running"], "status": tracker["status"]},
        },
    }


@router.post("/engines/apply")
def engines_apply(request: Request, payload: Dict[str, Any] = Body(...)):
    preset_id = str(payload.get("presetId") or payload.get("preset") or "")
    try:
        result = apply_engine_preset(_db(request), preset_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {
        "ok": True,
        **result,
        "target": _svc(request).target_info(result["settings"]),
    }


# --------------------------------------------------------------------- dex
@router.get("/dex/meta")
def dex_meta():
    return dex.meta()


@router.get("/dex/pokemon")
def dex_pokemon(
    q: str = "",
    element: str = "",
    stage: str = "",
    sort: str = "id",
    order: str = "asc",
    limit: int = 24,
    offset: int = 0,
):
    return dex.pokemon_list(q, element, stage, sort, order, limit, offset)


@router.get("/dex/pokemon/{name}")
def dex_pokemon_detail(name: str):
    data = dex.pokemon_detail(name)
    if not data:
        raise HTTPException(404, "图鉴中没有这只精灵")
    return data


@router.get("/dex/skills")
def dex_skills(q: str = "", element: str = "", category: str = "", limit: int = 40, offset: int = 0):
    return dex.skill_list(q, element, category, limit, offset)


# --------------------------------------------------------------------- pvp
@router.get("/pvp/meta")
def pvp_meta(request: Request):
    return pvp.meta(_svc(request).battle)


@router.post("/pvp/analyze")
def pvp_analyze(request: Request, payload: Dict[str, Any] = Body(...)):
    try:
        return pvp.analyze(payload.get("team") or [])
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/pvp/matchup")
def pvp_matchup(request: Request, payload: Dict[str, Any] = Body(...)):
    try:
        return pvp.matchup(
            _svc(request).battle,
            payload.get("team") or [],
            str(payload.get("opponent") or "wing"),
            int(payload.get("simulations") or 60),
            int(payload.get("maxTurns") or 30),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


# --------------------------------------------------------------------- pvp dataset
# Community dataset (datasets/pvp/pvp_data.db): six stats, skill power/energy,
# traits with battle effects, public usage stats and the merged type matrix.
@router.get("/pvp/dataset")
def pvp_dataset(request: Request):
    return _svc(request).pvpdata.summary()


@router.get("/pvp/dataset/pets/{name}")
def pvp_dataset_pet(request: Request, name: str):
    return _svc(request).pvpdata.profile(name)


@router.get("/pvp/dataset/usage")
def pvp_dataset_usage(request: Request, kind: str = "pets", limit: int = 20):
    return _svc(request).pvpdata.leaderboard(kind, limit)


@router.get("/pvp/dataset/skills")
def pvp_dataset_skills(request: Request, q: str = "", element: str = "", category: str = "",
                       limit: int = 40):
    return _svc(request).pvpdata.skills(q, element, category, limit)


# --------------------------------------------------------------------- components
@router.get("/components")
def components():
    return build_registry()


@router.get("/hotkeys")
def hotkeys_status(request: Request):
    return request.app.state.hotkeys.status()


# --------------------------------------------------------------------- harness
@router.get("/harness/manifest")
def harness_manifest(request: Request):
    return harness.manifest(request.app, base_url=str(request.base_url).rstrip("/"))


@router.get("/harness/tools")
def harness_tools(request: Request):
    return {
        "name": "Rocogi",
        "systemPrompt": harness.SYSTEM_PROMPT,
        "tools": harness.tools_schema(),
        "manifest": "/api/harness/manifest",
        "act": "/api/harness/act",
    }

@router.post("/harness/act")
def harness_act(request: Request, payload: Dict[str, Any] = Body(...)):
    action = str(payload.get("action") or payload.get("tool") or "")
    params = payload.get("params") or payload.get("arguments") or {}
    return harness.execute(request.app, action, params)


@router.get("/harness/artifact")
def harness_artifact(label: str = "observe"):
    if label not in ("observe", "capture"):
        raise HTTPException(400, "非法标签")
    path = harness.HARNESS_DIR / f"{label}.jpg"
    if not path.exists():
        raise HTTPException(404, "还没有 harness 截图")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


# --------------------------------------------------------------------- websocket
async def run_stream(websocket: WebSocket, run_id: str):
    await websocket.accept()
    db = websocket.app.state.db
    hub = websocket.app.state.runs.hub
    after = 0
    try:
        query = websocket.query_params.get("after")
        if query:
            after = int(query)
    except ValueError:
        after = 0
    channel = hub.subscribe(run_id)
    try:
        backlog = db.get_events(run_id, after=after, limit=5000)
        for event in backlog:
            await websocket.send_text(json.dumps(event, ensure_ascii=False))
            after = max(after, int(event.get("seq", 0)))
        while True:
            try:
                event = channel.get_nowait()
            except Exception:
                await asyncio.sleep(0.15)
                if not db.get_run(run_id):
                    break
                continue
            if int(event.get("seq", 0)) <= after:
                continue
            after = int(event.get("seq", 0))
            await websocket.send_text(json.dumps(event, ensure_ascii=False))
            if event.get("type") == "run.finished":
                break
    except WebSocketDisconnect:
        pass
    finally:
        hub.unsubscribe(run_id, channel)
        try:
            await websocket.close()
        except Exception:
            pass


# --------------------------------------------------------------------- diagnostics
@router.post("/diagnostics/screenshot")
def diagnostics_screenshot(request: Request):
    services = _svc(request)
    settings = load_settings(_db(request))
    frame = services.capture(settings)
    scene = services.classify_scene(frame)
    return {"frame": frame.summary(), "scene": scene["kind"], "scores": scene["scores"]}
