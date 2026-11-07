# Windows 实机接入

模拟目标（`kind=mock`）能演示全部功能，但真正要驱动游戏，得把目标切到真实窗口。本文讲清楚三件事：窗口怎么找、画面怎么拿、键鼠怎么发，以及每一环在 Windows 上的坑。

## 1. 一次性准备

```powershell
cd rocogi
.\scripts\setup-windows.ps1
```

会装 `backend\requirements.txt`（含 `opencv-python-headless`、`pillow`、`numpy`），额外装 `pywin32` 与 `interception-python`。`pywin32` 用于部分窗口/输入调用，不装也能跑 SendInput 路径；`interception-python` 只有用驱动输入时才需要。

## 2. 目标窗口

设置页「游戏目标」的 `window_title` 是**标题关键词**，默认 `洛克王国：世界`。查找逻辑在 `backend/app/adapters/window.py:20 find_window()`：先 `FindWindowW` 精确匹配，失败后 `EnumWindows` 做大小写无关的子串匹配，取第一个命中。

窗口句柄解析发生在 `WindowsGameTarget.__init__`（`backend/app/adapters/mock.py:303-316`），找不到会直接抛 `未找到窗口: <关键词>`，所以切换实机前先把游戏开着。

**建议把标题写成游戏窗口里独有的一段**（比如版本号或服务器名），避免命中启动器、更新器或浏览器标签。

## 3. 采帧

当前实机采帧是 **GDI**：`backend/app/adapters/mock.py:370`

```python
gdi32.BitBlt(mem_dc, 0, 0, width, height, hwnd_dc, 0, 0, 0x00CC0020)
```

从窗口 DC 做 `SRCCOPY` 拷贝。它的优点是零依赖、不需要驱动；缺点也很明确：

- **窗口被遮挡或最小化时拿到的是脏帧**；
- UE5 的独占全屏/D3D 表面可能拷不到内容（黑帧）；
- 游戏在后台会**冻结渲染**，后台帧没有意义。

所以实机预设都带 `"force_foreground": true`，采帧前调 `ensure_foreground()`（`backend/app/adapters/window.py:47`）：最小化就 `ShowWindow(SW_RESTORE)`，然后 `BringWindowToTop` + `SetWindowPos`，再用 `SetForegroundWindow`；被前台锁拒绝时走 `AttachThreadInput` 强制抢焦点。

想自己判断窗口状态，可以让 harness 执行 `foreground` 动作（等价于采帧前的自动置前）：

```powershell
curl.exe -s -X POST http://127.0.0.1:8787/api/harness/act -H "Content-Type: application/json" -d "{\"action\":\"foreground\",\"params\":{\"window_title\":\"洛克王国：世界\"}}"
```

返回里 `result.focused=true` 表示目标窗口已经是前台，`result.restored=true` 表示刚从最小化恢复，`result.reason` 说明失败原因（如 `未找到窗口: …`）。

**如果实机一直黑帧**：先把游戏切到窗口化/无边框，系统缩放设 100%，再试。GDI 抓不到硬件加速表面时，退路是配套的 `suite/engines/capture`（`PrintWindow` + 桌面 DC 回退，见 `suite/engines/capture/engine_main.py:11-14` 的注释），它把这条限制写在文件头里，不是万能药。

## 4. 输入后端

| 后端 | 值 | 依赖 | 适用 |
| --- | --- | --- | --- |
| 模拟 | `mock` | 无 | 演示、调试节点逻辑 |
| SendInput | `windows` | 无 | 实机入门，游戏接受普通注入时够用 |
| Interception | `interception` | 驱动 + `interception-python` + 管理员 | 游戏过滤注入、需要驱动层键鼠时 |

能力探测在 `backend/app/config.py:213 platform_capabilities()`，其中 `interception` 读环境变量 `ROCOFLOW_INTERCEPTION=1` 作为开关：

```powershell
$env:ROCOFLOW_INTERCEPTION = "1"
```

### 安装 Interception

```powershell
# 1. 下载 oblitum/Interception v1.0.1 并解压
#    https://github.com/oblitum/Interception/releases/tag/v1.0.1
# 2. 管理员终端进入解压目录
.\install-interception.exe /install
# 3. 重启电脑
sc query interception      # 状态应为 RUNNING
# 4. 安装 Python 绑定（仅 Windows）
.venv\Scripts\pip install interception-python pywin32
```

之后以**管理员身份**启动后端，否则打开设备会失败。装完驱动不想用了，在同一个目录跑 `.\install-interception.exe /uninstall` 并重启。

## 5. 引擎预设

`backend/app/config.py:88 ENGINE_PRESETS` 里 5 套预设，设置页一键套用：

