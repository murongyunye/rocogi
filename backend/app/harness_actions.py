"""把 rocogi 引擎已有能力暴露成 Delias 需要的 harness 动作。

这些是新增的独立 action：不改名、不改动既有 action 的字段与语义。契约字段
全部由 ``harness_contracts`` 生成，语义说明见 ``docs/deepseek-harness.md``
第 9 节与 ``docs/delias-adapter-report.md``。
"""

from __future__ import annotations

from typing import Any, Dict, List

from . import engine_vendor
from . import harness_contracts as contracts
from .adapters import detector, ocr
from .adapters.input import create_input
from .adapters.turn_state import read_turn_state
from .adapters.window import ensure_foreground

ACTIONS = (
    "match_template",
    "detect_sprites",
    "ocr",
    "foreground",
    "set_input_backend",
    "route_plan",
    "map_points",
    "turn_state",
    "vendor_status",
    "vendor_action",
    "vendor_blocked",
)

_BACKEND_ALIASES = {
    "sendinput": "windows",
    "windows": "windows",
    "mock": "mock",
    "interception": "interception",
}
_OCR_MODES = ("number", "percentage", "text")
_VENDOR_ACTIONS = (
    "rocopilot",
    "auto_rocokingdom",
    "luoke_location",
    "roco_map_tracker",
    "autocapture",
    "game_automation",
    "nrc_ai",
    "adolph_rules",
    "balance_lab",
)


def _tool(name: str, description: str, params: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {"name": name, "description": description, "parameters": params},
    }


def _error(action: str, message: str) -> Dict[str, Any]:
    return {"ok": False, "action": action, "error": message}


def _clamp01(value: Any, default: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return float(default)


def _int_param(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _roi(value: Any) -> List[float] | None:
    """把 Delias 的 ``{x,y,w,h}`` 或 ``[x,y,w,h]`` 规整成归一化比例列表。"""
    if isinstance(value, dict):
        value = [value.get(key) for key in ("x", "y", "w", "h")]
    if isinstance(value, (list, tuple)) and len(value) == 4:
        try:
            return [float(item) for item in value]
        except (TypeError, ValueError):
            return None
    return None


def tools_schema() -> List[Dict[str, Any]]:
    return [
        _tool(
            "rocogi_match_template",
            "Match one template against the current screen. Returns matched, score and pixel-space points for Delias match_template.",
            {
                "type": "object",
                "properties": {
                    "template": {"type": "string"},
                    "threshold": {"type": "number", "minimum": 0, "maximum": 1},
                    "roi": {"type": ["object", "array", "string"]},
                },
                "required": list(contracts.ACTION_REQUIRED_FIELDS["match_template"]),
            },
        ),
        _tool(
            "rocogi_detect_sprites",
            "Detect sprite candidates in the current screen. Returns candidates with bbox, confidence and center for Delias detect_sprites.",
            {
                "type": "object",
                "properties": {
                    "roi": {"type": ["object", "array"]},
                    "min_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "maxItems": {"type": "integer", "minimum": 1, "maximum": 50},
                    "model": {"type": "string"},
                },
            },
        ),
        _tool(
            "rocogi_ocr",
            "Read a HUD region and return text, numeric value and confidence for Delias ocr.",
            {
                "type": "object",
                "properties": {
                    "roi": {"type": ["object", "array"]},
                    "mode": {"type": "string", "enum": list(_OCR_MODES)},
                    "engine": {"type": "string", "enum": ["auto", "builtin", "tesseract"]},
                    "min_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": list(contracts.ACTION_REQUIRED_FIELDS["ocr"]),
            },
        ),
        _tool(
            "rocogi_foreground",
            "Bring the game window to the foreground and report focused/hwnd for Delias foreground.",
            {
                "type": "object",
                "properties": {"window_title": {"type": "string"}, "hwnd": {"type": "integer"}},
            },
        ),
        _tool(
            "rocogi_set_input_backend",
            "Validate an input backend and report availability plus fallback reason for Delias set_input_backend.",
            {
                "type": "object",
                "properties": {
                    "backend": {"type": "string", "enum": ["mock", "sendinput", "windows", "interception"]},
                },
                "required": list(contracts.ACTION_REQUIRED_FIELDS["set_input_backend"]),
            },
        ),
        _tool(
            "rocogi_route_plan",
            "Plan a pixel-space route over explicit points or map labels. Returns route and total_distance for Delias route_plan.",
            {
                "type": "object",
                "properties": {
                    "points": {"type": "array", "items": {"type": "object"}},
                    "start": {"type": "object"},
                    "labels": {"type": "array", "items": {"type": "string"}},
                    "categories": {"type": "array", "items": {"type": "string"}},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 200},
                    "roundtrip": {"type": "boolean"},
                },
            },
        ),
        _tool(
            "rocogi_map_points",
            "List map points filtered by mark_type or pixel bounds. Returns points and total for Delias map_points.",
            {
                "type": "object",
                "properties": {
                    "mark_type": {"type": "integer"},
                    "bounds": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "number"},
                            "y": {"type": "number"},
                            "w": {"type": "number"},
                            "h": {"type": "number"},
                        },
                    },
                    "labels": {"type": "array", "items": {"type": "string"}},
                    "categories": {"type": "array", "items": {"type": "string"}},
                    "limit": {"type": "integer", "minimum": 1},
                },
            },
        ),
        _tool(
            "rocogi_turn_state",
            "Read the battle HUD into turn, enemyHp, skills and polluted for Delias turn_state.",
            {"type": "object", "properties": {}},
        ),
        _tool(
            "rocogi_vendor_status",
            "Report every vendored adapter contract and resolution state for Delias vendor_status.",
            {"type": "object", "properties": {}},
        ),
        _tool(
            "rocogi_vendor_action",
            "Run one vendored adapter action and return its raw result for Delias vendor_action.",
            {
                "type": "object",
                "properties": {"action": {"type": "string", "enum": list(_VENDOR_ACTIONS)}},
                "required": list(contracts.ACTION_REQUIRED_FIELDS["vendor_action"]),
            },
        ),
        _tool(
            "rocogi_vendor_blocked",
            "Run the blocked-adapter summary and return blockers verbatim for Delias vendor_blocked.",
            {"type": "object", "properties": {}},
        ),
    ]


