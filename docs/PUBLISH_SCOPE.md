# 发布范围

本仓库只放**能复现的文本源码与自有数据**：克隆下来，装上依赖，就能跑起 8787/5173 与全部工作流。工具链、上游整树、构建产物、模型权重一律不入库。这条线如果没写清楚，别人克隆下来只会看到一堆导入错误。

判断标准只有一条：**能被脚本重新生成的，不进仓库；不能重新生成、又是跑起来必需的，必须进仓库。**

> **0.4.4 起新增一条硬约束：第三方游戏数据与美术素材既不进仓库，也不进发行包。**
> 具体指 BWIKI 导出的战斗库（`datasets/bwiki/*.db|json|raw|wiki`）、社区 PvP 数据集（`datasets/pvp/*.db`）、
> 地图物品图标（`datasets/map/icons/`、`data/map/icons/`）与游戏内截图（`docs/screenshots/*.png`）。
> 仓库只保留**导入脚本 + 出处说明**，使用者在自己机器上按各自的权利状况重建。
>
> 同一版还把 `vendor/`（16 个上游仓库整树）、`archive/`、`webui/`、`release/` 移出了版本库：它们分别是
> 第三方代码、交付归档与构建产物，用 `vendor/tools/fetch-upstream.ps1` 与 `scripts/package-release.py`
> 就能重建，不必留在仓库里。跟踪文件数因此从 7653 降到 534。
> 理由：这些内容的知识产权不属于本项目，随仓库/发行包再分发既超出「个人研究」的范围，也容易被判为二次分发。

> **0.4.5 起把「能不能重取」变成机器可查的结论。** `scripts/assets/manifest.json` 记录 34 条资产，
> `scripts/trace-assets.py --check` 现场探测上游是否还在（结果见 [reports/asset-trace.md](reports/asset-trace.md)：
> 25 条可获取、9 条按策略排除或本地独有）。据此，15 个 vendor 上游仓、`archive/release`（1.23 GB 的 0.4.1
> 整包分片）与 `release/` 全部摘出 index；**唯一保留的二进制大头是 `archive/sift-map-tracker/`（338 MB）**，
> 因为它只有作者自建的 release 包、没有公开源码，删了就再也拿不回来。跟踪树由此从 7571 文件 / 1358 MB
> 降到 **936 文件 / 371 MB**（0.4.6 起新增配色轴的适配器与测试；文件数随源码增长，体积由 338 MB 的 SIFT 包主导）。

## 1. 入库（必需）

| 路径 | 内容 | 为什么必须在 |
| --- | --- | --- |
| `backend/app/` | FastAPI 应用：引擎组元、路由、会话、harness | 主体代码 |
| `backend/tests/` | pytest（65 passed / 1 skipped） | 回归防线 |
| `backend/vendor/nrc_ai/` | NRC 对战 AI 源码（MIT）+ `data/nrc.db`（1.2 MB，461 精灵 / 491 技能） | 对战与图鉴的兜底数据源，无网络依赖；数据库是该 MIT 项目自带的发行物 |
| `backend/requirements*.txt` | 依赖清单 | 装环境 |
| `data/map/` | 底图、`easy_roco.json` + `taptap.json`（9224 点位）、`marker_types.json`（4.1 MB）；**不含 `icons/`** | 资源地图与路线规划直接读它 |
| `datasets/tools/bwiki/` | `fetch_bwiki.py` / `import_bwiki.py` / `lua_literal.py` | 数据可重建的唯一路径 |
| `datasets/tools/pvp/` | `fetch_pvp.py`（按固定提交拉三个仓）/ `import_pvp.py` | 数据库从上游重建的唯一路径 |
| `datasets/bwiki/PROVENANCE.md`、`datasets/pvp/PROVENANCE.md` | 来源、固定提交、字段口径、许可声明 | 重建立依据；不含任何数据本体 |
| `datasets/map/poi/`、`datasets/map/poi_legacy/` | POI 坐标 JSON（无美术资源） | 地图数据流水线的输入 |
| `archive/sift-map-tracker/` | SIFT-Map-Tracker v0.10.2 发布包解压件（338 MB：特征 npz、底图 png、`service.exe`） | **无公开源**，删了无法重取；定位与锚点重建要用 |
| `datasets/{pets,scene}/classes.json` | YOLO 类别表与模板 | 识别训练配置 |
| `frontend/src/` | Vue 3 + TypeScript 全部视图与 `rocoui` 组件 | 界面 |
| `frontend/{package.json,vite.config.ts,tsconfig*.json,index.html}` | 前端工程配置 | 构建 |
| `backend-c/`（源码部分） | C 核心 `CMakeLists.txt` + 源码 | 可构建 |
| `suite/kernel/`、`suite/engines/*/engine_main.py`、`suite/config/`、`suite/docs/`、`suite/probes/`、`suite/rocogi-suite.cmd` | 六引擎运行时、探针与文档 | 可选但属于源码 |
| `scripts/` | 构建、部署、验证脚本（`verify/` 下 7 个） | 复现与验收 |
| `docs/` | 说明文档（**不含 `screenshots/`**） | 文档完整性 |
| `start-all.ps1` / `stop-all.ps1` | 一键起停（见 [FIRST_RUN.md](FIRST_RUN.md)） | 本机启动入口 |
| `.github/workflows/` | CI（pytest、引擎构建） | 持续集成 |

