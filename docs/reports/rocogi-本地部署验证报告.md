# rocogi 本地部署验证报告

- **日期**：2026-11-06
- **部署根**：`C:\Users\13005\Downloads\work\rocogi`（引擎硬编码 `<WORK>\rocogi\vendor` 相对根，根目录名必须为 rocogi）
- **上游**：murongyunyeh/rocogi main 分支（镜像 290 个第一方文件 + vendor 6646/6677 文件）+ archive/release/rocogi-0.4.1-full.zip（11 卷 844MB，sha256 MATCH）重资产抽取
- **结论**：**verify_round round 1 全绿（11/11 PASS）**，四端口服务全 200，P0 静态扫描通过（1 条良性备注）

## 1. 环境与工具链
| 组件 | 版本 | 偏差说明 |
|---|---|---|
| Python | 3.12.14（python-build-standalone，捆绑拷贝到钉版路径 `cpython-3.12.16-windows-x86_64-none\python.exe`） | patch 版本偏差（16→14），上游钉 3.12.16 的 release 下载 404/504；同源构建，运行无碍 |
| uv | 0.13.7（GitHub latest） | 无偏差 |
| Node | v24.21.0（捆绑拷贝到 `.toolchain\node`） | 无版本钉定要求 |
| GCC | MinGW-W64 x86_64-ucrt-posix gcc 16.2.0（WinLibs r3，便携 zip） | **本机无任何编译器**，verify_round 硬性要求 8788 C-core → 拉便携工具链编译，非产品偏差 |

环境变量（运行 suite 必需，沙盒/本地化所致）：
- `UV_CACHE_DIR=<root>\.cache\uv`、`UV_PYTHON_INSTALL_DIR=<root>\.cache\uv-python`（uv 默认 AppData 被沙盒拒，os error 5）
- `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`（cp936 解码炸弹，见 §4）

## 2. 服务与探针（verify_round round 1，11/11 PASS）
```
[PASS] clean-state / build-assets(9224 points/94992 features) / compileall(bad=0) / assets-verify(hashes 10/0, canonicalMap=true)
[PASS] engines-verify 36/36（55 组件 ready=44/notWired=6/skipped=1/blockedVendor=4）
[PASS] requirements-lock 7/7 match（capture 3 / vision 7 / input 4 / sift 3 / battle 14 / scheduler 19 / vendor stdlib-only）
[PASS] three-chains（sift locate / capture capture / battle responder 全 ok）
[PASS] frontend-probes 8787=200 8788=200 8800=200 5173=200（statsTotal 55==components.toml，vendor 组 16 组件可见）
[PASS] supervisor-restart 0.863s（kill vision 自动重启，seq 连续、时间戳单调）
[PASS] frontend-latest-run（WebUI 可见 verify-restart 运行与 vendor 组件）
```

文档：`suite\docs\verify-round-1.md`。服务：backend uvicorn 8787 / **C-core（自编译）8788** / webui 8800 / vite 5173。

### backend 单测
**64 passed / 2 skipped / 3 failed**——3 个失败全为 OCR 用例，定性为**文档化偏差，不改产品代码**：
- CI（ubuntu）的 builtin OCR 模板用 DejaVuSans-Bold，Windows 命中 `arialbd.ttf`；测试 mock 用 cv2.putText Hershey 字形，arial 模板最佳分 0.375 < min_confidence 0.45 → text=''。
- 曾试装 tesseract 5.4.0 + pytesseract：`_tesseract` 对 stylized 字体读出的乱码硬标 confidence=1.0 抢答，反而更糟 → 已卸载恢复 CI 等价环境。
- 建议后续（产品侧）：给 `backend/app/adapters/ocr.py` 加 Hershey 模板 fallback。

### 引擎构建
- 7 个引擎 venv（uv 建）+ requirements.lock 回填（仓库未发货 lock，MERGE_GAP 已承诺）。
- vision/scheduler 补 pyyaml、sift 补 pillow（assets/verify.py 需要）。
- vision sprite_detector：onnxruntime 实跑 640x640 推理（mock 帧 0 detections，正常）。
- interception 键盘驱动未装：input 引擎 3 条目中相关项 skipped（合理降级，sendinput 路径可用）。

