# 大文件审计（`c:\Users\13005\Downloads\work`）

> 只读遍历，未删除、未提交、未修改任何被审计文件。生成时间：2026-11-06。

## 0. 口径与方法

| 项目 | 值 |
| --- | --- |
| 扫描根 | `c:\Users\13005\Downloads\work` |
| 扫描方式 | `os.walk` 递归，`os.stat(follow_symlinks=False)`，不跟随链接 |
| 「大文件」阈值 | 50 MiB = 52,428,800 B；「超大」阈值 100 MiB = 104,857,600 B（与 GitHub 单文件硬限同口径） |
| 全树规模 | **172,274 个文件 / 15,713,040,956 B（14.63 GiB）** |
| 扫描耗时 | 501.7 s |
| 读取失败 | 481 条（多为无权限或无响应路径），不影响下列结论 |
| 云端判定依据 | 远端 `murongyunyeh/rocogi` 在 commit `5b8de48d538a09f8be44f826fcb8f6cacc470b18` 的完整 git tree：**7,238 个 blob / 438,530,214 B**。逐文件比对 **路径 + git blob SHA-1**（`blob <len>\0` + 内容），不做文件名猜测 |

## 1. 全部 >50 MiB 的单文件（43 个）

「所属仓/模块」列区分该文件属于哪个组件；「云端」列是实测结论。