## 2. 不入库（可再生成 / 体积大 / 第三方权利）

| 路径 | 体积（本机现状） | 怎么回来 |
| --- | --- | --- |
| `datasets/bwiki/*.db`、`*.json`、`raw/`、`wiki/` | 9.5 MB | `fetch_bwiki.py` + `import_bwiki.py`（需要能连 wiki.biligame.com） |
| `datasets/pvp/*.db`、`.cache/` | 5.0 MB + 7.5 MB | `fetch_pvp.py` + `import_pvp.py`（按固定提交拉三个仓） |
| `datasets/map/icons/`、`data/map/icons/` | 10.2 MB | 地图流水线的图标抓取步骤；游戏内美术，不上传 |
| `docs/screenshots/*.png` | 6.7 MB | `node scripts/verify/make-shots.mjs` 本地导出 13 张 |
| `.toolchain/` | 1.2 GB | 便携 Python 3.12.16 / Node / MinGW / uv；改 `start-all.ps1` 顶部路径或用系统安装版 |
| `.venv/` | 211 MB | `scripts/setup-windows.ps1` |
| `frontend/node_modules/`、`frontend/dist/` | — | `cd frontend; npm install; npm run build` |
| `vendor/`（15 个可追溯上游仓，工作副本） | 50 MB | `vendor/tools/fetch-upstream.ps1`，按 `vendor/upstream_sources.json` 的 commit 逐个拉回（`bootstrap.ps1 -Apply` 也会补） |
| `suite/assets/{maps,features,models,db}/` | 199 MB | `suite/assets/build.py` 从 `vendor/` + `datasets/` 重建 |
| `suite/engines/*/.venv/`、`suite/logs/`、`suite/runs/` | 845 MB | 各引擎自建 venv；日志运行时生成 |
| `backend-c/build2/` | 16 MB | `scripts/build-engines.ps1`（cmake + MinGW） |
| `datasets/models/upstream/` | 239 MB | `datasets/tools/fetch_upstream.py`，`MANIFEST.json` 里有 sha256 |
| `datasets/map/render/` | 26 MB | 地图渲染管线产物（POI 预览图） |
| `release/` | 26 MB | `scripts/package-release.py --mode lite` / `--mode full` |
| `webui/` | 0.3 MB | 本机静态预览目录，不参与主链路（仍跟踪，体积可忽略） |
| `archive/release` | 1.23 GB | 0.4.1 整包的 11 个分片与合并脚本，**0.4.5 起已从磁盘删除**；要旧包直接用 Release 产物或重新打包 |
| `.cache/` | 296 MB | uv 包缓存，删了会自动重建 |
| `.tmp/` | 437 MB | 临时目录：上游压缩包、wiki 抓取缓存、本机探针 |
| `optional/`、`references/` | — | 可选的第三方材料，按需自行放置 |
| `runtime/` | 21 MB | 运行时状态：`rocoflow.db`、运行证据截图、SIFT 锚点缓存；删掉等于恢复出厂 |
| `logs/` | — | `start-all.ps1` 的启动表、PID 记录 |
| `*.zip`、`*.db-shm`、`*.db-wal` | — | 压缩包与 SQLite 边车文件 |

## 2.5 自构建矩阵（哪些能重取，靠什么重取）

判定不看体积看来源：**有公开源 + 能校验的才允许删**。

| 资产 | 最后核验 | 取回方式 | 入库? |
| --- | --- | --- | --- |
| 15 个上游仓（Adolph / BetterGI / NRC_AI / RocoPilot / AutoCapture / map-tracker / Interception …） | 可获取 | `fetch-upstream.ps1`（codeload tar.gz，按 commit 固定） | 否 |
| 模型权重 11 个（`datasets/models/upstream/*.pt|onnx|npz`，239 MB） | 10 个可获取、1 个本地独有 | `fetch_upstream.py weights`（sha256 在 `MANIFEST.json`） | 否 |
| BWIKI 战斗库 | 可重建（需连 wiki） | `fetch_bwiki.py` + `import_bwiki.py` | 否 |
| 社区 PvP 数据集 | 可重建（三个仓 + 固定提交） | `fetch_pvp.py` + `import_pvp.py` | 否 |
| 地图图标 / 文档截图 | 本机生成 | 图标抓取步骤 / `make-shots.mjs` | 否 |
| 前端 dist、C 核心、发行 zip | 构建产物 | `vite build` / `build-engines.ps1` / `package-release.py` | 否 |
| **SIFT-Map-Tracker v0.10.2 发布包** | **只有作者自建 zip** | **无公开源，只能保留** | **是（338 MB）** |
| SIFT 特征 npz / 两张底图 / `service.exe` | 同上（不可重算） | — | 是 |

机器可读版是 `scripts/assets/manifest.json`，现场核验：

