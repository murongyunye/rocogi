# BLOCKED 项处理结果（7 项）

- 处理时间：2026-11-05
- 边界：只写 `work\rocogi\vendor\` 与 `work\rocogi\.toolchain\`；`work\upstream` 只读；未触碰 `rocogi\suite` / `rocogi\webui`；无删除、无系统 PATH/注册表写入（驱动安装除外，见第 7 项）。
- 工具链细节与下载 sha256：[TOOLCHAIN.md](TOOLCHAIN.md)

## 总览

| # | 项 | 原卡点 | 现在状态 | 关键证据 |
|---|---|---|---|---|
| 1 | yottaapp-yotta（Go/Wails） | 无 Go/Wails，前端缺 bindings | **resolved** | `.toolchain\build\yotta.exe` 60.7 MB |
| 2 | babalae-better-genshin-impact（C#/WPF） | 缺 SDK；且上游目标是 .NET 10，不是 .NET 8 | **resolved（仅 build）** | `0 个错误`，`BetterGI.exe` |
| 3 | rookie-orange-rocokingdom-ui（pnpm） | 缺 pnpm 与依赖 | **resolved** | `pnpm -r run build` exit 0 |
| 4 | eachyczhang-RocoTools（图鉴数据） | `data/` 只有 `.gitkeep` | **resolved** | 594 宠物 / 553 技能 / 571 图标 |
| 5 | rocom-codex-pets-gen（资源/渲染器） | 缺资源目录与渲染器 | **partial** | 渲染器已就位；资源为专有游戏资产 |
| 6 | sift-map-tracker（无源码） | 只有 exe；缺默认路线与 region | **resolved（外部进程 + 默认路线 + region）** | 162 节点路线；`found=true` 74/76 帧 |
| 7 | oblitum-Interception（驱动） | 未安装驱动 | **resolved（待重启生效）** | 驱动文件 + 过滤驱动注册表已写入；`post-reboot-check.ps1` 已就绪 |

---

## 1. yotta（Go + Wails v3）

**原卡点**：无 Go 工具链、无 Wails CLI、无 WebView2、`frontend/dist` 与 `frontend/bindings` 不存在。

**补了什么**

| 组件 | 版本 | 路径 |
|---|---|---|
| Go | `go1.25.13 windows/amd64` | `.toolchain\go`（GOROOT/GOPATH/GOCACHE 均指到 `.toolchain`） |
| Wails CLI | `v3.0.0-beta.6` | `.toolchain\gobin\wails3.exe`（`go install github.com/wailsapp/wails/v3/cmd/wails3@v3.0.0-beta.6`） |
| Node | `24.18.0`（`frontend` 的 `engines.node>=24` + `engine-strict=true` 强制要求） | `.toolchain\node24\node-v24.18.0-win-x64` |
| pnpm | `11.5.3`（root `packageManager` 另锁 11.1.2，由 corepack 缓存） | `.toolchain\npm-global\pnpm.cmd` |
| WebView2 | 系统已装 `156.0.4314.58` | `C:\Program Files (x86)\Microsoft\EdgeWebView\Application` |

**实测**

```powershell
# 1) 生成 Wails RPC 绑定（gitignore 产物，必须先生成）
node frontend/scripts/generate-bindings.mjs
# → Processed: 559 Packages, 19 Services, 231 Methods, 28 Enums, 304 Models, 1 Event（6m32s）

# 2) 前端生产构建
frontend\node_modules\.bin\run-s.CMD build:app bundle:check
# → vite v8.2.1 ✓ built；bundle 预算检查通过；exit 0

