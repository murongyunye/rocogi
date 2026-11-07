# Release verification · 0.4.0

- 时间：2026-11-05 19:10 CST
- 源码基线：`vendor/` 16 仓整包导入（1,324,626,890 B）；suite 0.4.0；7 引擎 / 55 组件 / 36 入口；vendor 最新状态 15 resolved / adapted、1 partial（pets-gen）、0 blocked
- 说明：两个 zip 均在本机重新解压到 `work/rocogi-verify/` 后验证。

## 包体

| 包 | 大小 | 文件数 | 内容 |
| --- | --- | --- | --- |
| `release/rocogi-0.4.0-lite.zip` | 约 17.5 MB | 530 | 自有代码 + suite + 文档；**不含 vendor** |
| `release/rocogi-0.4.0-full.zip` | 约 890.7 MB | 9,214 | lite + `vendor/` 源码/许可证/data + `artifacts/` 已构建入口 |

SHA-256 在打包完成后于 `release/` 目录单独计算并随发布说明给出（构建会改变包内文档，故不写回包内文档）。

两个包均为 ZIP64；full 包内大二进制（png/exe/npz/onnx/db 等）以 STORED 写入，源码用 DEFLATE。

## 解压后验证

| 检查 | lite | full |
| --- | --- | --- |
| `zipfile.extractall` | 530 文件 / 2.1s | 9,214 文件 / 48.4s |
| 包内 `__pycache__` / `.pyc` / `.venv` / `node_modules` / `.toolchain` / `*.orig` | 0 | 0 |
| 包内 `bin/Debug`、`bin/Release`、`obj/` | 0 | 0 |
| `python -m compileall suite backend` | exit 0 | exit 0 |
| `vendor/manifest.json` 仓库数 | n/a | 16 |
| 许可证文件（`vendor/*/LICENSE*`） | n/a | 10 |
| 适配器 `adapter.py` | n/a | 16 |
| sift 客户端 / 服务 / `assets/SIFT_features.npz` / 补位路线 | n/a | 全部存在（150.6 / 56.7 / 76.4 MB；162 nodes / 161 edges） |
| `vendor/docs/evidence/sift_route_probe.json`、`vendor/tools/post-reboot-check.ps1` | n/a | 存在 |
| `artifacts/yotta/yotta.exe`、`artifacts/bettergi/BetterGI.exe` | n/a | 存在（57.9 / 0.3 MB） |
| 解压后启动后端 `/api/health` | **200**，`version=0.4.0` | **200**，`version=0.4.0`；`interception=false`（待重启）、`sift=true` |

启动命令（验证时使用 8898/8899，避开常驻 8787/8788/5173/8800）：

```
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8899
```

## 常驻运行（终验后）

- `side-live5`（`--duration 0`）：7 引擎全部 running；`/wapi/overview` 的 `currentRun.run_id=side-live5`，run 详情 manifest 含 7 引擎与 55 个组件（vendor 16）。
- 8787 Python 后端已重启为 `version=0.4.0`；8788 C 后端、5173 Vite、8800 WebUI 均 200。
- 说明：8800 为只读适配层，只区分 `skipped` 与其余状态，`/wapi/components` 会把 `not-wired` / `blocked-vendor` 折叠为 `ready`（总数 55、vendor 16 正确）；组件状态的权威来源是 `suite/config/components.toml` 与 `rocogi-suite engines`。

## 结论

两个包都能解压、编译通过、后端可启动；full 包完整携带 vendor 源码、16 个适配器、许可证、sift 运行所需的客户端/服务/assets/补位路线、探测证据与 resolved 构建入口，未夹带缓存/venv/node_modules/.toolchain/`.orig`。lite 用于常规分发，full 用于 GPL/LGPL 与源码可获取要求。
