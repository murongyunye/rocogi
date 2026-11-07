from __future__ import annotations

from ..adapters.frame import Frame
from ..adapters.vision import resolve_roi
from ..contracts import FieldDef, NodeContract, NodeResult, PortDef, register

INPUT = [PortDef("in", "输入")]
OUT = [PortDef("out", "输出")]


@register(
    NodeContract(
        type="game.capture",
        title="游戏截图",
        category="capture",
        description="从已绑定的游戏目标抓取一帧，并把截图写入运行证据。",
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("region", "采集区域", "select", "full", options=[
                {"value": "full", "label": "整个窗口"},
                {"value": "top-right", "label": "右上区域"},
                {"value": "bottom-right", "label": "右下区域"},
                {"value": "center", "label": "中央区域"},
                {"value": "custom", "label": "自定义比例"},
            ]),
            FieldDef("customRegion", "自定义区域", "text", "0.2,0.2,0.6,0.4",
                     help="左,上,宽,高 的比例值"),
            FieldDef("save", "保存截图证据", "boolean", True),
        ],
        tags=["截图", "目标"],
    )
)
def game_capture(ctx, node):
    frame = ctx.capture(save=False)
    region = node.config.get("region", "full")
    region_value = node.config.get("customRegion") if region == "custom" else region
    if region_value and region_value != "full":
        x, y, w, h = resolve_roi(frame, region_value)
        cropped = Frame(
            image=frame.image[y : y + h, x : x + w].copy(),
            meta={**frame.meta, "crop": [x, y, w, h], "sourceFrame": frame.summary()},
        )
        frame = cropped
    ctx.frame = frame
    if node.config.get("save", True):
        artifact = ctx.save_frame(frame, "capture")
    else:
        artifact = None
    return NodeResult(
        outputs={
            "width": frame.width,
            "height": frame.height,
            "scene": frame.meta.get("scene", "unknown"),
            "artifact": artifact,
        },
        message=f"截取 {frame.width}x{frame.height} · {frame.meta.get('scene', 'unknown')}",
    )


@register(
    NodeContract(
        type="input.key",
        title="按键",
        category="input",
        description="向游戏窗口发送按键。模拟目标会把动作记录到运行日志。",
        effectful=True,
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("key", "按键", "text", "x", required=True, placeholder="x / 1 / esc / f"),
            FieldDef("presses", "次数", "number", 1, minimum=1, maximum=20, step=1),
            FieldDef("interval", "间隔秒", "number", 0.08, minimum=0, maximum=2, step=0.01),
        ],
        tags=["键鼠"],
    )
)
def input_key(ctx, node):
    key = str(node.config.get("key", "x"))
    presses = int(ctx.eval(node.config.get("presses"), 1) or 1)
    interval = float(ctx.eval(node.config.get("interval"), 0.08) or 0)
    ctx.act("key", key=key, presses=presses, interval=interval)
    ctx.log(f"按键 {key.upper()} x{presses}")
    return NodeResult(outputs={"key": key, "presses": presses}, message=f"按键 {key}")


@register(
    NodeContract(
        type="input.click",
        title="点击坐标",
        category="input",
        description="在游戏窗口内点击指定坐标或画面中心。",
        effectful=True,
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("x", "X 表达式", "expression", "frame.width * 0.5"),
            FieldDef("y", "Y 表达式", "expression", "frame.height * 0.75"),
            FieldDef("button", "按键", "select", "left", options=[
                {"value": "left", "label": "左键"},
                {"value": "right", "label": "右键"},
            ]),
        ],
        tags=["键鼠"],
    )
)
def input_click(ctx, node):
    x = int(float(ctx.eval(node.config.get("x"), 0) or 0))
    y = int(float(ctx.eval(node.config.get("y"), 0) or 0))
    ctx.act("click", x=x, y=y, button=node.config.get("button", "left"))
    return NodeResult(outputs={"x": x, "y": y}, message=f"点击 ({x}, {y})")


@register(
    NodeContract(
        type="input.move",
        title="移动视角",
        category="input",
        description="发送鼠标相对移动，用于转向或对准精灵。",
        effectful=True,
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("dx", "水平位移", "number", 0, minimum=-2000, maximum=2000, step=5),
            FieldDef("dy", "垂直位移", "number", 0, minimum=-2000, maximum=2000, step=5),
        ],
        tags=["键鼠"],
    )
)
def input_move(ctx, node):
    dx = int(ctx.eval(node.config.get("dx"), 0) or 0)
    dy = int(ctx.eval(node.config.get("dy"), 0) or 0)
    ctx.act("move", dx=dx, dy=dy)
    return NodeResult(outputs={"dx": dx, "dy": dy}, message=f"移动 ({dx}, {dy})")