## 3. C-core 编译（8788）
- 源码 `backend-c/src`（16 个 .c）+ stb_image 第三方；MinGW gcc 直接编译（未走 cmake，等价命令行）：
  `gcc -std=c11 -O2 -I third_party src\*.c(16个) -o build2\rocogi-core.exe -lws2_32 -ld3d11 -ldxgi -luuid -lole32 -luser32 -lgdi32 -static`
- 产物 792KB，仅无害 warning（stb 未用函数、strncpy 截断告警）。
- `/api/health` → `{"ok":true,"engine":"c","version":"0.2.0"}`。
- 注：release v0.2.0 的 rocogi-core-0.2.0.zip 是源码快照而非预编译二进制，故本地编译。

## 4. 修复的产品 bug（1 处，最小补丁）
**`vendor/adapters/balance_lab/adapter.py:40-41`**：node 子进程输出为 UTF-8（data_version 含 0xac 等非 cp936 序列），`subprocess.run(text=True)` 在 Windows 默认 cp936 解码 → `_readerthread` UnicodeDecodeError → stdout/stderr 返回 None → `(proc.stderr or proc.stdout).strip()` AttributeError，engine_import 检查崩溃。
修法：`subprocess.run(..., encoding="utf-8", errors="replace")` + `or ""` 兜底，附注释。补丁后 36/36 全过。
同族隐患（未改，报告在案）：`verify_round.py` 内部 subprocess 与其余 adapter 的 `text=True` 同模式；CI（UTF-8 locale）不触发，仅 Windows 本地化环境触发。**部署面通过环境变量 PYTHONUTF8=1 规避，未改这些文件。**

## 5. P0 静态扫描（禁游戏内存读写）
模式：`pymem / ReadProcessMemory / WriteProcessMemory / OpenProcess / PROCESS_VM_* / Nt[Read|Write]VirtualMemory`，扫描第一方运行面（backend/ suite/ webui/ scripts/ backend-c/src+tools/ frontend/src），排除虚拟环境/工具链/缓存/资产。

- **判定：PASS**。唯一命中：`webui/server.py:138` `OpenProcess(0x1000, False, pid)`——**PROCESS_QUERY_LIMITED_INFORMATION 纯查询**（pid_alive 判断引擎进程存活），无 VM_READ/VM_WRITE 权限，目标为 rocogi 自身引擎进程而非游戏，不构成内存访问。
- vendor/ 第三方仓库按设计单列（多含 pymem 类代码，但 suite 只以 import 检查/适配器干跑方式使用，不在 P0 运行面）。
- 扫描脚本：`.tmp/p0_scan.py`（可复跑）。

## 6. 已知偏差与遗留清单
1. **Python patch 版本** 3.12.14 vs 钉定 3.12.16（上游 release 不可达，捆绑拷贝替代）。
2. **vendor 镜像 31/6677 失败**：文件名含 Windows 非法字符（`?` 等，sift-map-tracker legacy-json/resources），Windows 文件系统无法存放，无解；均为非运行必需资产。
3. **OCR 3 测试失败**：Windows 字体模板偏差（§2，文档化）。
4. **balance_lab 补丁**：1 处最小产品补丁（§4）。
5. **环境变量**：UV_CACHE_DIR / PYTHONUTF8 必须（沙盒 + cp936）。
6. **mkdir DACL bug**：本份 python-build-standalone 的 `os.mkdir(mode=0o700)` 在 Windows 造受保护 DACL → `.venv\Lib\site-packages\sitecustomize.py` 猴补丁抹 mode（pytest tmp 工厂硬编码 0o700）。
7. **待办**：真截图（`suite/config/capture.toml` `enable_real_capture=false` 待开）+ suite 实机跑测，**等用户玩完游戏通知后进行**。

## 7. 实机测试（2026-11-06，用户授权后）
游戏：《洛克王国：世界》运行中，窗口 hwnd=789686，标题 `洛克王国：世界  `（尾随空格，keyword 匹配 OK）。**全程零内存访问**（PrintWindow/BitBlt 窗口层 + SendInput 虚拟键鼠，单次受控）。

