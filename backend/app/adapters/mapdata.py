from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from ..config import MAP_DIR

MAP_WIDTH = 6144
MAP_HEIGHT = 5888


class MapData:
    def __init__(self) -> None:
        self.points: List[Dict[str, Any]] = []
        self.marker_types: List[Dict[str, Any]] = []
        self.categories: List[Dict[str, Any]] = []
        self.labels: List[Dict[str, Any]] = []
        self._lng_slope = 0.000171763
        self._lng_intercept = -1.239386
        self._lat_slope = -0.000171857
        self._lat_intercept = 1.135431
        self._load()

    # ------------------------------------------------------------------ load
    def _load(self) -> None:
        raw: List[Dict[str, Any]] = []
        for filename in ("taptap.json", "easy_roco.json"):
            path = MAP_DIR / filename
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            for item in data:
                raw.append(
                    {
                        "id": str(item.get("id")),
                        "title": str(item.get("title") or ""),
                        "label": str(item.get("label") or "未分类"),
                        "category": str(item.get("category") or "其他"),
                        "markType": item.get("mark_type"),
                        "x": float(item.get("pixel_x") or 0),
                        "y": float(item.get("pixel_y") or 0),
                        "source": filename.replace(".json", ""),
                        "icon": f"icons/{item.get('mark_type')}.png",
                    }
                )

        # Deduplicate nearby points with the same label from both sources.
        seen = set()
        for point in raw:
            key = (round(point["x"] / 24), round(point["y"] / 24), point["label"])
            if key in seen:
                continue
            seen.add(key)
            self.points.append(point)

        marker_path = MAP_DIR / "marker_types.json"
        if marker_path.exists():
            self.marker_types = json.loads(marker_path.read_text(encoding="utf-8"))

        self._fit_projection()
        self._build_stats()

    def _fit_projection(self) -> None:
        easy_path = MAP_DIR / "easy_roco.json"
        if not easy_path.exists():
            return
        data = json.loads(easy_path.read_text(encoding="utf-8"))
        x = np.array([p["pixel_x"] for p in data], dtype=float)
        y = np.array([p["pixel_y"] for p in data], dtype=float)
        lng = np.array([p["lng"] for p in data], dtype=float)
        lat = np.array([p["lat"] for p in data], dtype=float)
        if len(x) > 8:
            self._lng_slope, self._lng_intercept = np.polyfit(x, lng, 1)
            self._lat_slope, self._lat_intercept = np.polyfit(y, lat, 1)

    def _build_stats(self) -> None:
        category_counts: Dict[str, int] = {}
        label_counts: Dict[str, int] = {}
        for point in self.points:
            category_counts[point["category"]] = category_counts.get(point["category"], 0) + 1
            label_counts[point["label"]] = label_counts.get(point["label"], 0) + 1
        palette = [
            "#5eead4", "#fbbf24", "#f472b6", "#60a5fa", "#34d399",
            "#a78bfa", "#fb923c", "#38bdf8", "#facc15", "#c084fc",
            "#4ade80", "#f87171", "#94a3b8", "#2dd4bf", "#e879f9",
        ]
        sorted_categories = sorted(category_counts.items(), key=lambda kv: -kv[1])
        self.categories = [
            {"id": key, "label": key, "count": count, "color": palette[index % len(palette)]}
            for index, (key, count) in enumerate(sorted_categories)
        ]
        self.labels = [
            {"id": key, "label": key, "count": count}
            for key, count in sorted(label_counts.items(), key=lambda kv: -kv[1])
        ]

    # ------------------------------------------------------------------ query
    def meta(self) -> Dict[str, Any]:
        return {
            "pointCount": len(self.points),
            "categoryCount": len(self.categories),
            "labelCount": len(self.labels),
            "categories": self.categories,
            "labels": self.labels[:80],
            "mapWidth": MAP_WIDTH,
            "mapHeight": MAP_HEIGHT,
            "baseMap": "/api/assets/map/base_map.jpg",
            "markerTypeCount": len(self.marker_types),
        }

    def pixel_to_latlng(self, x: float, y: float) -> Dict[str, float]:
        return {
            "lng": float(self._lng_slope * x + self._lng_intercept),
            "lat": float(self._lat_slope * y + self._lat_intercept),
        }

    def nearest(self, x: float, y: float, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        candidates = self.points
        if category:
            candidates = [p for p in candidates if p["category"] == category]
        if not candidates:
            return None
        return min(candidates, key=lambda p: (p["x"] - x) ** 2 + (p["y"] - y) ** 2)

    def plan_route(
        self,
        start: Dict[str, Any],
        labels: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        limit: int = 20,
        roundtrip: bool = False,
    ) -> Dict[str, Any]:
        sx, sy = float(start.get("x", 0)), float(start.get("y", 0))
        labels = [label for label in (labels or []) if label]
        categories = [category for category in (categories or []) if category]

        def allowed(point: Dict[str, Any]) -> bool:
            if labels and point["label"] not in labels:
                return False
            if categories and point["category"] not in categories:
                return False
            return True

        candidates = [point for point in self.points if allowed(point)]
        limit = max(1, min(int(limit), 200))
        if len(candidates) < limit:
            limit = len(candidates)

        route: List[Dict[str, Any]] = []
        current = (sx, sy)
        remaining = candidates[:]
        for _ in range(limit):
            if not remaining:
                break
            nearest_index = min(
                range(len(remaining)),
                key=lambda i: (remaining[i]["x"] - current[0]) ** 2 + (remaining[i]["y"] - current[1]) ** 2,
            )
            point = remaining.pop(nearest_index)
            route.append(point)
            current = (point["x"], point["y"])

        distance = 0.0
        prev = (sx, sy)
        for point in route:
            distance += math.hypot(point["x"] - prev[0], point["y"] - prev[1])
            prev = (point["x"], point["y"])
        if roundtrip and route:
            distance += math.hypot(route[-1]["x"] - sx, route[-1]["y"] - sy)
            route.append({"id": "return", "title": "返回起点", "label": "起点", "category": "路线",
                          "x": sx, "y": sy, "markType": 0, "source": "plan", "icon": ""})

        return {
            "start": {"x": sx, "y": sy},
            "route": [
                {
                    "id": p["id"],
                    "title": p.get("title") or p["label"],
                    "label": p["label"],
                    "category": p["category"],
                    "x": p["x"],
                    "y": p["y"],
                    "icon": p.get("icon", ""),
                }
                for p in route
            ],
            "count": len(route),
            "distancePx": round(distance, 1),
            "estimatedMinutes": max(1, round(distance / 14.0 / 60.0)),
            "labels": labels,
            "categories": categories,
        }
