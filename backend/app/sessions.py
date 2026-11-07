from __future__ import annotations

import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import cv2

from .adapters.position import SiftPositionSource
from .adapters.detector import detect_sprites
from .adapters.tracking import MultiTargetTracker, PositionSmoother
from .adapters.turn_state import read_turn_state
from .adapters.vision import annotate_matches
from .adapters.window import ensure_foreground
from .config import RUNTIME_DIR, load_settings

LIVE_DIR = RUNTIME_DIR / "live"
TRACKER_DIR = RUNTIME_DIR / "tracker"

DEFAULT_REALTIME = {
    "interval": 0.6,
    "auto_ball": True,
    "battle_response": True,
    "party_confirm": True,
    "normal_strategy": "gather",
    "polluted_strategy": "escape",
    "threshold": 0.45,
    "save_screenshots": True,
    "capture_retries": 3,
    "capture_verify": 1.2,
    "capture_pan": False,
    "capture_pan_steps": 6,
    "capture_pan_pixels": 90,
}

DEFAULT_TRACKER = {
    "interval": 0.5,
    "confidenceMin": 0.25,
    "screenshotEvery": 2,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _save_jpeg(image, path: Path, quality: int = 82) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])


class RealtimeSession:
    """Continuous detection + action loop, similar to BetterGI real-time triggers."""

    def __init__(self, services) -> None:
        self.services = services
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._config = dict(DEFAULT_REALTIME)
        self._logs: deque[Dict[str, Any]] = deque(maxlen=200)
        self._status = "idle"
        self._error = ""
        self._started_at: Optional[str] = None
        self._ticks = 0
        self._battles = 0
        self._balls = 0
        self._confirms = 0
        self._actions = 0
        self._scene = "unknown"
        self._scores: Dict[str, float] = {}
        self._phase = "idle"
        self._capture_attempts = 0
        self._empty_scans = 0
        self._pan_count = 0
        self._last_throw_at = 0.0
        self._latest_url: Optional[str] = None
        self._latest_ts = 0.0
        self._tracker = MultiTargetTracker()
        self._tracks: List[Dict[str, Any]] = []
        self._aim: Optional[Dict[str, Any]] = None
        self._turn_state: Optional[Dict[str, Any]] = None

    def config(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._config)

    def start(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return self.status()
            base = load_settings(self.services.db).get("realtime", {})
            self._config = {**DEFAULT_REALTIME, **base, **(config or {})}
            self._stop.clear()
            self._logs.clear()
            self._status = "starting"
            self._error = ""
            self._ticks = self._battles = self._balls = self._confirms = self._actions = 0
            self._phase = "scan"
            self._capture_attempts = 0
            self._empty_scans = 0
            self._pan_count = 0
            self._last_throw_at = 0.0
            self._started_at = _now()
            self._latest_url = None
            self._tracks = []
            self._aim = None
            self._turn_state = None
            self._tracker.reset()
            self._thread = threading.Thread(target=self._run, daemon=True, name="rocoflow-realtime")
            self._thread.start()
        return self.status()

    def stop(self) -> Dict[str, Any]:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=3)
        with self._lock:
            self._status = "idle"
        return self.status()

    def _log(self, kind: str, message: str, **extra) -> None:
        with self._lock:
            self._logs.append({"ts": _now(), "kind": kind, "message": message, **extra})

    def _run(self) -> None:
        with self._lock:
            self._status = "running"
        settings = self.services.settings()
        interval = max(0.15, float(self._config.get("interval", 0.6)))
        threshold = float(self._config.get("threshold", 0.45))
        retries = max(1, min(int(self._config.get("capture_retries", 3)), 10))
        verify_wait = max(0.3, float(self._config.get("capture_verify", 1.2)))
        pan_enabled = bool(self._config.get("capture_pan", False))
        pan_steps = max(1, min(int(self._config.get("capture_pan_steps", 6)), 20))
        pan_pixels = max(10, min(int(self._config.get("capture_pan_pixels", 90)), 600))
        target_settings = settings.get("target", {})
        if target_settings.get("kind") == "windows" and target_settings.get("force_foreground", False):
            ensure_foreground(str(target_settings.get("window_title") or ""))
        self._log("system", "实时任务已启动")
        while not self._stop.is_set():
            try:
                frame = self.services.capture(settings)
                scene = self.services.classify_scene(frame, threshold=threshold, use_edges=True)
                kind = scene["kind"]
                with self._lock:
                    self._scene = kind
                    self._scores = scene["scores"]
                    self._ticks += 1
                match_list = list(scene["details"].values())
                detected = detect_sprites(
                    frame.image,
                    settings.get("vision", {}),
                    threshold=max(0.3, threshold - 0.1),
                    max_items=8,
                )
                tracks = self._tracker.update(detected.get("sprites", []), interval)
                turn_state = read_turn_state(frame, settings) if kind in ("battle_normal", "battle_polluted") else None
                with self._lock:
                    self._tracks = tracks
                    confirmed = [track for track in tracks if track["status"] == "confirmed"]
                    self._aim = confirmed[0] if confirmed else (tracks[0] if tracks else None)
                    self._turn_state = turn_state
                match_list.extend(
                    {
                        "ok": True,
                        "template": f"track {track['id']}",
                        "score": track["score"],
                        "x": track["x"],
                        "y": track["y"],
                        "w": track["w"],
                        "h": track["h"],
                        "cx": track["cx"],
                        "cy": track["cy"],
                    }
                    for track in tracks
                )
                action = ""
                if kind in ("battle_normal", "battle_polluted") and self._config.get("battle_response", True):
                    strategy = (
                        self._config.get("polluted_strategy", "escape")
                        if kind == "battle_polluted"
                        else self._config.get("normal_strategy", "gather")
                    )
                    action = strategy
                    if strategy == "gather":
                        self.services.act(settings, "key", key="x")
                    elif strategy == "skill1_gather":
                        self.services.act(settings, "key", key="1")
                        self.services.act(settings, "key", key="x")
                    elif strategy == "escape":
                        self.services.act(settings, "key", key="esc")
                        yes = self.services.match_template(frame, "yes.png", threshold * 0.8, "center", True, 1.0)
                        if yes.get("matched"):
                            self.services.act(settings, "click", x=yes.get("cx", 0), y=yes.get("cy", 0))
                        match_list.append(yes)
                    with self._lock:
                        self._battles += 1
                        self._phase = "battle"
                        self._capture_attempts = 0
                        self._empty_scans = 0
                    self._log("battle", f"{'污染' if kind == 'battle_polluted' else '普通'}战斗 · {strategy}")
                    if turn_state and self._ticks % 4 == 0:
                        enemy = turn_state.get("enemy", {})
                        skill = next((item for item in turn_state.get("skills", []) if item.get("available")), None)
                        self._log(
                            "turn",
                            f"回合 {turn_state.get('turn') or '?'} · 敌方 HP {enemy.get('hpPercent', 0)}%"
                            f" · {'技能可用' if skill else '技能不可用'}",
                        )
                elif kind in ("field_pet",) and self._config.get("auto_ball", True):
                    now = time.monotonic()
                    with self._lock:
                        attempts = self._capture_attempts
                        last_throw = self._last_throw_at
                        self._empty_scans = 0
                        self._pan_count = 0
                    if attempts and now - last_throw < verify_wait:
                        with self._lock:
                            first_verify = self._phase != "verify"
                            self._phase = "verify"
                        action = "capture_verify"
                        if first_verify:
                            self._log("capture", f"等待捕捉结果 · 第 {attempts}/{retries} 次")
                    elif attempts >= retries:
                        with self._lock:
                            self._capture_attempts = 0
                            self._phase = "scan"
                        self._log("capture", f"达到最大丢球次数 {retries}，重新扫描")
                        action = "idle"
                    else:
                        ball = self.services.match_template(frame, "elf_P.png", threshold, "center", True, 1.0)
                        exchange = self.services.match_template(frame, "exchange.png", threshold, "center", True, 1.0)
                        match_list.extend([ball, exchange])
                        best = max([ball, exchange], key=lambda item: item.get("score", 0.0))
                        if best.get("matched"):
                            self.services.act(settings, "key", key="x")
                            action = "auto_ball"
                            with self._lock:
                                self._capture_attempts = attempts + 1
                                self._last_throw_at = now
                                self._phase = "throw"
                                self._balls += 1
                            self._log(
                                "ball",
                                f"自动丢球 {attempts + 1}/{retries} · 分数 {best.get('score', 0):.3f}",
                            )
                        else:
                            with self._lock:
                                self._phase = "scan"
                            if self._aim:
                                action = "aim"
                                self._log(
                                    "capture",
                                    f"跟踪候选精灵 #{self._aim['id']} · 分数 {self._aim['score']:.3f}",
                                )
                            else:
                                action = "idle"
                elif kind == "party_confirm" and self._config.get("party_confirm", True):
                    confirm = self.services.match_template(frame, "qiudaidai.png", threshold, "center", True, 1.0)
                    match_list.append(confirm)
                    if confirm.get("matched"):
                        self.services.act(settings, "key", key="f")
                        action = "party_confirm"
                        with self._lock:
                            self._confirms += 1
                            self._phase = "confirm"
                            self._capture_attempts = 0
                        self._log("party", "检测到同行请求，已按 F 确认")
                else:
                    action = "idle"
                    with self._lock:
                        attempts = self._capture_attempts
                        last_throw = self._last_throw_at
                    if kind != "field":
                        with self._lock:
                            self._empty_scans = 0
                            self._pan_count = 0
                    if attempts and time.monotonic() - last_throw >= verify_wait:
                        with self._lock:
                            self._capture_attempts = 0
                            self._phase = "scan"
                        self._log("capture", "捕捉流程结束 · 场景已切换")
                    if kind == "field" and pan_enabled:
                        with self._lock:
                            empty = self._empty_scans + 1
                            self._empty_scans = empty
                            pans = self._pan_count
                        if empty >= 5 and pans < pan_steps:
                            self.services.act(settings, "move", dx=pan_pixels, dy=0)
                            action = "pan"
                            with self._lock:
                                self._pan_count += 1
                                self._empty_scans = 0
                                self._phase = "pan"
                            self._log("capture", f"视野搜索 · 旋转视角 {self._pan_count}/{pan_steps}")
                        else:
                            with self._lock:
                                self._phase = "scan"
                    else:
                        with self._lock:
                            self._phase = "scan"

                if action in ("gather", "skill1_gather", "escape", "auto_ball", "party_confirm", "pan", "aim"):
                    with self._lock:
                        self._actions += 1

                if self._config.get("save_screenshots", True):
                    annotated = annotate_matches(frame, match_list)
                    cv2.putText(
                        annotated,
                        kind,
                        (30, annotated.shape[0] - 36),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.1,
                        (12, 20, 30),
                        3,
                    )
                    cv2.putText(
                        annotated,
                        kind,
                        (30, annotated.shape[0] - 36),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.1,
                        (140, 240, 220),
                        2,
                    )
                    _save_jpeg(annotated, LIVE_DIR / "latest.jpg")
                    with self._lock:
                        self._latest_ts = time.time()
                        self._latest_url = f"/api/live/artifact?t={int(self._latest_ts * 1000)}"
            except Exception as exc:  # noqa: BLE001
                with self._lock:
                    self._error = str(exc)
                    self._status = "error"
                self._log("error", f"实时任务出错: {exc}")
                break
            self._stop.wait(interval)
        with self._lock:
            if self._status != "error":
                self._status = "idle"
        self._log("system", "实时任务已停止")

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": bool(self._thread and self._thread.is_alive()),
                "status": self._status,
                "error": self._error,
                "startedAt": self._started_at,
                "scene": self._scene,
                "phase": self._phase,
                "scores": self._scores,
                "tracks": list(self._tracks),
                "aim": self._aim,
                "turnState": self._turn_state,
                "config": dict(self._config),
                "capture": {
                    "attempts": self._capture_attempts,
                    "emptyScans": self._empty_scans,
                    "panCount": self._pan_count,
                },
                "counters": {
                    "ticks": self._ticks,
                    "actions": self._actions,
                    "battles": self._battles,
                    "balls": self._balls,
                    "confirms": self._confirms,
                },
                "latestUrl": self._latest_url,
                "logs": list(self._logs)[-40:],
            }


