/* Rocogi 套件控制台 · 前端逻辑（无构建步骤） */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const state = {
  view: "overview",
  overview: null,
  pinnedRun: null,
  workflows: [],
  nodeCatalog: {},
  wfId: null,
  comps: null,
  compFilter: "all",
  vendor: null,
  runs: [],
  runId: null,
  log: { timer: null, running: false, offset: 0, lines: 0, runId: null, engine: null },
  assets: null,
};

const ENGINE_COLORS = {
  capture: "#7aa7d9", vision: "#c99ad6", input: "#e2ab53",
  sift: "#5fd6c0", battle: "#e06d60", scheduler: "#8fbf6f", vendor: "#8b9dc3",
};

const COMPONENT_STATES = [
  { key: "ready", field: "ready", cls: "ok" },
  { key: "not-wired", field: "notWired", cls: "warn" },
  { key: "skipped", field: "skipped", cls: "mute" },
  { key: "blocked-vendor", field: "blockedVendor", cls: "bad" },
];

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function num(n) { return n == null ? "—" : Number(n).toLocaleString("en-US"); }
function fmtSec(v) { return v == null ? "—" : `${Number(v).toFixed(1)}s`; }
function shortTime(iso) {
  if (!iso) return "—";
  const m = String(iso).match(/T(\d\d:\d\d:\d\d)/);
  return m ? m[1] : String(iso).slice(0, 19);
}
function hhmmss(ts) {
  if (!ts) return "—";
  const d = new Date(Number(ts) * 1000);
  return d.toTimeString().slice(0, 8);
}
function bytes(n) {
  if (n == null) return "—";
  const u = ["B", "KB", "MB", "GB"];
  let v = Number(n), i = 0;
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(i ? 1 : 0)} ${u[i]}`;
}
function statusChip(status) {
  const map = {
    ok: ["ok", "成功"], running: ["warn", "运行中"], stopped: ["mute", "已停止"],
    failed: ["bad", "失败"], ready: ["ok", "ready"], "not-wired": ["warn", "not-wired"],
    skipped: ["mute", "skipped"], "blocked-vendor": ["bad", "blocked-vendor"],
    resolved: ["ok", "resolved"], partial: ["warn", "partial"], blocked: ["bad", "blocked"],
    unknown: ["mute", "未知"],
  };
  const [cls, label] = map[status] || ["mute", status || "—"];
  return `<span class="chip ${cls}">${esc(label)}</span>`;
}
function stateBadges(stats) {
  return COMPONENT_STATES.map((s) =>
    `<span class="state-badge ${s.cls}" title="${esc(s.key)}"><i>${esc(s.key)}</i><b>${num(stats[s.field] || 0)}</b></span>`).join("");
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  let data = null;
  try { data = await res.json(); } catch (_) { data = { ok: false, error: "响应不是 JSON" }; }
  if (!res.ok && (!data || data.ok !== false)) throw new Error(data && data.error ? data.error : `HTTP ${res.status}`);
  return data;
}

/* --------------------------------------------------------------- navigation */
function setView(view) {
  state.view = view;
  $$(".nav-item").forEach((b) => b.classList.toggle("is-active", b.dataset.view === view));
  $$(".view").forEach((v) => v.classList.toggle("is-active", v.id === `view-${view}`));
  const tasks = {
    overview: loadOverview, workflow: loadWorkflows, components: loadComponents,
    evidence: loadEvidence, assets: loadAssets, logs: loadLogRuns, trigger: loadTriggerMeta,
  };
  if (tasks[view]) tasks[view]().catch((e) => console.error(view, e));
}

/* ------------------------------------------------------------------ overview */
async function loadOverview() {
  const data = await api("/wapi/overview");
  state.overview = data;
  state.pinnedRun = data.pinnedRun ? data.pinnedRun.run_id : null;
  $("#overviewStamp").textContent = `刷新于 ${shortTime(data.generatedAt)}`;
  $("#railSuite").textContent = data.backends.suite.version || "—";
  $("#railPy").textContent = data.backends.python.ok ? (data.backends.python.version || "在线") : "离线";
  $("#railC").textContent = data.backends.c.ok ? (data.backends.c.version || "在线") : "离线";
  $("#verPy").textContent = data.backends.python.version || "—";
  $("#verC").textContent = data.backends.c.version || "—";
  $("#dotPy").className = data.backends.python.ok ? "ok" : "bad";
  $("#dotC").className = data.backends.c.ok ? "ok" : "bad";

  const cur = data.currentRun;
  $("#topRun").textContent = cur ? cur.run_id : "无运行记录";
  $("#topRunStatus").outerHTML = `<span id="topRunStatus" class="chip ${cur ? (cur.status === "ok" ? "ok" : cur.status === "failed" ? "bad" : "warn") : "mute"}">${cur ? (cur.status === "ok" ? "成功" : cur.status === "failed" ? "失败" : "运行中") : "空"}</span>`;
  $("#topDuration").textContent = cur ? fmtSec(cur.duration) : "—";
  $("#topEvents").textContent = cur ? num(cur.events) : "—";
  $("#topMode").textContent = cur
    ? `${cur.mode}${cur.engineCount ? ` · ${cur.engineCount} 引擎` : ""}${cur.processes ? ` / ${cur.processes} 进程` : ""}`
    : "—";

  const st = data.componentStats;
  const enginesReady = data.engines.filter((e) => e.status === "ready").length;
  $("#kpis").innerHTML = [
    kpi("引擎就绪", `${enginesReady}<small>/ ${data.engines.length}</small>`, data.engines.filter((e) => e.status !== "ready").map((e) => e.name).join(" · ") || "全部 venv 可用", enginesReady === data.engines.length ? "ok" : "bad"),
    kpi("组件", num(st.total), `${st.ready} ready · ${st.notWired} not-wired · ${st.skipped} skipped · ${st.blockedVendor} blocked-vendor`, "accent"),
    kpi("当前 run", esc(cur ? cur.run_id : "—"), cur ? `${cur.mode} · ${cur.status}${cur.pinned ? " · 常驻" : ""}` : "尚未运行", "accent"),
    kpi("耗时", cur ? fmtSec(cur.duration) : "—", cur ? `事件 ${num(cur.events)} 条` : "—", ""),
    kpi("后端", `${data.backends.python.ok ? "8787" : "8787 ✕"}<small>·</small>${data.backends.c.ok ? "8788" : "8788 ✕"}`, `py ${data.backends.python.version || "—"} · c ${data.backends.c.version || "—"}`, data.backends.python.ok && data.backends.c.ok ? "ok" : "bad"),
  ].join("");

  $("#compSummary").innerHTML = `<span class="state-line-label">${esc(data.componentSummary)}</span>${stateBadges(st)}`;

  $("#engineSub").textContent = `${enginesReady}/${data.engines.length} venv 就绪 · ${st.total} 组件`;
  $("#engineList").innerHTML = data.engines.map((e, i) => `
    <div class="engine-row">
      <span class="engine-idx">${String(i + 1).padStart(2, "0")}</span>
      <div class="engine-main">
        <b>${esc(e.label)} <span style="color:var(--dim);font-size:11px;font-family:var(--mono)">${esc(e.name)}</span></b>
        <span>${esc(e.entry)}</span>
      </div>
      <div class="engine-side">
        ${statusChip(e.status === "ready" ? "ready" : "not-wired")}
        <span>${e.components} 组件</span>
      </div>
    </div>`).join("");

  $("#recentRuns").innerHTML = data.recentRuns.length ? data.recentRuns.map((r) => `
    <div class="run-row${r.pinned ? " is-pinned" : ""}" data-run="${esc(r.run_id)}">
      <div><b>${esc(r.run_id)}</b><span>${shortTime(r.started_at)} · ${esc(r.mode)}${r.pinned ? " · 常驻" : ""}</span></div>
      <div class="right">${statusChip(r.status)}</div>
      <div class="right"><span>${fmtSec(r.duration)}</span></div>
    </div>`).join("") : `<div class="empty-state">runs/ 目录暂无记录</div>`;
  $$("#recentRuns .run-row").forEach((row) => row.addEventListener("click", () => {
    state.runId = row.dataset.run;
    setView("evidence");
  }));

  renderRelease(data.release);
  renderVendorOverview(data.vendor);
}

function notice(tone, title, body) {
  return `<div class="notice ${tone}"><b>${esc(title)}</b><p>${esc(body || "—")}</p></div>`;
}

function renderRelease(rel) {
  if (!rel) return;
  $("#releaseSub").textContent = `${rel.docPath || ""}${rel.verifiedAt ? " · " + rel.verifiedAt : ""}`;
  const pkgs = (rel.packages || []).slice().sort((a, b) => a.bytes - b.bytes);
  $("#releaseGrid").innerHTML = pkgs.map((p) => `
    <div class="pkg">
      <div class="pkg-head"><b>${esc((p.name || "").replace("rocogi-0.4.0-", "").replace(".zip", ""))}</b><span>${p.files ? num(p.files) + " 文件" : ""}</span></div>
      <div class="pkg-size">${bytes(p.bytes)}</div>
      <code title="${esc(p.sha256 || "")}">sha256 ${esc(p.sha8 || "—")}…</code>
      <p>${esc(p.contents || p.sizeLabel || "")}</p>
    </div>`).join("");
  $("#releaseNotes").innerHTML = (rel.highlights || []).map((h) => notice("mute", "发布验证", h)).join("");
}

function renderVendorOverview(v) {
  if (!v) return;
  const s = v.summary || {};
  $("#vendorSub").textContent = `${s.total} 仓 · ${s.resolved} resolved / ${s.partial} partial / ${s.blocked} blocked`;
  $("#vendorSummary").innerHTML = [
    `<span class="state-badge ok"><i>resolved</i><b>${num(s.resolved)}</b></span>`,
    `<span class="state-badge warn"><i>partial</i><b>${num(s.partial)}</b></span>`,
    `<span class="state-badge bad"><i>blocked</i><b>${num(s.blocked)}</b></span>`,
    `<span class="vendor-bytes">${s.total} 仓 · ${bytes(s.totalBytes)}</span>`,
  ].join("");
  const notes = (v.blockedItems || []).map((b) => notice("bad", `blocked 项 · ${b.repo}`, b.reason));
  (v.pendingReboot || []).forEach((p) => {
    const pre = p.preRebootResult ? ` · 重启前 ${p.preRebootResult.pass} pass / ${p.preRebootResult.fail} fail` : "";
    notes.push(notice("warn", `待重启生效 · ${p.repo}`, `${p.note || ""}${p.script ? ` · 重启后跑 ${p.script}` : ""}${pre}`));
  });
  notes.push(notice("mute", "口径区分", v.note));
  $("#vendorNotices").innerHTML = notes.join("");
}

function kpi(label, value, note, tone) {
  return `<div class="kpi ${tone || ""}"><i>${esc(label)}</i><b>${value}</b><span>${esc(note)}</span></div>`;
}

/* ----------------------------------------------------------------- workflows */
async function loadWorkflows() {
  const data = await api("/wapi/workflows");
  state.workflows = data.workflows || [];
  state.nodeCatalog = data.nodeCatalog || {};
  if (!state.workflows.length) {
    $("#dag").innerHTML = "";
    $("#workflowTabs").innerHTML = "";
    $("#nodeInspector").innerHTML = `<div class="empty">8787 未返回工作流。</div>`;
    return;
  }
  if (!state.wfId || !state.workflows.some((w) => w.id === state.wfId)) state.wfId = state.workflows[0].id;
  $("#workflowTabs").innerHTML = state.workflows.map((w) =>
    `<button data-wf="${esc(w.id)}" class="${w.id === state.wfId ? "is-on" : ""}">${esc(w.name)}</button>`).join("");
  $$("#workflowTabs button").forEach((b) => b.addEventListener("click", () => {
    state.wfId = b.dataset.wf;
    $$("#workflowTabs button").forEach((x) => x.classList.toggle("is-on", x === b));
    renderWorkflow();
  }));
  renderWorkflow();
}

function nodeColor(type) {
  const cat = state.nodeCatalog[type];
  return (cat && cat.accent) || "#5fd6c0";
}
function nodeLabel(node) {
  return node.config && node.config.label ? node.config.label : (state.nodeCatalog[node.type] ? state.nodeCatalog[node.type].title : node.id);
}

function renderWorkflow() {
  const wf = state.workflows.find((w) => w.id === state.wfId);
  if (!wf) return;
  const nodes = wf.graph.nodes || [];
  const edges = wf.graph.edges || [];
  const W = 184, H = 58, PAD = 34;
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  nodes.forEach((n) => {
    minX = Math.min(minX, n.x ?? 0); minY = Math.min(minY, n.y ?? 0);
    maxX = Math.max(maxX, (n.x ?? 0) + W); maxY = Math.max(maxY, (n.y ?? 0) + H);
  });
  const ox = PAD - minX, oy = PAD - minY;
  const vbW = maxX - minX + PAD * 2, vbH = maxY - minY + PAD * 2;
  const pos = {};
  nodes.forEach((n) => { pos[n.id] = { x: (n.x ?? 0) + ox, y: (n.y ?? 0) + oy }; });

  const svg = $("#dag");
  svg.setAttribute("viewBox", `0 0 ${vbW} ${vbH}`);
  svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
  const edgeParts = edges.map((e, i) => {
    const a = pos[e.from], b = pos[e.to];
    if (!a || !b) return "";
    const x1 = a.x + W, y1 = a.y + H / 2, x2 = b.x, y2 = b.y + H / 2;
    const dx = Math.max(40, Math.abs(x2 - x1) * 0.5);
    const port = e.fromPort && e.fromPort !== "out" ? ` is-port-${e.fromPort}` : "";
    return `<path class="edge${port}" data-edge="${i}" data-from="${esc(e.from)}" data-to="${esc(e.to)}"
      marker-end="url(#arrow)" d="M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}" />`;
  }).join("");

  const nodeParts = nodes.map((n) => {
    const p = pos[n.id];
    const color = nodeColor(n.type);
    const label = String(nodeLabel(n)).slice(0, 14);
    return `<g class="node-box" data-node="${esc(n.id)}" transform="translate(${p.x},${p.y})">
      <rect class="body" width="${W}" height="${H}" rx="6" />
      <rect class="accent" width="3" height="${H - 18}" x="0" y="9" fill="${color}" />
      <text class="label" x="15" y="25">${esc(label)}</text>
      <text class="kind" x="15" y="43">${esc(n.type)}</text>
    </g>`;
  }).join("");

  svg.innerHTML = `<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="#3d4b4a"></path></marker></defs>${edgeParts}${nodeParts}`;

  // hover spotlight
  $$("#dag .node-box").forEach((g) => {
    const id = g.dataset.node;
    g.addEventListener("mouseenter", (ev) => {
      $$("#dag .edge").forEach((ed) => {
        const linked = ed.dataset.from === id || ed.dataset.to === id;
        ed.classList.toggle("is-hot", linked);
        ed.classList.toggle("is-dim", !linked);
      });
      $$("#dag .node-box").forEach((n) => n.classList.toggle("is-dim", n.dataset.node !== id));
      const node = nodes.find((n) => n.id === id);
      const cat = state.nodeCatalog[node.type] || {};
      const tip = $("#dagTip");
      tip.hidden = false;
      tip.innerHTML = `<b>${esc(nodeLabel(node))}</b><br><code>${esc(node.type)}</code><br>${esc(cat.categoryLabel || "未分类")} · ${esc(node.id)}`;
      posTip(ev, tip);
    });
    g.addEventListener("mousemove", (ev) => posTip(ev, $("#dagTip")));
    g.addEventListener("mouseleave", () => {
      $("#dagTip").hidden = true;
      $$("#dag .edge").forEach((ed) => ed.classList.remove("is-hot", "is-dim"));
      $$("#dag .node-box").forEach((n) => n.classList.remove("is-dim"));
    });
    g.addEventListener("click", () => {
      $$("#dag .node-box").forEach((n) => n.classList.toggle("is-sel", n === g));
      showNode(nodes.find((n) => n.id === id));
    });
  });

  const cats = {};
  nodes.forEach((n) => {
    const c = state.nodeCatalog[n.type] || { category: "other", categoryLabel: "其他", accent: "#5fd6c0" };
    cats[c.category] = c;
  });
  $("#nodeLegend").innerHTML = Object.values(cats).map((c) =>
    `<span><em style="background:${esc(c.accent)}"></em>${esc(c.categoryLabel)}</span>`).join("");
  $("#nodeInspector").innerHTML = `<div class="empty">选择节点查看类型、分类与配置。当前工作流：${esc(wf.name)}</div>`;
  $(".canvas-wrap").dataset.count = nodes.length;
}

function posTip(ev, tip) {
  const box = $(".canvas-wrap").getBoundingClientRect();
  const x = Math.min(ev.clientX - box.left + 16, box.width - tip.offsetWidth - 10);
  const y = Math.min(ev.clientY - box.top + 14, box.height - tip.offsetHeight - 10);
  tip.style.left = `${x}px`; tip.style.top = `${y}px`;
}

function showNode(node) {
  if (!node) return;
  const cat = state.nodeCatalog[node.type] || {};
  $("#nodeInspector").innerHTML = `
    <h4>${esc(nodeLabel(node))}</h4>
    <div class="type">${esc(node.type)}</div>
    <div class="meta">
      <span class="chip mute">${esc(cat.categoryLabel || "未分类")}</span>
      <span class="chip mute">端口 out</span>
      ${cat.description ? `<span class="chip mute" title="${esc(cat.description)}">有说明</span>` : ""}
    </div>
    <dl>
      <dt>节点 id</dt><dd>${esc(node.id)}</dd>
      <dt>坐标</dt><dd>${node.x ?? "—"}, ${node.y ?? "—"}</dd>
      <dt>分类</dt><dd>${esc(cat.category || "—")}</dd>
    </dl>
    <pre>${esc(JSON.stringify(node.config ?? {}, null, 2))}</pre>`;
}

/* ---------------------------------------------------------------- components */
async function loadComponents() {
  const data = await api("/wapi/components");
  state.comps = data;
  const st = data.stats;
  $("#compKpis").innerHTML = [
    kpi("组件总数", num(st.total), "components.toml · 7 引擎", "accent"),
    kpi("ready", num(st.ready), "venv 可用且已接线", "ok"),
    kpi("not-wired", num(st.notWired), "有源码但未接入运行时", ""),
    kpi("skipped", num(st.skipped), "明确跳过并附原因", ""),
    kpi("blocked-vendor", num(st.blockedVendor), "外部前置未满足", "bad"),
  ].join("");
  $("#compStates").innerHTML = stateBadges(st) + `<span class="state-total">共 ${num(st.total)} 件 · 四档不折叠</span>`;
  renderComponents();
  await loadVendorPanel();
}

function renderComponents() {
  const data = state.comps;
  if (!data) return;
  $("#compGrid").innerHTML = data.groups.map((g) => {
    const rows = g.components.map((c) => {
      const hide = state.compFilter === "issue" && c.status === "ready";
      const reason = c.reason || c.note || "";
      const detail = `
        <div class="detail"><dl>
          <dt>原因</dt><dd>${esc(reason || "—")}</dd>
          <dt>说明</dt><dd>${esc(c.note || "—")}</dd>
          <dt>status</dt><dd>${esc(c.declared || "—")}${c.declared && c.declared !== c.status ? ` → ${esc(c.status)}` : ""}</dd>
          <dt>implemented</dt><dd>${c.implemented ? "true" : "false"}</dd>
          <dt>依赖</dt><dd>${esc((c.deps || []).join(", ") || "—")}</dd>
          <dt>入口</dt><dd>${esc(c.entry || "—")}</dd>
          <dt>配置</dt><dd>${esc(c.config || "—")}</dd>
          <dt>功能</dt><dd>${esc((c.usedBy || []).join(", ") || "未在 8787 usage 中出现")}</dd>
        </dl></div>`;
      return `<div class="comp-row ${hide ? "is-hidden" : ""}" data-status="${esc(c.status)}" title="${esc(reason)}">
        <div class="line"><b>${esc(c.id)}</b><span class="impl ${c.implemented ? "ok" : "mute"}">${c.implemented ? "impl" : "no-impl"}</span>${statusChip(c.status)}</div>${detail}</div>`;
    }).join("");
    const count = g.counts.total;
    const bits = [
      ["ready", g.counts.ready, "ok"], ["not-wired", g.counts.notWired, "warn"],
      ["skipped", g.counts.skipped, "mute"], ["blocked-vendor", g.counts.blockedVendor, "bad"],
    ].filter(([, n]) => n > 0).map(([k, n, cls]) => `<span class="mini ${cls}">${esc(k)} ${n}</span>`).join("");
    const groupHidden = state.compFilter === "issue" && g.counts.ready === count;
    return `<div class="comp-group ${groupHidden ? "is-hidden" : ""}">
      <div class="comp-head">
        <b><em style="background:${ENGINE_COLORS[g.engine] || "#5fd6c0"}"></em>${esc(g.labelFull)}</b>
        <span>${esc(g.engine)} · ${bits} <em class="total">${count}</em></span>
      </div>${rows}</div>`;
  }).join("");
  $$("#compGrid .comp-row").forEach((row) => row.addEventListener("click", () => row.classList.toggle("is-open")));
}
$$("#compFilter button").forEach((b) => b.addEventListener("click", () => {
  state.compFilter = b.dataset.filter;
  $$("#compFilter button").forEach((x) => x.classList.toggle("is-on", x === b));
  renderComponents();
}));

async function loadVendorPanel() {
  const v = state.vendor || (state.vendor = await api("/wapi/vendor"));
  const s = v.summary || {};
  $("#vendorPanelSub").textContent = `${s.total} 仓 · ${s.resolved} resolved / ${s.partial} partial / ${s.blocked} blocked（仓级）`;
  const suiteBlocked = state.comps ? state.comps.stats.blockedVendor : "—";
  $("#vendorPanelNote").textContent = `${v.note} 当前 suite 组件 blocked-vendor ${suiteBlocked} 条，与仓级 0 blocked 不可混用。`;
  const rows = (v.repos || []).map((r) => {
    const res = r.resolution || {};
    const desc = res.stillBlocked || res.note || res.done || "";
    return `<tr>
      <td><b>${esc(r.repo)}</b></td>
      <td>${statusChip(r.status)}</td>
      <td class="mono">${esc(r.license || "—")}</td>
      <td class="mono">${r.size ? `${num(r.size.files)} / ${bytes(r.size.bytes)}` : "—"}</td>
      <td class="vdesc">${esc(desc)}</td></tr>`;
  }).join("");
  $("#vendorPanel").innerHTML = `<thead><tr><th>repo</th><th>resolution</th><th>license</th><th>files / size</th><th>说明</th></tr></thead><tbody>${rows}</tbody>`;
  const notes = (v.blockedItems || []).map((b) => notice("bad", `blocked 项 · ${b.repo}`, b.reason));
  (v.pendingReboot || []).forEach((p) => {
    const pre = p.preRebootResult ? ` · 重启前 ${p.preRebootResult.pass} pass / ${p.preRebootResult.fail} fail` : "";
    notes.push(notice("warn", `待重启生效 · ${p.repo}`, `${p.note || ""}${p.script ? ` · 重启后跑 ${p.script}` : ""}${pre}`));
  });
  $("#vendorPanelNotices").innerHTML = notes.join("");
}

/* ------------------------------------------------------------------- evidence */
async function loadEvidence() {
  const data = await api("/wapi/runs?limit=80");
  state.runs = data.runs || [];
  if (!state.runs.length) {
    $("#runSelect").innerHTML = "";
    $("#timeline").innerHTML = `<div class="empty-state">暂无 run 记录</div>`;
    return;
  }
  if (!state.runId || !state.runs.some((r) => r.run_id === state.runId)) {
    state.runId = (state.pinnedRun && state.runs.some((r) => r.run_id === state.pinnedRun)) ? state.pinnedRun : state.runs[0].run_id;
  }
  $("#runSelect").innerHTML = state.runs.map((r) =>
    `<option value="${esc(r.run_id)}" ${r.run_id === state.runId ? "selected" : ""}>${esc(r.run_id)} · ${esc(r.status)}</option>`).join("");
  await showRun(state.runId);
}

async function showRun(runId) {
  state.runId = runId;
  const d = await api(`/wapi/runs/${encodeURIComponent(runId)}`);
  const m = d.manifest || {};
  $("#manifestSub").textContent = d.summary.status;
  $("#manifestFacts").innerHTML = [
    ["run_id", esc(m.run_id || runId)],
    ["模式", esc(m.mode || "—")],
    ["开始", esc(shortTime(m.started_at))],
    ["config sha", `<span title="${esc((m.config || {}).sha256 || "")}">${esc(((m.config || {}).sha256 || "—").slice(0, 16))}</span>`],
    ["快照字节", num(m.configSnapshotBytes)],
    ["组件", `${(m.components || []).length} 条`],
    ["引擎版本", esc(Object.entries(m.engines || {}).map(([k, v]) => `${k}:${v.python || v.status || "—"}`).join(" · "))],
    ["事件", `${num(d.events.length)} 条`],
  ].map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}</dd>`).join("");

  const engines = Object.entries((d.metrics || {}).engines || {});
  $("#metricTable").innerHTML = `<thead><tr><th>engine</th><th>state</th><th>pid</th><th>restarts</th><th>exit</th></tr></thead>
    <tbody>${engines.map(([name, s]) => `<tr>
      <td>${esc(name)}</td><td>${esc(s.state || "—")}</td><td>${esc(s.pid ?? "—")}</td>
      <td>${s.restarts ?? 0}${s.restart_seconds && s.restart_seconds.length ? ` (${s.restart_seconds.map((x) => Number(x).toFixed(2)).join("/")})` : ""}</td>
      <td>${esc(s.exitcode ?? "—")}</td></tr>`).join("")}</tbody>`;

  renderTimeline(d.events || []);
}

