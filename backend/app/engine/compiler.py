from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..contracts import get_contract


@dataclass
class GraphNode:
    id: str
    type: str
    x: float = 0
    y: float = 0
    config: Dict[str, Any] = field(default_factory=dict)
    disabled: bool = False
    title: str = ""


@dataclass
class GraphEdge:
    id: str
    from_node: str
    from_port: str
    to_node: str
    to_port: str


@dataclass
class Graph:
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    subgraphs: Dict[str, Any] = field(default_factory=dict)

    @property
    def node_by_id(self) -> Dict[str, GraphNode]:
        return {node.id: node for node in self.nodes}


@dataclass
class Issue:
    level: str
    message: str
    node_id: Optional[str] = None


@dataclass
class CompiledGraph:
    graph: Graph
    issues: List[Issue]
    outgoing: Dict[Tuple[str, str], List[GraphEdge]]
    starts: List[GraphNode]

    @property
    def errors(self) -> List[Issue]:
        return [issue for issue in self.issues if issue.level == "error"]

    @property
    def ok(self) -> bool:
        return not self.errors


def default_config(node_type: str) -> Dict[str, Any]:
    contract = get_contract(node_type)
    if not contract:
        return {}
    return {f.key: f.default for f in contract.fields if f.default is not None}


def parse_graph(raw: Dict[str, Any]) -> Graph:
    nodes: List[GraphNode] = []
    for item in raw.get("nodes", []) or []:
        node_type = str(item.get("type", ""))
        config = dict(item.get("config") or {})
        base = default_config(node_type)
        base.update(config)
        nodes.append(
            GraphNode(
                id=str(item.get("id")),
                type=node_type,
                x=float(item.get("x", 0) or 0),
                y=float(item.get("y", 0) or 0),
                config=base,
                disabled=bool(item.get("disabled", False)),
                title=str(item.get("title") or ""),
            )
        )
    edges: List[GraphEdge] = []
    for item in raw.get("edges", []) or []:
        edges.append(
            GraphEdge(
                id=str(item.get("id") or f"e{len(edges)}"),
                from_node=str(item.get("from")),
                from_port=str(item.get("fromPort") or "out"),
                to_node=str(item.get("to")),
                to_port=str(item.get("toPort") or "in"),
            )
        )
    return Graph(nodes=nodes, edges=edges, subgraphs=dict(raw.get("subgraphs") or {}))


def compile_graph(raw: Dict[str, Any]) -> CompiledGraph:
    graph = parse_graph(raw)
    issues: List[Issue] = []
    outgoing: Dict[Tuple[str, str], List[GraphEdge]] = {}

    seen = set()
    for node in graph.nodes:
        if not node.id:
            issues.append(Issue("error", "节点缺少 id"))
            continue
        if node.id in seen:
            issues.append(Issue("error", f"节点 id 重复: {node.id}", node.id))
        seen.add(node.id)
        contract = get_contract(node.type)
        if not contract:
            issues.append(Issue("error", f"未知节点类型: {node.type}", node.id))
            continue
        if not node.disabled:
            for field_def in contract.fields:
                if field_def.required and node.config.get(field_def.key) in (None, ""):
                    issues.append(Issue("error", f"节点「{contract.title}」缺少必填项: {field_def.label}", node.id))
            outputs = {p.id for p in contract.outputs}
            inputs = {p.id for p in contract.inputs}
            for edge in graph.edges:
                if edge.from_node == node.id and edge.from_port not in outputs:
                    issues.append(
                        Issue("error", f"节点「{contract.title}」没有输出端口 {edge.from_port}", node.id)
                    )
                if edge.to_node == node.id and edge.to_port not in inputs:
                    issues.append(
                        Issue("error", f"节点「{contract.title}」没有输入端口 {edge.to_port}", node.id)
                    )

    node_ids = {node.id for node in graph.nodes}
    for edge in graph.edges:
        if edge.from_node not in node_ids:
            issues.append(Issue("error", f"连线起点不存在: {edge.from_node}"))
        if edge.to_node not in node_ids:
            issues.append(Issue("error", f"连线终点不存在: {edge.to_node}"))
    for node in graph.nodes:
        contract = get_contract(node.type)
        if contract and contract.inputs and not node.disabled:
            incoming = [e for e in graph.edges if e.to_node == node.id]
            if not incoming and node.type != "flow.subgraph":
                issues.append(Issue("warning", f"节点「{contract.title}」没有输入连线", node.id))

    for edge in graph.edges:
        outgoing.setdefault((edge.from_node, edge.from_port), []).append(edge)

    starts = [node for node in graph.nodes if node.type == "run.start" and not node.disabled]
    if not starts:
        issues.append(Issue("error", "工作流至少需要一个「运行开始」节点"))

    # Reachability (ignoring direction of loops) for a warning only.
    reachable = set()
    stack = [node.id for node in starts]
    while stack:
        current = stack.pop()
        if current in reachable:
            continue
        reachable.add(current)
        for edge in graph.edges:
            if edge.from_node == current:
                stack.append(edge.to_node)
    for node in graph.nodes:
        if node.id not in reachable and node.type != "run.start":
            contract = get_contract(node.type)
            issues.append(
                Issue("warning", f"节点「{contract.title if contract else node.type}」从开始节点不可达", node.id)
            )

    return CompiledGraph(graph=graph, issues=issues, outgoing=outgoing, starts=starts)
