from __future__ import annotations

from pathlib import Path

from .config import TEMPLATE_DIR
from .storage import Database


def node(node_id: str, node_type: str, x: float, y: float, config: dict | None = None) -> dict:
    return {"id": node_id, "type": node_type, "x": x, "y": y, "config": config or {}}


def edge(edge_id: str, from_node: str, from_port: str, to_node: str, to_port: str = "in") -> dict:
    return {"id": edge_id, "from": from_node, "fromPort": from_port, "to": to_node, "toPort": to_port}


CATCH_GRAPH = {
    "nodes": [
        node("start", "run.start", 60, 340, {"label": "抓宠循环"}),
        node("init", "flow.set_var", 280, 340, {"name": "tick", "value": "0"}),
        node("loop", "flow.branch", 520, 340, {"condition": "vars.tick < 6"}),
        node("cap", "game.capture", 760, 180, {"region": "full", "save": True}),
        node("classify", "vision.classify", 980, 180, {"threshold": 0.5, "annotate": True}),
        node("battle_q", "flow.branch", 1200, 180, {"condition": "nodes.classify.isBattle"}),
        node("smart", "game.smart_battle", 1440, 60, {
            "normalStrategy": "gather",
            "pollutedStrategy": "escape",
            "threshold": 0.5,
        }),
        node("ball", "game.auto_ball", 1440, 300, {"mode": "key", "key": "x", "threshold": 0.45}),
        node("confirm", "game.party_confirm", 1680, 300, {"key": "f", "threshold": 0.45}),
        node("delay", "flow.delay", 1920, 300, {"ms": 200}),
        node("inc", "flow.set_var", 2160, 180, {"name": "tick", "value": "vars.tick + 1"}),
        node("done_log", "flow.log", 760, 520, {"message": "演示循环结束 · 丢球 {{vars.ball_count}} 次 · 战斗 {{vars.battle_count}} 场"}),
        node("end", "run.stop", 980, 520, {"reason": "抓宠演示完成"}),
    ],
    "edges": [
        edge("e1", "start", "out", "init"),
        edge("e2", "init", "out", "loop"),
        edge("e3", "loop", "true", "cap"),
        edge("e4", "cap", "out", "classify"),
        edge("e5", "classify", "out", "battle_q"),
        edge("e6", "battle_q", "true", "smart"),
        edge("e7", "battle_q", "false", "ball"),
        edge("e8", "smart", "out", "inc"),
        edge("e9", "ball", "out", "confirm"),
        edge("e10", "confirm", "out", "delay"),
        edge("e11", "delay", "out", "inc"),
        edge("e12", "inc", "out", "loop"),
        edge("e13", "loop", "false", "done_log"),
        edge("e14", "done_log", "out", "end"),
    ],
    "subgraphs": {},
    "variables": {"ball_count": 0, "battle_count": 0},
}

ROUTE_GRAPH = {
    "nodes": [
        node("start", "run.start", 80, 220, {"label": "资源巡线"}),
        node("locate", "map.locate", 320, 220, {"threshold": 0.2}),
        node("route", "map.route", 560, 220, {"labels": "宝箱", "limit": 10}),
        node("follow", "map.follow", 800, 220, {"steps": 3, "intervalMs": 120}),
        node("log", "flow.log", 1040, 220, {"message": "已到达 {{nodes.route.count}} 个宝箱点，相对距离 {{nodes.route.distancePx}} px"}),
        node("end", "run.stop", 1280, 220, {"reason": "巡线完成"}),
    ],
    "edges": [
        edge("e1", "start", "out", "locate"),
        edge("e2", "locate", "out", "route"),
        edge("e3", "route", "out", "follow"),
        edge("e4", "follow", "out", "log"),
        edge("e5", "log", "out", "end"),
    ],
    "subgraphs": {},
    "variables": {},
}

BATTLE_GRAPH = {
    "nodes": [
        node("start", "run.start", 80, 220, {"label": "对战推演"}),
        node("sim", "battle.simulate", 340, 220, {"opponent": "wing", "simulations": 15, "maxTurns": 10}),
        node("win_q", "flow.branch", 600, 220, {"condition": "nodes.sim.winner == 'a'"}),
        node("win_log", "flow.log", 860, 120, {"message": "推演胜利 · {{nodes.sim.turns}} 回合"}),
        node("lose_log", "flow.log", 860, 340, {"message": "推演未获胜 · 胜者 {{nodes.sim.winner}}"}),
        node("end", "run.stop", 1120, 220, {"reason": "推演结束"}),
    ],
    "edges": [
        edge("e1", "start", "out", "sim"),
        edge("e2", "sim", "out", "win_q"),
        edge("e3", "win_q", "true", "win_log"),
        edge("e4", "win_q", "false", "lose_log"),
        edge("e5", "win_log", "out", "end"),
        edge("e6", "lose_log", "out", "end"),
    ],
    "subgraphs": {},
    "variables": {},
}


def seed(db: Database) -> None:
    from .onedragon import DEFAULT_PLAN, ONEDRAGON_WORKFLOW_ID, sync_workflow

    if not db.get_workflow("wf_demo_catch"):
        db.create_workflow(
            "抓宠巡航 · 自动丢球",
            "截图识别战斗与可捕捉精灵，普通战斗聚能、污染战斗逃跑，空闲时自动丢球。演示使用模拟游戏窗口，可切换到 Windows 目标。",
            CATCH_GRAPH,
            tags=["抓宠", "战斗", "循环"],
            target_slot="nrc-game",
            workflow_id="wf_demo_catch",
        )
        db.create_workflow(
            "资源巡线 · 宝箱路线",
            "定位当前位置，按宝箱点位规划最近邻路线，并沿路线推进。地图页可查看完整点位与路线。",
            ROUTE_GRAPH,
            tags=["地图", "路线", "SIFT"],
            target_slot="nrc-game",
            workflow_id="wf_demo_route",
        )
        db.create_workflow(
            "对战推演 · MCTS 决策",
            "调用内置洛克王国对战引擎，让两套阵容进行对抗式 MCTS 推演并输出胜负。",
            BATTLE_GRAPH,
            tags=["对战", "MCTS"],
            target_slot="nrc-game",
            workflow_id="wf_demo_battle",
        )

    for path in sorted(Path(TEMPLATE_DIR).glob("*.png")):
        db.upsert_resource(
            f"tpl_{path.stem}",
            "template",
            path.name,
            {"fileName": path.name, "width": None, "height": None,
             "url": f"/api/assets/templates/{path.name}"},
            path=str(path.relative_to(TEMPLATE_DIR.parent.parent)),
            tags=["模板", "视觉"],
        )

    if not db.get_workflow(ONEDRAGON_WORKFLOW_ID):
        sync_workflow(db, DEFAULT_PLAN)
