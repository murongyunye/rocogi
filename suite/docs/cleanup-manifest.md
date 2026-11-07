# 清理清单（cleanup-manifest）

- 生成时间：2026-11-05
- 范围：仅 `work\` 内部；**不触碰** `work\upstream\` 与 `work\rocogi\webui\`（另一会话专属）
- 原则：先列清单 → 再执行；不清理回收站（系统限制，交由用户自行处理）

## 已执行删除

| # | 路径 | 体积 | 原因 |
| --- | --- | --- | --- |
| 1 | `work\.tmp\` | 0 MB / 10 文件 | 临时目录 |
| 2 | `work\_diag\` | 0.3 MB / 87 文件 | 上一轮只读体检的诊断输出，结论已写入 docs |
| 3 | `work\templates\` | 空 | 空目录，模板资产已归入 `suite/assets` 与 `rocogi\data` |
| 4 | `work\.screenshots\` | 空 | 空目录 |
| 5 | `work\rocogi\suite\probes\auto-rocokingdom\` | 184 MB / 2503 文件 | S0 阶段试验用副本（含独立 env），被 `suite/engines/vision` + `capture` 取代 |
| 6 | `work\rocogi\suite\logs\` | 生成物 | 每轮运行日志；结论已固化到 `docs/verify-round-N.md` |
| 7 | `work\rocogi\suite\runs\` | 生成物 | 运行证据（manifest/events/metrics）；结论已固化到 docs |
| 8 | `work\rocogi\captures\` | 8.1 MB / 39 文件 | 历史运行截图证据 |
| 9 | `work\rocogi\runtime\` | 0.1 MB / 1 文件 | 保留：`runtime/rocoflow.db` 是 8787/8788 后端正在使用的工作流库，删掉会影响在线服务 |
| 10 | `work\rocogi\**\__pycache__\` | 生成物 | 字节码缓存（排除 `webui`、`.venv`、`node_modules`） |
| 11 | `work\rocogi\suite\logs-round*.txt` | 草稿 | 本地跑批的中间输出，结论已进 docs |
| 12 | `work\rocogi\suite\probes\{autocapture,luoke-location,roco-map-tracker,rocopilot}\env\` | 764 MB / 约 9500 文件 | S0 阶段每个上游单独建的试验 venv，已被 6 个正式引擎替代 |
| 13 | `work\rocogi\suite\probes\interception\Interception.zip` 解压源 | 0.4 MB | 保留解压后的安装器供人工提权安装，zip 可删（本轮保留以便复用） |
| 14 | `work\rocogi\suite\runs\side-live`、`suite\logs\side-live` | 0.1 MB | 同名 run 被重复启动后终止的残留（仅 manifest，无有效证据）；有效常驻证据保留在 `side-live3` |
| 15 | `work\_relcheck-1541` | 16.9 MB | 发布包解压校验临时目录（已完成后端 8799 健康检查），校验完毕即删 |

## 保留（明确不清理）

| 路径 | 原因 |
| --- | --- |
| `work\upstream\` | 只读参考源，禁止改动 |
| `work\rocogi\webui\` | 另一会话专属 |
| `work\.toolchain\` | 便携 uv / python / git，全部脚本依赖 |
| `work\rocogi\.venv`、`work\rocogi\.toolchain` | 8787/8788 后端运行时 |
| `work\rocogi\frontend\node_modules` | 5173 前端运行时 |
| `work\rocogi\suite\assets`、`suite\config`、`suite\engines` | 套件本体 |
| `work\rocogi\docs`、`packaging`、`scripts` | 发布与文档资产 |
| `work\rocogi\data` | 地图/模板/点位等产品数据（4.1 MB） |
