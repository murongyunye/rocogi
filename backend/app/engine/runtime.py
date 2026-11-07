from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..contracts import get_contract, get_spec
from .compiler import CompiledGraph, compile_graph
from .expression import evaluate, render_template


class AbortedRun(RuntimeError):
    pass


def _jsonable(value: Any, depth: int = 0) -> Any:
    if depth > 5:
        return "..."
    if value is None or isinstance(value, (bool, int, float, str)):
        if isinstance(value, float):
            return round(value, 4)
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        if len(value) > 30:
            return [_jsonable(v, depth + 1) for v in value[:30]] + ["..."]
        return [_jsonable(v, depth + 1) for v in value]
    if hasattr(value, "image"):
        image = getattr(value, "image")
        shape = getattr(image, "shape", None)
        return {"frame": list(shape) if shape else None, "meta": _jsonable(getattr(value, "meta", {}), depth)}
    try:
        import numpy as np

        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, np.ndarray):
            return {"ndarray": list(value.shape)}
    except Exception:
        pass
    return str(value)


@dataclass
class RunStats:
    steps: int = 0
    node_runs: int = 0
    captures: int = 0
    actions: int = 0
    logs: int = 0
    matches: int = 0
    started_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": self.steps,
            "nodeRuns": self.node_runs,
            "captures": self.captures,
            "actions": self.actions,
            "logs": self.logs,
            "matches": self.matches,
            "durationMs": int((time.time() - self.started_at) * 1000),
        }


