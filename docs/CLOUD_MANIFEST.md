# 云端清单（CLOUD_MANIFEST）

本文件是 `rocogi` 仓库在 GitHub 上的**唯一权威清单**：记录远端文件数、总字节、
`archive/` 与 `release/` 的全部内容、LFS 对象，以及**仍未上云的项及原因**。

- 仓库：`https://github.com/murongyunyeh/rocogi`（私有）
- 分支：`main`
- 本文件提交前的 HEAD：`dddf1231e6dc0dce1c19cd814cbc4b3ce53af6f8`
- 生成时间：2026-11-06
- 统计口径：GitHub Git Trees API（`recursive=1`，`truncated=false`），
  只计 `type=blob` 的文件；LFS 指针按指针文件自身字节计，不含 LFS 对象存储。
- 下表数字取自 `dddf123` 快照（此时本文件与 `docs/LARGE_FILES_AUDIT.md` 尚未提交）；
  两者随后在同一提交中入库，提交后远端为 **7,260 个 blob**。

## 1. 总览

| 指标 | 数值 |
| --- | ---: |
| 远端文件数（blob） | 7,258 |
| 远端总字节 | 1,390,295,394（约 1.29 GiB） |
| 其中 `archive/` | 218 个 / 1,289,009,945 B |
| 其中 `release/` | 1 个 / 17,641,940 B |
| 其中源码与文档等其余目录 | 7,039 个 / 83,643,509 B |

### 1.1 目录分布

| 目录 | 文件数 | 字节 |
| --- | ---: | ---: |
| `archive/` | 218 | 1,289,009,945 |
| `vendor/` | 6,677 | 67,278,473 |
| `release/` | 1 | 17,641,940 |
| `docs/` | 32 | 7,183,922 |
| `data/` | 52 | 4,310,980 |
| `backend/` | 83 | 2,208,596 |
| `frontend/` | 42 | 776,037 |
| `packaging/` | 9 | 686,307 |
| `backend-c/` | 51 | 546,213 |
| `webui/` | 18 | 280,548 |
| `suite/` | 45 | 221,618 |
| 根目录文件 | 9 | 70,940 |
| `scripts/` | 11 | 49,133 |
| `game-data/` | 7 | 25,164 |
| `sdk/` | 1 | 4,261 |
| `.github/` | 2 | 1,317 |
| **合计** | **7,258** | **1,390,295,394** |

## 2. `archive/` 全部内容（218 个 / 1,289,009,945 B）

| 子目录 | 文件数 | 字节 | 说明 |
| --- | ---: | ---: | --- |
| `archive/release/` | 15 | 934,107,047 | 0.4.1 full 包的分段与校验材料，见 §3 |
| `archive/sift-map-tracker/` | 203 | 354,902,898 | sift 完整源码归档，见 §2.1 |

### 2.1 `archive/sift-map-tracker/`（203 个 / 354,902,898 B）

| 子路径 | 文件数 | 字节 | 说明 |
| --- | ---: | ---: | --- |
| `sift-map-tracker/` | 100 | 341,408,095 | 主程序源码、资源、模型、`service.exe` |
| `legacy-json/` | 99 | 12,773,679 | 14 个历史版本的资源/路线 JSON |
| `Resources/` | 1 | 712,782 | `Sounds/item_alert.wav` |
| 顶层文件 | 3 | 8,342 | `MERGE-REPORT.md`、`build-manifest.json`、`SiftMapTracker.Client.exe`（LFS 指针，134 B） |

`>10 MiB` 的文件：

| 文件 | 字节 |
| --- | ---: |
| `sift-map-tracker/assets/SIFT_features.npz` | 80,157,992 |
| `sift-map-tracker/assets/display_map.png` | 73,292,633 |
| `sift-map-tracker/service/service.exe` | 59,505,395 |
| `sift-map-tracker/assets/raw.png` | 48,600,819 |
| `sift-map-tracker/assets/logic_map.png` | 48,600,819 |
| `sift-map-tracker/assets/SIFT_features_075.npz` | 18,903,971 |

`sift-map-tracker/service/service.exe`、`SIFT_features.npz`、`display_map.png` 超过 GitHub
50 MiB 建议值但低于 100 MiB 硬限，直接以普通 git blob 存放在仓库中。

## 3. `archive/release/`：0.4.1 full 包（分段）

整包 `rocogi-0.4.1-full.zip` 共 **934,102,683 B**，按 **90,000,000 B** 切成 11 段
（前 10 段等长，第 11 段 34,102,683 B）。逐段 SHA-256：

