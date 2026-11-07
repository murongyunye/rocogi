from __future__ import annotations

from app.harness_contracts import (
    foreground_contract,
    input_backend_contract,
    match_contract,
    ocr_contract,
    points_contract,
    route_contract,
    route_from_points,
    sprite_contract,
    turn_contract,
    vendor_contract,
)


def test_match_contract_only_reports_points_when_matched():
    result = match_contract(
        {
            "ok": True,
            "matched": True,
            "score": 0.91234,
            "x": 10,
            "y": 20,
            "w": 30,
            "h": 40,
            "cx": 25,
            "cy": 40,
            "roi": [0, 0, 100, 100],
            "template": "yes.png",
        }
    )
    assert result["matched"] is True
    assert result["score"] == 0.9123
    assert result["points"] == [{"x": 10, "y": 20, "w": 30, "h": 40, "cx": 25, "cy": 40, "score": 0.9123}]

    miss = match_contract({"ok": True, "matched": False, "score": 0.11})
    assert miss["points"] == []
    assert miss["score"] == 0.11


def test_sprite_contract_maps_bbox_and_filters_confidence():
    raw = {
        "count": 2,
        "source": "saliency",
        "roi": [0.28, 0.34, 0.44, 0.46],
        "model": None,
        "sprites": [
            {"x": 1, "y": 2, "w": 3, "h": 4, "cx": 2, "cy": 4, "score": 0.8, "label": "sprite"},
            {"x": 5, "y": 6, "w": 7, "h": 8, "cx": 8, "cy": 10, "score": 0.2, "label": "sprite"},
        ],
    }
    result = sprite_contract(raw, 0.4)
    assert result["count"] == 1
    assert result["candidates"][0]["bbox"] == {"x": 1, "y": 2, "w": 3, "h": 4}
    assert result["candidates"][0]["confidence"] == 0.8
    assert result["candidates"][0]["track_id"] is None
    assert len(result["sprites"]) == 2


def test_ocr_contract_derives_value_from_text():
    assert ocr_contract({"text": "45%", "confidence": 0.9}, "percentage")["value"] == 45.0
    assert ocr_contract({"text": "回合 12", "confidence": 0.9}, "number")["value"] == 12.0
    assert ocr_contract({"text": "没有数字", "confidence": 0.9}, "number")["value"] is None
    assert ocr_contract({"text": "45%", "confidence": 0.9}, "text")["value"] is None


def test_foreground_and_input_backend_contracts():
    foreground = foreground_contract(
        {"ok": True, "supported": True, "hwnd": 123, "restored": True, "foreground": 123}
    )
    assert foreground["focused"] is True
    assert foreground["hwnd"] == "123"
    assert foreground["supported"] is True

    degraded = input_backend_contract("sendinput", "mock", False, "WindowsInput 仅支持 Windows")
    assert degraded == {
        "requested": "sendinput",
        "backend": "mock",
        "available": False,
        "fallback_reason": "WindowsInput 仅支持 Windows",
    }


def test_route_helpers_report_pixel_distance():
    assert route_contract([{"x": 1}], 12.345) == {
        "route": [{"x": 1}],
        "total_distance": 12.3,
        "count": 1,
    }

    result = route_from_points([{"x": 3, "y": 4}, {"x": 0, "y": 0}], {"x": 0, "y": 0})
    assert [item["x"] for item in result["route"]] == [0, 3]
    assert [item["leg_distance"] for item in result["route"]] == [0.0, 5.0]
    assert result["total_distance"] == 5.0


def test_points_and_turn_contracts():
    assert points_contract([{"id": "a"}], 9) == {"points": [{"id": "a"}], "total": 9}

    state = {
        "ok": True,
        "phase": "battle",
        "scene": "battle_polluted",
        "polluted": True,
        "turn": 3,
        "enemy": {"hpRatio": 0.5, "hpPercent": 50},
        "skills": [{"slot": 1}],
        "ocr": {"turn": {"text": "3"}},
        "rois": {"turn": [0, 0, 1, 1]},
    }
    result = turn_contract(state)
    assert result["turn"] == 3
    assert result["enemyHp"] == 50
    assert result["polluted"] is True
    assert result["enemy"] == {"hpRatio": 0.5, "hpPercent": 50}


def test_vendor_status_keeps_adapter_object():
    raw = {
        "adapted": 1,
        "resolved": 2,
        "partial": 0,
        "adapters": {"rocopilot": {"status": "adapted", "blockers": []}},
    }
    result = vendor_contract(raw, "status")
    assert result["adapters"] == {"rocopilot": {"status": "adapted", "blockers": []}}
    assert result["count"] == 1
    assert result["adapted"] == 1
    assert result["resolved"] == 2


def test_vendor_action_returns_adapter_json_flat():
    raw = {
        "ok": False,
        "returncode": 1,
        "action": "rocopilot",
        "status": "blocked",
        "checks": [{"name": "probe", "ok": False}],
        "blockers": ["missing dependency"],
        "seconds": 1.2,
        "components": ["vendor.rocopilot"],
    }
    result = vendor_contract(raw, "rocopilot")
    assert result["status"] == "blocked"
    assert result["blockers"] == ["missing dependency"]
    assert result["returncode"] == 1
    assert "ok" not in result
    assert "adapters" not in result
