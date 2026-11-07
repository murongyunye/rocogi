# Third-party notices（Rocogi 0.4.6）

本项目为**个人非商业自用**的《洛克王国：世界》本地自动化研究工作台，不对外提供商业服务，也不以任何形式售卖、出租或按次收费。自 0.4.0 起，`vendor/` 目录**完整导入**了 16 个上游仓库的源码（逐文件比对 16/16，零缺失），并附带各仓原有 `LICENSE` / `NOTICE`。本文件逐仓说明许可证、用途、修改状态与适配层。

- 导入时间：2026-11-05；vendor 总体积 1,324,626,890 字节（约 1.23 GB）
- 最新状态（2026-11-05 18:30 CST）：**15 resolved / adapted、1 partial（pets-gen）、0 still-blocked**；sift-map-tracker 已补默认路线与 region 并实测 74/76 帧 `found=true`；Interception 驱动已装、待重启。
- 修改状态：**0 补丁**。上游源码原样保留；兼容化只发生在 `vendor/adapters/<repo>/` 与 `vendor/adapters/_common/`，以独立适配层、路径重定向、配置改写、进程隔离等方式实现，不改上游仓库内的源文件。
- 复制/改动机制记录：`vendor/patches/`（当前为空，仅保留机制）；适配契约：`vendor/adapters/<repo>/contracts/adapter_contract.json`
- `suite/engines/vendor/engine_main.py` 是唯一编排入口，它调用各仓适配层，不重复实现上游算法。

**本地副本状态（2026-11-06，第二轮：裁剪为运行时子集）**：`vendor/` 下 16 个上游仓已从
"整份源码常驻"改为**归档依赖**——本地只保留运行时真正读取的文件（Python import 闭包、配置
真实路径、运行时资产与全部 `LICENSE` / `NOTICE`），上游源码内容零改动。逐仓 `keep[]` 与理由见
`docs/VENDOR_RUNTIME_SCOPE.json`，结果见 `docs/PUBLISH_SCOPE.md` 第 5 节。

- 本地 `vendor/`：59,403 个文件 / 3.16 GB → 7,283 个文件 / **229 MB**（释放 52,120 个文件 / 2,784.1 MB）。
- 各仓 `LICENSE` / `NOTICE` / `COPYING` **全部保留**；被裁剪的只是运行时不需要的二进制、构建产物与非运行时代码。
- **重要**：远端 `murongyunyeh/rocogi` 的 `vendor/` 是文本白名单（6,172 文件 / 51.1 MB），
  不是完整二进制镜像。被裁剪的 917.6 MB 唯一性资产（客户端/service.exe、大地图、SIFT npz、
  `spirit_icons`、`big_map-annotated.png` 等）不在云端，归档来源为上游项目自身（公开仓库 /
  Release 资产 / 可重跑脚本）。裁剪前本地校验值与本文件第 19 行起的逐仓清单仍为权威许可证记录。
- 单行超大 JSON 分流后，`release/only-local/` 只剩 **99 个 sift `legacy-json`（12,773,679 B）**：
  balance-lab 12 个与 Wooziii 1 个已与上游 commit 副本逐字节核对相同后删除，改由远程调取；
  sift 99 个因令牌只有读权限（push 403）尚未上云，仍是唯一副本，未删除。详见
  `docs/PUBLISH_SCOPE.md` 第 7 节。
- **完整上游源码不本地常驻、也不在本仓库另存一份**：来源与 commit 固化在
  `vendor/upstream_sources.json`（15 个 GitHub 仓 + sift 发布包），需要时用
  `vendor/tools/fetch-upstream.ps1 -Repo <name>` 重拉到 `vendor/_restore/<repo>`，
  不会覆盖 `vendor/<repo>` 运行时子集。实测与例外（Adolph 的源码在其仓内 zip 中）见
  `docs/PUBLISH_SCOPE.md` 第 6 节。sift-map-tracker 无上游 git 仓，归档在本仓库
  `archive/sift-map-tracker/`。
- 若后续删除本地运行时子集，各仓许可证与来源仍以本文件及仓库内 `LICENSE` 为准，不因副本移除而失效。

## 逐仓清单