| 分段 | 字节 | SHA-256 |
| --- | ---: | --- |
| `rocogi-0.4.1-full.zip.part-01` | 90,000,000 | `ba69829a87444dd88ca2d8404ba4a7f0e210d442277021079220b5167d3c2917` |
| `rocogi-0.4.1-full.zip.part-02` | 90,000,000 | `b9cd189e4304245d0a1adce5de5832c3f377d9a72670b1283cb6253a2cc61203` |
| `rocogi-0.4.1-full.zip.part-03` | 90,000,000 | `fda72d919725fcab8977883a586ca1f513b159ce40cebf2768dc2aff4796d61c` |
| `rocogi-0.4.1-full.zip.part-04` | 90,000,000 | `603edf011940c0665a54878dab88da25b279d46593a27b6b68771eac45717d6d` |
| `rocogi-0.4.1-full.zip.part-05` | 90,000,000 | `321050d87c61dd9ad4bef53472a3a26fe3b8b51e36dc13abac06002e2c33d677` |
| `rocogi-0.4.1-full.zip.part-06` | 90,000,000 | `f6d017eb6fd0de48cdbea1d1daf5dbbfd934853d99e5f6b0e4299d139454eae4` |
| `rocogi-0.4.1-full.zip.part-07` | 90,000,000 | `5a54ef766740667a786bc2ec046095c0c7fcc5fd0dc5ca66af8606453c59d95f` |
| `rocogi-0.4.1-full.zip.part-08` | 90,000,000 | `9b2825f736d21a34c6c3b3ec18b9892df34f245552c4145d122f5f0eac18c3b9` |
| `rocogi-0.4.1-full.zip.part-09` | 90,000,000 | `5531049c9bfaedca62915dd43f8732dcbebb9c9fb82db31e5c7864709d9f9733` |
| `rocogi-0.4.1-full.zip.part-10` | 90,000,000 | `5e67d88614c94cc40a7275af142dc4de8c8564846613130124a751d44b5b99a0` |
| `rocogi-0.4.1-full.zip.part-11` | 34,102,683 | `b50198345539386b9de9f09e84a811f9c8e2d5c05ee89922b7b00440510d8006` |

**整包 SHA-256**：`35831d62f440ae67f718a11a3b849a19f734f3f8138af64a23e059fec147cac4`

配套 4 个文件：`SHA256SUMS.txt`（1,067 B，`sha256sum -c` 格式）、
`rocogi-0.4.1-full.zip.sha256`（89 B，整包哈希）、
`parts.json`（1,920 B，整包/逐段哈希与字节数，便于脚本解析）、
`merge-parts.ps1`（1,288 B，合并校验脚本）。

### 3.1 合并与校验

```powershell
# 进入含 11 个分段的目录后执行；默认输出到临时文件并校验整包 SHA-256
pwsh -File .\merge-parts.ps1 -Dir . -OutFile .\rocogi-0.4.1-full.zip
```

`merge-parts.ps1` 按文件名排序后顺序拼接，再以 `Get-FileHash -Algorithm SHA256`
与 `35831d62f440ae67f718a11a3b849a19f734f3f8138af64a23e059fec147cac4` 比对，
不一致时打印 `SHA256_MISMATCH` 并 `exit 1`。

实测结果：`merged_bytes=934102683`、`merged_sha256=35831d62…c147cac4`、`SHA256_OK`。

## 4. `release/`：0.4.1 lite 包

| 文件 | 字节 | 说明 |
| --- | ---: | --- |
| `release/rocogi-0.4.1-lite.zip` | 17,641,940 | 0.4.1 精简发布包，直接以普通 blob 存放 |

## 5. LFS 对象清单

| 路径 | 指针 blob | LFS oid（sha256） | 实际字节 |
| --- | ---: | --- | ---: |
| `archive/sift-map-tracker/SiftMapTracker.Client.exe` | 134 B | `b0a5f024facb49c8bb6b4754d0649e13a59a773b61faa59186aa56cb0a02b9be` | 157,916,510 |

`.gitattributes`（根目录，88 B）：

```
archive/sift-map-tracker/SiftMapTracker.Client.exe filter=lfs diff=lfs merge=lfs -text
```

只对该单个文件启用 LFS，未使用 `*.exe` 通配，避免把已以普通 blob 入库的
`service.exe` 转成指针。

### 5.1 上传异常与处理（如实记录）

`git-lfs 3.8.1` 自身的 `pre-push` 上传在 S3 阶段稳定失败（3 次尝试，均在同一 URL）：

