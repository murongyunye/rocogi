"""Probe the real Rocogi backends and dump JSON samples for the webui adapter."""
import json
import os
import sys
import urllib.request
import urllib.error

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "probe_out")
os.makedirs(OUT, exist_ok=True)

TARGETS = [
    ("8787", "GET", "/api/health"),
    ("8787", "GET", "/api/meta"),
    ("8787", "GET", "/api/engines"),
    ("8787", "GET", "/api/components"),
    ("8787", "GET", "/api/runs"),
    ("8787", "GET", "/api/nodes"),
    ("8787", "GET", "/api/workflows"),
    ("8787", "GET", "/api/map/meta"),
    ("8787", "GET", "/api/dex/meta"),
    ("8787", "GET", "/api/realtime/status"),
    ("8787", "GET", "/api/tracker/status"),
    ("8787", "GET", "/api/settings"),
    ("8787", "GET", "/api/resources"),
    ("8787", "GET", "/api/harness/manifest"),
    ("8787", "GET", "/api/harness/tools"),
    ("8787", "GET", "/api/battle/presets"),
    ("8787", "GET", "/api/map/points?max=5"),
    ("8787", "GET", "/api/assets/manifest.json"),
    ("8788", "GET", "/api/health"),
]

def fetch(port, path, timeout=20):
    url = f"http://127.0.0.1:{port}{path}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            ctype = resp.headers.get("content-type", "")
            ok = resp.status
            try:
                return {"url": url, "status": ok, "ctype": ctype, "json": json.loads(raw.decode("utf-8"))}
            except Exception:
                return {"url": url, "status": ok, "ctype": ctype, "text": raw.decode("utf-8", "replace")[:400]}
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")[:400]
        except Exception:
            body = ""
        return {"url": url, "status": e.code, "error": body}
    except Exception as e:
        return {"url": url, "status": "ERR", "error": str(e)}


def shape(obj, depth=0):
    if depth > 2:
        return "..."
    if isinstance(obj, dict):
        return {k: shape(v, depth + 1) for k, v in list(obj.items())[:14]}
    if isinstance(obj, list):
        return [shape(obj[0], depth + 1)] if obj else []
    return type(obj).__name__


def main():
    report = {}
    for port, method, path in TARGETS:
        res = fetch(port, path)
        key = f"{port}{path}"
        if "json" in res:
            res["shape"] = shape(res["json"])
            with open(os.path.join(OUT, key.replace("/", "_").replace("?", "_") + ".json"), "w", encoding="utf-8") as fh:
                json.dump(res["json"], fh, ensure_ascii=False, indent=2)
        report[key] = {k: v for k, v in res.items() if k != "json"}
    with open(os.path.join(OUT, "_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
