# rocogi datasets — 上游数据集与模型整合工作区

> 建于 2026-11-06。位置：`rocogi/datasets/`。rocogi 整体以 **AGPL-3.0** 开源（见仓库根 `LICENSE`）。
> 目标：把三个工具上游「已经列好类别」的数据集/模型/训练工具整合成一套可直接开训的工作区。

> **大文件说明**：模型权重（.pt/.onnx，共 ~170MB）不进 git，随发布走 GitHub Release 资产，
> 或用 `datasets/tools/fetch_upstream.py weights` 从上游原位拉取（带 sha256 校验）。
> 无许可上游（Tsuann/SCH）的脚本同样不直接入库，用 `fetch_upstream.py tools` 原位拉取。

---

## 1. 为什么要整合（一句话版）

rocogi 的精灵识别天花板卡在「只有 1 类 onnx 推理模型」。上游三家有现成的类别定义、已训权重和完整训练流水线——**类别表已经列好，权重已经训好，脚本已经写好**，缺的只是把它们拼到一个屋檐下。

| 上游 | 给了什么 | 类别表 |
|---|---|---|
| **Tsuann/RocoKingdom-AutoCapture** | sprite_detector.**pt** V4 权重（mAP50=0.994）+ 12 个训练/标注/增强脚本 | 8 只 S2 精灵（id 0-7，**已冻结**） |
| **Makapic/RocoPilot** | 4 个独立精灵 .pt（geli/huolong/youyingshu/xueren）+ 基座 yolo26s.pt + 11 个脚本 | 按精灵分桶，geli=和平鸽+菊花梨 |
| **SCH-CMYK/game-automation** | 场景 4 类 data.yaml + best_20260601.pt（19.2MB）+ LoFTR 定位模型 + 标注/训练器 | ore/creature/obstacle/character（id 0-3） |
| **SIFT-Map-Tracker v0.10.2（17 版合并包，本地）** | POI 资源数据集（现役 + 99 个历史版本 JSON）+ 72 张物品图标图形集 + 8 张标记渲染图 + 标准档 SIFT 特征 + item_siamese_v2.onnx | 按资源分类：植物/矿物/宝箱/战斗/收集/全部资源 |

## 2. 目录结构

```
datasets/
├── README.md                        ← 本文件
├── pets/                            ← 精灵检测数据集（统一 11 类）
│   ├── classes.json                 ← 统一类别表（Tsuann 8 类冻结 + Makapic 3 类追加）
│   ├── data.yaml.template           ← YOLO 训练配置模板
│   ├── sources/
│   │   ├── tsuann/classes.json      ← 上游原表 verbatim（id 0-7）
│   │   └── makapic/classes.json     ← 上游模型↔统一 id 映射（含内部类 id）
│   ├── labeled/                     ← 标注数据落点（per-species 分批，incremental_train 兼容）
│   ├── cumulative/                  ← incremental_train.py 的累积合并目录
│   ├── yolo_format/                 ← train_model.py prepare_dataset 的划分输出
│   └── raw/                         ← capture_dataset.py 采集会话落点
├── scene/                           ← 场景检测数据集（SCH 4 类，独立类别空间）
│   ├── classes.json / data.yaml.template / labeled/
├── map/                             ← SIFT-Map-Tracker v0.10.2 合并包拆出的地图侧数据集（§2.5）
│   ├── poi/                         ← 现役 v0.10.2 资源 JSON（[31]植物 等）
│   ├── poi_legacy/                  ← 99 个历史版本 POI/路线 JSON（v0.6.1→v0.10.1 演化链，原路径归档）
│   ├── routes/                      ← 现役跑图路线 JSON（作者署名保留在文件名）
│   ├── icons/                       ← 72 张物品图标图形集（resource_catalog/icons_cache）
│   ├── render/                      ← 8 张标记渲染图 full/nav（~27MB，本体走 Release，见 §2.5）
│   └── PROVENANCE/                  ← MERGE-REPORT.md + build-manifest.json（字节级合并纪律与 sha256）
├── raw/screenshots/                 ← 自采原始帧（rocogi capture 链路，1280×800）
├── tools/
│   ├── fetch_upstream.py            ← 无许可脚本与权重的原位拉取器（本仓库自有，AGPL）
│   ├── makapic/                     ← 11 个脚本 verbatim（MIT (c) 2026 yorusacri，随仓库分发）
│   │                                   train_*/detect_*/label_pets/label_tool/eval_geli/merge_xueren/mark_align
│   ├── tsuann/                      ← （fetch_upstream.py tools 拉取）12 个脚本，上游无 LICENSE 不入库
│   └── sch/                         ← （fetch_upstream.py tools 拉取）label_tool/trainer/download_models/data.yaml
├── models/upstream/                 ← 上游权重清单 MANIFEST.json（本体走 Release/fetch，许可见 §5）
└── training_runs/                   ← ultralytics runs/train 输出（.gitignore 自留地）
```

