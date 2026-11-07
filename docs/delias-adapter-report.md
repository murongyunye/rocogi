# Delias 契约改造报告

日期：2026-11-06
范围：`murongyunyeh/rocogi` 引擎层 / 适配层 / 文档层。
目标：让 Delias 所需工具不再因 rocogi 契约不满足而抛 `NotImplementedError`，并把**做不了的部分写清楚**而不是伪造。

## 1. 结论先行

- 实际不可用清单是 **14 项**，不是背景里说的 13 项：Delias `server/tools/__init__.py` 的 `UNSUPPORTED` 包含 11 个契约错配 + 3 个 `implemented: false`；`registry/tools.yaml` 已扩到 38 个工具。
- 分类结果：**A 类 8 项**（引擎有数据但字段没暴露）、**B 类 3 项**（引擎能力缺失但上游已有实现）、**C 类 3 项**（确实做不了）。
- 11 项已在 rocogi 服务端新增独立 harness 动作，字段按 Delias `tools.yaml` 输出契约生成，并已在 `harness.execute` 接线（import、dispatch、`tools_schema()` 合并、manifest 能力项）；**3 项 C 类未改一行代码**。
- **未修改 `vendor/` 与 `upstream/` 下任何上游源码**，也未删除、改写任何文件或历史。
- **本机没有执行过任何测试或真实截图**（任务约束禁止写入磁盘与 clone）；接线正确性改由 GitHub Actions 上的 pytest job 验证，真实截图仍需要 Windows 真机。
- 接线曾在 `769dc61` 被 `backend: import source` 重导入覆盖，11 个动作重新变成死代码；本次已按 `c9c912d` 原设计恢复，并新增回归测试与 push 触发的 pytest 门禁。

## 2. 核对依据

只读参考（Delias）：

- `registry/tools.yaml`：每个工具的 `input` / `output` / `engine.action` / `implemented`。
- `server/tools/__init__.py`：`UNSUPPORTED` 映射与 `HARNESS_ACTIONS`。
- `server/tools/adapters.py`：`UnsupportedAdapter` 抛 `NotImplementedError`。
- `server/app.py` / `server/registry.py`：`/v1/tools` 的 `available = spec.implemented and adapter.ready`。

rocogi 侧实现位置：

| 模块 | 作用 |
| --- | --- |
| `backend/app/harness_actions.py` | 11 个新动作的参数校验、图像/地图/子进程调用 |
| `backend/app/harness_contracts.py` | 纯字段映射（无图像依赖） |
| `backend/app/engine_vendor.py` | 以子进程只读调用 `suite/engines/vendor/engine_main.py` |
| `backend/app/harness.py` | 接入分发；既有动作不变 |
| `backend/tests/test_harness_contracts.py` | 字段映射单测 |
| `backend/tests/test_harness_actions.py` | 11 个动作的接线、schema 必填字段与 `execute` 端到端回归 |
| `.github/workflows/pytest.yml` | push / pull_request 上运行 `python -m pytest -q` |

> 为什么落在服务端而不是 `suite/engines/*/engine_main.py`：Delias 只走 `POST /api/harness/act`；`/v1/tools` 可用性取决于 harness 适配器（`adapter.ready`），只改 CLI 引擎不会消除 `NotImplementedError`。

## 3. 逐工具清单

### A 类：引擎已有数据，补齐契约字段（8 项）

