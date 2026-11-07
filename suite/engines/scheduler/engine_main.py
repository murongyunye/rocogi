"""scheduler engine - capture FSM (AutoCapture) + Rocogi DAG + one-dragon plan.

Integration sources (MERGE_MAP):
  state machine / realtime : AutoCapture state_machine.py (CaptureStateMachine)
  workflow DAG             : Rocogi backend/app/engine (existing Python DAG, yotta only as schema)
Own venv / process, no imports from other suite engines.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

SUITE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROCogi = os.path.dirname(SUITE)
WORK = os.path.dirname(ROCogi)
CAPTURE_ROOT = os.path.join(WORK, "rocogi", "vendor", "Tsuann-RocoKingdom-AutoCapture")
ROCogi_BACKEND = os.path.join(ROCogi, "backend")
sys.path.insert(0, ROCogi_BACKEND)
sys.path.insert(0, CAPTURE_ROOT)

ENGINE = "scheduler"
RUN_ID = ""
LOG_PATH = ""


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


def _state_name(machine) -> str:
    s = machine.state
    if callable(s):
        s = s()
    return getattr(s, "name", str(s))


# --------------------------------------------------------------------------
# DAG helpers
# --------------------------------------------------------------------------
def _ensure_nodes():
    """app.nodes must be imported *before* compiling so all contracts are registered."""
    import app.nodes  # noqa: F401  (registers every node type)


def _raw_from_cfg(cfg):
    nodes = cfg["dag"]["nodes"]
    edges = cfg["dag"].get("edges", [])
    raw = {
        "nodes": [{"id": n["id"], "type": n["type"], "config": n.get("config", {})} for n in nodes],
        # suite config uses source/target; Rocogi compiler expects from/to
        "edges": [
            {"id": e.get("id") or f"e{i}", "from": e["source"], "to": e["target"]}
            for i, e in enumerate(edges)
        ],
    }
    if "subgraphs" in cfg["dag"]:
        raw["subgraphs"] = cfg["dag"]["subgraphs"]
    return raw


def _issue_rows(compiled):
    return [{"level": i.level, "message": i.message, "node": i.node_id} for i in compiled.issues]


def action_dag(cfg):
    _ensure_nodes()
    from app.engine import compiler

    raw = _raw_from_cfg(cfg)
    compiled = compiler.compile_graph(raw)
    issues = _issue_rows(compiled)
    from app.contracts import catalog

    cat = catalog()
    out = {
        "action": "dag",
        "nodeCount": len(compiled.graph.nodes),
        "edgeCount": len(compiled.graph.edges),
        "issues": issues,
        "issueCount": len(issues),
        "contractCatalog": len(cat.get("nodes", [])) if isinstance(cat, dict) else None,
        "status": "ok" if not issues else "failed",
        "component": "scheduler.dag",
    }
    return out


class _EmitCollector:
    def __init__(self):
        self.events = []

    def __call__(self, kind, node_id, message, data):
        self.events.append({"kind": kind, "nodeId": node_id, "message": message,
                            "data": data if isinstance(data, dict) else {}})


class _ServicesStub:
    """Scheduler self-test graphs only use flow nodes; hardware nodes fail loudly."""

    def capture(self, settings, region=None):
        raise RuntimeError("capture node is owned by the capture engine; not available in scheduler")

    def position_for_frame(self, frame, position):
        return position

    def act(self, settings, action, **kwargs):
        raise RuntimeError("input nodes are owned by the input engine; not available in scheduler")


def _run_graph(raw, run_id, max_steps=200):
    from app.engine.compiler import compile_graph
    from app.engine.runtime import RunContext, Runtime
    import threading

    _ensure_nodes()
    compiled = compile_graph(raw)
    if not compiled.ok:
        raise RuntimeError("; ".join(i.message for i in compiled.errors))
    collector = _EmitCollector()
    ctx = RunContext(
        run_id=run_id,
        workflow={"name": "scheduler-self-test"},
        graph_raw=raw,
        services=_ServicesStub(),
        settings={},
        emit=collector,
        cancel_event=threading.Event(),
        run_dir=__import__("pathlib").Path(os.path.join(SUITE, "runs", run_id)),
    )
    stats = Runtime(ctx, compiled=compiled, max_steps=max_steps).run()
    return stats, collector.events, compiled


FLOW_GRAPH = {
    "nodes": [
        {"id": "start", "type": "run.start", "config": {}},
        {"id": "each", "type": "flow.foreach",
         "config": {"items": "[1, 2, 3]", "itemVar": "item", "subgraphId": "body"}},
        {"id": "gate", "type": "flow.branch", "config": {"condition": "vars.item > 1"}},
        {"id": "big", "type": "flow.log", "config": {"message": "item {{vars.item}} > 1"}},
        {"id": "small", "type": "flow.log", "config": {"message": "item {{vars.item}} <= 1"}},
        {"id": "stop", "type": "run.stop", "config": {}},
    ],
    "edges": [
        {"id": "e0", "from": "start", "to": "each"},
        {"id": "e1", "from": "each", "to": "gate"},
        {"id": "e2", "from": "gate", "fromPort": "true", "to": "big"},
        {"id": "e3", "from": "gate", "fromPort": "false", "to": "small"},
        {"id": "e4", "from": "big", "to": "stop"},
        {"id": "e5", "from": "small", "to": "stop"},
    ],
    "subgraphs": {
        "body": {
            "nodes": [
                {"id": "b_start", "type": "run.start", "config": {}},
                {"id": "b_log", "type": "flow.log", "config": {"message": "body item {{vars.item}}"}},
                {"id": "b_stop", "type": "run.stop", "config": {}},
            ],
            "edges": [
                {"id": "b0", "from": "b_start", "to": "b_log"},
                {"id": "b1", "from": "b_log", "to": "b_stop"},
            ],
        }
    },
}


EXEC_GRAPH = {
    "nodes": [
        {"id": "start", "type": "run.start", "config": {}},
        {"id": "set", "type": "flow.set_var", "config": {"name": "hits", "value": "2"}},
        {"id": "gate", "type": "flow.branch", "config": {"condition": "vars.hits > 1"}},
        {"id": "yes", "type": "flow.log", "config": {"message": "hits={{vars.hits}}"}},
        {"id": "no", "type": "flow.log", "config": {"message": "no hits"}},
        {"id": "stop", "type": "run.stop", "config": {}},
    ],
    "edges": [
        {"id": "e0", "from": "start", "to": "set"},
        {"id": "e1", "from": "set", "to": "gate"},
        {"id": "e2", "from": "gate", "fromPort": "true", "to": "yes"},
        {"id": "e3", "from": "gate", "fromPort": "false", "to": "no"},
        {"id": "e4", "from": "yes", "to": "stop"},
        {"id": "e5", "from": "no", "to": "stop"},
    ],
}


def action_executor(cfg):
    run_id = RUN_ID or "scheduler-executor"
    stats, events, compiled = _run_graph(EXEC_GRAPH, run_id, max_steps=int(cfg["session"].get("max_steps", 200)))
    return {
        "action": "executor",
        "status": "ok",
        "stats": stats,
        "eventCount": len(events),
        "eventKinds": sorted({e["kind"] for e in events}),
        "nodeTypes": [n.type for n in compiled.graph.nodes],
        "components": ["scheduler.executor", "scheduler.dag"],
    }


def action_flow(cfg):
    """branch + foreach + subgraph exercised through the real Rocogi runtime."""
    run_id = RUN_ID or "scheduler-flow"
    stats, events, compiled = _run_graph(FLOW_GRAPH, run_id, max_steps=int(cfg["session"].get("max_steps", 200)))
    subgraph_runs = sum(1 for e in events if e["kind"] == "run.started")
    return {
        "action": "flow",
        "status": "ok",
        "stats": stats,
        "subgraphRuns": subgraph_runs,
        "logs": [e["message"] for e in events if e["kind"] == "log"],
        "nodeTypes": sorted({n.type for n in compiled.graph.nodes}),
        "components": ["scheduler.branch", "scheduler.foreach", "scheduler.subgraph"],
    }


def action_events(cfg):
    """event bus: append to the run's events.jsonl with a monotonic seq."""
    run_id = RUN_ID or "scheduler-events"
    path = os.path.join(SUITE, "runs", run_id, "events.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    last_seq = 0
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    last_seq = max(last_seq, int(json.loads(line).get("seq") or 0))
                except (json.JSONDecodeError, ValueError):
                    continue
    rows = []
    for kind in ("node-attempt", "adapter-action", "node-status"):
        last_seq += 1
        row = {"seq": last_seq, "ts": round(time.time(), 3), "engine": ENGINE,
               "type": "event_bus", "kind": kind, "run_id": run_id}
        rows.append(row)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"action": "events", "path": os.path.relpath(path, SUITE), "appended": rows,
            "lastSeq": last_seq, "component": "scheduler.event_bus"}