class RunContext:
    def __init__(
        self,
        run_id: str,
        workflow: Dict[str, Any],
        graph_raw: Dict[str, Any],
        services: Any,
        settings: Dict[str, Any],
        emit: Callable[[str, Optional[str], str, Dict[str, Any]], None],
        cancel_event: threading.Event,
        run_dir: Path,
        depth: int = 0,
    ) -> None:
        self.run_id = run_id
        self.workflow = workflow
        self.graph_raw = graph_raw
        self.services = services
        self.settings = settings
        self.emit = emit
        self.cancel_event = cancel_event
        self.run_dir = run_dir
        self.depth = depth
        self.vars: Dict[str, Any] = dict(graph_raw.get("variables") or {})
        self.node_outputs: Dict[str, Dict[str, Any]] = {}
        self.stats = RunStats()
        self.frame = None
        self.position: Dict[str, Any] = {"x": 3072 / 2, "y": 5888 / 2, "lat": 0.5, "lng": -0.5}
        self.current_node_id: Optional[str] = None
        self.runtime: Optional[Runtime] = None
        self._artifact_seq = 0

    # ------------------------------------------------------------- expressions
    def env(self) -> Dict[str, Any]:
        return {
            "vars": self.vars,
            "nodes": self.node_outputs,
            "run": {"id": self.run_id, "stats": self.stats.to_dict()},
            "settings": self.settings,
            "frame": getattr(self.frame, "meta", {}) if self.frame is not None else {},
            "position": self.position,
        }

    def eval(self, expression: Any, default: Any = None) -> Any:
        if expression is None:
            return default
        if not isinstance(expression, str):
            return expression
        return evaluate(expression, self.env(), default)

    def text(self, value: Any) -> str:
        return render_template(str(value or ""), self.env())

    def require_frame(self):
        if self.frame is None:
            self.capture()
        return self.frame

    # ------------------------------------------------------------- actions
    def log(self, message: str, data: Optional[Dict[str, Any]] = None, node_id: Optional[str] = None) -> None:
        self.stats.logs += 1
        self.emit("log", node_id or self.current_node_id, self.text(message), data or {})

    def capture(self, region: Optional[List[float]] = None, save: bool = True):
        frame = self.services.capture(self.settings, region=region)
        self.frame = frame
        self.position = self.services.position_for_frame(frame, self.position)
        self.stats.captures += 1
        if save:
            self.save_frame(frame, "frame")
        return frame

    def save_frame(self, frame, label: str = "frame") -> Dict[str, Any]:
        self._artifact_seq += 1
        name = f"{label}-{self._artifact_seq:03d}.jpg"
        path = self.run_dir / name
        try:
            import cv2

            cv2.imwrite(str(path), frame.image, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
        except Exception:
            pass
        artifact = {
            "kind": "screenshot",
            "name": name,
            "url": f"/api/runs/{self.run_id}/artifacts/{name}",
        }
        self.emit("artifact", self.current_node_id, f"截图 {name}", artifact)
        return artifact

    def act(self, action: str, **kwargs) -> None:
        self.services.act(self.settings, action, **kwargs)
        self.stats.actions += 1

    # ------------------------------------------------------------- subgraphs
    def run_subgraph(self, subgraph_id: str) -> Any:
        subgraphs = self.graph_raw.get("subgraphs") or {}
        raw = subgraphs.get(subgraph_id)
        if not raw:
            raise AbortedRun(f"子图不存在: {subgraph_id}")
        if self.depth >= 6:
            raise AbortedRun("子图嵌套层级过深")
        if self.runtime is None:
            raise AbortedRun("运行时未初始化")
        return self.runtime.run_subgraph(self, raw)


class Runtime:
    def __init__(
        self,
        ctx: RunContext,
        compiled: Optional[CompiledGraph] = None,
        max_steps: int = 1200,
        max_visits: int = 80,
    ) -> None:
        self.ctx = ctx
        self.compiled = compiled or compile_graph(ctx.graph_raw)
        self.max_steps = max_steps
        self.max_visits = max_visits
        self._visits: Dict[str, int] = {}
        ctx.runtime = self

    def run(self) -> Dict[str, Any]:
        if not self.compiled.ok:
            raise AbortedRun("; ".join(issue.message for issue in self.compiled.errors))
        self.ctx.emit(
            "run.started",
            None,
            f"开始运行 {self.ctx.workflow.get('name', '')}",
            {"nodeCount": len(self.compiled.graph.nodes), "startCount": len(self.compiled.starts)},
        )
        try:
            for start in self.compiled.starts:
                self._walk(start.id)
        except AbortedRun:
            raise
        return self.ctx.stats.to_dict()

    def run_subgraph(self, parent_ctx: RunContext, raw_graph: Dict[str, Any]) -> Dict[str, Any]:
        compiled = compile_graph(raw_graph)
        if not compiled.ok:
            raise AbortedRun("子图编译失败: " + "; ".join(i.message for i in compiled.errors))
        child_ctx = parent_ctx
        child_ctx.depth = parent_ctx.depth + 1
        child = Runtime(
            child_ctx,
            compiled=compiled,
            max_steps=self.max_steps,
            max_visits=self.max_visits,
        )
        try:
            return child.run()
        finally:
            child_ctx.depth = parent_ctx.depth
            child_ctx.runtime = self

    # ------------------------------------------------------------- execution
    def _walk(self, node_id: str) -> None:
        queue: List[str] = [node_id]
        while queue:
            if self.ctx.cancel_event.is_set():
                raise AbortedRun("运行已取消")
            current_id = queue.pop(0)
            node = self.compiled.graph.node_by_id.get(current_id)
            if node is None:
                continue
            self._visits[current_id] = self._visits.get(current_id, 0) + 1
            if self._visits[current_id] > self.max_visits:
                raise AbortedRun(f"节点循环次数超过上限 {self.max_visits}: {current_id}")
            self.ctx.stats.steps += 1
            if self.ctx.stats.steps > self.max_steps:
                raise AbortedRun(f"运行步数超过上限 {self.max_steps}")

            if node.disabled:
                self.ctx.emit("node.skipped", node.id, "节点已禁用", {})
                next_edges = self.compiled.outgoing.get((node.id, "out"), [])
                for edge in reversed(next_edges):
                    queue.insert(0, edge.to_node)
                continue

            contract = get_contract(node.type)
            spec = get_spec(node.type)
            if spec is None:
                raise AbortedRun(f"未知节点类型: {node.type}")
            _contract, handler = spec
            title = node.title or (contract.title if contract else node.type)
            self.ctx.current_node_id = node.id
            self.ctx.emit("node.started", node.id, title, {"type": node.type})
            started = time.time()
            try:
                result = handler(self.ctx, node)
            except AbortedRun:
                raise
            except Exception as exc:  # noqa: BLE001
                self.ctx.emit(
                    "node.failed",
                    node.id,
                    f"{title} 失败: {exc}",
                    {"type": node.type, "error": str(exc)},
                )
                raise AbortedRun(f"{title} 执行失败: {exc}") from exc
            self.ctx.stats.node_runs += 1
            outputs = _jsonable(result.outputs or {})
            self.ctx.node_outputs[node.id] = outputs
            duration = int((time.time() - started) * 1000)
            self.ctx.emit(
                "node.finished",
                node.id,
                result.message or f"{title} 完成",
                {
                    "type": node.type,
                    "outputs": outputs,
                    "nextPort": result.next_port,
                    "durationMs": duration,
                },
            )
            if result.stop:
                return
            next_edges = self.compiled.outgoing.get((node.id, result.next_port), [])
            for edge in reversed(next_edges):
                queue.insert(0, edge.to_node)
