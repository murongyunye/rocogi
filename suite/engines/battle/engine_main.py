"""battle engine - dataset / team build / damage / decision (NRC_AI full stack).

Integration source (MERGE_MAP): NRC_AI src/* + assets/db/nrc.db.
Own venv / process, no imports from other suite engines.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time

SUITE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.path.dirname(os.path.dirname(SUITE))
NRC_ROOT = os.path.join(WORK, "rocogi", "vendor", "ColinHong10-NRC_AI")
sys.path.insert(0, NRC_ROOT)

ENGINE = "battle"
ASSETS = os.path.join(SUITE, "assets")
DB = os.path.join(ASSETS, "db", "nrc.db")  # overridden from config in main()
ROOT = os.path.dirname(SUITE)


def _db_path(cfg) -> str:
    rel = cfg.get("battle", {}).get("db", "")
    return os.path.normpath(os.path.join(SUITE, rel)) if rel else DB


def _bwiki_path(cfg) -> str:
    """BWIKI is the preferred battle dataset; nrc.db stays as the legacy fallback."""
    rel = cfg.get("battle", {}).get("bwiki_db", "")
    return os.path.normpath(os.path.join(ROOT, rel)) if rel else os.path.join(
        ROOT, "datasets", "bwiki", "bwiki_battle.db")


def _bwiki():
    import bwiki  # local module next to this file

    return bwiki

# bind NRC_AI to the suite's imported DB copy before anything touches the upstream data dir
try:
    import src.pokemon_db as _pdb

    _pdb._DB_PATH = DB
except Exception:  # noqa: BLE001
    _pdb = None

_OPEN = sqlite3.connect


def _ro_connect(database, *args, **kwargs):
    """Force read-only access on the imported nrc.db so no -wal/-shm lands in assets or upstream."""
    if isinstance(database, str) and "uri" not in kwargs:
        try:
            if os.path.abspath(database) == os.path.abspath(DB):
                return _OPEN(f"file:{database}?mode=ro&immutable=1", uri=True)
        except OSError:
            pass
    return _OPEN(database, *args, **kwargs)


sqlite3.connect = _ro_connect


def emit(log_path, event, **payload):
    rec = {"ts": round(time.time(), 3), "engine": ENGINE, "type": event, **payload}
    line = json.dumps(rec, ensure_ascii=False)
    print(line, flush=True)
    if log_path:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def load_toml(path):
    import tomllib

    with open(path, "rb") as fh:
        return tomllib.load(fh)


def _db_counts():
    con = _OPEN(f"file:{DB}?mode=ro&immutable=1", uri=True)
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    counts = {}
    for t in tables:
        try:
            counts[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except sqlite3.Error:
            counts[t] = -1
    con.close()
    return tables, counts


def action_dataset(cfg):
    tables, counts = _db_counts()
    return {"action": "dataset", "db": os.path.relpath(DB, SUITE), "tables": tables, "counts": counts}


def action_team(cfg):
    from src.team_builder import TeamBuilder

    team = TeamBuilder.create_wing_team()
    return {"action": "team_builder", "team": [{"name": p.name, "hp": p.hp, "speed": p.speed,
                                                "skills": [s.name for s in p.skills]} for p in team]}


def action_damage(cfg):
    from src.battle import DamageCalculator
    from src.team_builder import TeamBuilder

    a = TeamBuilder.create_wing_team()
    b = TeamBuilder.create_toxic_team()
    attacker, defender = a[0], b[0]
    skill = attacker.skills[0]
    dmg = DamageCalculator.calculate(attacker, defender, skill)
    return {"action": "damage_model", "attacker": attacker.name, "defender": defender.name,
            "skill": skill.name, "damage": dmg}


def action_responder(cfg):
    from src.battle import get_actions
    from src.models import BattleState
    from src.team_builder import TeamBuilder

    team_a = TeamBuilder.create_wing_team()
    team_b = TeamBuilder.create_toxic_team()
    state = BattleState(team_a=team_a, team_b=team_b)
    team = str(cfg.get("battle", {}).get("team", "a"))
    actions = get_actions(state, team)

    decision = None
    try:
        import random

        from src.mcts import MCTS

        # deterministic search: MCTS samples through the stdlib RNG, seed it per decision
        random.seed(int(cfg.get("battle", {}).get("random_seed", 20261105)))
        mcts = MCTS(simulations=int(cfg["battle"]["simulations"]), team=team)
        for attr in ("get_best_action", "search", "run", "decide", "best_action"):
            fn = getattr(mcts, attr, None)
            if callable(fn):
                decision = fn(state)
                break
    except Exception as exc:  # noqa: BLE001
        decision = {"error": f"{type(exc).__name__}: {exc}"}

    return {
        "action": "responder",
        "turn": state.turn,
        "availableActions": [_action_row(a) for a in actions[:8]],
        "availableCount": len(actions),
        "mcts": _plain(decision),
        "source": "NRC_AI get_actions + MCTS",
    }


def action_turn_state(cfg):
    """D-class gap: turn_state.

    HUD/OCR extraction stays in the backend adapter; this engine owns the *schema*
    side - turning an observation into an NRC_AI BattleState and back.
    """
    from src.models import BattleState
    from src.team_builder import TeamBuilder

    team_a = TeamBuilder.create_wing_team()
    team_b = TeamBuilder.create_toxic_team()
    obs = cfg.get("turn_state", {}).get("observation", {})
    state = BattleState(team_a=team_a, team_b=team_b)
    for ph, names in (("a", obs.get("aHpPct", [])), ("b", obs.get("bHpPct", []))):
        side = team_a if ph == "a" else team_b
        for mon, pct in zip(side, names):
            mon.hp = max(1, int(round(mon.hp * float(pct) / 100.0)))
    if "turn" in obs:
        state.turn = int(obs["turn"])
    return {
        "action": "turn_state",
        "turn": getattr(state, "turn", None),
        "sideA": [{"name": p.name, "hp": p.hp, "fainted": getattr(p, "fainted", False)} for p in team_a],
        "sideB": [{"name": p.name, "hp": p.hp, "fainted": getattr(p, "fainted", False)} for p in team_b],
        "observationApplied": obs,
        "source": "NRC_AI BattleState schema",
    }


def action_catalog(cfg):
    """BWIKI battle knowledge summary (skills/pets/learnsets/type chart)."""
    bw = _bwiki()
    data = bw.summary()
    data["action"] = "catalog"
    data["preferred"] = True
    data["fallback"] = os.path.relpath(DB, SUITE)
    return data


def action_pokedex(cfg):
    """Pet sheet from BWIKI: base stats, typing, ability, full learnset, evolution chain."""
    bw = _bwiki()
    name = str(cfg.get("pokedex", {}).get("name", "") or "").strip()
    if not name:
        return {"action": "pokedex", "error": "set [pokedex] name = \"<精灵名>\""}
    pets = bw.find_pet(name)
    if not pets:
        return {"action": "pokedex", "name": name, "found": False,
                "hint": "name not in BWIKI data; fall back to nrc.db"}
    pet = pets[0]
    skills = bw.pet_skills(pet["name"])
    return {
        "action": "pokedex",
        "found": True,
        "source": "bwiki",
        "pet": {k: pet[k] for k in ("pet_id", "name", "title", "types", "stage", "class",
                                    "hp", "atk", "def", "spatk", "spdef", "speed", "total",
                                    "feature_skill", "description")},
        "skills": [{k: s[k] for k in ("kind", "level", "skill_name", "element", "category",
                                      "damage_class", "energy", "power", "blood")} for s in skills],
        "evolution": bw.evolution_chain(pet["name"]),
    }


def action_skills(cfg):
    """Skill catalogue query: by name / element / category / max energy."""
    bw = _bwiki()
    q = cfg.get("skills", {})
    if q.get("name"):
        return {"action": "skills", "query": q, "skills": bw.find_skill(str(q["name"]))}
    limit = int(q.get("limit", 25))
    with bw.connect() as con:
        sql = "SELECT name, element, category, damage_class, energy, power, target, desc FROM skill WHERE 1=1"
        params = []
        if q.get("element"):
            sql += " AND element = ?"
            params.append(str(q["element"]))
        if q.get("category"):
            sql += " AND category = ?"
            params.append(str(q["category"]))
        if q.get("max_energy"):
            sql += " AND energy <= ?"
            params.append(int(q["max_energy"]))
        sql += " ORDER BY power IS NULL, power DESC LIMIT ?"
        params.append(limit)
        rows = [dict(r) for r in con.execute(sql, params)]
    return {"action": "skills", "query": q, "count": len(rows), "skills": rows}


def action_best_skill(cfg):
    """Rank a pet's attacking skills against the enemy typing (the live battle picker).

    cfg:
        [best_skill] pet = "水蓝蓝"  enemy_types = ["草"]  energy = 4
    Falls back to nrc.db names when BWIKI has no such pet.
    """
    bw = _bwiki()
    q = cfg.get("best_skill", {})
    pet = str(q.get("pet", "") or "").strip()
    if not pet:
        return {"action": "best_skill", "error": "set [best_skill] pet = \"<精灵名>\""}
    enemy = [str(t) for t in (q.get("enemy_types") or [])]
    energy = q.get("energy")
    energy = int(energy) if energy not in (None, "", "none") else None
    ranked = bw.best_skill(pet, enemy, energy)
    if not ranked:
        return {"action": "best_skill", "pet": pet, "found": False, "enemyTypes": enemy,
                "hint": "no attacking skill for this pet in BWIKI; fall back to nrc.db"}
    return {"action": "best_skill", "pet": pet, "found": True, "source": "bwiki",
            "enemyTypes": enemy, "energyBudget": energy,
            "best": ranked[0], "ranked": ranked[:6]}


def action_hud(cfg):
    """Parse a battle HUD read from OCR lines produced elsewhere.

    This engine has no OCR dependency on purpose: the vision layer recognises text
    (WinRT OCR / tesseract / a vision model) and hands over lines plus the frame
    size. HUD geometry lives in hud.py so every consumer shares one layout.

    cfg:
        [hud] lines = "<path to json: [{text,cx,cy}, ...]>"
              width = 1280
              height = 800
              image = "<fresh frame path, for provenance only>"
    """
    import json

    import hud
    import bwiki

    q = cfg.get("hud", {})
    lines_path = str(q.get("lines", "") or "").strip()
    if not lines_path:
        return {"action": "hud", "error": "set [hud] lines = \"<ocr lines json>\""}
    if not os.path.isabs(lines_path):
        lines_path = os.path.join(ROOT, lines_path)
    with open(lines_path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    lines = payload.get("lines") if isinstance(payload, dict) else payload
    width = int(q.get("width") or (payload.get("width") if isinstance(payload, dict) else 0) or 1280)
    height = int(q.get("height") or (payload.get("height") if isinstance(payload, dict) else 0) or 800)
    with bwiki.connect() as con:
        known = [r[0] for r in con.execute("SELECT DISTINCT name FROM skill")]
    read = hud.read(lines, width, height, known)
    read["action"] = "hud"
    read["linesFile"] = lines_path
    if q.get("image"):
        read["image"] = q["image"]
    read["source"] = "hud.py layout (ally top-left / enemy top-right / skills left / options bottom-right)"
    return read


def action_action_row(action):
    """Expose the NRC_AI action tuple shape without needing a BattleState."""
    return {"action": "action_row", "row": _action_row(action)}


def _action_row(action):
    """NRC_AI Action is a tuple: (skill_idx,) | (-1,) charge | (-2, switch_idx)."""
    vals = list(action) if isinstance(action, tuple) else _plain(action)
    head = vals[0] if isinstance(vals, list) else None
    if head is None:
        kind = "unknown"
    elif head == -1:
        kind = "charge"
    elif head == -2:
        kind = "switch"
    else:
        kind = "skill"
    return {"kind": kind, "raw": vals}


def _plain(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    for attr in ("name", "action_type"):
        if hasattr(value, attr):
            return {attr: _plain(getattr(value, attr))}
    return type(value).__name__


ACTIONS = {"dataset": action_dataset, "team": action_team, "damage": action_damage,
           "responder": action_responder, "turn_state": action_turn_state,
           "catalog": action_catalog, "pokedex": action_pokedex, "skills": action_skills,
           "best_skill": action_best_skill, "hud": action_hud}


def _bind_db(cfg=None):
    """Point NRC_AI at the suite's imported copy so the upstream dir stays untouched."""
    global DB
    if cfg is not None:
        DB = _db_path(cfg)
        path = _bwiki_path(cfg)
        import bwiki

        bwiki.bind(path)
    import src.pokemon_db as pdb

    pdb._DB_PATH = DB


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--log", default="")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--action", default="responder")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=float, default=1.0)
    args = ap.parse_args()

    cfg = load_toml(args.config)
    _bind_db(cfg)
    emit(args.log, "ready", run_id=args.run_id, config=args.config, python=sys.version.split()[0],
         components=["battle.dataset", "battle.team_builder", "battle.mcts", "battle.damage_model",
                     "battle.turn_state", "battle.responder", "battle.bwiki.catalog",
                     "battle.bwiki.pokedex", "battle.bwiki.skills", "battle.bwiki.best_skill",
                     "battle.hud"])

    fn = ACTIONS.get(args.action)
    if fn is None:
        emit(args.log, "error", error=f"unknown action: {args.action}", actions=sorted(ACTIONS))
        return 2

    if not args.once:
        try:
            while True:
                emit(args.log, "result", result=fn(cfg))
                time.sleep(max(0.1, args.interval))
        except KeyboardInterrupt:
            return 0

    try:
        emit(args.log, "result", result=fn(cfg))
    except Exception as exc:  # noqa: BLE001
        emit(args.log, "error", error=f"{type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
