from __future__ import annotations

import time

import app.nodes  # noqa: F401  register built-in nodes
from app.config import DEFAULT_SETTINGS
from app.engine.compiler import compile_graph
from app.onedragon import DEFAULT_PLAN, build_graph
from app.run_manager import RunHub, RunManager
from app.seed import seed
from app.services import Services
from app.sessions import RealtimeSession, TrackerSession
from app.storage import Database


def test_onedragon_graph_compiles():
    graph = build_graph(DEFAULT_PLAN)
    compiled = compile_graph(graph)
    assert compiled.ok, [issue.message for issue in compiled.issues]
    assert any(node["type"] == "game.auto_ball" for node in graph["nodes"])


def test_onedragon_run(tmp_path):
    db = Database(tmp_path / "od.db")
    seed(db)
    services = Services(db)
    runs = RunManager(db, services, RunHub())
    workflow = db.get_workflow("wf_onedragon")
    assert workflow
    run = runs.start(workflow, trigger="test")
    result = runs.wait(run["id"], timeout=30)
    assert result["status"] == "succeeded", result.get("error")
    assert result["summary"]["stats"]["nodeRuns"] > 0


def test_realtime_session(tmp_path):
    db = Database(tmp_path / "realtime.db")
    services = Services(db)
    session = RealtimeSession(services)
    session.start({"interval": 0.25, "auto_ball": True, "battle_response": True})
    time.sleep(1.6)
    status = session.status()
    session.stop()
    assert status["counters"]["ticks"] >= 2
    assert status["logs"]


def test_tracker_session(tmp_path):
    db = Database(tmp_path / "tracker.db")
    services = Services(db)
    session = TrackerSession(services)
    session.start({"interval": 0.3, "confidenceMin": 0.2})
    time.sleep(3.0)
    status = session.status()
    session.stop()
    assert status["stats"]["ticks"] >= 1
    assert status["current"] is not None
    assert status["trail"]