1. **真截图**：`enable_real_capture=true` 后 `capture --once` → backend=printwindow（PrintWindow 失败自动回退 BitBlt，vendor 预期路径），帧 1280×800 非黑（均值亮度 225-235，采样 1736 色）。PNG 证据：`.tmp/real_frame.png`。
2. **真帧 vision**：9 模板加载，scale 0.5/1.0 matchTemplate 正常（非战斗画面最高分 0.23<0.40=正确判定非战斗）；ONNX 精灵检测 0 命中（画面无精灵，合理）。
3. **输入 critical 修复 + 实测**：`suite/engines/input/engine_main.py` INPUT union 缺 MOUSEINPUT（x64 sizeof=32≠40 → SendInput 恒静默失败，检测报告 critical #1）——**已修**（补 MOUSEINPUT+HARDWAREINPUT 使 sizeof=40 + SendInput 返回值校验）。实测：SetForegroundWindow → 单键 `f`（hold 0.08s，1 次按压）→ `status: sent`，游戏窗口无恙。
4. **suite 实机跑测**：`cli.py run --run-id real-run-1 --duration 25`（allow_injection=false=注入关闭）→ **129 事件 / 7 引擎全在线**（capture 28 / vision 13 / input 29 / sift 14 / battle 12 / scheduler 26 / vendor 7），capture 27 次全为真实游戏帧，metrics.json 记录 mode=supervised。
5. **频率控制约定**：输入仅人工单键验证（1 次按压）；自动化跑测注入保持关闭；引擎循环 interval=1.0s；上游节奏约定 poll_interval 上限 5s / 触发冷却 1s。

## 8. 快速复现命令
```powershell
cd C:\Users\13005\Downloads\work\rocogi
$env:UV_CACHE_DIR="$PWD\.cache\uv"; $env:UV_PYTHON_INSTALL_DIR="$PWD\.cache\uv-python"
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'
# backend
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --port 8787
# C-core
backend-c\build2\rocogi-core.exe --port 8788
# webui / vite
.toolchain\python\...\python.exe webui\server.py            # 8800
frontend: ..\.toolchain\node\node.exe node_modules\vite\bin\vite.js --port 5173
# 全链路校验
cd suite; ..\.toolchain\python\...\python.exe probes\verify_round.py --round 1
```

## 9. BWIKI 战斗数据库导入（2026-11-07）
来源 **洛克王国:手游WIKI（BWIKI）** `https://wiki.biligame.com/rocom`，抓取时间 2026-11-06T23:57+08:00。
页面本身只有模板调用、SMW 语义查询仅覆盖 37 条技能，**权威数据在站点的 Lua 数据模块**里，因此直接解析模块字面量（`.tmp/lua_literal.py`，纯 tokenizer，不执行 Lua）。

| 模块 | 产出 |
| --- | --- |
| `模块:PetData/SkillCatalog` | **788** 技能（攻击 349 / 特性 231 / 状态 156 / 防御 52） |
| `模块:PetData/Core` | **596** 精灵（六维 + 双系别 + 特性技能 + 进化组） |
| `模块:PetData/LearnsetCatalog` | **29818** 条精灵-技能关联（等级/18 条血脉/技能石） |
| `模块:PetData/Evolution` | **242** 进化链（581 节点） |
| `Widget:RestrainCalc.js` | **113** 条属性倍率（strong x2.0 / resist x0.5，双属性相乘） |

产物：`datasets/bwiki/bwiki_battle.json` + `bwiki_battle.db`（SQLite，只读 `mode=ro&immutable=1`）；
署名与复现说明见 `datasets/bwiki/PROVENANCE.md`（BWIKI 内容 **CC BY-NC-SA 3.0 CN**）。

