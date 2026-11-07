# Rocogi WebUI · 接口契约（api-contract.md）

本文件记录 WebUI 与其数据源之间**实际存在**的接口，以及 WebUI 自身提供的适配层契约。
所有内容基于 2026-11-05 对运行中服务的真实探测，不包含推测接口。

- WebUI 进程：`http://127.0.0.1:8800`（仅监听 127.0.0.1，静态页面 + `/wapi/*` 适配层）
- 上游 Python 后端：`http://127.0.0.1:8787`（**0.4.0**）
- 上游 C 核心：`http://127.0.0.1:8788`（**0.2.0**，未随本轮升级）
- 工作流套件：`work/rocogi/suite`（**0.4.0**，7 引擎 / 55 组件 / 36 入口）
- 套件证据目录：`work/rocogi/suite/runs/<run_id>/{manifest.json,events.jsonl,metrics.json}`、`work/rocogi/suite/logs/<run_id>/<engine>.jsonl`
- 组件注册表：`work/rocogi/suite/config/components.toml`（55 条；44 ready / 6 not-wired / 1 skipped / 4 blocked-vendor）
- Vendor 仓清单：`work/rocogi/vendor/manifest.json`（16 仓；15 resolved / 1 partial / 0 blocked）
- 发布说明：`work/rocogi/docs/verify-release-0.4.0.md`；包体在 `work/rocogi/release/*.zip`

> 8790 端口不存在，未接入。

---

## 1. 上游真实接口（只读消费）

### 1.1 Python 后端 8787（0.4.0）

| 方法 | 路径 | 用途 | 实测 |
|---|---|---|---|
| GET | `/api/health` | 服务健康、平台能力 | 200，`ok/service/version=0.4.0/platform/activeRuns` |
| GET | `/api/meta` | 版本、目标窗口、设置、地图规模、计数 | 200，`version=0.4.0, workflowCount=4, runCount=0, map.pointCount=9224` |
| GET | `/api/engines` | 引擎预设与 5 引擎状态 + realtime/tracker 状态 | 200，`status.capture/vision/input/sift/battle`（无套件 7 引擎口径） |
| GET | `/api/components` | 组件/功能/分组/matrix/usage | 200；WebUI 仅取 `usage` 映射 |
| GET | `/api/workflows` | 4 条工作流 DAG（含节点 x/y 与连线） | 200，数组 |
| GET | `/api/nodes` | 节点类型目录（标题/分类/字段） | 200，`nodes/categories` |
| GET | `/api/runs` | 后端运行记录列表 | 200，**当前为空数组** |
| POST | `/api/workflows/{id}/run` | 触发后端 DAG 运行 | 存在，本 WebUI 未使用（见缺口 G3） |

### 1.2 C 核心 8788（0.2.0）

| 方法 | 路径 | 用途 | 实测 |
|---|---|---|---|
| GET | `/api/health` | C 引擎健康与 uptime | 200，`ok/engine/version=0.2.0/uptime_ms` |
| GET | `/api/windows` | 窗口枚举 | 200，`count=7`（WebUI 不做窗口识别，仅探测） |
| POST | `/api/capture/test`、`/api/input/test`、`/api/match/test`、`/api/workflows/run` | 截图/输入/匹配/工作流验证 | 存在（GET 返回 405）；本 WebUI 未接入 |

### 1.3 套件 CLI（子进程调用）

| 命令 | 输出 | 本 WebUI 用途 |
|---|---|---|
| `engines --json` | 7 引擎状态 + 55 组件统计 + 组件表 | 契约核对（总览/组件图谱以 TOML + venv 为准） |
| `call <engine> <action>` | 单引擎执行结果 JSON | 手动触发（sift locate / route、scheduler fsm、battle responder） |
| `run --once` | run_id + 合并事件数 + metrics 路径 | 端到端触发一次 7 引擎 run |
| `assets verify` | 哈希/点位/特征 mmap/NRC 校验 | 资产校验面板 |
| `evidence --run <id>` | run 摘要 | 运行证据（WebUI 直接读文件，口径一致） |

数据文件契约：