| # | 仓库（vendor/ 下） | 许可证 | 用途 | 修改 | 适配层摘要 |
| --- | --- | --- | --- | --- | --- |
| 1 | Adolph321-Adolph | **GPL-3.0** | 战斗规则 / 特性 / 技能校验 | 0 | `adapters/adolph_rules`：Node `verify.js` 子进程隔离，导出 200 精灵 / 200 技能 / 65 特性 |
| 2 | babalae-better-genshin-impact (BetterGI) | **GPL-3.0**（子项目 Fischless.WindowsInput 为 MIT） | 启动器与任务计划信息架构、WPF 自动化参考 | 0 | `adapters/bettergi`：静态导出 32 个公开类型；便携 .NET 10 SDK 构建 0 错误，可运行入口 `artifacts/bettergi/` 随 full 包；WPF 未运行 |
| 3 | ColinHong10-NRC_AI | **MIT** | 对战数据、效果引擎、`nrc.db` | 0 | `adapters/nrc_ai`：只读 sqlite URI（pokemon 461 / skill 491 / pokemon_skill 20433 / evolution 206），不写上游 DB |
| 4 | eachyczhang-RocoTools | **CC BY-NC-SA 4.0** | 图鉴字段模型、REST 查询服务 | 0 | `adapters/rocotools`：导出 18 张表结构 + 9 条路由；crawler 已落 594 宠物 / 553 技能 / 571 图标（15 MB）到 `vendor/data`，随 full 包 |
| 5 | ElliottZhao666666-rocom-codex-pets-gen | **MIT** | 桌宠资源生成 / 帧标准化 | 0 | `adapters/pets_gen`：7 项脚本检查通过；rocom-pets 1.14.2 Windows x64 渲染器已就位；专有游戏资源仍需 rocom-pets GUI 交互导出，**唯一 partial** |
| 6 | Makapic-RocoPilot | **MIT** | 截图、丢球/战斗策略、Interception 输入参考 | 0 | `adapters/rocopilot`：重定向 templates/models 基准目录；无驱动时回退 SendInput |
| 7 | oblitum-Interception | **LGPL-3.0（非商用；商用需单独授权）** | 内核级虚拟键鼠 | 0 | `adapters/interception`：导出 14 个 C API + 5 个枚举契约；安装器 17:34 CST 完成（`keyboard.sys` / `mouse.sys`、`UpperFilters` 已写），**待重启生效**；`vendor/tools/post-reboot-check.ps1` 就绪；未重启前使用 SendInput 回退 |
| 8 | Pacific-shark-roco-balance-lab | **MIT** | 6 人配队 / 平衡研究 | 0 | `adapters/balance_lab`：Node 直接导入 `src/engine.mjs`，12 exports / 6 roster / 25 moves |
| 9 | rookie-orange-rocokingdom-ui | **未声明**（仓库无 LICENSE） | UI 令牌与组件参考 | 0 | `adapters/rocokingdom_ui`：导出 tokens + 214 个 tsx 组件；pnpm 11.5.3 构建 exit 0，`apps/website/dist`（49 文件 / 14 MB）随 full 包 |
| 10 | SCH-CMYK-game-automation | **CC BY-NC 4.0** | 截图 / 视觉 / 定位 / 输入分层与挖矿配置 | 0 | `adapters/game_automation`：MiningConfig 28 字段；torch/ultralytics 降级为 OpenCV；DPI 归一化 1920x1080 |
| 11 | sift-map-tracker | **未声明**（仅发布二进制，无 LICENSE） | 小地图定位（二进制服务 + 客户端） | 0 | `adapters/sift_map_tracker`：新增 `probe_service.py` 与 `build_default_route.py`；补位 `routes/default_route.json`（162 nodes / 161 edges，生成非覆盖）、region `{0,0,255,235}`；实测 76 帧 / 74 `found=true`（`vendor/docs/evidence/sift_route_probe.json`）；客户端 `SiftMapTracker.Client.exe` 与 `assets/` 随 full 包，主算法仍用 #13 的 SIFTEngine |
| 12 | Tsuann-RocoKingdom-AutoCapture | **未声明**（仓库无 LICENSE） | 自动捕捉状态机 + ONNX 检测器 | 0 | `adapters/autocapture`：Linux/RKNN 配置改写为 Windows mss + ONNX；`sprite_detector.onnx` 随仓 |
| 13 | Wooziii-roco-map-tracker | **未声明**（README 声明地图/图标权利保留） | SIFT 定位引擎、寻路、坐标仿射 | 0 | `adapters/roco_map_tracker`：SIFTEngine + route_planner + 3 点 6144x5888↔8192x8192 仿射 |
| 14 | yorusacri-Auto-rocokingdom | **MIT** | 自动丢球 / 战斗 / 同行确认 | 0 | `adapters/auto_rocokingdom`：11 个核心模块 + 9 张模板；capture/vision 引擎已改为引用 vendor 副本 |
| 15 | yottaapp-yotta | **自定义 source-available（非商用）** | Workflow / Node Contract / Run Evidence 架构参考 | 0 | `adapters/yotta`：导出 189 个 builtin node 契约；便携 Go 1.25.13 + Wails v3 构建 `artifacts/yotta/yotta.exe`（60.7 MB），GUI 未启动 |
| 16 | zh19990906-luoke_location | **未声明**（README 要求遵守原素材许可） | 点位库、图标、3 点 ROI 归一化 | 0 | `adapters/luoke_location`：2469 点位 / 298 图标；SIFT 定位与地图素材 |