**接入点**（全部实测通过）：
- `suite/engines/battle/bwiki.py` — 只读访问器：`find_pet` / `find_skill`（前缀匹配，`音波`→`音波弹`）/ `pet_skills` / `type_multiplier` / `best_skill`（score = 威力x倍率/耗能）/ `evolution_chain`。
- `suite/engines/battle/engine_main.py` — 新增 `catalog` / `pokedex` / `skills` / `best_skill` 四个 action（实测：水蓝蓝 六维 75/35/56/76/79/51 总 372 + 特性「浸润」；best_skill 排序合理）。
- `backend/app/adapters/bwiki.py` + `backend/app/api/routes.py` — 6 条 `/api/bwiki/*` 路由（catalog / pets / pets{name} / skills / type-chart / best-skill），**实测全 200**（冰打草 multiplier 2.0，best=冷风 120 分）。
- 优先级：**bwiki 优先，nrc.db 兜底**（`suite/config/engines/battle.toml` `[battle] bwiki_db`）。

## 10. 战斗 HUD 解析（2026-11-07）
- 优先级：**bwiki 优先，nrc.db 兜底**（`suite/config/engines/battle.toml` `[battle] bwiki_db`）。
- `backend/app/adapters/bwiki.py` + `backend/app/api/routes.py` — 6 条 `/api/bwiki/*` 路由（catalog / pets / pets{name} / skills / type-chart / best-skill），**实测全 200**（冰打草 multiplier 2.0，best=冷风 120 分）。
- `suite/engines/battle/engine_main.py` — 新增 `catalog` / `pokedex` / `skills` / `best_skill` 四个 action（实测：水蓝蓝 六维 75/35/56/76/79/51 总 372 + 特性「浸润」；best_skill 排序合理）。
- `suite/engines/battle/bwiki.py` — 只读访问器：`find_pet` / `find_skill`（前缀匹配，`音波`→`音波弹`）/ `pet_skills` / `type_multiplier` / `best_skill`（score = 威力x倍率/耗能）/ `evolution_chain`。
**接入点**（全部实测通过）：

署名与复现说明见 `datasets/bwiki/PROVENANCE.md`（BWIKI 内容 **CC BY-NC-SA 3.0 CN**）。
产物：`datasets/bwiki/bwiki_battle.json` + `bwiki_battle.db`（SQLite，只读 `mode=ro&immutable=1`）；

| `Widget:RestrainCalc.js` | **113** 条属性倍率（strong x2.0 / resist x0.5，双属性相乘） |
| `模块:PetData/Evolution` | **242** 进化链（581 节点） |
| `模块:PetData/LearnsetCatalog` | **29818** 条精灵-技能关联（等级/18 条血脉/技能石） |
| `模块:PetData/Core` | **596** 精灵（六维 + 双系别 + 特性技能 + 进化组） |
| `模块:PetData/SkillCatalog` | **788** 技能（攻击 349 / 特性 231 / 状态 156 / 防御 52） |
| --- | --- |
| 模块 | 产出 |

页面本身只有模板调用、SMW 语义查询仅覆盖 37 条技能，**权威数据在站点的 Lua 数据模块**里，因此直接解析模块字面量（`.tmp/lua_literal.py`，纯 tokenizer，不执行 Lua）。
来源 **洛克王国:手游WIKI（BWIKI）** `https://wiki.biligame.com/rocom`，抓取时间 2026-11-06T23:57+08:00。

## 10b. 「假战斗帧」防护（2026-11-07）

被动 watcher 抓到过一帧 `phase=battle score=2` 的「战斗」——实际是 **DeepSeek Harness 窗口**（mean=215，OCR 读出「旧应用编辑 / 连接rocogi检测云端代码问题」）。原因：screen 后端复制的是桌面 DC 里客户端矩形内的内容，玩家切回 Harness 时被覆盖的窗口就成了「游戏帧」；而 watcher 只看文件存在与 mtime，没看引擎的 `occlusion` / `live.published`。

两层修复：
- `.tmp/battle_driver.py::capture()` 现在解析引擎的 result 事件（此前误取第一条 JSON = ready 事件，导致 title/occlusion 全为空），并按 `occlusion.occluded` 与 `live.published` 拒绝覆盖帧；同时记录 `LAST_META`。
- `.tmp/battle_watch.py` 在判定战斗前校验 **窗口标题包含「洛克」** 且 `mean ≤ 190`（游戏帧 80–160）。