## 3. 统一类别的合并规则（关键决策）

1. **Tsuann 的 id 0-7 永久冻结**——`sprite_detector.pt` V4 权重按这套 id 训练，改动即作废增量训练的兼容性。新物种一律从 id 8 起追加。
2. **Makapic 是「模型即类别」**：每只精灵一个独立模型、内部 id 恒为 0（geli.pt 例外=内部 2 类）。推理后按 `sources/makapic/classes.json` 的 `maps_to_unified_id` 折算：huolong→8、youyingshu→9、xueren→10、geli 的 hepingge→4 / juhuali→3。
3. **pets 与 scene 是两个数据集，不合并类别空间**：`creature`（场景级生物）与精灵物种是不同粒度；混训会互相污染标注口径。
4. 命名分歧记录而非抹平：Tsuann 的 `gongping_ge`（公平鸽）= Makapic 的 `hepingge`（和平鸽），在 classes.json 里以 aliases 互通。

## 4. 训练流水线（照抄 Tsuann README 的路数）

```
0) 备料  python datasets/tools/fetch_upstream.py all
         （tools = Tsuann/SCH 脚本；weights = 8 个权重 + sha256 校验；
          Makapic 脚本已随仓库分发，无需拉取）
① 采集   rocogi capture 链路（PrintWindow/BitBlt，1Hz）→ datasets/raw/screenshots/
         或 tools/tsuann/scripts/capture_dataset.py --screen（mss 全屏/区域）
② 提帧   tools/tsuann/scripts/extract_frames.py dataset/video/xxx.mp4 --sprite <name> --fps 2
③ 标注   tools/tsuann/scripts/auto_label.py <dir> --class-id <id>   （半自动）
         tools/makapic/scripts/label_pets.py <dir> --pet <name>    （拖拽画框）
         tools/tsuann/scripts/label_tool.py                        （Tsuann 版）
④ 分批   datasets/pets/labeled/<species>/（images/ + labels/，YOLO txt 格式）
⑤ 增量   tools/tsuann/scripts/incremental_train.py --new-data pets/labeled_<species>/ --device cuda
         → 自动合并 cumulative/ → 增强 → 重训 → 导出 ONNX
⑥ 全量   tools/tsuann/scripts/train_model.py --data pets/labeled/（prepare_dataset 自动 8:2 划分）
⑦ 部署   产物 onnx → suite/assets/models/sprite_detector.onnx（引擎 detector.py 后处理
         已按 [1,4+n,8400] 兼容多类，见部署验证报告 §7）
```

- 场景数据集（scene/）走 `tools/sch/trainer.py` 的 YOLOTrainer（yolo11n 基座）。
- 本机无 GPU/CUDA 时 `--device cpu` 可跑（Tsuann 脚本默认），RTX 卡建议 cuda。

## 2.5 map/ — SIFT-Map-Tracker 数据集区（2026-11-06 增）

**来源**：本地 `SIFT-Map-Tracker-v0.10.2-merged.zip`（sha256 `4ad3c40188ac998be3f6355fae0a26045df7ceea2c63c659f9bf6a7dc51b276c`）——把 SIFT-Map-Tracker **17 个历史发布包（v0.6.1→v0.10.2）按字节完整性合并**的单一版本：缺失文件按 manifest sha256 从旧版原样找回（7/8 成功，1 个无法恢复的 default_route.json 未用近似文件冒充），99 个旧版 JSON 全量归档。完整合并纪律见 `map/PROVENANCE/MERGE-REPORT.md`，官方字节清单见 `map/PROVENANCE/build-manifest.json`。

| 内容 | 数量/体积 | 说明 |
|---|---|---|
| `poi/` | 2 JSON | 现役 v0.10.2 资源数据（[31] 植物 类 729KB 等） |
| `poi_legacy/` | 99 JSON / 12.8MB | v0.6.1→v0.10.1 各版本资源/路线/目录数据（含 Rocopath、抖音作者路线），按原版本目录归档 |
| `routes/` | 2 JSON | 现役跑图路线（作者署名保留在文件名：落城遇、天天做梦） |
| `icons/` | 72 PNG / 10.2MB | 物品图标图形集（resource_catalog/icons_cache），配 `models/upstream/item_siamese_v2.onnx` 做物品匹配训练/评测 |
| `render/` | 8 PNG / 26.9MB | 标记渲染图（full=带 POI 标注 / nav=导航风），**走 Release datasets-v1，不进 git** |
| 标准档 SIFT 特征 | 80.2MB npz | **走 Release datasets-v1**；rocogi suite/assets 的 94992 特征即其 0.75 档（compact165） |

**Release 资产名对照**（GitHub 会洗掉资产名里的非 ASCII 与 `[]`，按此对照原始文件名）：