| 预设 | 目标 | 输入 | 定位源 | 采帧/识别 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `demo` | mock | mock | mock | 4 fps / 0.50 | 首次使用，免游戏 |
| `windows_sendinput` | windows | windows | sift | 4 fps / 0.55 | 实机入门 |
| `windows_interception` | windows | interception | sift | 5 fps / 0.52 | 实机推荐 |
| `low_latency` | windows | interception | sift（max_edge 1200） | 8 fps / 0.58，实时 0.25s | 抢球/战斗优先 |
| `accuracy` | windows | windows | sift（max_edge 2048） | 3 fps / 0.65，MCTS 120 次 | 离线分析、稳定跑图 |

预设只写引擎参数；窗口标题、输入后端、定位源这些**本机信息**存在设置里，工作流文件只带 `targetSlot`。

## 6. 小地图与 SIFT

地图追踪从画面右上角截小地图，默认归一化区域 `minimap_region = [0.84, 0.0275, 0.1172, 0.1875]`（`backend/app/config.py:62`）。它对应 2560×1600 下约 300×300 的方块。

- 分辨率或 UI 布局变了，先改这个区域，再点追踪页「重建锚点」；
- 锚点缓存写在 `runtime\cache\sift_anchors_*.npz`，重建会删掉重算 6000 个特征点（约 1 秒）；
- SIFT 的调优阈值在 `suite` 配置里（`min_inlier_count=5`、`min_inlier_ratio=0.18`、`min_match_count=5`），比上游默认宽松，实测 6 个取样点能锁 3 个且不锁错；
- 追踪页显示的 `confidence` 低于设置里的 `confidenceMin`（默认 0.25~0.3）就会标 `LOST`。

## 7. 热键

后端注册**系统级**热键（`backend/app/hotkeys.py`，`RegisterHotKey` + `GetMessageW` 消息循环），默认 `F9` 启动实时、`F10` 停止、`F11` 切换地图追踪；注册失败不影响其它功能，`GET /api/hotkeys` 会显示 `supported/running/bindings`。

网页里还有一层**页面级**快捷键（`frontend/src/App.vue`），逻辑一致：输入框聚焦时自动跳过，避免打字误触。

冲突处理：`F9` 常被录屏/语音软件占用，`F10` 在部分浏览器里是菜单键。改绑定（设置接口是 `PUT`，不是 `PATCH`）：

```powershell
curl.exe -s -X PUT http://127.0.0.1:8787/api/settings -H "Content-Type: application/json" -d "{\"hotkeys\":{\"start\":\"f7\",\"stop\":\"f8\",\"tracker\":\"f6\"}}"
```

改完要重启后端才会重新注册（热键在启动时注册）。

## 8. 数据与路径

| 内容 | 路径 | 说明 |
| --- | --- | --- |
| 应用数据库 | `runtime\rocoflow.db` | 设置、工作流、运行记录；删掉等于恢复出厂 |
| 运行证据截图 | `runtime\runs\<run_id>\` | 每步截图，可在「执行记录」里看 |
| 地图与图标 | `data\map\` | 9224 点位（`easy_roco.json` + `taptap.json`）、底图、图标 |
| 对战数据 | `datasets\bwiki\bwiki_battle.db` | 首选；可用 `ROCOFLOW_BWIKI_DB` 指向别处 |
| 旧对战数据 | `backend\vendor\nrc_ai\data\nrc.db` | BWIKI 缺名字时兜底 |
| SIFT 锚点缓存 | `runtime\cache\` | 可安全删除，下次自动重建 |

## 9. 边界（很重要）

- **不读写游戏内存**。`platform_capabilities()` 里 `reads_game_memory` 恒为 `false`，全部能力来自截屏 + 模板/轮廓识别 + 键鼠注入。
- **不做反检测**。如果游戏封禁自动化，本工具不提供绕过手段；用不用、怎么用由使用者负责。
- **模拟目标永远可用**。实机调试卡住时，把场景切到 `battle_polluted` 之类的固定画面单独验识别节点，比在游戏里试快得多。场景档位：`auto`（轮播）、`field_pet`（有可捕捉精灵）、`field`（空视野，可验「视角搜索」）、`battle_normal`、`battle_polluted`、`party_confirm`、`map`。
- **捕获状态机参数**放在设置文件的 `realtime` 段：`capture_retries`（最大丢球次数 1–10）、`capture_verify`（结果验证等待秒）、`capture_pan` / `capture_pan_steps` / `capture_pan_pixels`（空视野自动转视角搜索）。实时任务页启动时会把当前面板配置 `PUT /api/settings` 写回本机，F9 热键也读这一份启动。
