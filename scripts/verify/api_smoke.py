"""End-to-end API smoke test for the local rocogi backend (mock target)."""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8787"
results = []


def pet_path(name: str) -> str:
    """Percent-encode a pet name; hand-written codes are easy to get wrong."""
    return "/api/pvp/dataset/pets/" + urllib.parse.quote(name)


def call(method, path, payload=None, timeout=120):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            return resp.status, (json.loads(body) if body.strip().startswith(("{", "[")) else body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        return exc.code, body
    except Exception as exc:  # noqa: BLE001
        return 0, f"{type(exc).__name__}: {exc}"


def check(name, fn):
    started = time.time()
    try:
        res = fn()
        ok, detail = (res, "ok") if isinstance(res, bool) else res
    except Exception as exc:  # noqa: BLE001
        ok, detail = False, f"{type(exc).__name__}: {exc}"
    ms = int((time.time() - started) * 1000)
    results.append((name, ok, detail, ms))
    print(("PASS " if ok else "FAIL ") + f"{name} ({ms}ms) :: {str(detail)[:220]}")


def get_ok(path, predicate=None, timeout=60):
    status, body = call("GET", path, timeout=timeout)
    if status != 200:
        return False, f"HTTP {status} {str(body)[:160]}"
    if predicate and not predicate(body):
        return False, f"unexpected body {str(body)[:200]}"
    return True, "ok"


def main():
    check("meta", lambda: get_ok("/api/meta", lambda b: b["map"]["pointCount"] == 9224))
    check("nodes", lambda: get_ok("/api/nodes", lambda b: len(b.get("nodes", b)) > 10))
    check("actions", lambda: get_ok("/api/actions", lambda b: len(b.get("actions", b)) >= 30))
    check("components", lambda: get_ok("/api/components", lambda b: bool(b)))
    check("engines", lambda: get_ok("/api/engines", lambda b: len(b["presets"]) >= 4))
    check("settings", lambda: get_ok("/api/settings", lambda b: "target" in b))
    check("dex meta", lambda: get_ok("/api/dex/meta", lambda b: b["total"] >= 400))
    check("dex pokemon", lambda: get_ok("/api/dex/pokemon?limit=5", lambda b: len(b["items"]) == 5))
    check("dex detail", lambda: get_ok("/api/dex/pokemon/%E8%BF%AA%E8%8E%AB", lambda b: "pokemon" in b))
    check("dex skills", lambda: get_ok("/api/dex/skills?limit=5", lambda b: bool(b)))
    check("bwiki catalog", lambda: get_ok("/api/bwiki/catalog", lambda b: bool(b)))
    check("map points", lambda: get_ok("/api/map/points?limit=10", lambda b: bool(b)))
    check("map route", lambda: call("POST", "/api/map/route", {"category": "宝箱", "limit": 6})[0] == 200)
    check("map position", lambda: call("POST", "/api/map/position", {})[0] == 200)
    check("pvp meta", lambda: get_ok("/api/pvp/meta", lambda b: len(b["opponents"]) >= 2))
    check("pvp analyze", lambda: call("POST", "/api/pvp/analyze", {"team": ["千棘盔", "影狸", "裘卡", "琉璃水母", "迷迷箱怪", "海豹船长"]})[0] == 200)
    check("pvp matchup", lambda: call("POST", "/api/pvp/matchup", {"team": ["千棘盔", "影狸", "裘卡"], "opponent": "wing", "simulations": 12, "maxTurns": 20}, timeout=180)[0] == 200)
    check("pvp dataset", lambda: get_ok("/api/pvp/dataset", lambda b: b["available"] and b["counts"]["pet"] >= 600))
    check(
        "pvp dataset profile",
        lambda: get_ok(pet_path("千棘盔"), lambda b: b["found"] and b["pet"]["total"] > 0 and bool(b["learnset"])),
    )
    check("pvp dataset usage", lambda: get_ok("/api/pvp/dataset/usage?kind=skills&limit=5", lambda b: len(b["items"]) == 5))
    check("pvp dataset skills", lambda: get_ok("/api/pvp/dataset/skills?limit=5", lambda b: len(b["items"]) == 5))
    check(
        "pvp variant axes",
        # 形态 form 与配色 color_type 是两条轴：污染必须落在 color_type 上而不是 form。
        lambda: get_ok(
            pet_path("波波螺（被污染的样子）"),
            lambda b: b["found"] and b["variant"]["colorType"] == "pollution" and not b["pet"]["form"],
        ),
    )
    check(
        "pvp variant summary",
        lambda: get_ok("/api/pvp/dataset", lambda b: b["variantCounts"].get("normal", 0) > 600),
    )
    check("battle pokemon", lambda: get_ok("/api/battle/pokemon", lambda b: bool(b)))
    check("battle simulate", lambda: call("POST", "/api/battle/simulate", {}, timeout=180)[0] == 200)
    check("harness manifest", lambda: get_ok("/api/harness/manifest", lambda b: "tools" in b or "name" in b))
    check("harness tools", lambda: get_ok("/api/harness/tools", lambda b: bool(b)))
    check("harness act observe", lambda: call("POST", "/api/harness/act", {"action": "observe", "args": {}})[0] == 200)
    check("hotkeys", lambda: get_ok("/api/hotkeys", lambda b: bool(b)))
    check("onedragon plan", lambda: get_ok("/api/onedragon/plan", lambda b: len(b["plan"]["tasks"]) >= 5))
    check("workflows", lambda: get_ok("/api/workflows", lambda b: len(b) >= 4))

    status, workflows = call("GET", "/api/workflows")
    wf = workflows[0] if isinstance(workflows, list) and workflows else None
    if wf:
        status, run = call("POST", f"/api/workflows/{wf['id']}/run", {})
        check("workflow run", lambda: (status == 200, (run.get("id") if isinstance(run, dict) else run)))
        if status == 200 and isinstance(run, dict):
            run_id = run.get("id")
            deadline = time.time() + 120
            last = None
            while time.time() < deadline:
                _, detail = call("GET", f"/api/runs/{run_id}")
                last = detail
                if isinstance(detail, dict) and detail.get("status") in {"succeeded", "failed", "stopped", "error"}:
                    break
                time.sleep(1.5)
            status_ok = isinstance(last, dict) and last.get("status") not in {"running", "queued"}
            check("workflow run finished", lambda: (status_ok, f"status={last.get('status') if isinstance(last, dict) else last}"))
            _, events = call("GET", f"/api/runs/{run_id}/events")
            count = len(events) if isinstance(events, list) else len(events.get("events", []))
            check("workflow events", lambda: (count > 0, f"{count} events"))

    check("realtime start", lambda: call("POST", "/api/realtime/start", {})[0] == 200)

    # The session thread needs a few ticks; poll instead of assuming a fixed delay.
    def realtime_running():
        status, body = call("GET", "/api/realtime/status")
        if status != 200 or not isinstance(body, dict):
            return False, body
        ticks = (body.get("counters") or {}).get("ticks", 0)
        return (body.get("running") is True and ticks >= 1), f"running={body.get('running')} ticks={ticks}"

    running, detail = False, None
    for _ in range(20):
        running, detail = realtime_running()
        if running:
            break
        time.sleep(1)
    check("realtime status", lambda: (running, detail))
    check("realtime stop", lambda: call("POST", "/api/realtime/stop", {})[0] == 200)

    check("tracker start", lambda: call("POST", "/api/tracker/start", {})[0] == 200)
    time.sleep(3)
    check("tracker status", lambda: get_ok("/api/tracker/status", lambda b: b["running"] is True, timeout=30))
    check("tracker stop", lambda: call("POST", "/api/tracker/stop", {})[0] == 200)

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED: " + ", ".join(r[0] for r in failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

