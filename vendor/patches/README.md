# vendor/patches

本目录记录"必须改动上游源码"的补丁。当前阶段**没有任何补丁**：

- 所有兼容化都放在 `vendor/adapters/<name>/`，通过内存注入、路径重定向、子进程隔离实现；
- `vendor/<repo>/` 内文件与 `work/upstream/<repo>/` 逐字节一致，未做任何改写；
- 因此 `patches/` 为空，仅保留应用机制，便于后续必须改源码时有据可查。

## 约定

- 每个补丁放 `patches/<repo>/<序号>-<主题>.diff`，由 `git diff --no-index` 或 `git format-patch` 生成；
- 补丁只能应用到 `vendor/<repo>/`，**不得**用于 `work/upstream/`（上游只读）；
- 应用脚本：`patches/apply.ps1 -Repo <repo> -Diff <file>`；
- 应用后必须在 `vendor/docs/IMPORT_REPORT.md` 登记补丁文件名、原因、影响文件。

## 为什么现在是空目录

本轮目标是"整包导入 + 外部适配"，改上游文件会破坏可追溯性；凡是能用适配层解决的（路径、配置、坐标系、DPI、依赖降级），一律不改源码。
