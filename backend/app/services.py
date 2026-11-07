from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from .adapters import vision
from .adapters.battle import BattleLab
from .adapters.bwiki import BwikiData
from .adapters.frame import Frame
from .adapters.input import MockInput, create_input
from .adapters.mapdata import MapData
from .adapters.mock import MockGameTarget, WindowsGameTarget
from .adapters.position import MockPositionSource, SiftPositionSource
from .adapters.pvpdata import PvpData
from .config import load_settings


class Services:
    def __init__(self, db) -> None:
        self.db = db
        self.map = MapData()
        self.battle = BattleLab()
        self.bwiki = BwikiData()
        self.pvpdata = PvpData()
        self._lock = threading.RLock()
        self._mock_target: Optional[MockGameTarget] = None
        self._windows_target = None
        self._mock_input: Optional[MockInput] = None
        self._windows_input = None
        self._sift: Optional[SiftPositionSource] = None
        self._mock_position = MockPositionSource()

    # --------------------------------------------------------------- settings
    def settings(self) -> Dict[str, Any]:
        return load_settings(self.db)

    # --------------------------------------------------------------- targets
    def _target(self, settings: Dict[str, Any], force_capture: bool = True):
        kind = settings.get("target", {}).get("kind", "mock")
        if kind == "windows":
            if self._windows_target is None:
                self._windows_target = WindowsGameTarget(settings.get("target", {}))
            return self._windows_target
        if self._mock_target is None:
            self._mock_target = MockGameTarget(settings.get("target", {}))
        return self._mock_target

    def capture(self, settings: Dict[str, Any], region: Any = None) -> Frame:
        target = self._target(settings)
        frame = target.capture()
        meta = dict(frame.meta or {})
        meta.setdefault("width", frame.width)
        meta.setdefault("height", frame.height)
        meta["capturedAt"] = frame.ts
        frame.meta = meta
        return frame

    def target_info(self, settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        settings = settings or self.settings()
        try:
            return self._target(settings).info()
        except Exception as exc:  # noqa: BLE001
            return {"kind": settings.get("target", {}).get("kind"), "error": str(exc)}

    def set_scene(self, scene: str) -> None:
        with self._lock:
            if self._mock_target is None:
                self._mock_target = MockGameTarget(self.settings().get("target", {}))
            self._mock_target.set_scene(scene)

    # --------------------------------------------------------------- input
    def _input(self, settings: Dict[str, Any]):
        backend = settings.get("input", {}).get("backend", "mock")
        if backend == "windows":
            if self._windows_input is None:
                self._windows_input = create_input("windows")
            return self._windows_input
        if backend == "interception":
            if self._windows_input is None:
                self._windows_input = create_input("interception")
            return self._windows_input
        if self._mock_input is None:
            self._mock_input = MockInput()
        return self._mock_input

    def act(self, settings: Dict[str, Any], action: str, **kwargs) -> None:
        target_settings = settings.get("target", {})
        if target_settings.get("kind") == "windows" and target_settings.get("force_foreground", False):
            try:
                from .adapters.window import ensure_foreground

                ensure_foreground(str(target_settings.get("window_title") or ""))
            except Exception:
                pass
        backend = self._input(settings)
        if action == "key":
            backend.key(kwargs.get("key", "x"), kwargs.get("presses", 1), kwargs.get("interval", 0.08))
        elif action == "click":
            x = kwargs.get("x", 0)
            y = kwargs.get("y", 0)
            target = self._target(settings)
            if hasattr(target, "client_to_screen"):
                x, y = target.client_to_screen(int(x), int(y))
            backend.click(x, y, kwargs.get("button", "left"))
        elif action == "move":
            backend.move(kwargs.get("dx", 0), kwargs.get("dy", 0))
        else:
            raise ValueError(f"未知输入动作: {action}")

    def recent_actions(self, limit: int = 20) -> List[Dict[str, Any]]:
        if self._mock_input is None:
            return []
        return self._mock_input.recent(limit)

    # --------------------------------------------------------------- vision
    def match_template(
        self,
        frame: Frame,
        template: str,
        threshold: float = 0.5,
        roi: Any = "full",
        use_edges: bool = True,
        scale: float = 1.0,
    ) -> Dict[str, Any]:
        return vision.match_template(frame, template, threshold, roi, use_edges, scale)

    def classify_scene(self, frame: Frame, threshold: float = 0.5, use_edges: bool = True) -> Dict[str, Any]:
        return vision.classify_scene(frame, threshold, use_edges)

    # --------------------------------------------------------------- position
    def _position_source(self, settings: Dict[str, Any]):
        if settings.get("map", {}).get("position_source", "mock") == "sift":
            if self._sift is None:
                self._sift = SiftPositionSource(settings.get("map", {}))
            return self._sift
        return self._mock_position

    def position_for_frame(self, frame: Frame, current: Dict[str, Any] | None = None) -> Dict[str, Any]:
        settings = self.settings()
        source = self._position_source(settings)
        try:
            position = source.locate(frame, self.map)
        except Exception as exc:  # noqa: BLE001
            position = None
            if current:
                current = dict(current)
                current["error"] = str(exc)
        if position:
            return position
        return current or {}

    def plan_route(self, start: Dict[str, Any], labels: List[str], categories: List[str], limit: int, roundtrip: bool) -> Dict[str, Any]:
        return self.map.plan_route(start, labels, categories, limit, roundtrip)

    # --------------------------------------------------------------- battle
    def battle_decide(self, simulations: int = 60) -> Dict[str, Any]:
        return self.battle.decide(simulations)

    def battle_simulate(self, player_team, ai_team: str, simulations: int, max_turns: int) -> Dict[str, Any]:
        return self.battle.simulate(player_team, ai_team, simulations, max_turns)
