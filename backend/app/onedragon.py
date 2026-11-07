from __future__ import annotations

from typing import Any, Dict, List

ONEDRAGON_WORKFLOW_ID = "wf_onedragon"
ONEDRAGON_NAME = "一条龙 · 今日计划"

TASK_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "auto_ball",
        "name": "自动丢球",
        "description": "识别可捕捉精灵与交易请求，自动按键丢球。",
        "defaults": {"key": "x", "threshold": 0.45},
    },
    {
        "id": "smart_battle",
        "name": "战斗应对",
        "description": "普通/污染战斗分别执行聚能、逃跑或技能策略。",
        "defaults": {"normalStrategy": "gather", "pollutedStrategy": "escape"},
    },
    {
        "id": "party_confirm",
        "name": "同行确认",
        "description": "检测同行请求并自动按 F。",
        "defaults": {"key": "f", "threshold": 0.45},
    },
    {
        "id": "map_route",
        "name": "资源巡线",
        "description": "SIFT 定位后按资源名称规划路线并记录当前位置。",
        "defaults": {"labels": "宝箱", "limit": 8},
    },
    {
        "id": "battle_ai",
        "name": "对战决策",
        "description": "用 MCTS 给出当前预设阵容的推荐动作。",
        "defaults": {"simulations": 30},
    },
]

DEFAULT_PLAN: Dict[str, Any] = {
    "loops": 3,
    "tasks": [
        {"id": "auto_ball", "enabled": True, "config": {"key": "x", "threshold": 0.45}},
        {"id": "smart_battle", "enabled": True, "config": {"normalStrategy": "gather", "pollutedStrategy": "escape"}},
        {"id": "party_confirm", "enabled": True, "config": {"key": "f", "threshold": 0.45}},
        {"id": "map_route", "enabled": False, "config": {"labels": "宝箱", "limit": 8}},
        {"id": "battle_ai", "enabled": False, "config": {"simulations": 30}},
    ],
}


def normalize_plan(raw: Dict[str, Any] | None) -> Dict[str, Any]:
    plan = {**DEFAULT_PLAN, **(raw or {})}
    catalog = {item["id"]: item for item in TASK_CATALOG}
    tasks = []
    for item in plan.get("tasks") or []:
        task_id = str(item.get("id") or "")
        if task_id not in catalog:
            continue
        tasks.append(
            {
                "id": task_id,
                "enabled": bool(item.get("enabled", True)),
                "config": {**catalog[task_id]["defaults"], **(item.get("config") or {})},
            }
        )
    if not tasks:
        tasks = [dict(task) for task in DEFAULT_PLAN["tasks"]]
    plan["tasks"] = tasks
    plan["loops"] = max(1, min(int(plan.get("loops", 3) or 3), 20))
    return plan


