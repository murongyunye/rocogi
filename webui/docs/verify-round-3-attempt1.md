# 验证轮次 3

- 时间：2026-11-05 13:52:41
- 目标：`http://127.0.0.1:8800`
- 结论：**FAIL**（23/24 项通过）

| # | 检查项 | 请求 | 状态码 | 耗时 | 结果 | 说明 |
|---|---|---|---|---|---|---|
| 1 | 首页 HTML | `GET /` | 200 | 0.03s | PASS | index 含 7 段导航与 app.js |
| 2 | 样式 app.css | `GET /app.css` | 200 | 0.01s | PASS | 22092 bytes |
| 3 | 脚本 app.js | `GET /app.js` | 200 | 0.02s | PASS | 27670 bytes |
| 4 | 概览 /wapi/overview | `GET /wapi/overview` | 200 | 0.15s | PASS | 6 引擎 / 39 组件 / 1 最近 run |
| 5 | 组件图谱 /wapi/components | `GET /wapi/components` | 200 | 0.05s | PASS | 39 组件 / 6 组 / ready 36 skipped 3 not-wired 0 |
| 6 | 工作流 /wapi/workflows | `GET /wapi/workflows` | 200 | 0.07s | PASS | 4 工作流 / 36 节点 / 36 连线 / 23 节点类型 |
| 7 | 运行列表 /wapi/runs | `GET /wapi/runs?limit=40` | 200 | 0.03s | FAIL | 1 条 run |
| 8 | 运行详情 ui-20261105-135224 | `GET /wapi/runs/ui-20261105-135224` | 200 | 0.05s | PASS | 12 事件 / sha 715f320900 / 6 引擎指标 |
| 9 | 事件流 ui-20261105-135224 | `GET /wapi/runs/ui-20261105-135224/events?offset=0` | 200 | 0.01s | PASS | 12 行 / nextOffset 7070 |
| 10 | 日志流 ui-20261105-135224/sift | `GET /wapi/runs/ui-20261105-135224/logs/sift?offset=0` | 200 | 0.01s | PASS | engine=sift 2 行 / byte 956 |
| 11 | 日志增量语义 | `GET /wapi/runs/ui-20261105-135224/logs/sift?offset=956` | 200 | 0.01s | PASS | 二次读取 offset 落到 EOF，无重复行 |
| 12 | 资产清单 /wapi/assets | `GET /wapi/assets` | 200 | 0.03s | PASS | 点位 9224 / 特征 94992 / 清单 11 项 |
| 13 | 重新校验 POST /wapi/assets/verify | `POST /wapi/assets/verify` | 200 | 2.19s | PASS | 哈希 10 项失败 0 / mmap 0.0019s / ok=True |
| 14 | 桥接 8787 /api/meta | `GET /wapi/bridge?port=8787&path=/api/meta` | 200 | 0.06s | PASS | 8787 meta：workflowCount=4 pointCount=9224 |
| 15 | 桥接 8788 /api/health | `GET /wapi/bridge?port=8788&path=/api/health` | 200 | 0.0s | PASS | C 核心 0.2.0 uptime 32708562ms |
| 16 | 触发 SIFT 定位 | `POST /wapi/trigger` | 200 | 5.78s | PASS | status=ok resultKeys=4 run=call-20261105-135244 |
| 17 | 触发 路线规划 | `POST /wapi/trigger` | 200 | 3.08s | PASS | status=ok resultKeys=3 run=call-20261105-135250 |
| 18 | 触发 状态机 | `POST /wapi/trigger` | 200 | 3.43s | PASS | status=ok resultKeys=5 run=call-20261105-135253 |
| 19 | 触发 对战决策 | `POST /wapi/trigger` | 200 | 1.93s | PASS | status=ok resultKeys=6 run=call-20261105-135256 |
| 20 | 端到端 run --once | `POST /wapi/trigger` | 200 | 21.3s | PASS | run=ui-20261105-135258 events=12 21.22s |
| 21 | UI 运行列表出现新 run | `GET /wapi/runs?limit=40` | 200 | 0.08s | PASS | 新 run ui-20261105-135258 位于列表首位，events=12 |
| 22 | 新 run 事件可见 | `GET /wapi/runs/ui-20261105-135258/events?offset=0` | 200 | 0.02s | PASS | 12 条事件（['battle', 'capture', 'input', 'scheduler', 'sift', 'vision']） |
| 23 | 新 run 日志可见 | `GET /wapi/runs/ui-20261105-135258/logs/sift?offset=0` | 200 | 0.03s | PASS | engine=sift 2 行 |
| 24 | 概览当前 run 已切换 | `GET /wapi/overview` | 200 | 0.55s | PASS | 当前 run = ui-20261105-135258 |

## 关键响应片段

### 1. 首页 HTML

`GET /` → HTTP 200

```json
<!doctype html> <html lang="zh-CN"> <head> <meta charset="UTF-8" /> <meta name="viewport" content="width=device-width, initial-scale=1.0" /> <title>Rocogi 套件控制台</title> <link rel="stylesheet" href="/app.css" /> </head> <body> <div class="shell"> <aside class="rail"> <div class="brand"> <span class="…
```

