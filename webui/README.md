# Rocogi 工作流套件 · WebUI（对齐 0.4.0）

一个无构建步骤的深色工作流控制台，直接读取**真实运行数据**（套件 `runs/`、`logs/`、资产清单、CLI，以及 8787/8788 后端），不做游戏画面渲染，也不做窗口识别。

- 入口页面：[index.html](index.html)
- 服务地址：`http://127.0.0.1:8800`
- 接口契约：[docs/api-contract.md](docs/api-contract.md)
- 验证记录：[verify-round-1](docs/verify-round-1.md) … [verify-round-7](docs/verify-round-7.md)

## 版本口径（按端口分别标注，不统一显示 0.4.0）

| 组件 | 端口/路径 | 版本 | 说明 |
|---|---|---|---|
| 工作流套件 | `work/rocogi/suite` | **0.4.0** | 7 引擎 / 55 组件 |
| Python 后端 | 8787 | **0.4.0** | 本轮已升级 |
| C 核心 | 8788 | **0.2.0** | 未随本轮升级，界面按端口单独标注 |
| WebUI 适配层 | 8800 | — | 只读适配，不声明后端版本 |

## 怎么起

```powershell
# 工作目录内，无需 npm / 无需构建
& 'C:\Users\13005\Downloads\work\rocogi\.toolchain\python\cpython-3.12.16-windows-x86_64-none\python.exe' `
  'c:\Users\13005\Downloads\work\rocogi\webui\server.py'
```

打开 `http://127.0.0.1:8800`。服务仅监听 127.0.0.1:8800，不触碰 5173 / 8787 / 8788。

验证脚本（每轮逐接口请求，真实触发一次 `run --once`）：

```powershell
& 'C:\Users\13005\Downloads\work\rocogi\.toolchain\python\cpython-3.12.16-windows-x86_64-none\python.exe' `
  'c:\Users\13005\Downloads\work\rocogi\webui\scripts\verify_round.py' --round 8
