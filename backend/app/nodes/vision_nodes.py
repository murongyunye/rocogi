from __future__ import annotations

from ..adapters.frame import Frame
from ..adapters.vision import annotate_matches
from ..contracts import FieldDef, NodeContract, NodeResult, PortDef, register

INPUT = [PortDef("in", "输入")]
OUT = [PortDef("out", "输出")]

ROI_OPTIONS = [
    {"value": "full", "label": "整个画面"},
    {"value": "top-right", "label": "右上区域"},
    {"value": "bottom-right", "label": "右下区域"},
    {"value": "center", "label": "中央区域"},
    {"value": "top-half", "label": "上半画面"},
    {"value": "custom", "label": "自定义比例"},
]


@register(
    NodeContract(
        type="vision.template",
        title="模板匹配",
        category="vision",
        description="在画面中查找指定的视觉模板，输出匹配分数与坐标。",
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("template", "模板资源", "resource", "capture.png", required=True, help="来自资源库的 PNG 模板"),
            FieldDef("threshold", "匹配阈值", "number", 0.5, minimum=0.1, maximum=1.0, step=0.01),
            FieldDef("roi", "搜索区域", "select", "full", options=ROI_OPTIONS),
            FieldDef("customRoi", "自定义 ROI", "text", "0.2,0.2,0.6,0.4", help="左,上,宽,高 比例"),
            FieldDef("scale", "模板缩放", "number", 1.0, minimum=0.3, maximum=2.0, step=0.05),
            FieldDef("useEdges", "边缘预处理", "boolean", True),
            FieldDef("annotate", "保存标注截图", "boolean", True),
            FieldDef("autoCapture", "无画面时自动截图", "boolean", True),
        ],
        tags=["识别", "模板"],
    )
)
def vision_template(ctx, node):
    if ctx.frame is None and node.config.get("autoCapture", True):
        ctx.capture()
    frame = ctx.require_frame()
    template = str(node.config.get("template", "capture.png"))
    roi = node.config.get("customRoi") if node.config.get("roi") == "custom" else node.config.get("roi", "full")
    threshold = float(ctx.eval(node.config.get("threshold"), 0.5) or 0.5)
    scale = float(ctx.eval(node.config.get("scale"), 1.0) or 1.0)
    use_edges = bool(node.config.get("useEdges", True))
    match = ctx.services.match_template(frame, template, threshold, roi, use_edges, scale)
    if match.get("ok"):
        ctx.stats.matches += 1
    if match.get("ok") and node.config.get("annotate", True):
        annotated = annotate_matches(frame, [match])
        artifact = ctx.save_frame(Frame(image=annotated, meta=frame.meta), "match")
        ctx.emit("artifact", ctx.current_node_id, f"模板匹配 {template}", artifact)
    return NodeResult(
        outputs={
            "score": match.get("score", 0.0),
            "matched": bool(match.get("matched")),
            "x": match.get("x"),
            "y": match.get("y"),
            "width": match.get("w"),
            "height": match.get("h"),
            "centerX": match.get("cx"),
            "centerY": match.get("cy"),
            "template": template,
        },
        message=f"{template} 分数 {match.get('score', 0):.3f}",
    )


@register(
    NodeContract(
        type="vision.classify",
        title="场景识别",
        category="vision",
        description="综合匹配战斗、污染、可捕捉精灵与同行请求模板，判断当前场景类型。",
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("threshold", "判定阈值", "number", 0.5, minimum=0.1, maximum=1.0, step=0.01),
            FieldDef("useEdges", "边缘预处理", "boolean", True),
            FieldDef("autoCapture", "无画面时自动截图", "boolean", True),
            FieldDef("annotate", "保存识别截图", "boolean", True),
        ],
        tags=["识别", "场景"],
    )
)
def vision_classify(ctx, node):
    if ctx.frame is None and node.config.get("autoCapture", True):
        ctx.capture()
    frame = ctx.require_frame()
    result = ctx.services.classify_scene(
        frame,
        threshold=float(ctx.eval(node.config.get("threshold"), 0.5) or 0.5),
        use_edges=bool(node.config.get("useEdges", True)),
    )
    if node.config.get("annotate", True):
        annotated = annotate_matches(frame, list(result["details"].values()))
        artifact = ctx.save_frame(Frame(image=annotated, meta=frame.meta), "classify")
        ctx.emit("artifact", ctx.current_node_id, f"场景识别 {result['kind']}", artifact)
    ctx.vars["scene"] = result["kind"]
    return NodeResult(
        outputs={
            "kind": result["kind"],
            "scores": result["scores"],
            "isBattle": result["kind"] in ("battle_normal", "battle_polluted"),
            "isPolluted": result["kind"] == "battle_polluted",
        },
        message=f"场景 {result['kind']}",
    )