```powershell
.\.venv\Scripts\python.exe scripts\trace-assets.py --check                        # 25 ok / 0 miss / 9 skipped
.\.venv\Scripts\python.exe scripts\trace-assets.py --report docs\reports\asset-trace.md
.\.venv\Scripts\python.exe scripts\trim-buildable.py                             # dry-run：又有什么能删了
```

**保守策略**：`trace-assets.py` 报 `miss` 或 `local-only` 的资产一律不删，宁可让仓库大 338 MB，
也不留下一份取不回来的东西。

## 3. 二进制例外（已入库，但请知悉）

只剩一个，且是上游 MIT 项目的自有发行物：

1. `backend/vendor/nrc_ai/data/nrc.db` — 1.2 MB，461 精灵 / 491 技能 / 206 进化链，图鉴与对战兜底；随 `NRC_AI`（MIT）原样分发，未修改。

「能重建的两个库」不再入库，重建链路都在仓库里：

```powershell
# 1) 重新抓模块源码（需要能连 wiki.biligame.com）
.\.venv\Scripts\python.exe datasets\tools\bwiki\fetch_bwiki.py --list datasets\bwiki\titles.txt

# 2) 解析 Lua 模块，重写 json + db
.\.venv\Scripts\python.exe datasets\tools\bwiki\import_bwiki.py
# → {"skills": 788, "pets": 596, "pet_skill": 29818, "evolutions": 242, "type_relations": 113}
```

导入脚本只做 `return { ... }` 的字面量解析，**不执行任何 Lua 代码**；重跑结果与曾入库的版本逐项一致（`fetched_at` 时间戳除外）。`datasets/bwiki/PROVENANCE.md` 保留来源链接与 CC BY-NC-SA 3.0 CN 声明。

PvP 数据集同理，重建链路在 `datasets/tools/pvp/`（按固定提交拉取，不登录、不抓私有接口）：

```powershell
.\.venv\Scripts\python.exe datasets\tools\pvp\fetch_pvp.py   # → datasets\pvp\.cache\
.\.venv\Scripts\python.exe datasets\tools\pvp\import_pvp.py  # → datasets\pvp\pvp_data.db + 摘要 JSON
```

## 4. 体积与许可

- 入库体积约 **371 MB**，组成：`archive/sift-map-tracker/` 338.1 MB（不可重取）、`datasets/`（去数据库、图标与缓存后仅工具与 POI JSON）13.2 MB、`vendor/` 剩 5.7 MB（少量不可追溯文件）、`frontend/src` 5.3 MB、`data/map/` 4.1 MB、`backend/` 2.1 MB、`suite/` 0.3 MB、`webui/` 0.3 MB、`scripts/` 0.1 MB；`git ls-files | wc -l` = **936**。
- 上游整树 `vendor/` 是**运行时子集**，不是完整 git 树；许可逐个记录在 `vendor/manifest.json`（16 个仓库，含 GPL-3.0 等），汇总见 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。GPL 组件只以子进程/数据形式使用，不静态链接进主程序。
- BWIKI 数据为 **CC BY-NC-SA 3.0 CN**：非商业、同协议共享、必须署名 —— 因此**不再随仓库分发**，只在本地按需重建。
- PvP 社区数据来自三个公开仓（RokePvP-Calculator / roco-cal / RoCo-PVP），仅用于本地平衡研究，来源与口径见 `datasets/pvp/PROVENANCE.md`；同样不入库。
- 游戏名称、界面、精灵、技能、地图与图标的知识产权归腾讯及相应权利人，本项目不做二次分发。
- 本仓库代码许可见 [LICENSE](../LICENSE)。

## 5. 发布前自检

```powershell
# 0) 资产还能不能取回来？哪些又可以被摘掉？
.\.venv\Scripts\python.exe scripts\trace-assets.py --check        # 25 ok / 0 miss / 9 skipped
.\.venv\Scripts\python.exe scripts\trim-buildable.py              # dry-run，确认没有新的可重取项被跟踪

# 1) 有没有引用到不入库的路径？（应只剩 docs 内的文字提及）
.\.venv\Scripts\python.exe -c "import re,pathlib; [print(m) for m in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', pathlib.Path('README.md').read_text(encoding='utf-8')) if not m.startswith(('http','#'))]"

# 2) 第三方数据/素材是否真的没被跟踪？
git ls-files -- datasets/bwiki datasets/pvp datasets/map/icons docs/screenshots
#   期望输出：只有 datasets/pvp/PROVENANCE.md（其余为空）

# 3) 干净环境能否跑通
.\.venv\Scripts\python.exe scripts\verify\api_smoke.py    # 38/38
cd backend; ..\.venv\Scripts\python.exe -m pytest tests -q # 65 passed, 1 skipped

# 4) 发行包里有没有夹带数据
python scripts\package-release.py --mode lite
python -c "import zipfile;z=zipfile.ZipFile('release/rocogi-'+open('VERSION').read().strip()+'-lite.zip');print([n for n in z.namelist() if n.endswith(('.db','.png')) and ('bwiki' in n or 'pvp' in n or 'screenshots' in n)])"
#   期望输出：[]
```
