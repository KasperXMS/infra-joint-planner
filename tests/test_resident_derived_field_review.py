"""Synthetic metadata proof fixtures: no corpus bytes or operator execution."""

from __future__ import annotations

import copy
import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
reviewer = importlib.import_module("large_scale_resident_derived_field_review_v1")


def case() -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any],
                    dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    task: dict[str, Any] = {"artifacts": []}
    shapes: dict[str, dict[str, Any]] = {}
    metadata: list[dict[str, Any]] = []
    for identifier, digest in (("source1", "a"), ("source2", "b")):
        meta = {"artifact_id": identifier, "media_type": "application/json",
                "size_bytes": 100, "sha256_hex": digest * 64}
        metadata.append(meta)
        task["artifacts"].append({"artifact_id": identifier, "media_type": "application/json",
                                  "size_bytes": 100, "content_schema": {
                                      "kind": "record_array", "fields": {"body": "string"},
                                      "text_field": "body", "record_count": 2}})
        shapes[identifier] = {**meta, "record_count": 2, "actual_union_fields": ["body"],
                              "all_records_have_string_body": True}
    trace: list[dict[str, Any]] = [{"event_type": "logical.reasoning.input", "payload": {
        "logical_agent_id": "manager", "input_items": [{"content": json.dumps({"task": task})}]}}]
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    producer_by_id: dict[str, str] = {}
    for identifier, operator, inputs, output, owner in (
        ("retrieve1", "bm25_retrieve", ["source1"], "retrieved1", "manager"),
        ("retrieve2", "bm25_retrieve", ["source2"], "retrieved2", "manager"),
        ("aggregate", "aggregate_artifacts", ["retrieved1", "retrieved2"], "merged", "specialist"),
        ("bad", "bm25_retrieve", ["merged"], "missing", "specialist"),
    ):
        success = identifier != "bad"
        args: dict[str, Any] = {"output_artifact_id": output}
        if operator == "bm25_retrieve":
            args.update(query="SYNTHETIC_PRIVATE_QUERY", top_k=1,
                        text_field="body" if success else "text")
        declared = {"artifact_id": output, "media_type": "application/json",
                    "semantic_type": operator + "_result"}
        action = {"action_id": identifier, "owner_agent_id": owner, "action_type": "tool",
                  "operator": operator, "inputs": inputs, "outputs": [declared],
                  "arguments": args, "depends_on": []}
        observation: dict[str, Any] = {"action_id": identifier, "owner_agent_id": owner,
                                       "succeeded": success, "output": {},
                                       "produced_information": [], "failure_code": None,
                                       "failure_message": None}
        physical: dict[str, Any] = {"action_id": identifier,
                                    "selection": {"selected_agent_id": "SYNTHETIC_PRIVATE_OWNER"}}
        if success:
            meta = {"artifact_id": output, "media_type": "application/json",
                    "size_bytes": 99 if operator == "aggregate_artifacts" else 50,
                    "sha256_hex": str(len(metadata)) * 64}
            metadata.append(meta)
            observation.update(output=meta, produced_information=[{
                **meta, "semantic_type": declared["semantic_type"]}])
            physical["execution"] = {"operator": operator, "output": meta, "model_telemetry": None}
        else:
            message = "document field must be text: text"
            observation.update(failure_code="validation_failed", failure_message=message)
            physical["failure"] = {"failure_code": "validation_failed", "failure_message": message,
                                    "stage": "execution", "operator": operator}
        for kind, payload in (
            ("logical.action.prepared", {"action": action}),
            ("logical.observation", observation), ("physical.execution", physical),
            ("action.completed", {"action_id": identifier, "logical_agent_id": owner,
                                  "succeeded": success}),
        ):
            trace.append({"event_type": kind, "payload": payload})
        nodes.append({"action_id": identifier, "owner_agent_id": owner, "action_type": "tool",
                      "operator": operator, "inputs": inputs, "outputs": [output],
                      "status": "succeeded" if success else "failed"})
        for source in inputs:
            if source in producer_by_id:
                edges.append({"producer_action_id": producer_by_id[source],
                              "consumer_action_id": identifier, "information_id": source})
        producer_by_id[output] = identifier
    graph = {"nodes": nodes, "edges": edges, "version": 12}
    trace.append({"event_type": "workflow.graph.snapshot", "payload": graph})
    result = {"execution_completed": True, "failure": None, "loop": {"graph_snapshots": [graph]},
              "evaluation": {"benchmark_score": 0, "format_valid": True},
              "final_answer": "SYNTHETIC_PRIVATE_ANSWER"}
    states = {"owner1": {"artifacts": metadata}, "owner2": {"artifacts": copy.deepcopy(metadata)}}
    return trace, result, task, shapes, states


def event(trace: list[dict[str, Any]], kind: str, identifier: str) -> dict[str, Any]:
    for item in trace:
        payload = item["payload"]
        value = payload.get("action", payload)
        if item["event_type"] == kind and value.get("action_id") == identifier:
            return value
    raise AssertionError("fixture event absent")