### 2. 样式 app.css

`GET /app.css` → HTTP 200

```json
:root { --bg: #0a0c0d; --bg-2: #0e1112; --surface: #111516; --surface-2: #151a1b; --line: #202729; --line-2: #2b3437; --text: #e6eceb; --muted: #7d8a8d; --dim: #566265; --accent: #5fd6c0; --accent-dim: rgba(95, 214, 192, 0.14); --ok: #63cf9a; --warn: #e2ab53; --bad: #e06d60; --info: #7aa7d9; --mono:…
```

### 3. 脚本 app.js

`GET /app.js` → HTTP 200

```json
/* Rocogi 套件控制台 · 前端逻辑（无构建步骤） */ const $ = (sel, root = document) => root.querySelector(sel); const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel)); const state = { view: "overview", overview: null, workflows: [], nodeCatalog: {}, wfId: null, comps: null, compFilter: "all", run…
```

### 4. 概览 /wapi/overview

`GET /wapi/overview` → HTTP 200

```json
{"engines":6,"componentStats":{"total":39},"backends":{"python":"ok","c":"ok"}}
```

### 5. 组件图谱 /wapi/components

`GET /wapi/components` → HTTP 200

```json
{"groups": ["截图", "视觉", "输入", "定位", "对战", "调度"], "total": 39}
```

### 6. 工作流 /wapi/workflows

`GET /wapi/workflows` → HTTP 200

```json
{"ok": true, "workflows": [{"id": "wf_demo_catch", "name": "抓宠巡航 · 自动丢球", "description": "截图识别战斗与可捕捉精灵，普通战斗聚能、污染战斗逃跑，空闲时自动丢球。演示使用模拟游戏窗口，可切换到 Windows 目标。", "graph": {"nodes": [{"id": "start", "type": "run.start", "x": 60, "y": 340, "config": {"label": "抓宠循环"}}, {"id": "init", "type": "flow.set_var", …
```

### 7. 运行列表 /wapi/runs

`GET /wapi/runs?limit=40` → HTTP 200

```json
{"runs": [{"run_id": "ui-20261105-135224", "mode": "once", "started_at": "2026-11-05T13:52:25+0800", "duration": 5.13, "events": 12, "status": "ok", "failedEngines": [], "engines": {"capture": "exited", "vision": "exited", "input": "exited", "sift": "exited", "battle": "exited", "scheduler": "exited…
```

### 8. 运行详情 ui-20261105-135224

`GET /wapi/runs/ui-20261105-135224` → HTTP 200

```json
{"run_id": "ui-20261105-135224", "summary": {"run_id": "ui-20261105-135224", "mode": "once", "started_at": "2026-11-05T13:52:25+0800", "duration": 5.13, "events": 12, "status": "ok", "failedEngines": [], "engines": {"capture": "exited", "vision": "exited", "input": "exited", "sift": "exited", "battl…
```

### 9. 事件流 ui-20261105-135224

`GET /wapi/runs/ui-20261105-135224/events?offset=0` → HTTP 200

```json
{"lines": [{"ts": 1793857948.952, "engine": "capture", "type": "ready", "run_id": "ui-20261105-135224", "config": "c:\\Users\\13005\\Downloads\\work\\rocogi\\suite\\config\\engines\\capture.toml", "python": "3.12.16", "components": ["capture.mock_window", "capture.windows_window", "capture.frame_dig…
```

### 10. 日志流 ui-20261105-135224/sift

`GET /wapi/runs/ui-20261105-135224/logs/sift?offset=0` → HTTP 200

```json
{"lines": [{"ts": 1793857955.569, "engine": "sift", "type": "ready", "run_id": "ui-20261105-135224", "config": "c:\\Users\\13005\\Downloads\\work\\rocogi\\suite\\config\\engines\\sift.toml", "python": "3.12.16", "components": ["sift.minimap_region", "sift.features", "sift.anchor_index", "sift.homogr…
```

### 11. 日志增量语义

`GET /wapi/runs/ui-20261105-135224/logs/sift?offset=956` → HTTP 200

```json
{"lines": [], "nextOffset": 956, "size": 956, "engine": "sift"}
```

### 12. 资产清单 /wapi/assets

`GET /wapi/assets` → HTTP 200

```json
{"manifest": {"schema_version": 1, "generated_at": "2026-11-05T06:54:31+0800", "canonicalMap": {"width": 6144, "height": 5888, "x_min": -12, "y_min": -11, "tile_size": 256, "zoom": 7}, "sources": {"nrc_db": "upstream\\ColinHong10-NRC_AI\\data\\nrc.db", "sift_npz": "upstream\\sift-map-tracker\\sift-m…
```

### 13. 重新校验 POST /wapi/assets/verify

`POST /wapi/assets/verify` → HTTP 200

```json
{"hashes": {"checked": 10, "failed": 0, "failures": [], "ok": true}, "points": {"pointCount": 9224, "expected": 9224, "ok": true, "markerTypes": 291, "canonicalMap": {"width": 6144, "height": 5888, "x_min": -12, "y_min": -11, "tile_size": 256, "zoom": 7}}, "mmap": {"path": "assets\\features\\sift_07…
```

