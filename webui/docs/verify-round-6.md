# 验证轮次 6

- 时间：2026-11-05 19:48:20
- 目标：`http://127.0.0.1:8800`
- 结论：**PASS**（26/26 项通过）
- 浏览器控制台：PASS（0 error / 0 warning；总览与组件页逐页检查）

| # | 检查项 | 请求 | 状态码 | 耗时 | 结果 | 说明 |
|---|---|---|---|---|---|---|
| 1 | 首页 HTML | `GET /` | 200 | 0.01s | PASS | index 含 7 段导航、55 组件与 Vendor 面板 |
| 2 | 样式 app.css | `GET /app.css` | 200 | 0.01s | PASS | 27120 bytes |
| 3 | 脚本 app.js | `GET /app.js` | 200 | 0.02s | PASS | 33498 bytes · 四档/vendor/release 渲染标记齐全 |
| 4 | 概览 /wapi/overview | `GET /wapi/overview` | 200 | 0.24s | PASS | 7 引擎 / 55 组件 44-6-1-4 / py 0.4.0 vs c 0.2.0 / vendor 16·15·1·0 / release 2 包 / 当前 side-live5 15 进程 |
| 5 | 组件图谱 /wapi/components | `GET /wapi/components` | 200 | 0.05s | PASS | 55 组件 / 7 组 / 44-6-1-4 实计 44-6-1-4 / vendor 组 9-5-0-2 / 非 ready 均带原因 |
| 6 | Vendor 仓 /wapi/vendor | `GET /wapi/vendor` | 200 | 0.01s | PASS | 16 仓 · 15 resolved / 1 partial / 0 blocked · blocked=ElliottZhao666666-rocom-codex-pets-gen · 待重启 1 |
| 7 | 发布信息 /wapi/release | `GET /wapi/release` | 200 | 0.0s | PASS | 2 包 · lite 17527749B sha 9519fe73 · full 933988491B sha 74d1478b · files 530/9214 |
| 8 | 工作流 /wapi/workflows | `GET /wapi/workflows` | 200 | 0.05s | PASS | 4 工作流 / 36 节点 / 36 连线 / 24 节点类型 |
| 9 | 运行列表 /wapi/runs | `GET /wapi/runs?limit=40` | 200 | 0.16s | PASS | 10 条 run · 常驻 side-live5 15 进程 |
| 10 | 运行详情 ui-20261105-194618 | `GET /wapi/runs/ui-20261105-194618` | 200 | 0.03s | PASS | 14 事件 / sha 7d95bef3ce / 7 引擎指标 |
| 11 | 事件流 ui-20261105-194618 | `GET /wapi/runs/ui-20261105-194618/events?offset=0` | 200 | 0.03s | PASS | 14 行 / nextOffset 11644 |
| 12 | 日志流 ui-20261105-194618/sift | `GET /wapi/runs/ui-20261105-194618/logs/sift?offset=0` | 200 | 0.03s | PASS | engine=sift 2 行 / byte 956 |
| 13 | 日志增量语义 | `GET /wapi/runs/ui-20261105-194618/logs/sift?offset=956` | 200 | 0.01s | PASS | 二次读取 offset 落到 EOF，无重复行 |
| 14 | 资产清单 /wapi/assets | `GET /wapi/assets` | 200 | 0.04s | PASS | 点位 9224 / 特征 94992 / 清单 11 项 |
| 15 | 重新校验 POST /wapi/assets/verify | `POST /wapi/assets/verify` | 200 | 2.53s | PASS | 哈希 10 项失败 0 / mmap 0.0028s / ok=True |
| 16 | 桥接 8787 /api/meta | `GET /wapi/bridge?port=8787&path=/api/meta` | 200 | 0.03s | PASS | 8787 meta：version=0.4.0 workflowCount=4 pointCount=9224 |
| 17 | 桥接 8788 /api/health | `GET /wapi/bridge?port=8788&path=/api/health` | 200 | 0.03s | PASS | C 核心 0.2.0 uptime 54047562ms |
| 18 | 触发 SIFT 定位 | `POST /wapi/trigger` | 200 | 5.75s | PASS | status=ok resultKeys=4 run=call-20261105-194823 |
| 19 | 触发 路线规划 | `POST /wapi/trigger` | 200 | 3.77s | PASS | status=ok resultKeys=3 run=call-20261105-194829 |
| 20 | 触发 状态机 | `POST /wapi/trigger` | 200 | 4.08s | PASS | status=ok resultKeys=5 run=call-20261105-194833 |
| 21 | 触发 对战决策 | `POST /wapi/trigger` | 200 | 2.57s | PASS | status=ok resultKeys=6 run=call-20261105-194837 |
| 22 | 端到端 run --once | `POST /wapi/trigger` | 200 | 18.78s | PASS | run=ui-20261105-194840 events=14 18.71s |
| 23 | UI 运行列表出现新 run | `GET /wapi/runs?limit=40` | 200 | 0.15s | PASS | 新 run ui-20261105-194840 位于列表首位，events=14 |
| 24 | 新 run 事件可见 | `GET /wapi/runs/ui-20261105-194840/events?offset=0` | 200 | 0.02s | PASS | 14 条事件（['battle', 'capture', 'input', 'scheduler', 'sift', 'vendor', 'vision']） |
| 25 | 新 run 日志可见 | `GET /wapi/runs/ui-20261105-194840/logs/sift?offset=0` | 200 | 0.03s | PASS | engine=sift 2 行 |
| 26 | 概览 latest 更新且常驻仍选中 | `GET /wapi/overview` | 200 | 0.26s | PASS | latest=ui-20261105-194840 / current=side-live5 / pinned=side-live5（新 run 不抢占常驻选中） |

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
/* Rocogi 套件控制台 · 前端逻辑（无构建步骤） */ const $ = (sel, root = document) => root.querySelector(sel); const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel)); const state = { view: "overview", overview: null, pinnedRun: null, workflows: [], nodeCatalog: {}, wfId: null, comps: null, compF…
```

### 4. 概览 /wapi/overview

`GET /wapi/overview` → HTTP 200

```json
{"versions": {"python": "0.4.0", "c": "0.2.0"}, "componentSummary": "55 组件：44 ready / 6 not-wired / 1 skipped / 4 blocked-vendor", "currentRun": "side-live5"}
```

### 5. 组件图谱 /wapi/components

`GET /wapi/components` → HTTP 200

```json
{"stats": {"total": 55, "ready": 44, "notWired": 6, "skipped": 1, "blockedVendor": 4}, "vendorCounts": {"total": 16, "ready": 9, "notWired": 5, "blockedVendor": 2}}
```

### 6. Vendor 仓 /wapi/vendor

`GET /wapi/vendor` → HTTP 200

```json
{"summary": {"total": 16, "resolved": 15, "partial": 1, "blocked": 0}, "blocked": ["pets-gen"], "pendingReboot": ["Interception"]}
```

### 7. 发布信息 /wapi/release

`GET /wapi/release` → HTTP 200

```json
{"packages":[{"name":"rocogi-0.4.0-lite.zip","sha8":"9519fe73"},{"name":"rocogi-0.4.0-full.zip","sha8":"74d1478b"}]}
```

### 8. 工作流 /wapi/workflows

`GET /wapi/workflows` → HTTP 200

```json
{"ok": true, "workflows": [{"id": "wf_demo_catch", "name": "抓宠巡航 · 自动丢球", "description": "截图识别战斗与可捕捉精灵，普通战斗聚能、污染战斗逃跑，空闲时自动丢球。演示使用模拟游戏窗口，可切换到 Windows 目标。", "graph": {"nodes": [{"id": "start", "type": "run.start", "x": 60, "y": 340, "config": {"label": "抓宠循环"}}, {"id": "init", "type": "flow.set_var", …
```

### 9. 运行列表 /wapi/runs

`GET /wapi/runs?limit=40` → HTTP 200

```json
{"runs": [{"run_id": "20261105-194734", "mode": "supervised", "started_at": "2026-11-05T19:47:35+0800", "duration": 0.0, "events": 0, "status": "stopped", "engineCount": 7, "runningEngines": 7, "processes": null, "pinned": false, "failedEngines": [], "engines": {"capture": "running", "vision": "runn…
```

### 10. 运行详情 ui-20261105-194618

`GET /wapi/runs/ui-20261105-194618` → HTTP 200

```json
{"run_id": "ui-20261105-194618", "summary": {"run_id": "ui-20261105-194618", "mode": "once", "started_at": "2026-11-05T19:46:19+0800", "duration": 3.73, "events": 14, "status": "ok", "engineCount": 7, "runningEngines": 0, "processes": null, "pinned": false, "failedEngines": [], "engines": {"capture"…
```

### 11. 事件流 ui-20261105-194618

`GET /wapi/runs/ui-20261105-194618/events?offset=0` → HTTP 200

```json
{"lines": [{"ts": 1793879183.447, "engine": "capture", "type": "ready", "run_id": "ui-20261105-194618", "config": "C:\\Users\\13005\\Downloads\\work\\rocogi\\suite\\config\\engines\\capture.toml", "python": "3.12.16", "components": ["capture.mock_window", "capture.windows_window", "capture.frame_dig…
```

### 12. 日志流 ui-20261105-194618/sift

`GET /wapi/runs/ui-20261105-194618/logs/sift?offset=0` → HTTP 200

```json
{"lines": [{"ts": 1793879190.802, "engine": "sift", "type": "ready", "run_id": "ui-20261105-194618", "config": "C:\\Users\\13005\\Downloads\\work\\rocogi\\suite\\config\\engines\\sift.toml", "python": "3.12.16", "components": ["sift.minimap_region", "sift.features", "sift.anchor_index", "sift.homogr…
```

### 13. 日志增量语义

`GET /wapi/runs/ui-20261105-194618/logs/sift?offset=956` → HTTP 200

```json
{"lines": [], "nextOffset": 956, "size": 956, "engine": "sift"}
```

### 14. 资产清单 /wapi/assets

`GET /wapi/assets` → HTTP 200

```json
{"manifest": {"schema_version": 1, "generated_at": "2026-11-05T18:45:57+0800", "canonicalMap": {"width": 6144, "height": 5888, "x_min": -12, "y_min": -11, "tile_size": 256, "zoom": 7}, "sources": {"nrc_db": "rocogi\\vendor\\ColinHong10-NRC_AI\\data\\nrc.db", "sift_npz": "rocogi\\vendor\\sift-map-tra…
```

### 15. 重新校验 POST /wapi/assets/verify

`POST /wapi/assets/verify` → HTTP 200

```json
{"hashes": {"checked": 10, "failed": 0, "failures": [], "ok": true}, "points": {"pointCount": 9224, "expected": 9224, "ok": true, "markerTypes": 291, "canonicalMap": {"width": 6144, "height": 5888, "x_min": -12, "y_min": -11, "tile_size": 256, "zoom": 7}}, "mmap": {"path": "assets\\features\\sift_07…
```

### 16. 桥接 8787 /api/meta

`GET /wapi/bridge?port=8787&path=/api/meta` → HTTP 200

```json
{"version": "0.4.0", "platform": {"platform": "win32", "windows": true, "mock_target": true, "interception": false, "sift": true, "battle_ai": true, "reads_game_memory": false, "data_dir": "C:\\Users\\13005\\Downloads\\work\\rocogi\\data", "engine": "python"}, "target": {"kind": "mock", "title": "洛克…
```

### 17. 桥接 8788 /api/health

`GET /wapi/bridge?port=8788&path=/api/health` → HTTP 200

```json
{"ok": true, "engine": "c", "version": "0.2.0", "service": "rocoflow", "uptime_ms": 54047562}
```

### 18. 触发 SIFT 定位

`POST /wapi/trigger` → HTTP 200

```json
{"ok": true, "chain": "sift_locate", "run_id": "call-20261105-194823", "engine": "sift", "action": "locate", "status": "ok", "seconds": 5.75, "result": {"action": "locate", "mapSpace": {"width": 6144, "height": 5888}, "minimap": {"name": "162x162", "size": [162, 162]}, "result": {"state": "searching…
```

### 19. 触发 路线规划

`POST /wapi/trigger` → HTTP 200

```json
{"ok": true, "chain": "sift_route", "run_id": "call-20261105-194829", "engine": "sift", "action": "route", "status": "ok", "seconds": 3.75, "result": {"action": "route", "pointsUsed": 100, "plan": {"planned_count": 100, "source_mode": "fixed_corner", "pointIds": ["458469744640", "717227831296", "806…
```

### 20. 触发 状态机

`POST /wapi/trigger` → HTTP 200

```json
{"ok": true, "chain": "scheduler_fsm", "run_id": "call-20261105-194833", "engine": "scheduler", "action": "fsm", "status": "ok", "seconds": 4.08, "result": {"action": "fsm", "states": ["IDLE", "SCAN", "TRACK", "AIM", "THROW", "VERIFY", "PAUSED"], "events": ["START", "SPRITE_FOUND", "NO_SPRITE", "TAR…
```

### 21. 触发 对战决策

`POST /wapi/trigger` → HTTP 200

```json
{"ok": true, "chain": "battle_decide", "run_id": "call-20261105-194837", "engine": "battle", "action": "responder", "status": "ok", "seconds": 2.55, "result": {"action": "responder", "turn": 1, "availableActions": [{"kind": "charge", "raw": [-1]}, {"kind": "skill", "raw": [0]}, {"kind": "skill", "ra…
```

### 22. 端到端 run --once

`POST /wapi/trigger` → HTTP 200

```json
{"ok": true, "chain": "suite_run", "run_id": "ui-20261105-194840", "seconds": 18.71, "events": 14, "metrics": "runs\\ui-20261105-194840\\metrics.json", "summary": {"run_id": "ui-20261105-194840", "mode": "once", "started_at": "2026-11-05T19:48:41+0800", "duration": 4.04, "events": 14, "status": "ok"…
```

### 23. UI 运行列表出现新 run

`GET /wapi/runs?limit=40` → HTTP 200

```json
{"runs": [{"run_id": "ui-20261105-194840", "mode": "once", "started_at": "2026-11-05T19:48:41+0800", "duration": 4.04, "events": 14, "status": "ok", "engineCount": 7, "runningEngines": 0, "processes": null, "pinned": false, "failedEngines": [], "engines": {"capture": "exited", "vision": "exited", "i…
```

### 24. 新 run 事件可见

`GET /wapi/runs/ui-20261105-194840/events?offset=0` → HTTP 200

```json
{"lines": [{"ts": 1793879325.3, "engine": "capture", "type": "ready", "run_id": "ui-20261105-194840", "config": "C:\\Users\\13005\\Downloads\\work\\rocogi\\suite\\config\\engines\\capture.toml", "python": "3.12.16", "components": ["capture.mock_window", "capture.windows_window", "capture.frame_diges…
```

### 25. 新 run 日志可见

`GET /wapi/runs/ui-20261105-194840/logs/sift?offset=0` → HTTP 200

```json
{"lines": [{"ts": 1793879333.248, "engine": "sift", "type": "ready", "run_id": "ui-20261105-194840", "config": "C:\\Users\\13005\\Downloads\\work\\rocogi\\suite\\config\\engines\\sift.toml", "python": "3.12.16", "components": ["sift.minimap_region", "sift.features", "sift.anchor_index", "sift.homogr…
```

### 26. 概览 latest 更新且常驻仍选中

`GET /wapi/overview` → HTTP 200

```json
{"generatedAt": "2026-11-05T19:48:59+08:00", "backends": {"python": {"ok": true, "status": 200, "port": 8787, "role": "Python 后端", "latencyMs": 4.6, "version": "0.4.0", "activeRuns": 0, "error": null}, "c": {"ok": true, "status": 200, "port": 8788, "role": "C 核心", "latencyMs": 24.4, "version": "0.2.…
```
