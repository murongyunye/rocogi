from __future__ import annotations

import io
import json
import sys

import pytest

from app import (
    engine_battle,
    engine_cli,
    engine_core,
    engine_flow,
    engine_input,
    engine_sense,
    engine_sift,
    pvp,
)
from app.adapters.battle import BattleLab
from app.components import COMPONENT_STATUS, ENGINE_GROUPS, _component_index


def test_status_map_covers_every_component():
    index = _component_index()
    assert set(COMPONENT_STATUS) == set(index)
    for status, _note in COMPONENT_STATUS.values():
        assert status in ("ready", "partial", "missing")


def test_group_actions_match_engine_modules():
    handlers = {
        "sense": engine_sense,
        "input": engine_input,
        "sift": engine_sift,
        "battle": engine_battle,
        "flow": engine_flow,
    }
    for group in ENGINE_GROUPS:
        if group["id"] == "core":
            continue
        assert list(handlers[group["id"]].ACTIONS) == list(group["actions"])


def test_input_engine_validates_actions():
    with pytest.raises(ValueError, match="params.key"):
        engine_input.dispatch("press", {"backend": "mock"})
    with pytest.raises(ValueError, match="未知按键"):
        engine_input.dispatch("press", {"key": "不存在的键", "backend": "mock"})
    with pytest.raises(ValueError, match="params.actions"):
        engine_input.dispatch("sequence", {"actions": {"a": 1}, "backend": "mock"})
    with pytest.raises(ValueError, match="元素必须是"):
        engine_input.dispatch("sequence", {"actions": ["press"], "backend": "mock"})


def test_cli_invalid_params_json_returns_structured_error(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["rocogi-engine", "--engine", "core", "--action", "groups", "--params", "{bad"],
    )
    code = engine_cli.main()
    assert code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is False
    assert output["engine"] == "core"


def test_cli_invalid_stdin_returns_structured_error(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["rocogi-engine", "--stdin"])
    monkeypatch.setattr(sys, "stdin", io.StringIO("[1, 2]"))
    code = engine_cli.main()
    assert code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is False
    assert "JSON object" in output["error"]


def test_cli_unknown_engine_returns_structured_error(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["rocogi-engine", "--stdin"])
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"engine": "sensor", "action": "groups"}'))
    code = engine_cli.main()
    assert code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is False
    assert "未知引擎" in output["error"]


def test_core_engine_ambiguous_action_requires_group_prefix():
    with pytest.raises(ValueError, match="group.action"):
        engine_core.dispatch("meta", {})
    result = engine_core.dispatch("sift.meta", {})
    assert result["group"] == "sift"
    result = engine_core.dispatch("battle.meta", {})
    assert result["group"] == "battle"


def test_battle_engine_rejects_non_list_team():
    with pytest.raises(ValueError, match="team 必须是精灵名数组"):
        engine_battle.dispatch("analyze", {"team": "迪莫"})


def test_pvp_team_validation():
    with pytest.raises(ValueError, match="阵容为空"):
        pvp.analyze([])
    with pytest.raises(ValueError, match="最多 6"):
        pvp.analyze(["迪莫"] * 7)
    with pytest.raises(ValueError, match="重复精灵"):
        pvp.analyze(["迪莫", "迪莫"])
    with pytest.raises(ValueError, match="图鉴中不存在"):
        pvp.analyze(["迪莫", "查无此精灵"])


def test_pvp_matchup_unknown_opponent_errors():
    with pytest.raises(ValueError, match="对手精灵不存在"):
        pvp.matchup(BattleLab(), ["迪莫"], opponent="查无此精灵", simulations=10, max_turns=4)


def test_battle_engine_accepts_string_team_and_rejects_oversize():
    result = engine_battle.dispatch(
        "simulate",
        {"playerTeam": ["迪莫", "喵喵"], "aiTeam": "wing", "simulations": 10, "maxTurns": 6},
    )
    assert result["ok"] is True, result.get("error")
    lab = BattleLab()
    oversize = lab.simulate([{"name": "迪莫"}] * 7, "wing", simulations=10, max_turns=4)
    assert oversize["ok"] is False
    assert "最多 6" in oversize["error"]
