"""Build ``datasets/pvp/pvp_data.db`` from the cached community PvP datasets.

Inputs (see ``fetch_pvp.py``)::

    .cache/RokePvP-Calculator/   spirits.js, skills.js, type.js, spiritsPvP.js
    .cache/roco-cal/             skills_database/, pets_w_skill_json/, pets_trait_json/
    .cache/RoCo-PVP/             pokedex_pvp_usage.json

Output tables::

    meta        provenance: upstream commits, fetch date, row counts
    pet         653 spirit forms with six stats, traits and recommended PvP kit
    skill       damaging + status skills (power / energy / category / description)
    pet_skill   learnsets from roco-cal, plus the recommended PvP kit
    trait       trait rules with their structured battle effects
    type_chart  full 18x18 multiplier matrix (1.0 included)
    usage       public PvP usage: natures, IV spreads, bloodlines, skills

The type matrix is derived from the offensive lists in ``type.js``
(``strong`` x2 / ``weak`` x0.5).  The same file also carries defensive lists
(``resist`` / ``vulnerable``); they disagree with the offensive ones for a few
elements, so they are stored as reference only and never used by the importer.
``bwiki_battle.db`` ships 113 non-neutral pairs from the same wiki source, which
is used here as a cross-check.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "datasets" / "pvp" / ".cache"
OUT_DB = ROOT / "datasets" / "pvp" / "pvp_data.db"
BWIKI_DB = ROOT / "datasets" / "bwiki" / "bwiki_battle.db"

# 形态/配色两轴的口径来自上游 references/color-appearance.md，实现放在后端
# adapters/petvariant.py（运行时也要用，避免两份口径漂移）。
sys.path.insert(0, str(ROOT / "backend"))
from app.adapters.petvariant import COLOR_TYPES, classify, variant_summary  # noqa: E402

UPSTREAM = {
    "rokepvp": {
        "repo": "s422346963/RokePvP-Calculator",
        "commit": "624192b",
        "license": "见上游仓库",
    },
    "roco-cal": {
        "repo": "180sans/roco-cal",
        "commit": "1c58ec8",
        "license": "见上游仓库",
    },
    "rocopvp": {
        "repo": "sduwcdd/RoCo-PVP",
        "commit": "c6886de",
        "license": "见上游仓库",
    },
    "pets-gen": {
        "repo": "ElliottZhao666666/rocom-codex-pets-gen",
        "commit": "4ccce56",
        "license": "见上游仓库",
        "note": "references/color-appearance.md 定义形态与配色两轴、九类配色",
    },
}

CATEGORY_MAP = {"物理": "物攻", "魔法": "魔攻", "物攻": "物攻", "魔攻": "魔攻", "状态": "状态"}

# ---------------------------------------------------------------- JS parsing


def _balanced(src: str, start: int) -> str:
    depth = 0
    i = start
    in_str: Optional[str] = None
    while i < len(src):
        char = src[i]
        if in_str:
            if char == "\\":
                i += 2
                continue
            if char == in_str:
                in_str = None
        elif char in "\"'":
            in_str = char
        elif char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
            if depth == 0:
                return src[start : i + 1]
        i += 1
    return src[start:]


_IDENT_START = re.compile(r"[A-Za-z_$\u4e00-\u9fff]")
_IDENT_CHAR = re.compile(r"[A-Za-z0-9_$\u4e00-\u9fff]")


def js_to_json(src: str) -> str:
    """Turn the object/array literal dialect used by the JS data files into JSON.

    Handles bare keys, single quotes, and trailing commas outside strings.
    """
    out: List[str] = []
    i, n = 0, len(src)
    while i < n:
        char = src[i]
        if char in "\"'":
            quote = char
            buf = [quote]
            i += 1
            while i < n:
                ch = src[i]
                if ch == "\\" and i + 1 < n:
                    buf.append("\\\\")
                    buf.append(src[i + 1])
                    i += 2
                    continue
                if ch == quote:
                    i += 1
                    break
                buf.append('\\"' if ch == '"' else ch)
                i += 1
            if buf[0] == "'":
                buf[0] = '"'
            buf.append('"')
            out.append("".join(buf))
            continue
        if char == ",":
            k = i + 1
            while k < n and src[k] in " \t\r\n":
                k += 1
            if k < n and src[k] in "}]":
                i += 1
                continue
        if _IDENT_START.match(char):
            j = i
            while j < n and _IDENT_CHAR.match(src[j]):
                j += 1
            word = src[i:j]
            k = j
            while k < n and src[k] in " \t\r\n":
                k += 1
            if k < n and src[k] == ":" and word not in ("true", "false", "null"):
                out.append('"' + word + '"')
            else:
                out.append(word)
            i = j
            continue
        out.append(char)
        i += 1
    return "".join(out)


def load_js(path: Path, marker: str) -> Any:
    text = path.read_text(encoding="utf-8")
    start = text.index(marker) + len(marker)
    while start < len(text) and text[start] not in "[{":
        start += 1
    return json.loads(js_to_json(_balanced(text, start)))


# ---------------------------------------------------------------- helpers


FORM_RE = re.compile(r"[（(]([^）)]+)[）)]\s*$")


def split_form(name: str) -> Tuple[str, str]:
    text = str(name or "").strip()
    match = FORM_RE.search(text)
    if not match:
        return text, ""
    return text[: match.start()].strip(), match.group(1).strip()


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------- loaders


def load_spirits() -> List[Dict[str, Any]]:
    return load_js(CACHE / "RokePvP-Calculator" / "data" / "spirits.js", "const SPIRITS =")


def load_skills() -> List[Dict[str, Any]]:
    return load_js(CACHE / "RokePvP-Calculator" / "data" / "skills.js", "const SKILLS =")


def load_pvp_kits() -> Dict[str, Any]:
    return load_js(CACHE / "RokePvP-Calculator" / "data" / "spiritsPvP.js", "const SPIRITS_PVP =")


def load_types() -> Dict[str, Any]:
    return load_js(CACHE / "RokePvP-Calculator" / "data" / "type.js", "const TYPE_CHART =")


def load_roco_cal_pets() -> List[Dict[str, Any]]:
    rows = []
    for path in sorted((CACHE / "roco-cal" / "pets_w_skill_json").glob("*.json")):
        try:
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return rows


def load_roco_cal_skills() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in sorted((CACHE / "roco-cal" / "skills_database").glob("*.json")):
        rows.extend(json.loads(path.read_text(encoding="utf-8")))
    return rows


def load_roco_cal_traits() -> List[Dict[str, Any]]:
    """Read ``pets_trait_json/<category>/*.json``.

    Each file wraps a single trait as ``{"特性": {"名称": ..., "效果": ...}}``, so
    the trait name comes from the body, not from the top level key.
    """
    rows = []
    for path in sorted((CACHE / "roco-cal" / "pets_trait_json").rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        body = data.get("特性") if isinstance(data.get("特性"), dict) else {}
        if not body:
            continue
        rows.append({"name": body.get("名称") or path.stem, "category": path.parent.name, "body": body})
    return rows


def load_usage() -> Dict[str, Any]:
    path = CACHE / "RoCo-PVP" / "data" / "external" / "pokedex_pvp_usage.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- builders


def build_type_matrix(
    types: Dict[str, Any], bwiki_pairs: Dict[Tuple[str, str], float]
) -> Tuple[List[Tuple[str, str, float, str]], List[str], List[Tuple[str, str, float, float]]]:
    """Full 18x18 matrix from the offensive lists plus ``bwiki`` pairs.

    ``bwiki_battle.db`` ships the 113 non-neutral pairs parsed from the game wiki
    and is what the battle engine already uses, so it wins where the two
    sources disagree; the community table fills the pairs bwiki does not list.
    Every cell records which source produced it, and disagreements land in
    ``conflicts`` instead of being silently dropped.
    """
    names = sorted(types)
    matrix = {(a, d): 1.0 for a in names for d in names}
    source = {(a, d): "rokepvp" for a in names for d in names}
    warnings: List[str] = []
    for atk, spec in types.items():
        for target in spec.get("strong") or []:
            if (atk, target) in matrix:
                matrix[(atk, target)] = 2.0
        for target in spec.get("weak") or []:
            if (atk, target) in matrix:
                matrix[(atk, target)] = 0.5
        for target in spec.get("immune") or []:
            if (atk, target) in matrix:
                matrix[(atk, target)] = 0.0
    # Cross-check the defensive lists: they describe the same relation from the
    # other side, so they must agree with the offense table we just built.
    flip = {"resist": 0.5, "vulnerable": 2.0}
    for def_type, spec in types.items():
        for field, mult in flip.items():
            for atk_type in spec.get(field) or []:
                if (atk_type, def_type) in matrix and matrix[(atk_type, def_type)] != mult:
                    warnings.append(
                        f"{atk_type}->{def_type}: offense says {matrix[(atk_type, def_type)]}, "
                        f"defense '{field}' says {mult}"
                    )

    conflicts: List[Tuple[str, str, float, float]] = []
    for (atk, dfn), mult in bwiki_pairs.items():
        if (atk, dfn) not in matrix:
            warnings.append(f"bwiki pair {atk}->{dfn} ({mult}) is outside the 18 types")
            continue
        current = matrix[(atk, dfn)]
        if abs(current - mult) < 1e-9:
            source[(atk, dfn)] = "both" if abs(current - 1.0) > 1e-9 else "rokepvp"
            continue
        if abs(current - 1.0) < 1e-9:
            matrix[(atk, dfn)] = mult
            source[(atk, dfn)] = "bwiki"
            continue
        conflicts.append((atk, dfn, mult, current))
        matrix[(atk, dfn)] = mult
        source[(atk, dfn)] = "bwiki"
    rows = [(a, d, matrix[(a, d)], source[(a, d)]) for a in names for d in names]
    return rows, warnings, conflicts


def build_pets() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    spirits = load_spirits()
    kits = load_pvp_kits()
    rc_pets = load_roco_cal_pets()
    # The usage dump is keyed by internal id, and several ids share one display
    # name (alternate forms), so index it by name and keep the richest entry.
    usage = load_usage()["pets"]
    usage_by_name: Dict[str, Dict[str, Any]] = {}
    for item in usage.values():
        name = item.get("name") or ""
        if not name:
            continue
        current = usage_by_name.get(name)
        if current is None or len(item.get("skill_usage") or []) > len(current.get("skill_usage") or []):
            usage_by_name[name] = item

    rc_by_name: Dict[str, Dict[str, Any]] = {}
    for pet in rc_pets:
        rc_by_name.setdefault(pet["name"], pet)

    used_names = set()
    pets: List[Dict[str, Any]] = []
    seen_ids: Dict[str, int] = {}
    for spirit in spirits:
        name = spirit["n"]
        no = str(spirit.get("no") or "").strip()
        base, form = split_form(name)
        # 上游 ``st`` 是形态标签而不是进化阶段：除了「首领」以外都属于模型形态。
        stage_raw = str(spirit.get("st") or "").strip()
        boss = 1 if "首领" in stage_raw else 0
        if not form and stage_raw and not boss:
            form = stage_raw
        suffix = seen_ids.get(no, 0)
        seen_ids[no] = suffix + 1
        pet_id = f"{no}-{suffix}" if suffix else no
        rc = rc_by_name.get(name)
        if rc:
            used_names.add(name)
        kit = kits.get(name) or {}
        stats = [as_int(spirit.get(key)) for key in ("hp", "pa", "ma", "pd", "md", "sp")]
        total = sum(stats)
        usage_row = usage_by_name.get(name) or usage_by_name.get(base) or {}
        # The dump has no whole-pet appearance rate, so the pet level figure is
        # its most-used skill's share (labelled as such in the adapter/docs).
        top_skill = max((usage_row.get("skill_usage") or [{}]), key=lambda item: as_float(item.get("percent")))
        pets.append(
            {
                "pet_id": pet_id,
                "no": no,
                "name": name,
                "base_name": base,
                "form": form,
                "element1": spirit.get("a1") or "",
                "element2": spirit.get("a2") or "",
                "hp": stats[0],
                "atk": stats[1],
                "mag": stats[2],
                "def": stats[3],
                "res": stats[4],
                "spd": stats[5],
                "total": total,
                "trait": spirit.get("tr") or "",
                "trait_desc": spirit.get("tr_desc") or "",
                "stage_tag": "首领" if boss else "",
                "boss": boss,
                "sprite": spirit.get("img") or "",
                "pvp_natures": kit.get("n") or [],
                "pvp_iv": kit.get("v") or [],
                "pvp_skills": kit.get("s") or [],
                "rc_id": (rc or {}).get("id") or "",
                "rc_total": as_int((rc or {}).get("种族资质")),
                "usage_percent": as_float(top_skill.get("percent")),
                "usage_ratio": as_int(top_skill.get("ratio")),
            }
        )

    # roco-cal forms that RokePvP does not list (mostly cosmetic variants).
    extra: List[Dict[str, Any]] = []
    for pet in rc_pets:
        if pet["name"] in used_names:
            continue
        base, form = split_form(pet["name"])
        rc_id = str(pet.get("id") or "")
        extra.append(
            {
                "pet_id": f"rc-{rc_id}-{len(extra)}",
                "no": rc_id,
                "name": pet["name"],
                "base_name": base,
                "form": form,
                "element1": (pet.get("elements") or [""])[0],
                "element2": (pet.get("elements") or ["", ""])[1] if len(pet.get("elements") or []) > 1 else "",
                "hp": as_int(pet.get("hp")),
                "atk": as_int(pet.get("atk")),
                "mag": as_int(pet.get("mag")),
                "def": as_int(pet.get("def")),
                "res": as_int(pet.get("res")),
                "spd": as_int(pet.get("spd")),
                "total": as_int(pet.get("hp")) + as_int(pet.get("atk")) + as_int(pet.get("mag"))
                + as_int(pet.get("def")) + as_int(pet.get("res")) + as_int(pet.get("spd")),
                "trait": pet.get("特性") or "",
                "trait_desc": "",
                "stage_tag": "",
                "boss": 0,
                "sprite": "",
                "pvp_natures": [],
                "pvp_iv": [],
                "pvp_skills": [],
                "rc_id": rc_id,
                "rc_total": as_int(pet.get("种族资质")),
                "usage_percent": 0.0,
                "usage_ratio": 0,
            }
        )
    # 形态与配色是两条轴：括号里写「被污染的样子」时那是配色而不是模型形态。
    for pet in pets + extra:
        variant = classify(pet["name"], pet["form"])
        pet["base_name"] = variant["base_name"]
        pet["form"] = variant["form"]
        pet["form_raw"] = variant["form_raw"]
        pet["color_type"] = variant["color_type"]
        pet["color_label"] = variant["color_label"]
        pet["color_base"] = variant["color_base"]
        pet["color_effect"] = variant["color_effect"]
        pet["season"] = variant["season"]
        pet["is_shiny"] = 1 if variant["is_shiny"] else 0
        pet["is_polluted"] = 1 if variant["is_polluted"] else 0
    return pets, extra


def build_skills() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    base = load_skills()
    rc_skills = load_roco_cal_skills()
    rc_by_name: Dict[str, Dict[str, Any]] = {}
    for item in rc_skills:
        rc_by_name.setdefault(item["name"], item)

    skills: List[Dict[str, Any]] = []
    known = set()
    for item in base:
        name = item["n"]
        known.add(name)
        rc = rc_by_name.get(name) or {}
        skills.append(
            {
                "name": name,
                "element": item.get("a") or "",
                "category": CATEGORY_MAP.get(item.get("k") or "", item.get("k") or ""),
                "power": as_int(item.get("p")),
                "energy": as_int(item.get("c")),
                "combo": as_int(item.get("cb"), 1),
                "desc": item.get("desc") or "",
                "source": "rokepvp",
                "effect": rc.get("effect") or "",
                "buff_options": json.dumps(rc.get("buff_options") or [], ensure_ascii=False),
                "triggered": json.dumps(rc.get("triggered") or {}, ensure_ascii=False),
                "rc_power": as_int(rc.get("skill_power")),
            }
        )
    extra: List[Dict[str, Any]] = []
    for item in rc_skills:
        name = item["name"]
        if name in known:
            continue
        extra.append(
            {
                "name": name,
                "element": item.get("element") or "",
                "category": CATEGORY_MAP.get(item.get("type") or "", item.get("type") or "状态"),
                "power": as_int(item.get("skill_power")),
                "energy": as_int(item.get("cost")),
                "combo": as_int(item.get("combo"), 1),
                "desc": item.get("description") or "",
                "source": "roco-cal",
                "effect": item.get("effect") or "",
                "buff_options": json.dumps(item.get("buff_options") or [], ensure_ascii=False),
                "triggered": json.dumps(item.get("triggered") or {}, ensure_ascii=False),
                "rc_power": as_int(item.get("skill_power")),
            }
        )
    return skills, extra


def build_pet_skills(pets: Iterable[Dict[str, Any]]) -> List[Tuple[str, str, str, str]]:
    rc_pets = {pet["name"]: pet for pet in load_roco_cal_pets()}
    rows: List[Tuple[str, str, str, str]] = []
    for pet in pets:
        rc = rc_pets.get(pet["name"])
        if rc:
            for entry in rc.get("skills") or []:
                skill_name = str(entry.get("skill_name") or "").strip()
                if not skill_name:
                    continue
                rows.append((pet["name"], skill_name, str(entry.get("unlock_condition") or ""), "roco-cal"))
        for skill_name in pet.get("pvp_skills") or []:
            rows.append((pet["name"], str(skill_name), "PVP 推荐", "pvp-kit"))
    return rows


def build_traits() -> List[Tuple[str, str, str, str]]:
    rows = []
    for item in load_roco_cal_traits():
        body = item["body"] if isinstance(item["body"], dict) else {}
        name = body.get("名称") or item["name"]
        effect = body.get("效果") or ""
        rows.append((name, item["category"], effect, json.dumps(body.get("battle_effect") or {}, ensure_ascii=False)))
    return rows


def build_usage() -> List[Tuple[str, str, str, float, int, int]]:
    """Flatten the four usage lists, de-duplicated by (pet, kind, label).

    Several internal ids share one display name (alternate forms), so the same
    pet/kind/label can appear more than once; the highest share wins.
    """
    usage = load_usage()["pets"]
    merged: Dict[Tuple[str, str, str], Tuple[float, int, int]] = {}
    for row in usage.values():
        name = row.get("name") or ""
        if not name:
            continue
        for kind in ("nature_usage", "individual_value_usage", "bloodline_usage", "skill_usage"):
            for entry in row.get(kind) or []:
                key = (name, kind.replace("_usage", ""), str(entry.get("name") or ""))
                percent = as_float(entry.get("percent"))
                current = merged.get(key)
                if current is None or percent > current[0]:
                    merged[key] = (percent, as_int(entry.get("ratio")), as_int(entry.get("rank")))
    return [(name, kind, label, value[0], value[1], value[2]) for (name, kind, label), value in merged.items()]


# ---------------------------------------------------------------- write


SCHEMA = """
DROP TABLE IF EXISTS meta;
DROP TABLE IF EXISTS pet;
DROP TABLE IF EXISTS skill;
DROP TABLE IF EXISTS pet_skill;
DROP TABLE IF EXISTS trait;
DROP TABLE IF EXISTS type_chart;
DROP TABLE IF EXISTS type_conflict;
DROP TABLE IF EXISTS usage;

CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE pet(
    pet_id TEXT PRIMARY KEY,
    no TEXT, name TEXT, base_name TEXT, form TEXT,
    element1 TEXT, element2 TEXT,
    hp INTEGER, atk INTEGER, mag INTEGER, def INTEGER, res INTEGER, spd INTEGER,
    total INTEGER, trait TEXT, trait_desc TEXT, stage_tag TEXT, boss INTEGER,
    sprite TEXT, pvp_natures TEXT, pvp_iv TEXT, pvp_skills TEXT,
    rc_id TEXT, rc_total INTEGER, usage_percent REAL, usage_ratio INTEGER,
    form_raw TEXT, color_type TEXT, color_label TEXT, color_base TEXT,
    color_effect TEXT, season INTEGER, is_shiny INTEGER, is_polluted INTEGER
);
CREATE TABLE skill(
    name TEXT PRIMARY KEY, element TEXT, category TEXT, power INTEGER, energy INTEGER,
    combo INTEGER, desc TEXT, source TEXT, effect TEXT, buff_options TEXT,
    triggered TEXT, rc_power INTEGER
);
CREATE TABLE pet_skill(pet_name TEXT, skill_name TEXT, unlock TEXT, source TEXT);
CREATE TABLE trait(name TEXT PRIMARY KEY, category TEXT, effect TEXT, battle_effect TEXT);
CREATE TABLE type_chart(
    atk TEXT, def TEXT, multiplier REAL, source TEXT,
    PRIMARY KEY(atk, def)
);
CREATE TABLE type_conflict(atk TEXT, def TEXT, bwiki REAL, rokepvp REAL);
CREATE TABLE usage(pet_name TEXT, kind TEXT, label TEXT, percent REAL, ratio INTEGER, rank INTEGER);
"""


def load_bwiki_pairs() -> Dict[Tuple[str, str], float]:
    if not BWIKI_DB.exists():
        return {}
    conn = sqlite3.connect(f"file:{BWIKI_DB}?mode=ro", uri=True)
    try:
        return {(row[0], row[1]): row[2] for row in conn.execute("select atk, def, multiplier from type_chart")}
    finally:
        conn.close()


def main() -> int:
    if not CACHE.exists():
        print("cache missing: run fetch_pvp.py first", file=sys.stderr)
        return 1
    pets, extra_pets = build_pets()
    skills, extra_skills = build_skills()
    pet_skills = build_pet_skills(pets)
    traits = build_traits()
    bwiki_pairs = load_bwiki_pairs()
    type_rows, warnings, conflicts = build_type_matrix(load_types(), bwiki_pairs)
    ok_types = {name for name in load_types()}
    usage_rows = build_usage()

    OUT_DB.parent.mkdir(parents=True, exist_ok=True)
    # 每次重建：库是派生产物，留下旧表会让 CREATE TABLE 直接失败。
    for path in (OUT_DB, *(OUT_DB.with_name(OUT_DB.name + side) for side in ("-journal", "-wal", "-shm"))):
        if path.exists():
            path.unlink()
    conn = sqlite3.connect(OUT_DB)
    try:
        conn.executescript(SCHEMA)
        meta = {
            "built_at": "2026-11-07",
            "sources": json.dumps(UPSTREAM, ensure_ascii=False),
            "pets": str(len(pets) + len(extra_pets)),
            "skills": str(len(skills) + len(extra_skills)),
            "pet_skill": str(len(pet_skills)),
            "traits": str(len(traits)),
            "types": str(len(ok_types)),
            "type_pairs": str(len([row for row in type_rows if row[2] != 1.0])),
            "type_conflict": str(len(conflicts)),
            "type_source": "union: bwiki 优先，rokepvp 补缺",
            "usage": str(len(usage_rows)),
            "usage_note": "pet 级 usage_percent 取自该精灵主流技能的使用占比（上游未提供整只出场率）",
            "type_warnings": str(len(warnings)),
            "variant_source": "ElliottZhao666666/rocom-codex-pets-gen@4ccce56 references/color-appearance.md",
            "variant_note": "形态 form 与配色 color_type 是两条独立轴；括号里写「被污染的样子」按配色 pollution 处理，form 归一为空",
            "variant_counts": json.dumps(
                variant_summary([pet["name"] for pet in pets + extra_pets]), ensure_ascii=False
            ),
        }
        conn.executemany("INSERT INTO meta VALUES (?,?)", list(meta.items()))
        conn.executemany(
            "INSERT INTO pet VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    pet["pet_id"], pet["no"], pet["name"], pet["base_name"], pet["form"],
                    pet["element1"], pet["element2"], pet["hp"], pet["atk"], pet["mag"],
                    pet["def"], pet["res"], pet["spd"], pet["total"], pet["trait"],
                    pet["trait_desc"], pet["stage_tag"], pet["boss"], pet["sprite"],
                    json.dumps(pet["pvp_natures"], ensure_ascii=False),
                    json.dumps(pet["pvp_iv"], ensure_ascii=False),
                    json.dumps(pet["pvp_skills"], ensure_ascii=False),
                    pet["rc_id"], pet["rc_total"], pet["usage_percent"], pet["usage_ratio"],
                    pet["form_raw"], pet["color_type"], pet["color_label"], pet["color_base"],
                    pet["color_effect"], pet["season"], pet["is_shiny"], pet["is_polluted"],
                )
                for pet in pets + extra_pets
            ],
        )
        conn.executemany(
            "INSERT INTO skill VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    item["name"], item["element"], item["category"], item["power"], item["energy"],
                    item["combo"], item["desc"], item["source"], item["effect"],
                    item["buff_options"], item["triggered"], item["rc_power"],
                )
                for item in skills + extra_skills
            ],
        )
        conn.executemany("INSERT INTO pet_skill VALUES (?,?,?,?)", pet_skills)
        conn.executemany("INSERT OR REPLACE INTO trait VALUES (?,?,?,?)", traits)
        conn.executemany("INSERT INTO type_chart VALUES (?,?,?,?)", type_rows)
        conn.executemany("INSERT INTO type_conflict VALUES (?,?,?,?)", conflicts)
        conn.executemany("INSERT INTO usage VALUES (?,?,?,?,?,?)", usage_rows)
        conn.commit()
    finally:
        conn.close()

    summary = {
        "pets": len(pets) + len(extra_pets),        "pets_rokepvp": len(pets),
        "pets_roco_cal_only": len(extra_pets),
        "skills": len(skills) + len(extra_skills),
        "skills_rokepvp": len(skills),
        "skills_roco_cal_only": len(extra_skills),
        "pet_skill": len(pet_skills),
        "traits": len(traits),
        "usage": len(usage_rows),
        "type_pairs": len([row for row in type_rows if row[2] != 1.0]),
        "type_warnings": len(warnings),
        "db_bytes": OUT_DB.stat().st_size,
    }

    if BWIKI_DB.exists():
        bw = sqlite3.connect(f"file:{BWIKI_DB}?mode=ro", uri=True)
        try:
            bw_pets = {row[0] for row in bw.execute("select name from pet")}
            bw_skills = {row[0] for row in bw.execute("select name from skill")}
            bw_pairs = {(row[0], row[1]): row[2] for row in bw.execute("select atk, def, multiplier from type_chart")}
        finally:
            bw.close()
        mine = {name for name in (pet["name"] for pet in pets + extra_pets)}
        summary["bwiki_pets_covered"] = len(bw_pets & mine)
        summary["bwiki_pets_total"] = len(bw_pets)
        summary["bwiki_skills_covered"] = len(bw_skills & {item["name"] for item in skills + extra_skills})
        summary["bwiki_skills_total"] = len(bw_skills)
        covered = {(row[0], row[1]) for row in type_rows}
        summary["bwiki_type_pairs"] = len(bw_pairs)
        summary["bwiki_pairs_covered"] = len([key for key in bw_pairs if key in covered])
        summary["type_conflicts"] = [
            {"pair": f"{atk}->{dfn}", "bwiki": bw_mult, "rokepvp": pvp_mult}
            for atk, dfn, bw_mult, pvp_mult in conflicts
        ]

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if warnings:
        print("\n".join(warnings[:10]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
