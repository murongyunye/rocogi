# CHANGELOG

## 0.4.6 — 2026-11-08

> 精灵变体口径版本：按 pets-gen 的 `references/color-appearance.md` 把「模型形态」与「配色」拆成两条独立的轴。

### Added
- `backend/app/adapters/petvariant.py`：唯一实现九类配色判定（`normal` / `normal_glassy` / `normal_black_white` /
  `normal_seasonal` / `pollution` / `shiny` / `shiny_glassy` / `shiny_seasonal` / `shiny_black_white`），提供
  `classify(name, form)`、`split_form(name)`、`variant_summary(names)`；污染与异色互斥，冲突写 `notes`。
- `pvp_data.db` 的 `pet` 表新增配色轴八列（`form_raw` / `color_type` / `color_label` / `color_base` /
  `color_effect` / `season` / `is_shiny` / `is_polluted`），`meta` 增加 `variant_source`、`variant_note`、
  `variant_counts`；`datasets/pvp/PROVENANCE.md` 增加 pets-gen 来源行与九类配色表。
- `/api/pvp/dataset/pets/{name}` 返回 `variant`（配色轴）与 `siblings`（同族形态，最多 8 条）；
  `/api/pvp/dataset` 返回 `variantCounts / variantNote / variantSource`；`/api/dex/pokemon/{name}` 的
  `pokemon.variant` 同样带配色轴（camelCase，与 PvP 面板一致）。
- `/pvp` 数据面板：名字后显示配色 chip（异色品红、污染紫）、形态 chip、`S{n}` 赛季 chip，并列出同族形态可点跳转；
  `/dex` 详情抽屉同样显示配色 / 形态 / 赛季标签。
- `backend/tests/test_pet_variant.py`（9 个用例）与 `scripts/verify/api_smoke.py` 的两条新断言
  （`pvp variant axes`、`pvp variant summary`），冒烟从 38 项增至 **40 项**。

### Changed
- 导入脚本 `datasets/tools/pvp/import_pvp.py`：`build_pets()` 统一走 `classify`，重建前自动清掉旧库与
  `-journal/-wal/-shm`；配色型括号（「被污染的样子」）不再写成 `form`。
- `stage_tag` 只保留「首领」（67 只）：rokepvp 的 `st` 字段是形态标签，其余并入 `form`，修掉同一形态在
  「阶段」和「形态」两处重复显示的问题。
- `/api/dex/pokemon/{name}` 的 `variant` 字段名统一为 camelCase（首版误用 snake_case，前端读到 undefined 后
  渲染出空徽章）。

## 0.4.5 — 2026-11-08

> 自构建版本：先证明「哪些资产真的还能拿回来」，再把拿得回来的全部移出版本库；拿不回来的按保守策略留。

### Added
- `scripts/gen-asset-manifest.py`：从 `vendor/upstream_sources.json`、`datasets/models/upstream/MANIFEST.json`、
  `suite/assets/manifest.json` 汇总出 `scripts/assets/manifest.json`（34 条），每条标注 `kind`
  （`git-repo` / `repo-file` / `built-artifact` / `generated` / `local-only` / `rights-excluded`）与重建入口。
- `scripts/trace-assets.py`：`--check` 现场探测上游是否还在（git-repo 用 `codeload` tar.gz HEAD、repo-file 用
  `raw.githubusercontent` HEAD、构建产物校验重建脚本存在、本地独有直接跳过），`--fetch NAME|all` 按 manifest
  取回，`--report` 写 `docs/reports/asset-trace.md`。当前结果 **25 可获取 / 0 缺失 / 9 按策略排除或本地独有**。
- `scripts/report-tree-size.py`：按目录统计跟踪体积（`git ls-tree -r -l -z`，能处理带换行的文件名）。
- `scripts/trim-buildable.py`：dry-run 列出「可重取但仍被跟踪」的路径，`--apply` 执行 `git rm -r --cached`。

### Changed
- 版本库只留不可重取与自有源码：`git` 跟踪 **927 文件 / 371 MB**（其中 338 MB 是无公开源的
  `archive/sift-map-tracker/` 发布包），此前 7571 文件 / 1358 MB。