def sync_task(trace: list[dict[str, Any]], task: dict[str, Any]) -> None:
    trace[0]["payload"]["input_items"][0]["content"] = json.dumps({"task": task})


@pytest.mark.parametrize("owner", ["specialist", "manager"])
def test_pure_proof_preserves_zero_and_private_data_and_bounds_fields(owner: str) -> None:
    inputs = case()
    trace, result, _, _, _ = inputs
    event(trace, "logical.action.prepared", "bad")["owner_agent_id"] = owner
    event(trace, "logical.observation", "bad")["owner_agent_id"] = owner
    event(trace, "action.completed", "bad")["logical_agent_id"] = owner
    result["loop"]["graph_snapshots"][-1]["nodes"][-1]["owner_agent_id"] = owner
    before = copy.deepcopy(inputs)
    proof = reviewer.review(*inputs)
    assert inputs == before
    assert result["evaluation"]["benchmark_score"] == 0
    assert proof["inferred_record_contracts"]["merged"]["record_count"] == 2
    assert proof["inferred_record_contracts"]["merged"]["possible_fields"] == [
        "_bm25_score", "body"]
    assert proof["derived_field_proof"][0]["specialist_received_artifact_schema"] is None
    assert not proof["replacement_authorized"]
    assert not proof["new_store_or_corpus_body_decoded"]
    assert "PRIVATE" not in json.dumps(proof)
    assert "actual_union_fields" not in proof["inferred_record_contracts"]["merged"]


