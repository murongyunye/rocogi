# DEDUP_LOG · work 目录重复文件清理记录

执行时间：2026-11-06 02:10–02:35（Asia/Shanghai）
执行范围：`c:\Users\13005\Downloads\work`
判定标准：**只看文件内容 SHA-256 是否相同，不看文件名**。

---

## 1. 扫描口径

### 1.1 纳入扫描

`work\` 全树（含 `rocogi\`、`.publish-tmp\`、`.screenshots\`）。

### 1.2 排除项（按要求 + 安全考虑）

| 排除项 | 原因 |
| --- | --- |
| `**\.toolchain\**` | 便携工具链，不参与去重 |
| `**\vendor\**` | 只读区（本会话禁止修改/删除）；**但仍参与哈希计算**，用来判定其他位置的副本是否与 vendor 内容一致 |
| `**\node_modules\**`、`**\.venv\**`（含 `suite\engines\*\*.venv`） | 依赖环境 |
| `**\__pycache__\**`、`**\*.pyc` | 字节码缓存 |
| `rocogi\release\*.zip` | 发布包 |
| `**\.git\**` | 版本库元数据（同时避免误删正在被另一会话推送到 GitHub 的仓库状态） |
| `work\_publish_tmp\` | 另一会话正在执行 GitHub 推送的工作目录，任务未授权，全程未读写改动 |

### 1.3 规模

- 参与扫描：24,392 个文件 / 4,183,652,922 B（约 3.90 GiB）
- 参与哈希：22,197 个（只有体积出现碰撞的文件才需要算哈希）
- 重复组：8,924 组，理论可释放 1,683,980,286 B

---

## 2. 引用核查

核查位置：`rocogi\suite\`、`rocogi\webui\`、`rocogi\backend\`、`rocogi\frontend\`、`rocogi\docs\`、`rocogi\game-data\`、`rocogi\*.ps1`。

| 待删对象 | 引用位置 | 处理 |
| --- | --- | --- |
| `rocogi\upstream\`（整份镜像） | `suite\config\engines\sift.toml:13` `engine_repo = "../../upstream/Wooziii-roco-map-tracker/roco-map-tracker"` | **已改指**为 `../vendor/Wooziii-roco-map-tracker/roco-map-tracker`，改后实测解析到 `rocogi\vendor\...`，`config.json` 存在 |
| 同上 | `suite\docs\MERGE_GAP.md:3-4` 引用 `work\upstream\MERGE_MAP.md` / `INVENTORY.md` | 已改指到 `docs/upstream-snapshot/` 下的保留副本，并注明 upstream 镜像已移除 |
| 同上 | `docs\MERGE_LOG.md`、`docs\PUBLISH_SCOPE.md`、`CHANGELOG.md`、`THIRD_PARTY_NOTICES.md`、`suite\docs\cleanup-manifest.md` | 仅历史叙述（"upstream 如何被保留/为何不入仓"），非可执行路径，按历史记录原样保留 |
| 同上 | `suite\assets\build.py:26` 的 `UPSTREAM` 变量 | 值为 `os.path.join(ROCogi, "vendor")`，指向 vendor，无需改动 |

> 附带发现（未擅改）：`suite\config\suite.toml:12-13` 的 `[runtime].python` / `.uv` 仍写 `../../.toolchain/...`，解析到 `work\.toolchain`（合并到 `rocogi` 后已不存在）。该字段不被 `suite\kernel\cli.py` 用于拉起引擎（引擎用各自 `.venv`），属惰性元数据，本次未修改，仅在此记录。

---

## 3. 已执行删除

### 3.1 `rocogi\upstream\`（整份删除）

| 项 | 值 |
| --- | --- |
| 绝对路径 | `c:\Users\13005\Downloads\work\rocogi\upstream` |
| 删除前 | 9,880 个文件 / 1,843,559,846 B（1.717 GiB） |
| 内容核验 | 除 `.git`/`*.pyc` 外的 9,290 个文件中，**9,270 个与 `vendor\` 对应文件 SHA-256 完全相同** |
| 未命中 20 个 | 14 个为 0 字节空文件（`.gitkeep`、空 `__init__.py` 等，vendor 侧同样是 0 字节空文件）；6 个为下文保留的独有文档/差异文件 |
| 引用处置 | 见第 2 节，唯一功能性引用已改指到 `vendor` 并验证可用 |
| 版本库影响 | `upstream\` 在 `rocogi` 中从未被 git 跟踪（`git ls-files upstream` 计数为 0），删除不产生 git 删除记录，不影响正在进行的推送 |
| 回收站 | 11,285 项进入回收站，**需手动清空回收站后才真正释放磁盘** |

### 3.2 为删除 upstream 而事先保留的文件（新增，共 6 个 / 99,764 B）

路径：`c:\Users\13005\Downloads\work\rocogi\docs\upstream-snapshot\`

| 文件 | 体积 | 保留理由 |
| --- | ---: | --- |
| `MERGE_MAP.md` | 29,122 B | `suite\docs\MERGE_GAP.md` 直接引用；vendor 内无同名副本 |
| `INVENTORY.md` | 23,183 B | 同上；`vendor\docs\INVENTORY.md`（5,523 B）是另一份重写版，内容不同 |
| `rookie-orange-rocokingdom-ui\AGENTS.md` | 1,072 B | 与 vendor 版本哈希不同（1,057 B），属上游原文，避免丢失 |
| `rookie-orange-rocokingdom-ui\apps\website\src\route-tree.gen.ts` | 31,184 B | 同上（vendor 版 30,428 B） |
| `yottaapp-yotta\frontend\auto-imports.d.ts` | 2,962 B | 同上（vendor 版 1,942 B） |
| `yottaapp-yotta\frontend\components.d.ts` | 12,241 B | 同上（vendor 版 10,269 B） |

保留动作已完成逐文件 SHA-256 复验：6/6 与 upstream 原件一致（保留侧可用性确认）。

---

## 4. 保留未删（看着像重复但不动）

| 对象 | 规模 | 原因 |
| --- | ---: | --- |
| `vendor\` 内部重复（如 `BetterGI\bin\Release\*\BetterGI.dll` 与 `obj\Release\*\BetterGI.dll`） | 1,330 组 / 66.06 MB 可释放 | `vendor` 为只读区，本会话禁止删除 |
| `suite\assets\` 与 `vendor\` 的大型二进制重复（`big_map.png`、`display_map.png`、`logic_map.png`、`sprite_detector.onnx`、`SIFT_features*.npz` 等） | 6 组 / 270.44 MB 可释放 | `suite\assets` 是运行时直接读取的资源，`vendor` 不可删，两边都必须留 |
| `data\` ↔ `suite\assets\` 的地图图标/模板/底图 | 46 组 + 3 组 / 约 2.7 MB | 两侧分别被 Python 后端与 suite 引擎读取，属两份独立组件的资产，删任一侧都会破坏其中一方 |
| `backend-c\build\` ↔ `backend-c\build2\` 的 CMake 中间产物 | 45 组 / 0.73 MB | `start-all.ps1` 使用 `build2\rocogi-core.exe`；`build\` 虽未被引用，但属构建产物清理范畴而非内容重复，本次不扩大范围 |
| `frontend\dist\` ↔ `frontend\public\` 的品牌图/favicon | 4 组 / 0.25 MB | `dist\` 被 `scripts\setup-windows.ps1`、`build-rocogi-windows.ps1`、`deploy_local.py`、`run.sh` 显式引用，删了会断构建 |
| `suite\probes\*\requirements.lock`、`suite\probes\interception` 内 DLL | 2 组 | 探针目录自用，体积可忽略 |
| `work\.publish-tmp\` | 1,345 个文件 / 24,226,029 B | 内容为 GitHub 发布流程的暂存块（`blocks*.json`、`prepare*.py`、两个上游仓副本）。**另一会话正在推送 rocogi 到 GitHub**，无法确认其是否仍被读取，按"不确定一律保留"处理 |
| `work\_publish_tmp\` | 5 个文件 / 155,021 B | 另一会话当前活动目录（`pending.json`、`batch.txt` 等），任务未授权，未触碰 |
| `work\.screenshots\` | 0 个文件（仅一个空的 `.tmp` 子目录） | 只读核验确认全空；删除不释放任何空间，且可能被截图流程复用，保留 |

> 说明：全库仍有约 342.75 MB 的重复内容，全部落在"只读区"或"两侧都在使用"的组合里，按约束一律不删。

---

## 5. 释放体积

| 项 | 字节 | 换算 |
| --- | ---: | --- |
| 已删除 `rocogi\upstream\` | 1,843,559,846 | 1.717 GiB / 1.844 GB |
| 新增 `docs\upstream-snapshot\` | +99,764 | 约 +97 KiB |
| **净释放** | **1,843,460,082** | **约 1.717 GiB / 1.843 GB** |

注意：文件当前位于**回收站**，物理磁盘空间要在手动清空回收站后才归还。

---

## 6. 删除后健康检查（只读，未停止任何服务）

删除前后均未重启/停止服务，仅做 `Invoke-WebRequest` 探测：

| 端口 | 服务 | 结果 |
| --- | --- | --- |
| 8787 | Python 后端（uvicorn） | HTTP 200 |
| 8788 | C 核心（rocogi-core.exe） | HTTP 200 |
| 5173 | Vite 前端 | HTTP 200 |
| 8800 | WebUI | HTTP 200 |

`sift.toml` 改指后复验：`engine_repo` 解析为 `c:\Users\13005\Downloads\work\rocogi\vendor\Wooziii-roco-map-tracker\roco-map-tracker`，目录与 `config.json` 均存在。

---

## 7. 未执行项

- `work\.screenshots`：确认为空目录，删除无收益，保留。
- `backend-c\build\`：未被引用的旧构建树，属构建产物清理，非本任务范围。
- 回收站清空：需人工操作。