### 14. 桥接 8787 /api/meta

`GET /wapi/bridge?port=8787&path=/api/meta` → HTTP 200

```json
{"version": "0.2.0", "platform": {"platform": "win32", "windows": true, "mock_target": true, "interception": false, "sift": true, "battle_ai": true, "reads_game_memory": false, "data_dir": "C:\\Users\\13005\\Downloads\\work\\rocogi\\data", "engine": "python"}, "target": {"kind": "mock", "title": "洛克…
```

### 15. 桥接 8788 /api/health

`GET /wapi/bridge?port=8788&path=/api/health` → HTTP 200

```json
{"ok": true, "engine": "c", "version": "0.2.0", "service": "rocoflow", "uptime_ms": 32708562}
```

### 16. 触发 SIFT 定位

`POST /wapi/trigger` → HTTP 200

```json
{"ok": true, "chain": "sift_locate", "run_id": "call-20261105-135244", "engine": "sift", "action": "locate", "status": "ok", "seconds": 5.78, "result": {"action": "locate", "mapSpace": {"width": 6144, "height": 5888}, "minimap": {"name": "162x162", "size": [162, 162]}, "result": {"state": "searching…
```

### 17. 触发 路线规划

`POST /wapi/trigger` → HTTP 200

```json
{"ok": true, "chain": "sift_route", "run_id": "call-20261105-135250", "engine": "sift", "action": "route", "status": "ok", "seconds": 3.08, "result": {"action": "route", "pointsUsed": 100, "plan": {"planned_count": 100, "source_mode": "fixed_corner", "pointIds": ["458469744640", "717227831296", "806…
```

### 18. 触发 状态机

`POST /wapi/trigger` → HTTP 200

```json
{"ok": true, "chain": "scheduler_fsm", "run_id": "call-20261105-135253", "engine": "scheduler", "action": "fsm", "status": "ok", "seconds": 3.41, "result": {"action": "fsm", "states": ["IDLE", "SCAN", "TRACK", "AIM", "THROW", "VERIFY", "PAUSED"], "events": ["START", "SPRITE_FOUND", "NO_SPRITE", "TAR…
```

### 19. 触发 对战决策

`POST /wapi/trigger` → HTTP 200

```json
{"ok": true, "chain": "battle_decide", "run_id": "call-20261105-135256", "engine": "battle", "action": "responder", "status": "ok", "seconds": 1.93, "result": {"action": "responder", "turn": 1, "availableActions": [{"kind": "charge", "raw": [-1]}, {"kind": "skill", "raw": [0]}, {"kind": "skill", "ra…
```

### 20. 端到端 run --once

`POST /wapi/trigger` → HTTP 200

```json
{"ok": true, "chain": "suite_run", "run_id": "ui-20261105-135258", "seconds": 21.22, "events": 12, "metrics": "runs\\ui-20261105-135258\\metrics.json", "summary": {"run_id": "ui-20261105-135258", "mode": "once", "started_at": "2026-11-05T13:52:59+0800", "duration": 8.54, "events": 12, "status": "ok"…
```

### 21. UI 运行列表出现新 run

`GET /wapi/runs?limit=40` → HTTP 200

```json
{"runs": [{"run_id": "ui-20261105-135258", "mode": "once", "started_at": "2026-11-05T13:52:59+0800", "duration": 8.54, "events": 12, "status": "ok", "failedEngines": [], "engines": {"capture": "exited", "vision": "exited", "input": "exited", "sift": "exited", "battle": "exited", "scheduler": "exited…
```

### 22. 新 run 事件可见

`GET /wapi/runs/ui-20261105-135258/events?offset=0` → HTTP 200

```json
{"lines": [{"ts": 1793857982.206, "engine": "capture", "type": "ready", "run_id": "ui-20261105-135258", "config": "c:\\Users\\13005\\Downloads\\work\\rocogi\\suite\\config\\engines\\capture.toml", "python": "3.12.16", "components": ["capture.mock_window", "capture.windows_window", "capture.frame_dig…
```

### 23. 新 run 日志可见

`GET /wapi/runs/ui-20261105-135258/logs/sift?offset=0` → HTTP 200

```json
{"lines": [{"ts": 1793857991.491, "engine": "sift", "type": "ready", "run_id": "ui-20261105-135258", "config": "c:\\Users\\13005\\Downloads\\work\\rocogi\\suite\\config\\engines\\sift.toml", "python": "3.12.16", "components": ["sift.minimap_region", "sift.features", "sift.anchor_index", "sift.homogr…
```

### 24. 概览当前 run 已切换

`GET /wapi/overview` → HTTP 200

```json
{"generatedAt": "2026-11-05T13:53:20+08:00", "backends": {"python": {"ok": true, "status": 200, "latencyMs": 5.1, "version": "0.2.0", "activeRuns": 0, "error": null}, "c": {"ok": true, "status": 200, "latencyMs": 58.9, "version": "0.2.0", "uptimeMs": 32744375, "error": null}, "suite": {"ok": true, "…
```
