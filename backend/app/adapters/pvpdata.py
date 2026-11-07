"""Community PvP dataset adapter.

``datasets/pvp/pvp_data.db`` is built by ``datasets/tools/pvp/{fetch,import}_pvp.py``
from three community repositories (see ``datasets/pvp/PROVENANCE.md``):

    s422346963/RokePvP-Calculator -- 653 spirit forms, skill power/energy,
                                     offensive type table, recommended kits
    180sans/roco-cal              -- per-pet learnsets, skill effects, trait rules
    sduwcdd/RoCo-PVP              -- public PvP usage (natures, IVs, skills)

What it adds on top of ``bwiki_battle.db``: real power / energy / combo numbers,
trait battle effects, and usage statistics.  The type matrix is a union of the
community table and the wiki table (``bwiki`` wins on the 8 pairs where they
disagree; the disagreements are recorded in ``type_conflict``).
"""
from __future__ import annotations

import json
import re
import sqlite3
from typing import Any, Dict, Iterable, List, Optional

from ..config import PVP_DB

SOURCE = "pvp-community"

_FORM_RE = re.compile(r"[（(]([^）)]+)[）)]\s*$")


def available() -> bool:
    return PVP_DB.exists()


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{PVP_DB}?mode=ro&immutable=1", uri=True, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def strip_form(name: str) -> str:
    text = str(name or "").strip()
    match = _FORM_RE.search(text)
    return text[: match.start()].strip() if match else text


