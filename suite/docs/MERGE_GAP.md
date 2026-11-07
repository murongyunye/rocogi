# MERGE_GAP · 上游合并缺口与推进结果

依据：`docs/upstream-snapshot/MERGE_MAP.md`（39 组件 A/B/C/D 分级）与 `docs/upstream-snapshot/INVENTORY.md`（15+1 仓库清单）。
本文件只记录**本套件**的推进状态；原 `upstream/` 镜像已于去重时移除（内容与 `vendor/` 逐文件 sha256 一致），仅独有文档保留在 `docs/upstream-snapshot/`。

## 1. 主干矩阵落实情况

| 能力域 | 选定主干 | 落地位置 | 状态 |
| --- | --- | --- | --- |
| 截图 / 窗口 | Auto-rocokingdom `core/capture.py` | `suite/engines/capture/engine_main.py` | 已接；真实 PrintWindow 分支由 `window.enable_real_capture=false` 关闭并标注（不做游戏窗口识别验证） |
| 模板 / 场景 / ROI | Auto-rocokingdom `core/vision.py` | `suite/engines/vision/engine_main.py` | 已接，6 个 action |
| 精灵检测 | AutoCapture ONNX `detector.py:458-579` | `suite/engines/vision` + `assets/models/sprite_detector.onnx` | 已接，onnxruntime CPU；RocoPilot `.pt` 未进运行时 |
| SIFT | roco-map-tracker `SIFTEngine` | `suite/engines/sift/engine_main.py` | 已接；luoke_location 仅参数对照 |
| 输入注入 | game-automation `controller.py:69-230` + SendInput 自补 | `suite/engines/input/engine_main.py` | Interception 分支保留、驱动未装 -> skipped；SendInput 可用 |
| 地图 / 路线 | roco-map `route_planner.py:51-299` | `suite/engines/sift`（route action）+ `assets/map/points.sqlite` | 已接，目标空间 6144×5888 |
| 对战 | NRC_AI 全套 + `nrc.db` | `suite/engines/battle` | 已接（dataset/team/damage/responder/turn_state） |
| 状态机 / 实时 | AutoCapture `state_machine.py` | `suite/engines/scheduler` | 已接（capture_fsm） |
| 工作流 | Rocogi 现有 Python DAG | `rocogi/backend/app/engine` + `suite/engines/scheduler` | 已接（dag/executor/branch/foreach/subgraph/event_bus） |
| 图鉴 | NRC `nrc.db` | `suite/assets/db/nrc.db`（461 / 491 / 20433） | 已接（只读 immutable） |

## 2. D 类（需重写）缺口与结果

| 组件 | 原缺口 | 本次推进 | 结果 |
| --- | --- | --- | --- |
| `battle.turn_state` | 上游无实现（AutoCapture 只有战斗模板） | 在 battle 引擎新增 `turn_state` action：把观测（血量百分比/回合）灌入 NRC `BattleState` schema，HUD/OCR 抽取留在后端适配层 | **已补，entry 可跑**（`rocogi-suite call battle turn_state`） |
| `scheduler.dag` | yotta 是 Go，不可直接复用 | 保留 Rocogi 编译器；修三处阻断：compile 前 `import app.nodes`、`source/target`→`from/to`、issues 非空返回 `failed` | **已修，compile 通过且 issues=0** |
| `scheduler.executor` | 同上 | 用 Rocogi `Runtime` 执行纯 flow 图（start→set_var→branch→log→stop），事件收集器记录 node-attempt/log | **已补，entry 可跑** |
| `scheduler.onedragon_plan` | BetterGI C#，不可移植 | 按 BetterGI 任务开关/排序语义生成 plan（`config/engines/scheduler.toml` 的 `[[onedragon.tasks]]`），运行时仍是 Rocogi DAG | **已补，entry 可跑** |

## 3. A/B/C 类推进中补齐的缺口

