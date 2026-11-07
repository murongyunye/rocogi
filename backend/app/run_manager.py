from __future__ import annotations

import queue
import threading
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import RUNTIME_DIR, load_settings
from .engine import runtime as runtime_module
from .engine.compiler import compile_graph
from .engine.runtime import AbortedRun, RunContext, Runtime
from .storage import _new_id


class RunHub:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: Dict[str, List[queue.Queue]] = {}

    def subscribe(self, run_id: str) -> queue.Queue:
        channel: queue.Queue = queue.Queue(maxsize=1000)
        with self._lock:
            self._subscribers.setdefault(run_id, []).append(channel)
        return channel

    def unsubscribe(self, run_id: str, channel: queue.Queue) -> None:
        with self._lock:
            channels = self._subscribers.get(run_id, [])
            if channel in channels:
                channels.remove(channel)
            if not channels:
                self._subscribers.pop(run_id, None)

    def publish(self, run_id: str, event: Dict[str, Any]) -> None:
        with self._lock:
            channels = list(self._subscribers.get(run_id, []))
        for channel in channels:
            try:
                channel.put_nowait(event)
            except queue.Full:
                pass


class RunManager:
    def __init__(self, db, services, hub: RunHub) -> None:
        self.db = db
        self.services = services
        self.hub = hub
        self._lock = threading.RLock()
        self._threads: Dict[str, threading.Thread] = {}
        self._cancel: Dict[str, threading.Event] = {}
        self._last_run: Dict[str, str] = {}

    def start(self, workflow: Dict[str, Any], trigger: str = "manual") -> Dict[str, Any]:
        compiled = compile_graph(workflow["graph"])
        if not compiled.ok:
            raise ValueError("; ".join(issue.message for issue in compiled.errors))
        run_id = _new_id("run")
        summary = {
            "nodeCount": len(compiled.graph.nodes),
            "warnings": [issue.message for issue in compiled.issues if issue.level == "warning"],
        }
        self.db.create_run(run_id, workflow, trigger=trigger, summary=summary)
        cancel = threading.Event()
        thread = threading.Thread(
            target=self._execute,
            args=(run_id, workflow, cancel),
            daemon=True,
            name=f"run-{run_id}",
        )
        with self._lock:
            self._threads[run_id] = thread
            self._cancel[run_id] = cancel
            self._last_run[workflow["id"]] = run_id
        thread.start()
        return self.db.get_run(run_id)  # type: ignore[return-value]

    def stop(self, run_id: str) -> bool:
        with self._lock:
            cancel = self._cancel.get(run_id)
        if not cancel:
            return False
        cancel.set()
        return True

    def wait(self, run_id: str, timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        with self._lock:
            thread = self._threads.get(run_id)
        if thread:
            thread.join(timeout=timeout)
        return self.db.get_run(run_id)

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for thread in self._threads.values() if thread.is_alive())

    def last_run_id(self, workflow_id: str) -> Optional[str]:
        with self._lock:
            return self._last_run.get(workflow_id)

    # ------------------------------------------------------------------ worker
    def _execute(self, run_id: str, workflow: Dict[str, Any], cancel: threading.Event) -> None:
        seq = 0
        emit_lock = threading.Lock()
        status = "succeeded"
        error: Optional[str] = None

        def emit(event_type: str, node_id: Optional[str], message: str, data: Dict[str, Any]) -> None:
            nonlocal seq
            with emit_lock:
                seq += 1
                event = self.db.add_event(run_id, seq, event_type, message, node_id, data)
            event["runId"] = run_id
            self.hub.publish(run_id, event)

        try:
            settings = load_settings(self.db)
            engine = settings.get("engine", {})
            run_dir = RUNTIME_DIR / "runs" / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            ctx = RunContext(
                run_id=run_id,
                workflow=workflow,
                graph_raw=workflow["graph"],
                services=self.services,
                settings=settings,
                emit=emit,
                cancel_event=cancel,
                run_dir=run_dir,
            )
            engine_runtime = Runtime(
                ctx,
                compiled=compile_graph(workflow["graph"]),
                max_steps=int(engine.get("max_steps", 1200) or 1200),
                max_visits=int(engine.get("max_visits", 80) or 80),
            )
            stats = engine_runtime.run()
            summary = {
                "stats": stats,
                "vars": {key: value for key, value in ctx.vars.items() if isinstance(value, (int, float, str, bool))},
                "position": ctx.position,
                "nodeOutputs": {
                    key: {
                        field: value
                        for field, value in (output or {}).items()
                        if isinstance(value, (int, float, str, bool)) or value is None
                    }
                    for key, output in ctx.node_outputs.items()
                },
            }
            self.db.finish_run(run_id, status, duration_ms=stats.get("durationMs", 0), summary=summary)
        except AbortedRun as exc:
            status = "stopped" if cancel.is_set() else "failed"
            error = str(exc)
        except Exception as exc:  # noqa: BLE001
            status = "failed"
            error = f"{exc}"
            traceback.print_exc()
        finally:
            current = self.db.get_run(run_id) or {}
            if current.get("status") == "running":
                self.db.finish_run(
                    run_id,
                    status,
                    error=error,
                    duration_ms=current.get("durationMs", 0),
                    summary=current.get("summary", {}),
                )
            final = self.db.get_run(run_id) or {}
            emit(
                "run.finished",
                None,
                {"succeeded": "运行完成", "failed": f"运行失败: {error}", "stopped": "运行已停止"}.get(status, status),
                {
                    "status": status,
                    "error": error,
                    "summary": final.get("summary", {}),
                },
            )
            with self._lock:
                self._threads.pop(run_id, None)
                self._cancel.pop(run_id, None)
