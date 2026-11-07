// Verify the screenshots captured by scripts/verify/make-shots.mjs correspond to real,
// populated pages (no vision model here, so assert on DOM facts).
const PORT = 9334;
const BASE = 'http://127.0.0.1:5173';
const API = 'http://127.0.0.1:8787';

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
const evaluate = async (expression) => {
  const res = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  return res.result?.result?.value;
};
const goto = async (route, wait = 2600) => {
  await send('Page.navigate', { url: BASE + route });
  await sleep(wait);
};

// dex drawer
await goto('/dex', 3000);
const dexClick = await evaluate(`(() => {
  const card = document.querySelector('.dex-grid')?.firstElementChild;
  card?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  return Boolean(card);
})()`);
await sleep(1600);
const dexState = await evaluate(`(() => {
  const text = document.body.innerText;
  return {
    hasDetail: /六维|生命|技能表/.test(text),
    drawer: Boolean(document.querySelector('[class*="drawer"], aside[class*="detail"]')),
    lines: text.split('\\n').filter(Boolean).length,
  };
})()`);
console.log('dex clicked', dexClick, dexState);

// map route plan
await goto('/map', 3000);
const mapClick = await evaluate(`(() => {
  const btn = [...document.querySelectorAll('button')].find(b => /规划|路线/.test(b.textContent));
  btn?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  return btn ? btn.textContent.trim() : null;
})()`);
await sleep(2500);
const mapState = await evaluate(`(() => {
  const text = document.body.innerText;
  return { plan: /点位|距离|清除/.test(text), points: (text.match(/\\d+\\s*点位/) || [])[0] || null };
})()`);
console.log('map button', mapClick, mapState);

// battle result
await goto('/battle', 2600);
const battleClick = await evaluate(`(() => {
  const btn = [...document.querySelectorAll('button')].find(b => b.textContent.includes('开始推演'));
  btn?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  return Boolean(btn);
})()`);
await sleep(10000);
const battleState = await evaluate(`(() => {
  const text = document.body.innerText;
  return { result: /RESULT|回合/.test(text), winner: (text.match(/(胜利|平局|失败)/) || [])[0] || null };
})()`);
console.log('battle clicked', battleClick, battleState);

// realtime live frame
await fetch(`${API}/api/demo/scene`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scene: 'battle_polluted' }) });
await fetch(`${API}/api/realtime/start`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
await goto('/realtime', 4200);
const liveState = await evaluate(`(() => {
  const img = document.querySelector('img.live-image');
  return { hasImg: Boolean(img), w: img?.naturalWidth || 0, src: (img?.getAttribute('src') || '').slice(0, 40) };
})()`);
console.log('realtime live', liveState);
await fetch(`${API}/api/realtime/stop`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
await fetch(`${API}/api/demo/scene`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scene: 'auto' }) });

// tracker minimap preview
await fetch(`${API}/api/tracker/start`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
await goto('/tracker', 4000);
const trackerState = await evaluate(`(() => {
  const img = [...document.querySelectorAll('img')].find(i => (i.getAttribute('src') || '').includes('/api/tracker/artifact'));
  const text = document.body.innerText;
  return { preview: Boolean(img), w: img?.naturalWidth || 0, located: /LOCATED|置信度/.test(text) };
})()`);
console.log('tracker', trackerState);
await fetch(`${API}/api/tracker/stop`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });

ws.close();
