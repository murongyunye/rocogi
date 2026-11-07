# -*- coding: utf-8 -*-
"""Mirror vendor/ subtree of rocogi."""
import concurrent.futures as cf, json, os, sys, urllib.request

REPO = "murongyunyeh/rocogi"
MIRROR = r"C:\Users\13005\Downloads\work\rocogi-mirror"
token = open(r"C:\Users\13005\.rocogi\github_token", "r", encoding="utf-8").read().strip()
HDRS = {"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
        "User-Agent": "rocogi-mirror"}

tree = json.load(open(r"C:\Users\13005\Downloads\work\rocogi_tree2.json", encoding="utf-8"))
targets = [e["path"] for e in tree["tree"] if e["type"] == "blob" and e["path"].startswith("vendor/")]
print("vendor targets:", len(targets))

def fetch(path):
    out = os.path.join(MIRROR, path.replace("/", os.sep))
    if os.path.exists(out) and os.path.getsize(out) > 0:
        return path, -1, None
    os.makedirs(os.path.dirname(out), exist_ok=True)
    url = "https://raw.githubusercontent.com/%s/main/%s" % (REPO, urllib.request.quote(path))
    req = urllib.request.Request(url, headers=HDRS)
    err = None
    for _ in range(3):
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
done = 0
with cf.ThreadPoolExecutor(max_workers=12) as ex:
    for path, size, err in ex.map(fetch, targets):
        done += 1
        if err:
            fails.append(path)
            print("FAIL", path, err[:120])
        if done % 500 == 0:
            print("progress %d/%d" % (done, len(targets)))

print("done. fails:", len(fails))
sys.exit(1 if fails else 0)
