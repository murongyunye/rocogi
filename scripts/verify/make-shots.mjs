// Deliverable screenshots for README (docs/screenshots/*.png).
// Usage: node scripts/verify/make-shots.mjs [outDir]   (从仓库根目录运行)
// Captures the running Web UI at 1600x1000 through the CDP endpoint on 9334.
import fs from 'node:fs';
import path from 'node:path';

const PORT = process.env.CDP_PORT || 9334;
const BASE = process.env.WEB_BASE || 'http://127.0.0.1:5173';
const API = process.env.API_BASE || 'http://127.0.0.1:8787';
const OUT = process.argv[2] || 'docs/screenshots';

const targets = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const page = targets.find((t) => t.type === 'page' && !t.url.startsWith('devtools'));
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
ws.addEventListener('message', (event) => {
  const msg = JSON.parse(event.data.toString());
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg);
    pending.delete(msg.id);
  }
});
const send = (method, params = {}) =>
  new Promise((resolve) => {
    const next = ++id;
    pending.set(next, resolve);
    ws.send(JSON.stringify({ id: next, method, params }));
  });
await new Promise((r) => ws.addEventListener('open', r));

await send('Emulation.setDeviceMetricsOverride', { width: 1600, height: 1000, deviceScaleFactor: 1, mobile: false });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function evaluate(expression) {
  const res = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  return res.result?.result?.value;
}

async function goto(route, waitMs = 2400) {
  await send('Page.navigate', { url: BASE + route });
  await sleep(waitMs);
}

async function shot(name) {
  const res = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  const file = path.join(OUT, name);
  fs.writeFileSync(file, Buffer.from(res.result.data, 'base64'));
  const kb = Math.round(fs.statSync(file).size / 1024);
  console.log(`saved ${file} (${kb} KB)`);
}

async function api(pathname, body, method = 'POST') {
  const res = await fetch(API + pathname, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  return res.json();
}

fs.mkdirSync(OUT, { recursive: true });

// --- launcher -------------------------------------------------------------
await goto('/launcher', 2600);
await shot('00-launcher.png');

// --- workflow list + editor ----------------------------------------------
await goto('/workflows', 2600);
await shot('01-workflows.png');

await goto('/workflows/wf_demo_catch', 3200);
await shot('02-editor.png');

// --- resource map ---------------------------------------------------------
await goto('/map', 3200);
await evaluate(`(() => {
  const btns = [...document.querySelectorAll('button')].filter(b => b.textContent.includes('规划'));
  btns[0]?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  return btns.length;
})()`);
await sleep(1800);
await shot('03-map.png');

// --- realtime with a polluted battle on screen ---------------------------
await api('/api/demo/scene', { scene: 'battle_polluted' });
await api('/api/realtime/start', {});
await goto('/realtime', 4200);
await shot('04-realtime.png');
await api('/api/realtime/stop', {});
await api('/api/demo/scene', { scene: 'auto' });

// --- one dragon -----------------------------------------------------------
await goto('/onedragon', 2600);
await shot('05-onedragon.png');

// --- tracker with a live minimap preview ---------------------------------
await api('/api/tracker/start', {});
await goto('/tracker', 4200);
await shot('06-tracker.png');
await api('/api/tracker/stop', {});

// --- battle lab with a finished simulation -------------------------------
await goto('/battle', 2600);
await evaluate(`(() => {
  const btn = [...document.querySelectorAll('button')].find(b => b.textContent.includes('开始推演'));
  btn?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  return Boolean(btn);
})()`);
await sleep(9000);
await shot('07-battle.png');

// --- run evidence ---------------------------------------------------------
const runs = await (await fetch(`${API}/api/runs?limit=5`)).json();
const latest = runs.find((r) => r.status === 'succeeded') || runs[0];
if (latest) {
  await goto(`/runs/${latest.id}`, 3200);
  await shot('08-run-detail.png');
} else {
  console.log('no runs yet, skipped 08-run-detail.png');
}

// --- dex with the detail drawer open -------------------------------------
await goto('/dex', 3000);
// 卡片是 .dex-grid 的直接子元素（DexView.vue 的 openPet），点开才会出现 .dex-drawer 详情抽屉
const dexOpened = await evaluate(`(() => {
  const card = document.querySelector('.dex-grid')?.firstElementChild;
  card?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  return Boolean(card);
})()`);
await sleep(1800);
console.log('dex drawer opened:', dexOpened, '→', await evaluate(`Boolean(document.querySelector('.dex-drawer'))`));
await shot('09-dex.png');

// --- components -----------------------------------------------------------
await goto('/components', 3000);
await shot('10-components.png');

// --- pvp ------------------------------------------------------------------
await goto('/pvp', 3200);
// open the PvP dataset panel for the first slot so the shot shows six stats,
// trait, usage bars and the skill pool (not just the empty roster).
await evaluate(`(() => {
  const btn = document.querySelector('.slot-main-btn');
  btn?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  return Boolean(btn);
})()`);
await sleep(1600);
await shot('11-pvp.png');

// --- pet ------------------------------------------------------------------
await goto('/pet', 3000);
await shot('12-pet.png');

ws.close();