- `README.md` 的「体积与可选结构」整段重写：改成「版本库只留源码与取不回来的东西」，附三条自检命令、
  资产结论链接与新体积表；构建命令统一为 `package-release.py --mode lite|full`。
- `docs/PUBLISH_SCOPE.md` 新增 **§2.5 自构建矩阵**（8 行：能重取的资产 / 取回方式 / 是否入库），
  §4 体积口径改为 371 MB 并列出组成，§5 自检第 0 步改为跑 `trace-assets.py` 与 `trim-buildable.py`。

### Removed
- 从 index 摘除并删除磁盘副本：`archive/release`（0.4.1 整包 11 个分片，1781.7 MB）与 `release/`（118.9 MB）。
- 从 index 摘除（工作树保留，按需现取）：15 个可追溯上游仓（`vendor/` 6644 文件）、
  `datasets/bwiki/*.db|*.json|raw|wiki`、`datasets/pvp/pvp_data.db`、`datasets/map/icons/`、`docs/screenshots/`。

## 0.4.4 — 2026-11-08

> 合规整改版本：把「第三方游戏数据与美术素材」从版本库与发行包中彻底剥离，只保留导入脚本与出处说明。

### Removed
- 从版本库移除并加入 `.gitignore`：`datasets/bwiki/*.db|*.json|raw/|wiki/`（BWIKI 战斗库与模块源码）、
  `datasets/pvp/*.db`（社区 PvP 数据集）、`datasets/map/icons/` 与 `data/map/icons/`（109 张游戏物品图标）、
  `docs/screenshots/*.png`（13 张游戏内截图）。共 136 个数据/美术文件不再跟踪，工作树保留本地副本供本机运行。
- 同样移出版本库（可由脚本或本地构建重建）：`vendor/`（16 个上游仓库整树，6677 个文件，改用
  `vendor/tools/fetch-upstream.ps1` 按 `upstream_sources.json` 的提交拉回）、`archive/`（218）、
  `webui/`（18）、`release/`（1）。跟踪文件总数 **7653 → 534**。
- `scripts/package-release.py` 的 `SHIP_DATASETS` 只保留 `datasets/README.md`、两个 `PROVENANCE.md` 与
  `datasets/tools/{bwiki,pvp}/*.py`；lite 包不再含数据库，`_included_core` 无条件排除 `docs/screenshots/`、
  `data/map/icons/`、`suite/assets/map/`，`.db-shm`/`.db-wal` 一并跳过（lite 由 512 文件 42.3 MB 变为 423 文件 25.5 MB）。

### Changed
- `README.md`：删除 13 处截图引用，改为「截图本地生成」说明；来源表与体积表改为「数据库由脚本本地重建、不入库」。
- `docs/PUBLISH_SCOPE.md` 重写：新增「第三方数据既不进仓库也不进发行包」硬约束、自检第 2/4 步
  （`git ls-files` 与发包内容核对）、入库体积 55 MB → 20 MB。
- `docs/FIRST_RUN.md` 新增「1.5 重建第三方数据」：两条 fetch/import 命令 + 不重建时的兜底行为（回落到 `nrc.db`）。
- `datasets/README.md`、`THIRD_PARTY_NOTICES.md` 同步口径：图标与截图不再分发，署名与来源保留。
- `backend/app/adapters/pvpdata.py::resolve()` 增加 `available()` 守卫，数据库缺失时返回 `None` 而不是抛
  `sqlite3.OperationalError: unable to open database file`。
- 前端 PvP 数据面板新增「数据集未就绪」空态，提示重建命令（`available === false` 时优先展示）。
- `VERSION` / `suite.toml` / `backend.app.__version__` / `frontend/package.json` 升至 **0.4.4**。

## 0.4.3 — 2026-11-07

