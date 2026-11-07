# SIFT Map Tracker 合并报告（v0.10.2）

本目录是把 `Shift-Map-Tracker` 下 17 个发布包比对后合并出的**单一版本**，以最新的 **v0.10.2** 为基准。

## 1. 版本清单与客户端 exe 指纹

| 版本 | 客户端 exe sha256 前缀 | 文件数 | 解压大小 |
| --- | --- | ---: | ---: |
| v0.6.1 | Python 版（无 client exe） | 260 | 418.7 MB |
| v0.6.7 | Python 版（无 client exe） | 263 | 426.2 MB |
| v0.7.1 | Python 版（无 client exe） | 265 | 454.1 MB |
| v0.8.0 | Python 版（无 client exe） | 281 | 559.4 MB |
| v0.8.1 | Python 版（无 client exe） | 284 | 561.5 MB |
| v0.8.3 | Python 版（无 client exe） | 283 | 509.7 MB |
| v0.8.4 | Python 版（无 client exe） | 283 | 509.7 MB |
| v0.8.5 | Python 版（无 client exe） | 253 | 452.2 MB |
| v0.9.1 | bbd4f198acf6a6cb | 164 | 379.6 MB |
| v0.9.3 | 15425956ceef4a92 | 154 | 453.4 MB |
| v0.9.5 | c6ae69acd166d8bf | 105 | 528.9 MB |
| v0.9.6 | 2735db9a4f9a0b52 | 103 | 506.3 MB |
| v0.9.7 | faad01cb6c4c8c21 | 102 | 505.5 MB |
| v0.10.1 | c05004d30a5ee3c8 | 104 | 512.6 MB |
| v0.10.2 | b0a5f024facb49c8 | 106 | 585.5 MB |

- 0.6.1–0.8.5 是 Python 版（`app.py` + `assets/`），包内没有 WPF 客户端 exe；
- 0.9.1 起改为 WPF 客户端（`SiftMapTracker.Client.exe`，155–158 MB）+ 两个自包含服务；
- **每个 WPF 版本的客户端 exe 哈希都不同**，说明每次发版都重新编译过，无法跨版本复用同一个 exe；因此合并以最新 v0.10.2 的 exe 为唯一客户端。

## 2. JSON 比对结论

- 0.9.x 起每版 6–9 个 JSON，0.6–0.8 每版 25–46 个（旧目录结构 `assets/`、`resources/`）；
- v0.10.2 的 `build-manifest.json` 声明了 17 个文件的字节数与 sha256，但发布包里**缺了 8 个**（打包时被漏掉）；
- 旧版本里存的路线/资源 JSON 中有 99 个文件的内容在 v0.10.2 中完全不存在。

## 3. 本次合并动作

### 3.1 按清单恢复缺失文件（7/8，sha256 与清单一致）

| 文件 | 大小 | 来源版本 |
| --- | ---: | --- |
| `Resources/Sounds/item_alert.wav` | 0.68 MB | v0.8.0–0.9.6 |
| `sift-map-tracker/settings.py` | 1.1 KB | v0.9.6 |
| `sift-map-tracker/assets/SIFT_features_075.npz` | 18.03 MB | v0.9.5 |
| `sift-map-tracker/assets/SIFT_features_075.manifest.json` | 911 B | v0.9.3 |
| `sift-map-tracker/assets/item_siamese_v2.onnx` | 1.13 MB | v0.10.1 |
| `sift-map-tracker/assets/item_siamese_v2.manifest.json` | 3.2 KB | v0.10.1 |
| `sift-map-tracker/assets/resource_catalog/config.json` | 49 KB | v0.9.1 |

以上文件均由旧版本中原样取出，**字节与清单 sha256 完全一致**（未改写、未重压缩）。

### 3.2 无法恢复的 1 个文件

`sift-map-tracker/routes/default_route.json`（20024 B，sha256 `874df92c…73cc`）在所有 16 个旧版本中都没有同哈希副本；最接近的是 v0.9.7 的 `2.…78983697482.json`（19979 B，内容不同）。为保证「内容不变」，**没有用近似文件冒充**；该文件缺失不影响启动（`build-manifest.json` 里的 `tracker.defaultRouteSource` 指向的是另一条路线，客户端会在运行时补默认路线）。

### 3.3 旧版 JSON 归档

`legacy-json/<版本>/…`：99 个旧版本 JSON（12.18 MB），全部是与 v0.10.2 内容不重复的路线/资源/目录数据，按原版本、原相对路径存放。除 `build-manifest.json` / `screen-recognition.manifest.json` 这类构建元数据外，内容原样保留。

## 4. 体积

| 项 | 大小 |
| --- | ---: |
| 合并目录（212 个文件） | 617.6 MB |
| 其中 legacy-json 归档 | 12.18 MB |
| 打包 zip（`SIFT-Map-Tracker-v0.10.2-merged.zip`） | 见同级 zip |

> 未做任何瘦身：`raw.png` 与 `logic_map.png` 字节完全相同（各 46.35 MB），按要求保留两份。
