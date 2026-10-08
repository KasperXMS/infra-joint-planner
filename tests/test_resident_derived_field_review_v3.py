"""Metadata-only companion proofs; no corpus decoding or operator execution."""

from __future__ import annotations

import copy
import importlib
import json
from typing import Any, cast

import pytest
from test_resident_derived_field_review import add_context_companion, add_guard, case, event

reviewer = importlib.import_module("large_scale_resident_derived_field_review_v3")


def add_read(inputs: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    trace, result, _, _, states = inputs
    for kind in ("logical.observation", "physical.execution"):
        value = event(trace, kind, "aggregate")
        if kind == "physical.execution":
            value = value["execution"]
        value["output"]["size_bytes"] = 70_000
        if kind == "logical.observation":
            value["produced_information"][0]["size_bytes"] = 70_000
    for state in states.values():
        for meta in state["artifacts"]:
            if meta["artifact_id"] == "merged":
                meta["size_bytes"] = 70_000
    identifier = "specialist:read"
    action: dict[str, Any] = {
        "action_id": identifier, "owner_agent_id": "specialist", "inputs": ["merged"],
              "outputs": [], "depends_on": [], "action_type": "tool",
              "operator": "read_artifact", "arguments": {}}
    message = "artifact has 70000 bytes; read limit is 65536"
    obs: dict[str, Any] = {
        "action_id": identifier, "owner_agent_id": "specialist", "succeeded": False,
           "output": {}, "produced_information": [], "failure_code": "artifact_too_large",
           "failure_message": message, "physical_profile": None}
    physical = {"action_id": identifier, "selection": {"selected_agent_id": "worker"},
                "failure": {"operator": "read_artifact", "stage": "execution",
                            "failure_code": "artifact_too_large", "failure_message": message,
                            "duration_ms": 1.0, "exception_type": None}}
    for kind, payload in (
        ("logical.action.prepared", {"action": action}), ("logical.observation", obs),
        ("physical.execution", physical), ("action.completed", {
            "action_id": identifier, "logical_agent_id": "specialist", "succeeded": False}),
    ):
        trace.insert(-1, {"event_type": kind, "payload": payload})
    graph = result["loop"]["graph_snapshots"][-1]
    graph["nodes"].append({"action_id": identifier, "owner_agent_id": "specialist",
                           "action_type": "tool", "operator": "read_artifact", "status": "failed",
                           "inputs": ["merged"], "outputs": []})
    graph["edges"].append({"producer_action_id": "aggregate", "consumer_action_id": identifier,
                           "information_id": "merged"})
    return action, obs, physical


def add_collision(inputs: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    trace, result, _, _, _ = inputs
    prior = add_context_companion(trace, result)
    prior_id = prior["action_id"]
    prior["outputs"][0]["artifact_id"] = "derived/test/candidate"
    result["loop"]["graph_snapshots"][-1]["nodes"][-1]["outputs"] = ["derived/test/candidate"]
    prior_decision = "manager:native-turn:1"
    selected = {"action_id": prior_id, "logical_agent_id": "manager", "operator": "invoke_model",
                "decision_id": prior_decision, "selected_tool_arguments": {
                    "inputs": prior["inputs"], "arguments": {
                        "prompt": prior["prompt"], "output_artifact_id": "candidate"}}}
    accepted = {"batch_id": prior_decision + ":batch:call_context", "decision_id": prior_decision,
                "logical_agent_id": "manager", "action_ids": [prior_id],
                "input_artifact_ids": prior["inputs"], "same_batch_dependencies": [],
                "status": "accepted", "all_inputs_materialized": True}
    position = next(i for i, item in enumerate(trace)
                    if item["event_type"] == "logical.action.prepared"
                    and item["payload"]["action"]["action_id"] == prior_id)
    trace[position:position] = [
        {"event_type": "logical.action.selected", "payload": selected},
        {"event_type": "logical.batch.validation", "payload": accepted},
    ]
    identifier = "manager:call_collision"
    decision = "manager:native-turn:2"
    selected_again: dict[str, Any] = {
        "action_id": identifier, "logical_agent_id": "manager",
                      "operator": "invoke_model", "decision_id": decision,
                      "selected_tool_arguments": {"inputs": [], "arguments": {
                          "prompt": "SYNTHETIC_PRIVATE_PROMPT", "output_artifact_id": "candidate"}}}
    message = "logical outputs collide with existing artifacts: ['derived/test/candidate']"
    rejected = {"batch_id": decision + ":batch:call_collision", "decision_id": decision,
                "logical_agent_id": "manager", "action_ids": [identifier],
                "input_artifact_ids": [], "same_batch_dependencies": [],
                "status": "rejected", "reason": message}
    obs: dict[str, Any] = {
        "action_id": identifier, "owner_agent_id": "manager", "succeeded": False,
           "output": {}, "produced_information": [], "failure_code": "semantic_validation_failed",
           "failure_message": message, "physical_profile": None}
    for kind, payload in (("logical.action.selected", selected_again),
                          ("logical.batch.validation", rejected), ("logical.observation", obs)):
        trace.insert(-1, {"event_type": kind, "payload": payload})
    return selected_again, rejected, obs


def test_all_companions_preserve_original_evidence_and_exact_field_scope() -> None:
    inputs = case()
    add_read(inputs)
    add_collision(inputs)
    add_guard(inputs[0])
    before = copy.deepcopy(inputs)
    proof = reviewer.review(*inputs)
    assert inputs == before
    assert proof["version"] == "metadata-bound-derived-record-field-proof-v3"
    assert proof["covered_original_findings"] == [reviewer.GATE]
    assert len(proof["derived_field_proof"]) == 1
    for key in ("context_preflight_proof", "prephysical_guard_proof",
                "read_artifact_limit_proof", "output_collision_proof"):
        assert len(proof[key]) == 1
        assert not proof[key][0]["covers_original_audit_finding"]
        assert not proof[key][0]["reached_model_inference"]
    assert proof["output_collision_proof"][0]["reservation_survives_failed_physical_execution"]
    assert proof["read_artifact_limit_proof"][0]["size_bytes"] == 70_000
    assert "PRIVATE" not in json.dumps(proof)
    assert not proof["replacement_authorized"]


@pytest.mark.parametrize("damage", [
    "input", "outputs", "arguments", "operator", "owner", "code", "message", "stage",
    "physical-code", "physical-message", "exception", "duration", "selection", "execution",
    "result-output", "produced", "profile", "size", "replica", "dependency", "completed",
])
def test_read_companion_requires_exact_closed_metadata_failure(damage: str) -> None:
    inputs = case()
    action, obs, physical = add_read(inputs)
    key: str
    value: Any
    if damage in {"input", "outputs", "arguments", "operator", "owner"}:
        key, value = cast(dict[str, tuple[str, Any]], {
                      "input": ("inputs", ["unknown"]), "outputs": ("outputs", [{}]),
                      "arguments": ("arguments", {"max_bytes": 1}),
                      "operator": ("operator", "bm25_retrieve"),
                      "owner": ("owner_agent_id", "other")})[damage]
        action[key] = value
    elif damage in {"code", "message", "result-output", "produced", "profile"}:
        key, value = cast(dict[str, tuple[str, Any]], {
                      "code": ("failure_code", "validation_failed"),
                      "message": ("failure_message",
                                  "artifact has 70001 bytes; read limit is 65536"),
                      "result-output": ("output", {"text": "PRIVATE"}),
                      "produced": ("produced_information", [{}]),
                      "profile": ("physical_profile", {})})[damage]
        obs[key] = value
    elif damage in {"stage", "physical-code", "physical-message", "exception", "duration"}:
        key, value = {"stage": ("stage", "selection"),
                      "physical-code": ("failure_code", "validation_failed"),
                      "physical-message": ("failure_message", "different"),
                      "exception": ("exception_type", "ReadTimeout"),
                      "duration": ("duration_ms", float("nan"))}[damage]
        physical["failure"][key] = value
    elif damage in {"selection", "execution"}:
        physical[damage] = {}
    elif damage == "size":
        for state in inputs[4].values():
            state["artifacts"][-1]["size_bytes"] = 60000
    elif damage == "replica":
        inputs[4]["owner2"]["artifacts"][-1]["sha256_hex"] = "f" * 64
    elif damage == "dependency":
        inputs[1]["loop"]["graph_snapshots"][-1]["edges"].pop()
    elif damage == "completed":
        event(inputs[0], "action.completed", action["action_id"])["succeeded"] = True
    with pytest.raises(RuntimeError):
        reviewer.review(*inputs)


@pytest.mark.parametrize("damage", [
    "selected-missing", "selected-duplicate", "validation-missing", "validation-duplicate",
    "raw-output", "operator", "owner", "prompt", "extra-arg", "batch", "decision", "status",
    "reason", "readiness", "message", "code", "profile", "output", "prior-selected",
    "prior-batch", "prior-after", "unknown-reservation", "prepared", "physical", "completed",
    "graph", "reserved-materialized",
])
def test_output_collision_is_exact_prior_reservation_not_a_waiver(damage: str) -> None:
    inputs = case()
    trace, result, _, _, states = inputs
    selected, rejected, obs = add_collision(inputs)
    identifier = obs["action_id"]
    key: str
    value: Any
    if damage.endswith("-missing") or damage.endswith("-duplicate"):
        target = selected if damage.startswith("selected") else rejected
        item = next(item for item in trace if item["payload"] is target)
        if damage.endswith("-missing"):
            trace.remove(item)
        else:
            trace.insert(-1, copy.deepcopy(item))
    elif damage in {"raw-output", "prompt", "extra-arg"}:
        key, value = {"raw-output": ("output_artifact_id", "other"),
                      "prompt": ("prompt", ""), "extra-arg": ("unknown", 1)}[damage]
        selected["selected_tool_arguments"]["arguments"][key] = value
    elif damage in {"operator", "owner"}:
        selected["operator" if damage == "operator" else "logical_agent_id"] = "other"
    elif damage in {"batch", "decision", "status", "reason", "readiness"}:
        key = {"batch": "batch_id", "decision": "decision_id", "status": "status",
               "reason": "reason", "readiness": "input_artifact_ids"}[damage]
        rejected[key] = ["unknown"] if damage == "readiness" else "different"
    elif damage in {"message", "code", "profile", "output"}:
        key, value = cast(dict[str, tuple[str, Any]], {
                      "message": ("failure_message", "other"),
                      "code": ("failure_code", "validation_failed"),
                      "profile": ("physical_profile", {}), "output": ("output", {})})[damage]
        obs[key] = {"text": "PRIVATE"} if damage == "output" else value
    elif damage == "prior-selected":
        event(trace, "logical.action.selected", "manager:call_context")[
            "selected_tool_arguments"]["arguments"]["output_artifact_id"] = "other"
    elif damage == "prior-batch":
        target = next(item["payload"] for item in trace
                      if item["event_type"] == "logical.batch.validation"
                      and item["payload"]["status"] == "accepted")
        target["all_inputs_materialized"] = False
    elif damage == "prior-after":
        item = next(item for item in trace if item["event_type"] == "action.completed"
                    and item["payload"]["action_id"] == "manager:call_context")
        trace.remove(item)
        trace.insert(-1, item)
    elif damage == "unknown-reservation":
        event(trace, "logical.action.prepared", "manager:call_context")["outputs"] = []
    elif damage in {"prepared", "physical", "completed"}:
        kind = {"prepared": "logical.action.prepared", "physical": "physical.execution",
                "completed": "action.completed"}[damage]
        trace.insert(-1, {"event_type": kind, "payload": {
            "action": {"action_id": identifier}} if damage == "prepared"
            else {"action_id": identifier}})
    elif damage == "graph":
        result["loop"]["graph_snapshots"][-1]["nodes"].append({"action_id": identifier})
    elif damage == "reserved-materialized":
        states["owner1"]["artifacts"].append({"artifact_id": "derived/test/candidate",
            "media_type": "text/plain", "size_bytes": 3, "sha256_hex": "f" * 64})
    with pytest.raises(RuntimeError):
        reviewer.review(*inputs)


def test_frozen_v1_still_rejects_new_companions_and_v3_requires_field_failure() -> None:
    old = importlib.import_module("large_scale_resident_derived_field_review_v1")
    inputs = case()
    add_read(inputs)
    with pytest.raises(RuntimeError):
        old.review(*inputs)
    trace, result, _, _, _ = inputs
    trace[:] = [item for item in trace if item["payload"].get(
        "action", item["payload"]).get("action_id") != "bad"]
    graph = result["loop"]["graph_snapshots"][-1]
    graph["nodes"][:] = [node for node in graph["nodes"] if node["action_id"] != "bad"]
    graph["edges"][:] = [edge for edge in graph["edges"] if edge["consumer_action_id"] != "bad"]
    with pytest.raises(RuntimeError, match="exact audited derived field failure"):
        reviewer.review(*inputs)


_legacy = importlib.import_module("test_resident_derived_field_review")
_legacy_cases: list[tuple[str, str]] = [
    (name, damage)
    for name in (
        "test_no_unproven_case_can_be_a_validation_waiver",
        "test_only_exact_unprepared_guard_is_accepted",
        "test_context_companion_is_exact_preflight_evidence_only",
    )
    for damage in getattr(_legacy, name).pytestmark[0].args[1]
]


@pytest.mark.parametrize("name,damage", _legacy_cases)
def test_v3_preserves_frozen_v1_fail_closed_cases(
    monkeypatch: pytest.MonkeyPatch, name: str, damage: str,
) -> None:
    monkeypatch.setattr(_legacy, "reviewer", reviewer)
    getattr(_legacy, name)(damage)
