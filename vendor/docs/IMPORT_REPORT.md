# vendor 导入报告

- 生成时间：2026-11-05
- 来源：`work/upstream`（只读，复制导入）
- 目标：`work/rocogi/vendor/`
- 仓库数：16；导入体积：1.23 GB / 9,288 个文件（排除 `.git`、`__pycache__`、`.venv`）
- 比对结论：16/16 仓库逐文件比对 **0 缺失**；无令牌文件；无本机绝对路径泄漏；适配层 15 个 resolved/adapted / 1 个 partial / 0 个 still-blocked / 0 个 error
- 卡点状态更新时间：2026-11-05（逐项补齐见 [BLOCKERS.md](computer://c:\Users\13005\Downloads\work\rocogi\vendor\docs\BLOCKERS.md)、工具链见 [TOOLCHAIN.md](computer://c:\Users\13005\Downloads\work\rocogi\vendor\docs\TOOLCHAIN.md)）

## 状态定义

| 状态 | 含义 |
| --- | --- |
| imported | 源码完整复制，未做任何适配 |
| adapted | 源码完整 + 适配层干跑通过（`--help` 与 `--json` 均成功） |
| resolved | 原卡点已由便携工具链或替代方案解除，并实测构建/运行通过（证据见 `docs/evidence/`） |
| partial | 代码与契约已就绪，仍有不可自动补齐的外部资源缺口，已给出替代路径 |
| still-blocked | 无（本轮 0 项） |

本表所有仓库均已达到"完整源码 + 清单"的导入基础；`resolved` 表示已实际跑通构建或运行，`partial` 仅表示仍缺外部资源/配置，不代表文件缺失。逐项证据与人工步骤见 [BLOCKERS.md](computer://c:\Users\13005\Downloads\work\rocogi\vendor\docs\BLOCKERS.md)。

## 逐仓结果

| 仓库 | 语言 | 许可证 | 完整度 | 状态 | 说明 |
| --- | --- | --- | --- | --- | --- |
| Adolph321-Adolph | JavaScript | GPL-3.0 | complete（269 文件 / 1.31 MB） | adapted | Node 跑 `verify.js` 通过；200 宠物 / 200 技能 / 65 特性；进程隔离使用 |
| babalae-better-genshin-impact | C# | GPL-3.0（WindowsInput 子项目 MIT） | complete（3109 文件 / 28.35 MB） | resolved | 便携 .NET SDK 10.0.403 构建通过（上游目标框架实为 `net10.0-windows10.0.22621.0`，非 .NET 8）；0 错误 / 555 警告；不跑 WPF UI |
| ColinHong10-NRC_AI | Python | MIT | complete（478 文件 / 180.04 MB） | adapted | `nrc.db` 只读校验通过：pokemon 461 / skill 491 / pokemon_skill 20433 / evolution 206 |
| eachyczhang-RocoTools | JS/Vue + Python | CC BY-NC-SA 4.0 | complete（247 文件 / 2.69 MB） | resolved | 用仓库自带 `crawler/` 抓 BWIKI：594 宠物 / 553 技能 / 571 图标，15.0 MB 落地 `data/` |
| ElliottZhao666666-rocom-codex-pets-gen | Python | MIT | complete（22 文件 / 0.75 MB） | partial | 资源目录结构与字段已确认（`docs/resource-directory.md`）；渲染器 rocom-pets 1.14.2 已下载校验；仍缺游戏提取资源目录（需本机游戏客户端导出） |
| Makapic-RocoPilot | Python | MIT | complete（70 文件 / 61.19 MB） | adapted | config 可导入；9 模板 + 4 个 `.pt`；interception 可用，driver 未装时回退 SendInput |
| oblitum-Interception | C/C++ | LGPL-3.0（非商用） | complete（44 文件 / 0.12 MB） | resolved | Interception v1.0.1 安装成功：`keyboard.sys`/`mouse.sys` 已落入 `drivers/`，键盘 `{4D36E96B}`、鼠标 `{4D36E96F}` 的 `UpperFilters` 已写入；**待重启生效** |
| Pacific-shark-roco-balance-lab | JavaScript | MIT | complete（67 文件 / 15.57 MB） | adapted | Node 直接 import 引擎：12 个导出、6 角色 / 25 招式数据集 |
| rookie-orange-rocokingdom-ui | TypeScript/TSX | 未声明 | complete（439 文件 / 13.62 MB） | resolved | 便携 Node 22.23.4 + pnpm 11.5.3（npm 全局前缀指向 `.toolchain\npm-global`）；`pnpm -r run build` exit 0（`✓ built in 1.81s`）；令牌与 214 组件可被前端引用 |
| SCH-CMYK-game-automation | Python | CC BY-NC 4.0 | complete（48 文件 / 3.62 MB） | adapted | `MiningConfig`（28 字段）可导入；torch/ultralytics 缺失时降级 OpenCV；interception.dll 在仓库内 |
| sift-map-tracker | 二进制 + 1 个配置脚本 | 未声明 | complete（213 文件 / 617.62 MB） | resolved | **无运行时源码**；可选外部进程接入：补 162 节点 `default_route.json`（Wooziii route_planner）+ region `{0,0,255,235}`，探测 76 帧中 **74 帧 `found=true`**（center=3123,2511），探测后按进程树终止 |
| Tsuann-RocoKingdom-AutoCapture | Python | 未声明 | complete（37 文件 / 18.03 MB） | adapted | Linux/RKNN 配置注入为 Windows mss + ONNX；`sprite_detector.onnx`（11.7 MB）就位 |
| Wooziii-roco-map-tracker | Python / C# | 未声明 | complete（649 文件 / 140.93 MB） | adapted | `SIFTEngine`、`route_planner` 均可导入；`data/points.normalized.json` 2436 条点位 |
| yorusacri-Auto-rocokingdom | Python | MIT | complete（50 文件 / 0.65 MB） | adapted | 11 个 core 模块 + 9 模板；窗口/截图/模板路径全部重定向到 vendor |
| yottaapp-yotta | Go / TS / Vue | 自定义非商用 | complete（1950 文件 / 25.17 MB） | resolved | 便携 Go 1.25.13 + Wails v3.0.0-beta.6 + 系统 WebView2 `156.0.4314.58`；bindings 生成（559 packages/19 services/231 methods）后 `go build` 通过，产出 `yotta.exe`（60.7 MB） |
| zh19990906-luoke_location | Python | 未声明 | complete（1596 文件 / 153.61 MB） | adapted | 2469 点位 / 298 图标；桌面绝对小地图坐标已归一化为相对 ROI |

## 特别处理项

### sift-map-tracker：确认"只有 PyInstaller 产物，没有运行时源码"

- 全仓 `.py` 仅 1 个：`sift-map-tracker/settings.py`（客户端设置页导出的常量，文件头明确写明不是 tracker runtime）。
- 可执行物：`SiftMapTracker.Client.exe`（157.9 MB）、`sift-map-tracker/service/service.exe`、`screen-recognition/*.exe`。
- 发布清单 17 个文件，本地通过 16 个，唯一缺失 `sift-map-tracker/routes/default_route.json`（上游仓库本身也没有，不是导入丢失）。
- 与源码版 `SIFTEngine` 的替代关系：
  - **主实现**：`vendor/Wooziii-roco-map-tracker/roco-map-tracker/tracker/engines/sift_engine.py`，可在本进程内直接调用。
  - **二进制包角色**：参数/资源基准（`MAP_ORIGIN_X=-973`、`MAP_ORIGIN_Y=-1585`、`MATCH_RATIO=0.90`、`LOCAL_SEARCH_RADIUS_PX=280`、小地图 255×235）与可选外部进程。
  - **差异**：二进制只暴露 `sift` 单一算法；源码版支持 hybrid / sift / sift_tracker / sift_v02。二进制默认搜索半径 280、源码版默认 550，必须显式映射。
  - **结论**：不把二进制当算法源；算法用源码版，参数用二进制包 `settings.py` 校准。
- **本轮更新（2026-11-05）**：`service.exe` 已作为**可选外部进程**接入，探测脚本为 `adapters/sift_map_tracker/probe_service.py`（启动 → 读 NDJSON → 超时按进程树 `taskkill /T /F`）。实测启动 8.9 s，收到 `ready`×1、`frame`×102、`log`×2，`ready_payload` 含 `refresh_rate_ms=50`、`region={0,0,255,235}`、`route_path`、`control_path`；探测结束无残留进程。协议要点与失败原因见 [BLOCKERS.md](computer://c:\Users\13005\Downloads\work\rocogi\vendor\docs\BLOCKERS.md)。**补位**：用 `Wooziii` 的 `route_planner` 生成 162 节点 `routes\default_route.json`（来源与坐标依据写在 JSON `notes`），并把 region `{0,0,255,235}` 写入 `runtime\settings_override.json`（原文件备份 `.orig`）；探测 76 帧中 74 帧 `found=true`。

### rocom-codex-pets-gen：纠正任务前提

任务描述为"无源码"，实际有 7 个脚本 + 3 个测试（共 10 个 `.py`），`validate_input` 干跑导入通过。真正缺的是：单实体资源目录、rocom-pets 1.14.2 离屏渲染器、Codex Pets 插件环境。缺口不可从本仓其它分支补；发布物里也没有资源包。

- **本轮更新（2026-11-05）**：资源规范已逐项拆解（`entity.json` / `manifest.toml` / 两份 `model.glb` / `anim.rka` / `tex(body,eyes,body-mask).png` / metadata 5 文件 / `voice/*.wem`）；渲染器 `rocom-pets` 1.14.2 已下载并校验 sha256。**仍缺的是真实游戏资源**（本机游戏安装在 `C:\Program Files\洛克王国：世界(2002304)`，需用 rocom-pets GUI 从游戏 pak 导出），这一步无法在无人值守下完成 → `partial`。

### eachyczhang-RocoTools：数据缺口

`data/pets`、`data/skills`、`data/elements` 只有 `.gitkeep`，服务端 18 张表 schema 与 9 组 REST 路由都在，但没有可导入数据。可选补全路径：仓库自带 `crawler/` 重抓、`app/server` 的 import 脚本配外部 xlsx/json、或用 `NRC_AI/data/nrc.db` 的 461 条宝可梦/491 条技能做部分字段映射。

- **本轮更新（2026-11-05）**：已用仓库自带 `crawler/` 从 BWIKI MediaWiki API 实抓，落地到 `data/`：594 宠物 / 553 技能 / 571 图标，共 15,001,966 B。抓取失败数与来源见 `docs/evidence/rocotools_crawl_stats.json`。

### Wooziii-roco-map-tracker：上游脏数据

`roco-map-tracker/point.json` 实际是 biligame wiki 的 HTML 页面被误存为 `.json`，无法解析。适配层改用 `data/points.normalized.json`（2436 条），并在契约里标注该文件不可用。

## 适配层清单

| 适配器 | 上游 | 关键动作 | 状态 |
| --- | --- | --- | --- |
| `adapters/rocopilot` | Makapic-RocoPilot | config 路径重定向、模板/模型清点、SendInput 回退声明 | adapted |
| `adapters/auto_rocokingdom` | yorusacri-Auto-rocokingdom | 窗口/截图/模板路径重定向、core 入口契约 | adapted |
| `adapters/luoke_location` | zh19990906-luoke_location | 绝对小地图坐标 → 相对 ROI + 1920×1080 归一化；三种小地图尺寸配置化 | adapted |
| `adapters/roco_map_tracker` | Wooziii-roco-map-tracker | 直接 import SIFTEngine/route_planner；6144×5888 ↔ 8192×8192 三点仿射 | adapted |
| `adapters/autocapture` | Tsuann-RocoKingdom-AutoCapture | Linux/RKNN → Windows mss + ONNX 内存注入 | adapted |
| `adapters/game_automation` | SCH-CMYK-game-automation | MiningConfig 导入、DPI 归一化、torch/interception 降级 | adapted |
| `adapters/nrc_ai` | ColinHong10-NRC_AI | 只读 sqlite 数据契约 | adapted |
| `adapters/pets_gen` | rocom-codex-pets-gen | 脚本导入、外部资源缺口清单、资源目录规范拆解、rocom-pets 校验 | partial |
| `adapters/adolph_rules` | Adolph321-Adolph | Node `verify.js` + 规则索引契约 | adapted |
| `adapters/sift_map_tracker` | sift-map-tracker | 发布哈希校验、参数映射、替代关系、`service.exe` NDJSON 探测、默认路线生成 | resolved |
| `adapters/interception` | oblitum-Interception | 解析 C API/枚举契约；v1.0.1 驱动安装（UpperFilters 已写入） | resolved |
| `adapters/bettergi` | babalae-better-genshin-impact | 导出截图/热键/输入公开类型契约；便携 .NET SDK 10 构建通过 | resolved |
| `adapters/yotta` | yottaapp-yotta | node-contract schema 与 189 内置节点；Go 1.25.13 + Wails beta.6 构建通过 | resolved |
| `adapters/rocokingdom_ui` | rookie-orange-rocokingdom-ui | 设计令牌与组件清单；Node 22 + pnpm 11.5.3 构建通过 | resolved |
| `adapters/rocotools` | eachyczhang-RocoTools | REST 路由 + 18 表 schema；BWIKI 实抓数据落地 | resolved |
| `adapters/balance_lab` | Pacific-shark-roco-balance-lab | Node 直接 import 引擎并校验数据集 | adapted |

- 公共基座：`adapters/_common/`（`paths.py` 路径守卫、`coords.py` 三点仿射/DPI/小地图尺寸、`result.py` 统一结构化输出）。
- 每个适配器的完整契约已落盘：`adapters/<name>/contracts/adapter_contract.json`。
- 用法与解释器分配见 `adapters/README.md`。

## 卡点处理结果（原 7 项 blocked）

| 仓库 | 原卡点 | 补了什么（版本 / 路径） | 实测（命令 + 输出摘要） | 状态 | 仍缺什么 |
| --- | --- | --- | --- | --- | --- |
| yotta | 无 Go 工具链 | 便携 Go 1.25.13 → `.toolchain\go`；`go install` Wails v3.0.0-beta.6 → `.toolchain\gobin`；Node 24.18.0；复用系统 WebView2 `156.0.4314.58` | `wails3 generate bindings`（559 packages / 19 services / 231 methods）→ `go build -trimpath -o yotta.exe .` exit 0，60,669,952 B | resolved | — |
| bettergi | 无法构建 | 便携 .NET SDK 10.0.403 → `.toolchain\dotnet10`（上游目标框架是 `net10.0-windows10.0.22621.0`，不是 .NET 8）；`DOTNET_ROOT`/`APPDATA`/`NUGET_PACKAGES` 仅进程内 | `dotnet build -c Release` → 0 错误 / 555 警告，产出 `BetterGI.exe` | resolved（仅 build，未跑 WPF UI） | — |
| rocokingdom-ui | 缺 pnpm | 便携 Node 22.23.4 + `npm install -g pnpm@11.5.3`（全局前缀指向 `.toolchain\npm-global`，不装系统）；Git 2.56.0 供 `prepare` 脚本；`--node-linker=hoisted --package-import-method=copy` 规避符号链接 EBUSY | `pnpm -r run build` exit 0，`✓ built in 1.81s` | resolved | — |
| RocoTools | 图鉴数据缺失 | 仓库自带 `crawler/`（BWIKI MediaWiki API）+ 便携 venv → `vendor\eachyczhang-RocoTools\data\` | 594 宠物 / 553 技能 / 571 图标，15,001,966 B（`docs/evidence/rocotools_crawl_stats.json`） | resolved | — |
| pets-gen | 缺资源与渲染器 | `rocom-pets` 1.14.2（54.5 MB，sha256 `21DAFC…B4E5`），资源规范逐项拆解 | `rocom-pets.exe --help` 无 stdout（GUI 子系统静默）；CLI 参数从二进制字符串提取 | partial | 真实游戏资源（`model.glb`/`anim.rka`/tex/voice）需用 rocom-pets GUI 从本机游戏 pak 导出 |
| sift-map-tracker | 无运行时源码 | `adapters\sift_map_tracker\probe_service.py`（stdio 探测 + 超时杀进程树）+ `build_default_route.py`（Wooziii route_planner 生成 162 节点路线）；region 写入 `settings_override.json` | 启动后路线激活成功；76 帧中 74 帧 `found=true`，`center=(3123,2511)`，`route_name=默认采集路线-701` | resolved | — |
| Interception | 驱动未安装 | Interception v1.0.1（389,119 B，sha256 `AD0389…AF10`），`Start-Process -Verb RunAs /install` | `keyboard.sys`/`mouse.sys` 已安装；键盘 `{4D36E96B}`、鼠标 `{4D36E96F}` 的 `UpperFilters` 已写入 | resolved（待重启生效） | 需用户重启一次使过滤驱动挂载 |

逐项完整证据（命令原文、安装器输出、事件日志与失败码）见 [BLOCKERS.md](computer://c:\Users\13005\Downloads\work\rocogi\vendor\docs\BLOCKERS.md)；工具链下载 URL / 版本 / sha256 见 [TOOLCHAIN.md](computer://c:\Users\13005\Downloads\work\rocogi\vendor\docs\TOOLCHAIN.md)。

## 自检证据

| 项目 | 结果 |
| --- | --- |
| 逐仓文件比对 | 16/16 仓库 0 缺失（排除 `.git`/`__pycache__`/`.venv`） |
| 许可证文件 | 11 个仓库带 LICENSE/COPYING；5 个未声明（AutoCapture、roco-map-tracker、rocokingdom-ui、sift、luoke）已在清单标注 |
| 令牌扫描 | 0 个命中（`ghp_*` / `github_pat_*` / `sk-*` / `AKIA*` / `.env` / `credentials.json`） |
| 绝对路径扫描 | 2 处命中，均为上游自带系统常量（`yotta/scripts/browser-cdp-smoke.ps1` 的 Chrome 路径、`roco-map-tracker/.learnings/ERRORS.md` 的 Codex 路径）；**无本机 `C:\Users\13005` 路径** |
| 适配器干跑 | `--help` 16/16 成功；`--json` 15 resolved/adapted / 1 partial / 0 still-blocked / 0 error |
| 构建实测 | yotta `go build` exit 0（60.7 MB）；BetterGI `dotnet build` 0 错误；rocokingdom-ui `pnpm -r build` exit 0；证据在 `docs/evidence/` |
| 运行实测 | sift `service.exe` NDJSON 探测 + 合成小地图：74/76 帧 `found=true` 并清理进程树；RocoTools 抓取 594/553/571 条 |
| 重启自检 | `vendor\tools\post-reboot-check.ps1` 就绪；重启前 24 PASS / 3 FAIL（仅 Interception，属待重启） |
| 驱动安装 | Interception v1.0.1 安装成功，`UpperFilters` 已写入，**未重启系统** |
| 上游只读 | 未修改、未移动、未删除 `work/upstream` 任何文件 |
| 越界写入 | 仅写 `work/rocogi/vendor/` 与 `work/rocogi/.toolchain/`，未触碰 `rocogi/webui`、`rocogi/suite` 与其它代码 |
| Git 操作 | 无 commit / push / 分支写入 |
| 补丁 | 0 个（全部用适配层解决），机制保留在 `patches/` |

## 产物路径

- 机器可读清单：[manifest.json](computer://c:\Users\13005\Downloads\work\rocogi\vendor\manifest.json)（16 仓库，含 commit / 许可证 / 语言 / 体积 / 入口 / 构建要求 / 完整度 / 卡点状态）
- 人类可读清单：[INVENTORY.md](computer://c:\Users\13005\Downloads\work\rocogi\vendor\docs\INVENTORY.md)
- 自检明细：[import_selfcheck.json](computer://c:\Users\13005\Downloads\work\rocogi\vendor\docs\import_selfcheck.json)
- 卡点逐项处理：[BLOCKERS.md](computer://c:\Users\13005\Downloads\work\rocogi\vendor\docs\BLOCKERS.md)
- 便携工具链与复用检查：[TOOLCHAIN.md](computer://c:\Users\13005\Downloads\work\rocogi\vendor\docs\TOOLCHAIN.md)
- 构建/运行证据：`vendor\docs\evidence\`（yotta、BetterGI、rocokingdom-ui、RocoTools、sift）
- 适配层说明：[adapters/README.md](computer://c:\Users\13005\Downloads\work\rocogi\vendor\adapters\README.md)
- 补丁机制：[patches/README.md](computer://c:\Users\13005\Downloads\work\rocogi\vendor\patches\README.md)、[apply.ps1](computer://c:\Users\13005\Downloads\work\rocogi\vendor\patches\apply.ps1)

## 复现命令

```powershell
# 重新生成清单
& .toolchain\python\cpython-3.12.16-windows-x86_64-none\python.exe rocogi\vendor\docs\tools\generate_manifest.py
# 重新自检（文件比对 + 安全扫描 + 16 个适配器干跑）
& .toolchain\python\cpython-3.12.16-windows-x86_64-none\python.exe rocogi\vendor\docs\tools\verify_import.py
# 重新导出契约
& .toolchain\python\cpython-3.12.16-windows-x86_64-none\python.exe rocogi\vendor\docs\tools\export_contracts.py
```

## 已跑通的构建命令（全部便携、仅进程内环境变量）

```powershell
# yotta（Go + Wails v3）
$tc = "work\rocogi\.toolchain"
$env:PATH = "$tc\go\bin;$tc\gobin;$tc\node24;$env:PATH"
$env:GOROOT = "$tc\go"; $env:GOPATH = "$tc\gopath"; $env:GOCACHE = "$tc\gocache"
Set-Location work\rocogi\vendor\yottaapp-yotta
node frontend\scripts\generate-bindings.mjs          # 必须先跑，否则缺 bindings
npm --prefix frontend run build                      # 前端产物 frontend/dist
& "$tc\go\bin\go.exe" build -trimpath -o "$tc\build\yotta.exe" .

# BetterGI（.NET 10 SDK，非 .NET 8）
$env:DOTNET_ROOT = "$tc\dotnet10"
$env:APPDATA = "$tc\appdata"; $env:NUGET_PACKAGES = "$tc\nuget-packages"
& "$tc\dotnet10\dotnet.exe" build work\rocogi\vendor\babalae-better-genshin-impact\BetterGenshinImpact\BetterGenshinImpact.csproj -c Release

# rocokingdom-ui（Node 22 + pnpm 11.5.3）
$env:PATH = "work\.toolchain\node;$tc\npm-global;work\.toolchain\git\cmd;$env:PATH"
$env:PNPM_HOME = "$tc\pnpm-home"
Set-Location work\rocogi\vendor\rookie-orange-rocokingdom-ui
pnpm install --node-linker=hoisted --config.package-import-method=copy
pnpm --config.verify-deps-before-run=false -r run build

# RocoTools 数据抓取
& .toolchain\python\cpython-3.12.16-windows-x86_64-none\python.exe -m venv work\rocogi\.toolchain\venv-crawler
& work\rocogi\.toolchain\venv-crawler\Scripts\python.exe work\rocogi\vendor\eachyczhang-RocoTools\crawler\run.py

# sift-map-tracker 可选外部进程探测（探测后自动清理进程树）
& .toolchain\python\cpython-3.12.16-windows-x86_64-none\python.exe work\rocogi\vendor\adapters\sift_map_tracker\probe_service.py
```

## 说明

- 本轮未下载新仓库、未拉 LFS；工具链与依赖（Go / .NET SDK / Node / pnpm / NuGet / rocom-pets / Interception）全部下载到 `work/rocogi/.toolchain/`，URL 与 sha256 记录在 `docs/TOOLCHAIN.md`。
- 所有工具链均为便携解压，只用**进程内环境变量**（`PATH`/`GOROOT`/`GOPATH`/`GOCACHE`/`DOTNET_ROOT`/`APPDATA`/`NUGET_PACKAGES`/`PNPM_HOME`），未写系统 PATH、未改注册表、未装系统服务。
- 例外说明：Interception 是内核过滤驱动，安装必然写系统级注册表（`UpperFilters`），已在用户授权范围内执行，且**未重启系统**。
- `vendor/<repo>/` 源码与 `work/upstream/<repo>/` 逐字节一致（仅缺 `.git`/`__pycache__`/`.venv`）；构建产物（`node_modules`/`dist`/`obj`/`bin`/`data`）是新增的，不参与源码比对。
- 新增的非源码内容位于 `vendor/adapters/`、`vendor/docs/`、`vendor/patches/`、`vendor/manifest.json`，以及各仓库内的构建产物与 `data/`。
