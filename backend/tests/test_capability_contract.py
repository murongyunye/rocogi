from __future__ import annotations

import copy
import re

from app import capability_contract, harness, harness_actions, harness_contracts
from app.api import routes
from app.capability_contract import CONTRACT_VERSION, actions_document, nodes_document

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _tools():
    return {
        item["function"]["name"][len("rocogi_"):]: item["function"]
        for item in harness.tools_schema()
    }


def test_nodes_endpoint_shape():
    document = routes.nodes_catalog()
    assert document["contract_version"] == CONTRACT_VERSION
    assert HEX64.match(document["fingerprint"])
    assert document["node_count"] == 24
    assert len(document["nodes"]) == 24
    assert document["categories"]
    types = [node["type"] for node in document["nodes"]]
    assert len(set(types)) == 24
    for node in document["nodes"]:
        assert node["type"] and node["title"]
        assert isinstance(node["effectful"], bool)
        assert isinstance(node["inputs"], list) and isinstance(node["outputs"], list)
        for port in node["inputs"] + node["outputs"]:
            assert set(port) >= {"id", "label", "kind"}
        for field in node["fields"]:
            assert set(field) >= {"key", "label", "type", "required"}
            assert isinstance(field["required"], bool)
    delay = next(node for node in document["nodes"] if node["type"] == "flow.delay")
    ms = next(field for field in delay["fields"] if field["key"] == "ms")
    assert ms["type"] == "number" and ms["required"] is True
    assert ms["minimum"] == 0 and ms["maximum"] == 60000
    assert all("categoryLabel" in node and "accent" in node for node in document["nodes"])


def test_actions_endpoint_shape():
    document = routes.actions_catalog()
    assert document["contract_version"] == CONTRACT_VERSION
    assert HEX64.match(document["fingerprint"])
    tools = _tools()
    raw_names = [item["function"]["name"] for item in harness.tools_schema()]
    assert len(raw_names) == len(set(raw_names))
    assert document["action_count"] == 33
    assert document["action_count"] == len(tools)
    actions = document["actions"]
    names = [item["name"] for item in actions]
    assert len(names) == len(set(names))
    assert set(names) == set(tools)
    assert set(names) == set(harness_actions.ACTIONS) | set(
        harness_contracts.RUNTIME_OUTPUT_FIELDS
    )
    assert {"capture", "move"} <= set(tools)
    for item in actions:
        name = item["name"]
        assert item["tool"] == "rocogi_" + name
        schema = tools[name]["parameters"]
        expected_required = harness_contracts.ACTION_REQUIRED_FIELDS.get(name)
        if expected_required is None:
            expected_required = tuple(schema.get("required") or ())
        assert item["required"] == list(expected_required)
        assert item["required_any"] == list(
            harness_contracts.ACTION_REQUIRED_ANY.get(name, ())
        )
        if name in harness_contracts.ACTION_OUTPUT_FIELDS:
            expected_output = list(harness_contracts.ACTION_OUTPUT_FIELDS[name])
        else:
            expected_output = list(harness_contracts.RUNTIME_OUTPUT_FIELDS[name])
        assert item["output_fields"] == expected_output
        assert item["risk"] in capability_contract.RISK_LEVELS
        assert item["effectful"] is (item["risk"] != "read_only")
        assert isinstance(item["available"], bool)
        if item["available"]:
            assert item["unavailable_reason"] is None
        else:
            assert item["unavailable_reason"]
        param_names = {param["name"] for param in item["parameters"]}
        assert set(item["required"]) <= param_names
        assert set(item["required_any"]) <= param_names
        for param in item["parameters"]:
            assert param["required"] == (param["name"] in item["required"])
            prop = schema["properties"][param["name"]]
            assert param["type"] == prop.get("type")
            for key in ("enum", "minimum", "maximum", "maxItems", "items"):
                if key in prop:
                    assert param[key] == prop[key]


