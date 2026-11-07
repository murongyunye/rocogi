# Rocogi × DeepSeek Harness

Rocogi 提供一套面向 AI agent / DeepSeek Harness 的本地 HTTP 接口。Harness 不需要理解工作流细节，先调用 `observe`，再调用 `press_key` / `click` / `run_workflow` 即可驾驶引擎。

## 1. 最小接入

启动 Rocogi：

```bash
cd rocoflow
./scripts/run.sh
```

入口地址：

```
http://127.0.0.1:8787
```

先读取 manifest，它会返回系统提示词、工具 JSON Schema、当前目标、引擎预设、会话和运行状态：

```bash
curl http://127.0.0.1:8787/api/harness/manifest
```

## 2. 三步上手

```bash
# 1) 观察：截图 + 场景分类 + 坐标 + 会话状态
curl -X POST http://127.0.0.1:8787/api/harness/act \
  -H 'Content-Type: application/json' \
  -d '{"action":"observe"}'

# 2) 动作：按键 / 点击 / 定位
curl -X POST http://127.0.0.1:8787/api/harness/act \
  -H 'Content-Type: application/json' \
  -d '{"action":"press_key","params":{"key":"x"}}'

# 3) 完整任务：按名称运行工作流
curl -X POST http://127.0.0.1:8787/api/harness/act \
  -H 'Content-Type: application/json' \
  -d '{"action":"run_workflow","params":{"name":"抓宠巡航 · 自动丢球"}}'
```

`observe` 返回的 `result.screenshot` 可以直接作为视觉输入；`result.scene.kind` 取值为：

- `battle_normal`：普通战斗
- `battle_polluted`：污染战斗
- `field_pet`：野外可捕捉精灵
- `party_confirm`：同行请求
- `field`：普通野外

## 3. 工具列表

`GET /api/harness/tools` 返回 OpenAI function-calling 格式的完整工具列表：

| 工具 | 用途 |
| --- | --- |
| `rocogi_observe` | 截图 + 场景分类 + 地图坐标 + 截图 URL |
| `rocogi_capture` | 仅截图并保存 artifact，返回 frame 摘要 |
| `rocogi_press_key` | 按键（x / 1-6 / f / esc / space / enter） |
| `rocogi_click` | 窗口客户区坐标点击 |
| `rocogi_move` | 相对当前位置移动鼠标 |
| `rocogi_locate` | SIFT / 模拟定位 |
| `rocogi_start_realtime` / `rocogi_stop_realtime` | 启动/停止实时任务 |
| `rocogi_start_tracker` / `rocogi_stop_tracker` | 启动/停止地图追踪 |
| `rocogi_list_workflows` | 列出工作流 |
| `rocogi_run_workflow` | 按 ID 或名称运行工作流 |
| `rocogi_run_onedragon` | 执行一条龙任务 |
| `rocogi_run_status` / `rocogi_stop_run` | 查询 / 停止运行 |
| `rocogi_battle_decision` | MCTS 对战推荐动作 |
| `rocogi_battle_simulate` | 对战推演 |
| `rocogi_dex_lookup` | 图鉴查询：精灵六维 / 特性 / 技能 / 进化链，或技能检索 |
| `rocogi_pvp_analyze` | 6 人 PvP 阵容结构分析 |
| `rocogi_pvp_matchup` | 对毒队 / 翼王队的 6v6 MCTS 推演 |
| `rocogi_get_state` | 目标、会话、运行与引擎状态 |
| `rocogi_sequence` | 一次调用执行多个动作 |

单个动作接口：

```
POST /api/harness/act
{"action": "...", "params": {...}}
```

也接受工具名原样，例如 `{"action":"rocogi_press_key","params":{...}}`。

## 4. Python SDK

```python
from sdk.rocogi_harness import RocogiHarness

client = RocogiHarness("http://127.0.0.1:8787")
print(client.manifest()["state"])
observation = client.observe()
print(observation["result"]["scene"])
client.press("x")
```