验证：`capture()` 恢复输出 `title='洛克王国：世界  '` / `occluded=False` / `published=true`。误判产物已改名为 `.tmp/bogus_calib_harness.*` 留档。

## 11. 输入安全补丁（2026-11-07，防越窗点击）
- 自检：`suite/probes/hud_selftest.py` — **20/20 PASS**（合成 OCR 行覆盖战斗帧四格技能配对、野外帧、OCR 变形输入）。
- `battle` 引擎新增 action `hud`（`[hud] lines` 指向 OCR 层导出的行 JSON，相对路径按部署根解析）。实测野外帧：`phase=world`，己方 `鸭吉吉 104/104 lv10`，`worldSkill=音波`。
- `suite/engines/battle/hud.py` — 纯解析层（**不做 OCR**，battle 引擎 venv 无 OCR 依赖）：区域盒 `REGIONS`（ally/enemy/skills/options/world_skill）、`parse_hp`（容忍本游戏 OCR 的 `1D4/104` 形式）、`parse_level` + `parse_level_loose`（容忍 `10纟`）、`read_skills`（数字行与技能名行按同一基线配对，缺数字时按自上而下顺序补号）、`read` 输出 `phase`（battle/world/unknown，证据三项：敌方面板 / 技能列 / 选项）。

界面布局由玩家确认：**左上=己方精灵面板（血/能量/队伍数/属性/性别/等级）、右上=敌方面板、左侧边缘=带数字 1..4 的技能图标列（按数字键发动）、右下角=选项**。

## 12. 实机观察与遗留
- **UE5 后台冻结**：游戏不在前台时渲染停止（连续帧完全一致、OCR 0 行），因此自动化每轮必须先 `foreground()`（AttachThreadInput → ALT tap → SwitchToThisWindow 三级升级链，实测 attach 阶段即成功）。
- **抓帧**：PrintWindow 对 D3D 返回全黑 → 自动回退 BitBlt 桌面 DC（引擎既有逻辑），均值亮度 114-147，`occluded=false`。
- **待验证（需真实战斗帧）**：左侧技能图标列与右下角选项的像素坐标标定。工具已就绪：`.tmp/battle_watch.py`（被动抓帧，出现战斗即落盘 `.tmp/battle_calib.png` + `.tmp/battle_calib.json`）、`.tmp/battle_driver.py`（读 HUD → BWIKI 排序 → 按数字键放技能 → 复核血量）。
- `suite/config/engines/input.toml` 的 `allow_injection` 仍为临测值，收尾需还原 `false`。

## 13. SIFT 定位阈值调优（2026-11-07）

现象：vendored tracker 用一个 162x162 的小地图裁剪**自定位也会失败**（ground truth 裁剪 (3000,2900) 得 kp=139 / good=31 / **inliers=7** / ratio=0.226，homography 反算中心 (2995,2894) 距真值 <7 px，却因上游门槛 `min_inlier_count=8`、`min_inlier_ratio=0.35` 被丢弃）。

处置：**不改第三方代码与配置**，在 suite 侧新增覆盖：
- `suite/engines/sift/engine_main.py` 新增 `apply_tuning(settings, tuning)`，用 `dataclasses.replace` 覆盖冻结的 `TrackerSettings`，未知键跳过、异常不致命；`build_engine` 读取 `[sift.tuning]`。
- `suite/config/engines/sift.toml` 新增 `[sift.tuning] min_inlier_count=5 / min_inlier_ratio=0.18 / min_match_count=5`。

A/B 实测（6 个真值裁剪，每个都用全新 tracker）：

| 门槛 | 正确锁定 | 错误锁定 | 拒绝 |
| --- | --- | --- | --- |
| 上游 8 / 0.35 | 0 | 0 | 6 |
| 调优 5 / 0.18 | **3**（误差 0.0–1.4 px） | **0** | 3 |

即：从"一个都锁不上"变成"能锁的都锁得准，锁不上的老实拒绝"（低纹理区域仍拒绝，不做假定位）。
`--action locate` 复核：`state=locked center=[2999,2899]`（探针真值 3000,2900）。

