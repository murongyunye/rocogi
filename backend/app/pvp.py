"""PvP balance lab.

The lab is a local research surface, not an official tier list. It combines
the local Pokédex with the NRC MCTS battle engine: compose a 6-pet team, read
heuristic composition metrics, then run a deterministic 6v6 simulation against
one of the preset teams. Data reference: Pacific-shark/roco-balance-lab.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from .config import BATTLE_DB
from . import dex

ROLE_LABELS = ("速攻", "物攻", "魔攻", "耐久", "均衡")
CATEGORY_LABELS = ("物攻", "魔攻", "防御", "状态")
TYPE_LABELS = {
    "normal": "普通",
    "fire": "火",
    "water": "水",
    "grass": "草",
    "electric": "电",
    "ice": "冰",
    "bug": "虫",
    "ghost": "幽",
    "steel": "机械",
    "light": "光",
    "dark": "恶",
    "fighting": "武",
    "poison": "毒",
    "fairy": "萌",
    "psychic": "幻",
    "dragon": "龙",
    "ground": "地",
    "flying": "翼",
    "wing": "翼",
    "rock": "岩",
}


def _type_label(raw: Any) -> str:
    text = str(raw or "").strip()
    return TYPE_LABELS.get(text.lower(), text or "普通")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{BATTLE_DB}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _role(row: sqlite3.Row) -> str:
    hp = int(row["base_hp"] or 0)
    atk = int(row["base_atk"] or 0)
    spatk = int(row["base_spatk"] or 0)
    df = int(row["base_def"] or 0)
    spdef = int(row["base_spdef"] or 0)
    speed = int(row["base_speed"] or 0)
    bulk = hp + df + spdef
    if bulk >= 290 and speed < 95:
        return "耐久"
    if speed >= 100 and max(atk, spatk) >= 100:
        return "速攻"
    if spatk > atk + 12:
        return "魔攻"
    if atk > spatk + 12:
        return "物攻"
    return "均衡"


def _member(row: sqlite3.Row, skills: List[Dict[str, Any]]) -> Dict[str, Any]:
    element = row["element"] or "普通"
    return {
        "name": row["name"],
        "spiritNo": row["spirit_no"] or f"NO.{row['id']:03d}",
        "element": element,
        "elementColor": dex.ELEMENT_COLORS.get(element, "#A0A8B0"),
        "stage": row["evo_stage"] or "",
        "role": _role(row),
        "total": int(row["base_total"] or 0),
        "speed": int(row["base_speed"] or 0),
        "bulk": int(row["base_hp"] or 0) + int(row["base_def"] or 0) + int(row["base_spdef"] or 0),
        "stats": {
            "hp": int(row["base_hp"] or 0),
            "atk": int(row["base_atk"] or 0),
            "spatk": int(row["base_spatk"] or 0),
            "def": int(row["base_def"] or 0),
            "spdef": int(row["base_spdef"] or 0),
            "speed": int(row["base_speed"] or 0),
        },
        "skills": skills,
    }


def _skills_for(conn: sqlite3.Connection, pokemon_id: int, limit: int = 4) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT s.name, s.element, s.category, s.power, s.energy_cost FROM skill s"
        " JOIN pokemon_skill ps ON ps.skill_id = s.id WHERE ps.pokemon_id = ?"
        " ORDER BY s.power DESC, s.name LIMIT ?",
        (pokemon_id, limit),
    ).fetchall()
    return [
        {
            "name": row["name"],
            "element": row["element"],
            "category": row["category"],
            "power": int(row["power"] or 0),
            "energy": int(row["energy_cost"] or 0),
        }
        for row in rows
    ]


# Name resolution tolerates the form suffixes used by the BWIKI import.
# The dex stores alternate forms as `千棘盔（本来的样子）`, while NRC preset
# teams keep the bare name `千棘盔`. Exact matches win; otherwise the bare
# name is matched against the first form, then a unique prefix match.


def _strip_form(name: str) -> str:
    text = str(name or "").strip()
    for left, right in (("（", "）"), ("(", ")")):
        if left in text and right in text:
            head = text.split(left, 1)[0].strip()
            if head:
                return head
    return text


def _resolve_row(conn: sqlite3.Connection, name: str) -> Optional[sqlite3.Row]:
    raw = str(name or "").strip()
    if not raw:
        return None
    row = conn.execute("SELECT * FROM pokemon WHERE name = ?", (raw,)).fetchone()
    if row:
        return row
    base = _strip_form(raw)
    if base != raw:
        row = conn.execute("SELECT * FROM pokemon WHERE name = ?", (base,)).fetchone()
        if row:
            return row
    for pattern in (f"{base}（%", f"{base}(%"):
        row = conn.execute(
            "SELECT * FROM pokemon WHERE name LIKE ? ORDER BY id LIMIT 1", (pattern,)
        ).fetchone()
        if row:
            return row
    rows = conn.execute(
        "SELECT * FROM pokemon WHERE name LIKE ? ORDER BY id LIMIT 3", (f"%{base}%",)
    ).fetchall()
    if len(rows) == 1:
        return rows[0]
    return None


def _team_names(names: List[str]) -> List[str]:
    cleaned = [str(name).strip() for name in names if str(name).strip()]
    if not cleaned:
        raise ValueError("阵容为空，请至少选择一只精灵")
    if len(cleaned) > 6:
        raise ValueError(f"阵容最多 6 只精灵，当前填写了 {len(cleaned)} 只")
    duplicates = sorted({name for name in cleaned if cleaned.count(name) > 1})
    if duplicates:
        raise ValueError(f"阵容存在重复精灵: {', '.join(duplicates)}")
    return cleaned


def analyze(names: List[str]) -> Dict[str, Any]:
    names = _team_names(names)
    conn = _conn()
    try:
        rows = []
        unknown: List[str] = []
        for name in names:
            row = _resolve_row(conn, name)
            if row:
                rows.append(row)
            else:
                unknown.append(name)
        if unknown:
            raise ValueError(f"图鉴中不存在: {', '.join(unknown)}")
        members = [_member(row, _skills_for(conn, int(row["id"]))) for row in rows]
        category_rows = conn.execute(
            "SELECT s.category, COUNT(DISTINCT s.id) c FROM skill s"
            " JOIN pokemon_skill ps ON ps.skill_id = s.id"
            " JOIN pokemon p ON p.id = ps.pokemon_id"
            f" WHERE p.name IN ({','.join('?' for _ in rows)}) GROUP BY s.category",
            [row["name"] for row in rows],
        ).fetchall() if rows else []
    finally:
        conn.close()

    if not members:
        raise ValueError("阵容为空或精灵不存在")

    elements = [member["element"] for member in members]
    unique_elements = sorted(set(elements), key=elements.index)
    speeds = [member["speed"] for member in members]
    totals = [member["total"] for member in members]
    bulks = [member["bulk"] for member in members]
    roles = [member["role"] for member in members]
    skill_categories = {row["category"]: int(row["c"] or 0) for row in category_rows}

    avg_total = round(sum(totals) / len(totals), 1)
    avg_speed = round(sum(speeds) / len(speeds), 1)
    avg_bulk = round(sum(bulks) / len(bulks), 1)
    duplicate_elements = len(elements) - len(unique_elements)
    physical = sum(1 for member in members if member["stats"]["atk"] > member["stats"]["spatk"])
    special = sum(1 for member in members if member["stats"]["spatk"] > member["stats"]["atk"])
    fast = sum(1 for speed in speeds if speed >= 100)
    coverage = len([value for value in skill_categories.values() if value > 0])
    score = round(
        min(1.0, avg_total / 650) * 35
        + min(1.0, avg_speed / 140) * 25
        + (len(unique_elements) / max(len(members), 1)) * 20
        + (coverage / 4) * 10
        + min(1.0, avg_bulk / 300) * 10,
        1,
    )

    notes: List[str] = []
    if duplicate_elements:
        notes.append(f"阵容有 {duplicate_elements} 个重复属性，注意属性覆盖")
    if fast == 0:
        notes.append("没有速度线过 100 的成员，容易被先手压制")
    if physical and not special:
        notes.append("物攻偏向明显，缺少魔攻突破")
    if special and not physical:
        notes.append("魔攻偏向明显，缺少物攻突破")
    if not skill_categories.get("状态"):
        notes.append("缺少状态技能，续航与控场手段偏少")
    if not notes:
        notes.append("阵容结构较均衡，建议再用多套对手队伍验证")

    return {
        "ok": True,
        "members": members,
        "metrics": {
            "count": len(members),
            "avgTotal": avg_total,
            "avgSpeed": avg_speed,
            "maxSpeed": max(speeds),
            "avgBulk": avg_bulk,
            "elements": unique_elements,
            "duplicateElements": duplicate_elements,
            "physical": physical,
            "special": special,
            "fast": fast,
            "skillCategories": skill_categories,
            "coverage": coverage,
            "score": score,
        },
        "roles": {role: roles.count(role) for role in ROLE_LABELS if roles.count(role)},
        "notes": notes,
    }


def observations(limit: int = 8) -> Dict[str, Any]:
    limit = max(3, min(limit, 20))
    conn = _conn()
    try:
        total = [
            dict(row)
            for row in conn.execute(
                "SELECT name, element, evo_stage, base_total total, base_speed speed"
                " FROM pokemon ORDER BY base_total DESC, id LIMIT ?",
                (limit,),
            ).fetchall()
        ]
        speed = [
            dict(row)
            for row in conn.execute(
                "SELECT name, element, evo_stage, base_speed speed, base_total total"
                " FROM pokemon ORDER BY base_speed DESC, base_total DESC LIMIT ?",
                (limit,),
            ).fetchall()
        ]
        bulk = [
            dict(row)
            for row in conn.execute(
                "SELECT name, element, evo_stage,"
                " (base_hp + base_def + base_spdef) bulk, base_total total"
                " FROM pokemon ORDER BY bulk DESC, base_total DESC LIMIT ?",
                (limit,),
            ).fetchall()
        ]
    finally:
        conn.close()
    for group in (total, speed, bulk):
        for item in group:
            item["elementColor"] = dex.ELEMENT_COLORS.get(item["element"], "#A0A8B0")
    return {"topTotal": total, "topSpeed": speed, "topBulk": bulk}


def meta(battle: Any) -> Dict[str, Any]:
    presets = battle.presets()
    opponents = []
    for preset in presets:
        team = battle.preset_team(preset["id"])
        opponents.append({**preset, "members": team.get("members", []) if team.get("ok") else []})
    return {
        "dex": dex.meta(),
        "opponents": opponents,
        "observations": observations(8),
        "disclaimer": "本地研究用启发式，不是官方强度榜；MCTS 单局结果会受模拟次数与回合上限影响。",
    }


def _custom_enemy(name: str) -> Dict[str, Any]:
    conn = _conn()
    try:
        row = _resolve_row(conn, name)
        if not row:
            raise ValueError(f"对手精灵不存在: {name}")
        member = _member(row, _skills_for(conn, int(row["id"])))
    finally:
        conn.close()
    member["type"] = member["element"]
    return {"ok": True, "id": name, "members": [member]}


def matchup(
    battle: Any,
    names: List[str],
    opponent: str = "wing",
    simulations: int = 60,
    max_turns: int = 30,
) -> Dict[str, Any]:
    names = _team_names(names)
    opponent = str(opponent or "").strip()
    if not opponent:
        raise ValueError("请选择对手队伍或精灵")
    analysis = analyze(names)
    if opponent in ("toxic", "wing"):
        enemy = battle.preset_team(opponent)
    else:
        enemy = _custom_enemy(opponent)
    if not enemy.get("ok"):
        return {"ok": False, "error": enemy.get("error") or "对手队伍不可用", "player": analysis}
    for member in enemy.get("members", []):
        element = _type_label(member.get("type") or member.get("element"))
        member["element"] = element
        member["elementColor"] = dex.ELEMENT_COLORS.get(element, "#ec4899")
    result = battle.simulate(
        [{"name": name} for name in names],
        opponent,
        simulations,
        max_turns,
    )
    if not result.get("ok"):
        return {"ok": False, "error": result.get("error") or "战斗引擎不可用", "player": analysis, "enemy": enemy}
    return {
        "ok": True,
        "player": analysis,
        "opponent": opponent,
        "enemy": enemy,
        "battle": result,
        "winner": result.get("winner"),
        "turns": result.get("turns"),
        "durationMs": result.get("durationMs"),
        "logs": result.get("logs", []),
    }