def test_action_metadata_covers_every_tool():
    tools = set(_tools())
    assert set(harness_contracts.ACTION_RISK) == tools
    assert set(harness_contracts.ACTION_OUTPUT_FIELDS) | set(
        harness_contracts.RUNTIME_OUTPUT_FIELDS
    ) == tools
    assert not (
        set(harness_contracts.ACTION_OUTPUT_FIELDS)
        & set(harness_contracts.RUNTIME_OUTPUT_FIELDS)
    )
    assert set(harness_contracts.ACTION_REQUIRED_FIELDS) == set(harness_actions.ACTIONS)
    assert set(harness_contracts.ACTION_REQUIRED_ANY) <= tools


def test_risk_levels_use_declared_vocabulary():
    assert set(capability_contract.RISK_LEVELS) == {
        "read_only",
        "external_side_effect",
        "irreversible",
    }
    assert set(harness_contracts.ACTION_RISK.values()) <= set(
        capability_contract.RISK_LEVELS
    )


def test_fingerprint_is_stable_across_requests():
    assert routes.nodes_catalog()["fingerprint"] == routes.nodes_catalog()["fingerprint"]
    assert actions_document()["fingerprint"] == actions_document()["fingerprint"]


def test_node_contract_change_changes_fingerprint(monkeypatch):
    base = nodes_document()
    changed_nodes = copy.deepcopy(base["nodes"])
    changed_nodes[0]["fields"][0]["required"] = not changed_nodes[0]["fields"][0]["required"]
    monkeypatch.setattr(
        capability_contract,
        "catalog",
        lambda: {"nodes": changed_nodes, "categories": base["categories"]},
    )
    assert nodes_document()["fingerprint"] != base["fingerprint"]


def test_node_set_change_changes_fingerprint(monkeypatch):
    base = nodes_document()
    extra = copy.deepcopy(base["nodes"][0])
    extra["type"] = "test.extra"
    monkeypatch.setattr(
        capability_contract,
        "catalog",
        lambda: {"nodes": base["nodes"] + [extra], "categories": base["categories"]},
    )
    changed = nodes_document()
    assert changed["node_count"] == base["node_count"] + 1
    assert changed["fingerprint"] != base["fingerprint"]


def test_action_added_changes_fingerprint(monkeypatch):
    base = actions_document()
    tools = harness.tools_schema()
    extra_tool = {
        "type": "function",
        "function": {
            "name": "rocogi_test_action",
            "description": "test only",
            "parameters": {"type": "object", "properties": {}},
        },
    }
    monkeypatch.setattr(
        capability_contract.harness, "tools_schema", lambda: tools + [extra_tool]
    )
    monkeypatch.setattr(
        capability_contract,
        "ACTION_RISK",
        {**harness_contracts.ACTION_RISK, "test_action": "read_only"},
    )
    monkeypatch.setattr(
        capability_contract,
        "RUNTIME_OUTPUT_FIELDS",
        {**harness_contracts.RUNTIME_OUTPUT_FIELDS, "test_action": ()},
    )
    changed = actions_document()
    assert changed["action_count"] == base["action_count"] + 1
    assert changed["fingerprint"] != base["fingerprint"]


def test_action_removed_changes_fingerprint(monkeypatch):
    base = actions_document()
    tools = harness.tools_schema()
    removed = tools[-1]["function"]["name"][len("rocogi_"):]
    monkeypatch.setattr(
        capability_contract.harness, "tools_schema", lambda: tools[:-1]
    )
    changed = actions_document()
    assert changed["action_count"] == base["action_count"] - 1
    assert removed not in {item["name"] for item in changed["actions"]}
    assert changed["fingerprint"] != base["fingerprint"]


def test_action_schema_change_changes_fingerprint(monkeypatch):
    base = actions_document()
    tools = copy.deepcopy(harness.tools_schema())
    target = next(
        item for item in tools if item["function"]["name"] == "rocogi_click"
    )
    target["function"]["parameters"]["properties"]["x"]["type"] = "integer"
    monkeypatch.setattr(
        capability_contract.harness, "tools_schema", lambda: tools
    )
    changed = actions_document()
    assert changed["action_count"] == base["action_count"]
    assert changed["fingerprint"] != base["fingerprint"]


def test_fingerprint_ignores_environment_fields(monkeypatch):
    base = actions_document()
    monkeypatch.setattr(
        capability_contract,
        "platform_capabilities",
        lambda: {"platform": "linux", "windows": True},
    )
    assert actions_document()["fingerprint"] == base["fingerprint"]