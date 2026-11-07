"""机器可读能力契约发布口。

节点契约直接来自 contracts 注册表；动作契约直接来自 harness.tools_schema()，
并用 harness_contracts 中唯一的一份风险分级与输出字段声明补齐无法从 schema
推导的语义。本模块不保存第二份契约快照，也不访问磁盘上的 registry 文件。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Sequence

from . import engine_vendor
from . import harness
from .config import platform_capabilities
from .contracts import catalog
from .harness_contracts import (
    ACTION_OUTPUT_FIELDS,
    ACTION_REQUIRED_ANY,
    ACTION_REQUIRED_FIELDS,
    ACTION_RISK,
    RUNTIME_OUTPUT_FIELDS,
)

# 契约格式版本：新增向后兼容字段递增 minor，删除或改变既有语义递增 major。
CONTRACT_VERSION = "1.1.0"

# 风险分级：只读 / 有外部副作用 / 不可逆。effectful = risk != "read_only"。
RISK_LEVELS = ("read_only", "external_side_effect", "irreversible")

_UI_ONLY_KEYS = ("categoryLabel", "accent")


def canonical_json(payload: Any) -> str:
    """稳定序列化：键排序、无多余空白、保留中文原文。"""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(payload: Any) -> str:
    """对规范化 JSON 做 sha256；只由内容决定。"""
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _stable_nodes(nodes: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {key: value for key, value in node.items() if key not in _UI_ONLY_KEYS}
        for node in sorted(nodes, key=lambda item: item["type"])
    ]


def nodes_document() -> Dict[str, Any]:
    data = catalog()
    nodes = data["nodes"]
    return {
        "contract_version": CONTRACT_VERSION,
        "fingerprint": fingerprint({"nodes": _stable_nodes(nodes)}),
        "node_count": len(nodes),
        "nodes": nodes,
        "categories": data["categories"],
    }


def _availability(action: str, caps: Dict[str, Any]) -> tuple:
    if action == "foreground" and not caps.get("windows"):
        reason = "requires Windows window APIs (platform=" + str(caps.get("platform")) + ")"
        return False, reason
    if action.startswith("vendor_") and not engine_vendor.ENGINE.exists():
        return False, "vendor engine missing: suite/engines/vendor/engine_main.py"
    return True, None


def _parameters(schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    properties = schema.get("properties") or {}
    required = tuple(schema.get("required") or ())
    items: List[Dict[str, Any]] = []
    for name in sorted(properties):
        prop = properties[name]
        item: Dict[str, Any] = {
            "name": name,
            "type": prop.get("type"),
            "required": name in required,
        }
        for key in ("enum", "minimum", "maximum", "maxItems", "items"):
            if key in prop:
                item[key] = prop[key]
        items.append(item)
    return items


def _required(action: str, schema: Dict[str, Any]) -> List[str]:
    declared = ACTION_REQUIRED_FIELDS.get(action)
    if declared is not None:
        return list(declared)
    return list(schema.get("required") or ())


def _output_fields(action: str) -> List[str]:
    if action in ACTION_OUTPUT_FIELDS:
        return list(ACTION_OUTPUT_FIELDS[action])
    return list(RUNTIME_OUTPUT_FIELDS.get(action, ()))


def actions_document() -> Dict[str, Any]:
    caps = platform_capabilities()
    actions: List[Dict[str, Any]] = []
    for item in harness.tools_schema():
        tool = item["function"]
        action = tool["name"][len("rocogi_"):]
        schema = tool.get("parameters") or {}
        available, reason = _availability(action, caps)
        risk = ACTION_RISK[action]
        actions.append(
            {
                "name": action,
                "tool": tool["name"],
                "description": tool.get("description", ""),
                "available": available,
                "unavailable_reason": reason,
                "required": _required(action, schema),
                "required_any": list(ACTION_REQUIRED_ANY.get(action, ())),
                "parameters": _parameters(schema),
                "output_fields": _output_fields(action),
                "effectful": risk != "read_only",
                "risk": risk,
            }
        )
    stable = [
        {
            key: value
            for key, value in item.items()
            if key not in ("available", "unavailable_reason")
        }
        for item in sorted(actions, key=lambda item: item["name"])
    ]
    return {
        "contract_version": CONTRACT_VERSION,
        "fingerprint": fingerprint({"actions": stable}),
        "action_count": len(actions),
        "actions": actions,
    }