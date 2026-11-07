# MERGE_MAP · 上游源码合并映射表

> 目标：把 `work\upstream\` 里各工具的**源码/资产**合并成一个新功能套件，自研部分尽量少；暂不做前端画面。
> 本文只做**文件级静态分析**：给出实现归属、依赖、资产、冲突与难度分级，不含任何代码改动。
> 路径均相对 `work\upstream\`；行号为当前本地快照实测（`文件:起-止`）。`sift-map-tracker` 为发布包，目录是双层 `sift-map-tracker/sift-map-tracker/`。

## 0. 结论摘要

1. **视觉 + 截图 + 输入**：`RocoPilot` 与 `Auto-rocokingdom` 是同源分支（API 完全一致，后者多了健壮读图与诊断）。选 **`yorusacri-Auto-rocokingdom`** 做主干（`core/capture.py`、`core/vision.py`、`core/input.py`），RocoPilot 作为补齐来源。
2. **精灵检测**：主干选 **`AutoCapture` 的 ONNX 路径**（`detector.py:458-579`，模型 11.7 MB，仅需 `onnxruntime`）；`RocoPilot` 的 `.pt`（3 个共 59.1 MB）依赖 `torch+ultralytics`，只保留离线训练/转换用途，不进运行时。
3. **SIFT 定位**：主干选 **`Wooziii-roco-map-tracker` 的 `SIFTEngine`**（开源、可改参数、带局部搜索/惯性/重定位，`tracker/engines/sift_engine.py:35-507`）；`luoke_location` 作为**同算法第二实现与参数对照**（`main_sift.py:1185-1268`）；`sift-map-tracker` 的 `service.exe` 仅作**黑盒备选**（地图为 8192×8192，坐标系不同）。
4. **地图与路线**：底图/点位与 `luoke_location` **同源同尺寸 6144×5888**；路线规划选 **`roco-map-tracker`**（最近邻 + 2-opt + 聚类，`tracker/route_planner.py:51-299`），`game-automation` 的 857 行路线器可作备选。
5. **对战**：主干选 **`NRC_AI`**（纯 Python、无重依赖：`src/mcts.py:271-440`、`src/battle.py:230-312`、`src/models.py:52-94`、`data/nrc.db` 1.19 MB）；`roco-balance-lab` 的 `engine.mjs` 是 JS，公式可作**交叉校验**；`Adolph321` 规则集仅作字段补充。
6. **调度/工作流**：`yotta` 是 Go，**不能直接复用**；保留 Rocogi 现有的 Python DAG 实现，yotta 只做 schema 参考（`internal/nodecontract/contract.go`、`internal/run/journal.go`）。`AutoCapture` 的状态机是唯一完整的实时捕捉流程，选为主干（`state_machine.py`）。
7. **不能直接用的上游**：`pets-gen` 只有文档/agents（无源码）、`RocoTools` 无数据文件（爬虫运行时抓取）、`BetterGI` 是 C#、`rocokingdom-ui` 是 React 令牌参考。这四项只能"参考/重写"。
8. **一套 venv 可行但有条件**：运行时（core+detect+battle）可共用 `opencv>=4.9,<5 / numpy>=1.26.4,<2.3 / mss 9.x / pywin32 / onnxruntime`；`torch`、`kornia`、`ultralytics`、`rknn`、`PySide6/eel` 必须做成**可选 extras 或独立进程**。详见 §3.1。

**主干矩阵**

| 能力域 | 主干仓库 | 理由 | 备选 |
| --- | --- | --- | --- |
| 截图/窗口 | Auto-rocokingdom | 同源分支中最健壮，PrintWindow+回退，纯 Python | RocoPilot；BetterGI WGC（需 C# 进程） |
| 模板/场景/ROI | Auto-rocokingdom | 健壮读图、诊断、归一化 ROI | RocoPilot（更简单） |
| 精灵检测 | AutoCapture | ONNX 11.7 MB，CPU 可跑；含 letterbox/NMS | RocoPilot `.pt`（离线训练） |
| 输入注入 | game-automation | Interception 封装完整（移动/点击/热键） | RocoPilot/Auto-rocokingdom 的 interception 调用 |
| SIFT | roco-map-tracker | 开源、参数全、局部搜索+惯性+重定位 | luoke_location（精度对照）；sift exe（黑盒） |
| 地图/路线 | roco-map-tracker | 6144×5888 同源资产 + 2-opt/聚类路线 | game-automation；RocoPilot zigzag |
| 对战 | NRC_AI | 纯 Python 全量战斗规则 + MCTS + SQLite | balance-lab（JS 公式校验） |
| 状态机/实时 | AutoCapture | SCAN→TRACK→AIM→THROW→VERIFY 完整 | RocoPilot modes |
| 工作流 | （保留 Rocogi Python） | yotta 为 Go，不可直接复用 | yotta schema |
| 图鉴 | NRC `nrc.db` | 461/491/21,331 行可直接查 | RocoTools 字段模型（无数据） |

## 1. 39 个组件逐项映射

难度图例：**A**=直接 import 复用；**B**=改配置/路径；**C**=需写适配层；**D**=需重写核心。

### 1.1 截图引擎 capture（5）

| 组件 | 实现归属（路径:行） | 依赖 | 资源资产 | 冲突与选型 | 难度 |
| --- | --- | --- | --- | --- | --- |
| `capture.mock_window` | 无上游；Rocogi `backend/app/adapters/mock.py` | 无 | 无 | 无重复 | A |
| `capture.windows_window` | `babalae-better-genshin-impact/Fischless.GameCapture/Graphics/GraphicsCapture.cs:15`、`BitBlt/BitBltCapture.cs:8`；`Makapic-RocoPilot/core/capture.py:10-50`；`yorusacri-Auto-rocokingdom/core/capture.py:14-65` | RocoPilot: `pywin32`,`cv2`；BetterGI: C#/WinRT/D3D11 | 无 | PrintWindow（可后台）vs WGC（前台高帧）vs BitBlt；**选 Auto-rocokingdom 的 PrintWindow 路径**，WGC 作可选进程 | C（统一接口） |
| `capture.frame_digest` | 无上游；Rocogi `adapters/frame.py` | 无 | 无 | 无 | A |
| `capture.scene_switch` | 无上游（上游都接真实画面） | 无 | 无 | 无 | A |
| `capture.foreground` | `Makapic-RocoPilot/core/window.py:15-53`（`find_window_by_keyword`/客户区矩形）；BetterGI 窗口激活 | `win32gui`,`ctypes` | 无 | 三处都薄；直接取 RocoPilot | B |

### 1.2 视觉识别 vision（6）

| 组件 | 实现归属（路径:行） | 依赖 | 资源资产 | 冲突与选型 | 难度 |
| --- | --- | --- | --- | --- | --- |
| `vision.template_match` | `yorusacri-Auto-rocokingdom/core/vision.py:192-236`（主）；`Makapic-RocoPilot/core/vision.py:68-99`；`Tsuann-RocoKingdom-AutoCapture/detector.py:229-318`（模板 UI 检测） | `cv2`,`numpy` | RocoPilot `templates/` 9 个 PNG；AutoCapture `templates/` 仅 1 个 `README.md`（capture_success/fail/battle_end 未随仓库提供） | 三套；Auto-rocokingdom 多了健壮 `imread` 与诊断，**选它**；AutoCapture 提供多模板阈值 | A（需注入 CONFIG） |
| `vision.edge_preprocess` | `Makapic-RocoPilot/core/vision.py:31-38`；`yorusacri-Auto-rocokingdom/core/vision.py:32-45` | `cv2` | 无 | 同源（Canny/灰度/缩放） | A |
| `vision.scene_classify` | `Makapic-RocoPilot/core/battle_classify.py:21-77`；`yorusacri-Auto-rocokingdom/core/battle_classify.py`（同源重复） | `cv2` | 战斗/污染模板 | 同源，取 Auto-rocokingdom | A |
| `vision.roi` | `Makapic-RocoPilot/config.py:59-63`（归一化比例）；`Tsuann-RocoKingdom-AutoCapture/config.yaml:105-110`（offset/scale） | 无 | 无 | 归一化 vs 像素校准；统一成归一化 + 可选校准 | A |
| `vision.sprite_detector` | `Tsuann-RocoKingdom-AutoCapture/detector.py:458-579`（ONNX）、`320-457`（RKNN）、`652-826`（SpriteDetector 编排）；`Makapic-RocoPilot/core/pet_detector.py:9-48`（`ultralytics`） | ONNX 路径：`onnxruntime`,`cv2`,`numpy`；RocoPilot：`torch`,`ultralytics` | AutoCapture `models/` 17.6 MB（onnx 11.7 + pt 5.9）且仅单类"小独角兽"；RocoPilot `models/` 3 个 `.pt` 共 59.1 MB | 重依赖冲突：torch（GB 级）vs onnxruntime（几十 MB）。**ONNX 做主干**，`.pt` 只离线；多类模型需重训 | C（letterbox/输出解析适配） |
| `vision.ocr` | `Makapic-RocoPilot/core/ocr.py:18-53`（ROI 提取+预处理+识别，easyocr 可选） | `cv2`,`numpy`；可选 `easyocr`+`torch` | OCR ROI 配置（`config.py:78-86`） | 仅一套；easyocr 会引入 torch，建议换轻量 OCR 或模板数字识别 | C |

### 1.3 输入引擎 input（5）

| 组件 | 实现归属（路径:行） | 依赖 | 资源资产 | 冲突与选型 | 难度 |
| --- | --- | --- | --- | --- | --- |
| `input.mock` | 无上游；Rocogi `adapters/input.py::MockInput` | 无 | 无 | 无 | A |
| `input.sendinput` | `SCH-CMYK-game-automation/src/engine/controller.py:69-230`（实为 Interception 封装，非 SendInput）；`Makapic-RocoPilot/core/input.py:17-54`；`yorusacri-Auto-rocokingdom/core/input.py:29-60` | `interception-python`,`pywin32` | `interception.dll`（驱动） | **上游没有纯 SendInput 实现**，需自补；现有三条都是 Interception | C（补后端） |
| `input.interception` | `oblitum-Interception/library/interception.h:162-190` + `library/interception.c`；RocoPilot `core/input.py:17-54`；game-automation `controller.py:69-230` | C 库 + Python 绑定；Windows 管理员 | `interception.dll` | 三处重复封装；取 **game-automation**（含移动/点击/热键/上下文锁） | B |
| `input.key_queue` | `SCH-CMYK-game-automation/src/engine/controller.py:109-204`（`move_to`/`_human_move`）；`Tsuann-RocoKingdom-AutoCapture/controller.py:377-534`（拟人移动+PID 微调） | `ctypes`/HID/Interception | 无 | Windows（Interception）vs Linux（`/dev/hidg*`）；拟人曲线以 AutoCapture 更完整，但平台不可直接用 | C |
| `input.hotkey` | `SCH-CMYK-game-automation/src/automation/hotkey.py:14-93`（`RegisterHotKey` + 轮询回调）；`Tsuann-RocoKingdom-AutoCapture/state_machine.py`（HotkeyListener）；BetterGI `Fischless.HotkeyCapture` | `ctypes`/`pynput`/`evdev` | 无 | 平台不同；**Windows 用 game-automation** | B |

### 1.4 SIFT 定位 sift（8）

| 组件 | 实现归属（路径:行） | 依赖 | 资源资产 | 冲突与选型 | 难度 |
| --- | --- | --- | --- | --- | --- |
| `sift.minimap_region` | `zh19990906-luoke_location/main_sift.py:45-67` + `config.py:37-42`；`Wooziii-roco-map-tracker/roco-map-tracker/tracker/engines/sift_engine.py:94-112`；`SCH-CMYK-game-automation/src/engine/minimap_detector.py:19-205` + `automation/route_planner.py:148-183` | `cv2`,`numpy` | 无（截图实时裁剪） | 尺寸互不一致（见 §3.2）；选 **sift_engine 掩膜 + minimap_detector 自动检测** | B |
| `sift.features` | `zh19990906-luoke_location/main_sift.py:117-129`（120000/360 特征）；`Wooziii-roco-map-tracker/.../sift_engine.py:416-507` | `cv2`（SIFT 已并入主包）| 锚点缓存 `.npz` | 参数差异大（全局 12 万 vs 局部）；**选 roco-map 局部搜索** | A |
| `sift.anchor_index` | `zh19990906-luoke_location/map_mask.py:65-146`（`.npz`：`kp/des/map_h/map_w/...`）；`Wooziii-roco-map-tracker/.../hybrid_index.py:17-144` | `numpy` | luoke 运行时生成；roco `hybrid_index.npz` 2.39 MB | 缓存格式不同（键名/层数）；需转换器 | B |
| `sift.homography` | `zh19990906-luoke_location/main_sift.py:1185-1268`（knn+Lowe+RANSAC+`perspectiveTransform`）；`Wooziii-roco-map-tracker/.../sift_engine.py:184-245` | `cv2` | 无 | 同算法不同阈值（0.86 vs 0.90）；取 roco-map | A |
| `sift.trajectory` | `Wooziii-roco-map-tracker/.../sift_engine.py:253-341`（稳定点、惯性预测、重定位）；`zh19990906-luoke_location/main_sift.py`（跟踪/平滑） | `numpy` | 无 | 两套平滑/重定位；roco 参数化更全 | C |
| `sift.kalman_tracker` | `Tsuann-RocoKingdom-AutoCapture/tracker.py:20-367`（`KalmanTracker` + `MultiTracker` IoU 关联） | `numpy` | 无 | 仅此一套；直接取 | A |
| `sift.route_plan` | `Wooziii-roco-map-tracker/.../route_planner.py:51-299`（贪婪+2-opt+聚类）；`SCH-CMYK-game-automation/src/automation/route_planner.py:475-761`；`Makapic-RocoPilot/cruise_capture/cruise_controller.py:55-103`（zigzag） | `numpy` | 点位 JSON | 三种策略；**roco-map 主干**（质量/参数最好），game 备选，zigzag 仅区域巡航 | A |
| `sift.external_tracker` | `sift-map-tracker/sift-map-tracker/service/service.exe`（56.75 MB，PyInstaller 闭源）+ `sift-map-tracker/SiftMapTracker.Client.exe`（150.6 MB）；`SCH-CMYK-game-automation/src/utils/external_position.py:46-229`；`Wooziii-roco-map-tracker/.../service_host.py:155-267` | 子进程 + stdio JSON | 8192×8192 底图 46.35/69.9 MB + `SIFT_features.npz` 76.44 MB | 黑盒 vs 开源；坐标不同（见 §3.2）。建议**仅当需要 8192 高精地图时**启用 | A（当黑盒调用） |

### 1.5 对战引擎 battle（6）

| 组件 | 实现归属（路径:行） | 依赖 | 资源资产 | 冲突与选型 | 难度 |
| --- | --- | --- | --- | --- | --- |
| `battle.dataset` | `ColinHong10-NRC_AI/src/pokemon_db.py:18-315` + `data/nrc.db`；`Adolph321-Adolph/battle-rules-1-200-20261007/`（265 文件） | `sqlite3`（标准库） | `nrc.db` 1.19 MB（pokemon/skill/pokemon_skill）；Adolph 规则集 1.06 MB（`manifest.json`/`rule-index.json`/`index.js`） | NRC 可直接查询；Adolph 是反编译规则，GPL-3.0，仅字段补充 | A |
| `battle.team_builder` | `ColinHong10-NRC_AI/src/team_builder.py:15-157` | 标准库 | 无 | 仅此一套 | A |
| `battle.mcts` | `ColinHong10-NRC_AI/src/mcts.py:271-440`（`MCTS`，默认 200 模拟，`max_rounds=80`）；`src/main.py:101-161`（每方 150 模拟） | `random`,`math`,`ast` | 无 | 纯 MCTS，无 torch；直接取 | A |
| `battle.damage_model` | `ColinHong10-NRC_AI/src/models.py:52-94`（18 属性克制矩阵）；`src/battle.py:230-312`（`DamageCalculator`）；`Pacific-shark-roco-balance-lab/src/engine.mjs:81-121` | 标准库 / Node | 无 | 公式同源；NRC 覆盖特性/天气/连击更全，**NRC 主干**，balance 做交叉校验 | A |
| `battle.turn_state` | **无上游**（AutoCapture 只有战斗模板，无回合结构解析） | `cv2` + OCR | `battle_ui.png` 模板（AutoCapture 缺） | 无重复；需自研/保留 Rocogi 现有实现 | D |
| `battle.responder` | `Makapic-RocoPilot/modes/base.py:11-45` + `modes/ball_pet.py:154-265`；决策接 NRC | `cv2`,`pywin32` | 战斗模板 | 上游只有"检测→动作"，决策链需胶水 | C |

### 1.6 调度引擎 scheduler（9）

| 组件 | 实现归属（路径:行） | 依赖 | 资源资产 | 冲突与选型 | 难度 |
| --- | --- | --- | --- | --- | --- |
| `scheduler.dag` | `yottaapp-yotta/internal/nodecontract/contract.go`（Go）；Rocogi `backend/app/engine/compiler.py` | Go / 标准库 | workflow JSON | yotta 不可 Py 复用；**保留 Rocogi** | D（照抄 yotta 才需要） |
| `scheduler.executor` | `yottaapp-yotta/internal/run/*.go`（如 `journal.go`）；Rocogi `engine/runtime.py` | Go | Run journal | 同上 | D |
| `scheduler.branch` | Rocogi `engine/runtime.py::_run_branch` | 标准库 | 无 | 无上游等价 | A |
| `scheduler.foreach` | Rocogi `engine/runtime.py::_run_foreach` | 标准库 | 无 | 无 | A |
| `scheduler.subgraph` | Rocogi `engine/runtime.py`（`workflow.call`）；yotta 概念参考 | 标准库 | workflow JSON | 概念同源 | A |
| `scheduler.event_bus` | `yottaapp-yotta/internal/run/journal.go:20-60`（`node-attempt/adapter-action/node-status` 三种 kind）；Rocogi `run_manager.py` | Go vs Python | journal 条目 | 事件 schema 不同，需统一（§3.3） | B |
| `scheduler.session_loop` | `Tsuann-RocoKingdom-AutoCapture/state_machine.py:582-615`（主循环注册）；`Wooziii-roco-map-tracker/.../service_host.py:155-267`（stdio 命令循环）；`Makapic-RocoPilot/core/engine.py:110-148`（轮询主循环） | `threading` | 无 | 线程 vs 子进程；建议统一 asyncio/线程池 | C |
| `scheduler.capture_fsm` | `Tsuann-RocoKingdom-AutoCapture/state_machine.py:5-63`（状态枚举/转移表）与全流程；`Makapic-RocoPilot/modes/ball_pet.py:188-265`（`_detect_and_throw`） | `cv2` | 捕捉成功/失败模板 | AutoCapture 最完整（含重试、空视野平移）；**主干** | C（抽成独立 FSM） |
| `scheduler.onedragon_plan` | `babalae-better-genshin-impact/BetterGenshinImpact/Core/Config/OneDragonFlowConfig.cs:11-34`（`TaskEnabledList/TaskOrder/TaskDefinitions`）+ `GameTask/OneDragon/OneDragonTask.cs` | C#/.NET | BetterGI JSON 配置 | 不能直接用；仅参考任务编排语义 | D |

**难度分布**：A=20、B=6、C=9、D=4（共 39）。

## 2. 10 项功能的装配映射

| 功能 | 需要的组件 | 可复用上游实现 | 缺口 / 合并动作 | 难度 |
| --- | --- | --- | --- | --- |
| `onedragon` 一条龙 | dag, executor, branch, foreach, session_loop, capture_fsm, vision.*, input.* | BetterGI `OneDragonFlowConfig`（C# 仅参考）；AutoCapture FSM | 任务排序/循环→workflow 生成器需胶水；BetterGI 不可移植 | C |
| `realtime` 实时任务 | capture, foreground, template, scene_classify, fsm, input, responder | RocoPilot `core/engine.py:110-148` + `modes/`；AutoCapture FSM | 线程模型与事件流需统一；`MODES` 与 FSM 需并成一套 | C |
| `tracker` SIFT 地图追踪 | minimap_region, features, anchor_index, homography, trajectory, kalman, external_tracker | roco-map `SIFTEngine`；luoke 对照；sift exe 备选 | 锚点缓存格式/坐标空间需转换 | B |
| `workflow` 可视化工作流 | dag, executor, branch, foreach, subgraph, event_bus | Rocogi 现有；yotta 概念 | 无（前端暂不做） | A |
| `map` 资源路线 | route_plan + 地图/点位资产 + tracker | roco-map `route_planner.py`；luoke 资产 | 点位版本/坐标统一 | A/B |
| `battle` 对战实验室 | dataset, team_builder, mcts, damage_model | NRC_AI 全套 | 无 | A |
| `dex` 图鉴速查 | dataset（只读） | NRC `nrc.db`；RocoTools 字段模型 | RocoTools **无数据文件**，需用 NRC 字段映射 | B |
| `pvp` PvP 平衡实验室 | dataset, damage_model, mcts | `roco-balance-lab/src/engine.mjs:81-121`（6 人分析逻辑分散在 `src/*.mjs`） | JS→Python 移植；无 Python 实现 | D |
| `pet` 桌宠工坊 | 无核心算法（渲染/交互） | `ElliottZhao666666-rocom-codex-pets-gen` 仅有 `agents/docs/references/scripts`，**无 UI 源码** | 只能自研；RocoPilot overlay（`ball_pet.py:53-142`）可借窗口叠加思路 | C |
| `harness` AI Harness | dag, executor, event_bus, capture, input | 无上游 | 保留 Rocogi 现有 HTTP tool 网关 | A |

## 3. 三项高风险冲突

### 3.1 依赖版本冲突

| 仓库 | Python | 关键依赖（声明值） | 重依赖 |
| --- | --- | --- | --- |
| Makapic-RocoPilot | >=3.11 | opencv>=4.9.0.80, numpy>=1.26.4, mss>=9.0.1, pywin32>=306, interception-python, keyboard>=0.13.5；extras: easyocr(torch>=2, torchvision>=0.15), pet(ultralytics>=8.2) | torch（可选） |
| yorusacri-Auto-rocokingdom | >=3.10 | 同上 + `eel` | torch（可选） |
| Tsuann-RocoKingdom-AutoCapture | — | opencv>=4.8, numpy>=1.24, PyYAML>=5.4, onnxruntime>=1.15；可选 rknn-toolkit-lite2>=2.0, torch>=2.0, ultralytics>=8.0 | onnxruntime；RKNN（ARM） |
| SCH-CMYK-game-automation | — | torch>=2.0,<2.7, torchvision, ultralytics>=8.3,<9, kornia>=0.7, opencv>=4.8,<5, customtkinter>=5.2,<6, mss>=9,<10, interception-python, pywin32>=306, Pillow>=10,<12, numpy>=1.24,<2.3, pyyaml>=6,<7, pynput>=1.7,<2 | torch+kornia（LoFTR/检测） |
| zh19990906-luoke_location | — | opencv-python, numpy, mss, Pillow, requests；`main_ai.py` 另需 torch+kornia(LoFTR) | torch（仅 AI 版） |
| Wooziii-roco-map-tracker | — | opencv-python, numpy, mss, Pillow, PySide6, requests；LoFTR 可选 torch | PySide6 / torch（可选） |
| ColinHong10-NRC_AI | — | fastapi, uvicorn[standard], openpyxl, pandas, beautifulsoup4, requests | 无（战斗核心纯标准库） |
| roco-balance-lab | Node | ESM，无 Python 依赖 | 无 |

**冲突点**

- `numpy`：game-automation 要求 `<2.3`，其余 `>=1.24/1.26.4`。**交集 `>=1.26.4,<2.3` 可行**；opencv 4.9+ 的 wheel 已支持 numpy 2.x，但为稳妥建议锁 `numpy<2`。
- `opencv`：game-automation `<5`，RocoPilot/Auto-rocokingdom `>=4.9`。**交集 `>=4.9,<5` 可行**；SIFT 在主包内（无需 contrib）。
- `torch`：game-automation `<2.7`，RocoPilot/AutoCapture `>=2.0`。**交集 `>=2.0,<2.7` 可行**；但 `ultralytics>=8.3`、`kornia>=0.7`、`easyocr` 会再拉 torchvision 与大量 CUDA 依赖，体积/解析时间不可控。
- `onnxruntime`：仅 AutoCapture 需要，与 opencv/numpy 无冲突；`rknn-toolkit-lite2` **只支持 Linux aarch64（RK3588）**，Windows 装不上。
- `PySide6`（roco-map GUI）与 `eel`/`customtkinter` 互不冲突，但都属于 GUI 层；当前不做前端，建议**全部不装**。
- `interception-python` 需要 Windows + 管理员 + 驱动，无法在 Linux 沙箱运行。

**结论**

1. **一个 venv 可以共存**，但只限：`python 3.11` + `opencv-python>=4.9,<5` + `numpy>=1.26.4,<2.3` + `mss>=9.0.1,<10` + `pywin32>=306` + `onnxruntime>=1.15` + `Pillow>=10,<12` + `PyYAML>=6,<7`。
2. `torch/torchvision/kornia/ultralytics/easyocr` **列为 extras，不默认安装**；只有启用 `.pt` 检测或 LoFTR 时才装。
3. **必须拆进程的三类**：
   - `rknn`（RK3588 设备）→ 独立主机/进程，通过 HTTP/stdio 回传检测框；
   - `sift-map-tracker/service.exe`（Windows 闭源）→ 独立子进程，stdio JSON 协议（参考 `service_host.py:155-267`）；
   - 输入注入（Interception/SendInput）→ 独立进程，便于提权/崩溃隔离，主进程只发动作指令。
4. 若坚持单进程且要 LoFTR，则把 `torch` 固定为 CPU wheel（`2.2–2.6`），并接受 ~2 GB 安装体积；不推荐作为默认发行形态。

### 3.2 坐标系与分辨率差异

| 来源 | 底图尺寸 | 小地图区域 | 坐标系/原点 | DPI/缩放假设 | 证据 |
| --- | --- | --- | --- | --- | --- |
| luoke_location | **6144×5888**（`test_map_z12.png` 32.04 MB） | 150×150，默认 `top=292,left=1853`（可全屏框选覆盖） | `data/map_config.json`：z7，`x_min=-12,y_min=-11,tile=256`，左上原点 | 依赖实际窗口分辨率；框选规避 DPI | `config.py:37-42`、`data/map_config.json` |
| roco-map-tracker | **6144×5888**（`big_map.png` 32.04 MB；`big_map-1.png` 33.49、`-annotated` 32.34） | 用户框选（`Rect`），SIFT `global_downscale=0.5` | `CoordinateTransform.to_pixels(lat,lng)`（`models.py:50-69`），同一 6144×5888 空间 | 支持窗口位置/尺寸配置（`CaptureConfig`/`WindowPosition`） | `tracker/models.py:50-69`、`assets/maps/` |
| sift-map-tracker | **8192×8192**（`logic_map.png` 46.35 MB、`display_map.png` 69.9 MB） | **255×235**，`top=0,left=0` | `MAP_ORIGIN_X=-973, MAP_ORIGIN_Y=-1585` | 客户端按窗口相对坐标；`MAP_ORIGIN` 隐含平移 | `settings.py:2-11` |
| game-automation | `maps/big_map.png` 3.3 MB（尺寸未能读取，疑为 LFS/占位，需核） | 162×162，`top=47,left=1724`（1920×1080，Hough 自动检测；旧值 309/1837 已标注错误） | 与 luoke 同源底图（README 级证据） | 参考 1920×1080；`scale_x/scale_y` 按实际分辨率修正，**警告 DPI 缩放误导** | `utils/sift_config.py:15-19`、`utils/config.py:136-200` |
| RocoPilot / Auto-rocokingdom | 不涉及大地图 | 无小地图裁剪 | 窗口客户区像素 + **归一化 ROI**（`roi_*_ratio`） | 参考 **2560×1600**，`require_exact_resolution=False`；比例制屏蔽分辨率 | `config.py:42-63` |
| AutoCapture | 不涉及大地图 | 无（全画面 1920×1080 HDMI） | 屏幕像素 + `calibration.offset/scale` | 固定 1920×1080 采集 | `config.yaml:5-10,105-110` |

**结论**

1. **统一坐标空间**：以 **6144×5888 + `x_min=-12,y_min=-11,tile=256`** 为唯一 canonical 地图坐标（luoke 与 roco-map 已同源）。所有地图/路线/标记都存这个空间。
2. **8192 空间必须转换**：`8192/6144 = 1.3333`，但 `MAP_ORIGIN(-973,-1585)` 表示两端还存在平移，**不能只按比例缩放**。合并时需要选 3 个已知点做仿射标定，或在边界处转换（sift 结果→canonical）。在不标定前，禁止把 sift exe 的坐标与 6144 底图混用。
3. **小地图区域必须配置化**：已见 150×150、162×162、255×235 三种，且 `top/left` 差异巨大（窗口布局/分辨率导致）。建议：
   - 用 `minimap_detector.py:19-205` 的 Hough 自动检测作为首选；
   - 缓存到本机配置（按 `窗口尺寸 + DPI + 窗口位置` 做 key）；
   - 保留手动框选/覆盖值。
4. **DPI**：Windows 下必须声明 per-monitor DPI aware，并统一用**客户区坐标**（RocoPilot `window.py:15-53`）；game-automation 已显式警告"系统分辨率可能被 DPI 缩放误导"（`utils/config.py` 注释）。所有像素常量（ROI、瞄准偏移、小地图 rect）都应存"参考分辨率 + 比例"而非绝对像素。
5. **分辨率**：RocoPilot 的 2560×1600 归一化比例最稳；AutoCapture 的 1920×1080 绝对像素 + calibration 只适用于固定采集卡方案，合并时应转成比例或 canonical。

### 3.3 配置与日志格式

| 仓库 | 配置载体 | 配置形态 | 日志/输出 | 合并影响 |
| --- | --- | --- | --- | --- |
| RocoPilot | `config.py`（dataclass 常量） | Python 常量，模板/ROI/模型名全硬编码 | 控制台 + `logs/pollute_log.csv` | 需外置为 JSON，否则改配置要改代码 |
| Auto-rocokingdom | `config.py`（dataclass） | 同上，另有 `eel` 前端设置 | 控制台 | 同上 |
| AutoCapture | `config.yaml`（嵌套） | YAML：capture/detector/tracker/controller/automation | `utils.log` → `logs/` | 结构最清晰，可作为**统一配置蓝本** |
| luoke_location | `config.py` 常量 + `data/map_config.json` + `points_data.json` | Python 常量 + JSON 数据 | `out/sift_track_profile.txt`（可选）+ 控制台 | 常量需外置 |
| roco-map-tracker | `tracker/config.py` 默认值 + 用户 JSON | dataclass 默认 + JSON 覆盖 | `service_host.py` stdout JSON 协议（`ready/frame/error`） | 事件/帧协议可复用 |
| sift-map-tracker | `settings.py`（客户端 UI 生成）+ 运行时自有设置 | Python 常量；**非运行源码**（文件头明示） | 子进程 stdio | 只能通过 exe 参数/设置文件控制 |
| game-automation | `gmt/config.json` + `resolution.json` | JSON，SIFT 参数"权威源" | `logging` 文本 | 配置分层最规范（全局+运行时修正） |
| yotta | workflow JSON + Run journal | Graph/DAG JSON；journal 条目（`node-attempt/adapter-action/node-status`） | JSONL 式 journal | 事件 schema 最值得借鉴 |
| NRC_AI | CLI/服务参数 + SQLite | 参数 + 数据 | 控制台/HTTP | 无配置文件，需包一层 |
| balance-lab | Node 配置/数据 JSON | JS/JSON | 控制台/报告 | 仅算法移植需要 |

**统一最小集合（建议）**

1. **一个 `config.json`（v1）**：
   - `paths`：地图、点位、模板、模型、锚点缓存、运行目录；
   - `capture`：`window_title`、`ref_resolution`、`minimap_rect`（含 `dpi_scale`）、`fps`；
   - `engines`：SIFT 参数（`match_ratio/min_match_count/ransac/local_radius`）、检测（`conf/nms/input_size`）、战斗（`simulations/max_rounds`）；
   - `io`：输入后端（`mock/sendinput/interception`）、日志级别。
   各上游的专用配置保留为 `config.upstream.<repo>.json`，由适配层读取，不改上游文件。
2. **事件流 `events.jsonl`**：`{seq, ts, run_id, kind, node_id, payload}`，`kind` 至少覆盖 `node-attempt`、`adapter-action`、`node-status`（对齐 yotta `journal.go:20-60`），并补 `frame/position/action` 三类。
3. **日志**：统一 `ts level module message key=value` 单行文本，禁止上游 CSV/中文自由文本直接进主日志；保留 `pollute_log.csv` 作为可选导出。
4. **版本字段**：`config.json` 与 `events.jsonl` 都带 `schema_version`；合并时先写迁移函数（旧→新），不直接改上游默认值。

## 4. 建议的落地顺序（仅分析结论，不含代码）

1. 先合 **A 类 20 项**：NRC 对战全套（`dataset/team_builder/mcts/damage`）、RocoPilot/Auto-rocokingdom 的 `vision.template_match/edge_preprocess/scene_classify/roi`、`roco-map` 的 `features/homography/route_plan`、AutoCapture 的 `kalman_tracker`、Rocogi 的 DAG 五项。
2. 再合 **B 类 6 项**：`foreground/hotkey/anchor_index/route_plan/external_tracker/event_bus`——主要是路径与配置外置。
3. 然后写 **C 类适配层 9 项**：Windows 窗口统一接口、ONNX 检测 letterbox 解析、OCR、Input 后端、拟人移动、轨迹平滑、session loop、捕捉 FSM、战斗 responder。
4. 最后处理 **D 类 4 项**：`battle.turn_state`（自研）、`scheduler.dag/executor`（保留 Rocogi，不移植 yotta）、`onedragon_plan`（按 BetterGI 语义重写）。
5. **不要动**：`yotta` Go 代码、BetterGI C#、`pets-gen`（无源码）、`rocokingdom-ui`（前端令牌）。

## 5. 附：本次统计口径与限制

- 文件行号来自本地快照的 `Select-String`/`Read` 实测；`sift-map-tracker` 为编译发布包，只有 `settings.py`（客户端设置）+ `service.exe`，无可读运行源码。
- 体积为磁盘实测（MB，按 1 MB=1024 KB）；模板数量：RocoPilot 9 个 PNG、AutoCapture 1 个（缺关键模板）。
- 未做运行时基准（精度/速度以各仓库参数与实现复杂度推断，已在表中标注选型理由）；`game-automation/maps/big_map.png` 尺寸读取失败（疑似占位/特殊格式），未据此下结论。
- 合并许可提示：`Adolph321`、BetterGI 为 GPL-3.0；Interception 为 LGPL-3.0 非商用条款；yotta 为 source-available。本地自用不分发不受影响，但若将来分发，GPL 源码合入会使整个套件受 GPL 约束。