def dispatch(services: Any, settings: Dict[str, Any], action: str, params: Dict[str, Any]) -> Dict[str, Any] | None:
    """处理契约动作；未知动作返回 ``None``，交回 harness.execute。"""
    if action not in ACTIONS:
        return None

    if action == "match_template":
        template = str(params.get("template") or "").strip()
        if not template:
            return _error(action, "template required")
        roi: Any = params.get("roi") or "full"
        if not isinstance(roi, str):
            normalized = _roi(roi)
            if normalized is None:
                return _error(action, "roi must be {x,y,w,h} or [x,y,w,h] normalized")
            roi = normalized
        frame = services.capture(settings)
        match = services.match_template(
            frame,
            template,
            threshold=_clamp01(params.get("threshold"), 0.8),
            roi=roi,
        )
        result = contracts.match_contract(match)
        result["frame"] = frame.summary()
        return {"ok": bool(match.get("ok")), "action": action, "result": result}

    if action == "detect_sprites":
        roi = params.get("roi")
        if roi in (None, "", "full"):
            roi = None
        else:
            normalized = _roi(roi)
            if normalized is None:
                return _error(action, "roi must be {x,y,w,h} or [x,y,w,h] normalized")
            roi = normalized
        frame = services.capture(settings)
        options = dict(settings.get("vision", {}))
        if params.get("model"):
            options["model"] = str(params["model"])
        min_confidence = _clamp01(params.get("min_confidence") or params.get("threshold"), 0.4)
        raw = detector.detect_sprites(
            frame.image,
            options,
            roi=roi,
            threshold=min_confidence,
            max_items=_int_param(params.get("maxItems") or params.get("max_items"), 12),
        )
        result = contracts.sprite_contract(raw, min_confidence)
        result["frame"] = frame.summary()
        return {"ok": True, "action": action, "result": result}

    if action == "ocr":
        roi = _roi(params.get("roi"))
        if roi is None:
            return _error(action, "roi must be {x,y,w,h} or [x,y,w,h] normalized")
        mode = str(params.get("mode") or "number")
        if mode not in _OCR_MODES:
            return _error(action, f"mode must be one of {_OCR_MODES}")
        frame = services.capture(settings)
        raw = ocr.read_text(
            frame.image,
            roi=roi,
            engine=str(params.get("engine") or "auto"),
            min_confidence=_clamp01(params.get("min_confidence"), 0.45),
        )
        result = contracts.ocr_contract(raw, mode)
        result["frame"] = frame.summary()
        return {"ok": True, "action": action, "result": result}

    if action == "foreground":
        title = str(
            params.get("window_title")
            or params.get("title")
            or settings.get("target", {}).get("window_title")
            or ""
        )
        raw = ensure_foreground(title, _int_param(params.get("hwnd"), 0))
        result = contracts.foreground_contract(raw)
        payload: Dict[str, Any] = {"ok": bool(result["supported"]), "action": action, "result": result}
        if not result["supported"]:
            payload["error"] = result["reason"]
        return payload

    if action == "set_input_backend":
        requested = str(params.get("backend") or "")
        normalized = _BACKEND_ALIASES.get(requested)
        if not normalized:
            return _error(action, f"unsupported backend: {requested}")
        available = True
        fallback_reason = None
        backend = normalized
        try:
            create_input(normalized)
        except Exception as exc:  # noqa: BLE001
            available = False
            backend = "mock"
            fallback_reason = f"{type(exc).__name__}: {exc}"
        result = contracts.input_backend_contract(requested, backend, available, fallback_reason)
        payload = {"ok": available, "action": action, "result": result}
        if fallback_reason:
            payload["error"] = fallback_reason
        return payload

    if action == "route_plan":
        points = params.get("points")
        start = params.get("start") if isinstance(params.get("start"), dict) else {}
        if isinstance(points, list) and points:
            result = contracts.route_from_points(points, start)
        else:
            plan = services.plan_route(
                start,
                [str(item) for item in (params.get("labels") or [])],
                [str(item) for item in (params.get("categories") or [])],
                _int_param(params.get("limit"), 20),
                bool(params.get("roundtrip", False)),
            )
            result = contracts.route_contract(plan.get("route"), plan.get("distancePx"))
            result["estimated_minutes"] = plan.get("estimatedMinutes")
        result["start"] = start
        return {"ok": True, "action": action, "result": result}

    if action == "map_points":
        mark_type = params.get("mark_type")
        labels = {str(value) for value in (params.get("labels") or [])}
        categories = {str(value) for value in (params.get("categories") or [])}
        bounds = params.get("bounds") if isinstance(params.get("bounds"), dict) else None
        selected: List[Dict[str, Any]] = []
        for point in services.map.points:
            if mark_type is not None and str(point.get("markType")) != str(mark_type):
                continue
            if labels and point.get("label") not in labels:
                continue
            if categories and point.get("category") not in categories:
                continue
            if bounds:
                left = float(bounds.get("x") or 0)
                top = float(bounds.get("y") or 0)
                right = left + float(bounds.get("w") or 0)
                bottom = top + float(bounds.get("h") or 0)
                px = float(point.get("x") or 0)
                py = float(point.get("y") or 0)
                if not (left <= px <= right and top <= py <= bottom):
                    continue
            selected.append(point)
        total = len(selected)
        limit = _int_param(params.get("limit"), 0)
        if limit > 0:
            selected = selected[:limit]
        return {"ok": True, "action": action, "result": contracts.points_contract(selected, total)}

    if action == "turn_state":
        frame = services.capture(settings)
        state = read_turn_state(frame, settings)
        result = contracts.turn_contract(state)
        result["frame"] = frame.summary()
        return {"ok": bool(state.get("ok", True)), "action": action, "result": result}

    if action == "vendor_status":
        return _vendor(action, "status")

    if action == "vendor_action":
        requested = str(params.get("action") or "")
        if requested not in _VENDOR_ACTIONS:
            return _error(action, f"unknown vendor action: {requested}")
        return _vendor(action, requested)

    if action == "vendor_blocked":
        return _vendor(action, "blocked")

    return None


def _vendor(action: str, vendor_action: str) -> Dict[str, Any]:
    try:
        raw = engine_vendor.run_action(vendor_action)
    except Exception as exc:  # noqa: BLE001
        return _error(action, f"{type(exc).__name__}: {exc}")
    return {
        "ok": bool(raw.get("ok", True)),
        "action": action,
        "result": contracts.vendor_contract(raw, vendor_action),
    }
