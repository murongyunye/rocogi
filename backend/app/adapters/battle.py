from __future__ import annotations

import sqlite3
import threading
import time
import traceback
from typing import Any, Dict, List, Optional

from ..config import BATTLE_DB


def _action_label(state, team: str, action: tuple) -> str:
    team_list = state.team_a if team == "a" else state.team_b
    current = team_list[state.current_a if team == "a" else state.current_b]
    if not action:
        return "未知"
    if action[0] == -1:
        return "汇合聚能"
    if action[0] == -2:
        index = action[1] if len(action) > 1 else 0
        target = team_list[index] if 0 <= index < len(team_list) else None
        return f"换人 · {target.name if target else index}"
    index = action[0]
    if 0 <= index < len(current.skills):
        return current.skills[index].name
    return f"技能 {index}"


def _team_snapshot(state, team: str) -> List[Dict[str, Any]]:
    team_list = state.team_a if team == "a" else state.team_b
    current_index = state.current_a if team == "a" else state.current_b
    out = []
    for index, pokemon in enumerate(team_list):
        out.append(
            {
                "name": pokemon.name,
                "type": pokemon.pokemon_type.value,
                "hp": max(0, int(round(pokemon.current_hp))),
                "maxHp": int(round(pokemon.hp)),
                "energy": int(pokemon.energy),
                "fainted": bool(pokemon.is_fainted),
                "active": index == current_index,
                "skills": [skill.name for skill in pokemon.skills],
            }
        )
    return out


