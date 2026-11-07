"""BWIKI battle knowledge adapter (primary battle data source).

The dataset is generated from the wiki's own Lua data modules - see
`datasets/bwiki/PROVENANCE.md` and `.tmp/bwiki_import2.py`:

    788 skills, 596 pets, 29818 pet-skill links, 242 evolution chains,
    113 type-effectiveness relations (Widget:RestrainCalc).

`nrc.db` (nrc_ai vendor) remains available as the legacy source; this adapter is
preferred whenever a name resolves here because it covers the full skill catalogue
and the community-maintained type chart.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Dict, Iterable, List, Optional

from ..config import BWIKI_DB
from .petvariant import classify

PREFERRED = "bwiki"


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{BWIKI_DB}?mode=ro&immutable=1", uri=True, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def available() -> bool:
    return BWIKI_DB.exists()


class BwikiData:
    """Read-only queries over the imported BWIKI battle database."""

    source = PREFERRED

    def catalog(self) -> Dict[str, Any]:
        if not available():
            return {"available": False, "db": str(BWIKI_DB)}
        con = _connect()
        try:
            counts = {
                table: con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("skill", "pet", "pet_skill", "type_chart", "evolution")
            }
            meta = {row["key"]: row["value"] for row in con.execute("SELECT key, value FROM meta")}
        finally:
            con.close()
        return {
            "available": True,
            "preferred": PREFERRED,
            "fallback": "nrc.db",
            "counts": counts,
            "source": meta.get("source"),
            "sourceName": meta.get("source_name"),
            "fetchedAt": meta.get("fetched_at"),
            "license": meta.get("license"),
            "modules": meta.get("modules"),
        }

    def pets(self, query: str = "", limit: int = 40) -> Dict[str, Any]:
        limit = max(1, min(limit, 200))
        con = _connect()
        try:
            sql = ("SELECT pet_id, name, title, types, stage, class, hp, atk, def, spatk, spdef, speed, total"
                   " FROM pet")
            params: List[Any] = []
            if query:
                sql += " WHERE name LIKE ? OR title LIKE ?"
                params += [f"%{query}%", f"%{query}%"]
            sql += " ORDER BY stage, pet_id LIMIT ?"
            params.append(limit)
            rows = con.execute(sql, params).fetchall()
            total = con.execute("SELECT COUNT(*) FROM pet").fetchone()[0]
        finally:
            con.close()
        return {"source": PREFERRED, "total": total, "items": [
            {
                "id": r["pet_id"], "name": r["name"], "title": r["title"],
                "types": (r["types"] or "").split(",") if r["types"] else [],
                "stage": r["stage"], "class": r["class"],
                "stats": {"hp": r["hp"], "atk": r["atk"], "def": r["def"],
                          "spatk": r["spatk"], "spdef": r["spdef"], "speed": r["speed"]},
                "total": r["total"],
            } for r in rows]}

    def pet(self, name: str) -> Dict[str, Any]:
        con = _connect()
        try:
            row = con.execute(
                "SELECT * FROM pet WHERE name = ? OR title = ? ORDER BY stage LIMIT 1",
                (name, name)).fetchone()
            if row is None:
                row = con.execute(
                    "SELECT * FROM pet WHERE name LIKE ? ORDER BY stage LIMIT 1",
                    (f"%{name}%",)).fetchone()
            if row is None:
                return {"source": PREFERRED, "found": False, "name": name}
            pet = dict(row)
            skills = [dict(s) for s in con.execute(
                "SELECT kind, level, skill_name, element, category, damage_class, energy, power, blood"
                " FROM pet_skill WHERE pet_id = ? ORDER BY kind, level", (pet["pet_id"],))]
            chain = []
            if pet.get("evolution_groups"):
                group = pet["evolution_groups"].split(",")[0]
                chain = [dict(n) for n in con.execute(
                    "SELECT pet_id, name, stage, level, types FROM evolution WHERE group_key = ? ORDER BY ord",
                    (group,))]
            feature = None
            if pet.get("feature_skill"):
                feature = con.execute("SELECT name, desc FROM skill WHERE key = ?",
                                      (pet["feature_skill"],)).fetchone()
        finally:
            con.close()
        return {
            "source": PREFERRED,
            "found": True,
            "pet": {
                "id": pet["pet_id"], "name": pet["name"], "title": pet["title"],
                "types": (pet["types"] or "").split(",") if pet["types"] else [],
                "stage": pet["stage"], "class": pet["class"],
                "stats": {"hp": pet["hp"], "atk": pet["atk"], "def": pet["def"],
                          "spatk": pet["spatk"], "spdef": pet["spdef"], "speed": pet["speed"]},
                "total": pet["total"], "description": pet["description"],
                # 形态与配色两轴：wiki 把「被污染的样子」写在 form 里，那其实是配色。
                "variant": classify(pet["title"] or pet["name"], pet.get("form") or ""),
            },
            "ability": {"name": feature["name"], "desc": feature["desc"]} if feature else None,
            "skills": skills,
            "evolution": chain,
        }

    def skills(self, query: str = "", element: str = "", category: str = "",
               limit: int = 40) -> Dict[str, Any]:
        limit = max(1, min(limit, 200))
        sql = ("SELECT name, element, category, damage_class, energy, power, target, desc FROM skill WHERE 1=1")
        params: List[Any] = []
        if query:
            sql += " AND name LIKE ?"
            params.append(f"%{query}%")
        if element:
            sql += " AND element = ?"
            params.append(element)
        if category:
            sql += " AND category = ?"
            params.append(category)
        sql += " ORDER BY power IS NULL, power DESC LIMIT ?"
        params.append(limit)
        con = _connect()
        try:
            rows = [dict(r) for r in con.execute(sql, params)]
            total = con.execute("SELECT COUNT(*) FROM skill").fetchone()[0]
        finally:
            con.close()
        return {"source": PREFERRED, "total": total, "count": len(rows), "items": rows}

    def type_multiplier(self, atk_element: str, def_types: Iterable[str]) -> float:
        atk = atk_element[:-1] if atk_element.endswith("系") else atk_element
        mult = 1.0
        con = _connect()
        try:
            for dfn in def_types or []:
                d = dfn[:-1] if dfn.endswith("系") else dfn
                row = con.execute("SELECT multiplier FROM type_chart WHERE atk = ? AND def = ?",
                                  (atk, d)).fetchone()
                if row:
                    mult *= float(row["multiplier"])
        finally:
            con.close()
        return mult

    def type_chart(self, atk_element: Optional[str] = None) -> Dict[str, Any]:
        sql = "SELECT atk, def, multiplier FROM type_chart"
        params: List[Any] = []
        if atk_element:
            sql += " WHERE atk = ?"
            params.append(atk_element[:-1] if atk_element.endswith("系") else atk_element)
        con = _connect()
        try:
            rows = [dict(r) for r in con.execute(sql + " ORDER BY atk, multiplier DESC", params)]
        finally:
            con.close()
        chart: Dict[str, Dict[str, List[str]]] = {}
        for r in rows:
            bucket = chart.setdefault(r["atk"], {"strong": [], "resist": []})
            bucket["strong" if float(r["multiplier"]) > 1 else "resist"].append(r["def"])
        return {"source": PREFERRED, "relations": len(rows), "chart": chart}

    def best_skill(self, pet: str, enemy_types: Optional[Iterable[str]] = None,
                   energy: Optional[int] = None) -> Dict[str, Any]:
        sheet = self.pet(pet)
        if not sheet.get("found"):
            return {"source": PREFERRED, "found": False, "pet": pet,
                    "hint": "name not in BWIKI data; fall back to nrc.db"}
        enemy = list(enemy_types or [])
        ranked = []
        for s in sheet["skills"]:
            if s["category"] != "攻击" or not s["power"]:
                continue
            if energy is not None and int(s["energy"] or 0) > int(energy):
                continue
            mult = self.type_multiplier(s["element"], enemy)
            eff = float(s["power"]) * mult
            ranked.append({**s, "multiplier": round(mult, 3),
                           "effectivePower": round(eff, 1),
                           "score": round(eff / max(int(s["energy"] or 1), 1), 2)})
        ranked.sort(key=lambda x: (-x["score"], -x["effectivePower"]))
        return {"source": PREFERRED, "found": bool(ranked), "pet": sheet["pet"]["name"],
                "enemyTypes": enemy, "energyBudget": energy,
                "best": ranked[0] if ranked else None, "ranked": ranked[:8]}
