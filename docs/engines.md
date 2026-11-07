# 引擎分组、动作与完善度

> 本文由 `scripts/verify/gen-engines-doc.py` 依据 `/api/components`、`/api/engines` 生成，
> 数据源是 `backend/app/components.py` 的组元注册表，不是手写清单。改完组元重跑脚本即可刷新。

## 总览

- 引擎 **6** 个、组元 **39** 个、功能 **10** 个
- 功能→组元绑定 **137** 条；被复用的组元 **36**/39（最高复用 7 个功能，单功能专用 3 个）
- 完善度：ready **27** / partial **12** / 能力缺口 **0**
- 平均每个功能装配 13.7 个组元、3.2 个引擎

分组原则：引擎只取「组元」，组元只做一件事；同一能力可被多个功能复用，不在功能里重复实现。

## 引擎

| 引擎 | 名称 | 组元 | ready / partial | 说明 |
| --- | --- | --- | --- | --- |
| `capture` | 截图引擎 | 5 | 2 / 3 | 把窗口、模拟场景统一成带时间戳的帧，供其余引擎消费。 |
| `vision` | 视觉识别 | 6 | 5 / 1 | 模板匹配与场景分类，把像素翻译成可判断的语义。 |
| `input` | 输入引擎 | 5 | 2 / 3 | 同一套按键语义，可在模拟、SendInput、驱动层三种后端间切换。 |
| `sift` | SIFT 定位 | 8 | 5 / 3 | 不读内存，仅用小地图特征点匹配大地图完成实时定位。 |
| `battle` | 对战引擎 | 6 | 5 / 1 | 以 NRC_AI 数据与 MCTS 搜索回答“这一回合出什么”。 |
| `scheduler` | 调度引擎 | 9 | 8 / 1 | 把组元编成 DAG、会话循环或一条龙计划，并统一推送事件。 |

## 执行组

| 组 | 执行入口 | 引擎 | 动作 | 组元 |
| --- | --- | --- | --- | --- |
| 感知引擎 (`sense`) | `RocogiSense` | `capture`, `vision` | `capture`, `classify`, `match`, `observe`, `templates`, `sprites`, `ocr`, `foreground` | 11（ready 7） |
| 输入引擎 (`input`) | `RocogiInput` | `input` | `press`, `click`, `move`, `sequence`, `backend`, `hotkey` | 5（ready 2） |
| 定位引擎 (`sift`) | `RocogiSift` | `sift` | `locate`, `meta`, `points`, `route`, `anchors`, `tracker_info`, `tracker_prepare`, `tracker_launch` | 8（ready 5） |
| 对战引擎 (`battle`) | `RocogiBattle` | `battle`, `dex`, `pvp` | `dex_list`, `dex_detail`, `dex_skills`, `analyze`, `decide`, `simulate`, `matchup`, `meta`, `turn_state` | 6（ready 5） |
| 调度引擎 (`flow`) | `RocogiFlow` | `scheduler` | `workflows`, `run`, `status`, `stop`, `onedragon_plan`, `onedragon_run`, `settings` | 9（ready 8） |
| 统一小引擎 (`core`) | `RocogiEngine` | `capture`, `vision`, `input`, `sift`, `battle`, `scheduler` | `*` | 39（ready 27） |

## 组元明细

### 截图引擎（`capture`）

把窗口、模拟场景统一成带时间戳的帧，供其余引擎消费。

| 组元 | 说明 | 实现 | 状态 | 复用 |
| --- | --- | --- | --- | --- |
| `capture.mock_window` | 模拟窗口 — 合成采集/战斗/小地图场景，离线也能跑完整闭环。 | `adapters/mock.py::MockGameTarget` | ready（模拟场景端到端验证） | 6 功能 |
| `capture.windows_window` | Windows 窗口捕获 — 按窗口标题抓取客户区，失败时回退桌面区域。 | `adapters/mock.py::WindowsGameTarget` | partial（Windows 实机窗口未在当前沙箱验证） | 6 功能 |
| `capture.frame_digest` | 帧摘要 — 统一尺寸、时间戳、缩略图与场景元数据。 | `adapters/frame.py::Frame` | ready | 6 功能 |
| `capture.scene_switch` | 演示场景切换 — 自动 / 采集 / 战斗 / 小地图四种演示态。 | `services.py::set_scene` | partial（仅用于模拟目标演示） | 1 功能 |
| `capture.foreground` | 窗口前台与焦点 — 查找窗口、从最小化恢复并置前，保证截图与输入落在游戏窗口。 | `adapters/window.py::ensure_foreground` | partial（Windows 实机焦点切换未在当前沙箱验证） | 6 功能 |

### 视觉识别（`vision`）

模板匹配与场景分类，把像素翻译成可判断的语义。

