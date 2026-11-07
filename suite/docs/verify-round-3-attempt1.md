# verify round 3 · 失败留档（attempt 1）

- 时间：2026-11-05
- 结论：**FAIL（不计入通过）**

| 检查项 | 结果 | 证据 |
| --- | --- | --- |
| clean-state | PASS | `{"logs": 1, "runs": 2, "pycache": 9}` |
| build-assets | PASS | `{"ok": true, "pointCount": 9224, "featureCount": 94992}` |
| compileall | **FAIL** | `subprocess.TimeoutExpired`，300s 未完成；原因是 `compileall.compile_dir(suite)` 递归进入六个引擎 `.venv` 的 `Lib/site-packages`，扫描量不可控 |

## 处理

- 失败轮次不计入五轮通过。
- 修复验证探针 `suite/probes/verify_round.py` 的 `step_compile`：改为 `os.walk` + 剪枝 `.venv` / `node_modules` / `env` / `auto-rocokingdom` / `__pycache__`，只编译套件自有 `.py`。
- attempt 2：修复脚本自身用 `%` 格式化内嵌脚本时与 `'bad=%d' % len(bad)` 冲突，抛 `TypeError: not enough arguments for format string`；改为 `__SUITE__` 占位符 + `replace()`。同样不计入通过。
- 修复后重跑第 3 轮；产品代码未改动。