@pytest.mark.parametrize("damage", [
    "result-incomplete", "result-graph", "no-manager", "task-wire", "duplicate-prepared",
    "duplicate-observation", "duplicate-physical", "duplicate-completed", "duplicate-node",
    "duplicate-edge", "missing-edge", "wrong-edge", "open-graph", "graph-owner", "graph-input",
    "uncovered-failure", "logical-only-failure", "physical-only-failure", "wrong-failure-code",
    "wrong-message", "wrong-stage", "wrong-owner", "no-selection", "not-completed",
    "producer-failed", "unknown-transform", "wrong-producer-field", "producer-args",
    "producer-output-id", "ambiguous-producer", "initial-collision", "cycle", "missing-source",
    "dependency-not-ready", "explicit-missing-dependency", "physical-hash", "logical-hash",
    "produced-hash", "produced-semantic", "replica-hash", "replica-missing", "duplicate-replica",
    "media", "empty-output", "source-hash", "source-count", "source-empty", "source-fields",
    "source-body-type", "source-body-unproved", "source-text", "failed-field", "failed-output",
    "model-telemetry", "empty-model-telemetry", "failed-execution", "failed-materialized",
    "two-failure-inputs",
])
def test_no_unproven_case_can_be_a_validation_waiver(damage: str) -> None:
    inputs = case()
    trace, result, task, shapes, states = inputs
    prepared = event(trace, "logical.action.prepared", "aggregate")
    bad = event(trace, "logical.action.prepared", "bad")
    observation = event(trace, "logical.observation", "bad")
    physical = event(trace, "physical.execution", "bad")
    graph = result["loop"]["graph_snapshots"][-1]
    if damage == "result-incomplete":
        result["execution_completed"] = False
    elif damage == "result-graph":
        result["loop"]["graph_snapshots"] = []
    elif damage == "no-manager":
        trace.pop(0)
    elif damage == "task-wire":
        task["extra"] = "drift"
    elif damage.startswith("duplicate-") and damage.split("-", 1)[1] in {
        "prepared", "observation", "physical", "completed",
    }:
        kind = {"prepared": "logical.action.prepared", "observation": "logical.observation",
                "physical": "physical.execution", "completed": "action.completed"}[
                    damage.split("-", 1)[1]]
        trace.append(copy.deepcopy(next(item for item in trace if item["event_type"] == kind)))
    elif damage == "duplicate-node":
        graph["nodes"].append(copy.deepcopy(graph["nodes"][0]))
    elif damage == "duplicate-edge":
        graph["edges"].append(copy.deepcopy(graph["edges"][0]))
    elif damage == "missing-edge":
        graph["edges"].pop()
    elif damage == "wrong-edge":
        graph["edges"][-1]["information_id"] = "different"
    elif damage == "open-graph":
        graph["nodes"][-1]["status"] = "running"
    elif damage == "graph-owner":
        graph["nodes"][-1]["owner_agent_id"] = "other"
    elif damage == "graph-input":
        graph["nodes"][-1]["inputs"] = ["source1"]
    elif damage in {"uncovered-failure", "logical-only-failure", "physical-only-failure"}:
        kinds = [] if damage == "uncovered-failure" else [damage.split("-", 1)[0]]
        for kind, value in (("logical", observation), ("physical", physical)):
            if not kinds or kind in kinds:
                extra = copy.deepcopy(value)
                extra["action_id"] = "extra"
                trace.append({"event_type": "logical.observation" if kind == "logical"
                              else "physical.execution", "payload": extra})
    elif damage == "wrong-failure-code":
        physical["failure"]["failure_code"] = "unknown"
    elif damage == "wrong-message":
        physical["failure"]["failure_message"] = "other"
    elif damage == "wrong-stage":
        physical["failure"]["stage"] = "transfer"
    elif damage == "wrong-owner":
        observation["owner_agent_id"] = "other"
    elif damage == "no-selection":
        physical["selection"] = {}
    elif damage == "not-completed":
        event(trace, "action.completed", "bad")["succeeded"] = True
    elif damage == "producer-failed":
        event(trace, "logical.observation", "retrieve1")["succeeded"] = False
    elif damage == "unknown-transform":
        prepared["operator"] = graph["nodes"][2]["operator"] = "filter_records"
    elif damage == "wrong-producer-field":
        event(trace, "logical.action.prepared", "retrieve1")["arguments"]["text_field"] = "text"
    elif damage == "producer-args":
        prepared["arguments"]["unknown"] = "value"
    elif damage == "producer-output-id":
        prepared["arguments"]["output_artifact_id"] = "other"
    elif damage == "ambiguous-producer":
        event(trace, "logical.action.prepared", "retrieve1")["outputs"][0]["artifact_id"] = "merged"
    elif damage == "initial-collision":
        prepared["outputs"][0]["artifact_id"] = "source1"
    elif damage == "cycle":
        prepared["inputs"] = graph["nodes"][2]["inputs"] = ["merged"]
    elif damage == "missing-source":
        event(trace, "logical.action.prepared", "retrieve1")["inputs"] = ["unknown"]
    elif damage == "dependency-not-ready":
        done = next(item for item in trace if item["event_type"] == "action.completed"
                    and item["payload"]["action_id"] == "retrieve1")
        trace.remove(done)
        trace.append(done)
    elif damage == "explicit-missing-dependency":
        prepared["depends_on"] = ["unknown"]
    elif damage in {"physical-hash", "logical-hash", "produced-hash", "produced-semantic"}:
        obs = event(trace, "logical.observation", "aggregate")
        if damage == "physical-hash":
            execution = event(trace, "physical.execution", "aggregate")["execution"]
            execution["output"] = {**execution["output"], "sha256_hex": "f" * 64}
        elif damage == "logical-hash":
            obs["output"] = {**obs["output"], "sha256_hex": "f" * 64}
        else:
            key = "semantic_type" if damage == "produced-semantic" else "sha256_hex"
            obs["produced_information"][0][key] = "f" * 64
    elif damage == "replica-hash":
        states["owner2"]["artifacts"][-1]["sha256_hex"] = "f" * 64
    elif damage == "replica-missing":
        for state in states.values():
            state["artifacts"].pop()
    elif damage == "duplicate-replica":
        states["owner1"]["artifacts"].append(copy.deepcopy(states["owner1"]["artifacts"][0]))
    elif damage in {"media", "empty-output"}:
        meta = event(trace, "logical.observation", "aggregate")["output"]
        meta["media_type" if damage == "media" else "size_bytes"] = (
            "text/plain" if damage == "media" else 2)
    elif damage == "source-hash":
        shapes["source1"]["sha256_hex"] = "f" * 64
    elif damage == "source-count":
        shapes["source1"]["record_count"] = 3
    elif damage == "source-empty":
        shapes["source1"]["record_count"] = 0
    elif damage == "source-fields":
        shapes["source1"]["actual_union_fields"].append("hidden")
    elif damage == "source-body-type":
        task["artifacts"][0]["content_schema"]["fields"]["body"] = "string|null"
        sync_task(trace, task)
    elif damage == "source-body-unproved":
        shapes["source1"]["all_records_have_string_body"] = False
    elif damage == "source-text":
        shapes["source1"]["actual_union_fields"].append("text")
    elif damage == "failed-field":
        bad["arguments"]["text_field"] = "other"
    elif damage == "failed-output":
        bad["arguments"]["output_artifact_id"] = "other"
    elif damage in {"model-telemetry", "empty-model-telemetry"}:
        event(trace, "physical.execution", "aggregate")["execution"]["model_telemetry"] = (
            {"x": 1} if damage == "model-telemetry" else {})
    elif damage == "failed-execution":
        physical["execution"] = {}
    elif damage == "failed-materialized":
        states["owner1"]["artifacts"].append({"artifact_id": "missing",
            "media_type": "application/json", "size_bytes": 100, "sha256_hex": "f" * 64})
    elif damage == "two-failure-inputs":
        bad["inputs"].append("source1")
    else:
        raise AssertionError("unhandled damage")
    with pytest.raises(RuntimeError):
        reviewer.review(*inputs)


def test_default_text_failure_and_explicit_successful_dependency_are_provable() -> None:
    inputs = case()
    trace, result, _, _, _ = inputs
    event(trace, "logical.action.prepared", "bad")["arguments"].pop("text_field")
    event(trace, "logical.action.prepared", "aggregate")["depends_on"] = ["retrieve1"]
    graph = result["loop"]["graph_snapshots"][-1]
    graph["edges"][0]["information_id"] = "control-dependency"
    assert reviewer.review(*inputs)["derived_field_proof"][0]["requested_field"] == "text"
