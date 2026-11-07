from __future__ import annotations

"""Constant-velocity Kalman filter and IoU-based multi-target tracker.

Used by the SIFT tracker session for position smoothing and by the realtime
session for sprite candidates. Pure NumPy so it ships with the existing
runtime without extra dependencies.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

STATE_SIZE = 4


def _iou(a: Sequence[float], b: Sequence[float]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1 = max(ax, bx)
    y1 = max(ay, by)
    x2 = min(ax + aw, bx + bw)
    y2 = min(ay + ah, by + bh)
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = aw * ah + bw * bh - intersection
    return intersection / union if union > 0 else 0.0


class KalmanFilterCV:
    """Constant-velocity filter with state [x, y, vx, vy]."""

    def __init__(self, x: float, y: float, process: float = 0.08, measurement: float = 0.12) -> None:
        self.state = np.array([float(x), float(y), 0.0, 0.0], dtype=np.float64)
        self.transition = np.array(
            [[1.0, 0.0, 1.0, 0.0], [0.0, 1.0, 0.0, 1.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
        )
        self.observation = np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]])
        self.covariance = np.eye(STATE_SIZE) * 100.0
        self.process = np.eye(STATE_SIZE) * process
        self.measurement = np.eye(2) * measurement

    def predict(self, dt: float = 1.0) -> Tuple[float, float]:
        transition = np.array(
            [[1.0, 0.0, dt, 0.0], [0.0, 1.0, 0.0, dt], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
        )
        self.state = transition @ self.state
        self.covariance = transition @ self.covariance @ transition.T + self.process
        return float(self.state[0]), float(self.state[1])

    def update(self, x: float, y: float) -> Tuple[float, float]:
        measurement = np.array([[x], [y]], dtype=np.float64)
        residual = measurement - self.observation @ self.state.reshape(-1, 1)
        innovation = self.observation @ self.covariance @ self.observation.T + self.measurement
        gain = self.covariance @ self.observation.T @ np.linalg.inv(innovation)
        self.state = (self.state.reshape(-1, 1) + gain @ residual).flatten()
        self.covariance = (np.eye(STATE_SIZE) - gain @ self.observation) @ self.covariance
        return float(self.state[0]), float(self.state[1])

    @property
    def velocity(self) -> Tuple[float, float]:
        return float(self.state[2]), float(self.state[3])


class PositionSmoother:
    """Kalman smoothing for a single map position, with jump reset."""

    def __init__(self, process: float = 1.4, measurement: float = 8.0, max_jump: float = 420.0) -> None:
        self.process = process
        self.measurement = measurement
        self.max_jump = max_jump
        self._filter: Optional[KalmanFilterCV] = None

    def reset(self) -> None:
        self._filter = None

    def predict(self, dt: float = 1.0) -> Optional[Tuple[float, float]]:
        if self._filter is None:
            return None
        return self._filter.predict(max(0.05, dt))

    def update(self, x: float, y: float, dt: float = 1.0) -> Dict[str, Any]:
        if self._filter is None:
            self._filter = KalmanFilterCV(x, y, self.process, self.measurement)
            return {"x": float(x), "y": float(y), "rawX": float(x), "rawY": float(y), "jump": False}
        predicted_x, predicted_y = self._filter.predict(max(0.05, dt))
        jump = float(np.hypot(x - predicted_x, y - predicted_y)) > self.max_jump
        if jump:
            self._filter = KalmanFilterCV(x, y, self.process, self.measurement)
            return {"x": float(x), "y": float(y), "rawX": float(x), "rawY": float(y), "jump": True}
        smooth_x, smooth_y = self._filter.update(x, y)
        vx, vy = self._filter.velocity
        return {
            "x": smooth_x,
            "y": smooth_y,
            "rawX": float(x),
            "rawY": float(y),
            "vx": vx,
            "vy": vy,
            "jump": False,
        }


class Track:
    def __init__(self, box: Sequence[float], score: float, dt: float, track_id: int) -> None:
        self.id = track_id
        self.box = [float(value) for value in box]
        self.score = score
        self.filter = KalmanFilterCV(self.box[0] + self.box[2] / 2, self.box[1] + self.box[3] / 2, 0.5, 0.2)
        self.hits = 1
        self.missed = 0
        self.age = 0
        self.velocity = (0.0, 0.0)

    def predict(self, dt: float) -> None:
        cx, cy = self.filter.predict(dt)
        w = self.box[2]
        h = self.box[3]
        self.box = [cx - w / 2, cy - h / 2, w, h]

    def update(self, box: Sequence[float], score: float) -> None:
        self.box = [float(value) for value in box]
        self.filter.update(self.box[0] + self.box[2] / 2, self.box[1] + self.box[3] / 2)
        self.score = score
        self.hits += 1
        self.missed = 0
        self.velocity = self.filter.velocity


class MultiTargetTracker:
    """Greedy IoU association with tentative/confirmed/lost lifecycle."""

    def __init__(self, iou_threshold: float = 0.25, max_missed: int = 4, confirm_hits: int = 2) -> None:
        self.iou_threshold = iou_threshold
        self.max_missed = max_missed
        self.confirm_hits = confirm_hits
        self.tracks: List[Track] = []
        self._next_id = 1

    def reset(self) -> None:
        self.tracks = []
        self._next_id = 1

    def update(self, detections: List[Dict[str, Any]], dt: float = 1.0) -> List[Dict[str, Any]]:
        for track in self.tracks:
            track.predict(dt)
            track.age += 1
        candidates: List[Tuple[float, int, int]] = []
        for track_index, track in enumerate(self.tracks):
            for detection_index, detection in enumerate(detections):
                box = (detection["x"], detection["y"], detection["w"], detection["h"])
                score = _iou(track.box, box)
                if score >= self.iou_threshold:
                    candidates.append((score, track_index, detection_index))
        candidates.sort(reverse=True)
        used_tracks = set()
        used_detections = set()
        for _score, track_index, detection_index in candidates:
            if track_index in used_tracks or detection_index in used_detections:
                continue
            track = self.tracks[track_index]
            detection = detections[detection_index]
            track.update(
                (detection["x"], detection["y"], detection["w"], detection["h"]),
                float(detection.get("score", 0.0)),
            )
            used_tracks.add(track_index)
            used_detections.add(detection_index)
        for track_index, track in enumerate(self.tracks):
            if track_index not in used_tracks:
                track.missed += 1
        for detection_index, detection in enumerate(detections):
            if detection_index in used_detections:
                continue
            self.tracks.append(
                Track(
                    (detection["x"], detection["y"], detection["w"], detection["h"]),
                    float(detection.get("score", 0.0)),
                    dt,
                    self._next_id,
                )
            )
            self._next_id += 1
        self.tracks = [track for track in self.tracks if track.missed <= self.max_missed]
        return self.snapshot()

    def snapshot(self) -> List[Dict[str, Any]]:
        items = []
        for track in self.tracks:
            if track.hits < self.confirm_hits:
                status = "tentative"
            elif track.missed > 0:
                status = "lost"
            else:
                status = "confirmed"
            items.append(
                {
                    "id": track.id,
                    "status": status,
                    "x": int(track.box[0]),
                    "y": int(track.box[1]),
                    "w": int(track.box[2]),
                    "h": int(track.box[3]),
                    "cx": int(track.box[0] + track.box[2] / 2),
                    "cy": int(track.box[1] + track.box[3] / 2),
                    "score": round(float(track.score), 3),
                    "hits": track.hits,
                    "missed": track.missed,
                    "age": track.age,
                    "vx": round(float(track.velocity[0]), 2),
                    "vy": round(float(track.velocity[1]), 2),
                }
            )
        return items