let eventFilter = "all";
state.events = [];
function renderTimeline(events) {
  state.events = events;
  const engines = Array.from(new Set(events.map((e) => e.engine).filter(Boolean)));
  $("#eventSub").textContent = `${events.length} 条`;
  $("#eventFilters").innerHTML = [`<button data-f="all" class="${eventFilter === "all" ? "is-on" : ""}">全部</button>`]
    .concat(engines.map((e) => `<button data-f="${esc(e)}" class="${eventFilter === e ? "is-on" : ""}">${esc(e)}</button>`)).join("");
  $$("#eventFilters button").forEach((b) => b.addEventListener("click", () => {
    eventFilter = b.dataset.f;
    renderTimeline(state.events);
  }));
  const rows = events.filter((e) => eventFilter === "all" || e.engine === eventFilter);
  $("#timeline").innerHTML = rows.length ? rows.map((e) => {
    const type = e.type || "event";
    let body = "";
    if (type === "result") {
      body = `<span class="result">${esc(JSON.stringify(e.result).slice(0, 220))}</span>`;
    } else if (type === "error") {
      body = `<em>${esc(e.error)}</em>`;
    } else if (type === "ready") {
      body = `components ${esc((e.components || []).length)} · python ${esc(e.python || "—")}`;
    } else {
      body = esc(JSON.stringify(Object.fromEntries(Object.entries(e).filter(([k]) => !["ts", "engine", "type", "run_id"].includes(k)))).slice(0, 200));
    }
    return `<div class="tl-row"><span class="t">${hhmmss(e.ts)}</span><span class="eng">${esc(e.engine || "—")}</span>
      <span class="body"><span class="tl-type ${esc(type)}">${esc(type)}</span>${body}</span></div>`;
  }).join("") : `<div class="empty-state">没有符合筛选的事件</div>`;
}
$("#runSelect").addEventListener("change", (ev) => showRun(ev.target.value).catch((e) => console.error(e)));

