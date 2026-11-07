// CDP audit: per-route render check with a fixed 1600x1000 viewport.
// Usage: node scripts/verify/cdp-audit2.mjs [base]   → 写 scripts/verify/cdp-audit2.json
const PORT = process.env.CDP_PORT || 9334;
const BASE = process.argv[2] || 'http://127.0.0.1:5173';
const ROUTES = [
  '/launcher', '/onedragon', '/realtime', '/workflows', '/runs', '/tracker',
  '/dex', '/pet', '/map', '/battle', '/pvp', '/resources', '/harness',
  '/engines', '/components', '/settings',
];

const targets = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const page = targets.find((t) => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
const events = [];

ws.addEventListener('message', (event) => {
  const msg = JSON.parse(event.data);
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg);
    pending.delete(msg.id);
    return;
  }
  if (msg.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(msg.params.type)) {
    events.push(`${msg.params.type}: ${msg.params.args.map((a) => a.value ?? a.description ?? a.type).join(' ').slice(0, 200)}`);
  } else if (msg.method === 'Runtime.exceptionThrown') {
    events.push(`exception: ${msg.params.exceptionDetails.text} ${(msg.params.exceptionDetails.exception?.description || '').slice(0, 200)}`);
  } else if (msg.method === 'Network.responseReceived' && msg.params.response.status >= 400) {
    events.push(`HTTP ${msg.params.response.status} ${msg.params.response.url.slice(0, 160)}`);
  }
});

const send = (method, params = {}) =>
  new Promise((resolve) => {
    const mid = ++id;
    pending.set(mid, resolve);
    ws.send(JSON.stringify({ id: mid, method, params }));
  });

await new Promise((resolve) => ws.addEventListener('open', resolve));
await send('Runtime.enable');
await send('Network.enable');
await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', {
  width: 1600, height: 1000, deviceScaleFactor: 1, mobile: false,
});

const probe = String.raw`(() => {
  const box = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { w: Math.round(r.width), h: Math.round(r.height), sw: el.scrollWidth, cw: el.clientWidth };
  };
  const offenders = [];
  const sider = document.querySelector('.sider-inner');
  if (sider) {
    const sb = sider.getBoundingClientRect();
    const walk = (node) => {
      for (const child of node.children) {
        const r = child.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) continue;
        if (r.right - sb.right > 1) {
          offenders.push({
            tag: child.tagName.toLowerCase(),
            cls: String(child.className || '').slice(0, 70),
            w: Math.round(r.width),
            right: Math.round(r.right),
            text: (child.textContent || '').trim().slice(0, 50),
          });
        }
        if (offenders.length < 40) walk(child);
      }
    };
    walk(sider);
  }
  const main = document.querySelector('.main, .page');
  return {
    h1: document.querySelector('h1')?.textContent?.trim() || '',
    textLen: (main?.innerText || '').length,
    sider: box('.sider-inner'),
    siderOverflow: sider ? sider.scrollWidth - sider.clientWidth : 0,
    offenders: offenders.slice(0, 8),
    docOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    bodyOverflow: document.body.scrollWidth - document.body.clientWidth,
    cards: document.querySelectorAll('.panel, .card').length,
    buttons: document.querySelectorAll('button').length,
    canvases: document.querySelectorAll('canvas').length,
    svgs: document.querySelectorAll('svg').length,
    imgs: document.querySelectorAll('img').length,
    // Only a nearly empty page counts as "empty": sections legitimately say
    // "暂无进化链数据" / "暂无特性" while the page is fully populated.
    emptyText: (main?.innerText || '').length < 260 && /暂无|加载中|Loading/i.test((main?.innerText || '').slice(0, 400)),
  };
})()`;

const report = [];
for (const route of ROUTES) {
  events.length = 0;
  await send('Page.navigate', { url: BASE + route });
  await new Promise((r) => setTimeout(r, 2600));
  const res = await send('Runtime.evaluate', { expression: probe, returnByValue: true });
  const value = res.result?.result?.value || { error: 'evaluate failed' };
  report.push({ route, ...value, events: [...new Set(events)].slice(0, 8) });
  console.log(route, JSON.stringify({ h1: value.h1, textLen: value.textLen, siderOverflow: value.siderOverflow, docOverflow: value.docOverflow, cards: value.cards, buttons: value.buttons, empty: value.emptyText, events: value.events }));
}

await import('node:fs').then((fs) => fs.writeFileSync('scripts/verify/cdp-audit2.json', JSON.stringify(report, null, 2)));
ws.close();