- `runs/<run_id>/manifest.json`：`schema_version, run_id, mode, started_at, config{path,sha256,engine configs}, engines{versions}, components[]`（side-live5 含 55 组件与 kernel/capture/vision/input/sift/battle/scheduler/vendor）
- `runs/<run_id>/metrics.json`：`run_id, mode, duration, engines{pid,started_at,restarts,restart_seconds,state,exitcode}, eventsMerged`
- `runs/<run_id>/events.jsonl`：每行 `{ts, engine, type: ready|result|error|supervisor.restart, ...}`
- `logs/<run_id>/<engine>.jsonl`：与 events 同结构，单引擎流
- `assets/manifest.json`：`stats.features.featureCount=94992`、`stats.points.pointCount=9224`、`assets[].sha256`
- `vendor/manifest.json`：`repo_count=16, total_bytes=1324626890, status_summary{resolved_or_adapted:15, partial:1, still_blocked:0}`；可选 `repos[].status`、`repos[].resolution{still_blocked, activation_pending_reboot, post_reboot_check}`

---

## 2. WebUI 适配层契约（`/wapi/*`）

统一返回 `application/json; charset=utf-8`。错误形如 `{"ok":false,"error":"..."}`，HTTP 4xx/5xx。

### GET `/wapi/overview`

```json
{
  "generatedAt": "2026-11-05T19:40:00+08:00",
  "backends": {
    "python": {"ok": true, "port": 8787, "role": "Python 后端", "version": "0.4.0", "latencyMs": 12, "activeRuns": 0},
    "c": {"ok": true, "port": 8788, "role": "C 核心", "version": "0.2.0", "uptimeMs": 54156390},
    "suite": {"ok": true, "version": "0.4.0", "root": "rocogi/suite"}
  },
  "versions": {"suite": "0.4.0", "python": "0.4.0", "c": "0.2.0"},
  "engines": [{"name":"capture","label":"截图引擎","status":"ready","action":"capture","components":5,"entry":"rocogi-suite call capture capture"}],
  "componentStats": {"total":55,"ready":44,"notWired":6,"skipped":1,"blockedVendor":4},
  "componentSummary": "55 组件：44 ready / 6 not-wired / 1 skipped / 4 blocked-vendor",
  "currentRun": {"run_id":"side-live5","mode":"supervised","status":"running","pinned":true,"engineCount":7,"processes":15,"events":14,"duration":0.0},
  "pinnedRun": {"run_id":"side-live5", "...": "..."},
  "latestRun": {"run_id":"ui-20261105-195040", "...": "..."},
  "runCount": 11,
  "recentRuns": [{"run_id":"...","status":"ok","duration":18.0,"events":14,"mode":"once","pinned":false}],
  "vendor": {"summary":{"total":16,"resolved":15,"partial":1,"blocked":0,"totalBytes":1324626890},
             "blockedItems":[{"repo":"...pets-gen","reason":"..."}],
             "pendingReboot":[{"repo":"...Interception","script":"vendor/tools/post-reboot-check.ps1","preRebootResult":{"pass":24,"fail":3}}],
             "note":"仓级 resolution 与 suite 组件状态是两套口径"},
  "release": {"version":"0.4.0","docPath":"docs/verify-release-0.4.0.md",
              "packages":[{"name":"rocogi-0.4.0-lite.zip","bytes":17527749,"sha8":"9519fe73","files":530},
                          {"name":"rocogi-0.4.0-full.zip","bytes":933988491,"sha8":"74d1478b","files":9214}]}
}
```

`currentRun = pinnedRun || latestRun`：首屏默认选中常驻 `side-live5`；每轮新 run 只更新 `latestRun` 与运行列表首位，不抢占常驻选中。

### GET `/wapi/components`

```json
{
  "groups": [
    {"engine":"capture","label":"截图","engineStatus":"ready",
     "counts":{"total":5,"ready":5,"notWired":0,"skipped":0,"blockedVendor":0},
     "components":[
      {"id":"capture.mock_window","status":"ready","declared":"ready","reason":"","note":"",
       "implemented":true,"deps":["..."],"entry":"...","config":"...","usedBy":["onedragon"]}]}
  ],
  "stats": {"total":55,"ready":44,"notWired":6,"skipped":1,"blockedVendor":4},
  "states": ["ready","not-wired","skipped","blocked-vendor"],
  "sources": {"registry":"rocogi-suite/config/components.toml (0.4.0, 55 components)","usage":"8787 /api/components (usage map)"}
}
```

判定规则：**严格采用 `components.toml` 的 `status`**，四档不折叠：

- `ready` → `ready`
- `not-wired` → `not-wired`（有源码但未接入运行时）
- `skipped` → `skipped`
- `blocked-vendor` → `blocked-vendor`（外部前置未满足）
- 未知/缺省状态 → `not-wired`；若声明为 `ready` 但引擎 venv 缺失，也降级为 `not-wired`

所有非 `ready` 行必须返回非空 `reason`（取 `reason`，否则 `note`）。`declared` 保留 TOML 原始值，便于发现“声明 ready 但实际降级”的组件。

