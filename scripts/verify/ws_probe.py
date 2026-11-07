"""Probe: does the run evidence WebSocket push events live (not only replay)?"""
import asyncio
import json
import time
import urllib.request

import websockets

BASE = "http://127.0.0.1:8787"


def post(path, body=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body or {}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.load(urllib.request.urlopen(req, timeout=60))


async def main():
    run = post("/api/workflows/wf_demo_catch/run")
    run_id = run.get("id") or run.get("runId")
    print("run", run_id, "status", run.get("status"))
    url = f"ws://127.0.0.1:8787/api/ws/runs/{run_id}"
    t0 = time.time()
    stamps, kinds = [], {}
    last = None
    try:
        async with websockets.connect(url) as ws:
            while time.time() - t0 < 40:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=6)
                except asyncio.TimeoutError:
                    break
                msg = json.loads(raw)
                stamps.append(round(time.time() - t0, 2))
                kinds[msg.get("type")] = kinds.get(msg.get("type"), 0) + 1
                last = msg
    except websockets.exceptions.ConnectionClosedOK:
        print("socket closed by server after run.finished")
    detail = json.load(urllib.request.urlopen(f"{BASE}/api/runs/{run_id}", timeout=20))
    span = (stamps[0], stamps[-1]) if stamps else (None, None)
    live = sum(1 for i, s in enumerate(stamps) if i and s - stamps[i - 1] > 0.02)
    print("events", len(stamps), "kinds", kinds)
    print("arrival span", span, "progressive steps", live)
    print("samples", stamps[:6], "...", stamps[-4:])
    print("last", json.dumps(last, ensure_ascii=False)[:220])
    print("run status", detail.get("status"), "steps", len(detail.get("steps") or []), "events stored", len(detail.get("events") or []))


asyncio.run(main())
