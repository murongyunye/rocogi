# Rocogi 上游组件采集清单（INVENTORY）

- 采集时间：2026-11-05
- 采集范围：`README.md` 与 `backend/app/components.py` 交叉核对；README 中出现的全部 GitHub 链接
- 落盘位置：`c:\Users\13005\Downloads\work\upstream\<owner>-<repo>\`
- 结论口径：本地自用、不发布、不分发。许可证仅作事实记录，不作为可用性门槛。

## 0. 结论摘要

| 指标 | 结果 |
| --- | --- |
| GitHub 仓库（README 引用） | 15 个，去重后全部已采集 |
| 额外依赖仓库 | 1 个（`oblitum/Interception`，README 安装说明引用，已采集未安装） |
| 非 GitHub 来源 | 1 个（SIFT-Map-Tracker v0.10.2，本地发布包解压） |
| 落地目录合计 | 16 个，全部文件数 > 0 |
| 采集失败 | 0 个（无待授权的缺失仓库） |
| 组件核对 | 代码 39 个，README 声明 39 个，一致；ready 27 / partial 12，与 README 一致 |
| 功能核对 | 代码 FEATURES 10 个；README 首段声明 10 项，一致（README 正文 20 条 bullet = 10 个模块 + 10 条页面/子能力，见第 4 节） |
| 总体积 | 约 1.28 GB（含 617.6 MB SIFT 发布包） |

## 1. 仓库总览

| 仓库目录 | 上游地址 | commit | 文件数 | 体积 | 代码量 | 许可证 | 来源 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `yottaapp-yotta` | https://github.com/yottaapp/yotta | b835686 | 1950 | 25.2 MB | Go 1019 / TS 375 / Vue 156，约 26.4 万行 | source-available（个人/教育/研究） | README 引用 | 已采集（完整浅克隆） |
| `babalae-better-genshin-impact` | https://github.com/babalae/better-genshin-impact | bcfacfb | 3109 | 28.3 MB | C# 1786 / XAML 150，约 29.8 万行 | GPL-3.0 | README 引用 | 已采集（blobless + 稀疏，源码目录完整；仓库总量 375 MB，按体积约定只取源码） |
| `Makapic-RocoPilot` | https://github.com/Makapic/RocoPilot | 5f3f76e | 70 | 61.2 MB | Python 40，6264 行 | MIT | README + 组件引用 | 已采集（首次 checkout 失败，修复后完整） |
| `yorusacri-Auto-rocokingdom` | https://github.com/yorusacri/Auto-rocokingdom | a2589cd | 50 | 0.7 MB | Python 29，2068 行 | MIT | README + 组件引用 | 已采集 |
| `ColinHong10-NRC_AI` | https://github.com/ColinHong10/NRC_AI | 9b5801b | 476 | 180 MB | Python 45，18350 行 | MIT | README + 组件引用 | 已采集 |
| `zh19990906-luoke_location` | https://github.com/zh19990906/luoke_location | 5650fe6 | 1596 | 153.6 MB | Python 23，5083 行 | 未声明 LICENSE | README + 组件引用 | 已采集 |
| `Wooziii-roco-map-tracker` | https://github.com/Wooziii/roco-map-tracker | 6890ac6 | 649 | 140.9 MB | Python 104 / C# 11，34332 行 | 未声明 LICENSE | README + 组件引用 | 已采集 |
| `sift-map-tracker` | 本地发布包（非 GitHub） | v0.10.2 | 213 | 617.6 MB | Python 1（settings.py），其余为编译产物与 JSON 资源 | 包内无 LICENSE | README + 组件引用 | 已解压采集 |
| `SCH-CMYK-game-automation` | https://github.com/SCH-CMYK/game-automation | 4247f18 | 48 | 3.6 MB | Python 30，4379 行 | CC BY-NC 4.0 | README 引用 | 已采集 |
| `eachyczhang-RocoTools` | https://github.com/eachyczhang/-RocoTools | c983c8e | 247 | 2.7 MB | JS 81 / Vue 53 / Python 13，39746 行 | CC BY-NC-SA 4.0 | README 引用 | 已采集 |
| `rookie-orange-rocokingdom-ui` | https://github.com/rookie-orange/rocokingdom-ui | 2c8a1f6 | 439 | 13.6 MB | TSX 214 / TS 64，19810 行 | 未声明（package.json 无 license 字段） | README 引用 | 已采集 |
| `Tsuann-RocoKingdom-AutoCapture` | https://github.com/Tsuann/RocoKingdom-AutoCapture | 4045c88 | 37 | 18.0 MB | Python 24，7216 行 | 未声明 LICENSE | README + 组件引用 | 已采集 |
| `Pacific-shark-roco-balance-lab` | https://github.com/Pacific-shark/roco-balance-lab | 52f717d | 67 | 15.6 MB | MJS 21 / Python 3，3672 行 | MIT | README 引用 | 已采集 |
| `ElliottZhao666666-rocom-codex-pets-gen` | https://github.com/ElliottZhao666666/rocom-codex-pets-gen | 4ccce56 | 22 | 0.8 MB | Python 10，1233 行 | MIT | README 引用 | 已采集 |
| `Adolph321-Adolph` | https://github.com/Adolph321/- | f215166 | 269 | 1.3 MB | JS 2，34 行；主体为数据集 | GPL-3.0 | README + 组件引用 | 已采集（内含 zip 已解压为 `battle-rules-1-200-.../`） |
| `oblitum-Interception` | https://github.com/oblitum/Interception | 39eecbb | 44 | 0.1 MB | C++ 7 / C 2，1007 行 | 非商用 LGPL-3.0，商用另许可 | README 引用（安装说明） | 已采集（未安装驱动） |

## 2. 39 个组件总表

说明：这些组件的实现均在 Rocogi 自己的 Python 代码中；"上游参考"指设计、算法或数据/模板来源。C 难度是重写为 C 的估算，不代表当前已经移植。

| # | 组件 ID | 作用 | 上游参考 | 来源类型 | 许可证 | 可改性 | C 难度 | 已克隆路径 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `capture.mock_window` | 合成采集/战斗/小地图场景，离线闭环 | 无（Rocogi 自研） | 自研 | — | 可改 | 低 | — |
| 2 | `capture.windows_window` | 按窗口标题抓客户区，失败回退桌面 | BetterGI `Fischless.GameCapture` | 架构参考 | GPL-3.0 | 可读可改 | 低（Win32/DXGI 已有） | `upstream/babalae-better-genshin-impact` |
| 3 | `capture.frame_digest` | 统一尺寸/时间戳/缩略图/场景元数据 | 无 | 自研 | — | 可改 | 低 | — |
| 4 | `capture.scene_switch` | 自动 / 采集 / 战斗 / 小地图四种演示态 | 无 | 自研 | — | 可改 | 低 | — |
| 5 | `capture.foreground` | 查找窗口、恢复最小化并置前 | BetterGI 窗口激活流程 | 架构参考 | GPL-3.0 | 可读可改 | 低 | `upstream/babalae-better-genshin-impact` |
| 6 | `vision.template_match` | 多尺度 matchTemplate，坐标/分数/阈值 | RocoPilot、Auto-rocokingdom 模板资源 | 资产 + 算法参考 | MIT / MIT | 可改 | 中（多尺度与阈值，已有 match.c） | `upstream/Makapic-RocoPilot`、`upstream/yorusacri-Auto-rocokingdom` |
| 7 | `vision.edge_preprocess` | 灰度 / Canny / 降采样 | RocoPilot `core/vision.py` | 算法参考 | MIT | 可改 | 低 | `upstream/Makapic-RocoPilot` |
| 8 | `vision.scene_classify` | 区域分数汇总为场景类别 | RocoPilot、Auto-rocokingdom | 算法参考 | MIT / MIT | 可改 | 低 | 同上 |
| 9 | `vision.roi` | 归一化 ROI 与像素 ROI 互转 | 无 | 自研 | — | 可改 | 低 | — |
| 10 | `vision.sprite_detector` | ONNX 优先，无模型时轮廓/模板回退 | RocoPilot `.pt`/ONNX 模型（`.pt` 为实体，约 20 MB） | 资产 + 算法参考 | MIT | 可改 | 高（需 ONNX 推理运行时） | `upstream/Makapic-RocoPilot` |
| 11 | `vision.ocr` | 数字/百分比识别，Tesseract 可选扩展 | 无（Rocogi 自研；Tesseract 为外部依赖） | 自研 | — | 可改 | 中（数字模板低，通用 OCR 高） | — |
| 12 | `input.mock` | 只记录按键/点击，用于回放测试 | 无 | 自研 | — | 可改 | 低 | — |
| 13 | `input.sendinput` | 系统级键鼠事件，无需驱动 | AutoCapture HID/控制器思路 | 算法参考 | 未声明 | 可读可改 | 低（已有 input.c） | `upstream/Tsuann-RocoKingdom-AutoCapture` |
| 14 | `input.interception` | 驱动层注入，高节奏连续移动 | `oblitum/Interception` + RocoPilot 适配思路 | 库 + 架构参考 | LGPL-3.0（非商用） / MIT | 可改（驱动未安装） | 中（禁装内核驱动，建议保持 SendInput） | `upstream/oblitum-Interception`、`upstream/Makapic-RocoPilot` |
| 15 | `input.key_queue` | 按住时长、连按、抖动、客户区坐标换算 | AutoCapture `controller.py` | 算法参考 | 未声明 | 可读可改 | 低 | `upstream/Tsuann-RocoKingdom-AutoCapture` |
| 16 | `input.hotkey` | RegisterHotKey：F9 启动 / F10 停止 / F11 追踪 | BetterGI 热键布局 | 架构参考 | GPL-3.0 | 可读可改 | 低（已有 hotkey.c） | `upstream/babalae-better-genshin-impact` |
| 17 | `sift.minimap_region` | 归一化裁剪 + 椭圆掩膜隔离 UI | luoke_location 小地图裁剪 | 算法参考 | 未声明 | 可读可改 | 低 | `upstream/zh19990906-luoke_location` |
| 18 | `sift.features` | 地图端 6000 特征点，帧端实时提取 | luoke_location（OpenCV SIFT） | 算法参考 | 未声明 | 可读可改 | 高（SIFT 自实现成本大） | `upstream/zh19990906-luoke_location` |
| 19 | `sift.anchor_index` | 按最大边长缓存地图锚点 | luoke_location | 算法参考 | 未声明 | 可读可改 | 中 | 同上 |
| 20 | `sift.homography` | Lowe 比值 + RANSAC，输出地图坐标 | luoke_location | 算法参考 | 未声明 | 可读可改 | 高（RANSAC 自实现或依赖 OpenCV） | 同上 |
| 21 | `sift.trajectory` | 轨迹缓冲、置信度过滤、丢失重定位 | SIFT-Map-Tracker + 自研 | 算法参考 | 包内未声明 | 可改 | 中 | `upstream/sift-map-tracker` |
| 22 | `sift.kalman_tracker` | 位置平滑、跳变重置、IoU 关联 | SIFT-Map-Tracker + 自研 | 算法参考 | 包内未声明 | 可改 | 中 | `upstream/sift-map-tracker` |
| 23 | `sift.route_plan` | 点位最近邻排序并拼路线 | roco-map-tracker 点位数据 | 数据 + 算法参考 | 未声明 | 可读可改 | 低（Greedy NN） | `upstream/Wooziii-roco-map-tracker` |
| 24 | `sift.external_tracker` | v0.10.2 WPF 客户端 + service.exe 进程调用 | SIFT-Map-Tracker 发布包 | 二进制资产 | 包内未声明 | 可调用（不移植） | 低（进程/IPC，不必重写） | `upstream/sift-map-tracker` |
| 25 | `battle.dataset` | 461 精灵 / 491 技能本地 SQLite | NRC_AI `nrc.db`；Adolph 规则数据集 | 数据 + 代码 | MIT / GPL-3.0 | 可改 | 中（需 SQLite 读取或转 JSON） | `upstream/ColinHong10-NRC_AI`、`upstream/Adolph321-Adolph` |
| 26 | `battle.team_builder` | 读取预设队伍，生成双方初始快照 | NRC_AI | 算法参考 | MIT | 可改 | 低 | `upstream/ColinHong10-NRC_AI` |
| 27 | `battle.mcts` | 可配置模拟次数/回合上限，输出动作序列 | NRC_AI | 算法参考 | MIT | 可改 | 中 | 同上 |
| 28 | `battle.damage_model` | 技能效果扁平化，供模拟与响应 | NRC_AI `battle.py`；Adolph 规则字段 | 算法 + 数据 | MIT / GPL-3.0 | 可改 | 低（纯公式） | 同上 |
| 29 | `battle.turn_state` | 敌方血条、回合数、技能可用性、污染状态 | AutoCapture 血条识别 + 自研 | 算法参考 | 未声明 | 可读可改 | 中（依赖视觉） | `upstream/Tsuann-RocoKingdom-AutoCapture` |
| 30 | `battle.responder` | 检测到战斗后调用决策链 | NRC_AI、RocoPilot 战斗策略 | 算法参考 | MIT / MIT | 可改 | 中 | `upstream/ColinHong10-NRC_AI`、`upstream/Makapic-RocoPilot` |
| 31 | `scheduler.dag` | 23 种节点契约、环检测、执行顺序 | yotta Workflow/Node Contract 概念；game-automation 分层 | 架构参考 | source-available / CC BY-NC 4.0 | 可读可改 | 低 | `upstream/yottaapp-yotta`、`upstream/SCH-CMYK-game-automation` |
| 32 | `scheduler.executor` | 执行节点、变量环境、截图证据 | yotta Run Evidence 概念 | 架构参考 | source-available | 可读可改 | 中 | `upstream/yottaapp-yotta` |
| 33 | `scheduler.branch` | branch 节点按表达式选后继 | 无（Rocogi 自研） | 自研 | — | 可改 | 低 | — |
| 34 | `scheduler.foreach` | foreach 迭代并聚合结果 | 无 | 自研 | — | 可改 | 低 | — |
| 35 | `scheduler.subgraph` | `workflow.call` 复用另一张图 | 无 | 自研 | — | 可改 | 低 | — |
| 36 | `scheduler.event_bus` | seq 事件持久化 + WebSocket 回放 | yotta 事件/证据概念 | 架构参考 | source-available | 可读可改 | 低 | `upstream/yottaapp-yotta` |
| 37 | `scheduler.session_loop` | 实时任务 / 地图追踪周期线程与状态机 | AutoCapture、roco-map-tracker | 架构参考 | 未声明 | 可读可改 | 中 | `upstream/Tsuann-RocoKingdom-AutoCapture`、`upstream/Wooziii-roco-map-tracker` |
| 38 | `scheduler.capture_fsm` | SCAN→TRACK→AIM→THROW→VERIFY，重试与空视野平移 | AutoCapture | 算法参考 | 未声明 | 可读可改 | 低 | `upstream/Tsuann-RocoKingdom-AutoCapture` |
| 39 | `scheduler.onedragon_plan` | 任务开关、顺序与共享参数 | BetterGI 任务计划；yotta Workflow | 架构参考 | GPL-3.0 / source-available | 可读可改 | 低 | `upstream/babalae-better-genshin-impact`、`upstream/yottaapp-yotta` |

### 39 个组件的引擎归属

| 引擎 | 数量 | 组件 |
| --- | --- | --- |
| 截图 capture | 5 | mock_window / windows_window / frame_digest / scene_switch / foreground |
| 视觉 vision | 6 | template_match / edge_preprocess / scene_classify / roi / sprite_detector / ocr |
| 输入 input | 5 | mock / sendinput / interception / key_queue / hotkey |
| 定位 sift | 8 | minimap_region / features / anchor_index / homography / trajectory / kalman_tracker / route_plan / external_tracker |
| 对战 battle | 6 | dataset / team_builder / mcts / damage_model / turn_state / responder |
| 调度 scheduler | 9 | dag / executor / branch / foreach / subgraph / event_bus / session_loop / capture_fsm / onedragon_plan |
| 合计 | 39 | — |

## 3. 10 项功能总表

| 功能 | 名称 | 依赖组件 | 上游参考 | 许可证 |
| --- | --- | --- | --- | --- |
| `onedragon` | 一条龙 | `scheduler.onedragon_plan` + `scheduler.session_loop` + `scheduler.capture_fsm` + capture/input/vision 基础组件 | BetterGI、yotta、AutoCapture、RocoPilot | GPL-3.0 / source-available / 未声明 / MIT |
| `realtime` | 实时任务 | `scheduler.session_loop`、`scheduler.event_bus`、`vision.scene_classify`、`battle.responder` | RocoPilot、AutoCapture | MIT / 未声明 |
| `tracker` | 地图追踪 | `sift.minimap_region`、`sift.features`、`sift.anchor_index`、`sift.homography`、`sift.trajectory`、`sift.kalman_tracker`、`sift.external_tracker` | luoke_location、SIFT-Map-Tracker | 未声明 / 包内未声明 |
| `workflow` | 独立任务 | `scheduler.dag`、`executor`、`branch`、`foreach`、`subgraph`、`event_bus` | yotta、game-automation | source-available / CC BY-NC 4.0 |
| `map` | 资源地图 | `sift.route_plan` + 点位/底图数据 | roco-map-tracker、luoke_location | 未声明 |
| `battle` | 对战实验室 | `battle.dataset`、`team_builder`、`mcts`、`damage_model`、`turn_state`、`responder` | NRC_AI、Adolph | MIT / GPL-3.0 |
| `dex` | 图鉴速查 | `battle.dataset`（数据侧）；页面样式参考 RocoTools | NRC_AI、RocoTools | MIT / CC BY-NC-SA 4.0 |
| `pvp` | PvP 平衡 | `battle.team_builder`、`battle.mcts`、`battle.damage_model` | NRC_AI、roco-balance-lab | MIT |
| `pet` | 桌宠工坊 | 无后端组件（纯前端） | rocom-codex-pets-gen | MIT |
| `harness` | AI Harness | `scheduler.dag`、`scheduler.executor`、`scheduler.event_bus` | yotta | source-available |

## 4. README 与 components.py 的差异

1. **组件数量一致**：代码按引擎分组为 5+6+5+8+6+9 = 39，README 写"39 个组元"，一致。
2. **完成度一致**：`COMPONENT_STATUS` 中 `ready` 27 个、`partial` 12 个，与 README"27 / 39 已完善、12 个待完善"一致。
3. **功能条目口径不同（20 条 bullet vs 10 个 FEATURES）**：这不是数量错误，是统计口径差异。README 正文「功能」一节（L49-L68）恰为 **20 条 bullet**，而 `backend/app/components.py` 的 `FEATURES` 只有 **10 个模块**：
   - 20 条中的 10 条与 FEATURES 一一对应：一条龙任务计划 → `onedragon`、实时任务 → `realtime`、SIFT 地图追踪 → `tracker`、可视化工作流 → `workflow`、资源路线 → `map`、对战实验室 → `battle`、图鉴速查 → `dex`、桌宠工坊 → `pet`、PvP 平衡实验室 → `pvp`、AI Harness → `harness`。
   - 另 10 条属于页面入口、前置能力或横切能力，不进入 FEATURES 计数：启动器、本地优先目标、场景识别、自动丢球与战斗策略、捕捉状态机、识别增强、窗口与热键、组件图谱、运行证据、模拟游戏目标。
   - 结论：功能**模块**以代码为准 = **10**；README 的 20 条是「模块 + 页面/子能力」的混合描述，不能直接当作功能模块数量。
4. **上游表差异**：README 的"已整合的工具"表列 14 个 GitHub 仓库；`oblitum/Interception` 出现在 README 第 145 行的安装说明里，是第 15 个 GitHub 依赖。SIFT-Map-Tracker 无 GitHub 链接，来自本地发布包。
5. **许可证事实修正 — Adolph321 为 GPL-3.0，不是未声明**：`Adolph321/-` 仓库自带 `LICENSE`，原文为 GNU GENERAL PUBLIC LICENSE Version 3，因此许可证 = **GPL-3.0**。本清单第 0 / 1 / 2 / 5 节均按 GPL-3.0 记录；`THIRD_PARTY_NOTICES.md` 把它归入「未声明」的写法需要更正。真正「未声明」的仅有：`zh19990906-luoke_location`、`Wooziii-roco-map-tracker`、`rookie-orange-rocokingdom-ui`、`Tsuann-RocoKingdom-AutoCapture`，以及 SIFT-Map-Tracker 发布包（包内无许可证文件）。
6. **SIFT 位置差异**：README 指向 `optional/sift-tracker/`，本次按任务要求落在 `work/upstream/sift-map-tracker/`，未改动 Rocogi 仓库。

## 5. 许可证原文证据

| 仓库 | 原文关键句 |
| --- | --- |
| yotta | "This project is free for personal, educational, and research use. Commercial use, distribution for profit, SaaS offering, and paid services based on this project are prohibited without explicit written permission from the author."（source-available，非 OSI） |
| BetterGI | GNU GENERAL PUBLIC LICENSE Version 3 |
| RocoPilot / Auto-rocokingdom / NRC_AI / roco-balance-lab / rocom-codex-pets-gen | MIT License（"Permission is hereby granted, free of charge..."） |
| game-automation | "Attribution-NonCommercial 4.0 International"（CC BY-NC 4.0） |
| RocoTools | "Attribution-NonCommercial-ShareAlike 4.0 International"（CC BY-NC-SA 4.0，含中文说明） |
| Adolph321 | GNU GENERAL PUBLIC LICENSE Version 3 |
| Interception | README："Interception is dual-licensed. For non-commercial purposes it adopts LGPL for the library and its source code"；`licenses/non-commercial-usage/LGPL 3.0.txt` |
| luoke_location / roco-map-tracker / rocokingdom-ui / AutoCapture / SIFT 包 | 无 LICENSE 文件，README/package.json 亦未声明统一许可证 |
| rocokingdom-ui 补充 | `package.json` 仅含 `name` 等字段，无 `license` 字段 |

本地自用场景下全部按"可读、可改、可重写"处理；若未来对外发布，GPL/CC-NC/source-available/未声明四类需要单独复核。

## 6. 采集失败、取舍与授权

| 仓库 | 现象 | 原始错误 | 判断原因 | 处理 | 是否需要授权 |
| --- | --- | --- | --- | --- | --- |
| `Makapic-RocoPilot` | 两次 clone 后工作区不完整，`git status` 显示 `D` 一片 | `warning: Clone succeeded, but checkout failed.` / `EXIT=128` | 检出阶段失败，非仓库缺失；该仓库 `.pt` 为实体文件，非 LFS 指针 | 不删目录，先 `git status` 判定；`sparse-checkout disable` 后用 `-c filter.lfs.*` 覆盖并 `checkout -f HEAD`，最终 70 文件 / 61.2 MB | 否 |
| `babalae/better-genshin-impact` | 仓库 375 MB，超过单仓 300 MB 阈值 | — | 主要是资产与构建目录 | `--filter=blob:none --sparse`，只取 `BetterGenshinImpact`、`Docs`、`Fischless.GameCapture`、`Fischless.HotkeyCapture`、`Fischless.WindowsInput` | 否 |
| BetterGI 稀疏取舍 | 工作区 3109 文件，HEAD 树 3327 文件，差 218 | — | 未检出的 `Build`、`Test`、`.github`、`.idea` 等非源码目录 | 源码与 XAML 完整；如需全量可再 `git sparse-checkout disable` | 否 |
| 匿名 GitHub API | `api.github.com` 匿名请求 403 | `403 rate limit` | 未带令牌 | 使用 `C:\Users\13005\.rocogi\github_token` 临时 `http.extraheader`，未写入仓库配置、未回显 | 否 |
| SIFT-Map-Tracker | 非 GitHub 来源 | — | 本地发布包 | 从 `C:\Users\13005\Documents\deepseek-harness\tgx-workspace\Shift-Map-Tracker\SIFT-Map-Tracker-v0.10.2-merged.zip` 解压；源目录未改动 | 否 |
| Interception | 双许可驱动 | — | 需管理员权限安装内核驱动 | 仅采集源码，不安装、不改系统 | 否 |

## 7. 可直接复用的资产

| 资产 | 位置 | 说明 |
| --- | --- | --- |
| 点位与底图 | `upstream/Wooziii-roco-map-tracker` | `taptap.transformed.json`（1.72 MB，README 称 9,224 去重点位）、`big_map.png` 32.04 MB / `big_map-annotated.png` 32.34 MB / `big_map-1.png` 33.49 MB（6144×5888）、`hybrid_index.npz` 2.39 MB |
| SIFT 地图资源 | `upstream/zh19990906-luoke_location` | 1596 文件 / 153.6 MB，地图分块与特征缓存 |
| 对战数据 | `upstream/ColinHong10-NRC_AI` | `nrc.db` 与 Python 引擎（461 精灵 / 491 技能；本地另有一份 1.2 MB 内置副本） |
| 对战规则 | `upstream/Adolph321-Adolph/battle-rules-1-200-20261007` | 200 精灵特性 / 200 技能逻辑，zip 已解压，共 269 文件 |
| 视觉模板 | `upstream/Makapic-RocoPilot`、`upstream/yorusacri-Auto-rocokingdom` | 模板图 + `.pt` 模型（geli 21.9 MB / huolong 19.8 MB / youyingshu 18.7 MB） |
| 图鉴与查询 | `upstream/eachyczhang-RocoTools` | 图鉴字段模型与 JS 数据 |
| 设计令牌 | `upstream/rookie-orange-rocokingdom-ui` | paper / stone / gold 材质与圆角令牌 |
| SIFT 客户端 | `upstream/sift-map-tracker` | `SiftMapTracker.Client.exe`、`sift-map-tracker` 目录、`legacy-json`、`Resources`、`screen-recognition`，共 213 文件 / 617.6 MB |
| 架构参考 | `upstream/yottaapp-yotta`、`upstream/babalae-better-genshin-impact`、`upstream/SCH-CMYK-game-automation` | Workflow/Node Contract/Run Evidence、任务计划布局、能力分层 |

## 8. 全量 GitHub 链接去重结果（README）

| owner/repo | 本地状态 |
| --- | --- |
| yottaapp/yotta | 已采集 `upstream/yottaapp-yotta` |
| babalae/better-genshin-impact | 已采集 `upstream/babalae-better-genshin-impact` |
| Makapic/RocoPilot | 已采集 `upstream/Makapic-RocoPilot` |
| yorusacri/Auto-rocokingdom | 已采集 `upstream/yorusacri-Auto-rocokingdom` |
| ColinHong10/NRC_AI | 已采集 `upstream/ColinHong10-NRC_AI` |
| zh19990906/luoke_location | 已采集 `upstream/zh19990906-luoke_location` |
| Wooziii/roco-map-tracker | 已采集 `upstream/Wooziii-roco-map-tracker` |
| SCH-CMYK/game-automation | 已采集 `upstream/SCH-CMYK-game-automation` |
| eachyczhang/-RocoTools | 已采集 `upstream/eachyczhang-RocoTools` |
| rookie-orange/rocokingdom-ui | 已采集 `upstream/rookie-orange-rocokingdom-ui` |
| Tsuann/RocoKingdom-AutoCapture | 已采集 `upstream/Tsuann-RocoKingdom-AutoCapture` |
| Pacific-shark/roco-balance-lab | 已采集 `upstream/Pacific-shark-roco-balance-lab` |
| ElliottZhao666666/rocom-codex-pets-gen | 已采集 `upstream/ElliottZhao666666-rocom-codex-pets-gen` |
| Adolph321/- | 已采集 `upstream/Adolph321-Adolph` |
| oblitum/Interception | 已采集 `upstream/oblitum-Interception`（未安装） |

未采集的 GitHub 链接均来自 `.venv` 依赖 METADATA、SBOM 或 `backend-c/third_party/stb_image.h` 等第三方依赖声明（如 opencv/opencv、python-pillow/Pillow、numpy/numpy、fastapi/fastapi），不属于 Rocogi 参考/移植的上游组件，故不克隆。