| # | 路径（相对 `work`） | 字节 | MiB | 所属仓/模块 | 云端状态 |
| ---: | --- | ---: | ---: | --- | --- |
| 1 | `rocogi\release\rocogi-0.4.1-full.zip` | 934,102,683 | 890.8 | rocogi 发布包（整包） | 未在远端 |
| 2 | `.toolchain\nuget-packages\bettergi.assets.map\1.0.25\bettergi.assets.map.1.0.25.nupkg` | 215,576,403 | 205.6 | rocogi 工具链 / NuGet 缓存 | 未在远端（可重建） |
| 3 | `.toolchain\nuget-packages\microsoft.ai.directml\1.15.4\microsoft.ai.directml.1.15.4.nupkg` | 202,292,617 | 192.9 | 同上 | 未在远端（可重建） |
| 4 | `.toolchain\nuget-packages\bettergi.assets.model\1.0.39\bettergi.assets.model.1.0.39.nupkg` | 173,830,757 | 165.8 | 同上 | 未在远端（可重建） |
| 5 | `_publish_tmp\sift-extract\SiftMapTracker.Client.exe` | 157,916,510 | 150.6 | 工作区临时 / sift 归档待推副本 | 未在远端（不可重建） |
| 6 | `.toolchain\nuget-packages\microsoft.ml.onnxruntime\1.21.0\microsoft.ml.onnxruntime.1.21.0.nupkg` | 120,110,707 | 114.5 | rocogi 工具链 / NuGet 缓存 | 未在远端（可重建） |
| 7 | `.toolchain\venv-crawler\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v9.0.2.exe` | 105,423,872 | 100.5 | rocogi 工具链 / Python venv 依赖 | 未在远端（可重建） |
| 8 | `.toolchain\node24\node-v24.18.0-win-x64\node.exe` | 92,534,088 | 88.2 | rocogi 工具链 / Node 运行时 | 未在远端（可重建） |
| 9–18 | `_publish_tmp\release-parts\rocogi-0.4.1-full.zip.part-01` … `part-10` | 各 90,000,000 | 85.8 | 工作区临时 / 整包分段（未推） | 未在远端 |
| 19 | `.toolchain\node\node.exe` | 87,034,184 | 83.0 | rocogi 工具链 / Node 运行时 | 未在远端（可重建） |
| 20 | `.toolchain\nuget-packages\skiasharp.nativeassets.win32\3.119.4\runtimes\win-x86\native\libSkiaSharp.pdb` | 86,761,472 | 82.7 | rocogi 工具链 / NuGet 缓存 | 未在远端（可重建） |
| 21 | `.venv\Lib\site-packages\cv2\cv2.pyd` | 85,848,064 | 81.9 | rocogi 主 venv | 未在远端（可重建） |
| 22 | `.toolchain\...\skiasharp...\runtimes\win-arm64\native\libSkiaSharp.pdb` | 84,938,752 | 81.0 | rocogi 工具链 / NuGet 缓存 | 未在远端（可重建） |
| 23 | `.toolchain\...\skiasharp...\runtimes\win-x64\native\libSkiaSharp.pdb` | 84,033,536 | 80.1 | 同上 | 未在远端（可重建） |
| 24 | `.toolchain\nuget-packages\bettergi.assets.map\1.0.25\contentFiles\...\Teyvat_0_2048_SIFT.mat.png` | 80,418,623 | 76.7 | rocogi 工具链 / NuGet 缓存 | 未在远端（可重建） |
| 25 | `_publish_tmp\sift-clone\archive\sift-map-tracker\sift-map-tracker\assets\SIFT_features.npz` | 80,157,992 | 76.4 | 工作区临时 / 推送用 clone 工作树 | 内容已在远端（见 §4） |
| 26 | `_publish_tmp\sift-extract\sift-map-tracker\assets\SIFT_features.npz` | 80,157,992 | 76.4 | 工作区临时 / sift 归档副本 | 内容已在远端（见 §4） |
| 27 | `.toolchain\nuget-packages\skiasharp.nativeassets.win32\3.119.4\skiasharp.nativeassets.win32.3.119.4.nupkg` | 76,963,437 | 73.4 | rocogi 工具链 / NuGet 缓存 | 未在远端（可重建） |
| 28 | `rocogi\suite\engines\capture\.venv\Lib\site-packages\cv2\cv2.pyd` | 74,742,784 | 71.3 | suite / capture 引擎 venv | 未在远端（可重建） |
| 29 | `rocogi\suite\engines\scheduler\.venv\Lib\site-packages\cv2\cv2.pyd` | 74,742,784 | 71.3 | suite / scheduler 引擎 venv | 未在远端（可重建） |
| 30 | `rocogi\suite\engines\sift\.venv\Lib\site-packages\cv2\cv2.pyd` | 74,742,784 | 71.3 | suite / sift 引擎 venv | 未在远端（可重建） |
| 31 | `rocogi\suite\engines\vision\.venv\Lib\site-packages\cv2\cv2.pyd` | 74,742,784 | 71.3 | suite / vision 引擎 venv | 未在远端（可重建） |
| 32 | `_publish_tmp\sift-clone\.git\objects\46\947742db35be3118a20b65cbe682a546e6ee1a` | 73,314,849 | 69.9 | 工作区临时 / clone 对象库 | 未在远端（可重建） |
| 33 | `rocogi\suite\assets\maps\display_map.png` | 73,292,633 | 69.9 | suite / 地图资产 | 未在远端（同字节副本已在远端，见 §4） |
| 34 | `_publish_tmp\sift-clone\archive\...\assets\display_map.png` | 73,292,633 | 69.9 | 工作区临时 / 推送用 clone 工作树 | 内容已在远端（见 §4） |
| 35 | `_publish_tmp\sift-extract\sift-map-tracker\assets\display_map.png` | 73,292,633 | 69.9 | 工作区临时 / sift 归档副本 | 内容已在远端（见 §4） |
| 36 | `.toolchain\nuget-packages\opencvsharp4.runtime.win\4.11.0.20250507\opencvsharp4.runtime.win.4.11.0.20250507.nupkg` | 64,067,858 | 61.1 | rocogi 工具链 / NuGet 缓存 | 未在远端（可重建） |
| 37 | `.toolchain\nuget-packages\opencvsharp4.runtime.win\4.11.0.20250507\runtimes\win-x64\native\OpenCvSharpExtern.dll` | 62,044,672 | 59.2 | 同上 | 未在远端（可重建） |
| 38 | `.toolchain\build\yotta.exe` | 60,669,952 | 57.9 | 构建产物（yotta） | 未在远端（可重建） |
| 39 | `_publish_tmp\sift-clone\archive\...\service\service.exe` | 59,505,395 | 56.7 | 工作区临时 / 推送用 clone 工作树 | 内容已在远端（见 §4） |
| 40 | `_publish_tmp\sift-extract\sift-map-tracker\service\service.exe` | 59,505,395 | 56.7 | 工作区临时 / sift 归档副本 | 内容已在远端（见 §4） |
| 41 | `_publish_tmp\sift-clone\.git\objects\5a\969b39075a36684d8e6b62884cb3129342fe0b` | 59,060,428 | 56.3 | 工作区临时 / clone 对象库 | 未在远端（可重建） |
| 42 | `.toolchain\rocom-pets\rocom-pets-1.14.2-windows-x64.exe` | 54,496,847 | 52.0 | rocogi 工具链 / 预编译工具 | 未在远端（可重建） |
| 43 | `.toolchain\gobin\wails3.exe` | 52,772,352 | 50.3 | rocogi 工具链 / Go 工具 | 未在远端（可重建） |