### Added
- PvP 社区数据集：新增 `datasets/tools/pvp/`（`fetch_pvp.py` 按固定提交拉取三个公开仓、`import_pvp.py`
  生成 `datasets/pvp/pvp_data.db`）与 `datasets/pvp/PROVENANCE.md`（来源、表结构、口径差异）。
  数据规模：674 精灵 / 608 技能 / 28,781 技能关联 / 221 特性 / 324 格属性矩阵 / 41,276 条使用率。
- 后端 `backend/app/adapters/pvpdata.py` 与四个接口：`/api/pvp/dataset`、
  `/api/pvp/dataset/pets/{name}`、`/api/pvp/dataset/usage`、`/api/pvp/dataset/skills`。
- 前端 PvP 页「数据面板」：点阵容里的精灵名展开六维条、特性效果、弱点/抗性、主流技能使用率、
  推荐技能/性格/个体、技能池威力前 8；插槽高亮当前查看的精灵。

### Changed
- 属性相克取「bwiki 113 对 ∪ rokepvp 进攻表」，bwiki 优先；8 条冲突（光→幽、地→冰、冰→地、龙→龙、
  萌→恶、幽→光、幽→幽、恶→萌）写入 `type_conflict` 表并在 PROVENANCE 说明。
- `VERSION` / `suite.toml` / `backend.app.__version__` / `frontend/package.json` 升至 **0.4.3**。
- README 补三个数据来源仓库、`/api/pvp/dataset*` 接口表、数据集体积行。

### Fixed
- `roco-cal` 特性名取顶层 key 导致 221 条全叫「特性」；改为读 body 的「名称」。
- 导入脚本三处：`pet` 表占位符数量、属性矩阵成员判断（字符串 vs `(atk,def)` 元组）、
  bwiki 对比处对三元组列表做 `dict()` 抛 `ValueError`。

## 0.4.2 — 2026-11-07

### Added
- 验证脚本入库 `scripts/verify/`：`api_smoke.py`（34 项接口冒烟）、`cdp-audit2.mjs`（16 路由 DOM 审计）、
  `ws_probe.py`（运行证据 WebSocket）、`realtime_probe.py`（捕捉状态机）、`make-shots.mjs` / `check-shots.mjs`
  （README 截图与断言）、`gen-engines-doc.py`（按后端注册表生成引擎文档）。
- 文档：`docs/FIRST_RUN.md`、`docs/windows-setup.md`、`docs/PUBLISH_SCOPE.md`、`docs/engines.md`、
  `docs/统一验证清单.md`（README 功能 → 入口 / 接口 / 实测证据 / 结论）。
- BWIKI 数据管线入库：`datasets/tools/bwiki/`（fetch / import / lua_literal）与
  `datasets/bwiki/wiki/` 六个 Lua 模块 + `titles.txt`，数据库从此可复现。
- 实时捕捉状态机参数进入设置：`capture_retries` / `capture_verify` / `capture_pan` /
  `capture_pan_steps` / `capture_pan_pixels`；模拟目标扩到 7 档场景（新增 `field` 空视野档）。
- 页面级热键 F9 / F10 / F11（输入框聚焦时跳过）与侧栏热键提示条。

### Changed
- 前端启动实时任务前先 `PUT /api/settings`，热键启动也读取本机配置，「本地优先」落到实际行为。
- 一条龙执行前重置模拟场景，演示可复现。
- `start-all.ps1` 增加 preflight：缺 `.venv` / Node / vite 时打印 MISSING 与修复命令并以退出码 2 结束；
  c-backend / webui 缺失时记为 MISSING 而不是静默中断。
- `VERSION` / `suite.toml` / `backend.app.__version__` / `frontend/package.json` 升至 **0.4.2**。

### Fixed
- PvP 阵容名解析：NRC 预设队的裸名（「千棘盔」）解析到 BWIKI 形态名（「千棘盔（本来的样子）」），
  首屏 `/api/pvp/analyze` 的两条 400 消失；前端插槽改用 `memberAt(index)` 而不是按名字匹配。
- 侧栏 16 个导航项没有图标、品牌标题被 `v-if` 吞掉（补 `icon` / `eyebrow` / `title` 布尔属性与紧凑样式），
  横向溢出 133px 归零。