运行：

```bash
.venv/bin/python sdk/rocogi_harness.py
```

## 5. 推荐 agent 循环

```text
observe
  → 若 scene == battle_normal：press x（聚能）
  → 若 scene == battle_polluted：press esc → click yes 按钮
  → 若 scene == field_pet：press x（丢球）
  → 若 scene == party_confirm：press f
  → 每 3~5 步重新 observe
```

若任务较完整，优先调用 `rocogi_run_workflow` 或 `rocogi_run_onedragon`，不要逐步复刻工作流。

组队或判断属性前，可以让 agent 先查图鉴：

```bash
curl -X POST http://127.0.0.1:8787/api/harness/act \
  -H 'Content-Type: application/json' \
  -d '{"action":"dex_lookup","params":{"name":"迪莫"}}'
```

返回包含 `pokemon.stats`、`pokemon.ability`、`skills`、`evolution` 与 `related`，agent 不需要再抓网页。

## 6. 引擎参数

`GET /api/engines` 返回当前预设与全部引擎参数。可用预设：

- `demo`：模拟目标，适合 agent 首次接入与演练
- `windows_sendinput`：Windows 实机，无需驱动
- `windows_interception`：Windows 实机，Interception 驱动
- `low_latency`：实时优先
- `accuracy`：高精度识别

切换：

```bash
curl -X POST http://127.0.0.1:8787/api/engines/apply \
  -H 'Content-Type: application/json' \
  -d '{"presetId":"demo"}'
```

## 7. 本地与安全

- 接口默认无鉴权，只监听本机时使用；不要暴露到公网。
- 截图、运行记录与 SIFT 锚点都在 `runtime/`。
- Rocogi 不读取游戏内存，仅使用屏幕截图与键鼠模拟；`/api/harness/manifest` 的 `reads_game_memory` 固定为 `false`，并有静态审计测试守护。
- 自动化可能违反游戏服务条款，请只在你有权操作的环境中使用。

## 8. Headless 引擎可执行包

如果 agent 不需要 HTTP 服务，可以直接调用按功能拆分的引擎 exe：

```bash
RocogiEngine.exe --action library --pretty
RocogiEngine.exe --action sense.capture
RocogiEngine.exe --action battle.analyze --params "{\"team\":[\"迪莫\",\"喵喵\"]}"
RocogiBattle.exe --action dex_detail --params "{\"name\":\"迪莫\"}"
```

这些入口不启动 FastAPI/UI，只输出 JSON；构建方式与完整动作见 [engines.md](engines.md)。

## 9. Delias 契约动作（11 个）

以下动作由 `backend/app/harness_actions.py` 实现，并在 `backend/app/harness.py` 的 `execute()` 中分发；`tools_schema()` 会合并它们的 OpenAI function 定义。它们与既有动作使用同一调用约定：`POST /api/harness/act {"action": "...", "params": {...}}`；参数缺失或非法时返回 `{"ok": false, "error": ...}`，未知动作仍返回既有的 `unknown action: <name>`。

| 动作 | 必填参数 | 契约输出 |
| --- | --- | --- |
| `match_template` | `template` | `matched`、`score`、`points[]`（整帧像素） |
| `detect_sprites` | 无 | `candidates[]`（`bbox` / `confidence` / `cx` / `cy` / `label` / `track_id`） |
| `ocr` | `roi` | `text`、`value`、`confidence`、`mode` |
| `foreground` | 无 | `focused`、`hwnd`、`supported`、`reason` |
| `set_input_backend` | `backend` | `requested`、`backend`、`available`、`fallback_reason` |
| `route_plan` | 无 | `route[]`、`total_distance`、`count` |
| `map_points` | 无 | `points[]`、`total` |
| `turn_state` | 无 | `turn`、`enemyHp`、`skills[]`、`polluted` |
| `vendor_status` | 无 | `adapters{}` 与计数 |
| `vendor_action` | `action` | 适配器 JSON 平铺 |
| `vendor_blocked` | 无 | `adapters{}`、`blockedCount` |