class BattleLab:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._ready = False
        self._error: Optional[str] = None

    def _ensure(self) -> bool:
        if self._ready:
            return True
        if self._error:
            return False
        try:
            with self._lock:
                import src.battle as battle  # type: ignore
                import src.mcts as mcts  # type: ignore
                import src.team_builder as team_builder  # type: ignore
                from src.pokemon_db import get_pokemon, get_pokemon_skills  # type: ignore
                from src.skill_db import get_skill  # type: ignore
                from src.models import BattleState  # type: ignore

                self._battle = battle
                self._mcts = mcts
                self._TeamBuilder = team_builder.TeamBuilder
                self._BattleState = BattleState
                self._get_pokemon = get_pokemon
                self._get_pokemon_skills = get_pokemon_skills
                self._get_skill = get_skill
                self._ready = True
            return True
        except Exception as exc:  # noqa: BLE001
            self._error = str(exc)
            return False

    # ------------------------------------------------------------------ data
    def pokemon_list(self, query: str = "", limit: int = 40) -> Dict[str, Any]:
        limit = max(1, min(limit, 200))
        conn = sqlite3.connect(str(BATTLE_DB), check_same_thread=False)
        try:
            if query:
                rows = conn.execute(
                    "SELECT id,name,element,evo_stage,ability,base_hp,base_atk,base_spatk,base_def,base_spdef,base_speed"
                    " FROM pokemon WHERE name LIKE ? OR ability LIKE ? ORDER BY id LIMIT ?",
                    (f"%{query}%", f"%{query}%", limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id,name,element,evo_stage,ability,base_hp,base_atk,base_spatk,base_def,base_spdef,base_speed"
                    " FROM pokemon ORDER BY id LIMIT ?",
                    (limit,),
                ).fetchall()
            total = conn.execute("SELECT COUNT(*) FROM pokemon").fetchone()[0]
        finally:
            conn.close()
        return {
            "total": total,
            "items": [
                {
                    "id": row[0],
                    "name": row[1],
                    "element": row[2],
                    "stage": row[3],
                    "ability": row[4],
                    "stats": {
                        "hp": row[5],
                        "atk": row[6],
                        "spatk": row[7],
                        "def": row[8],
                        "spdef": row[9],
                        "speed": row[10],
                    },
                }
                for row in rows
            ],
        }

    def skills_for(self, name: str) -> List[Dict[str, Any]]:
        if not self._ensure():
            return []
        rows = self._get_pokemon_skills(name)
        return [
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "element": row.get("element"),
                "category": row.get("category"),
                "power": row.get("power"),
                "energy": row.get("energy_cost"),
            }
            for row in rows[:12]
        ]

    def presets(self) -> List[Dict[str, Any]]:
        return [
            {"id": "toxic", "name": "千棘盔毒队", "description": "消耗与中毒体系，适合持久战"},
            {"id": "wing", "name": "圣羽翼王队", "description": "高速翼系压制，适合速攻演示"},
        ]

    def preset_team(self, key: str) -> Dict[str, Any]:
        if key not in ("toxic", "wing"):
            return {"ok": False, "error": f"未知预设队伍: {key}，可选: toxic, wing"}
        if not self._ensure():
            return {"ok": False, "error": f"战斗引擎不可用: {self._error}"}
        with self._lock:
            try:
                team = self._preset_team(key)
                return {
                    "ok": True,
                    "id": key,
                    "members": [
                        {
                            "name": pokemon.name,
                            "type": pokemon.pokemon_type.value,
                            "hp": int(round(pokemon.hp)),
                            "energy": int(pokemon.energy),
                            "skills": [skill.name for skill in pokemon.skills],
                        }
                        for pokemon in team
                    ],
                }
            except Exception as exc:  # noqa: BLE001
                return {"ok": False, "error": str(exc)}

    # ------------------------------------------------------------------ teams
    def _preset_team(self, key: str):
        if key == "toxic":
            return self._TeamBuilder.create_toxic_team()
        return self._TeamBuilder.create_wing_team()

    def _custom_team(self, entries: List[Dict[str, Any]]):
        if len(entries) > 6:
            raise ValueError(f"阵容最多 6 只精灵，当前 {len(entries)} 只")
        team = []
        for entry in entries:
            if isinstance(entry, str):
                entry = {"name": entry}
            if not isinstance(entry, dict):
                raise ValueError("阵容元素必须是精灵名或对象")
            name = str(entry.get("name", "")).strip()
            if not name:
                continue
            data = self._get_pokemon(name)
            if not data:
                raise ValueError(f"精灵不存在: {name}")
            skills = [str(s) for s in (entry.get("skills") or [])]
            if not skills:
                learned = self._get_pokemon_skills(name)[:4]
                skills = [row["name"] for row in learned]
            if not skills:
                raise ValueError(f"精灵没有可用技能: {name}")
            nature = str(entry.get("nature") or "坦率")
            iv = entry.get("iv")
            team.append(self._TeamBuilder._p(name, skills, iv_config=iv, nature=nature))
        if not team:
            raise ValueError("阵容为空")
        return team

    def _build_state(self, team_a: Any, team_b: Any):
        return self._BattleState(team_a=team_a, team_b=team_b, current_a=0, current_b=0, turn=1)

    # ------------------------------------------------------------------ simulate
    def simulate(
        self,
        player_team: Optional[List[Dict[str, Any]]] = None,
        ai_team: str = "wing",
        simulations: int = 60,
        max_turns: int = 30,
    ) -> Dict[str, Any]:
        if not self._ensure():
            return {"ok": False, "error": f"战斗引擎不可用: {self._error}"}
        started = time.time()
        with self._lock:
            try:
                team_a = self._custom_team(player_team) if player_team else self._preset_team("toxic")
                team_b = self._custom_team([{"name": ai_team}]) if ai_team not in ("toxic", "wing") else self._preset_team(ai_team)
                state = self._build_state(team_a, team_b)
                mcts_a = self._mcts.MCTS(simulations=max(10, min(int(simulations), 300)), team="a")
                mcts_b = self._mcts.MCTS(simulations=max(10, min(int(simulations), 300)), team="b")
                self._battle.auto_switch(state)
                logs: List[Dict[str, Any]] = []
                logs.append({"kind": "start", "text": f"战斗开始 · {len(team_a)} vs {len(team_b)}"})
                turn_records: List[Dict[str, Any]] = []
                winner = self._battle.check_winner(state)
                for _ in range(max(1, min(int(max_turns), 80))):
                    if winner:
                        break
                    action_a = mcts_a.get_best_action(state)
                    action_b = mcts_b.get_best_action(state)
                    label_a = _action_label(state, "a", action_a)
                    label_b = _action_label(state, "b", action_b)
                    before_a = sum(p.current_hp for p in state.team_a)
                    before_b = sum(p.current_hp for p in state.team_b)
                    current_turn = state.turn
                    self._battle.execute_full_turn(state, action_a, action_b)
                    self._battle.auto_switch(state)
                    after_a = sum(p.current_hp for p in state.team_a)
                    after_b = sum(p.current_hp for p in state.team_b)
                    logs.append(
                        {
                            "kind": "turn",
                            "turn": current_turn,
                            "a": label_a,
                            "b": label_b,
                            "hpA": max(0, int(round(after_a))),
                            "hpB": max(0, int(round(after_b))),
                            "deltaA": int(round(after_a - before_a)),
                            "deltaB": int(round(after_b - before_b)),
                        }
                    )
                    turn_records.append(
                        {
                            "turn": current_turn,
                            "teamA": _team_snapshot(state, "a"),
                            "teamB": _team_snapshot(state, "b"),
                        }
                    )
                    winner = self._battle.check_winner(state)
                if winner:
                    logs.append({"kind": "end", "text": "我方胜利" if winner == "a" else "对方胜利"})
                else:
                    logs.append({"kind": "end", "text": "达到回合上限，判定为平局"})
                return {
                    "ok": True,
                    "winner": winner or "draw",
                    "turns": state.turn,
                    "durationMs": int((time.time() - started) * 1000),
                    "teamA": _team_snapshot(state, "a"),
                    "teamB": _team_snapshot(state, "b"),
                    "logs": logs,
                    "records": turn_records[-3:],
                }
            except Exception as exc:  # noqa: BLE001
                traceback.print_exc()
                return {"ok": False, "error": str(exc)}

    def decide(self, simulations: int = 60) -> Dict[str, Any]:
        if not self._ensure():
            return {"ok": False, "error": f"战斗引擎不可用: {self._error}"}
        with self._lock:
            try:
                state = self._build_state(self._preset_team("toxic"), self._preset_team("wing"))
                action = self._mcts.MCTS(simulations=max(10, min(int(simulations), 200)), team="a").get_best_action(state)
                return {
                    "ok": True,
                    "action": action,
                    "label": _action_label(state, "a", action),
                    "active": state.get_current("a").name,
                    "enemy": state.get_current("b").name,
                    "turn": state.turn,
                }
            except Exception as exc:  # noqa: BLE001
                return {"ok": False, "error": str(exc)}