| 组元 | 说明 | 实现 | 状态 | 复用 |
| --- | --- | --- | --- | --- |
| `vision.template_match` | 模板匹配 — 多尺度 matchTemplate，返回坐标、分数与阈值判定。 | `adapters/vision.py::match_template` | ready | 4 功能 |
| `vision.edge_preprocess` | 边缘预处理 — 灰度 / Canny / 降采样，提升低对比 UI 的稳定性。 | `adapters/vision.py::preprocess` | ready | 4 功能 |
| `vision.scene_classify` | 场景分类 — 汇总区域分数，归类为采集、战斗、小地图等场景。 | `adapters/vision.py::classify_scene` | ready | 4 功能 |
| `vision.roi` | ROI 解析 — 归一化区域与像素区域互转，供模板与小地图裁剪复用。 | `adapters/vision.py::resolve_roi` | ready | 3 功能 |
| `vision.sprite_detector` | 精灵候选检测 — 优先加载 ONNX 模型；无模型时用轮廓/模板回退，输出候选框。 | `adapters/detector.py::SpriteDetector` | ready（轮廓/模板回退已验证；ONNX 模型可选） | 4 功能 |
| `vision.ocr` | 数字与文本 OCR — 内置数字/百分比识别；安装 Tesseract 后支持中英文通用文本。 | `adapters/ocr.py::read_text` | partial（内置数字/百分比 OCR 已验证；通用中文文本需安装 Tesseract） | 4 功能 |

### 输入引擎（`input`）

同一套按键语义，可在模拟、SendInput、驱动层三种后端间切换。

| 组元 | 说明 | 实现 | 状态 | 复用 |
| --- | --- | --- | --- | --- |
| `input.mock` | 模拟输入 — 只记录按键与点击，不触碰操作系统，用于回放与测试。 | `adapters/input.py::MockInput` | ready | 4 功能 |
| `input.sendinput` | SendInput — 系统级键鼠事件，兼容性优先，无需额外驱动。 | `adapters/input.py::WindowsInput` | partial（Windows 实机未在当前沙箱验证） | 4 功能 |
| `input.interception` | Interception — 驱动层注入，适合高节奏采集与连续移动。 | `adapters/input.py::InterceptionInput` | partial（需要 Interception 驱动，未实机验证） | 4 功能 |
| `input.key_queue` | 按键队列 — 按住时长、连按次数、随机抖动与客户区坐标换算。 | `adapters/input.py::create_input` | ready | 4 功能 |
| `input.hotkey` | 全局热键 — Windows RegisterHotKey，F9 启动实时、F10 停止、F11 切换追踪。 | `hotkeys.py::HotkeyManager` | partial（Windows RegisterHotKey 已实现，未在实机验证） | 2 功能 |

### SIFT 定位（`sift`）

不读内存，仅用小地图特征点匹配大地图完成实时定位。

| 组元 | 说明 | 实现 | 状态 | 复用 |
| --- | --- | --- | --- | --- |
| `sift.minimap_region` | 小地图区域 — 归一化裁剪 + 椭圆掩膜，隔离小地图外的 UI 干扰。 | `adapters/position.py::SiftPositionSource` | ready | 3 功能 |
| `sift.features` | SIFT 特征 — 地图端 6000 特征点，帧端按掩膜实时提取。 | `adapters/position.py::SiftPositionSource._load_map` | ready | 3 功能 |
| `sift.anchor_index` | 锚点索引 — 按最大边长缓存地图锚点到 runtime/cache。 | `adapters/position.py::SiftPositionSource._cache_path` | ready | 3 功能 |
| `sift.homography` | 单应性定位 — Lowe 比值筛选 + RANSAC 内点校验，输出地图坐标。 | `adapters/position.py::SiftPositionSource.locate` | ready | 3 功能 |
| `sift.trajectory` | 轨迹重建 — 会话内轨迹缓冲、置信度过滤与丢失重定位。 | `sessions.py::TrackerSession` | partial（已接卡尔曼平滑与短时预测，丢失重定位仍依赖下一帧 SIFT） | 2 功能 |
| `sift.kalman_tracker` | 卡尔曼与多目标追踪 — 位置平滑、跳变重置；精灵候选按 IoU 关联并保持稳定 ID。 | `adapters/tracking.py::MultiTargetTracker` | ready（位置平滑与 IoU 多目标关联已验证） | 3 功能 |
| `sift.route_plan` | 路线规划 — 按点位最近邻排序并拼接可执行路线。 | `services.py::plan_route` | partial（最近邻路线，未做避障或真实路网） | 2 功能 |
| `sift.external_tracker` | 外置 SIFT Map Tracker — v0.10.2 WPF 客户端 + 自包含 service.exe，可选 Windows 包。 | `optional/sift-tracker/` | partial（Windows WPF 可选包；Linux 只能解包与校验，不能启动） | 1 功能 |

