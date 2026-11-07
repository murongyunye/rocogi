from __future__ import annotations

from typing import Any, Dict, Optional

from . import nodes  # noqa: F401  (register node types)
from .config import DB_PATH, ensure_dirs, load_settings
from .onedragon import ONEDRAGON_WORKFLOW_ID, TASK_CATALOG, load_plan, save_plan
from .run_manager import RunHub, RunManager
from .seed import seed
from .services import Services
from .storage import Database

ACTIONS = ("workflows", "run", "status", "stop", "onedragon_plan", "onedragon_run", "settings")


class FlowEnv:
    def __init__(self) -> None:
        ensure_dirs()
        self.db = Database(DB_PATH)
        seed(self.db)
        self.services = Services(self.db)
        self.runs = RunManager(self.db, self.services, RunHub())

    def workflow(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        workflow_id = params.get("workflowId") or params.get("id")
        if workflow_id:
            return self.db.get_workflow(str(workflow_id))
        name = str(params.get("name") or "")
        if name:
            for item in self.db.list_workflows():
                if name in item["name"]:
                    return item
        return None

    def finish(self, run_id: str, timeout: float) -> Dict[str, Any]:
        run = self.runs.wait(run_id, timeout=timeout)
        events = self.db.get_events(run_id) if run else []
        return {"run": run, "events": events[-120:], "lastText": events[-1]["message"] if events else ""}


def dispatch(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    env = FlowEnv()

    if action == "workflows":
        return {"workflows": env.db.list_workflows()}

    if action == "settings":
        settings = load_settings(env.db)
        return {"settings": settings}

    if action == "run":
        workflow = env.workflow(params)
        if not workflow:
            raise ValueError("工作流不存在")
        run = env.runs.start(workflow, trigger=str(params.get("trigger") or "engine"))
        timeout = float(params.get("timeout") or 120)
        return env.finish(run["id"], timeout)

    if action == "status":
        run_id = params.get("runId")
        if not run_id:
            latest = env.db.list_runs(limit=1)
            run_id = latest[0]["id"] if latest else None
        if not run_id:
            raise ValueError("还没有运行记录")
        return env.finish(str(run_id), float(params.get("timeout") or 0))

    if action == "stop":
        run_id = str(params.get("runId") or "")
        if not run_id:
            raise ValueError("stop 需要 runId")
        stopped = env.runs.stop(run_id)
        return {"runId": run_id, "stopping": stopped}

    if action == "onedragon_plan":
        return {
            "plan": load_plan(env.db),
            "tasks": TASK_CATALOG,
            "workflowId": ONEDRAGON_WORKFLOW_ID,
        }

    if action == "onedragon_run":
        plan = save_plan(env.db, params["plan"]) if params.get("plan") else load_plan(env.db)
        workflow = env.db.get_workflow(ONEDRAGON_WORKFLOW_ID)
        if not workflow:
            raise ValueError("一条龙工作流不存在")
        run = env.runs.start(workflow, trigger="engine")
        return {**env.finish(run["id"], float(params.get("timeout") or 180)), "plan": plan}

    raise ValueError(f"未知调度动作: {action}")
