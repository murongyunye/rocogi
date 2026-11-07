# -*- coding: utf-8 -*-
"""Push rocogi-mirror/frontend to branch feature/rocokingdom-ui via Git Data API."""
import base64, json, os, sys, urllib.request, urllib.error

REPO = "murongyunyeh/rocogi"
API = "https://api.github.com"
MIRROR = r"C:\Users\13005\Downloads\work\rocogi-mirror\frontend"
BRANCH = "feature/rocokingdom-ui"
EXCLUDE_DIRS = {"node_modules", "dist"}
EXCLUDE_FILES = {"pnpm-workspace.yaml", "pnpm-lock.yaml"}

token = open(r"C:\Users\13005\.rocogi\github_token", "r", encoding="utf-8").read().strip()
HDRS = {
    "Authorization": "Bearer " + token,
    "Accept": "application/vnd.github+json",
    "User-Agent": "rocogi-push",
    "X-GitHub-Api-Version": "2022-11-28",
}

def gh(method, path, payload=None):
    url = API + path if path.startswith("/") else path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=HDRS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        print("HTTP %s %s -> %s" % (method, path, e.code))
        print(e.read().decode("utf-8")[:2000])
        raise

# 1. collect files
files = []
for root, dirs, names in os.walk(MIRROR):
    rel_dir = os.path.relpath(root, MIRROR)
    parts = set(rel_dir.split(os.sep)) if rel_dir != "." else set()
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    for n in names:
        if rel_dir == "." and n in EXCLUDE_FILES:
            continue
        files.append(os.path.join(root, n))
files.sort()
print("files to push:", len(files))

# 2. base commit + tree
ref = gh("GET", "/repos/%s/git/ref/heads/main" % REPO)
base_sha = ref["object"]["sha"]
commit = gh("GET", "/repos/%s/git/commits/%s" % (REPO, base_sha))
base_tree = commit["tree"]["sha"]
print("main head:", base_sha, "tree:", base_tree)

# 3. create blobs
tree_entries = []
for i, fp in enumerate(files, 1):
    rel = os.path.relpath(fp, MIRROR).replace(os.sep, "/")
    data = open(fp, "rb").read()
    blob = gh("POST", "/repos/%s/git/blobs" % REPO,
              {"content": base64.b64encode(data).decode("ascii"), "encoding": "base64"})
    tree_entries.append({"path": "frontend/" + rel, "mode": "100644",
                         "type": "blob", "sha": blob["sha"]})
    if i % 20 == 0 or i == len(files):
        print("blobs %d/%d" % (i, len(files)))

# 4. create tree (base_tree merges our entries on top of main's tree)
tree = gh("POST", "/repos/%s/git/trees" % REPO,
          {"base_tree": base_tree, "tree": tree_entries})
print("new tree:", tree["sha"], "truncated:", tree.get("truncated"))

# 5. branch exists?
try:
    existing = gh("GET", "/repos/%s/git/ref/heads/%s" % (REPO, BRANCH))
except urllib.error.HTTPError as e:
    if e.code == 404:
        existing = None
    else:
        raise

msg = ("feat(frontend): adopt rocokingdom-ui design system (Vue port)\n\n"
       "- vendor verbatim dist CSS + fonts from rocokingdom-ui@0.0.1-beta.0 (MIT)\n"
       "- add src/rocoui: Vue 3 port of 24 components with verbatim class names\n"
       "  (RocoShape/Material/Panel/Button/Checkbox/Switch/Tabs/Radio/Toggle/Select/Modal/Drawer...)\n"
       "- add Badge/Tag/Breadcrumb/Slider approximations (absent from beta package)\n"
       "- retheme shell & views to paper/stone/gold tokens via CSS bridge\n"
       "- rebuild App.vue on Layout/SideNav primitives")

new_commit = gh("POST", "/repos/%s/git/commits" % REPO,
                {"message": msg, "tree": tree["sha"], "parents": [base_sha]})
print("new commit:", new_commit["sha"])

if existing:
    gh("PATCH", "/repos/%s/git/refs/heads/%s" % (REPO, BRANCH),
       {"sha": new_commit["sha"], "force": False})
    print("branch updated:", BRANCH)
else:
    gh("POST", "/repos/%s/git/refs" % REPO,
       {"ref": "refs/heads/" + BRANCH, "sha": new_commit["sha"]})
    print("branch created:", BRANCH)

print("DONE")
print("https://github.com/%s/tree/%s" % (REPO, BRANCH))
print("https://github.com/%s/commit/%s" % (REPO, new_commit["sha"]))