# 3) Go 构建
go build -trimpath -o .toolchain\build\yotta.exe .
# → exit 0；产物 60,669,952 B；go version -m 显示 go1.25.13 / github.com/yottaapp/yotta
```

**状态**：resolved。未启动 GUI（避免留窗口），构建产物可执行文件已产出。

**备注**：`pnpm run build` 会先做 deps status 检查并重跑 install，在未开开发者模式的 Windows 上因符号链接 `EBUSY` 失败；已用 `node_modules\.bin\run-s` 直接执行同一脚本，并在 TOOLCHAIN 中记录规避方式。

---

## 2. babalae-better-genshin-impact（C# / WPF）

**原卡点**：按最初假设需要“.NET 8 SDK”，且本机 `dotnet` 不可用。

**纠正**：上游 `BetterGenshinImpact.csproj` 的 `TargetFramework` 实为 **`net10.0-windows10.0.22621.0`**、`LangVersion 14.0`，.NET 8 SDK 无法构建。因此：

| 组件 | 版本 | 路径 |
|---|---|---|
| .NET SDK | `10.0.403`（实际使用） | `.toolchain\dotnet10` |
| .NET SDK | `8.0.427`（已下载保留，未使用） | `.toolchain\dotnet` |
| NuGet 缓存 | — | `.toolchain\nuget-packages`（3.5 GB） |

**实测**

```powershell
$env:DOTNET_ROOT="$tc\dotnet10"; $env:APPDATA="$tc\appdata"; $env:NUGET_PACKAGES="$tc\nuget-packages"
dotnet build vendor\babalae-better-genshin-impact\BetterGenshinImpact\BetterGenshinImpact.csproj -c Release
# → "555 个警告 / 0 个错误"，已用时间 4m3s
# → 产物 bin\Release\net10.0-windows10.0.22621.0\BetterGI.exe
```

**状态**：resolved（仅编译，按任务要求不运行 WPF UI）。

**说明**：构建时 NuGet 会读取 `%APPDATA%\NuGet\NuGet.Config`，沙箱下被拒；已把进程内 `APPDATA` 指向 `.toolchain\appdata`，不改用户配置。未构建测试工程（`TextProcess`/`Test` 依赖上游未随包提供的子模块资源）。

---

## 3. rookie-orange-rocokingdom-ui（pnpm 工作区）

**原卡点**：缺 pnpm、缺 catalog 依赖。

**补了什么**：`.toolchain\npm-global` 安装 `pnpm@11.5.3`（用既有 Node 22 的 npm，进程内 prefix，不装全局到系统）。

**实测**

```powershell
pnpm install --node-linker=hoisted --config.package-import-method=copy
# → resolved 0, downloaded 500+, 7 workspace projects；node_modules 完整

