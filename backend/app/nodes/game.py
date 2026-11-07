from __future__ import annotations

from ..adapters.frame import Frame
from ..adapters.vision import annotate_matches
from ..contracts import FieldDef, NodeContract, NodeResult, PortDef, register

INPUT = [PortDef("in", "输入")]
OUT = [PortDef("out", "输出")]

STRATEGY_FIELD = dict(
    type="select",
    default="gather",
    options=[
        {"value": "gather", "label": "只聚能（按 X）"},
        {"value": "escape", "label": "逃跑（ESC + 确认）"},
        {"value": "skill1_gather", "label": "技能1 后聚能"},
        {"value": "none", "label": "不操作"},
    ],
)


def _capture_if_needed(ctx, node):
    if ctx.frame is None:
        ctx.capture()
    return ctx.require_frame()


@register(
    NodeContract(
        type="game.auto_ball",
        title="自动丢球",
        category="game",
        description="识别可捕捉精灵与交易提示，按配置自动丢球或点击。",
        effectful=True,
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("mode", "触发方式", "select", "key", options=[
                {"value": "key", "label": "按键"},
                {"value": "click", "label": "点击目标"},
            ]),
            FieldDef("key", "触发按键", "text", "x"),
            FieldDef("threshold", "识别阈值", "number", 0.5, minimum=0.1, maximum=1.0, step=0.01),
            FieldDef("autoCapture", "自动截图", "boolean", True),
            FieldDef("annotate", "保存识别截图", "boolean", True),
        ],
        tags=["抓宠", "丢球"],
    )
)
def game_auto_ball(ctx, node):
    frame = _capture_if_needed(ctx, node)
    threshold = float(ctx.eval(node.config.get("threshold"), 0.5) or 0.5)
    matches = [
        ctx.services.match_template(frame, name, threshold, "center", True, 1.0)
        for name in ("elf_P.png", "exchange.png")
    ]
    best = max(matches, key=lambda item: item.get("score", 0.0))
    triggered = bool(best.get("matched"))
    if node.config.get("annotate", True):
        artifact = ctx.save_frame(Frame(image=annotate_matches(frame, matches), meta=frame.meta), "ball")
        ctx.emit("artifact", ctx.current_node_id, "丢球识别", artifact)
    if triggered:
        if node.config.get("mode", "key") == "click":
            ctx.act("click", x=best.get("cx", frame.width // 2), y=best.get("cy", frame.height // 2))
        else:
            ctx.act("key", key=str(node.config.get("key", "x")), presses=1)
        ctx.vars["ball_count"] = int(ctx.vars.get("ball_count", 0)) + 1
        ctx.log(f"检测到可丢球目标，已触发（分数 {best.get('score', 0):.3f}）")
    return NodeResult(
        outputs={
            "triggered": triggered,
            "score": best.get("score", 0.0),
            "template": best.get("template"),
            "ballCount": ctx.vars.get("ball_count", 0),
        },
        message="丢球触发" if triggered else "未发现丢球目标",
    )


@register(
    NodeContract(
        type="game.smart_battle",
        title="战斗应对",
        category="game",
        description="识别普通/污染战斗，并按各自策略执行聚能、逃跑或技能。",
        effectful=True,
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("normalStrategy", "普通战斗策略", **STRATEGY_FIELD),
            FieldDef("pollutedStrategy", "污染战斗策略", **{**STRATEGY_FIELD, "default": "escape"}),
            FieldDef("threshold", "识别阈值", "number", 0.5, minimum=0.1, maximum=1.0, step=0.01),
            FieldDef("autoCapture", "自动截图", "boolean", True),
        ],
        tags=["战斗", "策略"],
    )
)
def game_smart_battle(ctx, node):
    frame = _capture_if_needed(ctx, node)
    threshold = float(ctx.eval(node.config.get("threshold"), 0.5) or 0.5)
    scene = ctx.services.classify_scene(frame, threshold=threshold, use_edges=True)
    kind = scene["kind"]
    if kind not in ("battle_normal", "battle_polluted"):
        return NodeResult(outputs={"battleType": "none", "action": "none"}, message="当前不在战斗")

    polluted = kind == "battle_polluted"
    strategy = node.config.get("pollutedStrategy" if polluted else "normalStrategy", "gather")
    action = strategy
    if strategy == "gather":
        ctx.act("key", key="x", presses=1)
    elif strategy == "skill1_gather":
        ctx.act("key", key="1", presses=1)
        ctx.act("key", key="x", presses=1)
    elif strategy == "escape":
        ctx.act("key", key="esc", presses=1)
        yes = ctx.services.match_template(ctx.frame, "yes.png", threshold * 0.8, "center", True, 1.0)
        if yes.get("matched"):
            ctx.act("click", x=yes.get("cx", frame.width // 2), y=yes.get("cy", frame.height // 2))
            ctx.log("确认逃跑")
    else:
        action = "none"

    battle_type = "polluted" if polluted else "normal"
    ctx.vars["battle_type"] = battle_type
    ctx.vars["battle_count"] = int(ctx.vars.get("battle_count", 0)) + 1
    ctx.log(f"{'污染' if polluted else '普通'}战斗 · 策略 {action}")
    return NodeResult(
        outputs={
            "battleType": battle_type,
            "action": action,
            "battleCount": ctx.vars.get("battle_count", 0),
            "scores": scene["scores"],
        },
        message=f"{'污染' if polluted else '普通'}战斗 · {action}",
    )


@register(
    NodeContract(
        type="game.party_confirm",
        title="同行确认",
        category="game",
        description="检测同行请求并自动按 F 确认。",
        effectful=True,
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("key", "确认按键", "text", "f"),
            FieldDef("threshold", "识别阈值", "number", 0.5, minimum=0.1, maximum=1.0, step=0.01),
            FieldDef("autoCapture", "自动截图", "boolean", True),
        ],
        tags=["队伍"],
    )
)
def game_party_confirm(ctx, node):
    frame = _capture_if_needed(ctx, node)
    threshold = float(ctx.eval(node.config.get("threshold"), 0.5) or 0.5)
    match = ctx.services.match_template(frame, "qiudaidai.png", threshold, "center", True, 1.0)
    confirmed = bool(match.get("matched"))
    if confirmed:
        ctx.act("key", key=str(node.config.get("key", "f")), presses=1)
        ctx.log("检测到同行请求，已按 F 确认")
    return NodeResult(
        outputs={"confirmed": confirmed, "score": match.get("score", 0.0)},
        message="已确认同行" if confirmed else "未检测到同行请求",
    )


@register(
    NodeContract(
        type="game.state",
        title="读取游戏状态",
        category="game",
        description="只读取场景分类结果，不执行任何操作。",
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("threshold", "识别阈值", "number", 0.5, minimum=0.1, maximum=1.0, step=0.01),
            FieldDef("autoCapture", "自动截图", "boolean", True),
        ],
        tags=["状态"],
    )
)
def game_state(ctx, node):
    frame = _capture_if_needed(ctx, node)
    threshold = float(ctx.eval(node.config.get("threshold"), 0.5) or 0.5)
    scene = ctx.services.classify_scene(frame, threshold=threshold, use_edges=True)
    return NodeResult(
        outputs={"kind": scene["kind"], "scores": scene["scores"]},
        message=f"状态 {scene['kind']}",
    )
