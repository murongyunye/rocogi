from __future__ import annotations

from typing import Any, Dict

from . import engine_battle, engine_flow, engine_input, engine_sense, engine_sift
from .components import build_registry

ACTIONS = ("library", "groups", "*")

_HANDLERS = {
    "sense": engine_sense,
    "input": engine_input,
    "sift": engine_sift,
    "battle": engine_battle,
    "flow": engine_flow,
}


def dispatch(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if action == "library":
        registry = build_registry()
        return {
            "version": registry["version"],
            "stats": registry["stats"],
            "groups": registry["groups"],
            "gaps": registry["gaps"],
            "engines": [
                {
                    "id": engine["id"],
                    "name": engine["name"],
                    "components": [
                        {
                            "id": component["id"],
                            "name": component["name"],
                            "status": component["status"],
                            "statusNote": component["statusNote"],
                        }
                        for component in engine["components"]
                    ],
                }
                for engine in registry["engines"]
            ],
        }

    if action == "groups":
        return {"groups": build_registry()["groups"]}

    if "." in action:
        group, sub = action.split(".", 1)
        handler = _HANDLERS.get(group)
        if not handler:
            raise ValueError(f"未知引擎组: {group}")
        if not sub:
            raise ValueError(f"缺少动作名: {action}，格式为 group.action")
        return {"group": group, "result": handler.dispatch(sub, params)}

    matches = [group for group, handler in _HANDLERS.items() if action in handler.ACTIONS]
    if len(matches) == 1:
        group = matches[0]
        return {"group": group, "result": _HANDLERS[group].dispatch(action, params)}
    if len(matches) > 1:
        raise ValueError(
            f"统一引擎动作 {action} 在多个引擎组中同名（{', '.join(matches)}），"
            f"请使用 group.action，例如 {matches[0]}.{action}"
        )

    raise ValueError(f"未知统一引擎动作: {action}")
