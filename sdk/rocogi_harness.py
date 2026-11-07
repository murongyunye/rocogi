from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict, List, Optional


class RocogiHarness:
    """Minimal Python client for the Rocogi DeepSeek Harness gateway."""

    def __init__(self, base_url: str = "http://127.0.0.1:8787", timeout: float = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def manifest(self) -> Dict[str, Any]:
        return self._request("GET", "/api/harness/manifest")

    def tools(self) -> Dict[str, Any]:
        return self._request("GET", "/api/harness/tools")

    def act(self, action: str, **params: Any) -> Dict[str, Any]:
        return self._request("POST", "/api/harness/act", {"action": action, "params": params})

    def observe(self) -> Dict[str, Any]:
        return self.act("observe")

    def press(self, key: str, presses: int = 1) -> Dict[str, Any]:
        return self.act("press_key", key=key, presses=presses)

    def click(self, x: float, y: float, button: str = "left") -> Dict[str, Any]:
        return self.act("click", x=x, y=y, button=button)

    def locate(self) -> Dict[str, Any]:
        return self.act("locate")

    def workflows(self) -> List[Dict[str, Any]]:
        return self.act("list_workflows")["result"]

    def run_workflow(self, workflow_id: Optional[str] = None, name: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if workflow_id:
            params["workflowId"] = workflow_id
        if name:
            params["name"] = name
        return self.act("run_workflow", **params)

    def run_onedragon(self, plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.act("run_onedragon", **({"plan": plan} if plan else {}))

    def status(self, run_id: Optional[str] = None) -> Dict[str, Any]:
        return self.act("run_status", **({"runId": run_id} if run_id else {}))

    def start_realtime(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.act("start_realtime", **({"config": config} if config else {}))

    def stop_realtime(self) -> Dict[str, Any]:
        return self.act("stop_realtime")

    def start_tracker(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.act("start_tracker", **({"config": config} if config else {}))

    def stop_tracker(self) -> Dict[str, Any]:
        return self.act("stop_tracker")

    def dex_lookup(
        self,
        name: Optional[str] = None,
        query: Optional[str] = None,
        kind: Optional[str] = None,
        element: Optional[str] = None,
        limit: int = 8,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": limit}
        if name:
            params["name"] = name
        if query:
            params["query"] = query
        if kind:
            params["kind"] = kind
        if element:
            params["element"] = element
        return self.act("dex_lookup", **params)

    def pvp_analyze(self, team: List[str]) -> Dict[str, Any]:
        return self.act("pvp_analyze", team=team)

    def pvp_matchup(
        self,
        team: List[str],
        opponent: str = "wing",
        simulations: int = 40,
        max_turns: int = 30,
    ) -> Dict[str, Any]:
        return self.act(
            "pvp_matchup",
            team=team,
            opponent=opponent,
            simulations=simulations,
            maxTurns=max_turns,
        )


if __name__ == "__main__":
    client = RocogiHarness()
    manifest = client.manifest()
    print(f"Rocogi {manifest['version']} · scene tools: {len(manifest['tools'])}")
    observation = client.observe()
    print(json.dumps(observation["result"], ensure_ascii=False, indent=2)[:1200])