字段语义、取值范围与真机限制见 [delias-adapter-report.md](delias-adapter-report.md) 第 3、5 节。

### 9.1 回归门禁

- `backend/tests/test_harness_actions.py` 锁定：11 个动作都能被 `dispatch` 识别、都出现在 `tools_schema()`、schema 的 `required` 与 `harness_contracts.ACTION_REQUIRED_FIELDS` 一致，并有一个经由 `harness.execute` 的端到端 `match_template` 用例。
- `.github/workflows/pytest.yml` 在每次 push / pull_request 上运行 `python -m pytest -q`（Ubuntu + Python 3.12），安装 `backend/requirements.txt` 与 `backend/requirements-dev.txt`。
- 依赖 Windows / 真机的能力（`foreground` 置前、`sendinput` / `interception` 后端、真实游戏 ROI）不在 CI 中执行；现有相关测试已用 `skipif` 隔离，CI 不做额外排除。



## 10. 机器可读能力契约（`GET /api/nodes`、`GET /api/actions`）

这两个端点是对外发布能力契约的唯一口。Delias 不再保存手工比对的快照，也不应复制本文档的表格作为第二事实源。

### 10.1 `GET /api/nodes`

- 数据源：`backend/app/contracts.py` 的节点注册表（`node_contracts()`）；响应在既有 `nodes` / `categories` 字段上追加 `contract_version`、`fingerprint`、`node_count`，既有字段语义不变。
- 每个节点给出 `type`、`title`、`category`、`description`、`effectful`、`inputs` / `outputs`（`id` / `label` / `kind`）与 `fields`。
- `fields[]` 的 `required` 表示必填配置；`type` 为 `text|textarea|number|boolean|select|expression|resource|target`；`minimum` / `maximum` / `step` 给出数值范围；`options` 给出 `select` 的枚举。
- `effectful=true` 表示节点会向游戏或外部系统产生副作用（键鼠输入、移动、HTTP 请求、停止运行等）；读屏、识别、纯计算与本地变量写入为 `false`。

### 10.2 `GET /api/actions`

`/api/actions` 现在发布 `harness.tools_schema()` 的全部 33 个动作：22 个运行期既有动作（含此前只在 `execute()` 分支里的 `capture`、`move`，本轮已补进 schema）+ 11 个 Delias 契约动作。它不再只覆盖契约动作，因此 Delias 不需要在测试里维护 `_RUNTIME_ACTIONS` 之类的本地 allowlist。

- 数据源：动作名、`tool`、`description`、`parameters[]` 与 schema 级 `required` 全部由 `harness.tools_schema()` 现场导出，不另存动作表。`harness_contracts` 只补充 schema 无法表达的语义：`ACTION_RISK`（风险分级）、`ACTION_REQUIRED_ANY`（“至少一个”约束）与 `ACTION_OUTPUT_FIELDS` / `RUNTIME_OUTPUT_FIELDS`（成功路径保证输出键）。
- 每个动作的结构：
  - `name` / `tool`（`rocogi_*`）/ `description`
  - `required`：扁平必填参数，与 `tools_schema()` 的 `required` 逐项一致
  - `required_any`：无法用扁平 required 表达的“至少给出一个”约束；仅 `run_workflow` 为 `["workflowId", "name"]`，其余为空
  - `parameters[]`：`name` / `type` / `required`，并原样带出 `enum` / `minimum` / `maximum` / `maxItems` / `items`
  - `output_fields[]`：动作成功后 `result` 顶层保证出现的键
  - `available` / `unavailable_reason`：仅表示当前运行环境是否具备条件
  - `effectful` / `risk`
- `output_fields` 只声明成功路径稳定出现的键。`list_workflows`（`result` 是数组）与 `dex_lookup`（精灵详情与列表两种返回形态没有共同键）声明为空数组，表示没有可跨形态保证的顶层键，而不是没有输出。

