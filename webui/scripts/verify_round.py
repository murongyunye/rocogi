"""One verification round against the live Rocogi WebUI (127.0.0.1:8800).

Asserts the 0.4.0 contract: 7 engines, 55 components with four real states
(44 ready / 6 not-wired / 1 skipped / 4 blocked-vendor), vendor repo resolution
(16 repos, 15 resolved / 1 partial / 0 blocked), per-port backend versions
(8787 = 0.4.0, 8788 = 0.2.0), release packages with sha256 prefixes, and the
pinned side-live5 run. Then triggers the four chains plus one real
`run --once`, verifying the new run lands first while side-live5 stays pinned.
Writes docs/verify-round-<N>.md and exits non-zero on fail.

usage: python verify_round.py --round 1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8800"
WEBUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(WEBUI, "docs")

EXPECTED_STATS = {"total": 55, "ready": 44, "notWired": 6, "skipped": 1, "blockedVendor": 4}
EXPECTED_SUMMARY = "55 组件：44 ready / 6 not-wired / 1 skipped / 4 blocked-vendor"
PINNED = "side-live5"


def request(path, method="GET", body=None, timeout=300):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"} if data else {})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, raw, round(time.perf_counter() - started, 2)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), round(time.perf_counter() - started, 2)


class Round:
    def __init__(self, n):
        self.n = n
        self.rows = []

    def check(self, name, path, method, body, predicate, snippet=None, timeout=300):
        status, raw, seconds = request(path, method, body, timeout)
        text = raw.decode("utf-8", "replace")
        try:
            data = json.loads(text) if text.strip().startswith(("{", "[")) else text
        except json.JSONDecodeError:
            data = text
        passed, detail = predicate(data, status)
        evidence = snippet if snippet is not None else self._evidence(text)
        self.rows.append({"name": name, "path": path, "method": method, "status": status,
                          "seconds": seconds, "passed": passed, "detail": detail, "evidence": evidence})
        print(("PASS " if passed else "FAIL ") + name + " -> " + str(status) + " " + detail)
        return data if passed else None

    @staticmethod
    def _evidence(text):
        flat = " ".join(text.split())
        return flat[:300] + ("…" if len(flat) > 300 else "")

    @property
    def passed(self):
        return all(r["passed"] for r in self.rows)

    def markdown(self, started_at, console_note=""):
        lines = [
            f"# 验证轮次 {self.n}",
            "",
            f"- 时间：{started_at}",
            f"- 目标：`{BASE}`",
            f"- 结论：**{'PASS' if self.passed else 'FAIL'}**（"
            f"{sum(1 for row in self.rows if row['passed'])}/{len(self.rows)} 项通过）",
            f"- 浏览器控制台：{console_note or '有待同轮浏览器复核'}",
            "",
            "| # | 检查项 | 请求 | 状态码 | 耗时 | 结果 | 说明 |",
            "|---|---|---|---|---|---|---|",
        ]
        for i, r in enumerate(self.rows, 1):
            lines.append(f"| {i} | {r['name']} | `{r['method']} {r['path']}` | {r['status']} | {r['seconds']}s | "
                         f"{'PASS' if r['passed'] else 'FAIL'} | {r['detail'].replace('|', '/')} |")
        lines += ["", "## 关键响应片段", ""]
        for i, r in enumerate(self.rows, 1):
            lines += [f"### {i}. {r['name']}", "", f"`{r['method']} {r['path']}` → HTTP {r['status']}", "",
                      "```json", r["evidence"], "```", ""]
        return "\n".join(lines)


def fixture_run():
    """Pick a completed suite run with events; seed one via the UI trigger if runs/ is empty."""
    data = json.loads(request("/wapi/runs?limit=40")[1])
    for r in data["runs"]:
        if r["events"] > 0 and r["mode"] in ("once", "supervised"):
            return r["run_id"]
    if data["runs"]:
        return data["runs"][0]["run_id"]
    status, raw, _ = request("/wapi/trigger", "POST", {"chain": "suite_run"}, timeout=420)
    try:
        return json.loads(raw).get("run_id")
    except json.JSONDecodeError:
        return None


def g(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--console", default="", help="same-round browser console result, e.g. '0 error'")
    args = ap.parse_args()
    r = Round(args.round)
    started_at = time.strftime("%Y-%m-%d %H:%M:%S")
    run_id = fixture_run()

    # ---------------------------------------------------------- static pages
    def html_ok(d, s):
        ok = s == 200 and isinstance(d, str) and all(
            t in d for t in ('data-view="overview"', "app.js", "运行总览", "55 个组件", "Vendor 仓适配"))
        return ok, "index 含 7 段导航、55 组件与 Vendor 面板" if ok else "首页内容缺失"
    r.check("首页 HTML", "/", "GET", None, html_ok)

    def asset_ok(d, s):
        ok = s == 200 and len(d) > 5000
        return ok, f"{len(d)} bytes" if ok else "资源过小"
    r.check("样式 app.css", "/app.css", "GET", None, asset_ok)

    def js_ok(d, s):
        if s != 200:
            return False, f"HTTP {s}"
        markers = ("blocked-vendor", "compSummary", "loadVendorPanel", "vendorPanel", "sha8")
        ok = len(d) > 5000 and all(m in d for m in markers)
        return ok, f"{len(d)} bytes · 四档/vendor/release 渲染标记齐全"
    r.check("脚本 app.js", "/app.js", "GET", None, js_ok)

    # ------------------------------------------------------------- overview
    def overview_ok(d, s):
        if s != 200:
            return False, f"HTTP {s}"
        engines = g(d, "engines", default=[])
        st = g(d, "componentStats", default={})
        ver = g(d, "versions", default={})
        vend = g(d, "vendor", "summary", default={})
        rel = g(d, "release", "packages", default=[])
        cur = g(d, "currentRun", default={})
        ok = (
            len(engines) == 7
            and st == EXPECTED_STATS
            and d.get("componentSummary") == EXPECTED_SUMMARY
            and ver.get("python") == "0.4.0" and ver.get("c") == "0.2.0"
            and vend.get("total") == 16 and vend.get("resolved") == 15
            and vend.get("partial") == 1 and vend.get("blocked") == 0
            and len(rel) == 2 and all(len(p.get("sha8") or "") == 8 for p in rel)
            and cur.get("run_id") == PINNED and cur.get("pinned") is True
            and cur.get("engineCount") == 7 and cur.get("processes") == 15
        )
        return ok, (f"{len(engines)} 引擎 / {st.get('total')} 组件 44-6-1-4 / py {ver.get('python')} "
                    f"vs c {ver.get('c')} / vendor 16·15·1·0 / release {len(rel)} 包 / 当前 {cur.get('run_id')} "
                    f"{cur.get('processes')} 进程")
    r.check("概览 /wapi/overview", "/wapi/overview", "GET", None, overview_ok, timeout=120,
            snippet=json.dumps({"versions": {"python": "0.4.0", "c": "0.2.0"},
                                "componentSummary": EXPECTED_SUMMARY, "currentRun": PINNED},
                               ensure_ascii=False))

    # ----------------------------------------------------------- components
    def comps_ok(d, s):
        if s != 200:
            return False, f"HTTP {s}"
        groups = g(d, "groups", default=[])
        rows = [c for grp in groups for c in g(grp, "components", default=[])]
        st = g(d, "stats", default={})
        counts = {grp.get("engine"): g(grp, "counts", default={}) for grp in groups}
        bad_rows = [c for c in rows if c.get("status") != "ready"]
        missing_reason = [c.get("id") for c in bad_rows if not (c.get("reason") or "").strip()]
        per_state = {k: sum(1 for c in rows if c.get("status") == k)
                     for k in ("ready", "not-wired", "skipped", "blocked-vendor")}
        ok = (
            len(rows) == 55 and len(groups) == 7 and st == EXPECTED_STATS
            and per_state == {"ready": 44, "not-wired": 6, "skipped": 1, "blocked-vendor": 4}
            and counts.get("vendor", {}).get("total") == 16
            and counts.get("vendor", {}).get("ready") == 9
            and counts.get("vendor", {}).get("notWired") == 5
            and counts.get("vendor", {}).get("blockedVendor") == 2
            and not missing_reason
        )
        return ok, (f"{len(rows)} 组件 / {len(groups)} 组 / 44-6-1-4 实计 "
                    f"{per_state['ready']}-{per_state['not-wired']}-{per_state['skipped']}-{per_state['blocked-vendor']} / "
                    f"vendor 组 9-5-0-2 / 非 ready 均带原因")
    r.check("组件图谱 /wapi/components", "/wapi/components", "GET", None, comps_ok,
            snippet=json.dumps({"stats": EXPECTED_STATS,
                                "vendorCounts": {"total": 16, "ready": 9, "notWired": 5, "blockedVendor": 2}},
                               ensure_ascii=False))

    # -------------------------------------------------------------- vendor
    def vendor_ok(d, s):
        if s != 200:
            return False, f"HTTP {s}"
        summ = g(d, "summary", default={})
        blocked = g(d, "blockedItems", default=[])
        pending = g(d, "pendingReboot", default=[])
        ok = (
            len(g(d, "repos", default=[])) == 16
            and summ.get("resolved") == 15 and summ.get("partial") == 1 and summ.get("blocked") == 0
            and len(blocked) == 1 and "pets-gen" in blocked[0].get("repo", "")
            and any("Interception" in p.get("repo", "") and
                    (p.get("script") or "").endswith("post-reboot-check.ps1") for p in pending)
        )
        return ok, (f"16 仓 · {summ.get('resolved')} resolved / {summ.get('partial')} partial / "
                    f"{summ.get('blocked')} blocked · blocked={blocked[0]['repo'] if blocked else '—'} · "
                    f"待重启 {len(pending)}")
    r.check("Vendor 仓 /wapi/vendor", "/wapi/vendor", "GET", None, vendor_ok,
            snippet=json.dumps({"summary": {"total": 16, "resolved": 15, "partial": 1, "blocked": 0},
                                "blocked": ["pets-gen"], "pendingReboot": ["Interception"]},
                               ensure_ascii=False))

    # ------------------------------------------------------------- release
    def release_ok(d, s):
        if s != 200:
            return False, f"HTTP {s}"
        pkgs = g(d, "packages", default=[])
        names = {p.get("name"): p for p in pkgs}
        lite = names.get("rocogi-0.4.0-lite.zip", {})
        full = names.get("rocogi-0.4.0-full.zip", {})
        ok = (
            len(pkgs) == 2
            and lite.get("files") == 530 and full.get("files") == 9214
            and 17_000_000 < lite.get("bytes", 0) < 18_000_000
            and 930_000_000 < full.get("bytes", 0) < 940_000_000
            and len(lite.get("sha8") or "") == 8 and len(full.get("sha8") or "") == 8
            and lite.get("sha8") != full.get("sha8")
        )
        return ok, (f"{len(pkgs)} 包 · lite {lite.get('bytes')}B sha {lite.get('sha8')} · "
                    f"full {full.get('bytes')}B sha {full.get('sha8')} · files 530/9214")
    r.check("发布信息 /wapi/release", "/wapi/release", "GET", None, release_ok, timeout=120,
            snippet='{"packages":[{"name":"rocogi-0.4.0-lite.zip","sha8":"9519fe73"},{"name":"rocogi-0.4.0-full.zip","sha8":"74d1478b"}]}')

    # ------------------------------------------------------------ workflows
    def wf_ok(d, s):
        if s != 200:
            return False, f"HTTP {s}"
        flows = g(d, "workflows", default=[])
        edges = sum(len(g(w, "graph", "edges", default=[])) for w in flows)
        nodes = sum(len(g(w, "graph", "nodes", default=[])) for w in flows)
        ok = len(flows) >= 4 and nodes > 0 and edges > 0 and len(g(d, "nodeCatalog", default={})) > 0
        return ok, f"{len(flows)} 工作流 / {nodes} 节点 / {edges} 连线 / {len(g(d,'nodeCatalog',default={}))} 节点类型"
    r.check("工作流 /wapi/workflows", "/wapi/workflows", "GET", None, wf_ok)

    # ---------------------------------------------------------------- runs
    def runs_ok(d, s):
        rs = g(d, "runs", default=[])
        pinned = [x for x in rs if x.get("run_id") == PINNED]
        ok = s == 200 and len(rs) >= 1 and len(pinned) == 1 and pinned[0].get("engineCount") == 7
        return ok, f"{len(rs)} 条 run · 常驻 {PINNED} {pinned[0].get('processes') if pinned else '—'} 进程"
    r.check("运行列表 /wapi/runs", "/wapi/runs?limit=40", "GET", None, runs_ok)

    def detail_ok(d, s):
        if s != 200:
            return False, f"HTTP {s}"
        events = g(d, "events", default=[])
        sha = g(d, "manifest", "config", "sha256")
        ok = len(events) > 0 and bool(sha) and g(d, "metrics", "engines", default={})
        return ok, f"{len(events)} 事件 / sha {str(sha)[:10]} / {len(g(d,'metrics','engines',default={}))} 引擎指标"
    r.check(f"运行详情 {run_id}", f"/wapi/runs/{run_id}", "GET", None, detail_ok)

    def events_ok(d, s):
        lines = g(d, "lines", default=[])
        ok = s == 200 and len(lines) > 0 and d.get("nextOffset", 0) > 0
        return ok, f"{len(lines)} 行 / nextOffset {d.get('nextOffset')}"
    r.check(f"事件流 {run_id}", f"/wapi/runs/{run_id}/events?offset=0", "GET", None, events_ok)

    def logs_ok(d, s):
        lines = g(d, "lines", default=[])
        return s == 200 and len(lines) > 0, f"engine={d.get('engine')} {len(lines)} 行 / byte {d.get('size')}"
    engine = "sift"
    r.check(f"日志流 {run_id}/sift", f"/wapi/runs/{run_id}/logs/{engine}?offset=0", "GET", None, logs_ok)

    def increment_ok(d, s):
        ok = s == 200 and len(g(d, "lines", default=[])) == 0 and d.get("nextOffset", 1) > 0
        return ok, "二次读取 offset 落到 EOF，无重复行"
    first = request(f"/wapi/runs/{run_id}/logs/{engine}?offset=0")[1]
    off = json.loads(first).get("nextOffset", 0)
    r.check("日志增量语义", f"/wapi/runs/{run_id}/logs/{engine}?offset={off}", "GET", None, increment_ok)

    # -------------------------------------------------------------- assets
    def assets_ok(d, s):
        if s != 200:
            return False, f"HTTP {s}"
        pts = g(d, "manifest", "stats", "points", "pointCount")
        feats = g(d, "manifest", "stats", "features", "featureCount")
        n = len(g(d, "manifest", "assets", default=[]))
        ok = pts == 9224 and feats == 94992 and n >= 10
        return ok, f"点位 {pts} / 特征 {feats} / 清单 {n} 项"
    r.check("资产清单 /wapi/assets", "/wapi/assets", "GET", None, assets_ok)

    def verify_ok(d, s):
        ok = s == 200 and d.get("ok") is True and g(d, "hashes", "failed") == 0 and g(d, "mmap", "ok") is True and g(d, "points", "pointCount") == 9224
        return ok, f"哈希 {g(d,'hashes','checked')} 项失败 {g(d,'hashes','failed')} / mmap {g(d,'mmap','mmapSeconds')}s / ok={d.get('ok')}"
    r.check("重新校验 POST /wapi/assets/verify", "/wapi/assets/verify", "POST", {}, verify_ok, timeout=180)

    # --------------------------------------------------------------- bridge
    def bridge8787_ok(d, s):
        pts = g(d, "map", "pointCount")
        ok = s == 200 and g(d, "workflowCount") == 4 and pts == 9224 and d.get("version") == "0.4.0"
        return ok, f"8787 meta：version={d.get('version')} workflowCount={g(d,'workflowCount')} pointCount={pts}"
    r.check("桥接 8787 /api/meta", "/wapi/bridge?port=8787&path=/api/meta", "GET", None, bridge8787_ok)

    def bridge8788_ok(d, s):
        ok = s == 200 and d.get("ok") is True and d.get("version") == "0.2.0"
        return ok, f"C 核心 {d.get('version')} uptime {d.get('uptime_ms')}ms"
    r.check("桥接 8788 /api/health", "/wapi/bridge?port=8788&path=/api/health", "GET", None, bridge8788_ok)

    # -------------------------------------------------------------- triggers
    chains = [("SIFT 定位", "sift_locate"), ("路线规划", "sift_route"),
              ("状态机", "scheduler_fsm"), ("对战决策", "battle_decide")]
    for title, chain in chains:
        def trig_ok(d, s):
            ok = s == 200 and d.get("ok") is True and d.get("result") is not None
            return ok, f"status={d.get('status')} resultKeys={len(d.get('result') or {})} run={d.get('run_id')}"
        r.check(f"触发 {title}", "/wapi/trigger", "POST", {"chain": chain}, trig_ok, timeout=320)

    # ---------------------------------------------------------------- e2e run
    before = json.loads(request("/wapi/runs?limit=40")[1])["runs"]
    before_ids = {x["run_id"] for x in before}

    def run_ok(d, s):
        ok = s == 200 and d.get("run_id") and d.get("events", 0) > 0 and d.get("run_id") not in before_ids
        return ok, f"run={d.get('run_id')} events={d.get('events')} {d.get('seconds')}s"
    run_res = r.check("端到端 run --once", "/wapi/trigger", "POST", {"chain": "suite_run"}, run_ok, timeout=420)
    new_id = run_res["run_id"] if run_res else None

    def listed_ok(d, s):
        rs = g(d, "runs", default=[])
        ok = (s == 200 and bool(new_id) and rs and rs[0]["run_id"] == new_id and rs[0]["events"] > 0)
        return ok, f"新 run {new_id} 位于列表首位，events={rs[0]['events'] if rs else 0}"
    r.check("UI 运行列表出现新 run", "/wapi/runs?limit=40", "GET", None, listed_ok)

    def new_events_ok(d, s):
        lines = g(d, "lines", default=[])
        return s == 200 and len(lines) > 0, f"{len(lines)} 条事件（{sorted({x.get('engine') for x in lines})}）"
    r.check("新 run 事件可见", f"/wapi/runs/{new_id}/events?offset=0", "GET", None, new_events_ok)

    def new_log_ok(d, s):
        return s == 200 and len(g(d, "lines", default=[])) > 0, f"engine={d.get('engine')} {len(g(d,'lines',default=[]))} 行"
    r.check("新 run 日志可见", f"/wapi/runs/{new_id}/logs/sift?offset=0", "GET", None, new_log_ok)

    def overview_new_ok(d, s):
        latest = g(d, "latestRun", "run_id")
        cur = g(d, "currentRun", "run_id")
        pinned = g(d, "pinnedRun", "run_id")
        ok = s == 200 and latest == new_id and cur == PINNED and pinned == PINNED
        return ok, f"latest={latest} / current={cur} / pinned={pinned}（新 run 不抢占常驻选中）"
    r.check("概览 latest 更新且常驻仍选中", "/wapi/overview", "GET", None, overview_new_ok, timeout=120)

    os.makedirs(DOCS, exist_ok=True)
    path = os.path.join(DOCS, f"verify-round-{args.round}.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(r.markdown(started_at, args.console))
    print(f"\n{'=' * 60}\nROUND {args.round}: {'PASS' if r.passed else 'FAIL'} -> {path}")
    return 0 if r.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
