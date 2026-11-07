from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import cv2
import numpy as np

from ..config import DATA_DIR, RUNTIME_DIR
from .frame import Frame
from .mapdata import MAP_HEIGHT, MAP_WIDTH, MapData
from .vision import resolve_roi


class MockPositionSource:
    name = "mock"

    def locate(self, frame: Frame, map_data: MapData) -> Optional[Dict[str, Any]]:
        position = (frame.meta or {}).get("position")
        if not position:
            return None
        latlng = map_data.pixel_to_latlng(position["x"], position["y"])
        return {
            "source": "mock",
            "x": float(position["x"]),
            "y": float(position["y"]),
            "confidence": 1.0,
            **latlng,
        }


class SiftPositionSource:
    """SIFT minimap localization (no game memory reads)."""

    name = "sift"

    def __init__(self, settings: Dict[str, Any]) -> None:
        self.settings = settings
        self.max_edge = int(settings.get("sift_max_edge", 1600) or 1600)
        self.region = settings.get("minimap_region") or [0.84, 0.0275, 0.1172, 0.1875]
        self._matcher = cv2.BFMatcher(cv2.NORM_L2)
        self._keypoints: Optional[np.ndarray] = None
        self._descriptors: Optional[np.ndarray] = None
        self._map_scale = (1.0, 1.0)
        self._sift = cv2.SIFT_create(nfeatures=6000)
        self._cache_path = RUNTIME_DIR / "cache" / f"sift_anchors_{self.max_edge}.npz"
        self._load_map()

    def _load_map(self) -> None:
        base_path = DATA_DIR / "map" / "base_map.jpg"
        image = cv2.imread(str(base_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            return
        h, w = image.shape
        scale = self.max_edge / max(h, w)
        if scale < 1.0:
            image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        self._map_shape = image.shape
        self._map_scale = (MAP_WIDTH / image.shape[1], MAP_HEIGHT / image.shape[0])
        if self.settings.get("cache_anchors", True) and self._cache_path.exists():
            cached = np.load(self._cache_path)
            if cached["descriptors"].shape[0] > 100:
                self._keypoints = cached["points"]
                self._descriptors = cached["descriptors"]
                return
        keypoints, descriptors = self._sift.detectAndCompute(image, None)
        if descriptors is None:
            return
        self._keypoints = np.array([kp.pt for kp in keypoints], dtype=np.float32)
        self._descriptors = descriptors
        if self.settings.get("cache_anchors", True):
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(self._cache_path, points=self._keypoints, descriptors=self._descriptors)

    def locate(self, frame: Frame, map_data: MapData) -> Optional[Dict[str, Any]]:
        if self._keypoints is None or self._descriptors is None:
            return None
        x, y, w, h = resolve_roi(frame, self.region)
        crop = frame.image[y : y + h, x : x + w]
        if crop.size == 0 or min(crop.shape[:2]) < 40:
            return None
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        mask = np.zeros(gray.shape, dtype=np.uint8)
        cv2.ellipse(
            mask,
            (gray.shape[1] // 2, gray.shape[0] // 2),
            (int(gray.shape[1] * 0.47), int(gray.shape[0] * 0.47)),
            0, 0, 360, 255, -1,
        )
        kp, desc = self._sift.detectAndCompute(gray, mask)
        if desc is None or len(kp) < 8:
            return None
        matches = self._matcher.knnMatch(desc, self._descriptors, k=2)
        good = []
        for pair in matches:
            if len(pair) < 2:
                continue
            best, second = pair[0], pair[1]
            if best.distance < 0.76 * second.distance:
                good.append(best)
        if len(good) < 10:
            return None
        src = np.float32([kp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst = self._keypoints[[m.trainIdx for m in good]].reshape(-1, 1, 2)
        homography, inliers = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
        if homography is None or inliers is None:
            return None
        inlier_count = int(inliers.sum())
        if inlier_count < 8:
            return None
        center = np.float32([[[gray.shape[1] / 2, gray.shape[0] / 2]]])
        projected = cv2.perspectiveTransform(center, homography)[0][0]
        full_x = float(projected[0] * self._map_scale[0])
        full_y = float(projected[1] * self._map_scale[1])
        if not (0 <= full_x <= MAP_WIDTH and 0 <= full_y <= MAP_HEIGHT):
            return None
        latlng = map_data.pixel_to_latlng(full_x, full_y)
        return {
            "source": "sift",
            "x": round(full_x, 1),
            "y": round(full_y, 1),
            "confidence": round(inlier_count / max(len(good), 1), 3),
            "inliers": inlier_count,
            "matches": len(good),
            **latlng,
        }


def create_position_source(settings: Dict[str, Any]):
    if settings.get("position_source") == "sift":
        return SiftPositionSource(settings)
    return MockPositionSource()
