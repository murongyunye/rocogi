# Release verification · 0.4.1

- 时间：2026-11-05 20:12 CST
- 源码基线：suite 0.4.1；7 引擎 / 55 组件 / 36 入口；vendor 16 仓（15 resolved / adapted、1 partial pets-gen、0 blocked）
- 相对 0.4.0 的核心修正：**0.4.0 的两个包实际未包含 `webui/`**，0.4.1 已把 `webui/`（18 个文件）打入 lite / full，并把 `start-all.ps1`、`stop-all.ps1`、`game-data/` 一并纳入。
- 说明：两个 zip 均在本机重新解压后验证；SHA-256 在打包后于 `release/` 单独计算（构建会改变包内文档，故不写回包内文档）。

## 包体

| 包 | 大小 | 文件数 | SHA-256 | 内容 |
| --- | ---: | ---: | --- | --- |
| `release/rocogi-0.4.1-lite.zip` | 16.8 MB（17,641,940 B） | 558 | `A28DAA30B6F2ABEFD9AAEAE1B176A4A4890386D7E001380F0D7FA2D2671A936A` | 自有代码 + suite + webui + game-data + 拉起脚本 + 文档 |
| `release/rocogi-0.4.1-full.zip` | 890.8 MB（934,102,683 B） | 9,243 | `35831D62F440AE67F718A11A3B849A19F734F3F8138AF64A23E059FEC147CAC4` | lite + `vendor/` 源码/许可证/data + `artifacts/` 已构建入口 |

两个包均为 ZIP64；大二进制（png/exe/npz/onnx/db 等）以 STORED 写入，源码用 DEFLATE。两包内均无 `__pycache__` / `.pyc` / `.venv` / `node_modules` / `.toolchain` / `*.orig` / `webui/.cache` / `webui/scripts/probe_out`；`game-data/incoming/` 不入包（由 `import.py` 首次运行时创建）。

### 与 0.4.0 的差异

| 项 | 0.4.0 | 0.4.1 |
| --- | --- | --- |
| `webui/` | 包内 0 个文件（遗漏） | 18 个文件（`server.py`、`index.html`、`app.js`、`app.css`、`docs/`、`scripts/verify_round.py`） |
| 拉起脚本 | 无 | `start-all.ps1` / `stop-all.ps1` |
| 数据接入 | 无 | `game-data/`（`import.py`、`README.md`、`processed/` 清单） |
| `/wapi/release` 版本来源 | 硬编码 0.4.0 | 从根 `VERSION` 推导（`docs/verify-release-<version>.md` + `rocogi-<version>-*.zip`） |
| 版本号 | 0.4.0 | 0.4.1（`VERSION`、`suite.toml`、`backend.app.__version__`、`frontend/package.json`） |
| 文件数 | lite 530 / full 9,214 | lite 558 / full 9,243 |

## 解压与启动验证

| 检查 | lite | full |
| --- | --- | --- |
| `zipfile.extractall` | 558 文件 | 9,243 文件 |
| `python -m compileall suite backend webui game-data` | exit 0 | exit 0 |
| 包内 `webui/server.py`、`index.html`、`app.js` | 存在 | 存在 |
| `start-all.ps1` / `stop-all.ps1` | 存在 | 存在 |
| `game-data/import.py` + `README.md` | 存在 | 存在 |
| `vendor/manifest.json` 仓库数 | n/a | 16 |
| `vendor/*/LICENSE*` | n/a | 10 |
| 适配器 `adapter.py` | n/a | 16 |
| sift 客户端 / 服务 / `assets/SIFT_features.npz` / 补位路线 | n/a | 全部存在 |
| `artifacts/yotta/yotta.exe`、`artifacts/bettergi/BetterGI.exe` | n/a | 存在 |
| 解压后启动后端 `/api/health` | **200**，`version=0.4.1` | 由 lite 同一后端代码验证 |

## 前端 3 轮复验（解压后的 full 包，8800）

每轮 8 项：首页、四档组件计数、`/wapi/vendor`、`/wapi/release` 与实包比对、`versions`、默认选中、8787/8788 版本。

| 轮次 | 运行树 | 结论 | 四档计数 | `/wapi/release` | 版本 |
| --- | --- | --- | --- | --- | --- |
| 1 | 解压 full（`work/rocogi-verify-041`） | **8/8 PASS** | 55 / 44 / 6 / 1 / 4 | 2 包，字节与 sha256 与实包一致 | suite 0.4.1 / py 0.4.1 / c 0.2.0 |
| 2 | 同上 | **8/8 PASS** | 55 / 44 / 6 / 1 / 4 | 同上 | 同上 |
| 3 | 同上 | **8/8 PASS** | 55 / 44 / 6 / 1 / 4 | 同上 | 同上 |
| 4 | 源码树（含 `side-live5`） | **8/8 PASS** | 55 / 44 / 6 / 1 / 4 | 同上（0.4.0 包列为历史版本） | 同上；`currentRun=side-live5` |

复验脚本：`scripts/verify-release-041.py`（结果 JSON 在 `logs/verify-041-round*.json`）。复验前把 `release/` 的两个 0.4.1 zip 与本文档复制进解压树的 `release/`、`docs/`，用于模拟发布目录布局并让 `/wapi/release` 完整解析。

**venv 说明**：发布包按约定不携带引擎 `.venv`（约 790 MB）。新解压树在未准备 venv 时，`/wapi/components` 会把依赖 venv 的引擎判为 `not-wired`（实测 0 / 50 / 1 / 4）。按 `docs/FIRST_RUN.md` 准备 7 个引擎 venv（或从既有工作树复制 `suite/engines/*/.venv`）后即为 44 / 6 / 1 / 4；上表三轮均在准备好 venv 的解压树上执行。

## 已知限制（与 0.4.0 相同）

- 8788 C 核心版本仍为 `0.2.0`，未随套件升到 0.4.1。
- `vendor` 的 pets-gen 仍为 partial（`blocked-vendor` 1 项），Interception 需重启后生效。
- 8800 适配层只读上游，`runs/`、`logs/` 由套件 CLI 产生。

## 结论

0.4.1 两个包均可解压、编译通过（`compileall` exit 0）、后端 `/api/health` 返回 `version=0.4.1`；解压后的 full 包携带新 `webui/`，在 8800 拉起后四档组件计数为 55 / 44 / 6 / 1 / 4，`/wapi/vendor` 读到 16 仓 + pets-gen partial + Interception 待重启，`/wapi/release` 显示的两个 0.4.1 包的名称、字节与 sha256 与 `release/` 实包一致，`versions` 正确分端口标注 8787=0.4.1、8788=0.2.0；4 轮复验全部 8/8 PASS。0.4.0 两个包按历史版本保留在 `release/`。
