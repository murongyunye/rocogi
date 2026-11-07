"""fetch_bwiki.py - fetch wikitext for a list of titles, save under datasets/bwiki/wiki/<name>.txt.

Usage: python fetch_bwiki.py "Title A" "Title B" ...
       python fetch_bwiki.py --list file_with_titles.txt
"""
import json
import os
import ssl
import sys
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
BASE = "https://wiki.biligame.com/rocom"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OUT = os.path.join(ROOT, "datasets", "bwiki", "wiki")


def api(**params):
    params.setdefault("format", "json")
    url = BASE + "/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45, context=CTX) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def fetch_batch(titles):
    d = api(action="query", prop="revisions", rvprop="content", rvslots="main",
            titles="|".join(titles))
    out = {}
    for _pid, p in d.get("query", {}).get("pages", {}).items():
        title = p.get("title", "")
        revs = p.get("revisions") or [{}]
        text = revs[0].get("slots", {}).get("main", {}).get("*", "")
        out[title] = text
    return out


def safe_name(title):
    return title.replace("/", "__").replace(":", "_").replace("\\", "_")


def save(title, text):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, safe_name(title) + ".txt")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return path


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--list":
        with open(args[1], encoding="utf-8") as fh:
            titles = [l.strip() for l in fh if l.strip()]
    else:
        titles = args
    total = 0
    for i in range(0, len(titles), 20):
        chunk = titles[i:i + 20]
        got = fetch_batch(chunk)
        for t in chunk:
            text = got.get(t, "")
            if not text:
                print(f"  MISS {t}")
                continue
            p = save(t, text)
            total += 1
            print(f"  {len(text):7d} {os.path.basename(p)}")
    print(f"saved {total}/{len(titles)} to {OUT}")
