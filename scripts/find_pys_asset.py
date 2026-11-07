# -*- coding: utf-8 -*-
"""Find a python-build-standalone asset for cpython 3.12.x windows install_only; else fallback marker."""
import json, urllib.request

HDRS = {"User-Agent": "rocogi-toolchain", "Accept": "application/vnd.github+json"}

def get(url):
    req = urllib.request.Request(url, headers=HDRS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

found = []
for page in (1, 2, 3):
    rels = get("https://api.github.com/repos/astral-sh/python-build-standalone/releases?per_page=100&page=%d" % page)
    for rel in rels:
        for a in rel.get("assets", []):
            n = a["name"]
            if ("cpython-3.12.16" in n or "cpython-3.12.14" in n) and n.endswith("install_only.tar.gz") and "windows" in n and "x86_64" in n and "shared" in n:
                found.append((rel["tag_name"], n, a["browser_download_url"]))
    if found:
        break

for tag, name, url in found[:10]:
    print(tag, "|", name)
    print("   ", url)
if not found:
    print("NO MATCH FOUND -> use bundled 3.12.14 fallback")