## full 包裁剪说明（仅体积，不改许可）

以下**中间产物/缓存**不入包，源码、LICENSE、游戏数据与已构建入口全部保留：

- `.toolchain/**`（约 9.5 GB：Go、两个 .NET SDK、NuGet 缓存、pnpm store）——绝不入包；
- `node_modules/**`、`obj/**`、`bin/Debug/**`、`bin/Release/**`、`.pnpm-store/**`、`__pycache__/**`、`*.zip` 缓存、`*.orig` 备份、`runs/**`、`logs/**`；
- BetterGI 完整 1.11 GB 构建输出（只带 `artifacts/bettergi/` 可运行入口）；
- `zh19990906-luoke_location/dist/**`（旧 PyInstaller GUI 产物，108 MB）；
- `sift-map-tracker` 仅去掉重复的 `screen-recognition/service.exe`（102.9 MB）与可再生 `resources/cache/**`（26 MB）；**保留**客户端 `SiftMapTracker.Client.exe`、`sift-map-tracker/service/service.exe`、`assets/**`（SIFT 特征与底图）和 `legacy-json/**`，保证服务与重录路线都可运行；
- `ColinHong10-NRC_AI/data/spirit_icons/**`（约 160 MB 宠物立绘，battle 只读 `nrc.db`）。

需要完整媒体时可从 upstream 原仓或其发布页补取；这不影响任何许可证义务。

## 构建产物位置（full 包）

`vendor/docs/BLOCKERS.md` 中 resolved 的项，其可运行入口随 full 包放在 `artifacts/`：

- `artifacts/yotta/yotta.exe`：Go 1.25.13 + Wails v3.0.0-beta.6 构建，60,669,952 B；非商用许可，未启动 GUI。
- `artifacts/bettergi/BetterGI.exe`、`BetterGI.dll`、`BetterGI.deps.json`、`BetterGI.runtimeconfig.json`：.NET 10 SDK 构建（0 错误）；GPL-3.0，随包即满足源码/许可证同发；完整 1.11 GB 输出未整包携带，运行还需上游构建目录中的同级 DLL。
- `vendor/rookie-orange-rocokingdom-ui/apps/website/dist/`：pnpm 构建产物 49 文件 / 14.0 MB。
- `vendor/eachyczhang-RocoTools/data/`：594 宠物 / 553 技能 / 571 图标，16 MB。
- `vendor/sift-map-tracker/sift-map-tracker/service/service.exe`：原始发布二进制（56.7 MB），未修改；同级 `assets/`（SIFT 特征与底图）随包，可直接按 NDJSON 协议启动。
- `vendor/sift-map-tracker/SiftMapTracker.Client.exe`：原始客户端二进制（150.6 MB），用于路线交互录制；`routes/default_route.json`（162 nodes / 161 edges）为**生成补位**，非上游文件。
- `vendor/sift-map-tracker/sift-map-tracker/runtime/settings_override.json`：写入 region `{top:0,left:0,width:255,height:235}`；原文件备份 `.orig` 不入包。
- `vendor/tools/post-reboot-check.ps1` + `vendor/docs/evidence/`：重启后驱动自检、sift 路线探测等证据随包。

## 许可证原文位置

各仓许可证文件均在 `vendor/<repo>/` 下，发布包（full）原样携带：

- `Adolph321-Adolph/LICENSE`、`babalae-better-genshin-impact/LICENSE`：GNU GPL v3.0 全文
- `ColinHong10-NRC_AI/LICENSE`、`ElliottZhao666666-rocom-codex-pets-gen/LICENSE`、`Makapic-RocoPilot/LICENSE`、`Pacific-shark-roco-balance-lab/LICENSE`、`yorusacri-Auto-rocokingdom/LICENSE`：MIT
- `eachyczhang-RocoTools/LICENSE`：CC BY-NC-SA 4.0（注明数据来自洛克王国世界 BWIKI）
- `SCH-CMYK-game-automation/LICENSE`：CC BY-NC 4.0
- `yottaapp-yotta/LICENSE`：自定义非商用许可（个人/教育/研究免费，商用禁止）
- 未声明仓库（`oblitum-Interception` 另见其 `README`/`COPYING` 说明、`rookie-orange-rocokingdom-ui`、`sift-map-tracker`、`Tsuann-RocoKingdom-AutoCapture`、`Wooziii-roco-map-tracker`、`zh19990906-luoke_location`）：仓库内无 LICENSE 文件，本项目**不替其重新授权**；对外分发前须取得各自作者许可。

