# work → rocogi 合并记录

- 时间：2026-11-05 21:00 CST
- 目标：`C:\Users\13005\Downloads\work` 下除 `rocogi` 外的内容全部并入 `rocogi`；旧验证产物留到阶段 4 删除。

## 决策与结果

| work 顶层项 | 来源 | 去向 / 处理 | 文件数 | 体积 | 校验方式 |
| --- | --- | --- | ---: | ---: | --- |
| `rocogi` | 自身 | 保留（目标目录） | 221,881 | 16.5 GB | n/a |
| `.toolchain` | 独立工具链 | 与 `rocogi\.toolchain` 去重后删除 | 24,094 | 1,289.5 MB | 逐文件路径+大小比对；见下 |
| `upstream` | 16 仓上游源码 | 移动 → `rocogi\upstream`（整份保留） | 9,878 | 1,758.7 MB | 与 `vendor` 逐文件 sha256 比对 |
| `Rocogi本地部署须知.md` | 部署说明 | 移动 → `rocogi\docs\notes\` | 1 | 约 30 KB | 文件存在性 |
| `rogogi本地部署路线.txt` | 路线笔记 | 移动 → `rocogi\docs\notes\` | 1 | 约 30 KB | 文件存在性 |
| `.screenshots` | 空目录（仅 `.tmp`） | 删除 | 0 | 0 | 空目录确认 |
| `rocogi-verify` | 0.4.0 解压验证树 | 留在 work，阶段 4 删除 | 9,214 | 1,034 MB | n/a |
| `rocogi-verify2` | 0.4.0 二次验证树 | 留在 work，阶段 4 删除 | 9,214 | 1,034 MB | n/a |
| `rocogi-verify-041` | 0.4.1 解压验证树（含复验用 venv 副本） | 留在 work，阶段 4 删除 | 约 18,000 | 2,677 MB | n/a |
| `rocogi-verify-041-lite` | 0.4.1 lite 解压树 | 留在 work，阶段 4 删除 | 558 | 25.6 MB | n/a |
| `rocogi-suite` / `_diag` / `logs` / `runs` / 旧 zip | 不存在 | 无需处理 | – | – | 盘点确认 |

## `.toolchain` 去重细节

同名子目录逐文件比对（相对路径 + 文件大小）：

| 子目录 | 相同 | 缺失 | 大小不同 | 结论 |
| --- | ---: | ---: | ---: | --- |
| cmake | 8,817 | 0 | 0 | 完全一致 |
| gh | 2 | 0 | 0 | 完全一致 |
| git | 375 | 0 | 0 | 完全一致 |
| node | 2,032 | 0 | 0 | 完全一致 |
| python | 3,388 | 8 | 16 | 差异全部是 `Lib\__pycache__\*.pyc`（0.1 MB），无源码/库缺失 |
| uv | 3 | 0 | 0 | 完全一致 |
| w64devkit | 9,451 | 0 | 0 | 完全一致 |

- `downloads\`（117.5 MB 安装包缓存）与 `cmake-tmp\` 未并入（缓存，可按记录重新下载）。
- 删除前先停止了 38 个依赖 `work\.toolchain` 的进程（suite 常驻 run、6 引擎、8787 uvicorn、8800 webui、5173 vite）。
- 9 个 venv 的 `pyvenv.cfg` 已把 `home` / `executable` / `base-prefix` 从 `work\.toolchain` 改为 `rocogi\.toolchain`：`rocogi\.venv`、7 个引擎 venv、`.toolchain\venv-crawler`。
- 删除后实测：`.venv` 可 `import fastapi 0.162.0`；sift venv 可 `import cv2 4.14.0`；`rocogi\.toolchain` python 3.12.16 正常。

## `upstream` 与 `vendor` 哈希比对

- 相同文件 **9,283**；仅上游有 **550**；大小/内容不同 **45**。
- 550 个“仅上游有”全部是 `.git` 内部文件（33 个/仓，含 hooks 样本、index、packed-refs）及 `__pycache__/*.pyc`；排除 `.git`、`__pycache__`、`.pyc` 后，**缺失 = 0**。
- 45 个差异全部是 `__pycache__/*.pyc`；唯一非 pyc 差异位于 `sift-map-tracker` 的 1 个文件（适配后的配置/补位路线），符合预期。
- 结论：`vendor` 已包含上游全部有效源码，`upstream` 按默认策略整份保留在 `rocogi\upstream`。

## 合并后路径修正

| 文件 | 修改 |
| --- | --- |
| `start-all.ps1` | `.toolchain` 路径由 `$Work`（父目录）改为 `$Root` |
| `webui/server.py` | `PYTHON` 改为 `<ROOT>/.toolchain/...` |
| `suite/probes/verify_round.py` | `PY` / `UV` 改为 `<ROOT>/.toolchain/...` |
| `docs/FIRST_RUN.md` | 路径改为 `rocogi\.toolchain` |
| `webui/README.md` | 两条示例命令路径改为 `rocogi\.toolchain` |
| 9 个 `pyvenv.cfg` | `home` 指向 `rocogi\.toolchain\python\cpython-3.12.16-...` |

## 失败与回滚

- `.toolchain` 首次递归删除时 `python\cpython-3.12-windows-x86_64-none` 被瞬时占用，其余 25,374 项已删除；3 秒后重试成功，未产生半删状态。
- 其余移动均为同卷 rename，无失败。
