# -*- coding: utf-8 -*-
"""Mirror first-party files of rocogi (skip archive/, docs/, vendor/, frontend/)."""
import base64, concurrent.futures as cf, json, os, sys, urllib.request, urllib.error

REPO = "murongyunyeh/rocogi"
MIRROR = r"C:\Users\13005\Downloads\work\rocogi-mirror"
SKIP_TOP = {"archive", "docs", "vendor", "frontend"}
token = open(r"C:\Users\13005\.rocogi\github_token", "r", encoding="utf-8").read().strip()
HDRS = {"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
        "User-Agent": "rocogi-mirror"}

tree = json.load(open(r"C:\Users\13005\Downloads\work\rocogi_tree2.json", encoding="utf-8"))
blobs = [e for e in tree["tree"] if e["type"] == "blob"]
targets = [e["path"] for e in blobs if e["path"].split("/")[0] not in SKIP_TOP]
print("targets:", len(targets), "total bytes:",
      sum(e.get("size", 0) for e in blobs if e["path"].split("/")[0] not in SKIP_TOP))

def fetch(path):
    out = os.path.join(MIRROR, path.replace("/", os.sep))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    url = "https://raw.githubusercontent.com/%s/main/%s" % (REPO, urllib.request.quote(path))
    req = urllib.request.Request(url, headers=HDRS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
            with open(out, "wb") as f:
                f.write(data)
            return path, len(data), None
        except Exception as e:  # noqa: BLE001
            err = e
    return path, 0, str(err)

fails = []
with cf.ThreadPoolExecutor(max_workers=8) as ex:
    for i, (path, size, err) in enumerate(ex.map(fetch, targets), 1):
        if err:
            fails.append((path, err))
            print("FAIL", path, err[:120])
        if i % 50 == 0:
            print("progress %d/%d" % (i, len(targets)))

print("done. fails:", len(fails))
if fails:
    sys.exit(1)
