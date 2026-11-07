# -*- coding: utf-8 -*-
"""Verify feature/rocokingdom-ui remote contents."""
import json, urllib.request, urllib.error

REPO = "murongyunyeh/rocogi"
BRANCH = "feature/rocokingdom-ui"
token = open(r"C:\Users\13005\.rocogi\github_token", "r", encoding="utf-8").read().strip()
HDRS = {"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
        "User-Agent": "rocogi-verify"}

def gh(path):
    req = urllib.request.Request("https://api.github.com" + path, headers=HDRS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

sha = gh("/repos/%s/git/ref/heads/%s" % (REPO, BRANCH))["object"]["sha"]
print("branch sha:", sha)
c = gh("/repos/%s/git/commits/%s" % (REPO, sha))
print("parents:", c["parents"][0]["sha"], "| files changed:", len(c.get("files", [])) or "(files not listed)")

checks = [
    ("frontend/src/rocoui/index.ts", 2385),
    ("frontend/src/rocoui/style.css", 48892),
    ("frontend/src/rocoui/extras.css", 5382),
    ("frontend/src/rocoui/rk.ts", 19339),
    ("frontend/src/rocoui/fonts/roco-kingdom-sans.ttf", 4564220),
    ("frontend/src/rocoui/fonts/roco-kingdom-rune.ttf", 14024),
    ("frontend/src/rocoui/PORT.md", 3098),
    ("frontend/src/App.vue", 6914),
    ("frontend/index.html", None),
]
ok = True
for path, expect in checks:
    try:
        meta = gh("/repos/%s/contents/%s?ref=%s" % (REPO, path, BRANCH))
        size = meta.get("size")
        mark = "OK " if (expect is None or size == expect) else "SIZE-MISMATCH"
        if expect is not None and size != expect:
            ok = False
        print("%s %s (%s bytes, expect %s)" % (mark, path, size, expect))
    except urllib.error.HTTPError as e:
        ok = False
        print("MISSING %s (HTTP %s)" % (path, e.code))

# zombie dir must NOT exist
try:
    gh("/repos/%s/contents/frontend/src/rocoui/components?ref=%s" % (REPO, BRANCH))
    ok = False
    print("FAIL zombie rocoui/components exists on branch")
except urllib.error.HTTPError as e:
    if e.code == 404:
        print("OK  no zombie rocoui/components on branch")
    else:
        raise

print("VERIFY:", "ALL PASS" if ok else "HAS PROBLEMS")
