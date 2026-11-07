from __future__ import annotations

import threading
from pathlib import Path

import pytest

import app.nodes  # noqa: F401  register built-in nodes
from app.config import DEFAULT_SETTINGS, DB_PATH
from app.engine.compiler import compile_graph
from app.engine.expression import ExpressionError, evaluate, render_template
from app.engine.runtime import AbortedRun, RunContext, Runtime
from app.services import Services
from app.storage import Database


def make_services(tmp_path: Path) -> Services:
    db = Database(tmp_path / "test.db")
    return Services(db)


def test_expression_and_template():
    env = {"nodes": {"cap": {"score": 0.82, "kind": "battle"}}, "vars": {"count": 2}}
    assert evaluate("nodes.cap.score > 0.5", env) is True
    assert evaluate("nodes.cap.kind == 'battle' and vars.count < 3", env) is True
    assert render_template("命中 {{nodes.cap.score}} / {{vars.count}}", env) == "命中 0.82 / 2"
    with pytest.raises(ExpressionError):
        evaluate("__import__('os').system('ls')", env)


def test_compiler_reports_invalid_graph():
    result = compile_graph({"nodes": [{"id": "a", "type": "missing.node"}], "edges": []})
    assert not result.ok
    messages = " ".join(issue.message for issue in result.issues)
    assert "未知节点类型" in messages
    assert "运行开始" in messages


def test_runtime_branch_and_cycle(tmp_path):
    services = make_services(tmp_path)
    graph = {
        "nodes": [
            {"id": "start", "type": "run.start", "x": 0, "y": 0, "config": {}},
            {"id": "init", "type": "flow.set_var", "x": 100, "y": 0,
             "config": {"name": "count", "value": "0"}},
            {"id": "loop", "type": "flow.branch", "x": 200, "y": 0,
             "config": {"condition": "vars.count < 3"}},
            {"id": "inc", "type": "flow.set_var", "x": 300, "y": 0,
             "config": {"name": "count", "value": "vars.count + 1"}},
            {"id": "log", "type": "flow.log", "x": 400, "y": 0,
             "config": {"message": "完成 {{vars.count}} 次"}},
            {"id": "end", "type": "run.stop", "x": 500, "y": 0, "config": {}},
        ],
        "edges": [
            {"id": "e1", "from": "start", "fromPort": "out", "to": "init", "toPort": "in"},
            {"id": "e2", "from": "init", "fromPort": "out", "to": "loop", "toPort": "in"},
            {"id": "e3", "from": "loop", "fromPort": "true", "to": "inc", "toPort": "in"},
            {"id": "e4", "from": "inc", "fromPort": "out", "to": "loop", "toPort": "in"},
            {"id": "e5", "from": "loop", "fromPort": "false", "to": "log", "toPort": "in"},
            {"id": "e6", "from": "log", "fromPort": "out", "to": "end", "toPort": "in"},
        ],
        "variables": {},
        "subgraphs": {},
    }
    workflow = {"id": "wf_test", "name": "分支循环", "graph": graph}
    events = []

    def emit(kind, node_id, message, data):
        events.append((kind, node_id, message, data))

    ctx = RunContext(
        run_id="run_test",
        workflow=workflow,
        graph_raw=graph,
        services=services,
        settings=DEFAULT_SETTINGS,
        emit=emit,
        cancel_event=threading.Event(),
        run_dir=tmp_path / "run",
    )
    ctx.run_dir.mkdir(parents=True, exist_ok=True)
    stats = Runtime(ctx, compile_graph(graph)).run()

    assert ctx.vars["count"] == 3
    assert stats["nodeRuns"] > 0
    logs = [event for event in events if event[0] == "log"]
    assert logs and logs[-1][2] == "完成 3 次"
    finished = [event for event in events if event[0] == "node.finished"]
    assert len(finished) == stats["nodeRuns"]


def test_runtime_cycle_guard(tmp_path):
    services = make_services(tmp_path)
    graph = {
        "nodes": [
            {"id": "start", "type": "run.start", "x": 0, "y": 0, "config": {}},
            {"id": "loop", "type": "flow.branch", "x": 100, "y": 0, "config": {"condition": "True"}},
        ],
        "edges": [
            {"id": "e1", "from": "start", "fromPort": "out", "to": "loop", "toPort": "in"},
            {"id": "e2", "from": "loop", "fromPort": "true", "to": "loop", "toPort": "in"},
        ],
    }
    workflow = {"id": "wf_loop", "name": "死循环", "graph": graph}
    ctx = RunContext(
        run_id="run_loop",
        workflow=workflow,
        graph_raw=graph,
        services=services,
        settings=DEFAULT_SETTINGS,
        emit=lambda *args: None,
        cancel_event=threading.Event(),
        run_dir=tmp_path,
    )
    with pytest.raises(AbortedRun):
        Runtime(ctx, compile_graph(graph), max_visits=5).run()


@pytest.mark.skipif(not DB_PATH.exists(), reason="runtime database is not available")
def test_seed_creates_demo_workflows(tmp_path):
    db = Database(tmp_path / "seed.db")
    from app.seed import seed

    seed(db)
    workflows = db.list_workflows()
    assert len(workflows) >= 3
    ids = {workflow["id"] for workflow in workflows}
    assert {"wf_demo_catch", "wf_demo_route", "wf_demo_battle"} <= ids