### GET `/wapi/vendor`

```json
{
  "summary": {"total":16,"resolved":15,"partial":1,"blocked":0,
              "reposDeclared":{"resolved_or_adapted":15,"partial":1,"still_blocked":0,"total":16},
              "totalBytes":1324626890,"generatedAt":"2026-11-05T16:16:06+08:00"},
  "repos": [{"repo":"...pets-gen","declared":"partial","status":"partial","license":"MIT",
             "size":{"files":22,"bytes":787161},"resolution":{"stillBlocked":"...需 GUI 导出","note":"..."}}],
  "blockedItems": [{"repo":"...pets-gen","status":"partial","reason":"..."}],
  "pendingReboot": [{"repo":"...Interception","script":"vendor/tools/post-reboot-check.ps1",
                     "preRebootResult":{"pass":24,"fail":3},"note":"已安装，待重启生效"}],
  "note": "仓级 resolution 状态（15/1/0）与 suite 组件 blocked-vendor（4 条）是两套口径，不可相加或混用。"
}
```

仓级状态规则：显式 `status=partial` → `partial`；`status=blocked` → `blocked`；`status=resolved` 或**未声明** → `resolved`（未声明按已导入/已适配归纳，见缺口 G12）。

### GET `/wapi/release`

```json
{
  "version": "0.4.0",
  "docPath": "docs/verify-release-0.4.0.md",
  "verifiedAt": "2026-11-05 19:10 CST",
  "packages": [
    {"name":"rocogi-0.4.0-lite.zip","bytes":17527749,"sizeLabel":"约 17.5 MB","files":530,
     "sha256":"9519fe73...","sha8":"9519fe73","contents":"自有代码 + suite + 文档；不含 vendor"},
    {"name":"rocogi-0.4.0-full.zip","bytes":933988491,"sizeLabel":"约 890.7 MB","files":9214,
     "sha256":"74d1478b...","sha8":"74d1478b","contents":"lite + vendor/ + artifacts/"}
  ],
  "otherPackages": [{"name":"rocogi-core-0.3.0.zip","bytes":6997286}],
  "highlights": ["两个包内 compileall 均 exit 0", "解压后后端 200、version=0.4.0、interception=false（待重启）、sift=true"]
}
```

sha256 由适配层本地计算并缓存到 `webui/.cache/release_sha.json`（发布文档本身不写 sha）。

### GET `/wapi/workflows`

```json
{"workflows":[{"id":"wf_demo_catch","name":"...","description":"...","graph":{"nodes":[...],"edges":[...]},"tags":[...]}],
 "nodeCatalog":{"run.start":{"title":"...","category":"run","categoryLabel":"...","accent":"..."}}}
```

### GET `/wapi/runs?limit=60`

```json
{"runs":[{"run_id":"side-live5","mode":"supervised","started_at":"...","duration":0.0,"events":14,
          "status":"running|ok|failed|stopped","engineCount":7,"runningEngines":7,"processes":15,
          "pinned":true,"failedEngines":[],"engines":{"capture":"running"}}]}
```

按目录 mtime 倒序；新 run 位于首位。`processes` 仅在运行态返回，由进程树推导。

### GET `/wapi/runs/{run_id}`

`{"run_id","manifest":{...},"metrics":{...},"events":[{...}],"logs":[{"engine":"capture","bytes":6090}]}`

### GET `/wapi/runs/{run_id}/events?offset=<byte>`

增量读取 `events.jsonl`，`offset` 为字节偏移，返回 `{"lines":[...],"nextOffset":1234,"size":58567}`。

### GET `/wapi/runs/{run_id}/logs/{engine}?offset=<byte>`

增量读取 `logs/<run_id>/<engine>.jsonl`，同样返回 `lines/nextOffset/size`。

### GET `/wapi/assets`

```json
{"manifest":{...assets/manifest.json 原文...},
 "verify":{"hashes":{"checked":10,"failed":0},"points":{"pointCount":9224,"ok":true},
           "mmap":{"shape":[94992,128],"mmapSeconds":0.0018,"ok":true},"ok":true,"cachedAt":"..."}}
```

### POST `/wapi/assets/verify`

重新执行 `assets/verify.py`（约 2.6 s，哈希 10 个文件），返回同 `verify` 结构并写入缓存 `webui/.cache/assets_verify.json`。

### POST `/wapi/trigger`

请求体 `{"chain":"sift_locate|sift_route|scheduler_fsm|battle_decide|suite_run"}`。