```

## 0.4.0 改动点清单

1. **组件状态四档（实锤缺陷修复）**：`/wapi/components` 原来把 `not-wired` 与 `blocked-vendor` 折叠为 `ready`，只单独区分 `skipped`。现在严格按 `suite/config/components.toml` 输出 `ready / not-wired / skipped / blocked-vendor`，统计为 **44 / 6 / 1 / 4（共 55）**，不再由引擎 venv 覆盖真实状态。
2. **每档计数徽标**：组件页顶部新增 5 个 KPI 与四档徽标；每个引擎分组头显示本组四档小计数；行级状态 chip 四色区分，行内展开 `原因 / 说明 / 声明 status / implemented / 依赖 / 入口 / 配置 / 使用方`，hover 直接显示原因。
3. **总览状态行**：运行总览新增一行固定文案 **“55 组件：44 ready / 6 not-wired / 1 skipped / 4 blocked-vendor”** 并附四档徽标，避免误以为全部可用。
4. **Vendor 面板独立口径**：组件页新增 16 仓表格，按 `vendor/manifest.json` 的仓级 `resolution` 输出 **15 resolved / 1 partial / 0 blocked**；与 suite 组件的 `blocked-vendor`（4 条）明确标注为两套口径，不相加、不混用。
5. **Vendor blocked 与待重启**：总览与 Vendor 面板都单列 blocked 项（现仅 `pets-gen`，专有资源需 GUI 导出）与 **Interception 待重启生效**提示（重启后跑 `vendor/tools/post-reboot-check.ps1`，重启前 24 pass / 3 fail）。
6. **发布信息**：总览新增 0.4.0 发布块，展示 `docs/verify-release-0.4.0.md` 的两个包体：lite 17,527,749 B / 530 文件 / `sha256 9519fe73…`；full 933,988,491 B / 9,214 文件 / `sha256 74d1478b…`（适配层本地计算并缓存）。
7. **按端口标注版本**：顶栏显示 `8787 0.4.0` 与 `8788 0.2.0`；左栏 suite / python / core 三处版本各自显示；概览 KPI 明确 `py 0.4.0 · c 0.2.0`。
8. **常驻 run 置顶**：首屏默认选中 `side-live5`（supervised，7 引擎 / 15 进程），同时保留 `latestRun`；每轮新触发的 run 会出现在运行列表首位并更新 overview 的 `latestRun`，但不抢占常驻选中。
9. **新增只读端点**：`GET /wapi/vendor`、`GET /wapi/release`；`/wapi/overview` 增加 `versions`、`componentSummary`、`pinnedRun/latestRun`、`vendor`、`release`、`runCount`。
10. **运行状态修正**：supervised run 不再一律显示 `stopped`，改为按 PID 存活判定 `running`，并推导进程树数量（当前 15）。

## 面板与数据来源

| 面板 | 内容 | 真实来源 |
|---|---|---|
| 01 运行总览 | 7 引擎 venv 状态、55 组件四档统计、当前 run（默认 side-live5）、成败/耗时/事件/进程数、分端口版本、发布信息、Vendor 摘要 | `config/components.toml` + venv 探测；`runs/<id>/{manifest,metrics}.json`；8787/8788 `/api/health`；`vendor/manifest.json`；`docs/verify-release-0.4.0.md` + `release/*.zip` |
| 02 工作流视图 | 4 条真实 DAG，按后端 `x/y` 坐标还原节点与连线，悬停高亮依赖、点击看类型/分类/配置 | 8787 `/api/workflows` + `/api/nodes` |
| 03 组件图谱 | 55 个组件按 7 引擎分组；`ready / not-wired / skipped / blocked-vendor` 四档不折叠，带原因与展开详情；16 仓 Vendor resolution 独立表格 | `config/components.toml`、`vendor/manifest.json`、8787 `/api/components` 的 usage |
| 04 运行证据 | manifest（含 config sha256、快照字节、引擎版本）、引擎 metrics、事件时间线（按引擎筛选） | `runs/<id>/{manifest,metrics}.json`、`events.jsonl` |
| 05 资产校验 | 点位 9224、SIFT 特征 94992、10 个文件哈希、mmap 耗时、逐文件清单；可一键重跑 | `assets/manifest.json` + 实时校验 |
| 06 实时日志流 | 选择 run/引擎，按字节 offset 每秒增量读取 JSONL，可暂停/清屏 | `logs/<id>/<engine>.jsonl` |
| 07 链路触发 | SIFT 定位、路线规划、状态机、对战决策，以及完整 `run --once`（7 引擎）；返回原始 JSON | `rocogi-suite call <engine> <action>`、`run --once` |

## 五轮复验结果（实际执行 7 轮，全部 PASS）

每轮 26 项检查：HTML/CSS/JS、overview 四档与双版本、components 四档计数与原因、vendor 16 仓、release 两包 sha8、工作流、运行/事件/日志/增量语义、资产校验、两处桥接、4 条链路、1 次真实 `run --once`、新 run 首位且常驻不抢占；另做浏览器控制台检查（0 error）。

| 轮次 | 结论 | 控制台 | 新 run | 关键断言 |
|---|---|---|---|---|
| 1 | PASS 26/26 | 0 error | `ui-20261105-193811`，14 事件 | 55 组件 44-6-1-4；vendor 16·15·1·0；py 0.4.0 / c 0.2.0 |
| 2 | PASS 26/26 | 0 error | `ui-20261105-194009`，14 事件 | 同上；release lite `9519fe73` / full `74d1478b` |
| 3 | PASS 26/26 | 0 error（复核） | `ui-20261105-194203`，14 事件 | 同上；当前 run `side-live5` 15 进程 |
| 4 | PASS 26/26 | 0 error | `ui-20261105-194432`，14 事件 | 同上；新 run 首位、latest 更新、pinned 不变 |
| 5 | PASS 26/26 | 0 error（复核） | `ui-20261105-194618`，14 事件 | 同上 |
| 6 | PASS 26/26 | 0 error | `ui-20261105-194840`，14 事件 | 追加回归 |
| 7 | PASS 26/26 | 0 error | `ui-20261105-195040`，14 事件 | 追加回归；4 条链路全部 status=ok |

说明：第 3、5 轮浏览器代理首次进入组件页时误用了不存在的 `/components` 路由（SPA 内应点击 `03 组件图谱`），重试后均为 0 error；产品侧无改动，API 轮次当轮即为 26/26。失败尝试未计入上表。

## 仍未解决的接口缺口

详见 [api-contract.md 第 3 节](docs/api-contract.md)。本轮新增/保留的关键缺口：

1. **8788 C 核心仍为 0.2.0**，未随套件 0.4.0 升级；前端只能按端口分别标注，无法统一版本。
2. **vendor manifest 有 9 个仓没有显式 `resolution.status`**，适配层按“resolved/adapted”归纳；这 9 仓没有逐仓 `resolution.done` 记录。
3. **`pets-gen` 不是独立 `blocked` 字段**：它在 `status=partial` + `resolution.still_blocked`，UI 以 blocked 项呈现；仓级 `blocked` 计数仍为 0。
4. **release 文档不含 sha256**：两个包的 sha256 由适配层本地计算（lite `9519fe73…`、full `74d1478b…`）并缓存；重打包后需刷新缓存文件。
5. **无权威进程数接口**：“15 进程”由 Windows Toolhelp32 进程树推导（supervisor + 7 引擎主进程 + 7 worker），非后端声明字段。
6. **`side-live5` 的 duration=0.0、事件持续追加**，不是“完成”语义；UI 依据 PID 存活标 `running`。
7. **事件/日志无 SSE/WebSocket**，前端仍按字节 offset 每秒轮询。
8. **8787 `/api/components` 的 usage 只覆盖部分组件**，未覆盖的显示“未在 8787 usage 中出现”。
9. **8788 无引擎清单与运行证据**，仅能展示 health/uptime。
10. 继承缺口：8787 `/api/runs` 不读套件 runs；工作流 DAG 运行不写套件证据；资产校验缓存依赖 `sift` venv；`runs/` 会被外部会话清理；系统时间跳变影响 supervisor 计时（G11）。

## 边界

- 只写 `work/rocogi/webui/`；未改 `suite/`、`backend/`、`vendor/`、`work/upstream`、现有 5173 前端，未执行任何 git 操作。
- 适配层对上游只读；唯一写入是 `webui/.cache/` 下的资产校验缓存与 release sha 缓存。
- 不删除任何目录或文件。
