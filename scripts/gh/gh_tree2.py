# -*- coding: utf-8 -*-
"""Fetch recursive git tree of murongyunyeh/rocogi and analyze composition."""
import json, urllib.request

REPO = "murongyunyeh/rocogi"
token = open(r"C:\Users\13005\.rocogi\github_token", "r", encoding="utf-8").read().strip()
HDRS = {"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
        "User-Agent": "rocogi-mirror"}

req = urllib.request.Request(
    "https://api.github.com/repos/%s/git/trees/main?recursive=1" % REPO, headers=HDRS)
with urllib.request.urlopen(req, timeout=120) as r:
    data = json.loads(r.read().decode("utf-8"))

blobs = [e for e in data["tree"] if e["type"] == "blob"]
print("truncated:", data.get("truncated"), "| blobs:", len(blobs))

top = {}
for e in blobs:
    key = e["path"].split("/")[0]
    top.setdefault(key, [0, 0])
    top[key][0] += 1
    top[key][1] += e.get("size", 0)

print("%-28s %6s %12s" % ("top-level", "files", "bytes"))
for k in sorted(top, key=lambda k: -top[k][1]):
    print("%-28s %6d %12d" % (k, top[k][0], top[k][1]))

# big blobs (>5MB)
big = sorted([e for e in blobs if e.get("size", 0) > 5_000_000], key=lambda e: -e["size"])
print("\nBlobs >5MB: %d" % len(big))
for e in big[:30]:
    print("  %10d  %s" % (e["size"], e["path"]))

with open(r"C:\Users\13005\Downloads\work\rocogi_tree2.json", "w", encoding="utf-8") as f:
    json.dump(data, f)
print("tree saved -> rocogi_tree2.json")