| 工具 | 改动文件 | 新增 / 变化字段 | 语义与取值范围 | 仍存在的限制 |
| --- | --- | --- | --- | --- |
| `delias.match_template` | `harness_actions.py`、`harness_contracts.py` | `matched`、`score`、`points[]`（`x`/`y`/`w`/`h`/`cx`/`cy`/`score`）、`frame` | 坐标是整帧像素；`score` 为 OpenCV `TM_CCOEFF_NORMED` 结果，已裁剪到 `0..1`，不是概率 | `matched=false` 时 `points` 为空；未在真机截图验证；阈值默认 0.8 |
| `delias.detect_sprites` | 同上 | `candidates[]`（`bbox{x,y,w,h}` / `confidence` / `cx` / `cy` / `label` / `track_id`）、`count`、`source`、`roi`、`model`，并保留原始 `sprites[]` | `confidence` 即检测器 `score`，按 `min_confidence` 过滤；`bbox` 为整帧像素 | `track_id` 恒为 `null`：检测器不做跨帧关联，不伪造 ID；无 ONNX 模型时回退模板/显著性，`confidence` 不可跨版本比较 |
| `delias.ocr` | 同上 | `text`、`value`、`confidence`、`mode`、`chars`、`source`、`roi`、`frame` | `value` 取识别文本中第一个数字，保留文本单位：`"45%"` → 45.0，`"回合 12"` → 12.0；`mode=text` 或无数值时 `null` | 内置字形只覆盖数字/百分比；通用中文需安装 Tesseract，未安装时 `text` 模式返回空文本 |
| `delias.foreground` | 同上 | `focused`、`hwnd`（字符串）、`supported`、`restored`、`foreground`、`reason` | `focused` = 调用后目标窗口确实在前台；`supported=false` 表示平台不支持（非 Windows） | 仅 Windows 有意义；容器/Linux 必然 `focused=false`；会改变前台窗口，非幂等 |
| `delias.set_input_backend` | 同上 | `backend`、`available`、`fallback_reason`、`requested` | `sendinput` 别名到引擎的 `windows` 后端（`WindowsInput` 即 SendInput）；构造失败则 `available=false`、`backend=mock` | `interception` 需已安装驱动并重启；`windows` 在非 Windows 上会失败并降级；未实机验证 |
| `delias.route_plan` | 同上 | `route[]`、`total_distance`、`count`、`leg_distance`、`start`、`estimated_minutes`（标签模式） | 距离单位与 `MapData.distancePx` 一致，为地图像素；`points` 输入用与引擎一致的贪心最近邻，距离相同取原始下标更小者 | 不是全局最优，也不避障或走真实路网；地图像素不等同于游戏世界坐标 |
| `delias.map_points` | 同上 | `points[]`、`total` | `total` 是过滤后的总数，`points` 可能被 `limit` 截断；坐标来自本地地图数据 | 只读本地资源，不实时探测；`mark_type` 为整数；坐标空间为地图 canonical 像素 |
| `delias.turn_state` | 同上 | `turn`、`enemyHp`、`skills[]`、`polluted`、`phase`、`scene`、`enemy`、`ocr`、`rois`、`frame` | `enemyHp` 直接取 `enemy.hpPercent`，是血条亮色像素占比换算的 `0..100` 整数；非战斗场景 `phase="not_battle"`、`turn=null` | 不是游戏内精确 HP；实机 ROI 需重新校准；技能条只识别已配置槽位 |

### B 类：能力在上游，适配层转接（3 项）

| 工具 | 改动文件 | 新增 / 变化字段 | 语义与取值范围 | 仍存在的限制 |
| --- | --- | --- | --- | --- |
| `delias.vendor_status` | `engine_vendor.py`、`harness_contracts.vendor_contract`、`harness_actions.py` | `adapters{}`（按适配器名索引，含 `repo`/`status`/`blockers`/`checks`/`resolution`）、`adapted`、`resolved`、`pendingReboot`、`partial`、`contractBlocked`、`count` | `adapters` 按 Delias 契约保持**对象**形态；计数原样来自引擎；引擎失败时 `ok=false` 并附 `error` | 需要 `suite/engines/vendor/engine_main.py` 与 `vendor/adapters/*` 存在；子进程执行，耗时较长；不推测、不补写适配器状态 |
| `delias.vendor_action` | 同上 | 平铺的适配器 JSON：`status`、`checks[]`、`blockers[]`、`seconds`、`components[]`、`returncode` | `action` 枚举与 `engine_vendor.ACTIONS` 一致（9 个）；单适配器返回码非 0 时 `ok=false` | 只跑适配器自检，不等同于游戏内动作成功；许可为上游事实（GPL / CC BY-NC / 未声明），不得打包分发 |
| `delias.vendor_blocked` | 同上 | `adapters{}`、`blockedCount`、`count` | 逐项执行阻塞适配器自检，`blockers` 原样返回 | 同 `vendor_status` 的依赖；`blocked` 适配器不得当作可用 |

### C 类：确实做不了，不动代码（3 项）

这 3 项在 Delias `registry/tools.yaml` 里本身就是 `implemented: false`，原因不在 rocogi 引擎契约，而在于缺少必要的定义层或部署边界。

| 工具 | 阻塞原因 | 需要的前提条件 |
| --- | --- | --- |
| `delias.build_workflow` | rocogi 只有 `POST /api/workflows` 接受**显式图**，没有任何 intent→graph 编译器或可审计的规划层。Delias 契约只给 `intent` + `constraints`，若在 rocogi 侧用规则硬凑，就是把“意图理解”伪造成确定性映射，`workflowId` 也没有真实出处。 | 先由 Delias 定义 intent 语法、允许的节点/参数白名单与失败语义；或引入可审计的规划器。前提未就绪前不实现。 |
| `delias.verify_run` | `registry/tools.yaml` 未定义 `expectations` 的结构与判定规则（只是在描述里出现词），没有“通过/失败”的判定依据。实现它必然要凭想象定义字段与容差。 | Delias 先给出 `expectations` schema（字段、比较运算符、容差、超时）；之后 rocogi 可基于已有 `run_status` 与回放数据实现。 |
| `delias.deploy` | Deploy 属于 Delias 自身发行/部署动作；rocogi 是本地 headless 引擎，没有部署目标、凭据、镜像仓库或权限模型，引擎层没有可复用的实现。 | 由 Delias 部署流水线实现；若需要 rocogi 产出制品，应先定义制品格式与校验方式。 |

## 4. 向后兼容

