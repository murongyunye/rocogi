# 洛克王国世界 · 战斗数据库（BWIKI 导入）

来源：**洛克王国:手游WIKI（BWIKI）** <https://wiki.biligame.com/rocom>
抓取时间：`2026-11-06T23:57+08:00`
抓取方式：MediaWiki API（`api.php?action=query&prop=revisions&rvprop=content`）+ `action=ask`（SMW）

## 为什么用 Lua 数据模块

精灵/技能页面本身只有模板调用（例如 `{{技能详情}}` 仅 8 字节），SMW 语义查询
（`[[技能名称::+]]`）只覆盖 **37 条**技能。真正的全量数据在站点的生成式 Lua 模块里，
所以本数据库直接从这些模块解析（`.tmp/lua_literal.py` 是一个纯字面量 Lua 解析器，
只处理 `return { ... }`，不执行任何 Lua 代码）：

| 模块 | 大小 | 内容 | 本库条目 |
| --- | --- | --- | --- |
| `模块:PetData/SkillCatalog` | 186 KB | 技能名称/属性/分类/耗能/威力/目标/描述 | **788** 技能 |
| `模块:PetData/Core` | 394 KB | 精灵名称/形态/系别/六维/特性技能/进化组 | **596** 精灵 |
| `模块:PetData/LearnsetCatalog` | 412 KB | 学习表：等级技能 + 18 条血脉技能 + 技能石 | **29818** 条精灵-技能关联 |
| `模块:PetData/Learnsets` | 17 KB | 精灵 ID → 学习表 ID | 映射表 |
| `模块:PetData/Evolution` | 114 KB | 进化链（可含分支、等级、系别） | **242** 链 / 581 节点 |
| `Widget:RestrainCalc.js` | 26 KB | 官方克制计算器的四向关系表 | **113** 条倍率关系 |

技能分类分布：攻击 349 / 特性 231 / 状态 156 / 防御 52。
特性（`category=特性`）在游戏里是精灵的固有被动，导入时单独保留（`pet.feature_skill`，
并在 `pet_skill.kind='feature'` 中可见），不会被当成可点击的技能按钮。

## 属性克制语义（来自 RestrainCalc 的四向表）

每种攻击属性给出四个列表，导入脚本按攻击方视角转成倍率：

- `strong` → ×2.0（攻击方克制防守方）
- `resist` → ×0.5（防守方抵抗攻击方）
- `weak` → 该属性**被**哪些属性克制（防守视角，不参与攻击倍率）
- `vulnerable` → 该属性**抵抗**哪些属性（防守视角，同上）

双属性防守时倍率相乘（`bwiki.type_multiplier()`）。

## 输出

- `bwiki_battle.json` — 可直接读的完整 dump（`meta` / `type_chart` / `skills` / `pets` / `evolutions`）
- `bwiki_battle.db` — SQLite，只读使用（`file:...?mode=ro&immutable=1`）

表结构：

```
skill(skill_id PK, key, name, element, category, damage_class, energy, power, target, icon_id, desc)
pet(pet_id PK, key, name, title, form, class, stage, types, hp, atk, def, spatk, spdef, speed,
    total, feature_skill, learnset, evolution_groups, description)
pet_skill(pet_id, skill_id, skill_name, element, category, damage_class, energy, power,
          level, kind, blood)   -- kind: learn | bloodline | stone | feature
type_chart(atk, def, multiplier)
evolution(group_key, pet_id, name, stage, level, types, ord)
meta(key, value)
```

## 重新生成

```powershell
# 1) 下载模块 wikitext（需要能连 wiki.biligame.com 的 TLS 环境）
.venv\Scripts\python.exe .tmp\bwiki_fetch.py
# 2) 解析 Lua 模块并写 json + db
.venv\Scripts\python.exe .tmp\bwiki_import2.py
```

## 使用位置

| 位置 | 用途 |
| --- | --- |
| `datasets/bwiki/bwiki_battle.db` | 数据本体 |
| `suite/engines/battle/bwiki.py` | suite 引擎侧只读访问器（`catalog` / `pokedex` / `skills` / `best_skill`） |
| `backend/app/adapters/bwiki.py` | 后端适配器（`/api/bwiki/*`） |
| `suite/config/engines/battle.toml` | `[battle] bwiki_db = "datasets/bwiki/bwiki_battle.db"`，优先于 `db = "assets/db/nrc.db"` |

**优先级**：名字能在本库解析时以本库为准（788 技能全量 + 官方克制表）；否则回退 `nrc.db`（NRC_AI 自带，491 技能）。

## 许可与署名

BWIKI 内容默认 **CC BY-NC-SA 3.0 CN**：非商业使用、相同方式共享、必须署名并保留本文件。
分发/二次开发时请保留来源链接与抓取时间，不要移除本 PROVENANCE.md。