/* --------------------------------------------------------------------- assets */
async function loadAssets() {
  const data = await api("/wapi/assets");
  state.assets = data;
  renderAssets();
}

function renderAssets() {
  const data = state.assets || {};
  const man = data.manifest || {};
  const stats = man.stats || {};
  const v = data.verify;
  const points = (stats.points || {}).pointCount;
  const feats = (stats.features || {}).featureCount;
  const hashes = v ? `${v.hashes.checked}/${v.hashes.checked + v.hashes.failed}` : "未校验";
  $("#assetKpis").innerHTML = [
    kpi("地图点位", num(points), `期望 9224 · ${(stats.points || {}).markerTypes || "—"} 标记类型`, points === 9224 ? "ok" : "bad"),
    kpi("SIFT 特征", num(feats), `shape ${v && v.mmap ? v.mmap.shape.join(" × ") : "94992 × 128"}`, feats === 94992 ? "ok" : "bad"),
    kpi("哈希", hashes, v ? `${v.hashes.failed} 失败 · ${v.hashes.checked} 已校验` : "点击重新校验", v && v.hashes.failed === 0 ? "ok" : ""),
    kpi("mmap 加载", v ? `${Number(v.mmap.mmapSeconds).toFixed(4)}<small>s</small>` : "—", "预算 2.0s", v && v.mmap.ok ? "ok" : ""),
    kpi("总体", v ? (v.ok ? "通过" : "未通过") : "—", v ? `校验于 ${shortTime(v.cachedAt)} · ${v.seconds}s` : "无缓存结果", v && v.ok ? "ok" : "bad"),
  ].join("");
  $("#assetSub").textContent = man.generated_at ? `生成于 ${shortTime(man.generated_at)}` : "读取 assets/manifest.json";
  const rows = (man.assets || []).map((a) => `<tr>
    <td class="kind">${esc(a.kind)}</td>
    <td class="mono">${esc(a.path)}</td>
    <td class="mono">${bytes(a.bytes)}</td>
    <td class="mono hash">${esc((a.sha256 || "—").slice(0, 20))}…</td></tr>`).join("");
  const extra = (man.assets || []).some((a) => !a.sha256) ? `<tr><td class="kind">templates</td><td class="mono">assets/templates</td><td class="mono">${bytes(92018)}</td><td class="mono hash">按目录计数，无单哈希</td></tr>` : "";
  $("#assetTable").innerHTML = `<thead><tr><th>kind</th><th>path</th><th>bytes</th><th>sha256</th></tr></thead><tbody>${rows}${extra}</tbody>`;
}

