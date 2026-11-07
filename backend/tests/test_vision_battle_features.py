from __future__ import annotations

import os

import cv2
import pytest

from app import engine_battle, engine_input, engine_sense
from app.adapters.detector import detect_sprites
from app.adapters.mock import MockGameTarget
from app.adapters.ocr import read_text
from app.adapters.tracking import MultiTargetTracker, PositionSmoother
from app.adapters.turn_state import read_turn_state
from app.adapters.window import ensure_foreground
from app.config import DEFAULT_SETTINGS
from app.hotkeys import HotkeyManager, parse_hotkey


def _frame(scene: str):
    target = MockGameTarget(DEFAULT_SETTINGS["target"])
    target.set_scene(scene)
    return target.capture()


def test_sprite_detector_finds_candidates():
    # 模拟场景里 field_pet 才有可捕捉精灵；field 是空视野（用于演示视角搜索）
    field = _frame("field_pet")
    battle = _frame("battle_normal")
    assert detect_sprites(field.image, {}).get("count", 0) >= 1
    assert detect_sprites(battle.image, {}).get("count", 0) >= 1


def test_ocr_reads_battle_turn_number():
    frame = _frame("battle_normal")
    result = read_text(frame.image, [0.03, 0.86, 0.25, 0.06])
    assert result["text"] == "3"
    assert result["confidence"] > 0.5


def test_turn_state_structured_hud():
    normal = read_turn_state(_frame("battle_normal"), DEFAULT_SETTINGS)
    polluted = read_turn_state(_frame("battle_polluted"), DEFAULT_SETTINGS)
    assert normal["phase"] == "battle"
    assert normal["polluted"] is False
    assert normal["turn"] == 3
    assert normal["enemy"]["hpPercent"] >= 80
    assert normal["skills"][0]["available"] is True
    assert polluted["polluted"] is True
    assert polluted["enemy"]["hpPercent"] <= 70
    field = read_turn_state(_frame("field"), DEFAULT_SETTINGS)
    assert field["phase"] == "not_battle"


def test_kalman_position_smoother_rejects_jump():
    smoother = PositionSmoother()
    first = smoother.update(100, 100)
    second = smoother.update(102, 101)
    jump = smoother.update(900, 900)
    assert first["x"] == 100
    assert 100 < second["x"] < 102
    assert jump["jump"] is True
    assert jump["x"] == 900


def test_multi_target_tracker_keeps_ids():
    tracker = MultiTargetTracker()
    first = tracker.update(
        [
            {"x": 10, "y": 10, "w": 50, "h": 50, "score": 0.8},
            {"x": 200, "y": 30, "w": 40, "h": 40, "score": 0.7},
        ]
    )
    assert {track["id"] for track in first} == {1, 2}
    second = tracker.update(
        [
            {"x": 12, "y": 11, "w": 50, "h": 50, "score": 0.9},
            {"x": 202, "y": 31, "w": 40, "h": 40, "score": 0.8},
        ]
    )
    assert {track["id"] for track in second} == {1, 2}
    assert all(track["status"] == "confirmed" for track in second)


@pytest.mark.skipif(os.name == "nt", reason="Windows 上窗口与热键是受支持能力")
def test_window_and_hotkey_fallbacks_on_non_windows():
    foreground = ensure_foreground("test")
    assert foreground["supported"] is False
    assert parse_hotkey("ctrl+shift+f9") == (6, 0x78)
    manager = HotkeyManager()
    started = manager.start({"start": "f9"}, lambda action: None)
    assert started["supported"] is False
    assert started["running"] is False
    manager.stop()


def test_new_engine_actions(tmp_path):
    frame = _frame("battle_normal")
    path = tmp_path / "battle.jpg"
    assert cv2.imwrite(str(path), frame.image)
    sprites = engine_sense.dispatch("sprites", {})
    assert sprites["count"] >= 1
    foreground = engine_sense.dispatch("foreground", {})
    assert "supported" in foreground
    hotkey = engine_input.dispatch("hotkey", {"bindings": {"start": "f9"}})
    assert hotkey["parsed"]["start"]["key"] == 0x78
    state = engine_battle.dispatch("turn_state", {"image": str(path)})
    assert state["phase"] == "battle"
    assert state["turn"] == 3
    assert state["enemy"]["hpPercent"] >= 80
