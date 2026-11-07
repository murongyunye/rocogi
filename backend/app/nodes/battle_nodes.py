from __future__ import annotations

from ..contracts import FieldDef, NodeContract, NodeResult, PortDef, register

INPUT = [PortDef("in", "输入")]
OUT = [PortDef("out", "输出")]


@register(
    NodeContract(
        type="battle.decide",
        title="对战决策",
        category="battle",
        description="使用对抗式 MCTS 从预设阵容中给出当前局面的推荐动作。",
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("simulations", "模拟次数", "number", 60, minimum=10, maximum=300, step=10),
            FieldDef("record", "写入变量", "boolean", True),
        ],
        tags=["MCTS", "AI"],
    )
)
def battle_decide(ctx, node):
    simulations = int(ctx.eval(node.config.get("simulations"), 60) or 60)
    result = ctx.services.battle_decide(simulations)
    if not result.get("ok"):
        ctx.log(f"对战决策不可用: {result.get('error')}", {"level": "warn"})
        return NodeResult(outputs={"ok": False, "error": result.get("error")}, message="对战决策不可用")
    ctx.vars["battle_action"] = result.get("label")
    ctx.log(f"MCTS 推荐动作 · {result.get('label')}（{result.get('active')} 对 {result.get('enemy')}）")
    return NodeResult(
        outputs={
            "ok": True,
            "label": result.get("label"),
            "active": result.get("active"),
            "enemy": result.get("enemy"),
            "turn": result.get("turn"),
        },
        message=f"推荐 {result.get('label')}",
    )


@register(
    NodeContract(
        type="battle.simulate",
        title="对战推演",
        category="battle",
        description="让两套阵容进行完整 MCTS 对战推演，并输出胜负结果。",
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("opponent", "对手阵容", "select", "wing", options=[
                {"value": "wing", "label": "圣羽翼王队"},
                {"value": "toxic", "label": "千棘盔毒队"},
            ]),
            FieldDef("simulations", "每回合模拟", "number", 30, minimum=10, maximum=200, step=10),
            FieldDef("maxTurns", "最大回合", "number", 20, minimum=1, maximum=60, step=1),
        ],
        tags=["推演", "AI"],
    )
)
def battle_simulate(ctx, node):
    result = ctx.services.battle_simulate(
        None,
        str(node.config.get("opponent", "wing")),
        int(ctx.eval(node.config.get("simulations"), 30) or 30),
        int(ctx.eval(node.config.get("maxTurns"), 20) or 20),
    )
    if not result.get("ok"):
        return NodeResult(outputs={"ok": False, "error": result.get("error")}, message="推演失败")
    ctx.vars["battle_winner"] = result.get("winner")
    ctx.log(f"对战推演结束 · 胜者 {result.get('winner')} · {result.get('turns')} 回合")
    return NodeResult(
        outputs={
            "ok": True,
            "winner": result.get("winner"),
            "turns": result.get("turns"),
            "durationMs": result.get("durationMs"),
        },
        message=f"推演胜者 {result.get('winner')}",
    )