## GPL-3.0 / LGPL-3.0 传染性与合规边界

本项目自身代码为 MIT。vendor 中两个 GPL-3.0 仓库与一个 LGPL-3.0 仓库的处理方式如下：

| 上游 | 许可证 | 集成方式 | 传染性结论 |
| --- | --- | --- | --- |
| Adolph321-Adolph | GPL-3.0 | 源码原样在 `vendor/`；运行时由 Node **独立进程**执行，通过 stdout JSON 通信 | 不静态链接、不进程内导入；本套件不因调用而整体变为 GPL。若再分发 full 包，Adolph 源码仍受 GPL-3.0 约束，需保留 LICENSE 与对应源码（full 包已包含） |
| babalae-better-genshin-impact | GPL-3.0 | 源码原样在 `vendor/`；便携 .NET 10 SDK **仅构建**（0 错误），未运行 WPF；可运行入口 `artifacts/bettergi/` 随 full 包 | 未形成衍生作品运行链路；full 包内按 GPL-3.0 提供源码与许可证 |
| oblitum-Interception | LGPL-3.0（非商用） | 源码原样；驱动安装器已执行但**尚未重启激活**；当前运行时使用 SendInput 回退 | 非商用个人使用；若重启后以动态库方式调用，需满足 LGPL 的替换/源码提供义务 |
| yottaapp-yotta | 自定义非商用 | 源码原样；便携 Go 1.25.13 + Wails v3 **仅构建**，GUI 未启动；`artifacts/yotta/yotta.exe` 随 full 包 | 禁止任何商业使用/付费服务；不得移除版权声明 |

**重要**：full 发布包因为包含 GPL-3.0 源码，其 `vendor/` 子树按 GPL-3.0 分发；套件自有代码（`suite/`、`backend/`、`frontend/` 等）仍为 MIT。两者在文件系统上边界清晰，不合并为单一衍生作品。个人非商业自用不触发 GPL 的分发义务；一旦对外分发 full 包，请同时提供完整的对应源码（full 包本身即满足）并保留全部 LICENSE。

## 未声明许可证 / 素材权利

以下仓库没有统一 LICENSE，源码与素材权利归原作者：

- `Wooziii-roco-map-tracker`：README 明确地图底图、图标、点位数据的第三方权利保留；本项目仅本地个人研究使用。
- `zh19990906-luoke_location`：点位库与地图素材来自社区/哔哩哔哩 WIKI，README 要求遵守上游与原素材许可。
- `Tsuann-RocoKingdom-AutoCapture`：无 LICENSE；仅本地研究。
- `rookie-orange-rocokingdom-ui`：无 LICENSE；仅导出令牌/组件契约；full 包携带其 pnpm 构建产物 `apps/website/dist`，不重新授权。
- `sift-map-tracker`：仅二进制发布、无 LICENSE；full 包携带其原始发布物（客户端、服务、assets 与补位路线），不修改、不反编译、不重新授权；`routes/default_route.json` 由本项目按公开点位生成，属补位文件。

## 游戏与素材

《洛克王国：世界》及其名称、界面、精灵、技能、地图、图标等知识产权归腾讯及相应权利人所有。本项目与官方无关联，仅供个人学习、研究与自动化实验。使用者应自行确认游戏服务条款、账号风险与素材分发权限。

**0.4.4 起本仓库与发行包不再包含任何游戏数据与美术素材**：BWIKI 导出的战斗库（`datasets/bwiki/*.db|json|raw|wiki`）、社区 PvP 数据集（`datasets/pvp/*.db`）、地图物品图标（`datasets/map/icons/`）与游戏内截图（`docs/screenshots/*.png`）均已从版本库与发行归档中移除，只保留导入脚本与出处说明 `PROVENANCE.md`。需要这些数据的使用者请在自己机器上按 [docs/PUBLISH_SCOPE.md](docs/PUBLISH_SCOPE.md) 的步骤重建，并自行承担相应许可与分发义务。

## 运行时依赖

- Python：FastAPI、Uvicorn、OpenCV、NumPy、Pillow、PyYAML、onnxruntime、mss、pywin32 等，遵循各自许可证。
- Node：Vue、Vite、各上游 `package.json` 依赖，遵循各自许可证。
- .NET / Go / Wails 仅用于构建 yotta 与 BetterGI，其运行时/SDK 不随包分发；可运行入口见 `artifacts/`。
- 界面使用系统字体栈，不打包字体文件。