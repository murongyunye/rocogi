from __future__ import annotations

import math

from app.adapters.battle import BattleLab
from app.adapters.mapdata import MapData
from app.adapters.mock import MockGameTarget
from app.adapters.position import SiftPositionSource
from app.adapters.vision import classify_scene, match_template


def test_map_data_and_route():
    map_data = MapData()
    meta = map_data.meta()
    assert meta["pointCount"] > 8000
    assert meta["categoryCount"] >= 10
    plan = map_data.plan_route({"x": 3072, "y": 2944}, labels=["宝箱"], limit=6)
    assert plan["count"] == 6
    assert plan["distancePx"] > 0
    assert len({point["id"] for point in plan["route"]}) == 6
    latlng = map_data.pixel_to_latlng(3072, 2944)
    assert -1.5 < latlng["lng"] < 0.5
    assert 0 < latlng["lat"] < 1.5


def test_mock_scene_classification():
    target = MockGameTarget({})
    expectations = {
        "field": "field",
        "field_pet": "field_pet",
        "battle_normal": "battle_normal",
        "battle_polluted": "battle_polluted",
        "party_confirm": "party_confirm",
    }
    for scene, expected in expectations.items():
        target.set_scene(scene)
        frame = target.capture()
        result = classify_scene(frame, threshold=0.5, use_edges=True)
        assert result["kind"] == expected, (scene, result)
    target.set_scene("battle_normal")
    match = match_template(target.capture(), "capture.png", 0.5, "top-right", True)
    assert match["matched"] and match["score"] > 0.85


def test_sift_localization():
    target = MockGameTarget({})
    frame = target.capture()
    map_data = MapData()
    source = SiftPositionSource({"sift_max_edge": 1200, "cache_anchors": False})
    result = source.locate(frame, map_data)
    assert result is not None
    truth = frame.meta["position"]
    distance = math.hypot(result["x"] - truth["x"], result["y"] - truth["y"])
    assert distance < 30, (result, truth)


def test_battle_simulation_repeated():
    lab = BattleLab()
    assert lab.simulate(None, "wing", simulations=10, max_turns=6)["ok"] is True
    custom = [{"name": "千棘盔"}, {"name": "影狸"}, {"name": "裘卡"}]
    result = lab.simulate(custom, "wing", simulations=10, max_turns=6)
    assert result["ok"] is True, result.get("error")
    assert result["logs"][0]["kind"] == "start"
    assert result["teamA"][0]["maxHp"] > 0