def _node(node_id: str, node_type: str, x: int, y: int, config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {"id": node_id, "type": node_type, "x": x, "y": y, "config": config or {}}


def _edge(edge_id: str, from_node: str, from_port: str, to_node: str, to_port: str = "in") -> Dict[str, Any]:
    return {"id": edge_id, "from": from_node, "fromPort": from_port, "to": to_node, "toPort": to_port}


def build_graph(plan: Dict[str, Any]) -> Dict[str, Any]:
    plan = normalize_plan(plan)
    enabled = [task for task in plan["tasks"] if task["enabled"]]
    if not enabled:
        enabled = [task for task in plan["tasks"]][:1]

    nodes: List[Dict[str, Any]] = [
        _node("od_start", "run.start", 60, 300, {"label": "一条龙"}),
        _node("od_init", "flow.set_var", 300, 300, {"name": "od_tick", "value": "0"}),
        _node("od_loop", "flow.branch", 540, 300, {"condition": f"vars.od_tick < {plan['loops']}"}),
        _node("od_cap", "game.capture", 780, 200, {"region": "full", "save": True}),
    ]
    edges: List[Dict[str, Any]] = [
        _edge("e_start", "od_start", "out", "od_init"),
        _edge("e_init", "od_init", "out", "od_loop"),
        _edge("e_loop_true", "od_loop", "true", "od_cap"),
    ]

    previous = "od_cap"
    x = 1020
    for index, task in enumerate(enabled):
        task_id = task["id"]
        config = task["config"]
        prefix = f"od_{index}_{task_id}"
        if task_id == "auto_ball":
            nodes.append(_node(f"{prefix}_run", "game.auto_ball", x, 200, {
                "mode": "key",
                "key": config.get("key", "x"),
                "threshold": config.get("threshold", 0.45),
                "autoCapture": False,
            }))
            edges.append(_edge(f"e_{index}_a", previous, "out", f"{prefix}_run"))
            previous = f"{prefix}_run"
            x += 240
        elif task_id == "smart_battle":
            nodes.append(_node(f"{prefix}_run", "game.smart_battle", x, 200, {
                "normalStrategy": config.get("normalStrategy", "gather"),
                "pollutedStrategy": config.get("pollutedStrategy", "escape"),
                "threshold": 0.5,
                "autoCapture": False,
            }))
            edges.append(_edge(f"e_{index}_a", previous, "out", f"{prefix}_run"))
            previous = f"{prefix}_run"
            x += 240
        elif task_id == "party_confirm":
            nodes.append(_node(f"{prefix}_run", "game.party_confirm", x, 200, {
                "key": config.get("key", "f"),
                "threshold": config.get("threshold", 0.45),
                "autoCapture": False,
            }))
            edges.append(_edge(f"e_{index}_a", previous, "out", f"{prefix}_run"))
            previous = f"{prefix}_run"
            x += 240
        elif task_id == "map_route":
            nodes.append(_node(f"{prefix}_locate", "map.locate", x, 200, {"autoCapture": False}))
            nodes.append(_node(f"{prefix}_route", "map.route", x + 220, 200, {
                "labels": config.get("labels", "宝箱"),
                "limit": config.get("limit", 8),
            }))
            nodes.append(_node(f"{prefix}_follow", "map.follow", x + 440, 200, {"steps": 2, "intervalMs": 80}))
            edges.append(_edge(f"e_{index}_a", previous, "out", f"{prefix}_locate"))
            edges.append(_edge(f"e_{index}_b", f"{prefix}_locate", "out", f"{prefix}_route"))
            edges.append(_edge(f"e_{index}_c", f"{prefix}_route", "out", f"{prefix}_follow"))
            previous = f"{prefix}_follow"
            x += 660
        elif task_id == "battle_ai":
            nodes.append(_node(f"{prefix}_run", "battle.decide", x, 200, {
                "simulations": config.get("simulations", 30),
            }))
            edges.append(_edge(f"e_{index}_a", previous, "out", f"{prefix}_run"))
            previous = f"{prefix}_run"
            x += 240

    nodes.append(_node("od_delay", "flow.delay", x, 200, {"ms": 250}))
    edges.append(_edge("e_delay_in", previous, "out", "od_delay"))
    nodes.append(_node("od_inc", "flow.set_var", x + 220, 200, {"name": "od_tick", "value": "vars.od_tick + 1"}))
    edges.append(_edge("e_inc", "od_delay", "out", "od_inc"))
    edges.append(_edge("e_loop_back", "od_inc", "out", "od_loop"))
    nodes.append(_node("od_done", "flow.log", 780, 500, {"message": "一条龙完成 · 循环 {{vars.od_tick}} 轮 · 丢球 {{vars.ball_count}} · 战斗 {{vars.battle_count}}"}))
    nodes.append(_node("od_end", "run.stop", 1020, 500, {"reason": "一条龙完成"}))
    edges.append(_edge("e_loop_false", "od_loop", "false", "od_done"))
    edges.append(_edge("e_done", "od_done", "out", "od_end"))

    return {"nodes": nodes, "edges": edges, "subgraphs": {}, "variables": {"ball_count": 0, "battle_count": 0}}


def sync_workflow(db, plan: Dict[str, Any]) -> Dict[str, Any]:
    graph = build_graph(plan)
    existing = db.get_workflow(ONEDRAGON_WORKFLOW_ID)
    if existing:
        return db.update_workflow(
            ONEDRAGON_WORKFLOW_ID,
            {
                "name": ONEDRAGON_NAME,
                "description": "由一条龙任务计划生成，可在任务计划页调整顺序、开关与参数。",
                "graph": graph,
                "tags": ["一条龙", "任务计划"],
                "targetSlot": "nrc-game",
            },
        )
    return db.create_workflow(
        ONEDRAGON_NAME,
        "由一条龙任务计划生成，可在任务计划页调整顺序、开关与参数。",
        graph,
        tags=["一条龙", "任务计划"],
        target_slot="nrc-game",
        workflow_id=ONEDRAGON_WORKFLOW_ID,
    )


def load_plan(db) -> Dict[str, Any]:
    stored = db.get_setting("onedragon")
    return normalize_plan(stored if stored else DEFAULT_PLAN)


def save_plan(db, plan: Dict[str, Any]) -> Dict[str, Any]:
    normalized = normalize_plan(plan)
    db.set_setting("onedragon", normalized)
    sync_workflow(db, normalized)
    return normalized
