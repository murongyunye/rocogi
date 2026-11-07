from __future__ import annotations

from ..contracts import FieldDef, NodeContract, NodeResult, PortDef, register
from ..engine.expression import ExpressionError
from ..engine.runtime import AbortedRun

INPUT = [PortDef("in", "输入")]
OUT = [PortDef("out", "输出")]


@register(
    NodeContract(
        type="run.start",
        title="运行开始",
        category="run",
        description="工作流的入口。一个工作流可以包含多个入口。",
        outputs=[PortDef("out", "开始")],
        fields=[FieldDef("label", "入口名称", "text", "开始", placeholder="例如：抓宠循环")],
        tags=["入口"],
    )
)
def run_start(ctx, node):
    return NodeResult(outputs={"label": node.config.get("label", "开始")}, message="进入工作流")


@register(
    NodeContract(
        type="run.stop",
        title="结束运行",
        category="run",
        description="停止当前运行，并把结果写入运行记录。",
        effectful=True,
        inputs=INPUT,
        fields=[FieldDef("reason", "结束原因", "text", "正常结束")],
        tags=["终止"],
    )
)
def run_stop(ctx, node):
    return NodeResult(outputs={"reason": node.config.get("reason")}, stop=True, message=ctx.text(node.config.get("reason", "正常结束")))


@register(
    NodeContract(
        type="flow.delay",
        title="等待",
        category="flow",
        description="等待指定毫秒数，期间可以中断运行。",
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("ms", "等待毫秒", "number", 300, minimum=0, maximum=60000, step=50, required=True),
        ],
        tags=["时间"],
    )
)
def flow_delay(ctx, node):
    ms = int(ctx.eval(node.config.get("ms"), 300) or 0)
    ms = max(0, min(ms, 60000))
    if ctx.cancel_event.wait(ms / 1000.0):
        raise AbortedRun("运行已取消")
    return NodeResult(outputs={"ms": ms}, message=f"等待 {ms} ms")


@register(
    NodeContract(
        type="flow.log",
        title="记录日志",
        category="flow",
        description="向运行时间线写入一条日志，支持 {{ }} 表达式。",
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("message", "日志内容", "textarea", "节点执行中", required=True, rows=2),
            FieldDef("level", "级别", "select", "info", options=[
                {"value": "info", "label": "信息"},
                {"value": "warn", "label": "警告"},
                {"value": "error", "label": "错误"},
            ]),
        ],
        tags=["日志"],
    )
)
def flow_log(ctx, node):
    message = ctx.text(node.config.get("message", ""))
    level = node.config.get("level", "info")
    ctx.log(message, {"level": level})
    return NodeResult(outputs={"message": message, "level": level}, message=message[:80])


@register(
    NodeContract(
        type="flow.set_var",
        title="设置变量",
        category="flow",
        description="把表达式结果写入运行变量，后续节点可通过 vars.名称 引用。",
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("name", "变量名", "text", "battle_count", required=True, placeholder="仅字母数字下划线"),
            FieldDef("value", "值表达式", "expression", "0", required=True, help="例如 nodes.cap.score 或 vars.count + 1"),
        ],
        tags=["变量"],
    )
)
def flow_set_var(ctx, node):
    name = str(node.config.get("name", "")).strip()
    if not name or not name.replace("_", "").isalnum():
        raise AbortedRun("变量名只允许字母、数字和下划线")
    value = ctx.eval(node.config.get("value"), 0)
    ctx.vars[name] = value
    return NodeResult(outputs={name: value}, message=f"{name} = {value}")


@register(
    NodeContract(
        type="flow.branch",
        title="条件分支",
        category="flow",
        description="条件为真时走「真」分支，否则走「假」分支。两条分支都可以继续连接节点。",
        inputs=INPUT,
        outputs=[PortDef("true", "真"), PortDef("false", "假")],
        fields=[
            FieldDef("condition", "条件表达式", "expression", "vars.count > 0", required=True,
                     help="例如 nodes.classify.kind == 'battle_normal'"),
        ],
        tags=["控制流"],
    )
)
def flow_branch(ctx, node):
    condition = node.config.get("condition", "")
    if not str(condition).strip():
        raise AbortedRun("条件分支缺少条件表达式")
    try:
        value = ctx.eval(condition, False)
    except ExpressionError as exc:
        raise AbortedRun(f"条件表达式错误: {exc}") from exc
    port = "true" if bool(value) else "false"
    return NodeResult(outputs={"condition": bool(value)}, next_port=port, message=f"条件 {bool(value)}")


@register(
    NodeContract(
        type="flow.subgraph",
        title="子图",
        category="flow",
        description="调用工作流内的可复用子图。",
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("subgraphId", "子图 ID", "text", "", required=True, help="在 graph.subgraphs 中定义"),
        ],
        tags=["复用"],
    )
)
def flow_subgraph(ctx, node):
    subgraph_id = str(node.config.get("subgraphId", "")).strip()
    if not subgraph_id:
        raise AbortedRun("子图节点缺少 subgraphId")
    result = ctx.run_subgraph(subgraph_id)
    return NodeResult(outputs={"subgraph": subgraph_id, "stats": result}, message=f"子图 {subgraph_id} 完成")


@register(
    NodeContract(
        type="flow.foreach",
        title="遍历子图",
        category="flow",
        description="对表达式给出的列表逐项执行同一个子图，每轮把当前项写入指定变量。",
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("items", "列表表达式", "expression", "[]", required=True, help="例如 vars.points 或 [1, 2, 3]"),
            FieldDef("itemVar", "当前项变量名", "text", "item", required=True),
            FieldDef("subgraphId", "子图 ID", "text", "", required=True, help="在 graph.subgraphs 中定义"),
        ],
        tags=["控制流", "复用"],
    )
)
def flow_foreach(ctx, node):
    items = ctx.eval(node.config.get("items"), [])
    if not isinstance(items, (list, tuple)):
        raise AbortedRun("遍历节点需要一个列表表达式")
    subgraph_id = str(node.config.get("subgraphId", "")).strip()
    if not subgraph_id:
        raise AbortedRun("遍历节点缺少 subgraphId")
    item_var = str(node.config.get("itemVar", "item")).strip() or "item"
    runs = []
    for index, item in enumerate(items):
        ctx.vars[item_var] = item
        ctx.log(f"{item_var}[{index}] = {item}", {"level": "info", "index": index})
        runs.append(ctx.run_subgraph(subgraph_id))
    return NodeResult(
        outputs={"count": len(items), "items": list(items), "runs": len(runs)},
        message=f"遍历 {len(items)} 项完成",
    )