### 对战引擎（`battle`）

以 NRC_AI 数据与 MCTS 搜索回答“这一回合出什么”。

| 组元 | 说明 | 实现 | 状态 | 复用 |
| --- | --- | --- | --- | --- |
| `battle.dataset` | 精灵 / 技能库 — 461 精灵、491 技能的本地 SQLite 数据。 | `vendor/nrc_ai/data/nrc.db` | ready | 7 功能 |
| `battle.team_builder` | 队伍预设 — 读取预设队伍并生成双方初始快照。 | `adapters/battle.py::BattleLab.presets` | ready | 5 功能 |
| `battle.mcts` | MCTS 决策 — 可配置模拟次数与回合上限，输出最优动作序列。 | `adapters/battle.py::BattleLab.decide` | ready | 5 功能 |
| `battle.damage_model` | 伤害与效果模型 — 技能效果扁平化，统一供模拟与响应使用。 | `adapters/battle.py::flatten_effects` | ready | 5 功能 |
| `battle.turn_state` | 战斗回合状态识别 — 读取敌方血条、回合数、技能可用性与污染状态，输出结构化状态。 | `adapters/turn_state.py::read_turn_state` | ready（模拟战斗界面已验证血条/回合/技能；实机 ROI 需校准） | 4 功能 |
| `battle.responder` | 战斗响应 — 实时会话检测到战斗后自动调用决策链。 | `sessions.py::RealtimeSession` | partial（已接回合状态识别，策略仍以配置规则为主） | 2 功能 |

### 调度引擎（`scheduler`）

把组元编成 DAG、会话循环或一条龙计划，并统一推送事件。

| 组元 | 说明 | 实现 | 状态 | 复用 |
| --- | --- | --- | --- | --- |
| `scheduler.dag` | DAG 编译 — 23 种节点契约、环检测与执行顺序计算。 | `engine/compiler.py::compile_graph` | ready | 3 功能 |
| `scheduler.executor` | 节点执行器 — 执行节点、维护变量环境、输出截图证据。 | `engine/runtime.py::Runtime` | ready | 3 功能 |
| `scheduler.branch` | 条件分支 — branch 节点按表达式选择后继路径。 | `engine/runtime.py::Runtime._run_branch` | ready | 2 功能 |
| `scheduler.foreach` | 循环遍历 — foreach 节点按列表迭代并聚合结果。 | `engine/runtime.py::Runtime._run_foreach` | ready | 2 功能 |
| `scheduler.subgraph` | 子图调用 — workflow.call 复用另一张工作流图。 | `engine/runtime.py::Runtime._run_workflow_call` | ready | 2 功能 |
| `scheduler.event_bus` | 事件总线 — seq 事件持久化 + WebSocket 实时回放。 | `run_manager.py::RunManager` | ready | 5 功能 |
| `scheduler.session_loop` | 会话循环 — 实时任务 / 地图追踪的周期线程与状态机。 | `sessions.py::RealtimeSession` | ready | 3 功能 |
| `scheduler.capture_fsm` | 捕捉状态机 — 扫描→丢球→验证→重试，空视野平移搜索（AutoCapture 参考）。 | `sessions.py::RealtimeSession._run` | partial（已接候选检测与跟踪，未接瞄准 PID） | 1 功能 |
| `scheduler.onedragon_plan` | 一条龙计划 — 任务开关、顺序与共享参数。 | `onedragon.py::load_plan` | ready | 2 功能 |

## 功能装配

