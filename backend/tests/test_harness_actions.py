from __future__ import annotations

from types import SimpleNamespace

from app import harness, harness_actions
from app.harness_contracts import ACTION_OUTPUT_FIELDS, ACTION_REQUIRED_FIELDS


class _Frame:
    image = None

    def summary(self):
        return {"width": 8, "height": 8, "source": "stub"}


class _Map:
    points = [
        {"id": "p1", "x": 10, "y": 20, "markType": 1, "label": "宝箱", "category": "chest"},
    ]


class _Services:
    map = _Map()

    def capture(self, settings):
        return _Frame()

    def match_template(self, frame, template, threshold=0.8, roi="full"):
        return {
            "ok": True,
            "matched": True,
            "score": 0.91234,
            "x": 10,
            "y": 20,
            "w": 30,
            "h": 40,
            "cx": 25,
            "cy": 40,
            "template": template,
            "roi": roi,
        }

    def plan_route(self, start, labels, categories, limit, roundtrip):
        return {
            "route": [{"id": "p1", "x": 10, "y": 20}],
            "distancePx": 12.34,
            "estimatedMinutes": 1,
        }


class _Db:
    def get_setting(self, scope, default=None):
        return {}


def _app():
    return SimpleNamespace(
        state=SimpleNamespace(
            services=_Services(),
            db=_Db(),
            runs=SimpleNamespace(),
            realtime=SimpleNamespace(),
            tracker=SimpleNamespace(),
        )
    )


_PARAMS = {
    "match_template": {"template": "yes.png"},
    "detect_sprites": {},
    "ocr": {"roi": [0, 0, 1, 1]},
    "foreground": {},
    "set_input_backend": {"backend": "mock"},
    "route_plan": {"points": [{"x": 0, "y": 0}]},
    "map_points": {},
    "turn_state": {},
    "vendor_status": {},
    "vendor_action": {"action": "rocopilot"},
    "vendor_blocked": {},
}


def _stub_actions(monkeypatch):
    monkeypatch.setattr(
        harness_actions,
        "ensure_foreground",
        lambda title, hwnd: {
            "ok": True,
            "supported": True,
            "hwnd": hwnd,
            "restored": False,
            "foreground": None,
            "reason": None,
        },
    )
    monkeypatch.setattr(harness_actions, "create_input", lambda backend: SimpleNamespace(backend=backend))
    monkeypatch.setattr(
        harness_actions.detector,
        "detect_sprites",
        lambda *args, **kwargs: {
            "sprites": [{"x": 1, "y": 2, "w": 3, "h": 4, "cx": 2, "cy": 4, "score": 0.8, "label": "sprite"}],
            "source": "stub",
            "roi": kwargs.get("roi"),
            "model": None,
        },
    )
    monkeypatch.setattr(
        harness_actions.ocr,
        "read_text",
        lambda *args, **kwargs: {
            "text": "12",
            "confidence": 0.9,
            "chars": [],
            "source": "stub",
            "roi": [0, 0, 1, 1],
        },
    )
    monkeypatch.setattr(
        harness_actions,
        "read_turn_state",
        lambda frame, settings: {
            "ok": True,
            "phase": "battle",
            "scene": "battle_normal",
            "polluted": False,
            "turn": 1,
            "enemy": {"hpPercent": 50},
            "skills": [],
            "ocr": {},
            "rois": {},
        },
    )
    monkeypatch.setattr(
        harness_actions.engine_vendor,
        "run_action",
        lambda action: {
            "ok": True,
            "status": "ok",
            "checks": [],
            "blockers": [],
            "seconds": 0.1,
            "components": [],
            "adapters": {"rocopilot": {"status": "adapted", "blockers": []}},
            "adapted": 1,
        },
    )


def test_every_contract_action_is_dispatched(monkeypatch):
    _stub_actions(monkeypatch)
    settings = {"target": {}, "vision": {}}
    for action in harness_actions.ACTIONS:
        result = harness_actions.dispatch(_Services(), settings, action, _PARAMS[action])
        assert result is not None, action
        assert result["action"] == action


def test_unknown_action_still_falls_through():
    assert harness_actions.dispatch(_Services(), {}, "not_a_contract_action", {}) is None


def test_tools_schema_exposes_every_contract_action():
    tools = {item["function"]["name"]: item["function"] for item in harness.tools_schema()}
    assert len(tools) == len(harness.tools_schema())
    for action in harness_actions.ACTIONS:
        assert "rocogi_" + action in tools


def test_schema_required_fields_match_contracts():
    assert set(ACTION_REQUIRED_FIELDS) == set(harness_actions.ACTIONS)
    tools = {item["function"]["name"]: item["function"] for item in harness.tools_schema()}
    for action, required in ACTION_REQUIRED_FIELDS.items():
        params = tools["rocogi_" + action]["parameters"]
        assert tuple(params.get("required", ())) == tuple(required)


def test_execute_routes_contract_action_end_to_end():
    result = harness.execute(_app(), "rocogi_match_template", {"template": "yes.png"})
    assert result["ok"] is True
    assert result["action"] == "match_template"
    assert result["result"]["matched"] is True
    assert result["result"]["points"] == [
        {"x": 10, "y": 20, "w": 30, "h": 40, "cx": 25, "cy": 40, "score": 0.9123}
    ]


def test_execute_keeps_unknown_action_behaviour():
    result = harness.execute(_app(), "definitely_unknown", {})
    assert result["ok"] is False
    assert result["error"] == "unknown action: definitely_unknown"




def test_output_fields_match_dispatch(monkeypatch):
    _stub_actions(monkeypatch)
    settings = {"target": {}, "vision": {}}
    for action in harness_actions.ACTIONS:
        result = harness_actions.dispatch(_Services(), settings, action, _PARAMS[action])
        declared = set(ACTION_OUTPUT_FIELDS[action])
        assert declared <= set(result["result"]), action


def test_output_contract_covers_every_action():
    assert set(ACTION_OUTPUT_FIELDS) == set(harness_actions.ACTIONS)