| Release 资产名 | 原文件（map/render/） |
|---|---|
| render__Z-.full.png / .nav.png | Z-全部资源 -SiftMapTracker.full/nav.png |
| render__0.35.+.full.png / .nav.png | 0[35] 植物+矿物 -SiftMapTracker.full/nav.png |
| render__.6.full.png / .nav.png | [6] 收集 类 -SiftMapTracker.full/nav.png |
| render__S3.-SiftMapTracker.full.png / .nav.png | S3新增资源-SiftMapTracker.full/nav.png |

**与既有资产去重**：`display_map.png` / `logic_map.png` / `SIFT_features_075.npz` 与部署树既有副本（suite/assets/maps + vendor/sift-map-tracker）**逐字节相同**（sha256 已核），未重复收录。

**许可备注**：图标/地图素材为游戏衍生素材、路线数据为社区作者贡献（作者署名保留在文件名与 JSON 内）。
0.4.4 起这些**图形素材不再入库、也不随发行包分发**（`datasets/map/icons/` 已加入 `.gitignore`），仓库只保留坐标 JSON 与抓取脚本；
需要时按 `docs/PUBLISH_SCOPE.md` 在本机重建，署名与来源一并保留。

## 5. 许可备忘（AGPL 全开源决策版）

rocogi 本仓库（含本目录的自有文件）以 **AGPL-3.0** 分发。第三方内容按其各自许可处理：

| 内容 | 许可 | 处置 |
|---|---|---|
| rocogi 自有代码/文档 | **AGPL-3.0**（仓库根 LICENSE） | 随仓库开源分发 |
| Makapic 代码/脚本 | **MIT**（Copyright (c) 2026 yorusacri） | verbatim 入库分发，保留版权声明 |
| Tsuann 代码/脚本 | **无 LICENSE 文件** = 默认保留所有权利 | **不入库**；`fetch_upstream.py tools` 原位拉取 |
| SCH 内容 | license NOASSERTION（自定义） | **不入库**；同上原位拉取 |
| 所有 `.pt` 权重 | **Ultralytics AGPL-3.0**（torch 元数据实锤） | 与本仓库同许可，兼容分发；走 Release 资产或 `fetch_upstream.py weights` |
| SCH best_20260601.pt / loftr_model.onnx | 无 LICENSE / 学术权重 | 不随仓库分发，走 `fetch_upstream.py weights` 或 SCH release v1.0 |
| SIFT-Map-Tracker 数据/图标/渲染 | 游戏衍生 + 社区署名数据（见 §2.5） | 坐标 JSON 随仓库（保留署名）；**图标与渲染图不入库**，本机重建；标准档 SIFT 特征走 Release |

## 6. 完整性校验记录（2026-11-06 下载时）

| 文件 | 尺寸 (B) | 校验 |
|---|---|---|
| sprite_detector.pt | 6237226 | == GitHub API blob size ✓ PK zip |
| geli.pt | 22495203 | == API ✓ PK |
| huolong.pt | 20310974 | == API ✓ PK |
| youyingshu.pt | 19160410 | == API ✓ PK |
| xueren.pt | 20310974 | sha256 == LFS oid 1103556…f9223 ✓ ⚠️ **与 huolong.pt 字节级相同（上游占位复件，非真雪人模型）** |
| yolo26s.pt | 22588772 | sha256 == LFS oid 1f47a78…9aa78a ✓ |
| best_20260601.pt | 19161683 | == SCH download_models.py 硬编码 ✓ |
| loftr_model.onnx | 39295679 | == SCH download_models.py 硬编码 ✓ |

（逐文件 sha256 见 `models/upstream/MANIFEST.json` 的 `sha256_actual` 字段。）

> ⚠️ **重要更正**：`xueren.pt` 与 `huolong.pt` sha256 完全相同（110355639ab2…）——上游 Makapic 并没有真正训练雪人模型，以 huolong 权重复件占位发布。统一类别表的 id 10（xueren 雪人）目前**无任何已训权重**，需自采重训；实际可用的上游精灵模型 = 小独角兽（Tsuann V4）、火龙、幼婴鼠、和平鸽+菊花梨（Makapic geli/huolong/youyingshu）。

## 7. 下一步（按性价比排序）

1. **跑通增量训练一发**：用实测的 capture 链路采 50-100 帧小独角兽 → auto_label → incremental_train 验证全链路（CPU 也能跑）。
2. **把 sprite_detector.pt V4 加载进训练循环**作为 `--model` 基座（而不是 yolov8n.pt）——保留已学的小独角兽知识。
3. Makapic 4 模型逐个 `detect_*.py` 离线评测，决定是「独立模型 ensemble」还是「数据合并重训单一 11 类模型」。
4. scene 4 类用 SCH best_20260601.pt 直接推理试跑（矿石/生物/障碍/角色），再决定要不要自采补充。
