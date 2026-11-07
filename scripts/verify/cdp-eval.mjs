// Run an arbitrary JS expression (file arg) in the page and print the result.
// Usage: node scripts/verify/cdp-eval.mjs <exprFile> [url]
import fs from 'node:fs';

const PORT = process.env.CDP_PORT || 9334;
const exprFile = process.argv[2];
const url = process.argv[3];
const expression = fs.readFileSync(exprFile, 'utf8');

const targets = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const page = targets.find((t) => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
const events = [];
ws.addEventListener('message', (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) {
    pending.get(m.id)(m);
    pending.delete(m.id);
    return;
  }
  if (m.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(m.params.type)) {
    events.push(`${m.params.type}: ${m.params.args.map((a) => a.value ?? a.description).join(' ')}`);
  } else if (m.method === 'Runtime.exceptionThrown') {
    events.push(`exception: ${m.params.exceptionDetails.text} ${m.params.exceptionDetails.exception?.description ?? ''}`);
  }
});
const send = (method, params = {}) =>
  new Promise((r) => {
    const i = ++id;
    pending.set(i, r);
    ws.send(JSON.stringify({ id: i, method, params }));
  });
await new Promise((r) => ws.addEventListener('open', r));
await send('Runtime.enable');
await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1600, height: 1000, deviceScaleFactor: 1, mobile: false });
if (url) {
  await send('Page.navigate', { url });
  await new Promise((r) => setTimeout(r, 3000));
}
const res = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
console.log(JSON.stringify(res.result?.result?.value ?? res.result, null, 2));
if (events.length) console.log('EVENTS', JSON.stringify(events.slice(0, 10), null, 2));
ws.close();