class TrackerSession:
    """Standalone SIFT minimap tracker exposed as the SIFT Map Tracker tool."""

    def __init__(self, services) -> None:
        self.services = services
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._config = dict(DEFAULT_TRACKER)
        self._status = "idle"
        self._error = ""
        self._source: Optional[SiftPositionSource] = None
        self._current: Optional[Dict[str, Any]] = None
        self._trail: deque[Dict[str, Any]] = deque(maxlen=400)
        self._logs: deque[Dict[str, Any]] = deque(maxlen=300)
        self._ticks = 0
        self._located = 0
        self._lost = 0
        self._latency = 0.0
        self._latest_url: Optional[str] = None
        self._started_at: Optional[str] = None
        self._rebuilding = False
        self._smoother = PositionSmoother()
        self._smoothing: Dict[str, Any] = {"enabled": True}

    def start(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return self.status()
            base = load_settings(self.services.db).get("tracker", {})
            self._config = {**DEFAULT_TRACKER, **base, **(config or {})}
            self._stop.clear()
            self._status = "building"
            self._error = ""
            self._ticks = self._located = self._lost = 0
            self._trail.clear()
            self._logs.clear()
            self._started_at = _now()
            self._latest_url = None
            self._smoother.reset()
            self._smoothing = {"enabled": True}
            self._thread = threading.Thread(target=self._run, daemon=True, name="rocoflow-tracker")
            self._thread.start()
        return self.status()

    def stop(self) -> Dict[str, Any]:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=3)
        with self._lock:
            self._status = "idle"
        return self.status()

    def rebuild_anchors(self) -> Dict[str, Any]:
        self.stop()
        with self._lock:
            self._rebuilding = True
            self._status = "rebuilding"
        cache = RUNTIME_DIR / "cache"
        for path in cache.glob("sift_anchors_*.npz"):
            try:
                path.unlink()
            except OSError:
                pass
        self._source = None
        self._smoother.reset()

        def worker():
            try:
                settings = load_settings(self.services.db).get("map", {})
                self._source = SiftPositionSource({**settings, "cache_anchors": True})
                self._log("system", "SIFT 锚点已重建")
                with self._lock:
                    self._status = "idle"
            except Exception as exc:  # noqa: BLE001
                with self._lock:
                    self._error = str(exc)
                    self._status = "error"
                self._log("error", f"锚点重建失败: {exc}")
            finally:
                with self._lock:
                    self._rebuilding = False

        threading.Thread(target=worker, daemon=True, name="rocoflow-sift-rebuild").start()
        return {"ok": True, "status": "rebuilding"}

    def _log(self, kind: str, message: str, **extra) -> None:
        with self._lock:
            self._logs.append({"ts": _now(), "kind": kind, "message": message, **extra})

    def _run(self) -> None:
        settings = load_settings(self.services.db)
        map_settings = dict(settings.get("map", {}))
        interval = max(0.2, float(self._config.get("interval", 0.5)))
        try:
            with self._lock:
                self._status = "building"
            if self._source is None:
                self._source = SiftPositionSource({**map_settings, "cache_anchors": True})
            self._log("system", "SIFT 锚点加载完成，开始追踪")
            with self._lock:
                self._status = "running"
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self._status = "error"
                self._error = str(exc)
            self._log("error", f"追踪初始化失败: {exc}")
            return
        screenshot_every = max(1, int(self._config.get("screenshotEvery", 2)))
        confidence_min = float(self._config.get("confidenceMin", 0.25))
        while not self._stop.is_set():
            try:
                started = time.perf_counter()
                frame = self.services.capture(settings)
                result = self._source.locate(frame, self.services.map)
                latency = time.perf_counter() - started
                with self._lock:
                    self._ticks += 1
                    self._latency = round(latency * 1000, 1)
                if result:
                    smoothed = self._smoother.update(result["x"], result["y"], interval)
                    merged = {
                        **result,
                        "x": round(smoothed["x"], 1),
                        "y": round(smoothed["y"], 1),
                        "rawX": round(smoothed.get("rawX", result["x"]), 1),
                        "rawY": round(smoothed.get("rawY", result["y"]), 1),
                        "velocity": {
                            "x": round(smoothed.get("vx", 0.0), 2),
                            "y": round(smoothed.get("vy", 0.0), 2),
                        },
                        "jump": bool(smoothed.get("jump")),
                    }
                    with self._lock:
                        self._located += 1
                        self._current = merged
                        self._smoothing = {"enabled": True, **smoothed}
                        self._trail.append(
                            {
                                "x": merged["x"],
                                "y": merged["y"],
                                "lat": merged.get("lat"),
                                "lng": merged.get("lng"),
                                "confidence": merged.get("confidence"),
                                "ts": _now(),
                            }
                        )
                    if result.get("confidence", 0) < confidence_min:
                        self._log("warn", f"定位置信度偏低 · {result.get('confidence')}")
                    if merged.get("jump"):
                        self._log("warn", "定位跳变过大，已重置卡尔曼滤波")
                    if self._ticks % 10 == 0:
                        self._log(
                            "locate",
                            f"定位 ({round(merged['x'])}, {round(merged['y'])}) · 置信度 {merged.get('confidence')} · {round(latency * 1000)} ms",
                        )
                else:
                    predicted = self._smoother.predict(interval)
                    with self._lock:
                        self._lost += 1
                        if predicted:
                            self._smoothing = {"enabled": True, "predicted": {"x": round(predicted[0], 1), "y": round(predicted[1], 1)}}
                    self._log("lost", "本帧未定位到小地图位置")
                if self._config.get("screenshotEvery", 2) and self._ticks % screenshot_every == 0:
                    region = map_settings.get("minimap_region") or [0.84, 0.0275, 0.1172, 0.1875]
                    x = int(region[0] * frame.width)
                    y = int(region[1] * frame.height)
                    w = int(region[2] * frame.width)
                    h = int(region[3] * frame.height)
                    crop = frame.image[max(0, y) : y + h, max(0, x) : x + w]
                    if crop.size:
                        crop = cv2.resize(crop, (max(200, crop.shape[1] * 2), max(200, crop.shape[0] * 2)))
                        _save_jpeg(crop, TRACKER_DIR / "latest.jpg")
                        with self._lock:
                            self._latest_url = f"/api/tracker/artifact?t={int(time.time() * 1000)}"
            except Exception as exc:  # noqa: BLE001
                with self._lock:
                    self._status = "error"
                    self._error = str(exc)
                self._log("error", f"追踪出错: {exc}")
                break
            self._stop.wait(interval)
        with self._lock:
            if self._status != "error":
                self._status = "idle"
        self._log("system", "地图追踪已停止")

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": bool(self._thread and self._thread.is_alive()),
                "status": self._status,
                "error": self._error,
                "rebuilding": self._rebuilding,
                "config": dict(self._config),
                "current": self._current,
                "trail": list(self._trail),
                "smoothing": dict(self._smoothing),
                "stats": {
                    "ticks": self._ticks,
                    "located": self._located,
                    "lost": self._lost,
                    "latencyMs": self._latency,
                },
                "latestUrl": self._latest_url,
                "logs": list(self._logs)[-50:],
                "startedAt": self._started_at,
                "anchor": {
                    "maxEdge": self._source.max_edge if self._source else None,
                    "cached": bool(self._source and self._source._keypoints is not None),
                    "points": int(len(self._source._keypoints)) if self._source and self._source._keypoints is not None else 0,
                },
            }