- 11 个动作全部是**新增的独立 action**，不复用既有 action 名，不改既有字段名与语义。
- `harness.execute` 仅在剥离 `rocogi_` 前缀后调用新分发；未命中时原流程不变。
- `detect_sprites` 在 `candidates` 之外保留原始 `sprites[]`；`turn_state` 保留 `enemy` / `ocr` / `rois`；vendor 新动作直接返回引擎已有结构。
- `match_template` / `ocr` 的 `roi` 同时接受 Delias 的 `{x,y,w,h}` 对象与既有的 `[x,y,w,h]` 数组；非法 roi 返回错误而不是静默回退全图（避免误匹配）。

## 5. 验证状态（请勿误读）

| 状态 | 内容 |
| --- | --- |
| 静态实现 + CI | 字段映射、动作分发、vendor 子进程调用、文档与单测文件均已提交；`.github/workflows/pytest.yml` 在 Ubuntu + Python 3.12 上运行既有测试与新增回归测试；真实游戏截图仍未执行 |
| 需要真机（Windows）验证 | `foreground` 置前、`set_input_backend` 的 `sendinput` / `interception`、以及 `match_template` / `ocr` / `detect_sprites` / `turn_state` 在真实游戏画面上的 ROI 与阈值 |
| 需要特定权限/硬件 | `interception` 需驱动安装并重启；通用中文 OCR 需 Tesseract；`detect_sprites` 的 ONNX 路径需模型文件 |
| 需要运行环境 | vendor 三动作需 `suite/engines/vendor/` 及其解释器/依赖存在，否则返回 `ok=false` 与错误详情 |

## 5.1 接线覆盖事故与恢复

| 提交 | 内容 | 结果 |
| --- | --- | --- |
| `c9c912d` | `feat(harness): dispatch Delias contract actions without changing existing actions` | 在 `harness.py` 增加 4 处接线：import、`tools_schema()` 合并、manifest 4 个能力项、`execute()` 中的 `contract_actions.dispatch(...)` 早返回 |
| `769dc61` | `backend: import source` | 重导入 `harness.py` 时覆盖上述 4 处，净删 10 行；11 个动作重新变成只定义、不接线的死代码，真实调用退回 `unknown action` |
| 本次提交 | 按 `c9c912d` 原样恢复 4 处接线，不改既有动作 | 新增 `backend/tests/test_harness_actions.py` 与 `.github/workflows/pytest.yml`，防止再次被静默覆盖 |

- 首次真实 pytest 暴露既有用例 `test_route_helpers_report_pixel_distance` 的期望值与 `route_from_points` 的开放路径语义不符：`start(0,0) -> (0,0) -> (3,4)` 的正确总距离是 5.0，不是 10.0。已修正期望值并补充分段距离断言；未删除或跳过任何用例。

恢复原则：按原设计恢复，不重新设计分发方式；`dispatch` 未命中仍返回 `None`，`harness.execute` 对未知动作的行为保持不变。

## 6. Delias 侧仍需的改动（不在本仓库范围）

本次只保证 rocogi 能吐出契约字段；Delias 的 `NotImplementedError` 要真正消失，还需在 Delias 仓库：

1. 从 `server/tools/__init__.py` 的 `UNSUPPORTED` 移除这 11 项，改为 `HARNESS_ACTIONS` 映射：
   `match_template`→`match_template`、`detect_sprites`→`detect_sprites`、`ocr`→`ocr`、`foreground`→`foreground`、
   `set_input_backend`→`set_input_backend`、`route_plan`→`route_plan`、`map_points`→`map_points`、
   `turn_state`→`turn_state`、`vendor_status`→`vendor_status`、`vendor_action`→`vendor_action`（带 `params.action`）、
   `vendor_blocked`→`vendor_blocked`。
2. `vendor_action` 需要把适配器名作为 `params.action` 传入。
3. `/v1/tools` 的 `available` 需重新计算；它同时要求 `spec.implemented` 与 `adapter.ready`。

## 7. 未改变的部分

- `vendor/`、`upstream/` 下没有任何写入；B 类完全是只读调用。
- 未删除文件、未 force push、未改写历史。
- 原有 harness action（`capture` / `observe` / `press_key` / `locate` / `run_workflow` 等）字段未动。


## 8. 机器可读契约发布（替代人工比对）

上一轮 Delias 只能依赖只读快照 `registry/rocogi-contract.json` 拦截 Delias 侧漂移，rocogi 侧变化仍需人工比对。本轮新增：

- `GET /api/nodes`：24 个节点类型契约，直接由 `contracts.py` 注册表导出。
- `GET /api/actions`：11 个 harness 动作契约，直接由 `harness_actions.tools_schema()` 与 `harness_contracts.ACTION_REQUIRED_FIELDS` / `ACTION_OUTPUT_FIELDS` 导出。

两个端点都返回 `contract_version` 与规范化 JSON 的 sha256 指纹；指纹只随契约内容变化。Delias 只需对比指纹并在变化时重新生成映射，**不再需要人工比对 rocogi 侧变更**。字段语义、版本规则与消费方式见 `docs/deepseek-harness.md` 第 10 节。

`POST /api/validate` 的职责不变：只做单节点字段级校验，不查环、不查变量引用。
