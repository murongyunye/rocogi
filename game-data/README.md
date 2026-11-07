# game-data 真实数据接入

本目录只做**资源与模板**接入：规范化用户放进来的游戏截图、模板、地图和宠物资源。**不做实机截图链路验证，也不做游戏窗口识别**（这一轮明确不验证）。

## 目录约定

```
game-data/
  incoming/            只读；用户手工放原始文件，import.py 绝不改写
    frames/            *.png 游戏截图
    templates/         *.png 模板 / UI 元素（背景透明或纯色边框均可）
    map/               *.png 地图原图
    pets/              每个宠物一个子目录（rocom-pets 导出的实体资源）
  processed/           规范化产物（可重复生成）
  import.py            导入脚本
  import-report.md     每次运行覆盖的导入报告
```

### frames

- 格式：PNG（8/16 bit；RGB/RGBA/灰度均可）。
- 命名：任意；同名不同内容会记录 `nameCollisionWith`，不会互相覆盖。
- 产出：`processed/frames/index.json`（尺寸、DPI、sha256、来源、处理时间）；可选 `--roi x,y,w,h` 输出裁剪图 `processed/frames/<stem>-<sha8>-roi.png`。
- DPI 从 PNG `pHYs` 块读取；没有则记为 `null`。

### templates

- 格式：PNG，建议带 alpha 背景透明。
- 单边上限默认 2048 px（`--max-template-size` 可调）。
- 自动去除透明边/纯色边，输出裁剪后的 `processed/templates/<stem>-<sha8>.png`。
- 生成 `processed/templates/manifest.json`：名称、原始/裁剪尺寸、偏移、sha256、建议 ROI、自匹配得分（同图自匹配应 ≥ 0.99）。
- 建议 ROI 只是相对整帧的初始框，**不是标定结果**。

### map

- 支持已识别分辨率：
  - `8192 x 8192` → `8192 pixel world-map space`
  - `6144 x 5888` → legacy map space
- 其他分辨率**不会硬塞**：写入 `processed/map/calibration-<stem>.json`，状态 `needs-calibration`，需要人工给 3 个源点与 3 个目标点做仿射。
- 产出：`processed/map/index.json`（尺寸、sha256、空间判定、状态）。

### pets

- 每个宠物一个目录，必须包含：
  - `entity.json`（`schema = "rkpet2.entity.v1"`）
  - `manifest.toml`
  - `model.glb`（glTF 2.0 GLB）
  - `forms/<asset>/anim.rka`
  - `forms/<asset>/tex/*.png`
- 脚本先做本地存在性/格式检查，再调用
  `vendor/ElliottZhao666666-rocom-codex-pets-gen/scripts/validate_input.py`。
- 产出：`processed/pets/report.json` 与每只宠物的 `*-validator.json`。
- 资源本身不复制到 `processed/`，只记录来源与校验结果。

## 运行

用 suite 的 sift venv（已装 cv2 / numpy / Pillow）：

```powershell
& 'c:\Users\13005\Downloads\work\rocogi\suite\engines\sift\.venv\Scripts\python.exe' `
  'c:\Users\13005\Downloads\work\rocogi\game-data\import.py'
```

可选参数：

```powershell
# 给所有截图裁一个 ROI
... import.py --roi 100,80,640,360

# 调整模板尺寸上限 / 关闭自匹配自检
... import.py --max-template-size 1024 --no-self-check
```

退出码：有 failed 项为 1，否则 0（`needs-calibration` 计入 skipped，不算失败）。

## 去重与冲突

- 按内容 sha256 去重：同一分类内重复文件计入 skipped，并记录 `duplicateOf`。
- 同名不同内容：两个都保留；`frames` 记录 `nameCollisionWith`，模板输出文件名带 sha 前缀避免覆盖。
- 来源路径与处理时间逐条写进 JSON / `import-report.md`。

## 排查

| 现象 | 原因 | 处理 |
|---|---|---|
| `not a PNG file` | 扩展名是 .png 但内容不是 PNG | 另存为真正的 PNG |
| `missing dependency: cv2` | 用错解释器 | 用上面的 sift venv，不要用系统 Python |
| template `exceeds max` | 尺寸超过上限 | 缩小图片或调大 `--max-template-size` |
| map `needs-calibration` | 新分辨率 | 按 `calibration-*.json` 人工给 3 点，不要自动拟合 |
| pets `validate_input.py exit 1` | 资源缺文件/格式不符 | 看 `processed/pets/*-validator.json` 的 errors |

## 边界

- 只写 `game-data/processed/` 与 `game-data/import-report.md`。
- `incoming/` 全程只读。
- 不改 8787 / 8788 / 5173 / 8800 进程，不改 `webui/`。
- 不验证游戏窗口识别与实机截图链路。