> 另外 `_publish_tmp\release-parts\rocogi-0.4.1-full.zip.part-11` 为 34,102,683 B（32.5 MiB），低于 50 MiB 门槛，未计入上表；整包分 11 段，前 10 段各 90 MB。

## 2. >100 MiB 的单文件（7 个）

**GitHub 单文件硬限 100 MiB，普通 push 必失败。**

| # | 路径（相对 `work`） | 字节 | MiB | 性质 |
| ---: | --- | ---: | ---: | --- |
| 1 | `rocogi\release\rocogi-0.4.1-full.zip` | 934,102,683 | 890.8 | 自有发布包整包，需分段才能上云 |
| 2 | `.toolchain\nuget-packages\bettergi.assets.map\1.0.25\bettergi.assets.map.1.0.25.nupkg` | 215,576,403 | 205.6 | NuGet 缓存，可重新下载 |
| 3 | `.toolchain\nuget-packages\microsoft.ai.directml\1.15.4\microsoft.ai.directml.1.15.4.nupkg` | 202,292,617 | 192.9 | 同上 |
| 4 | `.toolchain\nuget-packages\bettergi.assets.model\1.0.39\bettergi.assets.model.1.0.39.nupkg` | 173,830,757 | 165.8 | 同上 |
| 5 | `_publish_tmp\sift-extract\SiftMapTracker.Client.exe` | 157,916,510 | 150.6 | 上游 sift 发布包内二进制，**无远端副本** |
| 6 | `.toolchain\nuget-packages\microsoft.ml.onnxruntime\1.21.0\microsoft.ml.onnxruntime.1.21.0.nupkg` | 120,110,707 | 114.5 | NuGet 缓存，可重新下载 |
| 7 | `.toolchain\venv-crawler\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v9.0.2.exe` | 105,423,872 | 100.5 | pip 依赖自带的 ffmpeg，可重新安装 |

## 3. 总计

| 区间 | 文件数 | 总字节 | 折合 |
| --- | ---: | ---: | ---: |
| >50 MiB | **43** | **4,712,388,472** | 4.39 GiB |
| >100 MiB | **7** | **1,909,253,549** | 1.78 GiB |
| 全树 | 172,274 | 15,713,040,956 | 14.63 GiB |

其中 7 个 >100 MiB 文件占全树的 **12.2%**，43 个 >50 MiB 文件占 **30.0%**。

## 4. 云端状态

43 个文件里，**没有任何一个以原路径存在于远端**。分四类（合计 43）：

| 云端状态 | 个数 | 说明 |
| --- | ---: | --- |
| 已在远端（原路径） | 0 | 远端 7,238 个 blob 中无任何一条匹配这 43 个路径 + blob SHA |
| 内容已在远端（不同路径、同字节） | 7 | `_publish_tmp` 下 sift 副本 6 个 + `suite\assets\maps\display_map.png`，见下 |
| 未在远端（可重建） | 24 | `.toolchain` 17 个、各 venv 5 个、clone 对象 2 个 |
| 未在远端（不可重建） | 12 | `release` 整包 1、`_publish_tmp` 分段 10、`SiftMapTracker.Client.exe` 1 |

**「内容已在远端」的判定**（本地路径不在远端树上，但同样字节的内容已随 `archive/sift-map-tracker/` 上云，git blob SHA-1 实测一致；下表 4 个唯一对象，另有 sift-clone 下 3 个同字节副本，合计 7 个文件）：

| 本地文件 | 远端对应路径 | blob SHA-1 |
| --- | --- | --- |
| `_publish_tmp\sift-extract\sift-map-tracker\assets\SIFT_features.npz` | `archive/sift-map-tracker/sift-map-tracker/assets/SIFT_features.npz` | `e14179502832…` |
| `_publish_tmp\sift-extract\sift-map-tracker\assets\display_map.png` | `archive/sift-map-tracker/sift-map-tracker/assets/display_map.png` | `46947742db35…` |
| `_publish_tmp\sift-extract\sift-map-tracker\service\service.exe` | `archive/sift-map-tracker/sift-map-tracker/service/service.exe` | `5a969b39075a…` |
| `rocogi\suite\assets\maps\display_map.png` | `archive/sift-map-tracker/sift-map-tracker/assets/display_map.png` | `46947742db35…`（与上一条同一 blob） |

> 说明：`SiftMapTracker.Client.exe`（150.6 MiB）**没有**远端副本——它是 202 文件推送时唯一被排除的文件，原因是超过 100 MiB 硬限。

## 5. 按目录汇总

