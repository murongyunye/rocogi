# 第一次跑起来

目标：在一台干净的 Windows 上，从克隆到看到界面、跑通一条工作流，不超过 10 分钟。默认用**模拟目标**，不需要装游戏。

## 0. 前置

| 需要 | 说明 |
| --- | --- |
| Windows 10/11 + PowerShell 5.1+ | 启动脚本是 `.ps1` |
| 仓库根 | 所有命令都在 `rocogi\` 目录执行（不是它的上级目录） |
| Python 3.12 | 仓库自带便携版 `.toolchain\python\cpython-3.12.16-windows-x86_64-none\python.exe` |
| Node 20+ | 仓库自带便携版 `.toolchain\node\node.exe` |

`.toolchain\` 是便携工具链，不入库。如果手上没有它，用自己的 Python/Node 也行，改 `start-all.ps1` 顶部三行路径即可：

```powershell
$Py   = Join-Path $Root '.toolchain\python\cpython-3.12.16-windows-x86_64-none\python.exe'
$Node = Join-Path $Root '.toolchain\node\node.exe'
$Vite = Join-Path $Root 'frontend\node_modules\vite\bin\vite.js'
```

## 1. 装依赖

已有 `.venv\` 与 `frontend\node_modules\` 的本机形态可以跳过这一步。干净克隆先体检，再补依赖：

```powershell
.\scripts\bootstrap.ps1          # 逐项体检：[ ok ] / [miss] + 修复命令
.\scripts\bootstrap.ps1 -Apply   # 自动补齐缺的 MinGit / node / vendor / 数据库
.\scripts\setup-windows.ps1
```

`bootstrap.ps1` 只补缺失项：便携 git（落到 `.toolchain\git\`，`fetch-upstream.ps1` 直接用）、
python/uv/node、`.venv`、前端依赖与 `dist`、16 个 vendor 上游、两个第三方数据库。
`-Json` 给 CI 用，全就绪时退出码 0。

`setup-windows.ps1` 做三件事：建 `.venv`、装 `backend\requirements.txt`（外加 `pywin32`、`interception-python`）、装前端依赖并在缺 `frontend\dist\index.html` 时构建一次。

## 1.5 重建第三方数据（仓库与发行包都不带数据库）

从 **0.4.4** 起，BWIKI 战斗库、社区 PvP 数据集、地图物品图标与游戏截图都不入库、也不进发行包 —— 这些内容的权利不属于本项目。仓库里只保留导入脚本与出处说明，需要图鉴增强与 PvP 数据面板时在本机自行生成：

```powershell
# 图鉴增强（788 技能 / 596 精灵）——需要能连 wiki.biligame.com
.\.venv\Scripts\python.exe datasets\tools\bwiki\fetch_bwiki.py --list datasets\bwiki\titles.txt
.\.venv\Scripts\python.exe datasets\tools\bwiki\import_bwiki.py

# PvP 社区数据（674 精灵 / 608 技能 / 41,276 条使用率）——按固定提交匿名拉取
.\.venv\Scripts\python.exe datasets\tools\pvp\fetch_pvp.py
.\.venv\Scripts\python.exe datasets\tools\pvp\import_pvp.py

