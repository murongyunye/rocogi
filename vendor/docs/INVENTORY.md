# vendor 上游源码清单

- 生成时间：2026-11-05T16:16:06+08:00
- 仓库数：16；总体积：1.23 GB
- 比对口径：排除 `.git`、`__pycache__`、`.venv`，逐文件路径比对

| 仓库 | commit | 语言 | 许可证 | 文件数 | 体积 | 完整度 |
| --- | --- | --- | --- | --- | --- | --- |
| Adolph321-Adolph | `f215166` | JavaScript(2) | GPL-3.0 | 269 | 1.31 MB | complete |
| ColinHong10-NRC_AI | `9b5801b` | Python(45), Batch(1) | MIT | 478 | 180.04 MB | complete |
| ElliottZhao666666-rocom-codex-pets-gen | `4ccce56` | Python(10) | MIT | 22 | 0.75 MB | complete |
| Makapic-RocoPilot | `5f3f76e` | Python(40), Batch(3) | MIT | 70 | 61.19 MB | complete |
| Pacific-shark-roco-balance-lab | `52f717d` | JavaScript(22), Python(3) | MIT | 67 | 15.57 MB | complete |
| SCH-CMYK-game-automation | `4247f18` | Python(30), Batch(3) | CC BY-NC 4.0 | 48 | 3.62 MB | complete |
| Tsuann-RocoKingdom-AutoCapture | `4045c88` | Python(24), Shell(1), PowerShell(1) | 未声明（仓库无 LICENSE 文件） | 37 | 18.03 MB | complete |
| Wooziii-roco-map-tracker | `6890ac6` | Python(104), C#(11), Batch(1) | 未声明（README 声明第三方地图/图标权利保留） | 649 | 140.93 MB | complete |
| babalae-better-genshin-impact | `bcfacfb` | C#(1786), JavaScript(4) | GPL-3.0（子项目 Fischless.WindowsInput 为 MIT） | 3109 | 28.35 MB | complete |
| eachyczhang-RocoTools | `c983c8e` | JavaScript(82), Vue(53), Python(13) | CC BY-NC-SA 4.0 | 247 | 2.69 MB | complete |
| oblitum-Interception | `39eecbb` | C++(7), C(2), C/C++ header(2) | LGPL-3.0（非商用；商用需单独授权） | 44 | 0.12 MB | complete |
| rookie-orange-rocokingdom-ui | `2c8a1f6` | TypeScript/TSX(214), TypeScript(64) | 未声明（仓库无 LICENSE 文件） | 439 | 13.62 MB | complete |
| sift-map-tracker | `n/a` | Python(1) | 未声明（仅发布二进制，无 LICENSE 文件） | 213 | 617.62 MB | complete |
| yorusacri-Auto-rocokingdom | `a2589cd` | Python(29) | MIT | 50 | 0.65 MB | complete |
| yottaapp-yotta | `b835686` | Go(1019), TypeScript(375), Vue(156) | 自定义非商用许可（个人/教育/研究免费，商用禁止） | 1950 | 25.17 MB | complete |
| zh19990906-luoke_location | `5650fe6` | Python(23) | 未声明（README 要求遵守上游与原素材许可） | 1596 | 153.61 MB | complete |

## 入口与构建要求

### Adolph321-Adolph
- 入口：`battle-rules-1-200-20261007/battle-rules-1-200/verify.js`, `battle-rules-1-200-20261007/battle-rules-1-200/index.js`
- 构建：Node 22+（仅 verify.js）; 无编译产物

### ColinHong10-NRC_AI
- 入口：`start.py`, `run_web.py`, `src/main.py`, `src/server.py`
- 构建：Python 3.11+; fastapi/uvicorn/pandas/openpyxl; data/nrc.db（已随仓库）

### ElliottZhao666666-rocom-codex-pets-gen
- 入口：`scripts/validate_input.py`, `scripts/render_source.py`, `scripts/normalize_frames.py`
- 构建：Python 3.11+; Pillow>=11、imageio-ffmpeg; 外部资源目录 + rocom-pets 1.14.2

### Makapic-RocoPilot
- 入口：`main.py`, `config.py`
- 构建：Python 3.11+; opencv-python、numpy、mss、pygetwindow; ultralytics(torch) 可选; interception-python（缺驱动时回退 SendInput）

### Pacific-shark-roco-balance-lab
- 入口：`server.mjs`, `src/engine.mjs`, `scripts/experiment.mjs`
- 构建：Node >=22.12; pnpm（仅前端）

### SCH-CMYK-game-automation
- 入口：`main.py`, `run.bat`, `src/engine/controller.py`
- 构建：Python 3.11+; torch/torchvision/ultralytics/kornia; opencv-python、customtkinter、mss; interception-python + 驱动

### Tsuann-RocoKingdom-AutoCapture
- 入口：`main.py`, `config.yaml`, `models/sprite_detector.onnx`
- 构建：Python 3.11+; opencv-python、onnxruntime、PyYAML; RKNN 仅 RK3588 需要

### Wooziii-roco-map-tracker
- 入口：`roco-map-tracker/main.py`, `roco-map-tracker/service_main.py`, `roco-map-tracker/tracker/engines/sift_engine.py`
- 构建：Python 3.11+; opencv-python、numpy、mss、Pillow、PySide6、requests

### babalae-better-genshin-impact
- 入口：`BetterGenshinImpact.sln`, `BetterGenshinImpact/Program.cs`
- 构建：.NET 8 SDK; NuGet 联网还原; Windows 10/11 + WPF

### eachyczhang-RocoTools
- 入口：`app/server/src/index.js`, `app/client/src/main.js`, `crawler`
- 构建：Node 20+ / npm; better-sqlite3、sharp 预编译二进制; 实际图鉴数据（缺失）

### oblitum-Interception
- 入口：`library/interception.h`, `samples`
- 构建：MSVC 或 MinGW; WDK 签名 + 管理员安装内核驱动

### rookie-orange-rocokingdom-ui
- 入口：`package.json`, `packages/tokens/src/index.ts`, `packages/ui/src/index.ts`
- 构建：Node >=22.12; pnpm 11.5.3; vite-plus catalog 依赖

### sift-map-tracker
- 入口：`SiftMapTracker.Client.exe`, `sift-map-tracker/service/service.exe`, `sift-map-tracker/settings.py`
- 构建：Windows x64; 无构建（发布包已含 exe）

### yorusacri-Auto-rocokingdom
- 入口：`main.py`, `client_main.py`, `core/engine.py`
- 构建：Python 3.11+; opencv-python、numpy、mss、pygetwindow(pywin32)

### yottaapp-yotta
- 入口：`main.go`, `cmd/node-catalog/main.go`, `contracts/node/v2/builtin-catalog.json`, `frontend/package.json`
- 构建：Go 1.25（go.mod 声明）; Wails + WebView2; Node 22.12+ / npm

### zh19990906-luoke_location
- 入口：`main_sift.py`, `main_ai.py`, `data/points_data.json`
- 构建：Python 3.11+; opencv-python、numpy、PySide6; data 地图资源（已随仓库含 dist）