- 模拟帧字体回退到 `ImageFont.load_default()`，HUD 中文不可读、回合数 OCR 恒为 `?`；
  改为 Windows 字体优先（msyh / msyhbd / simhei / arial）。
- `field` 场景原本也画精灵与交换图标，识别恒为 `field_pet`，空视野视角搜索分支不可达。
- 地图追踪「重建锚点」没有反馈：改为轮询 status，提示特征点数与耗时。
- 实时任务停止后计数器仍显示上一轮：加「上次会话」角标并压暗数值。
- `vite.config.ts` 的 watch 忽略编辑器临时目录，避免 dev server 因 EBUSY 崩溃。

### Docs
- README 补目录索引与体积表，本地链接 19 个全部可达。

## 0.4.1 — 2026-11-05

### Added
- **WebUI 进入发布包**：`webui/` 已加入 lite / full 的打包范围（0.4.0 的两个包实际未包含 webui），解压后即可在 `8800` 拉起前端。
- 前端 0.4.1 对齐：`/wapi/components` 按 `ready / not-wired / skipped / blocked-vendor` 四档直出 `components.toml` 真实状态（55 / 44 / 6 / 1 / 4）；`/wapi/vendor`（16 仓 + pets-gen partial + Interception 待重启）；`/wapi/release`（两包体积与 sha256）；总览 `versions` 分端口标注（8787 / 8788）；默认选中 `side-live5`。
- `start-all.ps1` / `stop-all.ps1`：重启后幂等拉起 8787/8788/5173/8800 与常驻 suite，只按 `logs/pids.json` 的 PID 精确停止。
- `game-data/` 真实数据接入管线：frames / templates / map / pets 规范化、sha256 去重、模板透明边裁剪与自匹配、地图分辨率判定与待标定提示、宠物资源 `validate_input.py` 校验。

### Changed
- `VERSION` / `suite.toml` / `backend.app.__version__` / `frontend/package.json` 升至 **0.4.1**；`/api/health` 与 harness/components 元数据同步返回 0.4.1。
- `webui/server.py` 的发布信息改为从根 `VERSION` 推导（`docs/verify-release-<version>.md` + `rocogi-<version>-*.zip`），不再硬编码 0.4.0。
- 打包脚本新增 `webui/`、`game-data/`、`start-all.ps1`、`stop-all.ps1`；排除 `webui/.cache`、`webui/scripts/probe_out`、`__pycache__`。
- 8788 C 核心版本仍为 0.2.0（未随套件升级，属已知限制）。

### Fixed
- 0.4.0 发布包遗漏 `webui/`，导致“解压后没有前端可拉”。

## 0.4.0 — 2026-11-05

### Added
- **vendor 全量源码导入**：16 个上游仓库整包进入 `vendor/`（1,324,626,890 B，逐文件 16/16 零缺失）；最终 **15 resolved / adapted、1 partial（pets-gen）、0 blocked**。
- 新引擎 `suite/engines/vendor`：`engine_main.py` 按真实适配器入口派发，不重复实现算法；`status`（含最新 resolution）/ 9 个 adapted action / `blocked`（仅 pets-gen）汇总，共 11 个去重 entry。
- 组件注册表从 39 增至 **55**：新增 16 条 vendor 组件，状态为 `ready` / `not-wired` / `blocked-vendor`（含原因），源码已导入的组件不再标 `skipped`。
- `THIRD_PARTY_NOTICES.md` 按 vendor 逐仓重写：许可证、个人非商业用途、0 补丁、适配层摘要、GPL/LGPL/CC 传染性边界、resolved 构建方式与产物、partial 说明。
- `suite/docs/MERGE_GAP.md` 第 4 节：原 7 个 blocked 项的缺什么、具体命令、代价、管理员/联网要求与最新 resolution。
- 发布脚本支持 `--mode both|lite|full`：`rocogi-0.4.0-lite.zip` 与 `rocogi-0.4.0-full.zip`（ZIP64，GB 级 vendor；含 sift 客户端/服务/assets 与补位路线）。