| 缺口 | 处理 |
| --- | --- |
| `scheduler.foreach` 原为占位 | 在 `rocogi/backend/app/nodes/flow.py` 新增 `flow.foreach` 节点契约：按列表逐项写变量并执行子图，`scheduler flow` 真实跑 3 轮子图 |
| `scheduler.branch` / `subgraph` 长期只有声明 | 由 `scheduler flow` 自检图实际执行（branch true/false 两分支 + subgraph/ foreach 组合） |
| `scheduler.event_bus` | 新增 `call scheduler events`：向 `runs/<id>/events.jsonl` 追加 seq 连续事件 |
| `capture.scene_switch` / `capture.foreground` | 改为真实实现：帧摘要变化判定 + `SetForegroundWindow`（无窗口句柄时返回 unavailable） |
| `input.key_queue` / `input.hotkey` | 队列 worker（dry-run / 真实注入）+ `RegisterHotKey` 消息泵自检 |
| 坐标空间（6144×5888 vs 8192×8192） | sift 引擎新增 `affine_from_three_points()`，meta 输出 `spaceBridge` 明确"禁止只缩放，需 3 点仿射" |
| 小地图三档尺寸 | `config/engines/capture.toml` 的 `[minimap.profiles]` 配置化（150×150 / 162×162 / 255×235），不再写死 |
| `engines --verify` 只跑默认动作 | 改为逐 entry：**35 个**去重入口（原 25 个 + vendor 10 个）全部实跑并校验结构化输出；组件注册表 55 条 |
| vendor 全量源码导入（P0） | 16 仓整包导入 `vendor/`，逐文件 16/16 零缺失（1,324,626,890 B）；9 个 adapted 由 `suite/engines/vendor/engine_main.py` 按真实入口接线；6 个已 resolved 的仓以 `vendor status` + 证据暴露，1 个 partial（pets-gen）走 `vendor blocked` |
| 引擎引用上游副本 | capture/vision/sift/battle/scheduler/input 与 `suite/assets/build.py` 全部从 `work/upstream` 切到 `vendor/`（单一源码基线；upstream 仅保留只读） |

## 4. vendor 原 blocked 七项：缺什么、补上的命令与代价（当前 1 partial / 0 blocked）

状态口径：`blocked-vendor` = 源码已完整导入且契约已导出，但端到端运行仍缺外部前提；`not-wired` = 已构建/已具备可运行入口，但未接入 suite 运行时。最新事实（**2026-11-05 18:30 CST**，`vendor/manifest.json` + `vendor/docs/BLOCKERS.md`）：**15 resolved / adapted、1 partial（pets-gen）、0 still-blocked**。`adapter_contract.json` 是各适配层对“自身能否免外部进程运行”的静态结论，未随工具链补件刷新；vendor `status` 已同时返回原始契约状态与最新 `resolution`（resolved / resolved-pending-reboot / partial），组件状态与本表以最新 `resolution` 为准。`vendor blocked` 现在只汇总真正仍缺条件的 pets-gen。

| 项目 | 缺什么 | 补上的具体命令 | 代价 / 权限 / 联网 |
| --- | --- | --- | --- |
| Interception 驱动 | **已安装、待重启生效**：17:34 CST 管理员安装器返回 0，`keyboard.sys` 已存在，但 `sc query interception` 仍 1060；源码与 API 契约已导入 | 已执行：`install-interception.exe /install`（输出见 `vendor/docs/interception_install_output.txt`）；重启后 `sc query keyboard` / `sc query mouse` 验证；卸载 `/uninstall` | 安装已完成（管理员已用）；**重启后生效**；不联网。按用户要求**本轮不重启**，运行继续走 SendInput 回退 |
| BetterGI | ~~.NET 8 SDK~~ **纠正：上游是 net10.0-windows** | 便携 `.toolchain\dotnet10`（10.0.403）+ NuGet 缓存；`dotnet build ...BetterGenshinImpact.csproj -c Release` → 555 警告 / **0 错误**（4m3s） | **resolved（仅 build）**；完整输出 1.11 GB 不整包塞入，full 包只带可运行入口 `artifacts/bettergi/{BetterGI.exe,BetterGI.dll,deps,runtimeconfig}`；WPF 未运行（`not-wired`） |
| yotta | ~~Go 1.25 + Wails + WebView2~~ **已解决** | 便携 `.toolchain\go`（1.25.13）+ `wails3 v3.0.0-beta.6`；产物 `.toolchain\build\yotta.exe`（60,669,952 B） | **resolved**；full 包 `artifacts/yotta/yotta.exe`；未启动 GUI、未接入 suite 运行时（状态 `not-wired`） |
| rocokingdom-ui | ~~pnpm 11.5.3 + catalog~~ **已解决** | 便携 pnpm 11.5.3：`pnpm install --node-linker=hoisted --config.package-import-method=copy`；`pnpm --config.verify-deps-before-run=false -r run build` → exit 0 | **resolved**；`apps/website/dist` 49 文件 / 14.0 MB 随 full 包的 vendor 子树；静态 UI 未由 suite 托管（`not-wired`） |
| RocoTools | ~~图鉴数据~~ **已解决** | 仓库自带 crawler：`.toolchain\venv-crawler\Scripts\python.exe vendor\eachyczhang-RocoTools\crawler\run.py --full` | **resolved**：594 宠物 / 553 技能 / 571 图标 / 16 MB 落在 `vendor/eachyczhang-RocoTools/data`；REST 服务未启动（无 node_modules），状态 `not-wired` |
| pets-gen | 渲染器**已补**（rocom-pets 1.14.2 windows-x64 exe）；仍缺专有游戏资源（`entity.json` + `model.glb`/`anim.rka`/贴图） | 渲染器：`vendor/.../rocom-pets-1.14.2-windows-x64.exe`；资源需从本机游戏 `C:\Program Files\洛克王国：世界(2002304)` 通过 rocom-pets GUI 导出，再跑 `render_source.py` | **partial**：脚本 `validate_input.py` / `render_source.py --help` 通过；资源为专有资产且需交互式导出，保持 `blocked-vendor` |
| sift-map-tracker | 无运行时源码；原缺 `default_route.json` 与 region | 新增 `probe_service.py` + `build_default_route.py`：由 Wooziii `points.normalized.json`（mark_type 701，162 点）经 `tracker.route_planner` 生成 `routes/default_route.json`（162 nodes / 161 edges，77,442 B，`sift0.6`）；`runtime/settings_override.json` 写入 region `{0,0,255,235}`（原文件备份 `.orig`，不入包） | **resolved**：`probe_service.py --synthetic-minimap` 实测 76 帧 / **74 found=true**，center=(3123,2511)，`tracking_source=global_relocate`，route_name=默认采集路线-701；证据 `vendor/docs/evidence/sift_route_probe.json`。`service.exe` 作为可选外部进程，结束必须 `taskkill /T`；suite 主定位仍走 Wooziii SIFTEngine，状态 `not-wired` |