def _json(value: Any, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


class PvpData:
    """Read-only queries over the imported community PvP database."""

    source = SOURCE

    # ---------------------------------------------------------------- meta

    def summary(self) -> Dict[str, Any]:
        if not available():
            return {"available": False, "db": str(PVP_DB)}
        con = _connect()
        try:
            meta = {row["key"]: row["value"] for row in con.execute("SELECT key, value FROM meta")}
            counts = {
                table: con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("pet", "skill", "pet_skill", "trait", "type_chart", "usage")
            }
            by_category = {
                row["category"]: row["n"]
                for row in con.execute("SELECT category, COUNT(*) AS n FROM skill GROUP BY category")
            }
            conflicts = [dict(row) for row in con.execute("SELECT * FROM type_conflict")]
            variant_counts = {
                row["color_type"]: row["n"]
                for row in con.execute(
                    "SELECT color_type, COUNT(*) AS n FROM pet GROUP BY color_type ORDER BY n DESC")
            }
        finally:
            con.close()
        return {
            "available": True,
            "db": str(PVP_DB),
            "source": SOURCE,
            "builtAt": meta.get("built_at"),
            "sources": _json(meta.get("sources"), {}),
            "typeSource": meta.get("type_source"),
            "usageNote": meta.get("usage_note"),
            "counts": counts,
            "skillsByCategory": by_category,
            "typePairs": int(meta.get("type_pairs") or 0),
            "typeConflicts": conflicts,
            "variantCounts": variant_counts,
            "variantNote": meta.get("variant_note"),
            "variantSource": meta.get("variant_source"),
        }

    # ---------------------------------------------------------------- lookup

    def resolve(self, name: str) -> Optional[sqlite3.Row]:
        """Find one row: exact name, then form-stripped base, then prefix."""
        if not available():
            return None
        con = _connect()
        try:
            row = con.execute("SELECT * FROM pet WHERE name = ? ORDER BY boss, pet_id LIMIT 1", (name,)).fetchone()
            if row is not None:
                return row
            base = strip_form(name)
            row = con.execute(
                "SELECT * FROM pet WHERE base_name = ? ORDER BY boss, pet_id LIMIT 1", (base,)).fetchone()
            if row is not None:
                return row
            rows = con.execute(
                "SELECT * FROM pet WHERE name LIKE ? OR base_name LIKE ? ORDER BY boss, pet_id LIMIT 2",
                (f"{base}%", f"%{base}%")).fetchall()
            if len(rows) == 1:
                return rows[0]
            return None
        finally:
            con.close()

    # ---------------------------------------------------------------- type chart

    def _chart(self, con: sqlite3.Connection) -> Dict[tuple, float]:
        return {
            (row["atk"], row["def"]): float(row["multiplier"])
            for row in con.execute("SELECT atk, def, multiplier FROM type_chart")
        }

    def _defensive(self, chart: Dict[tuple, float], types: Iterable[str]) -> Dict[str, Any]:
        """Incoming damage multipliers against a defender with ``types``."""
        defenders = [t for t in types if t]
        weak: List[Dict[str, Any]] = []
        resist: List[Dict[str, Any]] = []
        immune: List[str] = []
        for atk in sorted({key[0] for key in chart}):
            mult = 1.0
            for dfn in defenders:
                mult *= chart.get((atk, dfn), 1.0)
            if mult > 1.0:
                weak.append({"type": atk, "multiplier": round(mult, 2)})
            elif mult < 1.0:
                if mult == 0.0:
                    immune.append(atk)
                resist.append({"type": atk, "multiplier": round(mult, 2)})
        weak.sort(key=lambda row: -row["multiplier"])
        resist.sort(key=lambda row: row["multiplier"])
        return {"weak": weak, "resist": resist, "immune": immune}

    def _offensive(self, chart: Dict[tuple, float], types: Iterable[str]) -> Dict[str, List[Dict[str, Any]]]:
        strong: List[Dict[str, Any]] = []
        resisted: List[Dict[str, Any]] = []
        for dfn in sorted({key[1] for key in chart}):
            mult = 1.0
            for atk in types:
                mult *= chart.get((atk, dfn), 1.0)
            if mult > 1.0:
                strong.append({"type": dfn, "multiplier": round(mult, 2)})
            elif mult < 1.0:
                resisted.append({"type": dfn, "multiplier": round(mult, 2)})
        strong.sort(key=lambda row: -row["multiplier"])
        return {"strong": strong, "resisted": resisted}

    def multipliers_against(self, defender_types: Iterable[str]) -> Dict[str, Any]:
        if not available():
            return {"available": False}
        con = _connect()
        try:
            chart = self._chart(con)
        finally:
            con.close()
        return {"available": True, "types": list(defender_types),
                **self._defensive(chart, defender_types)}

    # ---------------------------------------------------------------- profile

    def profile(self, name: str, usage_limit: int = 6) -> Dict[str, Any]:
        if not available():
            return {"available": False, "found": False, "name": name}
        con = _connect()
        try:
            row = self.resolve(name)
            if row is None:
                return {"available": True, "found": False, "name": name}
            chart = self._chart(con)
            pet = dict(row)
            stats = {
                "hp": pet["hp"], "atk": pet["atk"], "mag": pet["mag"],
                "def": pet["def"], "res": pet["res"], "spd": pet["spd"],
            }
            types = [t for t in (pet["element1"], pet["element2"]) if t]
            trait_row = con.execute(
                "SELECT name, category, effect, battle_effect FROM trait WHERE name = ?", (pet["trait"],)
            ).fetchone()
            learnset = [dict(_) for _ in con.execute(
                "SELECT ps.skill_name AS name, ps.unlock AS unlock, ps.source AS learn_source,"
                " s.element AS element, s.category AS category, s.power AS power, s.energy AS energy,"
                " s.combo AS combo, s.desc AS description, s.effect AS effect"
                " FROM pet_skill ps LEFT JOIN skill s ON s.name = ps.skill_name"
                " WHERE ps.pet_name = ? ORDER BY s.power IS NULL, s.power DESC, ps.skill_name",
                (pet["name"],))]
            usage: Dict[str, List[Dict[str, Any]]] = {}
            for kind in ("nature", "individual_value", "bloodline", "skill"):
                usage[kind] = [
                    {"label": r["label"], "percent": round(r["percent"], 2), "ratio": r["ratio"], "rank": r["rank"]}
                    for r in con.execute(
                        "SELECT label, percent, ratio, rank FROM usage WHERE pet_name = ? AND kind = ?"
                        " ORDER BY rank, percent DESC LIMIT ?", (pet["name"], kind, usage_limit))
                ]
            skill_index = {item["name"]: item for item in learnset if item.get("element")}
            # 同一只精灵的其它形态：名字不同但 base_name 相同（配色轴另算）。
            siblings = [
                {"name": r["name"], "form": r["form"] or "", "colorType": r["color_type"],
                 "colorLabel": r["color_label"], "types": [t for t in (r["element1"], r["element2"]) if t]}
                for r in con.execute(
                    "SELECT name, form, color_type, color_label, element1, element2 FROM pet"
                    " WHERE base_name = ? AND name != ? ORDER BY color_type, name LIMIT 8",
                    (pet["base_name"], pet["name"]))
            ]
        finally:
            con.close()

        recommended = []
        for skill_name in _json(pet["pvp_skills"], []):
            info = skill_index.get(skill_name)
            if info:
                recommended.append({k: info[k] for k in ("name", "element", "category", "power", "energy", "combo")})
            else:
                recommended.append({"name": skill_name, "element": "", "category": "", "power": None,
                                    "energy": None, "combo": None})
        return {
            "available": True,
            "found": True,
            "source": SOURCE,
            "pet": {
                "id": pet["pet_id"],
                "no": pet["no"],
                "name": pet["name"],
                "baseName": pet["base_name"],
                "form": pet["form"],
                "types": types,
                "stats": stats,
                "total": pet["total"],
                "stageTag": pet["stage_tag"],
                "boss": bool(pet["boss"]),
                "trait": pet["trait"],
                "traitDesc": pet["trait_desc"],
                "usagePercent": pet["usage_percent"],
                "usageRatio": pet["usage_ratio"],
            },
            "trait": None if trait_row is None else {
                "name": trait_row["name"],
                "category": trait_row["category"],
                "effect": trait_row["effect"],
                "battleEffect": _json(trait_row["battle_effect"], {}),
            },
            "defense": self._defensive(chart, types),
            "offense": self._offensive(chart, types),
            "recommended": {"skills": recommended,
                            "natures": _json(pet["pvp_natures"], []),
                            "individualValues": _json(pet["pvp_iv"], [])},
            "usage": usage,
            "learnset": learnset,
            "variant": {
                "colorType": pet["color_type"],
                "colorLabel": pet["color_label"],
                "colorBase": pet["color_base"],
                "colorEffect": pet["color_effect"],
                "season": pet["season"],
                "isShiny": bool(pet["is_shiny"]),
                "isPolluted": bool(pet["is_polluted"]),
                "formLabel": pet["form"] or "",
                "formRaw": pet["form_raw"] or "",
            },
            "siblings": siblings,
        }

    # ---------------------------------------------------------------- lists

    def leaderboard(self, kind: str = "usage", limit: int = 20) -> Dict[str, Any]:
        """Top pets by usage, or top skills/natures by usage share."""
        if not available():
            return {"available": False}
        limit = max(1, min(limit, 200))
        con = _connect()
        try:
            if kind == "pets":
                rows = [dict(r) for r in con.execute(
                    "SELECT name, element1, element2, total, usage_percent, trait FROM pet"
                    " WHERE usage_percent > 0 ORDER BY usage_percent DESC LIMIT ?", (limit,))]
                return {"available": True, "kind": kind, "items": rows}
            if kind in ("skills", "natures", "bloodline"):
                usage_kind = "skill" if kind == "skills" else ("nature" if kind == "natures" else "bloodline")
                rows = [dict(r) for r in con.execute(
                    "SELECT label, SUM(percent) AS percent, COUNT(DISTINCT pet_name) AS pets FROM usage"
                    " WHERE kind = ? GROUP BY label ORDER BY percent DESC LIMIT ?", (usage_kind, limit))]
                return {"available": True, "kind": kind, "items": rows}
            rows = [dict(r) for r in con.execute(
                "SELECT pet_name, percent FROM usage WHERE kind = 'skill' ORDER BY percent DESC LIMIT ?",
                (limit,))]
        finally:
            con.close()
        return {"available": True, "kind": kind, "items": rows}

    def skills(self, query: str = "", element: str = "", category: str = "", limit: int = 40) -> Dict[str, Any]:
        if not available():
            return {"available": False, "items": []}
        limit = max(1, min(limit, 200))
        sql = ("SELECT name, element, category, power, energy, combo, desc, effect, source FROM skill WHERE 1=1")
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
        return {"available": True, "total": total, "items": rows}