| 功能 | 路由 | 组元数 | 组元 |
| --- | --- | --- | --- |
| 一条龙 (`onedragon`) | `/onedragon` | 26 | `capture.mock_window` `capture.windows_window` `capture.frame_digest` `vision.template_match` `vision.edge_preprocess` `vision.scene_classify` `input.mock` `input.sendinput` `input.interception` `input.key_queue` `battle.dataset` `battle.team_builder` `battle.mcts` `battle.damage_model` `battle.responder` `battle.turn_state` `capture.foreground` `vision.sprite_detector` `vision.ocr` `scheduler.dag` `scheduler.executor` `scheduler.branch` `scheduler.foreach` `scheduler.subgraph` `scheduler.event_bus` `scheduler.onedragon_plan` |
| 实时任务 (`realtime`) | `/realtime` | 24 | `capture.mock_window` `capture.windows_window` `capture.frame_digest` `vision.template_match` `vision.edge_preprocess` `vision.scene_classify` `input.mock` `input.sendinput` `input.interception` `input.key_queue` `battle.dataset` `battle.team_builder` `battle.mcts` `battle.damage_model` `battle.responder` `battle.turn_state` `capture.foreground` `vision.sprite_detector` `vision.ocr` `input.hotkey` `sift.kalman_tracker` `scheduler.session_loop` `scheduler.capture_fsm` `scheduler.event_bus` |
| 地图追踪 (`tracker`) | `/tracker` | 13 | `capture.mock_window` `capture.windows_window` `capture.frame_digest` `sift.minimap_region` `sift.features` `sift.anchor_index` `sift.homography` `sift.trajectory` `sift.external_tracker` `sift.kalman_tracker` `capture.foreground` `scheduler.session_loop` `scheduler.event_bus` |
| 独立任务 (`workflow`) | `/workflows` | 21 | `capture.mock_window` `capture.windows_window` `capture.frame_digest` `vision.template_match` `vision.edge_preprocess` `vision.scene_classify` `vision.roi` `input.mock` `input.sendinput` `input.interception` `input.key_queue` `battle.turn_state` `capture.foreground` `vision.sprite_detector` `vision.ocr` `scheduler.dag` `scheduler.executor` `scheduler.branch` `scheduler.foreach` `scheduler.subgraph` `scheduler.event_bus` |
| 资源地图 (`map`) | `/map` | 10 | `capture.mock_window` `capture.windows_window` `capture.frame_digest` `capture.foreground` `vision.roi` `sift.minimap_region` `sift.features` `sift.anchor_index` `sift.homography` `sift.route_plan` |
| 对战实验室 (`battle`) | `/battle` | 4 | `battle.dataset` `battle.team_builder` `battle.mcts` `battle.damage_model` |
| 图鉴速查 (`dex`) | `/dex` | 1 | `battle.dataset` |
| PvP 平衡 (`pvp`) | `/pvp` | 4 | `battle.dataset` `battle.team_builder` `battle.mcts` `battle.damage_model` |
| 桌宠工坊 (`pet`) | `/pet` | 1 | `battle.dataset` |
| AI Harness (`harness`) | `/harness` | 33 | `capture.mock_window` `capture.windows_window` `capture.frame_digest` `capture.scene_switch` `capture.foreground` `vision.template_match` `vision.edge_preprocess` `vision.scene_classify` `vision.roi` `vision.sprite_detector` `vision.ocr` `input.mock` `input.sendinput` `input.interception` `input.key_queue` `input.hotkey` `sift.minimap_region` `sift.features` `sift.anchor_index` `sift.homography` `sift.trajectory` `sift.kalman_tracker` `sift.route_plan` `battle.dataset` `battle.team_builder` `battle.mcts` `battle.damage_model` `battle.turn_state` `scheduler.dag` `scheduler.executor` `scheduler.session_loop` `scheduler.event_bus` `scheduler.onedragon_plan` |

## partial 组元与原因

partial 表示「契约已接、能力受外部环境限制」，在组件图谱里如实标注，mock 目标下不影响主链路。

| 组元 | 原因 |
| --- | --- |
| `capture.windows_window` | Windows 实机窗口未在当前沙箱验证 |
| `capture.scene_switch` | 仅用于模拟目标演示 |
| `capture.foreground` | Windows 实机焦点切换未在当前沙箱验证 |
| `vision.ocr` | 内置数字/百分比 OCR 已验证；通用中文文本需安装 Tesseract |
| `input.sendinput` | Windows 实机未在当前沙箱验证 |
| `input.interception` | 需要 Interception 驱动，未实机验证 |
| `input.hotkey` | Windows RegisterHotKey 已实现，未在实机验证 |
| `sift.trajectory` | 已接卡尔曼平滑与短时预测，丢失重定位仍依赖下一帧 SIFT |
| `sift.route_plan` | 最近邻路线，未做避障或真实路网 |
| `sift.external_tracker` | Windows WPF 可选包；Linux 只能解包与校验，不能启动 |
| `battle.responder` | 已接回合状态识别，策略仍以配置规则为主 |
| `scheduler.capture_fsm` | 已接候选检测与跟踪，未接瞄准 PID |

## 引擎参数预设

当前生效：`demo`

| 预设 | 名称 | 目标 | 输入 | 定位源 | 标签 |
| --- | --- | --- | --- | --- | --- |
| `demo` | 演示 / 模拟目标 | mock | mock | mock | 推荐首次使用 |
| `windows_sendinput` | Windows 实机 · SendInput | windows | windows | sift | 实机入门 |
| `windows_interception` | Windows 实机 · Interception | windows | interception | sift | 实机推荐 |
| `low_latency` | 低延迟实时 | windows | interception | sift | 实时优先 |
| `accuracy` | 高精度识别 | windows | windows | sift | 精度优先 |

预设只写引擎参数；窗口标题、输入后端、定位源这类本机信息在「设置」里保存，工作流只带 `targetSlot`。
