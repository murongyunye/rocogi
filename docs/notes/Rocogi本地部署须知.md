# Rocogi · 洛克工坊

> 以 [yottaapp/yotta](https://github.com/yottaapp/yotta) 的工作流结构为骨架，按 [BetterGI](https://github.com/babalae/better-genshin-impact) 的启动器 / 任务计划 / 实时触发布局组织，面向《洛克王国：世界》的本地优先自动化工作台。

Rocogi 把截图、模板识别、键鼠输入、地图定位、资源路线与对战决策连接成可编辑、可运行、可回放的工作流。它不读取游戏内存，所有数据、资源和运行记录都留在本机。

架构上，Rocogi 把能力拆成 6 个引擎、39 个组元；每个功能只装配它需要的那部分组元，同一个组元可以同时服务多个功能。「组件图谱」页面会实时展示这份复用矩阵。核心逻辑只使用屏幕截图、模板识别与键鼠模拟，绝不读取游戏内存。

![启动器](docs/screenshots/00-launcher.png)

## 布局与交互

界面按 BetterGI 的信息架构组织：

- **启动器**：横幅 + 实时引擎启动卡 + 功能模块卡片 + 最近执行。
- **一条龙**：左侧任务列表（开关、排序、循环轮数），右侧任务配置与执行进度，计划会同步生成可编辑的独立工作流。
- **实时任务**：对应 BetterGI 的实时触发，持续截图、识别并执行丢球 / 战斗 / 同行确认。
- **独立任务**：可视化工作流编辑器。
- **执行记录**：节点时间线、日志、变量、节点输出与截图证据。
- **工具**：地图追踪（SIFT Map Tracker）、图鉴速查、桌宠工坊、资源地图、对战实验室、PvP 平衡实验室、资源库、AI Harness。
- **配置**：引擎参数（预设与当前参数）、组件图谱（功能-组元复用矩阵）、本机设置。

## 已整合的工具

| 来源 | 在本项目中的角色 | 集成方式 |
| --- | --- | --- |
| [yottaapp/yotta](https://github.com/yottaapp/yotta) | 产品蓝图：Workflow / Node Contract / Target / Resource / Run Evidence | 按同一套概念重新实现 Python 运行时与 Vue 编辑器，未复制其源码 |
| [babalae/better-genshin-impact](https://github.com/babalae/better-genshin-impact) | 架构与布局参考：启动器、任务计划、实时触发、执行记录 | 只参考信息架构与自动化流程；未复制 GPL 源码，也未使用其原神数据集、任务配置、素材或地图 |
| [Makapic/RocoPilot](https://github.com/Makapic/RocoPilot) | 视觉模板、自动丢球、污染/普通战斗策略、Interception 输入思路 | 模板资源 + 场景识别与策略节点；新增 Interception 输入适配层 |
| [yorusacri/Auto-rocokingdom](https://github.com/yorusacri/Auto-rocokingdom) | 智能战斗、同行确认、丢球模板 | 模板与节点行为参考 |
| [ColinHong10/NRC_AI](https://github.com/ColinHong10/NRC_AI) | 洛克王国对战引擎与数据 | `backend/vendor/nrc_ai` 内置源码与 `nrc.db`，提供 MCTS 决策/推演 |
| [zh19990906/luoke_location](https://github.com/zh19990906/luoke_location) | SIFT 小地图定位 | 重新实现定位源适配器，支持锚点缓存与本地邻域搜索 |
| [Wooziii/roco-map-tracker](https://github.com/Wooziii/roco-map-tracker) | 地图底图与 POI 点位 | 导入 9,224 个去重点位与 6144×5888 世界地图 |
| [夸克网盘 SIFT-Map-Tracker](https://pan.quark.cn/s/bb51fb772eec) | SIFT Map Tracker v0.10.2：WPF 客户端 + 自包含服务 + 地图/特征/ONNX 资源 | 可选外置包 `optional/sift-tracker/` 导入定位引擎，提供 `tracker_info / tracker_prepare / tracker_launch`；Windows 才能启动 |
| [SCH-CMYK/game-automation](https://github.com/SCH-CMYK/game-automation) | 组件化分层经验：`src/engine` 提供能力组元，`src/automation` 只组合功能所需子集 | 落成 `backend/app/components.py` 注册表、`/api/components` 与「组件图谱」页面；未复制其代码 |
| [eachyczhang/-RocoTools](https://github.com/eachyczhang/-RocoTools) | 图鉴字段模型与快速查询交互：属性、形态、特性、六维、技能、进化链 | 新增「图鉴速查」页面与 `/api/dex/*` 接口，直接读取本地 NRC 图鉴库 |
| [rookie-orange/rocokingdom-ui](https://github.com/rookie-orange/rocokingdom-ui) | 《洛克王国：世界》视觉参考：paper / stone / gold 材质令牌与厚实圆角轮廓 | 仅提取设计令牌并移植到 Vue 主题（上游为 React 组件库，未直接安装）；图鉴卡片与面板使用其 paper/gold 材质 |
| [Tsuann/RocoKingdom-AutoCapture](https://github.com/Tsuann/RocoKingdom-AutoCapture) | 自动捕捉状态机：SCAN → TRACK → AIM → THROW → VERIFY，含重试、验证等待与空视野平移搜索 | 在实时任务中落成捕捉状态机、丢球重试与视角搜索配置；不采用其 RK3588/HID 硬件链路，也不读取内存 |
| [Pacific-shark/roco-balance-lab](https://github.com/Pacific-shark/roco-balance-lab) | PvP 平衡研究：6 人配队、阵容结构、MCTS 推演与证据报告 | 新增「PvP 平衡实验室」页面与 `/api/pvp/*`；用本地图鉴 + NRC MCTS 实现，未复制其强化学习训练代码 |
| [ElliottZhao666666/rocom-codex-pets-gen](https://github.com/ElliottZhao666666/rocom-codex-pets-gen) | 桌宠生成：原模型渲染、九种颜色、动作状态与独立精灵表 | 借鉴其「选精灵 + 动作状态 + 弹窗桌宠」交互，用纯 CSS 绘制伙伴；不依赖其渲染器或游戏模型资源 |
| [Adolph321/-](https://github.com/Adolph321/-) | 对战规则数据集（200 精灵特性 / 200 技能逻辑） | 仅作为规则字段参考，未导入或执行其中的反编译战斗代码 |

> BetterGI 只用于参考架构与自动化流程。它的数据集、任务配置、地图、素材与游戏资源属于《原神》，与《洛克王国：世界》无关，本项目**未导入任何 BetterGI 数据**；图鉴、对战、地图与模板数据分别来自 NRC_AI 与洛克王国世界社区仓库。

> 本项目在 Linux 沙箱中完成了模拟目标的端到端验证。Windows 窗口捕获、SendInput 与 Interception 适配代码已实现，但需要 Windows 实机配合游戏验证。SIFT Map Tracker v0.10.2 从夸克网盘下载后放到 `optional/sift-tracker/`（不进入 Git），再通过附件导入；BetterGI 的安装包与资源属于《原神》，本项目不会导入。

## 功能

- **启动器**：BetterGI 风格横幅、实时引擎启动卡、功能模块、最近执行与本机能力。
- **一条龙任务计划**：5 个任务可排序、开关、配置与循环；计划生成独立 workflow，执行过程写入运行证据。
- **实时任务**：连续识别普通/污染战斗、可捕捉精灵与同行请求，实时预览命中画面、分数与动作日志。
- **SIFT 地图追踪**：实时小地图定位、轨迹回溯、坐标/置信度/延迟、锚点重建、小地图预览与宝箱/植物矿物/精灵/收集路线库。
- **可视化工作流**：节点画布、拖拽连线、条件分支、循环回边、子图、变量与表达式，包含校验提示和实时运行状态。
- **本地优先目标**：工作流只保存逻辑与目标槽位；窗口标题、输入后端、定位源保存在本机设置。
- **场景识别**：OpenCV Canny + 模板匹配，识别普通战斗、污染战斗、可捕捉精灵、交易请求与同行确认。
- **自动丢球与战斗策略**：普通战斗聚能、污染战斗逃跑或技能后聚能，空档期自动丢球。
- **资源路线**：9,224 个点位分类筛选、最近邻路线规划、地图上实时查看当前位置。
- **对战实验室**：内置 NRC 对战数据库与对抗式 MCTS，可编辑阵容并推演至胜负。
- **图鉴速查**：461 精灵 / 491 技能 / 206 进化链，按名称、属性、形态、类别筛选；详情含六维、特性、技能表、进化链与同系推荐。
- **桌宠工坊**：从图鉴选一只精灵，生成可拖动的桌面伙伴窗口；支持待机、跳跃、睡觉三种状态与尺寸调节。
- **PvP 平衡实验室**：6 人阵容编辑、速度线 / 耐久 / 物魔分布 / 技能覆盖分析，以及 MCTS 6v6 推演与战斗日志。
- **捕捉状态机**：实时任务按扫描→丢球→验证→重试运行，可配置最大丢球次数、验证等待与空视野视角搜索。
- **识别增强**：精灵候选检测（可选 ONNX 模型，无模型时轮廓/模板回退）、数字 OCR、卡尔曼位置平滑与 IoU 多目标追踪、结构化战斗回合状态。
- **窗口与热键**：Windows 窗口自动恢复/置前；F9 启动实时、F10 停止、F11 切换地图追踪。
- **组件图谱**：展示 6 个引擎、39 个组元与 10 个功能之间的装配关系，标出每个组元被多少功能复用，可点击功能筛选。
- **AI Harness**：DeepSeek Harness / 任意 agent 通过 HTTP 读取 manifest、观察画面、按键点击、运行任务，并可用 `rocogi_dex_lookup` 查询图鉴。
- **运行证据**：节点时间线、日志、变量、节点输出与截图证据，WebSocket 实时推送并持久化。
- **模拟游戏目标**：无需安装游戏即可完整演示，场景可在设置中切换，方便单独调试识别节点。

![一条龙](docs/screenshots/05-onedragon.png)

![实时任务](docs/screenshots/04-realtime.png)

![地图追踪](docs/screenshots/06-tracker.png)

![独立任务](docs/screenshots/01-workflows.png)

![工作流编辑器](docs/screenshots/02-editor.png)

![资源地图](docs/screenshots/03-map.png)

![对战实验室](docs/screenshots/07-battle.png)

![图鉴速查](docs/screenshots/09-dex.png)

![PvP 平衡实验室](docs/screenshots/11-pvp.png)

![桌宠工坊](docs/screenshots/12-pet.png)

![组件图谱](docs/screenshots/10-components.png)

![运行证据](docs/screenshots/08-run-detail.png)

## 快速开始

### Linux / macOS 演示模式

依赖：Python 3.11+、Node.js 18+。

```bash
cd rocoflow
./scripts/run.sh
```

脚本会创建 `.venv`、安装后端依赖、在缺少前端产物时执行 `npm install && npm run build`，然后启动服务：

```text
http://127.0.0.1:8787
```

也可以手动启动：

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd frontend && npm install && npm run build && cd ..
.venv/bin/uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8787
```

### 前端开发模式

```bash
# 终端 1
cd backend && PYTHONPATH=. ../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8787

# 终端 2
cd frontend && npm run dev
```

访问 `http://127.0.0.1:5173`，Vite 会把 `/api` 与 WebSocket 代理到 8787。

### Windows 实机

1. 安装 Python 3.11/3.12 与 Node.js，克隆本仓库并安装依赖（命令同 Linux，使用 `.venv\Scripts\` 路径）。
2. 在设置中把「游戏目标」切到 **Windows 游戏窗口**，填入窗口标题关键词（默认 `洛克王国：世界`）。
3. 选择输入后端：
   - `Windows SendInput`：无需驱动，兼容性一般；
   - `Interception`：需要先安装驱动与 `interception-python`，以管理员身份运行。
4. 启动后端，打开工作流运行。

Interception 安装步骤：

```powershell
# 1. 下载并解压 oblitum/Interception v1.0.1
#    https://github.com/oblitum/Interception/releases/tag/v1.0.1
# 2. 管理员终端进入解压目录
.\install-interception.exe /install
# 3. 重启电脑
sc query interception   # 状态应为 RUNNING
# 4. 安装 Python 绑定（仅 Windows）
.venv\Scripts\pip install interception-python pywin32
```

详细说明见 [docs/windows-setup.md](docs/windows-setup.md)。

## 内置工作流

| 工作流 | 内容 |
| --- | --- |
| 一条龙 · 今日计划 | 由任务计划生成：丢球、战斗、同行确认、资源巡线按顺序执行并循环 |
| 抓宠巡航 · 自动丢球 | 截图 → 场景识别 → 分支：战斗应对 / 自动丢球 → 变量计数 → 循环回边 |
| 资源巡线 · 宝箱路线 | 地图定位 → 宝箱路线规划 → 沿路线移动 → 日志 |
| 对战推演 · MCTS 决策 | 调用本地对战引擎推演两套阵容 → 按胜负分支 → 结束 |

## 节点

| 分类 | 节点 |
| --- | --- |
| 运行 | 运行开始、结束运行 |
| 流程 | 等待、记录日志、设置变量、条件分支、子图 |
| 采集 | 游戏截图 |
| 视觉 | 模板匹配、场景识别 |
| 游戏 | 自动丢球、战斗应对、同行确认、读取游戏状态 |
| 地图 | 地图定位、规划路线、沿路线移动 |
| 对战 | 对战决策、对战推演 |
| 输入 | 按键、点击坐标、移动视角 |
| 网络 | HTTP 请求 |

字段支持表达式：`vars.count`、`nodes.节点ID.字段`，以及 `{{ }}` 文本模板。

## 架构

```text
frontend/               Vue 3 + Vite 可视化工作台
  views/                启动器、一条龙、实时任务、地图追踪、独立任务、执行记录、工具、设置
  components/           Canvas 编辑器、节点库、检查器、运行控制台

backend/app/
  contracts.py          节点契约（输入/输出端口、字段、分类）
  engine/               图解析、校验、表达式、带循环保护的运行时
  nodes/                23 个内置节点实现
  components.py         引擎组元注册表、功能→组元映射与复用统计
  hotkeys.py            Windows 全局热键（RegisterHotKey 消息循环）
  engine_cli.py         headless 引擎 CLI（JSON-over-CLI）
  engine_sense.py       感知引擎：截图 / 模板 / 场景 / 精灵检测 / OCR / 窗口前台
  engine_input.py       输入引擎：模拟 / SendInput / Interception / 热键信息
  engine_sift.py        定位引擎：SIFT / 锚点 / 路线
  engine_battle.py      对战引擎：图鉴 / 阵容 / MCTS / 回合状态
  engine_flow.py        调度引擎：工作流 / 一条龙
  engine_core.py        统一小引擎：按 group.action 路由
  dex.py                图鉴速查（精灵/技能/进化链，只读本地 NRC 数据）
  pvp.py                PvP 阵容分析、数据观察与 MCTS 6v6 推演
  harness.py            DeepSeek Harness manifest / OpenAI tools / act 网关
  sessions.py           实时任务与 SIFT 地图追踪会话
  onedragon.py          一条龙任务计划与 workflow 生成
  adapters/             模拟/Windows 目标、视觉、输入、SIFT、地图、对战、精灵检测、OCR、卡尔曼追踪
  run_manager.py        Run 生命周期、事件持久化、WebSocket 推送
  api/routes.py         REST、会话与运行证据接口
  services.py           本机目标与适配器编排

backend/vendor/nrc_ai/  NRC_AI 对战引擎（MIT）与 nrc.db
data/                   地图 JSON、底图、模板、对战数据库
packaging/entries/      headless 引擎入口脚本
scripts/build-engines.* Windows / Linux 引擎构建脚本
scripts/package-release.py 核心 / 引擎 / SIFT 分层发行包
optional/sift-tracker/  可选 SIFT Map Tracker v0.10.2（Windows WPF，474 MB）
release/                分层发行归档（core / engine / SIFT）
docs/engines.md         引擎分组、动作与完善度
docs/screenshots/       交付截图
runtime/                运行数据库、截图证据、实时/追踪截图与 SIFT 锚点缓存（自动生成）
```

设计对应关系：

- **Workflow / Graph**：前端画布与 `workflow.graph` JSON。
- **Node Contract**：`contracts.py` 注册的 23 种节点，前端按契约自动生成检查器。
- **Target Slot / Target Binding**：工作流保存 `nrc-game`，本机设置保存实际窗口或模拟目标。
- **Resource**：模板资源入库，节点通过资源名引用。
- **Run / Run Evidence**：每次运行持久化事件、日志、变量、节点输出和截图。

## API 摘要

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/meta` | 版本、平台能力、目标、地图与资源统计 |
| GET | `/api/nodes` | 节点契约目录 |
| GET/POST | `/api/workflows` | 工作流列表 / 创建 |
| GET/PUT/DELETE | `/api/workflows/{id}` | 读取 / 保存 / 删除 |
| POST | `/api/workflows/{id}/run` | 启动运行 |
| GET | `/api/runs` | 运行记录 |
| GET | `/api/runs/{id}/events` | 运行事件 |
| POST | `/api/runs/{id}/stop` | 停止运行 |
| WS | `/api/ws/runs/{id}` | 实时运行事件 |
| GET | `/api/map/points` | 地图点位 |
| POST | `/api/map/route` | 路线规划 |
| POST | `/api/map/position` | 从当前画面定位 |
| GET/POST | `/api/realtime/status|start|stop` | 实时任务会话 |
| GET/POST | `/api/tracker/status|start|stop` | SIFT 地图追踪会话 |
| POST | `/api/tracker/anchors/rebuild` | 重建 SIFT 锚点 |
| GET/PUT | `/api/onedragon/plan` | 一条龙任务计划 |
| POST | `/api/onedragon/run` | 执行一条龙 |
| GET | `/api/battle/pokemon` | 精灵数据 |
| POST | `/api/battle/simulate` | MCTS 推演 |
| GET | `/api/dex/meta` | 图鉴元数据（属性、形态、类别与统计） |
| GET | `/api/dex/pokemon` | 按名称/属性/形态/种族值查询精灵 |
| GET | `/api/dex/pokemon/{name}` | 精灵详情：六维、特性、技能、进化链、同系 |
| GET | `/api/dex/skills` | 技能库查询 |
| GET | `/api/pvp/meta` | PvP 元数据、预设对手与数据观察 |
| POST | `/api/pvp/analyze` | 6 人阵容结构分析 |
| POST | `/api/pvp/matchup` | MCTS 6v6 推演 |
| GET | `/api/components` | 引擎组元注册表、功能装配与复用矩阵 |
| GET | `/api/hotkeys` | 全局热键支持状态与绑定 |
| GET | `/api/engines` | 引擎预设与当前参数 |
| POST | `/api/engines/apply` | 应用引擎预设 |
| GET | `/api/harness/manifest` | Harness manifest / 系统提示词 / 工具列表 |
| GET | `/api/harness/tools` | OpenAI function tools |
| POST | `/api/harness/act` | 执行 agent 动作（含 `dex_lookup`） |
| GET/PUT | `/api/settings` | 本机设置 |

交互式文档：`http://127.0.0.1:8787/docs`。

## Headless 引擎可执行包

39 个组元按功能组合为 5 个功能引擎，并额外提供 1 个统一小引擎。它们不启动 FastAPI、不加载前端，只做 JSON-over-CLI：

| 引擎 | 产物 | 组元 | 主要动作 |
| --- | --- | --- | --- |
| 感知 | `RocogiSense.exe` | capture + vision | capture / classify / match / sprites / ocr / foreground |
| 输入 | `RocogiInput.exe` | input | press / click / move / sequence / hotkey |
| 定位 | `RocogiSift.exe` | sift | locate / meta / points / route |
| 对战 | `RocogiBattle.exe` | battle + dex + pvp | dex_list / analyze / simulate / matchup / turn_state |
| 调度 | `RocogiFlow.exe` | scheduler | workflows / run / status / onedragon_run |
| 统一 | `RocogiEngine.exe` | 全部 | `sense.capture`、`battle.analyze` 等 |

```bash
# Linux 已构建并完成冒烟测试，产物在 dist/engines/
bash scripts/build-engines.sh

# Windows 生成 .exe（PyInstaller 不支持 Linux 交叉编译）
powershell -ExecutionPolicy Bypass -File scripts/build-engines.ps1
RocogiEngine.exe --action library --pretty
```

GitHub Actions 工作流 `.github/workflows/build-engines.yml` 也会在 `windows-latest` 上构建并上传 exe 制品。完整动作、构建方式与当前完善度见 [docs/engines.md](docs/engines.md)。

Linux 实测体积：感知 108 MB、输入 44 MB、定位 108 MB、对战 109 MB、调度 109 MB；五包合计约 478 MB。统一小引擎通过共享运行时与数据，把入口收敛为单个约 109 MB 的 `RocogiEngine`。

可选外置包：`optional/sift-tracker/` 内含 SIFT Map Tracker v0.10.2（约 474 MB 压缩 / 618 MB 解压），不进入基础发行包；用 `RocogiSift --action tracker_prepare` 按需解包，Windows 上再用 `tracker_launch` 启动。

私有仓发行附件：`v0.2.0` Release 已上传 6 个引擎二进制、核心源码 zip、Linux 统一引擎包与 SIFT 合并包，可用 `gh release download v0.2.0 -R murongyunyeh/rocogi` 获取。

当前组件库状态：**27 / 39 已完善，12 个待完善，0 项能力缺口**；待完善项会在组件图谱页面和 `/api/components` 中列出。

## 体积与可选结构

当前工作区约 **1.6 GB**（含开发依赖与可选包），拆解如下：

| 分类 | 体积 | 是否随基础包分发 |
| --- | ---: | --- |
| 核心源码（backend / data / frontend / docs 文本 / scripts / sdk） | 9.5 MB | 是 |
| 核心发行 zip | 10.2 MB | 是 |
| 统一引擎 `RocogiEngine` | 109 MB | 可选 |
| 5 个功能引擎（分组 exe） | 约 478 MB | 可选，通常不需要 |
| SIFT Map Tracker 外置包 | 474 MB | 可选 |
| 文档截图 | 6.7 MB | 可选 |
| runtime（运行记录与 DB） | 29 MB | 否，可清理 |
| dist/engines | 588 MB | 构建产物 |
| .venv / node_modules | 400 MB | 否，开发依赖 |
| references | 94 MB | 否，上游参考 |
| release 归档 | 593 MB | 交付产物 |

体积结论与处理：

- **没有发现核心资源重复**：`data/`、`backend/vendor/`、`frontend/public/` 做过 sha256 扫描，无同内容文件。
- **统一引擎已经合并了 5 个功能引擎的公共运行时**：5 包合计约 478 MB，统一后单个约 109 MB。默认只分发 `RocogiEngine`，5 个分组 exe 作为可选调试包。
- **SIFT 包内 `raw.png` 与 `logic_map.png` 字节完全相同**（各约 46 MB）；本地可用 NTFS 硬链接替代一份，省约 46 MB。
- **SIFT 包与 release 副本已用硬链接**，不会重复占用磁盘；`release` 目录是交付层，`optional` 是源包层。
- **已删除 PyInstaller `build/` 中间目录**（543 MB），构建脚本可随时重新生成。
- 建议发行分层：`core 10 MB` → `core + 统一引擎 约 118 MB` → `+ SIFT 约 594 MB` → 文档截图按需附带。

构建发行包：

```bash
python scripts/package-release.py            # 仅核心源码 zip（10 MB）
python scripts/package-release.py --with-engine  # 加统一引擎
python scripts/package-release.py --all      # 核心 + 引擎 + SIFT + 文档截图
bash scripts/project-size.sh                 # 查看当前体积分类
```

## 测试

```bash
cd backend
../.venv/bin/pip install -r requirements-dev.txt
PYTHONPATH=. ../.venv/bin/pytest
```

覆盖表达式安全求值、图校验、分支/循环运行时、循环保护、种子工作流、地图路线、模拟场景识别、SIFT 定位、连续对战推演、精灵检测、OCR、卡尔曼追踪、回合状态、组件库状态与引擎 CLI，以及「不读取游戏内存」的静态审计。

## 参考仓库（可选）

运行时所需的数据与引擎已随仓库提供。若需要对照上游源码或重新导入素材：

```bash
./scripts/fetch-references.sh
```

脚本会把 yotta、BetterGI、NRC_AI、RocoPilot、Auto-Roco、roco-map-tracker、luoke_location、game-automation、RocoTools、RocoKingdom UI、AutoCapture、roco-balance-lab、rocom-codex-pets-gen 与 Adolph 对战规则克隆到 `references/`。夸克网盘的 SIFT-Map-Tracker v0.10.2 作为可选外置包放在 `optional/sift-tracker/`，不进入基础发行包。

> `references/` 仅用于对照上游实现，不会被后端导入；其中若存在上游的内存读取示例，也未接入 Rocogi 运行时。运行代码只使用截图、视觉与键鼠输入。

## 数据来源与许可

- **yotta**：产品概念与交互结构参考，上游为 source-available 许可；本项目未复制其代码。
- **BetterGI**：启动器 / 任务计划 / 实时触发 / 执行记录的信息架构与自动化流程参考，上游为 GPL-3.0；本项目未复制其源码，未使用其原神数据集、任务配置、素材或地图。
- **RocoPilot / Auto-Roco**：MIT，模板资源与行为策略参考。
- **NRC_AI**：MIT，对战引擎源码与数据库随项目内置，许可证见 `backend/vendor/nrc_ai/`。
- **roco-map-tracker / luoke_location**：仓库未声明统一许可证；地图、点位与图标来自 Easy-Roco、TapTap 社区与哔哩哔哩游戏 WIKI，权利归原作者与权利人。
- **game-automation**：仅参考其 engine / automation 分层思路，未复制代码。
- **RocoTools**：图鉴字段模型与交互参考，上游数据协议为 CC BY-NC-SA 4.0；本项目图鉴直接读取本地 NRC 数据库，未导入其数据文件。
- **RocoKingdom UI**：MIT 许可，仅提取 paper / stone / gold 色板与圆角材质令牌并移植到 Vue 主题，未引入 React 组件代码。
- **RocoKingdom-AutoCapture**：仅参考捕捉状态机、重试与视角搜索思路；其 RK3588 / HDMI / HID 代码与模型未集成。
- **roco-balance-lab**：MIT 许可，参考 PvP 研究维度与交互；本项目用本地图鉴 + NRC MCTS 独立实现，未复制训练代码。
- **rocom-codex-pets-gen**：MIT 许可，参考桌宠动作状态与交互；本项目不包含其渲染器、模型或游戏素材。
- **Adolph321/-**：仅阅读其战斗规则字段说明；未导入 zip 中的反编译战斗代码。
- **SIFT-Map-Tracker（夸克分享 / v0.10.2）**：作为「地图追踪」工具的功能参考，并作为可选 Windows 外置包放在 `optional/sift-tracker/`；其二进制与游戏素材未修改，授权以原作者发布说明为准。

本项目代码采用 MIT 许可，详见 [LICENSE](LICENSE)。第三方数据与素材不自动继承本项目许可，分发前请自行确认权利与游戏条款。完整说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 安全与合规

- 本项目仅供学习、研究与个人自动化实验，**绝不读取游戏进程内存**，不修改游戏文件。
- 后端只使用窗口截图（GDI / PrintWindow）、模板与 SIFT 视觉、键鼠模拟（SendInput / Interception）。
- 静态审计测试会扫描 `backend/app`、`sdk`、`scripts`、`packaging`，禁止出现 `ReadProcessMemory`、`OpenProcess`、`pymem`、`/proc/*/mem` 等内存读取 API。
- 自动化操作可能违反游戏服务条款并带来账号风险，请只在你有权操作的环境中使用。
- 模拟目标不会影响操作系统；切换到 Windows 目标与输入后端前请确认窗口与坐标。
- 运行记录中的截图可能包含账号信息，分享前请自行检查。
