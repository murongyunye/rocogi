"""Delias 契约字段规整。

本模块只做字段映射与推导：输入是 rocogi 引擎已有返回值，输出对应 Delias
``registry/tools.yaml`` 的 output 契约。不抓图、不调用模型、不写盘。

字段语义、取值范围与仍存在的限制见：

- ``docs/deepseek-harness.md`` 第 9 节
- ``docs/delias-adapter-report.md``
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List

_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")

_VENDOR_SUMMARY_KEYS = (
    "adapted",
    "resolved",
    "pendingReboot",
    "partial",
    "contractBlocked",
    "blockedCount",
)


# 11 个契约动作的必填输入字段。harness_actions.tools_schema 的 required
# 与 harness_actions.dispatch 的参数校验都以这里为准，测试会锁定三者一致。
ACTION_REQUIRED_FIELDS: Dict[str, tuple] = {
    "match_template": ("template",),
    "detect_sprites": (),
    "ocr": ("roi",),
    "foreground": (),
    "set_input_backend": ("backend",),
    "route_plan": (),
    "map_points": (),
    "turn_state": (),
    "vendor_status": (),
    "vendor_action": ("action",),
    "vendor_blocked": (),
}


# 每个契约动作在 result 中保证出现的顶层字段。可选字段（error /
# estimated_minutes / vendor 摘要计数）不在此列；测试会用 dispatch 的真实
# 返回值校验这里始终是实现输出的子集。
ACTION_OUTPUT_FIELDS: Dict[str, tuple] = {
    "match_template": ("matched", "score", "points", "template", "roi", "frame"),
    "detect_sprites": ("candidates", "count", "source", "roi", "model", "min_confidence", "sprites", "frame"),
    "ocr": ("text", "value", "confidence", "mode", "chars", "source", "roi", "frame"),
    "foreground": ("focused", "hwnd", "supported", "restored", "foreground", "reason"),
    "set_input_backend": ("requested", "backend", "available", "fallback_reason"),
    "route_plan": ("route", "total_distance", "count", "start"),
    "map_points": ("points", "total"),
    "turn_state": ("turn", "enemyHp", "skills", "polluted", "phase", "scene", "enemy", "ocr", "rois", "frame"),
    "vendor_status": ("action", "adapters", "count"),
    "vendor_action": ("action",),
    "vendor_blocked": ("action", "adapters", "count")
}

# 22 个运行期既有动作在成功路径上的 result 顶层保证字段。列表型返回值
# （list_workflows）与存在多种返回形态的动作（dex_lookup）不声明任何键。
RUNTIME_OUTPUT_FIELDS: Dict[str, tuple] = {
    "get_state": ("platform", "target", "enginePreset", "realtime", "tracker", "workflows", "activeRuns", "latestRun"),
    "dex_lookup": (),
    "pvp_analyze": ("ok", "members", "metrics", "roles", "notes"),
    "pvp_matchup": ("ok", "player", "opponent", "enemy", "battle", "winner", "turns", "durationMs", "logs"),
    "observe": ("timestamp", "scene", "position", "frame", "screenshot", "sessions"),
    "capture": ("screenshot", "frame"),
    "press_key": ("key", "presses"),
    "click": ("x", "y"),
    "move": ("dx", "dy"),
    "locate": ("position",),
    "start_realtime": ("running", "status", "error", "config"),
    "stop_realtime": ("running", "status", "error", "config"),
    "start_tracker": ("running", "status", "error", "config"),
    "stop_tracker": ("running", "status", "error", "config"),
    "list_workflows": (),
    "run_workflow": ("runId", "workflowId", "run"),
    "run_onedragon": ("runId", "plan"),
    "run_status": ("run", "events", "lastText"),
    "stop_run": ("runId", "stopping"),
    "battle_decision": ("ok", "action", "label", "active", "enemy", "turn"),
    "battle_simulate": ("ok", "winner", "turns", "durationMs", "teamA", "teamB", "logs", "records"),
    "sequence": ("steps",),
}

# 无法用扁平 required 表达的“至少给出一个”约束，取自实现：
# run_workflow 按 workflowId 或 name 查找工作流，两者都缺失时返回 workflow not found。
ACTION_REQUIRED_ANY: Dict[str, tuple] = {
    "run_workflow": ("workflowId", "name"),
}

# 风险分级：read_only（无外部副作用）/ external_side_effect（有外部副作用但可停止）/ irreversible（不可逆）。
# effectful = risk != "read_only"。每个动作必须在此分级，新增动作若漏登记测试会立即失败。
ACTION_RISK: Dict[str, str] = {
    "observe": "read_only",
    "capture": "read_only",
    "press_key": "external_side_effect",
    "click": "external_side_effect",
    "move": "external_side_effect",
    "locate": "read_only",
    "start_realtime": "external_side_effect",
    "stop_realtime": "external_side_effect",
    "start_tracker": "external_side_effect",
    "stop_tracker": "external_side_effect",
    "list_workflows": "read_only",
    "run_workflow": "irreversible",
    "run_onedragon": "irreversible",
    "run_status": "read_only",
    "stop_run": "external_side_effect",
    "battle_decision": "read_only",
    "battle_simulate": "read_only",
    "dex_lookup": "read_only",
    "pvp_analyze": "read_only",
    "pvp_matchup": "read_only",
    "get_state": "read_only",
    "sequence": "irreversible",
    "match_template": "read_only",
    "detect_sprites": "read_only",
    "ocr": "read_only",
    "foreground": "external_side_effect",
    "set_input_backend": "external_side_effect",
    "route_plan": "read_only",
    "map_points": "read_only",
    "turn_state": "read_only",
    "vendor_status": "read_only",
    "vendor_action": "irreversible",
    "vendor_blocked": "read_only",
}


def _number(value: Any, digits: int = 4) -> float:
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return 0.0


def match_contract(match: Dict[str, Any]) -> Dict[str, Any]:
    """把 ``vision.match_template`` 结果映射成 Delias match_template 契约。

    ``points`` 只有在 ``matched=True`` 时包含一个框；坐标是整帧像素坐标。
    ``score`` 是 OpenCV TM_CCOEFF_NORMED 结果，已裁剪到 0..1，不是概率。
    """
    matched = bool(match.get("matched"))
    points: List[Dict[str, Any]] = []
    if matched:
        points.append(
            {
                "x": int(match.get("x") or 0),
                "y": int(match.get("y") or 0),
                "w": int(match.get("w") or 0),
                "h": int(match.get("h") or 0),
                "cx": int(match.get("cx") or 0),
                "cy": int(match.get("cy") or 0),
                "score": _number(match.get("score")),
            }
        )
    result = {
        "matched": matched,
        "score": _number(match.get("score")),
        "points": points,
        "template": match.get("template"),
        "roi": match.get("roi"),
    }
    if match.get("error"):
        result["error"] = str(match["error"])
    return result


def sprite_contract(raw: Dict[str, Any], min_confidence: float = 0.0) -> Dict[str, Any]:
    """把 ``detector.detect_sprites`` 结果映射成 Delias detect_sprites 契约。

    ``candidates[].bbox`` 是整帧像素矩形；``confidence`` 即引擎的 ``score``。
    ``track_id`` 目前恒为 ``None``：检测器本身不做跨帧关联，这里不伪造 ID。
    """
    sprites = list(raw.get("sprites") or [])
    threshold = float(min_confidence)
    candidates: List[Dict[str, Any]] = []
    for item in sprites:
        confidence = _number(item.get("score"))
        if confidence < threshold:
            continue
        candidates.append(
            {
                "bbox": {
                    "x": int(item.get("x") or 0),
                    "y": int(item.get("y") or 0),
                    "w": int(item.get("w") or 0),
                    "h": int(item.get("h") or 0),
                },
                "confidence": confidence,
                "cx": int(item.get("cx") or 0),
                "cy": int(item.get("cy") or 0),
                "label": str(item.get("label") or "sprite"),
                "track_id": None,
            }
        )
    return {
        "candidates": candidates,
        "count": len(candidates),
        "source": raw.get("source"),
        "roi": raw.get("roi"),
        "model": raw.get("model"),
        "min_confidence": _number(min_confidence),
        "sprites": sprites,
    }


def ocr_contract(raw: Dict[str, Any], mode: str = "number") -> Dict[str, Any]:
    """把 ``ocr.read_text`` 结果映射成 Delias ocr 契约。

    ``value`` 取识别文本中的第一个数字，保持文本单位：``"45%"`` 得到 45.0，
    ``"回合 12"`` 得到 12.0。``mode="text"`` 或无数字时为 ``None``。
    """
    text = str(raw.get("text") or "")
    value = None
    if mode in ("number", "percentage"):
        found = _NUMBER_RE.search(text)
        if found:
            try:
                value = float(found.group(0))
            except ValueError:
                value = None
    return {
        "text": text,
        "value": value,
        "confidence": _number(raw.get("confidence")),
        "mode": mode,
        "chars": list(raw.get("chars") or []),
        "source": raw.get("source"),
        "roi": raw.get("roi"),
    }


def foreground_contract(raw: Dict[str, Any]) -> Dict[str, Any]:
    """把 ``ensure_foreground`` 结果映射成 Delias foreground 契约。

    ``focused`` 表示调用后目标窗口是否真的位于前台；``ok`` 只表示检查已执行。
    """
    hwnd = raw.get("hwnd") or 0
    return {
        "focused": bool(raw.get("ok")),
        "hwnd": str(int(hwnd)) if hwnd else "",
        "supported": bool(raw.get("supported", False)),
        "restored": bool(raw.get("restored", False)),
        "foreground": raw.get("foreground"),
        "reason": raw.get("reason"),
    }


def input_backend_contract(
    requested: str,
    backend: str,
    available: bool,
    fallback_reason: str | None = None,
) -> Dict[str, Any]:
    """把输入后端自检结果映射成 Delias set_input_backend 契约。"""
    return {
        "requested": requested,
        "backend": backend,
        "available": bool(available),
        "fallback_reason": fallback_reason,
    }


def route_contract(route: Any, total_distance: Any) -> Dict[str, Any]:
    """把 ``MapData.plan_route`` 的路线映射成 Delias route_plan 契约。

    ``total_distance`` 单位与 ``distancePx`` 相同，为地图像素。
    """
    items = list(route or [])
    return {"route": items, "total_distance": _number(total_distance, 1), "count": len(items)}


def route_from_points(points: List[Dict[str, Any]], start: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """按最近邻顺序串起调用方给出的点位。

    引擎的 ``MapData.plan_route`` 只接受 label/category 过滤，Delias 的
    ``route_plan`` 以 points 为输入；这里用与 ``plan_route`` 相同的贪心最近邻
    规则补齐。距离单位为地图像素，起点为 ``start``。距离相同时取原始下标更小
    者，因此结果确定，但不是全局最优路径，也不做避障。
    """
    current_x = float((start or {}).get("x") or 0.0)
    current_y = float((start or {}).get("y") or 0.0)
    remaining = [dict(item) for item in (points or [])]
    route: List[Dict[str, Any]] = []
    total = 0.0
    while remaining:
        index = min(
            range(len(remaining)),
            key=lambda i: (float(remaining[i].get("x") or 0.0) - current_x) ** 2
            + (float(remaining[i].get("y") or 0.0) - current_y) ** 2,
        )
        item = remaining.pop(index)
        px = float(item.get("x") or 0.0)
        py = float(item.get("y") or 0.0)
        leg = math.hypot(px - current_x, py - current_y)
        total += leg
        item["leg_distance"] = round(leg, 1)
        route.append(item)
        current_x, current_y = px, py
    return {"route": route, "total_distance": round(total, 1), "count": len(route)}


def points_contract(points: Any, total: int) -> Dict[str, Any]:
    """把地图点位列表映射成 Delias map_points 契约。"""
    return {"points": list(points or []), "total": int(total)}


def turn_contract(state: Dict[str, Any]) -> Dict[str, Any]:
    """把 ``read_turn_state`` 结果映射成 Delias turn_state 契约。

    ``enemyHp`` 直接取 ``enemy.hpPercent``：由血条亮色像素占比换算的 0..100
    整数，不是游戏内精确 HP。
    """
    enemy = state.get("enemy") or {}
    return {
        "turn": state.get("turn"),
        "enemyHp": enemy.get("hpPercent"),
        "skills": list(state.get("skills") or []),
        "polluted": bool(state.get("polluted")),
        "phase": state.get("phase"),
        "scene": state.get("scene"),
        "enemy": enemy,
        "ocr": state.get("ocr") or {},
        "rois": state.get("rois") or {},
    }


def vendor_contract(raw: Dict[str, Any], action: str) -> Dict[str, Any]:
    """把 vendor 引擎结果映射成 Delias 的 vendor 契约。

    ``status`` / ``blocked``：Delias 契约要求 ``adapters`` 是对象（按适配器名
    索引），原样保留，并保留 adapted/resolved/partial 等计数。
    单个适配器动作：引擎 JSON 本身就是契约（status/checks/blockers/seconds），
    这里直接平铺，不额外包一层 ``adapters``。
    """
    if action in ("status", "blocked"):
        adapters = raw.get("adapters")
        if not isinstance(adapters, (dict, list)):
            adapters = {}
        result: Dict[str, Any] = {
            "action": action,
            "adapters": adapters,
            "count": len(adapters),
        }
        for key in _VENDOR_SUMMARY_KEYS:
            if key in raw:
                result[key] = raw[key]
        return result
    result = {key: value for key, value in raw.items() if key not in ("ok", "returncode")}
    result["action"] = action
    result["returncode"] = raw.get("returncode")
    return result
