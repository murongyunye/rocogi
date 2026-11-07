from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from app import harness, harness_actions, harness_contracts

_SETTINGS = {"target": {}, "vision": {}, "engine": {"preset": "demo"}}


class _Frame:
    def __init__(self):
        self.image = np.zeros((8, 8, 3), dtype=np.uint8)

    def summary(self):
        return {"width": 8, "height": 8, "source": "stub"}


class _Services:
    def __init__(self):
        self.actions = []
        self.battle = SimpleNamespace()
        self.map = SimpleNamespace(points=[])

    def capture(self, settings, region=None):
        return _Frame()

    def classify_scene(self, frame, threshold=0.5, use_edges=True):
        return {"kind": "field", "scores": {}, "details": {}}

    def position_for_frame(self, frame, current=None):
        return {"x": 1, "y": 2, "source": "stub"}

    def act(self, settings, action, **kwargs):
        self.actions.append((action, kwargs))

    def target_info(self, settings=None):
        return {"kind": "stub"}

    def battle_decide(self, simulations=60):
        return {
            "ok": True,
            "action": "x",
            "label": "聚能",
            "active": "迪莫",
            "enemy": "喵喵",
            "turn": 1,
        }

    def battle_simulate(self, player_team, ai_team, simulations, max_turns):
        return {
            "ok": True,
            "winner": "a",
            "turns": 2,
            "durationMs": 5,
            "teamA": [],
            "teamB": [],
            "logs": [],
            "records": [],
        }


class _Session:
    def __init__(self):
        self.config = {}

    def start(self, config=None):
        self.config = config or {}
        return self.status()

    def stop(self):
        return self.status()

    def status(self):
        return {
            "running": False,
            "status": "idle",
            "error": "",
            "scene": None,
            "anchor": None,
            "config": dict(self.config),
        }


class _Runs:
    def start(self, workflow, trigger="harness"):
        return {"id": "run-1", "workflowId": workflow["id"], "status": "running"}

    def stop(self, run_id):
        return True

    def active_count(self):
        return 0


class _Db:
    def get_setting(self, scope, default=None):
        return {}

    def list_workflows(self):
        return [{"id": "wf-1", "name": "抓宠"}]

    def get_workflow(self, workflow_id):
        return {"id": workflow_id, "name": "抓宠"}

    def list_runs(self, limit=1):
        return [{"id": "run-1"}]

    def get_run(self, run_id):
        return {"id": run_id, "status": "running"}

    def get_events(self, run_id):
        return [{"message": "started"}]


def _app():
    return SimpleNamespace(
        state=SimpleNamespace(
            services=_Services(),
            db=_Db(),
            runs=_Runs(),
            realtime=_Session(),
            tracker=_Session(),
        )
    )


_PARAMS = {
    "get_state": {},
    "dex_lookup": {"name": "迪莫"},
    "pvp_analyze": {"team": ["迪莫"]},
    "pvp_matchup": {"team": ["迪莫"]},
    "observe": {},
    "capture": {},
    "press_key": {"key": "x"},
    "click": {"x": 1, "y": 2},
    "move": {"dx": 3, "dy": 4},
    "locate": {},
    "start_realtime": {},
    "stop_realtime": {},
    "start_tracker": {},
    "stop_tracker": {},
    "list_workflows": {},
    "run_workflow": {"workflowId": "wf-1"},
    "run_onedragon": {},
    "run_status": {},
    "stop_run": {"runId": "run-1"},
    "battle_decision": {},
    "battle_simulate": {},
    "sequence": {"actions": [{"action": "observe"}]},
}


def _stub(monkeypatch):
    monkeypatch.setattr(harness, "load_settings", lambda db: dict(_SETTINGS))
    monkeypatch.setattr(
        harness, "_save", lambda image, label="latest": "/api/harness/artifact?label=" + label
    )
    monkeypatch.setattr(
        "app.adapters.vision.annotate_matches",
        lambda frame, details: frame.image.copy(),
    )
    monkeypatch.setattr(
        harness.dex,
        "pokemon_detail",
        lambda name: {
            "pokemon": {"name": name},
            "skills": [],
            "evolution": [],
            "related": [],
        },
    )
    monkeypatch.setattr(
        harness.dex,
        "pokemon_list",
        lambda query, element="", limit=24, **kwargs: {
            "total": 0,
            "limit": limit,
            "offset": 0,
            "items": [],
        },
    )
    monkeypatch.setattr(
        harness.dex,
        "skill_list",
        lambda query, element="", limit=40, **kwargs: {
            "total": 0,
            "limit": limit,
            "offset": 0,
            "items": [],
        },
    )
    monkeypatch.setattr(
        harness.pvp,
        "analyze",
        lambda names: {
            "ok": True,
            "members": [],
            "metrics": {},
            "roles": {},
            "notes": [],
        },
    )
    monkeypatch.setattr(
        harness.pvp,
        "matchup",
        lambda battle, names, opponent="wing", simulations=60, max_turns=30: {
            "ok": True,
            "player": {},
            "opponent": opponent,
            "enemy": {},
            "battle": {},
            "winner": "a",
            "turns": 1,
            "durationMs": 1,
            "logs": [],
        },
    )
    monkeypatch.setattr(harness, "load_plan", lambda db: {"tasks": []})


def _runtime_actions():
    tools = {
        item["function"]["name"][len("rocogi_"):]
        for item in harness.tools_schema()
    }
    return tools - set(harness_actions.ACTIONS)


def test_every_runtime_action_dispatches_with_declared_outputs(monkeypatch):
    _stub(monkeypatch)
    assert _runtime_actions() == set(_PARAMS)
    for action, params in _PARAMS.items():
        payload = harness.execute(_app(), action, params)
        assert payload["ok"] is True, (action, payload)
        assert payload["action"] == action
        declared = set(harness_contracts.RUNTIME_OUTPUT_FIELDS[action])
        if declared:
            assert isinstance(payload["result"], dict), action
            assert declared <= set(payload["result"]), action


def test_runtime_metadata_covers_every_runtime_action():
    runtime = _runtime_actions()
    assert set(harness_contracts.RUNTIME_OUTPUT_FIELDS) == runtime
    assert runtime <= set(harness_contracts.ACTION_RISK)