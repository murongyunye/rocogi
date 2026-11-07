# rocogi 代码问题检测报告

**仓库**：[murongyunyeh/rocogi](https://github.com/murongyunyeh/rocogi)（main @ a0252875，2026-11-06）
**方法**：GitHub API 实测（token 鉴权）→ 269 个第一方文件镜像到本地 → 三个独立审查代理分片全读 + 本鱼独立核查（语法扫描 107 个 .py 全过、CI 历史逐 job 日志、仓库树 8481 项、安全功能开关、Token 权限）。
**范围**：第一方代码 `backend/`、`suite/`、`backend-c/`、`frontend/`、`webui/`、`packaging/`、`scripts/`、`sdk/`、`.github/`（vendor/ 为 16 个上游仓库快照，仅抽查安全性）。

## 结论速览

| 级别 | 数量 | 说明 |
| --- | --- | --- |
| 🔴 Critical | **1** | suite 键盘注入 100% 静默失败（核心能力不可用且谎报成功） |
| 🟠 Major | **17** | 功能性缺陷：路径兼容、并发安全、静默降级、启动崩溃、脚本路径全错等 |
| 🟡 Minor | **46** | 句柄泄漏、竞态、吞错、校验缺失、死配置键等 |
| 流程/安全 | 4 项 | CI 覆盖缺口、GitHub 安全功能全关、archive 1.2GB 分卷、CI 失败史 |

综合评价：**架构设计相当克制规范**（领域核心+适配层、禁读内存护栏、app.js 全量 esc()、55 组元配置与引擎键位一致），但存在三个系统性弱点：① Windows 兼容细节（ANSI 路径/cp936 编码/GDI 生命周期）未经真实环境验证；② suite 从未进 CI，导致 Critical 级缺陷存活至今；③ 脚本层的路径约定三套互斥，镜像/部署场景全灭。

---

## 🔴 Critical

### C1 · suite 键盘注入 100% 静默失败（x64）
- **位置**：`suite/engines/input/engine_main.py:69-79`、`:176-177`
- **机制**：`INPUT` ctypes union 只定义了 `KEYBDINPUT`，缺 `MOUSEINPUT`。x64 下 `KEYBDINPUT=40` 字节，而正确 union 需 40（含 MOUSEINPUT 与对齐）→ 传入 SendInput 的 `cbSize` 与系统期望不符，**Vista 起 cbSize 严格校验，SendInput 恒返回 0**；`:79` 丢弃返回值，`:176-177` 仍返回 `{"status":"sent","backend":"sendinput"}` —— 成功是谎报。
- **佐证**：`suite/probes/input_drill.py:20-39` 同样结构错误但**检查了返回值**，x64 上跑一次即可证实 `apiAccepted=0`；`components.toml` 中 `input.sendinput status="ready"` 与现实相反。
- **修法**：union 补 `MOUSEINPUT`（最大成员决定 size）+ 校验 `SendInput` 返回值≠0，失败时上报错误事件；同修 `input_drill.py`。

---

## 🟠 Major（17）

### backend/app（5）
| # | 位置 | 问题 | 修法 |
| --- | --- | --- | --- |
| M1 | `backend/app/adapters/vision.py:46-48`（同族 `position.py:52`、`engine_common.py:36`、`engine/runtime.py:148`） | OpenCV `cv2.imread/imwrite` 在 Windows 只接受 ANSI 路径且失败**静默返回 None** → 中文/含空格安装路径下模板匹配、场景分类、SIFT、地图定位全灭 | `np.fromfile`+`cv2.imdecode` / `imencode`+`tofile` 统一封装 |
| M2 | `backend/app/nodes/capture.py:37-39` + `adapters/vision.py:60-66`、`vision_nodes.py:46` | 自定义 ROI 字段默认值就是逗号串 `"0.2,0.2,0.6,0.4"`，而 `resolve_roi` 只认 REGIONS 键或 4 元 list → 落 else 分支**恒取全屏**，用户配置静默失效 | resolve_roi 支持逗号串解析 + 不认识时显式告警 |
| M3 | `backend/app/main.py:52-59`、`hotkeys.py:70`、`config.py:185-189`、`routes.py:327-330` | 非法热键字符串经设置页原样持久化后，**下次启动 lifespan 无 try 直接崩**（`ValueError: 未知快捷键`） | `put_settings` 写入前过 `parse_hotkey` 校验；lifespan 降级容错 |
| M4 | `backend/app/adapters/mock.py:353-384`（`:301`、`services.py:37-39`） | 真机截图 GetDC/CreateCompatibleDC/Bitmap 无 try/finally（泄漏 GDI 句柄）、BitBlt/GetDIBits 返回值不查、窗口最小化→宽高 0→`cvtColor` 崩；hwnd 只找一次且缓存过期 | RAII 包装 + 返回值检查 + 每帧校验窗口有效性 |
| M5 | `backend/app/services/run_manager.py:55-76` | 无互斥直接起线程，所有 run 共享 Services 单例 → 并发 run 的 SendInput/截图交错串扰（与 backend-c M1 同源） | 全局运行锁或排队 |

### backend-c + frontend（2）
| # | 位置 | 问题 | 修法 |
| --- | --- | --- | --- |
| M6 | `backend-c/src/workflow.c:19-30` + `routes.c:662` + `http.c:274` | 全局 `g_data_dir/g_target` 每请求先 `free` 再赋值，而 HTTP 每连接一线程 → 并发 run 时 A 线程读悬空指针 / 目标窗口被 B 覆盖（UAF） | data_dir/target 改参数传递，删全局 |
| M7 | `backend-c/src/routes.c:700-752` vs `frontend/src/**`（`main.c:43,72`） | backend-c 只实现 10 个 API 端点，前端调 ~40 个（全在 Python 后端 61 路由里）且部分签名不同（`/api/workflows/run` 内联 JSON vs `/api/workflows/{id}/run`）→ **backend-c 托管 frontend/dist 必然大量 404** | 明确 backend-c 定位：要么补齐代理转发到 8787，要么去掉 static_dir 托管 |

### suite / scripts / webui / packaging（10）
| # | 位置 | 问题 | 修法 |
| --- | --- | --- | --- |
| M8 | `suite/engines/*/engine_main.py:239-245`（六个引擎同模式） | 主循环 `while True` 无 try/except → 任何异常**引擎即崩且无 error 事件**，suite 只看到进程退出 | 循环体包 try，异常 emit error 事件再退出 |
| M9 | `suite/cli.py:330-350` | 监督重启 backoff+`_wait_ready` **内联阻塞最长 60s**，且 `--duration` 截止检查在重启之后 → 截止时间被无形延长 | 重启移交后台线程，deadline 先查 |
| M10 | `suite/cli.py:354-357`（`suite.py:186-188`） | 退出只 `terminate` 直接子进程；vendor 引擎经 `subprocess.run(adapter)` 又起 adapter → **adapter 孤儿存活**继续占用游戏窗口 | Job Object 或进程树枚举击杀；stop-all.ps1 已有递归杀但缺等待复查 |
| M11 | `vendor engine_main.py:95-97`、`suite/cli.py:140,182`、`suite/kernel/suite.py:119-127`、`webui/server.py:593,561` | `subprocess` `text=True` 不带 `encoding` → Windows 默认 cp936，UTF-8 输出乱码/解码崩溃；且 `start-all.ps1:20-21` 设了 `PYTHONUTF8` 而 `rocogi-suite.cmd`/手动路径没设，行为分裂 | 全部加 `encoding="utf-8", errors="replace"`（`deploy_local.py:49-57` 是现成正面范例） |
| M12 | `scripts/start-all.ps1:3,69-71,140-142` | `$ErrorActionPreference='Continue'` 下 `Start-Process` 失败→pid=0→`Get-Process -Id 0`（Idle）无 `.StartTime` → **脚本崩在中途**，后续服务不启动 | 每步检查 `$?`/pid 非零再继续 |
| M13 | `packaging/scripts/build-rocogi-windows.ps1:19-24` | npm/pip 失败不查 `$LASTEXITCODE` → **打包失败印成功、陈旧 dist 进 zip** | 每步断言退出码 |
| M14 | `packaging/scripts/setup-windows.ps1:14-16,26` | 同上，pip 装失败仍 exit 0 | 同上 |
| M15 | suite 六引擎 vendor 根三套互斥约定：battle/capture/input/sift/vision 硬编码 `<仓库上上级>/rocogi/vendor/<名>`；vendor 引擎 `:22` 与 `suite/assets/build.py:23-26` 用 `<repo>/vendor` | 任意非标准布局（zip 解包、自定义安装目录、本鱼镜像）**全部失效**；`sift.toml engine_repo` 与代码又矛盾 | 统一 `SUITE/../vendor` + 环境变量覆盖 |
| M16 | `scripts/deploy_local.py:339-345,414-422`（`:322-323`、`:28`） | `verify_api` 抛错→uvicorn 孤儿+文件句柄泄漏；`DEFAULT_ROOT` 硬编码 `C:\Users\13005\Downloads\rocogi`（作者机器路径进了仓库） | try/finally 收尾 + 参数化默认路径 |
| M17 | `scripts/rocogi-suite.cmd:2-3` | Python 路径 `%ROOT%..\..\.toolchain\...` 多跳一级指向**仓库外**（对照 `start-all.ps1:6`、`webui/server.py:29`、`verify_round.py:19` 都指仓库内）→ 执行 9009 | 改为与 start-all.ps1 一致的仓库内路径 |

---

## 🟡 Minor（46，按区域归并）

**backend-c + frontend（12）**：`workflow.c:316` static `buf[128]` 跨线程复用；`workflow.c:651/659/668` `exec_from` 返回值忽略→恒报 "finished"（`routes.c:668-669` 成了死代码）；`routes.c:424-431` crop 坐标 int 溢出→越界读；`routes.c:129-136` captures_dir 惰性初始化竞态；`routes.c:666` `g_run_count++` 非原子；`http.c:62-78` recv 无 `SO_RCVTIMEO`（慢连接占线程）；`http.c:204` `ACAO:*` 且无鉴权（CSRF/CSWSH 面）；`capture.c:47-49,115-120` 一次非超时 DXGI 错误→`g_dxgi_failed` 永久降级（ACCESS_LOST 本可恢复）；`host.c:86` 忽略 `nFileSizeHigh`（>4GB 文件大小错）；`main.c:47` 端口 `atoi` 无 0-65535 校验；`integrations/human_move.c:56-62,99-106` `used` 可超 `out_cap`；`frontend/src/views/PetView.vue:104-110` loadDetail 竞态（DexView 有 seq 守卫，PetView 漏）。

**backend/app（13）**：`input.py:114-117,132-135` 主屏归一化→多显示器错位；`input.py:197-202` `mouse_event` 吞错仍记成功；`storage.py:385-386` `_new_id`=毫秒+tid%4096 可碰撞；`storage.py` finish_run/update_workflow 锁外读改写；`run_manager.py:38-42` 事件队列 `queue.Full` 静默丢；`routes.py:204-213` run_artifact 未校验 run_id（`..` 可越界读 rocoflow.db）；`battle.py:85` sqlite 非只读会静默建空库（对照 `dex.py:66`/`pvp.py:49` 的 `mode=ro` 正确写法）；`position.py:62` np.load 未关；`mapdata.py:72-75` 缺键 KeyError 全局崩；`sessions.py:116-123` join(3) 超时仍强制 idle→`is_alive` 拒绝重启；`harness.py:394-395` presses 无 clamp（schema `maximum:20` 仅 UI 校验）；`detector.py:114-118` `cx>640` 产生负宽框→NMSBoxes 抛→整帧检测丢弃；`engine/runtime.py:145-150` imwrite 吞错仍 emit artifact（前端 404）。

**suite / scripts / webui / packaging（21）**：battle `:30-35` import 吞异常；capture `:53-55` 吞错回退 mock 黑帧；scheduler `:238-253` seq 竞态 + `:236` run_id 未消毒；input `:140-141` join 竞态 + `:126` RegisterHotKey 抢占已有热键 + `:176-177` 前台注入可能打错窗口（`deploy_local.py:223-224` 冒烟还会直发 press）；sift `:110-113` imread None→TypeError + `:153` sqlite 非只读；open() 不关系列（`sift:137`、`assets/build.py:108,153`、`verify.py:70,126`、`verify_round.py:133,148,235-236,245`、`s0_probe.py:122`）；`cli.py:307` kill 不 wait；`suite.py:119-127` TimeoutExpired 未捕 + `:103-104` 秒级时间戳 run_id 可碰撞；`webui/server.py:730-731` startswith 前缀绕过 + `:88-93` tmp 撞名 + `:132-144` pid 复用误判；死配置键（`vendor.toml` adapters_root/patches、`sift.toml` alternate_space、`vision.toml` confidence/backend）；`package-release.py:237-240` 字母序取 zip（v1.0.10 < v1.0.2 会选旧版）；`verify-release-041.py:164` `makedirs("")`；工具链版本钉死 `cpython-3.12.16` ×4 处；`verify_round.py:146` freeze 超时；`stop-all.ps1:70-74` TOCTOU；`start-all.ps1:224` vite `--host 0.0.0.0` 局域网暴露（backend 自己都只绑 127.0.0.1）；`cli.py:341-343` missing-venv 仍记 running；`assets/build.py:63-68` 仅比 size 即跳过复制 + `:235` 反斜杠路径进 sources 清单；跨区提示 `backend/app/engine_cli.py:102,105` print 在管道消费时有 cp936 `UnicodeEncodeError` 风险。

---

## 流程 / 仓库卫生（云端侧实测）

1. **CI 覆盖缺口（Critical 的直接成因）**：`.github/workflows/pytest.yml` 只跑 `backend/`；suite、backend-c、scripts、webui **零测试覆盖**。C1 这种在 CI 跑一次 `input_drill.py` 就能现形的缺陷存活至今，就是因为 suite 不进 CI。建议：pytest 矩阵加 suite 探针（input_drill 允许 apiAccepted=0 环境跑通结构校验）、backend-c 加编译步骤。
2. **GitHub 安全功能全关**：Dependabot（404）、CodeQL（从无分析记录）、secret scanning（禁用）。仓库有 16 个 vendor 快照，至少应开 Dependabot + secret scanning。
3. **archive/ 1.2GB**：11 个 90MB 分卷 zip 直接进 git；克隆成本高且 git 对二进制无 delta。建议改 GitHub Release 附件（当前 Release 只有 v0.2.0，v0.4.1 的 zip 只躺在 archive/ 里未发布）。
4. **CI 失败史（已修复）**：eb78d44 挂在 `test_capability_contract.py::test_actions_endpoint_shape` 的 `assert 33 == 11`——11→33 动作集扩容后旧断言没跟上（典型"魔法数字断言"脆弱性）；由 ec996bc/a025287 修复，当前 HEAD 绿。

## ✅ 核实无问题的部分（正面清单）

- **语法**：107 个第一方 .py 全部通过 AST 解析，零语法错误。
- **backend-c**：capture.c GDI/D3D 资源释放全路径正确、http.c body 所有权链清晰、input/match/mapstat/pngio/winenum/hotkey/static/json/strbuf/nodes 干净。
- **frontend**：定时器/WS/RAF 清理齐全、类型与后端序列化一致（`storage.py:374-377`、`sessions.py:353`）、WS 端点与 `main.py:92` 一致；质量明显高于 backend-c。
- **webui**：`app.js` 40 处 innerHTML 全部过 `esc()`，无 XSS。
- **安全护栏**：vendor/nrc_ai 15 个 py 无 eval/exec/shell=True；`test_memory_safety.py` 的禁读内存正则扫描有效。
- **packaging**：entries+launcher 设计正确；`build-engines.ps1` 检查到位；`stop-all.ps1` 有 startTime 防误杀。
- **配置**：`config/*.toml` 与 55 组元引擎键位一致。

## 建议修复顺序

1. **C1**（SendInput union + 返回值校验）——核心能力当前不可用。
2. **M17/M15**（路径修复）——让 suite 在标准安装外能跑起来。
3. **M1**（OpenCV 非 ASCII 路径封装）——中文 Windows 用户第一杀手。
4. **M3**（热键校验+lifespan 容错）——一次误配置=下次启动崩溃。
5. **M6/M5**（并发互斥）——真机多任务前必须解决。
6. **M12/M13/M14**（脚本退出码）——发布链路可靠性。
7. CI 补 suite 探针 + 开启 Dependabot/secret scanning（半小时配置，防 C2 出现）。
8. 其余 minor 按"改到哪个文件顺手修"节奏清。

---
*检测执行：3 个独立审查代理（backend/app 52 文件全读；suite/scripts/webui/packaging/sdk 全读；backend-c/src 30 C 文件 + integrations + frontend 25 文件）+ 云端 API 核查。所有发现均带文件:行号与机制描述，可直接定位。*