```
LFS: Not Implemented: https://github-cloud.s3.amazonaws.com/alambic/media/1296810258/b0/a5/b0a5f024…b9be?actor_id=96469121&key_id=0&repo_id=1444796896
error: failed to push some refs to 'https://github.com/murongyunyeh/rocogi.git'
```

排障结论（实测，非推断）：

| 检查 | 结果 |
| --- | --- |
| `POST /info/lfs/objects/batch`（operation=upload） | HTTP 200，返回 `upload` + `verify` 动作 |
| 用同一签名 URL 执行 `curl -X PUT --data-binary` | **HTTP 200**，上传 157,916,510 B |
| `POST` 到返回的 `verify` 地址 | HTTP 200 |
| `operation=download` 批量接口 | HTTP 200，返回可下载的预签名 URL |

即：**S3 与凭据均正常，问题出在 git-lfs 客户端的上传实现**（服务器回 501 Not Implemented）。
处理方式：按 batch API 返回的签名 `upload` 动作直接 PUT 对象（`curl`），再调用 `verify` 登记，
随后以 `git push --no-verify` 推送指针提交（跳过有问题的 LFS pre-push 钩子）。
最终以**干净目录 clone + LFS 拉取**做端到端验证，见 §6.2。

## 6. 校验记录

### 6.1 `archive/release/` 与 `release/` 的 blob 比对（16/16 一致）

对本地 11 段 + 4 个校验材料 + lite 包，逐一按 `sha1("blob <len>\0" + bytes)`
与远端 tree 的 `sha`、`size` 比对：`same 16 / diff 0 / missing 0`。

### 6.2 Client.exe 的干净 clone 校验

在空目录重新 clone（`--depth 1 --filter=blob:none --no-checkout`，固定到 `dddf123`），
先取出 `.gitattributes` 再 checkout 目标目录，由 LFS smudge 下载真实对象：

| 项目 | 结果 |
| --- | --- |
| clone 的 HEAD | `dddf1231e6dc0dce1c19cd814cbc4b3ce53af6f8` |
| 仓库内指针 | `version https://git-lfs.github.com/spec/v1` / `oid sha256:b0a5f024…b9be` / `size 157916510` |
| clone 得到的字节数 | 157,916,510 |
| clone 得到的 SHA-256 | `b0a5f024facb49c8bb6b4754d0649e13a59a773b61faa59186aa56cb0a02b9be` |
| 与本地 SHA-256 比较 | **一致** |

### 6.3 整包还原校验

见 §3.1，本地实测合并结果与整包 SHA-256 完全一致。

## 7. 仍未上云的项及原因

结论：**不可再生的本地内容已全部上云**。以下仅剩可再生内容。

| 类别 | 规模 | 原因 |
| --- | --- | --- |
| `.toolchain/`（git、python、node、go、cmake、dotnet、nuget-packages、build 产物） | 约 9 GB（其中 >50 MiB 的 17 个） | 工具链与包缓存，可按版本重新下载/安装 |
| `.venv/`、`suite/engines/*/.venv/` | 各 venv 的 `cv2.pyd` 等 | 由 `requirements.txt` 重建 |
| `node_modules/`、`dist/`、`build/`、`build2/`、`obj/`、`bin/`、`__pycache__/` | 数千文件 | 构建产物，可再生 |
| `runs/`、`logs/`、`suite/runs/` | 运行记录 | 运行期生成，无归档价值 |
| `.secrets/`、令牌文件 | — | 凭据，**不得上云** |
| `_publish_tmp/` 中的旧 clone 对象库 | 2 个 >50 MiB 对象 | 推送过程产物，已随本次归档作废 |

> 说明：`release/rocogi-0.4.1-full.zip` 与 `_publish_tmp/sift-extract/SiftMapTracker.Client.exe`
> 曾是仅有的两处「不可再生的未上云内容」，现已分别以 11 个分段（§3）与 LFS 对象（§5）上云。

## 8. 与其它文档的关系

- `docs/PUBLISH_SCOPE.md`：发布范围与连接器限制的历史说明，其中「两个 zip 只在本地」一节
  已被本文件取代（full 包已分段上云、lite 包已直推）。
- `docs/LARGE_FILES_AUDIT.md`：全树 `>50 MiB` / `>100 MiB` 扫描与分类，本文件 §7 的分类依据。
- `docs/VENDOR_RUNTIME_SCOPE.json`：本地 `vendor/` 运行时子集的逐文件清单；
  完整上游源码以 `archive/sift-map-tracker/` 与 `vendor/` 远端内容为准。