## 5. 三项高风险冲突的处理

1. **依赖冲突**：7 个引擎各自独立 venv，互不共享（`capture/vision/input/sift/battle/scheduler/vendor`），每引擎一份 `requirements.lock`，锁文件与 `uv pip freeze` 逐条一致（见 verify round）。vendor 引擎自身只依赖 stdlib，按 action 把适配器派发到对应引擎 venv / 便携 Python / Node。
2. **坐标空间**：canonical 固定 6144×5888；8192 空间仅在 meta 中登记，跨空间必须走 3 点仿射，未标定前禁止混用。
3. **必须拆进程的三类**：RKNN（仅 Linux aarch64，未安装）、`sift service.exe`（无运行时源码，已 resolved 的可选外部进程）、Interception（驱动已装、待重启，blocked-vendor）——三者在组件注册表中都有独立状态与原因，不混进主运行时。

## 6. 待办（未完成项）

- **blocked 条件已交付**：`vendor/docs/BLOCKERS.md`（2026-11-05 18:30 CST）显示 **15 resolved / adapted、1 partial（pets-gen）、0 still-blocked**；sift-map-tracker 已由 partial 转 resolved（默认路线 + region + 74/76 found）。6 个 resolved 仓（sift、Interception、BetterGI、yotta、rocokingdom-ui、RocoTools）在组件表中为 `not-wired` 或 `blocked-vendor（待重启）`，产物/证据随 full 包；最后一次变更后已重跑五轮。
- `input.interception`：源码与契约已导入；17:34 CST 管理员安装器成功（`keyboard.sys` 存在），**待重启激活**（服务仍 1060）。本轮按用户要求不重启，状态保持 `blocked-vendor`；SendInput 回退演练在非交互桌面 `apiAccepted=0`，需用户在活动会话重跑 `suite/probes/input_drill.py`。
- `vision.ocr`：无 OCR 源码导入（vendor 与 upstream 均无），状态保留 `skipped`，不伪造实现；可选 Tesseract（轻量）或 easyocr（重）。
- `sift.external_tracker` / `vendor.sift_map_tracker`：外部进程条件已 resolved（`routes/default_route.json` 162 nodes / 161 edges、region `{0,0,255,235}`、74/76 found）；suite 主定位仍走 SIFTEngine，native `sift.external_tracker` 未接运行时，`vendor.sift_map_tracker` 为 `not-wired`。
- `scheduler.session_loop`：仍为静态阶段表，待接入真实定时器（`not-wired`）。
- `capture.windows_window` 真实分支：按约定留空标注，不做游戏窗口识别验证。
