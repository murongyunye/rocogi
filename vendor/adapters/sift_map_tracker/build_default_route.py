"""用 Wooziii-roco-map-tracker 的 route_planner 生成 sift 的 default_route.json。

背景：sift-map-tracker 发布物里 `routes/default_route.json` 缺失（上游即无），
service.exe 启动时读该文件失败（日志：Unable to activate route）。

做法（补位，不覆盖任何上游文件）：
  1. 取 Wooziii 的 `data/points.normalized.json`（2436 条，8192-map-space 像素坐标）；
  2. 选一类采集物（默认 mark_type 701），交给 route_planner.plan_route 做聚类 + 2-opt 排序；
  3. 按 sift 的 `format_version = sift0.6` 结构写出 points / nodes / edges。

坐标假设：Wooziii 与 sift 都用 8192×8192 地图像素坐标系，直接沿用 pixel_x / pixel_y，
与 legacy `SIFT-Map-Tracker-v0.10.1/routes/default_route.json` 的同区域坐标量级一致。
"""
import argparse
import json
import os
import sys
import uuid

VENDOR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WOOZIII = os.path.join(VENDOR, "Wooziii-roco-map-tracker", "roco-map-tracker")
POINTS = os.path.join(WOOZIII, "data", "points.normalized.json")
OUT_DEFAULT = os.path.join(
    VENDOR, "sift-map-tracker", "sift-map-tracker", "routes", "default_route.json"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mark-type", type=int, default=701, help="要规划的采集物 mark_type")
    ap.add_argument("--out", default=OUT_DEFAULT)
    args = ap.parse_args()

    sys.path.insert(0, WOOZIII)
    from tracker.models import NormalizedPoint  # noqa: E402
    from tracker.route_planner import plan_route, measure_route_distance  # noqa: E402

    raw = json.load(open(POINTS, encoding="utf-8"))
    points = [
        NormalizedPoint(
            id=item["id"],
            mark_type=int(item["mark_type"]),
            title=item.get("title") or "",
            lat=float(item.get("lat", 0)),
            lng=float(item.get("lng", 0)),
            pixel_x=int(item["pixel_x"]),
            pixel_y=int(item["pixel_y"]),
            icon_path=item.get("icon_path") or "",
            label=item.get("label") or "",
        )
        for item in raw
        if int(item["mark_type"]) == args.mark_type
    ]
    if not points:
        print(json.dumps({"error": "no_points", "mark_type": args.mark_type}))
        return 2

    plan = plan_route(
        points=points,
        enabled_mark_types={args.mark_type},
        collectible_mark_types={args.mark_type},
        start_mode="fixed_corner",
        current_position=None,
        map_height=8192,
    )

    nodes = []
    for index, waypoint in enumerate(plan.waypoints):
        nodes.append({
            "id": uuid.uuid5(uuid.NAMESPACE_URL, f"wooziii:{waypoint.point_id}").hex,
            "x": int(waypoint.pixel_x),
            "y": int(waypoint.pixel_y),
            "label": waypoint.title or f"节点 {index + 1}",
            "radius": 30,
            "node_type": "collect",
        })

    points_out = [
        {"x": node["x"], "y": node["y"], "label": node["label"], "radius": node["radius"]}
        for node in nodes
    ]
    edges = [
        {"id": uuid.uuid4().hex, "from": nodes[i]["id"], "to": nodes[i + 1]["id"], "edge_type": "normal"}
        for i in range(len(nodes) - 1)
    ]

    payload = {
        "format_version": "sift0.6",
        "name": f"默认采集路线-{args.mark_type}",
        "loop": False,
        "notes": (
            "由 vendor/adapters/sift_map_tracker/build_default_route.py 生成；"
            "来源：Wooziii-roco-map-tracker/data/points.normalized.json + tracker.route_planner；"
            "坐标为 8192 地图像素，仅用于截图识别导航。"
        ),
        "points": points_out,
        "nodes": nodes,
        "edges": edges,
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    print(json.dumps({
        "out": args.out,
        "mark_type": args.mark_type,
        "nodes": len(nodes),
        "edges": len(edges),
        "polyline_distance_px": round(measure_route_distance(plan.polyline), 1),
        "first": points_out[0] if points_out else None,
        "last": points_out[-1] if points_out else None,
        "bytes": os.path.getsize(args.out),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
