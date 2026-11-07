# PvP 社区数据集（datasets/pvp）

`pvp_data.db` 由 `datasets/tools/pvp/fetch_pvp.py` + `import_pvp.py` 从三个公开仓的**固定提交**生成。
仓库内只保留生成结果与生成脚本；上游原始文件缓存在 `datasets/pvp/.cache/`（已 gitignore，可随时重下）。

## 来源

| 仓库 | 提交 | 取用的数据 | 用途 |
| --- | --- | --- | --- |
| [s422346963/RokePvP-Calculator](https://github.com/s422346963/RokePvP-Calculator) | `624192b` | `data/spirits.js`（653 条形态）、`data/skills.js`（373 条技能）、`data/type.js`（18 属性相克）、`data/spiritsPvP.js`（332 条推荐配置） | 精灵六维与形态、技能威力/能耗/连击、属性矩阵、推荐性格与个体 |
| [180sans/roco-cal](https://github.com/180sans/roco-cal) | `1c58ec8` | `src-tauri/resources/rocodatebase/data/{skills_database,pets_w_skill_json,pets_trait_json}` | 补齐技能（607 条）、解锁条件与血脉技能、特性效果文案（221 条结构化特性） |
| [sduwcdd/RoCo-PVP](https://github.com/sduwcdd/RoCo-PVP) | `c6886de` | `data/external/pokedex_pvp_usage.json` | 公开使用率：性格 / 个体 / 血脉 / 技能四类 |
| [ElliottZhao666666/rocom-codex-pets-gen](https://github.com/ElliottZhao666666/rocom-codex-pets-gen) | `4ccce56` | `references/color-appearance.md` | 形态 / 配色两轴口径（九类配色与互斥规则），不是数据行，只作为分类依据 |

## 形态与配色是两条轴

`references/color-appearance.md` 把「模型形态」与「颜色类型」分开：形态由唯一实体 + `form_asset` 决定
（如「本来的样子」「看守果实的样子」），颜色类型是另一条独立轴，共九类：

| 中文 | `color_type` | 基础目录 | 效果 |
| --- | --- | --- | --- |
| 常规 | `normal` | `normal` | 无 |
| 常规炫彩 | `normal_glassy` | `normal` | 配色 + 粒子 |
| 黑白炫彩 | `normal_black_white` | `normal` | 黑白预设 |
| 赛季限定炫彩 | `normal_seasonal` | `normal` | 赛季预设 |
| 污染 | `pollution` | `normal` | 原污染效果 |
| 异色 | `shiny` | `shiny` | 无 |
| 异色炫彩 | `shiny_glassy` | `shiny` | 配色 + 粒子 |
| 异色赛季炫彩 | `shiny_seasonal` | `shiny` | 赛季预设 |
| 异色黑白炫彩 | `shiny_black_white` | `shiny` | 黑白预设 |

约束：污染与异色互斥且不与其他炫彩叠加；黑白与异色黑白是两类；异色必须来自 `shiny` 素材。

上游三个仓都只有名字里的括号，没有颜色轴。导入时用 `backend/app/adapters/petvariant.py::classify`
统一判定：括号里写「被污染的样子」时 `color_type=pollution` 且 `form` 归一为空（旧版把污染当成形态存），
真正的模型形态（「磨损的样子」「春天的样子」…）继续留在 `form`；同时修正 `stage_tag` —— rokepvp 的 `st`
字段是形态标签，只有「首领」才算阶段标记。配色分布写进 `meta.variant_counts`，界面按 `color_type` 上色，
不再与形态、阶段混在一起。

## 表结构（`pvp_data.db`）

| 表 | 行数 | 说明 |
| --- | --- | --- |
| `pet` | 674 | 每行一只形态：`id/no/name/base_name/form/types_json/stats_json/total/stage_tag/boss/trait/usage_percent`，另有配色轴 `form_raw/color_type/color_label/color_base/color_effect/season/is_shiny/is_polluted` |
| `skill` | 608 | `name/element/category(物攻/魔攻/状态/防御)/power/energy/combo/description/source` |
| `pet_skill` | 28781 | 精灵—技能关联，含 `unlock` 解锁条件与 `learn_source` |
| `trait` | 221 | `name/category/effect/battle_effect_json`（roco-cal 的结构化效果） |
| `type_chart` | 324 | 18×18 完整矩阵，`source` 记 `bwiki`/`both`/`rokepvp` |
| `type_conflict` | 8 | 两套上游表冲突的格子（bwiki ×2.0 vs rokepvp ×0.5），保留供审计 |
| `usage` | 41276 | `(pet_name, kind, label, percent, ratio, rank)`，kind 为 nature/individual_value/bloodline/skill |
| `meta` | — | 生成时间、来源提交、类型来源说明、使用率口径说明 |

## 已知口径差异

- **属性相克**：`type.js` 的进攻表与防守表互相矛盾（126 处）。本项目只信进攻表，并与 `datasets/bwiki/bwiki_battle.db` 的 113 对非中性关系取并集、bwiki 优先；8 条冲突写进 `type_conflict` 便于复核。
- **使用率**：上游按内部 id 存，865 条对应 546 个名字（245 组重名）。导入时按名字归并、保留条目最多的那条记录；`pet.usage_percent` 是「该精灵主流技能的最高使用率」，不是整只出场率（上游没有出场率字段）。
- **形态**：rokepvp 以形态为行（「首领」「蓬松的样子」等），roco-cal 只有基名；两边同名不同形态时以 rokepvp 为准，roco-cal 独有形态补 `rc-<id>-<n>`。
- **阶段与形态**：rokepvp 的 `st` 是形态标签而不是进化阶段，只有含「首领」时才写进 `stage_tag`，其余并入 `form`；不要再拿 `stage_tag` 表示形态。
- **血脉技能**（`unlock` 含「血脉」）来自 roco-cal 的全量技能表，属于「可学但需条件」，界面里标为技能池而非当前配招。

## 重建

```powershell
cd <repo>
.venv\Scripts\python.exe datasets\tools\pvp\fetch_pvp.py     # 联网拉三个仓的固定提交
.venv\Scripts\python.exe datasets\tools\pvp\import_pvp.py    # 生成 datasets/pvp/pvp_data.db
```

导入脚本结尾会打印一份 JSON 摘要（各类行数、bwiki 覆盖率、类型冲突数），便于回归对比。