### Changed
- capture / vision / sift / battle / scheduler / input 引擎与 `suite/assets/build.py` 的上游路径全部从 `work/upstream` 切到 `vendor/`（单一源码基线；upstream 只读保留）。
- `engines --verify` 由 25 个入口扩展到 **36** 个入口；组件总数校验改为动态读取 `components.toml`。
- 前端探针新增：`/wapi/components` 必须看到 55 条组件与 vendor 分组；重启后 `/wapi/runs` 与 `/wapi/overview` 必须指到 `verify-restart` 且 manifest 含 vendor。
- `VERSION` / `suite.toml` 升至 0.4.0。

### Fixed
- `verify_round.py` 新增 `frontend-latest-run` 步骤；修复 frontend 异常分支的语法错误。
- Interception 驱动：17:34 CST 管理员安装器返回 0，`keyboard.sys` 已落盘，但服务仍 1060，**重启后才生效**；按要求不重启，运行时继续 SendInput 回退，状态保持 `blocked-vendor`。
- 吸收 `vendor/docs/BLOCKERS.md` 最终状态（18:30 CST）：yotta（Go 1.25.13 + Wails，`artifacts/yotta/yotta.exe`）、BetterGI（.NET 10 build，`artifacts/bettergi/`）、rocokingdom-ui（pnpm dist）、RocoTools（594/553/571 数据）、Interception（驱动已装待重启）为 resolved；sift-map-tracker 由 partial 转 resolved：补 `routes/default_route.json`（162 nodes / 161 edges）、region `{0,0,255,235}`，`probe_service.py` 实测 76 帧 / 74 `found=true`；仅 pets-gen 保持 partial，still-blocked=0。

## 0.3.0 — 2026-11-05

### Added
- `suite/`：六引擎整合运行时（capture / vision / input / sift / battle / scheduler），每引擎独立 venv、独立进程、独立 `requirements.lock`。
- 39 组件注册表 `suite/config/components.toml`：归属引擎、入口命令、配置路径、依赖、`status`、`implemented`、原因。
- `rocogi-suite` CLI：`run | call | engines | assets | evidence`；`engines --verify` 逐 entry 实跑（25 个去重入口）。
- 三条主链路：SIFT 定位、捕捉状态机、对战决策（均为结构化返回）。
- `scheduler flow`：branch / foreach / subgraph 真实执行；`scheduler events`：seq 连续的事件总线。
- `battle turn_state`：观测 → NRC `BattleState` schema（D 类重写缺口）。
- `scheduler onedragon_plan`：按 BetterGI 语义生成任务计划，运行时仍是 Rocogi DAG。
- 发布工件：`VERSION`、`CHANGELOG.md`、`scripts/package-release.py`（含 suite）、zip 发布包。

### Fixed
- `vision.sprite_detector` 缺 `pyyaml`（venv 无 pip，改用 `uv pip` 装入并落锁）。
- `scheduler.dag`：compile 前 `import app.nodes`；`source/target` → `from/to`；issues 非空返回 `failed`。
- manifest 引擎依赖改为 `uv pip freeze --python`（原 `python -m pip freeze` 在无 pip 的 venv 里恒为空）。
- `events.jsonl` 合并先读后写，不再截断 `supervisor.restart`；合入后按 ts 排序并补 `seq`。
- `restart_seconds` 改为"杀进程 → 到 ready"计时（用 perf_counter，避免系统时钟跳变），并接线 `startup_timeout_sec` / `restart_backoff_sec`。
- `assets/manifest.json` 绝对路径改为相对路径；`nrc.db` 只读 `immutable=1`，不再生成 `-wal/-shm`。
- MCTS 由 `battle.random_seed` 播种，重复调用结果一致。
- capture mock 帧尺寸读 `[frame]`（2560×1600），不再写死 1920×1080。
- 10 个"标 ready 无实现"组件：能接的补实现，接不了的改 `not-wired` 并写原因。
- `suite.toml` 恢复 `[paths]`（`evidence` 不带 `--run` 时不再 `KeyError`），套件版本对齐 0.3.0。

## 0.2.0

- 后端 DAG/适配层、前端工作台、打包脚本。
