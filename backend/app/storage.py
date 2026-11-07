from __future__ import annotations

import json
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS workflows (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    graph_json TEXT NOT NULL,
    target_slot TEXT NOT NULL DEFAULT 'nrc-game',
    tags_json TEXT NOT NULL DEFAULT '[]',
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    workflow_name TEXT NOT NULL,
    status TEXT NOT NULL,
    trigger TEXT NOT NULL DEFAULT 'manual',
    started_at TEXT NOT NULL,
    finished_at TEXT,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    summary_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS run_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    ts TEXT NOT NULL,
    type TEXT NOT NULL,
    node_id TEXT,
    message TEXT NOT NULL DEFAULT '',
    data_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_run_events_run ON run_events(run_id, seq);
CREATE TABLE IF NOT EXISTS resources (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    tags_json TEXT NOT NULL DEFAULT '[]',
    data_json TEXT NOT NULL DEFAULT '{}',
    path TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    # ---------------------------------------------------------------- workflows
    def list_workflows(self) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM workflows ORDER BY updated_at DESC"
            ).fetchall()
        result = [self._row_workflow(row) for row in rows]
        for item in result:
            with self._lock:
                last = self._conn.execute(
                    "SELECT * FROM runs WHERE workflow_id=? ORDER BY started_at DESC LIMIT 1",
                    (item["id"],),
                ).fetchone()
            item["lastRun"] = self._row_run(last) if last else None
        return result

    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM workflows WHERE id=?", (workflow_id,)
            ).fetchone()
        return self._row_workflow(row) if row else None

    def create_workflow(
        self,
        name: str,
        description: str,
        graph: Dict[str, Any],
        tags: Optional[List[str]] = None,
        target_slot: str = "nrc-game",
        workflow_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        workflow_id = workflow_id or _new_id("wf")
        ts = now_iso()
        with self._lock:
            self._conn.execute(
                "INSERT INTO workflows (id,name,description,graph_json,target_slot,tags_json,revision,created_at,updated_at)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    workflow_id,
                    name,
                    description,
                    json.dumps(graph, ensure_ascii=False),
                    target_slot,
                    json.dumps(tags or [], ensure_ascii=False),
                    1,
                    ts,
                    ts,
                ),
            )
            self._conn.commit()
        return self.get_workflow(workflow_id)  # type: ignore[return-value]

    def update_workflow(self, workflow_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        current = self.get_workflow(workflow_id)
        if not current:
            return None
        graph = patch.get("graph", current["graph"])
        payload = {
            "name": patch.get("name", current["name"]),
            "description": patch.get("description", current["description"]),
            "graph_json": json.dumps(graph, ensure_ascii=False),
            "target_slot": patch.get("targetSlot", current["targetSlot"]),
            "tags_json": json.dumps(patch.get("tags", current["tags"]), ensure_ascii=False),
            "revision": current["revision"] + 1,
            "updated_at": now_iso(),
        }
        with self._lock:
            self._conn.execute(
                "UPDATE workflows SET name=?,description=?,graph_json=?,target_slot=?,tags_json=?,revision=?,updated_at=?"
                " WHERE id=?",
                (
                    payload["name"],
                    payload["description"],
                    payload["graph_json"],
                    payload["target_slot"],
                    payload["tags_json"],
                    payload["revision"],
                    payload["updated_at"],
                    workflow_id,
                ),
            )
            self._conn.commit()
        return self.get_workflow(workflow_id)

    def delete_workflow(self, workflow_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM workflows WHERE id=?", (workflow_id,))
            self._conn.commit()
        return cur.rowcount > 0

    # ---------------------------------------------------------------- runs
    def create_run(
        self,
        run_id: str,
        workflow: Dict[str, Any],
        trigger: str = "manual",
        summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            self._conn.execute(
                "INSERT INTO runs (id,workflow_id,workflow_name,status,trigger,started_at,summary_json)"
                " VALUES (?,?,?,?,?,?,?)",
                (
                    run_id,
                    workflow["id"],
                    workflow["name"],
                    "running",
                    trigger,
                    now_iso(),
                    json.dumps(summary or {}, ensure_ascii=False),
                ),
            )
            self._conn.commit()
        return self.get_run(run_id)  # type: ignore[return-value]

    def finish_run(
        self,
        run_id: str,
        status: str,
        error: Optional[str] = None,
        duration_ms: int = 0,
        summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        current = self.get_run(run_id)
        merged = {**(current["summary"] if current else {}), **(summary or {})}
        with self._lock:
            self._conn.execute(
                "UPDATE runs SET status=?,finished_at=?,duration_ms=?,error=?,summary_json=? WHERE id=?",
                (
                    status,
                    now_iso(),
                    duration_ms,
                    error,
                    json.dumps(merged, ensure_ascii=False),
                    run_id,
                ),
            )
            self._conn.commit()

    def list_runs(self, limit: int = 50, workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            if workflow_id:
                rows = self._conn.execute(
                    "SELECT * FROM runs WHERE workflow_id=? ORDER BY started_at DESC LIMIT ?",
                    (workflow_id, limit),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
                ).fetchall()
        return [self._row_run(row) for row in rows]

    def recover_stale_runs(self) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE runs SET status='failed', finished_at=?, error=? WHERE status='running'",
                (now_iso(), "服务重启，运行已中断"),
            )
            self._conn.commit()

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        return self._row_run(row) if row else None

    def add_event(
        self,
        run_id: str,
        seq: int,
        event_type: str,
        message: str = "",
        node_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        item = {
            "seq": seq,
            "ts": now_iso(),
            "type": event_type,
            "nodeId": node_id,
            "message": message,
            "data": data or {},
        }
        with self._lock:
            self._conn.execute(
                "INSERT INTO run_events (run_id,seq,ts,type,node_id,message,data_json) VALUES (?,?,?,?,?,?,?)",
                (
                    run_id,
                    seq,
                    item["ts"],
                    event_type,
                    node_id,
                    message,
                    json.dumps(data or {}, ensure_ascii=False),
                ),
            )
            self._conn.commit()
        return item

    def get_events(self, run_id: str, after: int = 0, limit: int = 2000) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM run_events WHERE run_id=? AND seq>? ORDER BY seq LIMIT ?",
                (run_id, after, limit),
            ).fetchall()
        return [
            {
                "seq": row["seq"],
                "ts": row["ts"],
                "type": row["type"],
                "nodeId": row["node_id"],
                "message": row["message"],
                "data": json.loads(row["data_json"]),
            }
            for row in rows
        ]

    # ---------------------------------------------------------------- resources
    def list_resources(self, kind: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            if kind:
                rows = self._conn.execute(
                    "SELECT * FROM resources WHERE kind=? ORDER BY created_at", (kind,)
                ).fetchall()
            else:
                rows = self._conn.execute("SELECT * FROM resources ORDER BY kind,created_at").fetchall()
        return [
            {
                "id": row["id"],
                "kind": row["kind"],
                "name": row["name"],
                "tags": json.loads(row["tags_json"]),
                "data": json.loads(row["data_json"]),
                "path": row["path"],
                "createdAt": row["created_at"],
            }
            for row in rows
        ]

    def upsert_resource(
        self,
        resource_id: str,
        kind: str,
        name: str,
        data: Optional[Dict[str, Any]] = None,
        path: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO resources (id,kind,name,tags_json,data_json,path,created_at) VALUES (?,?,?,?,?,?,?)"
                " ON CONFLICT(id) DO UPDATE SET kind=excluded.kind,name=excluded.name,"
                "tags_json=excluded.tags_json,data_json=excluded.data_json,path=excluded.path",
                (
                    resource_id,
                    kind,
                    name,
                    json.dumps(tags or [], ensure_ascii=False),
                    json.dumps(data or {}, ensure_ascii=False),
                    path,
                    now_iso(),
                ),
            )
            self._conn.commit()

    # ---------------------------------------------------------------- settings
    def get_setting(self, key: str, default: Any = None) -> Any:
        with self._lock:
            row = self._conn.execute("SELECT value_json FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row["value_json"]) if row else default

    def set_setting(self, key: str, value: Any) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO settings (key,value_json) VALUES (?,?)"
                " ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json",
                (key, json.dumps(value, ensure_ascii=False)),
            )
            self._conn.commit()

    # ---------------------------------------------------------------- helpers
    def _row_workflow(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "graph": json.loads(row["graph_json"]),
            "targetSlot": row["target_slot"],
            "tags": json.loads(row["tags_json"]),
            "revision": row["revision"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def _row_run(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "workflowId": row["workflow_id"],
            "workflowName": row["workflow_name"],
            "status": row["status"],
            "trigger": row["trigger"],
            "startedAt": row["started_at"],
            "finishedAt": row["finished_at"],
            "durationMs": row["duration_ms"],
            "error": row["error"],
            "summary": json.loads(row["summary_json"]),
        }


def _new_id(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000):x}{threading.get_ident() % 4096:03x}"
