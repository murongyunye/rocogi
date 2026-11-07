import json
import time
import urllib.request

BASE = "http://127.0.0.1:8787"


def call(path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


call("/api/realtime/start", "POST", {})
seen = []
for _ in range(26):
    status = call("/api/realtime/status")
    snap = (
        status.get("phase"),
        status["counters"]["ticks"],
        status["counters"]["balls"],
        status["counters"]["battles"],
        status["scene"],
    )
    if not seen or seen[-1] != snap:
        seen.append(snap)
    time.sleep(1)
call("/api/realtime/stop", "POST", {})
print("phase/tick/ball/battle/scene transitions:")
for row in seen:
    print(row)
final = call("/api/realtime/status")
print("logs tail:")
for entry in final["logs"][-12:]:
    print(" ", entry["kind"], entry["message"])
print("counters:", final["counters"])
