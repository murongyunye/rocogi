from __future__ import annotations

from app import engine_battle, engine_core, engine_sense
from app.components import build_registry


def test_component_library_has_status_and_groups():
    registry = build_registry()
    component_ids = {
        component["id"]
        for engine in registry["engines"]
        for component in engine["components"]
    }
    group_ids = {
        component_id
        for group in registry["groups"]
        for component_id in group["components"]
    }
    assert group_ids == component_ids
    assert registry["stats"]["readyComponents"] + registry["stats"]["partialComponents"] == len(component_ids)
    assert registry["stats"]["gapCount"] == 0
    assert registry["gaps"] == []
    for engine in registry["engines"]:
        for component in engine["components"]:
            assert component["status"] in ("ready", "partial", "missing")


def test_battle_engine_actions():
    detail = engine_battle.dispatch("dex_detail", {"name": "迪莫"})
    assert detail["pokemon"]["name"] == "迪莫"
    analysis = engine_battle.dispatch("analyze", {"team": ["迪莫", "喵喵"]})
    assert analysis["metrics"]["count"] == 2


def test_sense_engine_templates():
    result = engine_sense.dispatch("templates", {})
    assert result["count"] >= 1
    assert "elf_P.png" in result["templates"]


def test_core_engine_library():
    result = engine_core.dispatch("library", {})
    assert result["stats"]["componentCount"] == 39
    assert len(result["groups"]) == 6
