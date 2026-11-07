"""Suite kernel: config, registry, evidence, logging, supervisor."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_toml(path: str) -> dict:
    with open(path, "rb") as fh:
        return tomllib.load(fh)


class Suite:
    def __init__(self):
        self.root = ROOT
        self.config_path = os.path.join(ROOT, "config", "suite.toml")
        self.cfg = load_toml(self.config_path)
        self.config_text = open(self.config_path, encoding="utf-8").read()
        self.config_sha256 = hashlib.sha256(self.config_text.encode("utf-8")).hexdigest()

    # ---------------------------------------------------------------- paths
    def path(self, *parts) -> str:
        return os.path.join(self.root, *parts)

    @property
    def logs_dir(self) -> str:
        return self.path(self.cfg["paths"]["logs"])

    @property
    def runs_dir(self) -> str:
        return self.path(self.cfg["paths"]["runs"])

    @property
    def assets_dir(self) -> str:
        return self.path(self.cfg["paths"]["assets"])

    def engine_names(self) -> list[str]:
        return list(self.cfg["engines"]["order"])

    def engine_cfg(self, name: str) -> dict:
        return load_toml(self.path("config", "engines", f"{name}.toml"))

    def engine_python(self, name: str) -> str:
        venv = self.engine_cfg(name)["engine"]["venv"]
        return self.path(venv, "Scripts", "python.exe")

    def engine_script(self, name: str) -> str:
        return self.path(self.engine_cfg(name)["engine"]["script"])

    def engine_config(self, name: str) -> str:
        return self.path("config", "engines", f"{name}.toml")

    def uv_exe(self) -> str:
        rel = self.cfg.get("runtime", {}).get("uv", "")
        return os.path.normpath(self.path(rel)) if rel else ""

    # ---------------------------------------------------------------- registry
    def components(self) -> list[dict]:
        path = self.path("config", "components.toml")
        if not os.path.exists(path):
            return []
        return load_toml(path).get("components", [])

    def engine_status(self, name: str) -> str:
        py = self.engine_python(name)
        if not os.path.exists(py):
            return "missing-venv"
        return "ready"

    def component_table(self) -> list[dict]:
        status = {n: self.engine_status(n) for n in self.engine_names()}
        rows = []
        for c in self.components():
            engine = c["engine"]
            state = c.get("status", "ready")
            reason = c.get("reason", "")
            if state == "ready":
                state = "ready" if status.get(engine) == "ready" else "missing-deps"
                if state != "ready":
                    reason = f"engine venv missing: {self.path(self.engine_cfg(engine)['engine']['venv'])}"
            rows.append(
                {
                    "id": c["id"],
                    "engine": engine,
                    "entry": c["entry"],
                    "config": c["config"],
                    "deps": c["deps"],
                    "status": state,
                    "implemented": bool(c.get("implemented", state == "ready")),
                    "reason": reason,
                }
            )
        return rows

    # ---------------------------------------------------------------- evidence
    def new_run_id(self) -> str:
        return time.strftime("%Y%m%d-%H%M%S")

    def run_dir(self, run_id: str) -> str:
        return self.path("runs", run_id)

    def log_dir(self, run_id: str) -> str:
        return self.path("logs", run_id)

    def engine_versions(self) -> dict:
        versions = {"kernel": {"python": sys.version.split()[0], "suite": self.cfg["suite"]["version"]}}
        for name in self.engine_names():
            py = self.engine_python(name)
            if not os.path.exists(py):
                versions[name] = {"status": "missing-venv"}
                continue
            out = subprocess.run([py, "-c", "import sys;print(sys.version.split()[0])"],
                                 capture_output=True, text=True, timeout=30)
            # engine venvs are created by uv and contain no pip -> freeze through uv
            uv = self.uv_exe()
            if os.path.exists(uv):
                frozen = subprocess.run([uv, "pip", "freeze", "--python", py],
                                        capture_output=True, text=True, timeout=60)
            else:
                frozen = subprocess.run([py, "-m", "pip", "freeze"], capture_output=True, text=True, timeout=60)
            pkgs = [l for l in frozen.stdout.splitlines() if l.strip()] if frozen.returncode == 0 else []
            versions[name] = {"python": out.stdout.strip(), "packages": pkgs,
                              "packagesError": None if frozen.returncode == 0 else frozen.stderr.strip()[:300]}
            lock = os.path.join(os.path.dirname(self.engine_python(name)), "..", "requirements.lock")
            lock = os.path.normpath(lock)
            versions[name]["lock"] = os.path.relpath(lock, self.root) if os.path.exists(lock) else None
        return versions

    def write_manifest(self, run_id: str, engines: list[str], mode: str, extra: dict | None = None) -> dict:
        os.makedirs(self.run_dir(run_id), exist_ok=True)
        manifest = {
            "schema_version": 1,
            "run_id": run_id,
            "mode": mode,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "config": {
                "path": os.path.relpath(self.config_path, self.root),
                "sha256": self.config_sha256,
                "snapshot": self.config_text,
                "engines": {n: open(self.engine_config(n), encoding="utf-8").read() for n in engines},
            },
            "engines": self.engine_versions(),
            "components": [c for c in self.component_table() if c["engine"] in engines],
            "extra": extra or {},
        }
        self.write_json(os.path.join(self.run_dir(run_id), "manifest.json"), manifest)
        return manifest

    def write_json(self, path: str, data) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

    def load_json(self, path: str, default=None):
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    # ---------------------------------------------------------------- launch
    def spawn(self, name: str, run_id: str, *, once: bool, action: str | None, interval: float | None, mode: str) -> dict:
        py = self.engine_python(name)
        script = self.engine_script(name)
        if not os.path.exists(py):
            return {"engine": name, "status": "missing-venv", "path": py}
        log_dir = self.log_dir(run_id)
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"{name}.jsonl")
        action = action or self.engine_cfg(name)["engine"]["action"]
        interval = interval if interval is not None else float(self.engine_cfg(name)["engine"]["interval"])
        cmd = [py, script, "--config", self.engine_config(name), "--log", log_path,
               "--run-id", run_id, "--action", action, "--interval", str(interval)]
        if once:
            cmd.append("--once")
        kwargs = {}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
        return {"engine": name, "status": "started", "pid": proc.pid, "log": os.path.relpath(log_path, self.root),
                "action": action, "proc": proc}


def tail_events(log_path: str, limit: int = 5) -> list:
    if not os.path.exists(log_path):
        return []
    lines = []
    with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if line:
                lines.append(line)
    out = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
