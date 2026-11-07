# -*- coding: utf-8 -*-
"""Verify rocogi backend API endpoints (localhost, urllib) — real route names."""
import json, time, urllib.request

BASE = "http://127.0.0.1:8787"

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

checks = [
    ("health", "/api/health"),
    ("meta", "/api/meta"),
    ("nodes", "/api/nodes"),
    ("actions", "/api/actions"),
    ("components", "/api/components"),
    ("workflows", "/api/workflows"),
    ("runs", "/api/runs"),
    ("resources", "/api/resources"),
    ("map-meta", "/api/map/meta"),
    ("battle-pokemon", "/api/battle/pokemon"),
    ("battle-presets", "/api/battle/presets"),
    ("settings", "/api/settings"),
    ("realtime-status", "/api/realtime/status"),
    ("tracker-status", "/api/tracker/status"),
    ("onedragon-plan", "/api/onedragon/plan"),
    ("engines", "/api/engines"),
    ("dex-meta", "/api/dex/meta"),
    ("dex-pokemon", "/api/dex/pokemon?limit=5"),
    ("pvp-meta", "/api/pvp/meta"),
    ("hotkeys", "/api/hotkeys"),
    ("harness-manifest", "/api/harness/manifest"),
    ("harness-tools", "/api/harness/tools"),
]
ok = 0
for name, path in checks:
    try:
        d = get(path)
        if isinstance(d, dict) and "items" in d:
            n, total = len(d["items"]), d.get("total")
        elif isinstance(d, list):
            n = total = len(d)
        else:
            n = total = "-"
        print("OK  %-16s n=%s total=%s" % (name, n, total))
        ok += 1
    except Exception as e:
        print("FAIL %-16s %s" % (name, e))
print("PASSED %d/%d" % (ok, len(checks)))