pnpm --config.verify-deps-before-run=false -r run build
# → apps/website build: ✓ built in 1.81s（首次 40.42s）；exit 0
```

**状态**：resolved。产物 `apps/website/dist/`（含 `index.html` 与 assets）。

**卡点规避**：Windows 未开开发者模式时，pnpm 的 `store\v11\projects\<hash> -> 项目目录` 符号链接报 `EBUSY`；用 `--node-linker=hoisted` + `package-import-method=copy`，并绕过 `pnpm run` 的隐式 install 检查。

---

## 4. eachyczhang-RocoTools（图鉴数据）

**原卡点**：`data/pets`、`data/skills`、`data/elements` 只有 `.gitkeep`。

**补了什么**：仓库自带 `crawler/` 就是完整抓取器（MediaWiki API：`wiki.biligame.com/rocom`）。新建 `.toolchain\venv-crawler`（Python 3.12.16 + requests/bs4/lxml），直接执行：

```powershell
venv-crawler\Scripts\python.exe vendor\eachyczhang-RocoTools\crawler\run.py --full
```

**实测结果**（`vendor\docs\evidence\rocotools_crawl_stats.json`）

| 数据集 | 结果 |
|---|---|
| `data/pets/pet_list.json` / `.csv` | **594 条**宠物 |
| `data/skills/skill_list.json` / `.csv` | **553** 条技能 |
| `data/elements/element_chart.json` + 结构化覆盖 | 元素克制表齐全 |
| `data/natures/`、`data/eggs/` | 性格、蛋组数据齐全 |
| `data/public/` | **571 个图标**，15,001,966 B（约 14.3 MB） |
| 总计 | 594 个数据文件 / 16 MB+（不含原有 `.gitkeep`） |

**状态**：resolved。数据源为公开 BWIKI（CC BY-NC-SA 4.0 同源许可），只落盘在 vendor，未改上游。

---

## 5. rocom-codex-pets-gen（资源与渲染器）

**原卡点**：缺“单实体资源目录”和 `rocom-pets` 1.14.2 渲染器。

**渲染器：已补**

- npm 上 **不存在** `rocom-pets`（`registry.npmjs.org/rocom-pets` → 404）。
- 公开源：GitHub `whoisnian/rocom-pets`，release `1.14.2` 提供 `rocom-pets-1.14.2-windows-x64.exe`（54,496,847 B，sha256 `21DAFC…8B4E5`）。
- 许可：仓库**没有 LICENSE 文件**（GitHub API `license=null`），默认“保留所有权利”。按个人非商业自用仅本地使用，不再分发。
- 已确认其内置 CLI（从二进制字符串提取）：`--pack`、`--pet`、`--form`、`--mutation`、`--packs-dir`、`--render <png>`、`--out`、`--size`、`--time`、`--yaw`、`--px-per-cm`、`--sheet`、`--video`、`--ffmpeg`、`--config`、`--list`；并内置 `rocom-pets-export`（环境变量 `ROCOM_PETS_EXPORT` 可覆盖）。
- 实测：`--help` 无 stdout（Windows GUI 子系统程序，静默退出），`--list`/`--render` 缺 pack 时同样静默退出（无 PNG 产物）；不能仅凭 CLI 判定渲染成功，需先有合法宠物包。

**资源：仍缺，且无法自动补**

资源规范见 [resource-directory.md](file:///c:/Users/13005/Downloads/work/rocogi/vendor/ElliottZhao666666-rocom-codex-pets-gen/docs/resource-directory.md)，一个输入根目录必须包含：

```
entity.json            # schema: rkpet2.entity.v1（entity_id/form_asset/palette）
manifest.toml
model.glb              # 根模型：glTF 2.0 + 骨骼 + 命名动画（采样用）
forms/<asset>/
  model.glb            # 原生渲染器几何/骨骼/UV/材质槽
  anim.rka             # 兼容渲染器的动画缓存（专有格式）
  tex/body.png, eyes.png, body-mask.png
  voice/*.wem, *.wav   # 可选
metadata/
  materials.json, face_curves.json, morph_targets.json, animations.json,
  source-files.json    # 文件大小 + SHA-256
effects.json / effects/glassy/...   # 可选颜色效果
```

这些是**游戏本体提取物**（`.glb`/`.rka`/`.wem` 为专有格式），仓库无示例数据，公开源也没有合法分发。

**可行的公开补法（已确认本机具备）**：

- 本机已安装游戏：`C:\Program Files\洛克王国：世界(2002304)`（注册表存在 `洛克王国：世界` 条目）。
- `rocom-pets` 内置导出器可直接从游戏 pak 导出宠物包（GUI“导出/更新选中”，或 `--packs-dir` + 导出后的 pack）。
- 导出 → 用 `rocom-pets --pack <id> --render <png> --size ...` 生成渲染图 → 再交给 pets-gen 的 `render_source.py`。

**状态**：**partial**。渲染器已解决；资源缺口属于“专有游戏资产 + 需交互式 GUI 导出”，不能由脚本自动完成。脚本侧 `validate_input.py --help` / `render_source.py --help` 已通过，依赖（Pillow、imageio-ffmpeg）已装入 `.toolchain\venv-crawler`。

---

## 6. sift-map-tracker（无源码 → 改为可选外部进程）

**原卡点**：只有 PyInstaller 二进制，无运行时源码。

**补了什么**：新增黑盒探测器 [probe_service.py](file:///c:/Users/13005/Downloads/work/rocogi/vendor/adapters/sift_map_tracker/probe_service.py)，并实测 `service.exe`。

**协议要点（实测）**

| 项 | 结果 |
|---|---|
| 启动方式 | 无参数直接启动；无法识别的参数返回 `{"type":"startup_cancelled","reason":"unknown_arguments"}` |
| 已知内部参数 | `--prepare-sift-cache`（从字节码反汇编得到） |
| 传输 | **stdio NDJSON**：服务把 JSON 逐行写 stdout，stderr 为人类日志 |
| 启动耗时 | 约 **6.9–8.9 s**（加载 `assets\SIFT_features.npz`：148,435 keypoints / descriptors (148435,128)） |
| 握手首帧 | `{"type":"ready","refresh_rate_ms":50,"region":{top,left,width,height},"route_path":"...routes\\default_route.json","control_path":"...runtime\\control_state.json","memory_policy":"禁止读取游戏内存…"}` |
| 帧消息 | `{"type":"frame","found":false,"inertial":false,"tracking_source":"searching","minimap_visible":false,"center_x":null…,"frame_ms":0,"image_b64":…,"detected_items":[],"item_status":{"enabled":false},"route_name":null,"waypoint_index":null,"waypoint_total":0,…}`，间隔约 50 ms |
| 日志 | `{"type":"log","level":"error","message":"..."}` |
| 超时/失败行为 | 未配置 region 时：`Tracker loop error: Capture region has not been configured. Select the minimap region in the client first.`；`routes/default_route.json` 不存在时：`Unable to activate route: default_route.json.` |
| 副作用 | 启动即在 `sift-map-tracker/runtime/` 写 `control_state.json`、`settings_override.json` |
| 退出 | 必须 **杀进程树**（PyInstaller onefile 派生子进程）：`taskkill /PID <pid> /T /F`；探测脚本已内置，实测结束后无残留 `service.exe` |

**接入方式**：作为“可选外部进程”由适配层按需拉起 → 逐行解析 stdout → 只消费 `frame`；`control_state.json` 由客户端写（region/route），或在集成侧生成后再拉起。**不常驻**：每次任务结束必须 `taskkill /T`。

**补齐（2026-11-05，补位不覆盖）**

1. **默认路线**：新增生成器 [build_default_route.py](file:///c:/Users/13005/Downloads/work/rocogi/vendor/adapters/sift_map_tracker/build_default_route.py)
   - 数据源：`Wooziii-roco-map-tracker/data/points.normalized.json`（mark_type 701，162 点）
   - 算法：`tracker.route_planner.plan_route`（`fixed_corner` 起点 + 聚类 + 2-opt）
   - 输出：`vendor\sift-map-tracker\sift-map-tracker\routes\default_route.json`（162 nodes / 161 edges / 77,442 B，`format_version = sift0.6`）
   - 坐标沿用 8192 地图像素系（与 legacy v0.10.1 的 `default_route.json` 同区域坐标量级一致）；来源写进 JSON 的 `notes` 字段。
   - 该文件是**新增补位**，未改动/覆盖任何上游文件。
2. **region**：在 `runtime\settings_override.json` 增加 `MINIMAP_REGION = {top:0,left:0,width:255,height:235}`（原文件已备份为 `settings_override.json.orig`）。
3. **实测**：

   ```powershell
   venv-crawler\Scripts\python.exe vendor\adapters\sift_map_tracker\probe_service.py `
       --seconds 10 --synthetic-minimap --crop-size 256 `
       --out vendor\docs\evidence\sift_route_probe.json
   # → 76 帧：found=true 74，minimap_visible=true 74
   # → 首帧 found=true：center=(3123,2511)，route_name=默认采集路线-701，
   #    waypoint_total=162，tracking_source=global_relocate
   # → 日志：Active route changed: default_route.json；不再出现 Unable to activate route
   ```

   `--synthetic-minimap` 仅用于**无游戏自检**：把 `logic_map.png` 裁成 255×235 圆形小地图显示在 region 区域（(0,0)），探测结束后立即关闭窗口。真实游戏接入时不需要该参数。

**状态**：**resolved**。默认路线与 region 已补，`found=true` 已实测（74/76 帧）；真实游戏场景只需把游戏小地图放进 region（或由客户端选择 region）。

---

## 7. oblitum-Interception（内核驱动）

**原卡点**：驱动未安装，需管理员权限。

**补了什么**

- 从 GitHub release 下载 `Interception v1.0.1`（`Interception.zip`，389,119 B，sha256 `AD0389…9AF10`），解压到 `.toolchain\interception\Interception`。
- 安装器：`command line installer\install-interception.exe`（32 位 Inno/NSIS 风格命令行安装器）。
- 提权方式：`Start-Process -Verb RunAs`。实测当前代理进程为**非管理员**（`IsInRole(Administrator)=False`），但 RunAs 启动的子进程获得 **High Mandatory Level**，UAC 未阻塞、无 `consent.exe` 停留。

**实测**

```powershell
$p = Start-Process -FilePath "<installer>" -ArgumentList "/install" -Verb RunAs -PassThru -Wait
# → 安装器退出码 0；日志见 vendor\docs\interception_install_output.txt
```

| 校验项 | 结果 |
|---|---|
| `C:\Windows\System32\drivers\keyboard.sys` | 存在 |
| `C:\Windows\System32\drivers\mouse.sys` | 存在 |
| Keyboard class `UpperFilters` | `keyboard, kbdclass` |
| Mouse class `UpperFilters` | `mouse, mouclass` |
| `identify.exe`（samples\x86） | 重启前无输出（驱动尚未加载，属预期） |
| 系统重启 | **未重启**（按约束） |

**重启后一键自检**：[post-reboot-check.ps1](file:///c:/Users/13005/Downloads/work/rocogi/vendor/tools/post-reboot-check.ps1)（只读脚本，**不会自动重启系统**）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File vendor\tools\post-reboot-check.ps1
```

覆盖项：键盘/鼠标 `UpperFilters`、`keyboard.sys`/`mouse.sys` 文件、`Win32_SystemDriver` 的 `State`、`interception_create_context()`（P/Invoke 加载 `SCH-CMYK-game-automation\interception.dll`，返回非空即 PASS）、端口 8787/8788/5173/8800、以及 `.toolchain` 各组件版本与构建产物。

重启前实测（`docs\evidence\post_reboot_check_pre_reboot.txt`）：**24 PASS / 3 FAIL**，3 个 FAIL 全部是 Interception（`UpperFilters` 已写入，但驱动 `State=NotPresent`、`create_context` 返回 NULL，属重启前预期）；重启后重跑同一脚本即可确认 3 项转 PASS。

**状态**：**resolved（安装完成，待重启生效）**。驱动为系统级组件，`install-interception.exe` 会写 `System32\drivers` 与 `Control\Class` 的 `UpperFilters`；这是本任务唯一允许的系统级写入。

**最小人工步骤（若需在交互式桌面重做一次）**

1. 用 Win+X → “终端(管理员)”（或开始菜单右键 PowerShell → 以管理员身份运行）。
2. 执行：
   ```powershell
   & "C:\Users\13005\Downloads\work\rocogi\.toolchain\interception\Interception\command line installer\install-interception.exe" /install
   ```
3. 看到 UAC 弹窗时点“是”（仅此一次）。
4. **重启一次**，驱动才加载；重启后可用 `samples\x86\identify.exe` 看到 `keyboard=… mouse=…`。
5. 卸载：同一安装器执行 `/uninstall`，再重启。

> 本轮已自动完成步骤 1–3（RunAs 自动通过），仅剩第 4 步“重启”未做。

---

## 结论

- **resolved**：yotta、BetterGI（build）、rocokingdom-ui、RocoTools、sift-map-tracker（默认路线 + region + `found=true` 实测）、Interception（待重启）。
- **partial**：pets-gen（渲染器已补，专有资源需游戏内导出）。
- **still-blocked**：0。
- 全部工具链便携、仅进程内生效；未写系统 PATH、未改用户 NuGet 配置、未装系统服务（驱动除外）。