# 文档截图（13 张，含游戏画面，仅本地留存）
node scripts\verify\make-shots.mjs
```

不跑也能启动：图鉴与对战会回落到 `backend/vendor/nrc_ai/data/nrc.db`（461 精灵 / 491 技能，MIT 项目自带），PvP 数据面板显示「数据集未就绪」并在 `/api/pvp/dataset` 返回 `available: false`。

## 2. 一键拉起

```powershell
.\start-all.ps1
```

脚本是幂等的：已经在跑的服务不会再起一份，直接复用。约 12 秒后打印一张表：

```
service         port status   http version note
python-backend  8787 SKIPPED  200  0.4.6   already listening
c-backend       8788 PASS     200  0.2.0   started
vite            5173 SKIPPED  200  -       already listening
webui           8800 PASS     200  -       started
suite           -    PASS     -    -       resident run 20261107-131238
```

状态含义：

| 状态 | 含义 | 要不要管 |
| --- | --- | --- |
| `PASS` | 本次启动成功并且探活 200 | 不用 |
| `SKIPPED` | 端口上已有服务、探活也 200，直接复用 | 不用 |
| `MISSING` | 依赖或构建产物不存在（如 `backend-c\build2\rocogi-core.exe`） | 按 note 里的命令补 |
| `FAIL` | 起了但探活失败 | 看 `logs\start-all-<stamp>-<service>.err.log` |
| `CONFLICT` | 端口被别的进程占着（不是本仓库的服务） | 先释放端口或改端口 |

退出码：`0` 全部正常；`2` 前置依赖缺失（`.venv` / 便携 Python / Node / vite 之一没找到，脚本会逐条打印修复命令）；`1` 有 `FAIL`/`CONFLICT`/`MISSING`。

日志落在 `logs\start-all-<stamp>.log` 与同名 `.csv`，PID 记在 `logs\pids.json`。

## 3. 打开界面

| 地址 | 是什么 |
| --- | --- |
| http://127.0.0.1:5173 | 前端开发服务器（改代码热更新，日常用这个） |
| http://127.0.0.1:8787 | 后端 + 已构建的前端（`frontend\dist` 存在时同源托管 SPA，可单端口使用） |
| http://127.0.0.1:8787/api/health | 后端探活，返回 `{"status":"ok",...}` |
| http://127.0.0.1:8787/docs | FastAPI 自动生成的接口文档 |
| http://127.0.0.1:8788 | C 核心（可选组件，不参与主链路） |
| http://127.0.0.1:8800 | WebUI 静态预览（可选，`webui\` 是本机目录不入库） |
| ws://127.0.0.1:8787/api/ws/runs/<id> | 运行证据实时推送 |

第一次打开如果看到「目标：模拟」，那就是对的——不需要游戏窗口也能演示全部页面。

## 4. 五分钟验收

```powershell
# 后端接口冒烟：38 项，含工作流运行、实时任务、追踪、PvP、PvP 数据集、图鉴、地图路线
.\.venv\Scripts\python.exe scripts\verify\api_smoke.py

# 前端路由审计：16 个路由的 console 错误 / 异常 / 失败请求 / 溢出
node scripts\verify\cdp-audit2.mjs
```

两条都过了，说明前后端链路是通的。路由审计需要先用 `--remote-debugging-port=9334` 启动 Edge（脚本默认连 `http://127.0.0.1:9334`），具体用法见脚本头部注释。

界面里手点一遍的顺序建议：

1. **启动器** → 看四个统计与「本机能力」；
2. **一条龙** → 勾选任务、点「开始一条龙」，等进度到 100%；
3. **执行记录** → 点最新一条，看时间线、节点输出、截图证据；
4. **实时任务** → 点「启动实时任务」，看预览图、场景识别、命中框与动作日志（按 F10 停）；
5. **工作流** → 打开「抓宠巡航 · 自动丢球」，点「运行」，节点会实时变色。

## 5. 停止

```powershell
.\stop-all.ps1
```

只停 `logs\pids.json` 里记录过的进程，并校验 PID 的启动时间差（≤5 秒）以防 PID 复用误杀；端口被其它程序占用时不会动它。

## 常见问题

**表格里 c-backend 是 MISSING。** C 核心是可选组件，需要 `cmake` + MinGW 自行构建：

```powershell
cd backend-c
cmake -B build2 -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release
cmake --build build2 -j
```

不想构建就忽略——8787 的 Python 后端已经覆盖全部功能。

**5173 打不开但 8787 能开。** 前端没装依赖或没构建：

```powershell
cd frontend; npm install; npm run build
```

**改了 `backend\app\*.py` 不生效。** 启动脚本没带 `--reload`，改完要重启后端：`.\stop-all.ps1` 再 `.\start-all.ps1`。前端改 `.vue` 不用重启，vite 会热更新（`vite.config.ts` 已忽略编辑器的临时目录，避免原子替换把 dev server 带崩）。

**跑后端测试报 `ModuleNotFoundError: No module named 'app'`。** 测试要在 `backend\` 目录下跑：

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests -q
```

**用 PowerShell 调接口看到中文乱码。** `Invoke-WebRequest` 会按 Latin-1 解 UTF-8。用 `curl.exe` 或 Python `urllib` 验证，乱码是显示问题不是数据问题。

**Windows 上识别不了游戏画面。** 先确认游戏在前台：UE5 后台会冻结渲染，截图拿到黑帧。见 [docs/windows-setup.md](windows-setup.md)。