def action_onedragon(cfg):
    """One-dragon plan: BetterGI task-list semantics, executed on the Rocogi DAG runtime."""
    tasks = cfg.get("onedragon", {}).get("tasks", [])
    enabled = [t for t in tasks if t.get("enabled", True)]
    enabled.sort(key=lambda t: t.get("order", 99))
    plan = [
        {"step": i + 1, "task": t["id"], "component": t.get("component", ""), "order": t.get("order", 99)}
        for i, t in enumerate(enabled)
    ]
    return {
        "action": "onedragon_plan",
        "status": "ok",
        "tasksTotal": len(tasks),
        "tasksEnabled": len(enabled),
        "plan": plan,
        "runtime": "Rocogi Python DAG (yotta used only as schema reference)",
        "component": "scheduler.onedragon_plan",
    }


def action_fsm(cfg):
    import state_machine as sm

    machine = sm.CaptureStateMachine()
    trace = [{"event": "init", "state": _state_name(machine)}]
    for name in ("start", "pause", "resume", "stop"):
        fn = getattr(machine, name, None)
        if callable(fn):
            fn()
            trace.append({"event": name, "state": _state_name(machine)})
    return {
        "action": "fsm",
        "states": [s.name for s in sm.State],
        "events": [e.name for e in sm.Event],
        "trace": trace,
        "component": "scheduler.capture_fsm",
    }


def action_session(cfg):
    return {
        "action": "session_loop",
        "intervalMs": cfg["session"]["interval_ms"],
        "stages": ["scan", "track", "aim", "throw", "verify"],
        "components": ["scheduler.session_loop", "scheduler.capture_fsm", "scheduler.onedragon_plan"],
        "status": "ready",
    }


ACTIONS = {
    "fsm": action_fsm,
    "dag": action_dag,
    "executor": action_executor,
    "flow": action_flow,
    "events": action_events,
    "onedragon": action_onedragon,
    "session": action_session,
}


def main() -> int:
    global RUN_ID, LOG_PATH
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--log", default="")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--action", default="fsm")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=float, default=1.0)
    args = ap.parse_args()

    RUN_ID = args.run_id
    LOG_PATH = args.log
    cfg = load_toml(args.config)
    emit(args.log, "ready", run_id=args.run_id, config=args.config, python=sys.version.split()[0],
         components=["scheduler.dag", "scheduler.executor", "scheduler.branch", "scheduler.foreach",
                     "scheduler.subgraph", "scheduler.event_bus", "scheduler.session_loop",
                     "scheduler.capture_fsm", "scheduler.onedragon_plan"])

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
