# vendor/adapters

上游源码零改动的前置兼容层。每个适配器只做三件事：**路径重定向、配置注入、依赖降级/契约导出**，默认干跑（`--help` / `--json`），不启动游戏、不安装驱动、不写上游目录。

## 统一用法

```powershell
# 干跑（结构化 JSON，退出码 0=adapted，2=blocked）
& <venv>\Scripts\python.exe vendor\adapters\<name>\adapter.py --json
# 查看说明
& <venv>\Scripts\python.exe vendor\adapters\<name>\adapter.py --help
```

## 解释器分配（依赖不混装，按引擎独立 venv 复用）

| 适配器 | 解释器 | 原因 |
| --- | --- | --- |
| rocopilot / auto_rocokingdom | `suite/engines/capture/.venv` | 需 cv2 / numpy / mss / pywin32 |
| luoke_location / roco_map_tracker | `suite/engines/sift/.venv` | SIFTEngine 需 cv2 + numpy |
| autocapture / game_automation | `suite/engines/scheduler/.venv` | 需 PyYAML |
| pets_gen | `suite/engines/vision/.venv` | 需 Pillow |
| nrc_ai / adolph_rules / sift_map_tracker / interception / bettergi / yotta / rocokingdom_ui / rocotools / balance_lab | 便携 Python / Node | 纯标准库或子进程调用 Node |

## 适配器清单

| 适配器 | 上游 | 做了什么 |
| --- | --- | --- |
| `rocopilot` | Makapic-RocoPilot | config 路径重定向到 vendor；模板/模型清点；interception 缺失时声明 SendInput 回退 |
| `auto_rocokingdom` | yorusacri-Auto-rocokingdom | 窗口/截图/模板路径重定向；core 模块入口契约 |
| `luoke_location` | zh19990906-luoke_location | 桌面绝对小地图坐标 → 相对窗口 ROI + 1920×1080 归一化；尺寸预设可配 |
| `roco_map_tracker` | Wooziii-roco-map-tracker | 直接导入 SIFTEngine/route_planner；6144×5888 ↔ 8192×8192 三点仿射；发现 point.json 实为 HTML |
| `autocapture` | Tsuann-RocoKingdom-AutoCapture | Linux/RKNN 配置 → Windows mss + ONNX 注入；模型清点 |
| `game_automation` | SCH-CMYK-game-automation | MiningConfig 导入；分辨率/DPI 归一化；torch/interception 缺失降级 |
| `nrc_ai` | ColinHong10-NRC_AI | 只读打开 nrc.db，导出表结构与计数（461 宝可梦 / 491 技能 / 20433 关联） |
| `pets_gen` | rocom-codex-pets-gen | 脚本导入；澄清"有源码"，列出外部资源与渲染器缺口 |
| `adolph_rules` | Adolph321-Adolph | 调 Node 跑 verify.js；导出 200 宠物/200 技能/65 特性契约 |
| `sift_map_tracker` | sift-map-tracker | 校验 build-manifest 哈希；导出 settings 常量；判定"无运行时源码"并给出与 SIFTEngine 的替代关系 |
| `interception` | oblitum-Interception | 解析 interception.h 导出函数/枚举；驱动安装标记 blocked |
| `bettergi` | babalae-better-genshin-impact | 导出 GameCapture/Hotkey/WindowsInput 公开类型契约；构建标记 blocked |
| `yotta` | yottaapp-yotta | 导出 node-contract schema 与 189 个内置节点；构建标记 blocked（无 Go） |
| `rocokingdom_ui` | rookie-orange-rocokingdom-ui | 导出设计令牌（颜色/尺寸）与 214 个组件清单；构建标记 blocked（缺 pnpm） |
| `rocotools` | eachyczhang-RocoTools | 导出 REST 路由/18 张表 schema；图鉴数据缺口标记 blocked |
| `balance_lab` | Pacific-shark-roco-balance-lab | Node 直接 import 引擎，校验 6 角色/25 招式模拟数据集 |

## 坐标与尺寸铁律

- `6144×5888` 与 `8192×8192` 是**两套独立空间**，跨空间必须用 `_common/coords.py::calibrate` 输入 3 组物理对应点求解仿射，禁止只做缩放。
- 小地图尺寸 150×150 / 162×162 / 255×235 全部走 `MINIMAP_SIZES` 配置表，业务代码不得写死。
- DPI/分辨率差异用 `normalize_rect` 归一到 1920×1080 基准，再做坐标换算。

## 补丁政策

本层不修改 `vendor/<repo>/` 内任何文件；确需改源码时走 `vendor/patches/<repo>/*.diff` + `patches/apply.ps1`，并在 `docs/IMPORT_REPORT.md` 登记。
