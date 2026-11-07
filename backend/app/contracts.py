from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional


@dataclass(frozen=True)
class PortDef:
    id: str
    label: str
    kind: str = "exec"  # exec | data


@dataclass(frozen=True)
class FieldDef:
    key: str
    label: str
    type: str = "text"  # text | textarea | number | boolean | select | expression | resource | target
    default: Any = None
    options: Optional[List[Dict[str, str]]] = None
    placeholder: str = ""
    help: str = ""
    required: bool = False
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    step: Optional[float] = None
    rows: int = 3


@dataclass(frozen=True)
class NodeContract:
    type: str
    title: str
    category: str
    description: str
    inputs: List[PortDef] = field(default_factory=list)
    outputs: List[PortDef] = field(default_factory=list)
    fields: List[FieldDef] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    icon: str = "node"
    # effectful=True 表示执行该节点会改变外部世界或运行状态；纯读屏与计算为 False。
    effectful: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["inputs"] = [asdict(p) for p in self.inputs]
        data["outputs"] = [asdict(p) for p in self.outputs]
        data["fields"] = [asdict(f) for f in self.fields]
        return data


@dataclass
class NodeResult:
    outputs: Dict[str, Any] = field(default_factory=dict)
    next_port: str = "out"
    stop: bool = False
    message: Optional[str] = None
    artifacts: List[Dict[str, Any]] = field(default_factory=list)


NodeHandler = Callable[[Any, Any], NodeResult]

_REGISTRY: Dict[str, tuple[NodeContract, NodeHandler]] = {}

CATEGORY_META = {
    "run": {"label": "运行", "accent": "#5eead4"},
    "flow": {"label": "流程", "accent": "#94a3b8"},
    "capture": {"label": "采集", "accent": "#60a5fa"},
    "vision": {"label": "视觉", "accent": "#a78bfa"},
    "game": {"label": "游戏", "accent": "#fbbf24"},
    "map": {"label": "地图", "accent": "#34d399"},
    "battle": {"label": "对战", "accent": "#f472b6"},
    "input": {"label": "输入", "accent": "#fb923c"},
    "net": {"label": "网络", "accent": "#38bdf8"},
}


def register(contract: NodeContract) -> Callable[[NodeHandler], NodeHandler]:
    def decorator(handler: NodeHandler) -> NodeHandler:
        if contract.type in _REGISTRY:
            raise RuntimeError(f"duplicate node type: {contract.type}")
        _REGISTRY[contract.type] = (contract, handler)
        return handler

    return decorator


def get_spec(node_type: str) -> Optional[tuple[NodeContract, NodeHandler]]:
    return _REGISTRY.get(node_type)


def get_contract(node_type: str) -> Optional[NodeContract]:
    spec = _REGISTRY.get(node_type)
    return spec[0] if spec else None


def catalog() -> Dict[str, Any]:
    nodes = []
    for contract, _handler in _REGISTRY.values():
        item = contract.to_dict()
        meta = CATEGORY_META.get(contract.category, {"label": contract.category, "accent": "#94a3b8"})
        item["categoryLabel"] = meta["label"]
        item["accent"] = meta["accent"]
        nodes.append(item)
    categories = [
        {"id": key, "label": value["label"], "accent": value["accent"]}
        for key, value in CATEGORY_META.items()
        if any(n["category"] == key for n in nodes)
    ]
    return {"nodes": nodes, "categories": categories}


def node_contracts() -> List[NodeContract]:
    """按注册顺序导出全部节点契约，供机器可读端点使用。"""
    return [contract for contract, _handler in _REGISTRY.values()]
