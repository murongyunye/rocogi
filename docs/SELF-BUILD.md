# 自构建说明（0.4.5 起，当前 0.4.6）

这份包只放**源码与取不回来的东西**，其余全部由仓库里的脚本现取。目标是：拿到 300 MB 左右，
就能在任意 Windows 机器上把整套系统（后端 8787 / 前端 5173 / 六引擎 / 地图追踪 / 图鉴 / PvP）跑起来。

## 包里有什么

| 内容 | 说明 |
| --- | --- |
| `backend/`、`frontend/src/`、`suite/`、`backend-c/` | 全部源码（FastAPI 应用、Vue 3 界面、六引擎运行时、C 核心） |
| `data/map/` + `datasets/map/{poi,poi_legacy,routes}` | 底图与 9224 个 POI 坐标（JSON，不含美术资源） |
| `datasets/tools/` | BWIKI / PvP / 上游资产 / 模型权重的取回与导入脚本 |
| `scripts/` | `bootstrap.ps1`（体检）、`setup-windows.ps1`、`package-release.py`、`verify/` |
| `archive/sift-map-tracker/` | SIFT 定位包 338 MB —— **唯一的大件**，见下文 |
| `docs/` | 说明文档；`docs/reports/asset-trace.md` 是资产核验记录 |

## 包里没有、但一条命令能补的

```powershell
# 0) 体检：缺什么、怎么补（不下载，只打印）
.\scripts\bootstrap.ps1

# 1) 自动补齐能无人值守的部分：MinGit、Node、15 个 vendor 上游仓、两个数据库
.\scripts\bootstrap.ps1 -Apply

# 2) 单独补某项
.\vendor\tools\fetch-upstream.ps1                    # 15 个上游仓（按 pinned commit）
.\rocogi\.venv\Scripts\python.exe datasets\tools\bwiki\fetch_bwiki.py --list datasets\bwiki\titles.txt
.\rocogi\.venv\Scripts\python.exe datasets\tools\bwiki\import_bwiki.py
.\rocogi\.venv\Scripts\python.exe datasets\tools\pvp\fetch_pvp.py
.\rocogi\.venv\Scripts\python.exe datasets\tools\pvp\import_pvp.py
.\rocogi\.venv\Scripts\python.exe datasets\tools\fetch_upstream.py weights   # 239 MB 模型权重
node scripts\verify\make-shots.mjs                  # 13 张文档截图（游戏内画面，不入库）

# 3) 装依赖并构建
.\scripts\setup-windows.ps1
cd frontend; npm install; npm run build
```

## 为什么留着 338 MB 的 SIFT 包

`archive/sift-map-tracker/` 来自 SIFT-Map-Tracker v0.10.2：作者只发了打包好的 release zip，
**没有公开仓库、没有 commit、没有源码**。里面是运行时必需的四件东西：

| 文件 | 大小 | 作用 |
| --- | ---: | --- |
| `sift-map-tracker/assets/SIFT_features.npz` | 76.4 MB | 6000 个地图特征点，锚点定位直接用 |
| `sift-map-tracker/assets/display_map.png` | 69.9 MB | 小地图预览底图 |
| `sift-map-tracker/assets/logic_map.png`（与 `raw.png` 同内容） | 各 46.4 MB | 坐标映射底图 |
| `sift-map-tracker/service/service.exe` | 56.8 MB | 上游定位服务可执行文件 |

删掉它们 = 地图追踪彻底失效且无法恢复，所以按「保守策略」入库。其余资产都过了
`scripts/trace-assets.py --check`，确认上游还在才移出版本库。

## 怎么复核这个判断

```powershell
.\rocogi\.venv\Scripts\python.exe scripts\trace-assets.py --check    # 25 ok / 0 miss / 9 skipped
.\rocogi\.venv\Scripts\python.exe scripts\report-tree-size.py        # 按目录看跟踪体积
.\rocogi\.venv\Scripts\python.exe scripts\trim-buildable.py          # 还有没有可重取却被跟踪的
```

`scripts/assets/manifest.json` 是机器可读版：34 条资产，每条写明 `kind`、来源、固定提交与重建入口。
核验结果随版本记录在 `docs/reports/asset-trace.md`。

## 两个包

| 产物 | 大小 | 用途 |
| --- | ---: | --- |
| `rocogi-0.4.6-src.zip` | ≈296 MB | 直接解压即用；不含 git 历史 |
| `rocogi-0.4.6.bundle` | ≈248 MB | `git clone rocogi-0.4.6.bundle rocogi`，单提交快照，可继续提交 |

两者内容一致（936 个跟踪文件）。校验：`sha256sum -c rocogi-0.4.6.sha256.txt`。

## 已知缺口

- `vendor/sift-map-tracker/legacy-json/**` 里有 31 个文件名含 Windows 非法字符（`[4] 寳…`），
  这些 blob 在原始仓库对象库里，小写/大写路径在 Linux 上能还原，Windows 上必须跳过。
- `archive/sift-map-tracker/SiftMapTracker.Client.exe` 是上游遗留的 LFS 指针（134 字节），
  已从 `.gitattributes` 移除 `filter=lfs` 规则，克隆不再需要 git-lfs。
- 发行包里不含 BWIKI / PvP 数据库：它们的权利不属于本项目，必须本机重建（见上面第 2 步）。
