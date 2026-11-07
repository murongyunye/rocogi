from __future__ import annotations

from typing import Any, Dict, List

from . import dex, pvp
from .adapters.battle import BattleLab
from .adapters.turn_state import read_turn_state
from .engine_common import load_cli_settings, load_frame

ACTIONS = ("dex_list", "dex_detail", "dex_skills", "analyze", "decide", "simulate", "matchup", "meta", "turn_state")


def _battle() -> BattleLab:
    return BattleLab()


def _player_team(raw: Any) -> Any:
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ValueError("playerTeam 必须是数组，元素为精灵名或 {name, skills, nature, iv}")
    team: List[Any] = []
    for entry in raw:
        if isinstance(entry, str):
            name = entry.strip()
            if name:
                team.append({"name": name})
            continue
        if not isinstance(entry, dict):
            raise ValueError("playerTeam 的元素必须是精灵名或对象")
        team.append(entry)
    if not team:
        raise ValueError("阵容为空，请至少选择一只精灵")
    return team


def _team(raw: Any) -> List[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("team 必须是精灵名数组")
    return [str(item) for item in raw]


def dispatch(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if action == "turn_state":
        settings = load_cli_settings(params.get("settings") if isinstance(params.get("settings"), str) else None)
        frame = load_frame(params, settings)
        return read_turn_state(frame, settings)

    if action == "meta":
        battle = _battle()
        return {
            "dex": dex.meta(),
            "presets": battle.presets(),
            "opponents": pvp.meta(battle)["opponents"],
            "observations": pvp.observations(8),
        }

    if action == "dex_list":
        return dex.pokemon_list(
            str(params.get("q") or ""),
            str(params.get("element") or ""),
            str(params.get("stage") or ""),
            str(params.get("sort") or "id"),
            str(params.get("order") or "asc"),
            int(params.get("limit") or 24),
            int(params.get("offset") or 0),
        )

    if action == "dex_detail":
        detail = dex.pokemon_detail(str(params.get("name") or ""))
        if not detail:
            raise ValueError("图鉴中没有这只精灵")
        return detail

    if action == "dex_skills":
        return dex.skill_list(
            str(params.get("q") or ""),
            str(params.get("element") or ""),
            str(params.get("category") or ""),
            int(params.get("limit") or 40),
            int(params.get("offset") or 0),
        )

    if action == "analyze":
        return pvp.analyze(_team(params.get("team")))

    if action == "decide":
        return _battle().decide(int(params.get("simulations") or 40))

    if action == "simulate":
        return _battle().simulate(
            _player_team(params.get("playerTeam")),
            str(params.get("aiTeam") or "wing"),
            int(params.get("simulations") or 40),
            int(params.get("maxTurns") or 30),
        )

    if action == "matchup":
        return pvp.matchup(
            _battle(),
            _team(params.get("team")),
            str(params.get("opponent") or "wing"),
            int(params.get("simulations") or 40),
            int(params.get("maxTurns") or 30),
        )

    raise ValueError(f"未知对战动作: {action}")