```json
{"ok":true,"chain":"sift_locate","run_id":"call-20261105-195012","engine":"sift","action":"locate",
 "status":"ok","seconds":6.79,"result":{...引擎原始 result...},
 "stdout":"...","log":"logs/call-.../sift.jsonl"}
```

`suite_run` 走 `run --once`（7 引擎），返回 `{"ok":true,"chain":"suite_run","run_id":"...","events":14,"metrics":{...}}`，本次 run 会立即出现在 `GET /wapi/runs` 首位，并更新 `/wapi/overview` 的 `latestRun`。

### GET `/wapi/bridge?port=8787&path=/api/meta`

透传上游 GET（仅允许 8787/8788 与 `/api/` 前缀），返回原始 JSON。

---

## 3. 后端缺口（contract gaps）

| 编号 | 缺口 | 现状 | WebUI 处理 |
|---|---|---|---|
| G1 | 8787 无“套件 7 引擎”的运行时状态 | `/api/engines` 仍只有 5 个后端引擎 + realtime/tracker，无 `scheduler`/`vendor` | 以 `components.toml` + venv 探测判定 7 引擎，metrics.json 提供真实启停 |
| G2 | 8787 `/api/runs` 为空，且不读套件 `runs/` | 两套运行记录未打通 | 适配层直接读 `rocogi/suite/runs` |
| G3 | 8787 `/api/workflows/{id}/run` 的运行不写入套件证据目录 | 后端 DAG 运行与套件 run 是两套 | 工作流视图只做可视化，不冒充触发入口；端到端触发走 `suite_run` |
| G4 | 8787 `/api/assets/*` 无资产清单与哈希接口 | `/api/assets/manifest.json` 返回 404 | 资产面板读 `rocogi/suite/assets/manifest.json` + `verify.py` |
| G5 | 事件流无 SSE/WebSocket | 仅文件追加 | 前端按字节 offset 轮询 JSONL（1 s） |
| G6 | SIFT `locate` 在确定性探针裁剪下返回 `state=searching`、`center_x=null` | 契约级输出，非精度结论 | 原样展示 JSON，界面标注“契约结果，未做精度验证” |
| G7 | 8788 仅暴露 health/windows/capture-test 等，无引擎清单与运行证据 | C 核心不产出 runs/ 结构 | 仅展示 8788 健康、uptime 与版本 |
| G8 | ~~组件状态被折叠成两档~~（**本轮已修复**） | 旧版把 `not-wired` / `blocked-vendor` 折叠为 `ready` | 四档直出，计数 44/6/1/4，非 ready 必带原因 |
| G9 | 引擎配置曾出现非法 TOML | `config/engines/input.toml` 的 `hotkey_modifiers = 0x0001 + 0x0002` 使 `tomllib` 报错，后被其他会话改为合法值 | `engine_meta()` 解析失败时退化为正则读取 `action`，UI 不因单文件损坏而 500 |
| G10 | 套件 `runs/` 会被其他整合会话清理 | 历史上一度被整体清空，`/wapi/runs` 瞬时为空 | 适配层如实反映；验证脚本在空目录时自动触发一次 run 播种 |
| G11 | 系统时间在运行中跳变 | supervisor 以墙钟计算超时，跳变时出现负超时 | 属环境问题；WebUI 只读展示 metrics，不做时间修正 |
| G12 | `vendor/manifest.json` 有 9 个仓没有显式 `resolution.status` | 这 9 仓也没有逐仓 `resolution.done` 记录 | 未声明按 resolved/adapted 归纳；面板保留 `declared=null` 与原始字段 |
| G13 | `pets-gen` 没有独立 `blocked` 状态 | 实际是 `status=partial` + `resolution.still_blocked` | 仓级 blocked 计数仍为 0，另设 `blockedItems` 展示 pets-gen |
| G14 | 发布文档不含 sha256 | `docs/verify-release-0.4.0.md` 只给体积/文件数/验证结论 | 适配层对两个 zip 本地计算 sha256 并缓存，返回前 8 位 |
| G15 | 无权威进程数接口 | metrics 只有 7 个引擎 pid；15 进程需看进程树 | 适配层用 Toolhelp32 推导 supervisor + 引擎主进程 + worker 数 |
| G16 | 8788 C 核心未升级 | 套件与 8787 已 0.4.0，8788 仍 0.2.0 | 按端口分别标注版本，不统一显示 |
| G17 | `side-live5` 的 duration/events 语义 | `duration=0.0`、事件持续追加，不是完成态 | 依据 PID 存活展示 `running`，不伪造耗时 |
