"""Quick Pokédex lookup for 洛克王国：世界.

Data comes from the same local NRC_AI SQLite database used by the battle
engine (461 pets / 491 skills / 206 evolution links). The lookup is read-only
and follows the field model documented by eachyczhang/-RocoTools:
element, stage, ability, six base stats and the skill list.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from .config import BATTLE_DB
from .adapters.petvariant import classify

ELEMENT_COLORS: Dict[str, str] = {
    "草": "#4EBC73",
    "水": "#3F89D9",
    "火": "#F26B4E",
    "地": "#C58B4A",
    "翼": "#7FB2E5",
    "冰": "#7FD6E0",
    "虫": "#9BBF4A",
    "幽": "#8A6FD1",
    "电": "#F2C94C",
    "机械": "#8A9BA8",
    "光": "#E8C25A",
    "恶": "#6B5B95",
    "武": "#C9603F",
    "毒": "#A15BB5",
    "普通": "#A0A8B0",
    "萌": "#F5A3C7",
    "幻": "#D96FE0",
    "龙": "#5B7FD9",
}

CATEGORY_COLORS: Dict[str, str] = {
    "物攻": "#FF9636",
    "魔攻": "#9446EC",
    "防御": "#3F89B4",
    "状态": "#2E7D32",
}

STAT_KEYS = [
    ("hp", "生命", "base_hp", "#FF5722"),
    ("atk", "物攻", "base_atk", "#FF9636"),
    ("spatk", "魔攻", "base_spatk", "#9446EC"),
    ("def", "物防", "base_def", "#3F89B4"),
    ("spdef", "魔防", "base_spdef", "#2E7D32"),
    ("speed", "速度", "base_speed", "#E91E63"),
]

SORT_FIELDS = {
    "id": "id",
    "total": "base_total",
    "hp": "base_hp",
    "speed": "base_speed",
    "atk": "base_atk",
    "spatk": "base_spatk",
    "def": "base_def",
    "spdef": "base_spdef",
}


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{BATTLE_DB}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _parse_ability(raw: str) -> Dict[str, str]:
    text = (raw or "").strip()
    if not text or text == ":":
        return {"name": "", "description": ""}
    for sep in (":", "："):
        if sep in text:
            name, description = text.split(sep, 1)
            return {"name": name.strip()[:24], "description": description.strip()}
    return {"name": text[:24], "description": ""}


def _stat_block(row: sqlite3.Row) -> List[Dict[str, Any]]:
    return [
        {
            "key": key,
            "label": label,
            "value": int(row[column] or 0),
            "color": color,
        }
        for key, label, column, color in STAT_KEYS
    ]


def _item(row: sqlite3.Row, detail: bool = False) -> Dict[str, Any]:
    ability = _parse_ability(row["ability"])
    element = row["element"] or "普通"
    data: Dict[str, Any] = {
        "id": row["id"],
        "spiritNo": row["spirit_no"] or f"NO.{row['id']:03d}",
        "name": row["name"],
        "element": element,
        "elementColor": ELEMENT_COLORS.get(element, "#A0A8B0"),
        "stage": row["evo_stage"] or "",
        "ability": ability,
        "total": int(row["base_total"] or 0),
        "stats": _stat_block(row),
    }
    if detail:
        data["statValues"] = {
            "hp": row["stat_hp"],
            "atk": row["stat_atk"],
            "spatk": row["stat_spatk"],
            "def": row["stat_def"],
            "spdef": row["stat_spdef"],
            "speed": row["stat_speed"],
        }
    else:
        data["statPreview"] = {key: int(row[column] or 0) for key, _, column, _ in STAT_KEYS}
    return data


def meta() -> Dict[str, Any]:
    conn = _conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM pokemon").fetchone()[0]
        skill_total = conn.execute("SELECT COUNT(*) FROM skill").fetchone()[0]
        elements = [
            {
                "name": row[0],
                "count": row[1],
                "color": ELEMENT_COLORS.get(row[0], "#A0A8B0"),
            }
            for row in conn.execute(
                "SELECT element, COUNT(*) c FROM pokemon GROUP BY element ORDER BY c DESC, element"
            ).fetchall()
        ]
        stages = [row[0] for row in conn.execute("SELECT DISTINCT evo_stage FROM pokemon WHERE evo_stage<>''")]
        categories = [
            {"name": row[0], "count": row[1], "color": CATEGORY_COLORS.get(row[0], "#6B7280")}
            for row in conn.execute("SELECT category, COUNT(*) c FROM skill GROUP BY category ORDER BY c DESC")
        ]
        stats = conn.execute(
            "SELECT MAX(base_total), MIN(base_total), ROUND(AVG(base_total)) FROM pokemon"
        ).fetchone()
        evolution_count = conn.execute("SELECT COUNT(*) FROM evolution").fetchone()[0]
    finally:
        conn.close()
    return {
        "total": total,
        "skillTotal": skill_total,
        "evolutionTotal": evolution_count,
        "elements": elements,
        "stages": stages,
        "categories": categories,
        "sortFields": list(SORT_FIELDS.keys()),
        "maxTotal": stats[0] or 0,
        "minTotal": stats[1] or 0,
        "avgTotal": stats[2] or 0,
        "source": "NRC_AI local sqlite · RocoTools 字段模型",
    }


def pokemon_list(
    query: str = "",
    element: str = "",
    stage: str = "",
    sort: str = "id",
    order: str = "asc",
    limit: int = 24,
    offset: int = 0,
) -> Dict[str, Any]:
    limit = max(1, min(limit, 120))
    offset = max(0, offset)
    where: List[str] = []
    params: List[Any] = []
    if query:
        where.append("(name LIKE ? OR ability LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])
    if element:
        where.append("element = ?")
        params.append(element)
    if stage:
        where.append("evo_stage = ?")
        params.append(stage)
    where_sql = f" WHERE {' AND '.join(where)}" if where else ""
    sort_column = SORT_FIELDS.get(sort, "id")
    direction = "DESC" if str(order).lower() == "desc" else "ASC"
    conn = _conn()
    try:
        total = conn.execute(f"SELECT COUNT(*) FROM pokemon{where_sql}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM pokemon{where_sql} ORDER BY {sort_column} {direction}, id ASC LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
    finally:
        conn.close()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_item(row) for row in rows],
    }


def pokemon_detail(name: str) -> Optional[Dict[str, Any]]:
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM pokemon WHERE name = ?", (name,)).fetchone()
        if not row:
            return None
        skills = [
            {
                "id": item["id"],
                "name": item["name"],
                "element": item["element"],
                "elementColor": ELEMENT_COLORS.get(item["element"], "#A0A8B0"),
                "category": item["category"],
                "categoryColor": CATEGORY_COLORS.get(item["category"], "#6B7280"),
                "power": int(item["power"] or 0),
                "energy": int(item["energy_cost"] or 0),
                "description": item["description"] or "",
            }
            for item in conn.execute(
                "SELECT s.* FROM skill s JOIN pokemon_skill ps ON ps.skill_id = s.id"
                " WHERE ps.pokemon_id = ? ORDER BY s.category, s.power DESC, s.name",
                (row["id"],),
            ).fetchall()
        ]
        evolution = [
            {
                "from": item["from_name"],
                "to": item["to_name"],
                "level": item["evo_level"],
                "condition": item["condition"] or "",
                "chainText": item["chain_text"] or "",
            }
            for item in conn.execute(
                "SELECT * FROM evolution WHERE from_name = ? OR to_name = ? ORDER BY evo_level, id",
                (name, name),
            ).fetchall()
        ]
        element = row["element"] or "普通"
        related = [
            _item(item)
            for item in conn.execute(
                "SELECT * FROM pokemon WHERE element = ? AND name <> ? ORDER BY base_total DESC LIMIT 6",
                (element, name),
            ).fetchall()
        ]
    finally:
        conn.close()
    pokemon = _item(row, detail=True)
    pokemon["elementCount"] = len(related)
    # 名字里的括号既可能是模型形态，也可能是配色（「被污染的样子」）。
    variant = classify(row["name"])
    pokemon["variant"] = {
        "colorType": variant["color_type"],
        "colorLabel": variant["color_label"],
        "colorEffect": variant["color_effect"],
        "formLabel": variant["form"],
        "formRaw": variant["form_raw"],
        "season": variant["season"],
        "isShiny": variant["is_shiny"],
        "isPolluted": variant["is_polluted"],
    }
    return {
        "pokemon": pokemon,
        "skills": skills,
        "evolution": evolution,
        "related": related,
    }


def skill_list(
    query: str = "",
    element: str = "",
    category: str = "",
    limit: int = 40,
    offset: int = 0,
) -> Dict[str, Any]:
    limit = max(1, min(limit, 120))
    offset = max(0, offset)
    where: List[str] = []
    params: List[Any] = []
    if query:
        where.append("(s.name LIKE ? OR s.description LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])
    if element:
        where.append("s.element = ?")
        params.append(element)
    if category:
        where.append("s.category = ?")
        params.append(category)
    where_sql = f" WHERE {' AND '.join(where)}" if where else ""
    conn = _conn()
    try:
        total = conn.execute(f"SELECT COUNT(*) FROM skill s{where_sql}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT s.*, COUNT(ps.pokemon_id) learnable FROM skill s"
            f" LEFT JOIN pokemon_skill ps ON ps.skill_id = s.id{where_sql}"
            " GROUP BY s.id ORDER BY s.category, s.power DESC, s.name LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
    finally:
        conn.close()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": row["id"],
                "name": row["name"],
                "element": row["element"],
                "elementColor": ELEMENT_COLORS.get(row["element"], "#A0A8B0"),
                "category": row["category"],
                "categoryColor": CATEGORY_COLORS.get(row["category"], "#6B7280"),
                "power": int(row["power"] or 0),
                "energy": int(row["energy_cost"] or 0),
                "description": row["description"] or "",
                "learnable": int(row["learnable"] or 0),
            }
            for row in rows
        ],
    }