### 5.1 `rocogi` 内部（按一级子目录）

| 目录 | 文件数 | 字节 | 折合 | 性质 |
| --- | ---: | ---: | ---: | --- |
| `.toolchain` | 147,712 | 10,909,432,816 | 10.16 GiB | **可再生**：NuGet 缓存、Node/Python/Git 运行时、Go 工具、构建产物 |
| `suite` | 10,132 | 1,106,274,847 | 1.03 GiB | 混合：代码/配置为源码，`engines\*\\.venv`（4×约 170–230 MiB）与 `logs\*` 为可再生 |
| （根目录文件） | 68 | 955,775,114 | 0.89 GiB | 主要是 `release\*.zip` 整包与分段来源 |
| `vendor` | 7,394 | 246,626,911 | 0.23 GiB | 上游运行时子集（源码，需保留语义） |
| `.venv` | 2,173 | 196,353,621 | 0.18 GiB | **可再生**：pip 安装 |
| `frontend` | 991 | 66,515,561 | 0.06 GiB | 其中 `node_modules` 约 60 MiB，**可再生** |
| `release` | 100 | 12,844,740 | 0.01 GiB | `only-local` 99 个 sift legacy-json + MANIFEST |
| `.git` | 577 | 12,049,502 | 0.01 GiB | 本地 git 元数据，可再生 |
| `docs` | 21 | 7,067,389 | 0.01 GiB | 源码文档 |
| `backend-c` | 187 | 5,581,822 | 0.01 GiB | 源码 |
| `data` | 52 | 4,310,980 | 0.00 GiB | 数据 |
| `webui` | 42 | 2,887,476 | 0.00 GiB | 源码 |
| `backend` | 91 | 2,302,670 | 0.00 GiB | 源码 |
| `packaging` | 7 | 572,866 | 0.00 GiB | 源码 |
| `.github` | 1 | 687 | — | 配置 |
| `game-data` | 4 | 617 | — | 配置 |
| `runtime` | 0 | 0 | — | 空目录 |

### 5.2 `work` 顶层其余目录

| 目录 | 文件数 | 字节 | 折合 | 性质 |
| --- | ---: | ---: | ---: | --- |
| `_publish_tmp` | 1,252 | 2,144,595,540 | 2.00 GiB | **可再生/临时**：sift 抽取副本 489 MB、整包分段 934 MB、推送用 clone 约 350 MB、辅助脚本 |
| `.publish-tmp` | 1,327 | 24,181,569 | 0.02 GiB | 上一次发布的临时分块目录，可再生 |
| （根目录文件） | 143 | 15,666,228 | 0.01 GiB | 脚本与日志 |
| `.screenshots` | 0 | 0 | — | 空目录 |

### 5.3 可再生内容占比

`.toolchain` + 各 `.venv` + `suite\engines\*\\.venv` + `frontend\node_modules` + `suite\logs` + `_publish_tmp` + `.publish-tmp` 合计约 **13.2 GiB**，占全树 **90%**，全部属于构建产物 / 依赖缓存 / 工具链 / 临时目录，删掉后可按依赖清单重建。

真正**不可再生的本地内容**只有两处：`rocogi\release\rocogi-0.4.1-full.zip`（890.8 MiB，云端无副本）与 `_publish_tmp\sift-extract\SiftMapTracker.Client.exe`（150.6 MiB，云端无副本，且超 100 MiB 硬限）。

## 6. 与云端现状的对照（事实）

- 远端 commit：`5b8de48d538a09f8be44f826fcb8f6cacc470b18`，共 **7,238 blob / 438,530,214 B**。
- `archive/sift-map-tracker/`：**202 个文件 / 354,902,764 B**，与本地 sift 归档副本一致（此前已逐文件 SHA-256 核对流程进行中，本次为路径级核对）。
- 远端目录分布：`archive` 202 文件 / 338.5 MiB，`vendor` 6,677 文件 / 64.2 MiB，`docs` 32 / 6.8 MiB，`data` 52 / 4.1 MiB，其余合计约 4.7 MiB。
- 本地 `vendor` 有 7,394 个文件，远端 `vendor` 只有 6,677 个：差额来自远端文本白名单（二进制不入仓），属已知差异。

## 7. 本次未做的事

- 未删除任何文件，未提交，未推送。
- 未对 43 个文件做内容级 SHA-256 校验（只做了路径 + git blob SHA-1 判定；blob SHA-1 本身即内容哈希）。
- 481 条目录读取失败未逐条展开（多为 `.toolchain` 内长路径与无权限项），如需清单可另跑。