### 10.3 风险分级（`effectful` / `risk`）

`risk` 只有三个取值，`effectful` 恒等于 `risk != "read_only"`，供 Delias 在执行前做权限拦截：

| risk | effectful | 语义 | 动作 |
| --- | --- | --- | --- |
| `read_only` | `false` | 只读屏、识别、计算或读取本地数据，不改变游戏与外部系统状态。截图落盘属于本地工件，不计外部副作用。 | `observe`、`capture`、`locate`、`get_state`、`list_workflows`、`run_status`、`dex_lookup`、`pvp_analyze`、`pvp_matchup`、`battle_decision`、`battle_simulate`、`match_template`、`detect_sprites`、`ocr`、`route_plan`、`map_points`、`turn_state`、`vendor_status`、`vendor_blocked` |
| `external_side_effect` | `true` | 会改变游戏输入、窗口焦点、输入后端或后台自动化会话；可以停止，但不是不可逆。 | `press_key`、`click`、`move`、`start_realtime`、`stop_realtime`、`start_tracker`、`stop_tracker`、`stop_run`、`foreground`、`set_input_backend` |
| `irreversible` | `true` | 启动完整工作流、一条龙、vendor 适配器或组合动作，执行后无法保证回滚，需要显式授权。 | `run_workflow`、`run_onedragon`、`sequence`、`vendor_action` |

### 10.4 版本与指纹

- `contract_version` 是契约格式版本，当前为 `1.1.0`。33 动作与 `effectful` / `risk` / `required_any` 均为向后兼容新增，递增 minor；删除或改变既有字段语义递增 major。
- `fingerprint` 是对规范化 JSON（键排序、无多余空白、UTF-8）做 sha256 得到的 64 位小写十六进制串。
- 节点指纹覆盖全部节点契约（忽略 UI 专用 `categoryLabel` / `accent`）。
- 动作指纹覆盖全部 33 个动作的 `name` / `tool` / `description` / `required` / `required_any` / `parameters` / `output_fields` / `effectful` / `risk`，与响应中的动作顺序无关；忽略运行时 `available` / `unavailable_reason`。
- 因此：新增或删除动作、修改参数类型/枚举/范围/必填性、修改输出字段或风险分级，指纹必然变化；同一契约在不同平台、不同 vendor 引擎状态下指纹不变。

### 10.5 Delias 如何消费

1. 启动或定时拉取 `GET /api/nodes` 与 `GET /api/actions`。
2. 对比 `contract_version` 与 `fingerprint`；指纹与本地缓存不同即视为契约变更，重新生成工具/节点映射，而不是人工比对。
3. 以 `/api/actions` 作为唯一动作清单，不再维护 `_RUNTIME_ACTIONS` 之类的本地 allowlist。
4. 执行前读取 `risk`：`read_only` 直接调用；`external_side_effect` 需会话内确认；`irreversible` 需显式人工授权。
5. `available=false` 的动作读取 `unavailable_reason`，不视为契约变更；运行时后端回退仍以动作返回的 `available` / `fallback_reason` 为准。

### 10.6 回归门禁

- `backend/tests/test_capability_contract.py`：33 个动作全覆盖、无重名、`required` / `parameters` / `output_fields` 与 `tools_schema()` 及元数据表一致、风险枚举合法、新增/删除动作与 schema 变化都会改变指纹、`available` 不进入指纹。
- `backend/tests/test_runtime_action_dispatch.py`：22 个运行期动作逐个经 `harness.execute()` 真实分发，断言声明的 `output_fields` 都在成功返回的 `result` 中。
- `backend/tests/test_harness_actions.py`：11 个契约动作的 dispatch 与输出契约继续锁定。

### 10.7 与 `/api/validate` 的边界

`POST /api/validate` 只做单节点字段级校验（节点类型存在、必填字段、表达式语法等），**不查环、不查变量引用**。图级严格校验仍由 Delias 侧校验器负责；本轮没有扩大 `/api/validate` 的职责。