$("#verifyAssets").addEventListener("click", async (ev) => {
  const btn = ev.currentTarget;
  btn.disabled = true; btn.textContent = "校验中…";
  try {
    await api("/wapi/assets/verify", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    await loadAssets();
  } catch (e) {
    $("#assetSub").textContent = `校验失败：${e.message}`;
  } finally {
    btn.disabled = false; btn.textContent = "重新校验";
  }
});

/* ----------------------------------------------------------------------- logs */
async function loadLogRuns() {
  if (!state.runs.length) {
    const data = await api("/wapi/runs?limit=80");
    state.runs = data.runs || [];
  }
  const select = $("#logRun");
  if (!state.runs.length) { select.innerHTML = ""; return; }
  if (!state.runId || !state.runs.some((r) => r.run_id === state.runId)) {
    state.runId = (state.pinnedRun && state.runs.some((r) => r.run_id === state.pinnedRun)) ? state.pinnedRun : state.runs[0].run_id;
  }
  select.innerHTML = state.runs.map((r) =>
    `<option value="${esc(r.run_id)}" ${r.run_id === state.runId ? "selected" : ""}>${esc(r.run_id)}</option>`).join("");
  await loadLogEngines(state.runId);
}

async function loadLogEngines(runId) {
  const detail = await api(`/wapi/runs/${encodeURIComponent(runId)}`);
  const engines = (detail.logs || []).map((l) => l.engine);
  const sel = $("#logEngine");
  sel.innerHTML = engines.length ? engines.map((e) => `<option value="${esc(e)}">${esc(e)}</option>`).join("") : "";
  if (state.log.running) stopLogStream();
  state.log.offset = 0;
  state.log.runId = runId;
  state.log.engine = engines[0] || null;
  $("#stream").innerHTML = engines.length ? "" : `<div class="meta">该 run 没有 engines 日志文件。</div>`;
  $("#logState").textContent = engines.length ? "待开始" : "无日志";
  $("#logOffset").textContent = engines.length ? `0 / ${engines.length} 引擎` : "";
}

$("#logRun").addEventListener("change", async (ev) => {
  await loadLogEngines(ev.target.value);
});
$("#logEngine").addEventListener("change", (ev) => {
  state.log.engine = ev.target.value;
  state.log.offset = 0;
  $("#stream").innerHTML = "";
  $("#logState").textContent = "待开始";
});
$("#logToggle").addEventListener("click", () => {
  if (state.log.running) stopLogStream(); else startLogStream();
});
$("#logClear").addEventListener("click", () => {
  $("#stream").innerHTML = "";
  state.log.lines = 0;
});

function startLogStream() {
  if (!state.log.engine || !state.log.runId) return;
  state.log.running = true;
  $("#logToggle").textContent = "暂停";
  $("#logState").textContent = "流式中";
  pollLog();
  state.log.timer = setInterval(pollLog, 1000);
}
function stopLogStream() {
  state.log.running = false;
  clearInterval(state.log.timer);
  state.log.timer = null;
  $("#logToggle").textContent = "开始流式";
  $("#logState").textContent = "已暂停";
}
async function pollLog() {
  const { runId, engine } = state.log;
  if (!runId || !engine) return;
  try {
    const data = await api(`/wapi/runs/${encodeURIComponent(runId)}/logs/${encodeURIComponent(engine)}?offset=${state.log.offset}`);
    state.log.offset = data.nextOffset;
    appendLogLines(data.lines || []);
    $("#logState").textContent = `流式中 · ${engine} · ${state.log.lines} 行`;
    $("#logOffset").textContent = `offset ${num(data.nextOffset)} / ${num(data.size)} bytes`;
  } catch (e) {
    $("#logState").textContent = `读取失败：${e.message}`;
  }
}
function appendLogLines(lines) {
  const box = $("#stream");
  const frag = document.createDocumentFragment();
  lines.forEach((e) => {
    const div = document.createElement("div");
    div.className = `ln is-new${e.type === "error" ? " is-error" : ""}`;
    const payload = Object.fromEntries(Object.entries(e).filter(([k]) => !["ts", "engine", "type", "run_id"].includes(k)));
    div.innerHTML = `<span class="ts">${hhmmss(e.ts)}</span><span class="en">${esc(e.engine || "")}</span>
      <span class="ty">${esc(e.type || "")}</span><span class="py">${esc(JSON.stringify(payload).slice(0, 300))}</span>`;
    frag.appendChild(div);
  });
  if (lines.length) {
    box.appendChild(frag);
    state.log.lines += lines.length;
    box.scrollTop = box.scrollHeight;
  }
}

/* -------------------------------------------------------------------- trigger */
const CHAIN_ROWS = [
    { chain: "sift_locate", title: "SIFT 定位", cmd: "rocogi-suite call sift locate", desc: "在 6144×5888 规范空间用 SIFT 匹配定位，输出 search state / center / confidence。" },
  { chain: "sift_route", title: "路线规划", cmd: "rocogi-suite call sift route", desc: "按 collectible mark types 规划最近邻采集路线，输出点位与折线。" },
  { chain: "scheduler_fsm", title: "状态机", cmd: "rocogi-suite call scheduler fsm", desc: "跑 AutoCapture 捕捉状态机的 start/pause/resume/stop 轨迹。" },
  { chain: "battle_decide", title: "对战决策", cmd: "rocogi-suite call battle responder", desc: "NRC_AI MCTS 决策，返回行动序列与胜率。" },
];

async function loadTriggerMeta() {
  $("#chainList").innerHTML = CHAIN_ROWS.map((c) => `
    <div class="chain-row">
      <div><b>${esc(c.title)}</b><span class="cmd">${esc(c.cmd)}</span></div>
      <p>${esc(c.desc)}</p>
      <button class="primary" data-chain="${esc(c.chain)}">执行</button>
    </div>`).join("");
  $$("#chainList button[data-chain]").forEach((b) => b.addEventListener("click", () => fire(b.dataset.chain, b)));
}

async function fire(chain, btn) {
  const label = btn.textContent;
  btn.disabled = true; btn.textContent = "执行中…";
  $("#triggerSub").textContent = `${chain} · 运行中`;
  $("#triggerJson").textContent = "…";
  try {
    const res = await api("/wapi/trigger", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ chain }),
    });
    $("#triggerJson").textContent = JSON.stringify(res, null, 2);
    $("#triggerSub").textContent = `${chain} · ${res.ok ? "成功" : "失败"} · ${fmtSec(res.seconds)} · run ${res.run_id}`;
    state.runs = [];
    await loadOverview().catch(() => {});
  } catch (e) {
    $("#triggerJson").textContent = JSON.stringify({ ok: false, error: e.message }, null, 2);
    $("#triggerSub").textContent = `${chain} · 失败`;
  } finally {
    btn.disabled = false; btn.textContent = label;
  }
}

$("#runSuite").addEventListener("click", async (ev) => {
  const btn = ev.currentTarget;
  btn.disabled = true; btn.textContent = "运行中…";
  $("#triggerSub").textContent = "suite_run · 7 引擎 --once";
  try {
    const res = await api("/wapi/trigger", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ chain: "suite_run" }),
    });
    $("#triggerJson").textContent = JSON.stringify(res, null, 2);
    $("#triggerSub").textContent = `suite_run · run ${res.run_id} · ${res.events ?? "—"} 事件`;
    state.runs = [];
    await loadOverview().catch(() => {});
  } catch (e) {
    $("#triggerJson").textContent = JSON.stringify({ ok: false, error: e.message }, null, 2);
  } finally {
    btn.disabled = false; btn.textContent = "完整 run · 7 引擎";
  }
});

/* ---------------------------------------------------------------------- boot */
$$(".nav-item").forEach((b) => b.addEventListener("click", () => setView(b.dataset.view)));
$("#refresh").addEventListener("click", async () => {
  state.runs = [];
  await loadOverview().catch((e) => console.error(e));
  if (state.view !== "overview") setView(state.view);
});
setView("overview");
