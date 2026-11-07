from __future__ import annotations

from ..contracts import FieldDef, NodeContract, NodeResult, PortDef, register
from ..engine.runtime import AbortedRun

INPUT = [PortDef("in", "输入")]
OUT = [PortDef("out", "输出")]


@register(
    NodeContract(
        type="map.locate",
        title="地图定位",
        category="map",
        description="通过小地图识别当前坐标。模拟目标直接读取演示坐标，SIFT 模式使用特征匹配。",
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("threshold", "最低置信度", "number", 0.2, minimum=0.0, maximum=1.0, step=0.05),
            FieldDef("autoCapture", "自动截图", "boolean", True),
        ],
        tags=["SIFT", "坐标"],
    )
)
def map_locate(ctx, node):
    if ctx.frame is None or node.config.get("autoCapture", True):
        ctx.capture()
    position = ctx.position or {}
    confidence = float(position.get("confidence", 0) or 0)
    threshold = float(ctx.eval(node.config.get("threshold"), 0.2) or 0)
    ok = confidence >= threshold
    ctx.vars["last_position"] = position
    if ok:
        ctx.log(f"定位成功 · {position.get('source')} · ({position.get('x')}, {position.get('y')}) · 置信度 {confidence}")
    return NodeResult(
        outputs={
            "ok": ok,
            "x": position.get("x"),
            "y": position.get("y"),
            "lat": position.get("lat"),
            "lng": position.get("lng"),
            "source": position.get("source"),
            "confidence": confidence,
        },
        message=f"定位 {position.get('source', 'unknown')} · {confidence}",
    )


@register(
    NodeContract(
        type="map.route",
        title="规划路线",
        category="map",
        description="按资源名称或分类，从当前位置规划最近邻访问路线。",
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("labels", "资源名称", "text", "宝箱",
                     placeholder="多个用逗号分隔，例如 宝箱,魔法石"),
            FieldDef("categories", "资源分类", "text", "",
                     placeholder="多个用逗号分隔，例如 花草,矿石"),
            FieldDef("limit", "最多访问点", "number", 12, minimum=1, maximum=100, step=1),
            FieldDef("roundtrip", "返回起点", "boolean", False),
        ],
        tags=["路线", "导航"],
    )
)
def map_route(ctx, node):
    labels = [item.strip() for item in str(node.config.get("labels", "")).split(",") if item.strip()]
    categories = [item.strip() for item in str(node.config.get("categories", "")).split(",") if item.strip()]
    limit = int(ctx.eval(node.config.get("limit"), 12) or 12)
    position = ctx.position or {}
    plan = ctx.services.plan_route(
        {"x": position.get("x", 0), "y": position.get("y", 0)},
        labels=labels,
        categories=categories,
        limit=limit,
        roundtrip=bool(node.config.get("roundtrip", False)),
    )
    ctx.vars["route"] = plan["route"]
    ctx.vars["route_distance"] = plan["distancePx"]
    ctx.log(f"路线规划完成 · {plan['count']} 个点 · 相对距离 {plan['distancePx']} px")
    return NodeResult(
        outputs={
            "count": plan["count"],
            "distancePx": plan["distancePx"],
            "estimatedMinutes": plan["estimatedMinutes"],
            "route": plan["route"],
            "labels": labels,
            "categories": categories,
        },
        message=f"路线 {plan['count']} 个点",
    )


@register(
    NodeContract(
        type="map.follow",
        title="沿路线移动",
        category="map",
        description="沿已规划路线移动。模拟目标会更新坐标并记录移动动作。",
        effectful=True,
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("steps", "移动段数", "number", 4, minimum=1, maximum=60, step=1),
            FieldDef("intervalMs", "每段等待", "number", 120, minimum=0, maximum=2000, step=20),
        ],
        tags=["路线", "巡航"],
    )
)
def map_follow(ctx, node):
    route = ctx.vars.get("route") or []
    if not route:
        return NodeResult(outputs={"traveled": 0, "finished": False}, message="没有可跟随的路线")
    steps = int(ctx.eval(node.config.get("steps"), 4) or 4)
    interval = max(0, int(ctx.eval(node.config.get("intervalMs"), 120) or 0))
    index = int(ctx.vars.get("route_index", 0))
    traveled = 0.0
    current = {"x": ctx.position.get("x", 0), "y": ctx.position.get("y", 0)}
    for _ in range(steps):
        if index >= len(route):
            break
        target = route[index]
        dx = float(target.get("x", current["x"])) - current["x"]
        dy = float(target.get("y", current["y"])) - current["y"]
        ctx.act("move", dx=int(dx * 0.25), dy=int(dy * 0.25))
        for _sub in range(4):
            current["x"] += dx / 4
            current["y"] += dy / 4
            traveled += ((dx / 4) ** 2 + (dy / 4) ** 2) ** 0.5
        ctx.position = {
            "source": "follow",
            "x": round(current["x"], 1),
            "y": round(current["y"], 1),
            "confidence": 1.0,
        }
        index += 1
        if ctx.cancel_event.wait(interval / 1000.0):
            ctx.vars["route_index"] = index
            raise AbortedRun("运行已取消")
    finished = index >= len(route)
    ctx.vars["route_index"] = index
    ctx.log(f"沿路线移动到第 {index}/{len(route)} 段")
    return NodeResult(
        outputs={"index": index, "total": len(route), "traveled": round(traveled, 1), "finished": finished},
        message=f"移动 {index}/{len(route)}",
    )
