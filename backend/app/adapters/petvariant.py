"""精灵「模型形态 × 配色」的两个独立维度。

数据来源与口径参考上游 `ElliottZhao666666/rocom-codex-pets-gen` 的
`references/color-appearance.md`（固定提交见 `datasets/pvp/PROVENANCE.md`）：

* **模型形态**由唯一实体 + `form_asset` 决定，例如「本来的样子」「磨损的样子」
  「看守果实的样子」。形态写在名字末尾的括号里。
* **配色**是另一条轴，共九类：常规 / 常规炫彩 / 黑白炫彩 / 赛季限定炫彩 /
  污染 / 异色 / 异色炫彩 / 异色赛季炫彩 / 异色黑白炫彩。

两条轴不能互相顶替：

* 「被污染的样子」在游戏里是**配色/效果**（pollution），不是模型形态，
  所以解析后 `form` 为空、`color_type = "pollution"`，原始括号文本留在 `form_raw`。
* 污染与异色互斥，也不与其它炫彩叠加；异色必须来自 shiny 素材。
* 黑白与「异色黑白」是两类，前者 `normal_black_white`、后者 `shiny_black_white`。

本模块只做名称层面的归类，不下载素材、不判断某个变体在本地有没有图。
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional

# color_type -> (中文标签, 基础目录, 说明)
COLOR_TYPES: Dict[str, Dict[str, Any]] = {
    "normal": {
        "label": "常规", "base_dir": "normal", "effect": "无",
    },
    "normal_glassy": {
        "label": "常规炫彩", "base_dir": "normal", "effect": "当前配色＋粒子/纹样",
    },
    "normal_black_white": {
        "label": "黑白炫彩", "base_dir": "normal", "effect": "当前黑白预设",
    },
    "normal_seasonal": {
        "label": "赛季限定炫彩", "base_dir": "normal", "effect": "当前赛季预设",
    },
    "pollution": {
        "label": "污染", "base_dir": "normal", "effect": "原污染效果",
    },
    "shiny": {
        "label": "异色", "base_dir": "shiny", "effect": "无",
    },
    "shiny_glassy": {
        "label": "异色炫彩", "base_dir": "shiny", "effect": "当前配色＋粒子/纹样",
    },
    "shiny_seasonal": {
        "label": "异色赛季炫彩", "base_dir": "shiny", "effect": "当前赛季预设",
    },
    "shiny_black_white": {
        "label": "异色黑白炫彩", "base_dir": "shiny", "effect": "当前黑白预设",
    },
}

COLOR_ORDER = list(COLOR_TYPES)

FORM_RE = re.compile(r"[（(]([^）)]+)[）)]\s*$")
SEASON_RE = re.compile(r"(?:S|s|第)\s*([0-9]+)\s*赛季|([0-9]+)\s*赛季")

# 括号里出现这些词，说明那是配色/效果而不是模型形态。
_COLOR_WORDS = ("污染", "异色", "炫彩", "黑白", "赛季")


def split_form(name: str) -> tuple[str, str]:
    """`波波螺（被污染的样子）` -> `("波波螺", "被污染的样子")`。"""
    text = str(name or "").strip()
    match = FORM_RE.search(text)
    if not match:
        return text, ""
    return text[: match.start()].strip(), match.group(1).strip()


def _season_of(text: str) -> Optional[int]:
    match = SEASON_RE.search(text)
    if not match:
        return None
    value = match.group(1) or match.group(2)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _looks_like_color(form: str) -> bool:
    return any(word in form for word in _COLOR_WORDS)


def color_type_of(text: str) -> str:
    """按九类口径判定配色类型。判定顺序即优先级。"""
    shiny = "异色" in text
    glassy = "炫彩" in text
    black_white = "黑白" in text
    polluted = "污染" in text
    seasonal = _season_of(text) is not None or "赛季" in text

    # 参考文档：污染与异色互斥，也不与另一种炫彩叠加 —— 污染优先。
    if polluted:
        return "pollution"
    if shiny and black_white:
        return "shiny_black_white"
    if shiny and seasonal:
        return "shiny_seasonal"
    if shiny and glassy:
        return "shiny_glassy"
    if shiny:
        return "shiny"
    if black_white:
        return "normal_black_white"
    if seasonal:
        return "normal_seasonal"
    if glassy:
        return "normal_glassy"
    return "normal"


def classify(name: str, form: str = "") -> Dict[str, Any]:
    """把一条精灵记录拆成「模型形态」与「配色」两轴。

    返回字段：
      base_name   去掉括号后的名字
      form        模型形态标签（配色型括号会被清空）
      form_raw    名字里原本的括号文本
      color_type  九类之一
      color_label 中文标签
      color_base  normal / shiny
      color_effect 该配色的效果说明
      season      赛季序号（没有则 None）
      is_shiny / is_polluted  便捷布尔量
      notes       解析时发现的口径冲突（例如同时写了污染和异色）
    """
    text = str(name or "").strip()
    base, raw_form = split_form(text)
    explicit = str(form or "").strip()
    if explicit and explicit != raw_form:
        source = f"{raw_form} {explicit}".strip()
    else:
        source = raw_form

    combined = f"{base} {source}"
    color_type = color_type_of(combined)
    info = COLOR_TYPES[color_type]

    notes = []
    if "污染" in combined and "异色" in combined:
        notes.append("污染与异色互斥，按参考口径取污染")
    if color_type != "normal" and not _looks_like_color(source):
        notes.append("配色写在名字主体而不是括号里")

    form_label = "" if (source and _looks_like_color(source)) else source
    return {
        "base_name": base,
        "form": form_label,
        "form_raw": source,
        "color_type": color_type,
        "color_label": info["label"],
        "color_base": info["base_dir"],
        "color_effect": info["effect"],
        "season": _season_of(combined) if color_type.endswith("seasonal") else None,
        "is_shiny": color_type.startswith("shiny"),
        "is_polluted": color_type == "pollution",
        "notes": notes,
    }


def variant_summary(names: Iterable[str]) -> Dict[str, int]:
    """统计一批名字的配色分布，只保留非零项。"""
    counts: Dict[str, int] = {}
    for name in names:
        color_type = classify(name)["color_type"]
        counts[color_type] = counts.get(color_type, 0) + 1
    return {key: counts[key] for key in COLOR_ORDER if counts.get(key)}
