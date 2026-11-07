"""Import BWIKI (洛克王国:手游WIKI, wiki.biligame.com/rocom) battle data.

Authoritative source is the wiki's generated Lua data modules, not the SMW ask API
(which only covers ~37 skills).  Modules parsed:

    模块:PetData/SkillCatalog    788 skills: name/element/category/energy/power/target/desc
    模块:PetData/Core            596 pets: name/types/base stats/feature skill/evolution group
    模块:PetData/LearnsetCatalog 299 learnsets: learn nodes, bloodline nodes, stone skills
    模块:PetData/Learnsets       pet id -> learnset id
    模块:PetData/Evolution       242 evolution chains

Type effectiveness chart is scraped out of Widget:RestrainCalc.js (the wiki's own
calculator), so the multipliers match what the community site uses.

Outputs (into datasets/bwiki/):
    bwiki_battle.json   human/agent readable dump + provenance block
    bwiki_battle.db     sqlite: skill, pet, pet_skill, type_chart, evolution, meta
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import lua_literal as L  # noqa: E402

WIKI_DIR = ROOT / "datasets" / "bwiki" / "wiki"
OUT_DIR = ROOT / "datasets" / "bwiki"
RAW_DIR = OUT_DIR / "raw"

STAT_KEYS = {"at": "atk", "df": "def", "hp": "hp", "sa": "spatk", "sd": "spdef", "se": "speed"}
CATEGORY_ORDER = {"攻击": 0, "防御": 1, "状态": 2, "特性": 3}


def strip_suffix(name: str) -> str:
    return name[:-1] if name.endswith("系") else name


def load_module(name: str):
    path = WIKI_DIR / f"模块_PetData__{name}.txt"
    if not path.exists():
        raise SystemExit(f"missing module file: {path}")
    return L.loads_file(str(path))


def parse_type_chart() -> dict:
    js = (RAW_DIR / "Widget_RestrainCalc.js").read_text(encoding="utf-8")
    types = re.search(r"const typeList = \[(.*?)\];", js, re.S)
    type_list = re.findall(r"'([^']+)'", types.group(1)) if types else []
    chart = {}
    block = re.search(r"const typeEffectChart = \{(.*?)\n\s*\};", js, re.S)
    if not block:
        raise SystemExit("could not locate typeEffectChart in RestrainCalc widget")
    for atk_type, body in re.findall(r"'([^']+)':\s*\{(.*?)\}", block.group(1), re.S):
        entry = {}
        for rel in ("strong", "resist", "weak", "vulnerable"):
            m = re.search(rel + r":\s*\[(.*?)\]", body, re.S)
            entry[rel] = [t for t in re.findall(r"'([^']*)'", m.group(1)) if t] if m else []
        chart[atk_type] = entry
    # multiplier for attacker type -> defender type
    mult = {}
    for atk, rel in chart.items():
        for dfn in rel["strong"]:
            mult[f"{atk}|{dfn}"] = 2.0
        for dfn in rel["resist"]:
            mult[f"{atk}|{dfn}"] = 0.5
    return {"types": type_list, "relations": chart, "multipliers": mult}


def main() -> int:
    skills_raw = load_module("SkillCatalog")
    core = load_module("Core")
    learnsets_ref = load_module("Learnsets")
    learnset_catalog = load_module("LearnsetCatalog")
    evolution = load_module("Evolution")

    skills = {}
    for key, s in skills_raw.items():
        if key.startswith("_"):
            continue
        skills[key] = {
            "key": key,
            "id": s.get("id"),
            "name": s.get("name"),
            "element": strip_suffix(str(s.get("element") or "")),
            "category": s.get("category"),
            "damage_class": s.get("damage_class"),
            "energy": s.get("energy"),
            "power": s.get("power"),
            "target": s.get("target"),
            "icon_id": s.get("icon_id"),
            "desc": s.get("desc"),
        }

    def skill_refs_for(learnset_id):
        ls = learnset_catalog.get(learnset_id) or {}
        out = []
        for node in ls.get("ns") or []:
            if isinstance(node, dict):
                out.append({"skill": node.get("sk"), "level": node.get("lv"), "kind": "learn"})
        for node in ls.get("bs") or []:
            if isinstance(node, dict):
                out.append({"skill": node.get("sk"), "level": node.get("lv"),
                            "kind": "bloodline", "blood": node.get("bl")})
        for sid in ls.get("ss") or []:
            if isinstance(sid, str):
                out.append({"skill": sid, "level": None, "kind": "stone"})
        fs = ls.get("fs")
        if isinstance(fs, str):
            out.append({"skill": fs, "level": None, "kind": "feature"})
        return out

    pets = {}
    for key, p in core.items():
        if key.startswith("_"):
            continue
        pet_id = p.get("i") or key
        stats = p.get("st") or {}
        learnset_id = learnsets_ref.get(pet_id) or learnsets_ref.get(key)
        if isinstance(learnset_id, dict):
            learnset_id = learnset_id.get("id") or next(iter(learnset_id.values()), None)
        refs = skill_refs_for(learnset_id) if learnset_id else []
        fs = p.get("fs")
        if isinstance(fs, str) and not any(r["skill"] == fs for r in refs):
            refs.append({"skill": fs, "level": None, "kind": "feature"})
        pets[pet_id] = {
            "key": key,
            "id": pet_id,
            "name": p.get("n"),
            "title": p.get("t"),
            "form": p.get("f"),
            "class": p.get("c"),
            "stage": p.get("sg"),
            "types": [strip_suffix(str(t)) for t in (p.get("tp") or [])],
            "stats": {long: stats.get(short) for short, long in STAT_KEYS.items()},
            "total": sum(v for v in (stats.get(k) for k in STAT_KEYS) if isinstance(v, int)),
            "feature_skill": fs if isinstance(fs, str) else None,
            "evolution_groups": p.get("evg") or [],
            "learnset": learnset_id,
            "skills": refs,
            "description": p.get("d"),
            "height": p.get("ht"),
            "weight": p.get("wt"),
        }

    evolutions = []
    for key, evo in evolution.items():
        if key.startswith("_"):
            continue
        chain = []
        for node in evo.get("chain") or []:
            chain.append({
                "id": node.get("id"),
                "name": node.get("name"),
                "stage": node.get("stage"),
                "level": node.get("level"),
                "types": [strip_suffix(str(t)) for t in (node.get("types") or [])],
            })
        evolutions.append({"key": key, "chain": chain})

    chart = parse_type_chart()

    pet_skill = []
    for pet in pets.values():
        for ref in pet["skills"]:
            skill = skills.get(ref["skill"])
            if not skill:
                continue
            pet_skill.append({
                "pet_id": pet["id"],
                "skill_id": skill["id"],
                "skill_key": skill["key"],
                "skill_name": skill["name"],
                "element": skill["element"],
                "category": skill["category"],
                "damage_class": skill["damage_class"],
                "energy": skill["energy"],
                "power": skill["power"],
                "level": ref["level"],
                "kind": ref["kind"],
                "blood": ref.get("blood"),
            })

    meta = {
        "source": "https://wiki.biligame.com/rocom",
        "source_name": "洛克王国:手游WIKI (BWIKI)",
        "modules": [
            "模块:PetData/SkillCatalog", "模块:PetData/Core",
            "模块:PetData/LearnsetCatalog", "模块:PetData/Learnsets",
            "模块:PetData/Evolution", "Widget:RestrainCalc",
        ],
        "fetched_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "license": "CC BY-NC-SA 3.0 CN (bwiki default); cite the wiki when redistributing",
        "counts": {
            "skills": len(skills),
            "pets": len(pets),
            "pet_skill": len(pet_skill),
            "evolutions": len(evolutions),
            "type_relations": len(chart["multipliers"]),
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": meta,
        "type_chart": chart,
        "skills": list(skills.values()),
        "pets": list(pets.values()),
        "evolutions": evolutions,
    }
    (OUT_DIR / "bwiki_battle.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    db_path = OUT_DIR / "bwiki_battle.db"
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.executescript("""
    CREATE TABLE skill (skill_id INTEGER PRIMARY KEY, key TEXT UNIQUE, name TEXT, element TEXT,
        category TEXT, damage_class TEXT, energy INTEGER, power INTEGER, target TEXT,
        icon_id TEXT, desc TEXT);
    CREATE TABLE pet (pet_id TEXT PRIMARY KEY, key TEXT, name TEXT, title TEXT, form TEXT,
        class TEXT, stage INTEGER, types TEXT, hp INTEGER, atk INTEGER, def INTEGER,
        spatk INTEGER, spdef INTEGER, speed INTEGER, total INTEGER, feature_skill TEXT,
        learnset TEXT, evolution_groups TEXT, description TEXT);
    CREATE TABLE pet_skill (pet_id TEXT, skill_id INTEGER, skill_name TEXT, element TEXT,
        category TEXT, damage_class TEXT, energy INTEGER, power INTEGER,
        level INTEGER, kind TEXT, blood TEXT,
        PRIMARY KEY (pet_id, skill_id, kind, level, blood));
    CREATE TABLE type_chart (atk TEXT, def TEXT, multiplier REAL, PRIMARY KEY (atk, def));
    CREATE TABLE evolution (group_key TEXT, pet_id TEXT, name TEXT, stage INTEGER,
        level INTEGER, types TEXT, ord INTEGER);
    CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
    CREATE INDEX idx_pet_name ON pet(name);
    CREATE INDEX idx_pet_skill_name ON pet_skill(skill_name);
    """)
    cur.executemany(
        "INSERT INTO skill VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [(s["id"], s["key"], s["name"], s["element"], s["category"], s["damage_class"],
          s["energy"], s["power"], s["target"], s["icon_id"], s["desc"]) for s in skills.values()])
    cur.executemany(
        "INSERT INTO pet VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(p["id"], p["key"], p["name"], p["title"], p["form"], p["class"], p["stage"],
          ",".join(p["types"]), p["stats"]["hp"], p["stats"]["atk"], p["stats"]["def"],
          p["stats"]["spatk"], p["stats"]["spdef"], p["stats"]["speed"], p["total"],
          p["feature_skill"], p["learnset"], ",".join(p["evolution_groups"]), p["description"])
         for p in pets.values()])
    cur.executemany(
        "INSERT OR IGNORE INTO pet_skill VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [(r["pet_id"], r["skill_id"], r["skill_name"], r["element"], r["category"],
          r["damage_class"], r["energy"], r["power"], r["level"], r["kind"], r["blood"])
         for r in pet_skill])
    cur.executemany("INSERT OR REPLACE INTO type_chart VALUES (?,?,?)",
                    [(k.split("|")[0], k.split("|")[1], v) for k, v in chart["multipliers"].items()])
    for evo in evolutions:
        for n, node in enumerate(evo["chain"]):
            cur.execute("INSERT INTO evolution VALUES (?,?,?,?,?,?,?)",
                        (evo["key"], node["id"], node["name"], node["stage"], node["level"],
                         ",".join(node["types"]), n))
    cur.executemany("INSERT INTO meta VALUES (?,?)",
                    [(k, v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))
                     for k, v in meta.items()])
    con.commit()
    con.close()

    print(json.dumps(meta["counts"], ensure_ascii=False))
    print("wrote", OUT_DIR / "bwiki_battle.json", "and", db_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
