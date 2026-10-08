"""Metadata-only synthetic original136 lifecycle; no backend/operator execution."""

from __future__ import annotations

import copy
import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from infra_joint.control.contracts import LogicalModelAction, LogicalToolAction
from infra_joint.control.graph import ExecutionGrownGraph

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
reviewer = importlib.import_module("large_scale_resident_model_artifact_type_review_v1")


def fixture() -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, dict[str, Any]]]:
    trace: list[dict[str, Any]] = []
    graph = ExecutionGrownGraph()
    metadata: list[dict[str, Any]] = [
        {
            "artifact_id": "video",
            "media_type": "video/mp4",
            "size_bytes": 10_000,
            "sha256_hex": "a" * 64,
        }
    ]
    producer: dict[str, str] = {}

    def emit(kind: str, payload: dict[str, Any]) -> None:
        trace.append({"event_type": kind, "payload": copy.deepcopy(payload)})

    def snapshot() -> None:
        emit("workflow.graph.snapshot", graph.snapshot().model_dump(mode="json"))

    def append(
        identifier: str,
        operator: str,
        inputs: list[str],
        outputs: list[dict[str, Any]],
        *,
        success: bool = True,
        prompt: str = "SYNTHETIC_PRIVATE_PROMPT",
        text: str = "SYNTHETIC_PRIVATE_MODEL_RESPONSE é",
        context: bool = False,
    ) -> None:
        owner = "manager"
        action_id = owner + ":" + identifier
        decision = owner + ":native-turn:" + str(len(graph.snapshot().nodes) + 1)
        batch_id = decision + ":batch:" + identifier
        args: dict[str, Any] = {}
        if outputs and operator != "sample_frames":
            args["output_artifact_id"] = outputs[0]["artifact_id"]
        if operator == "sample_frames":
            args = {"output_prefix": "frames", "max_frames": 10}
        requirements = {
            "modalities": ["image", "text"],
            "min_context_tokens": 1,
            "reserved_output_tokens": 2048,
            "required_capabilities": ["model"],
            "quality_class": None,
        }
        action: dict[str, Any] = {
            "action_id": action_id,
            "owner_agent_id": owner,
            "inputs": inputs,
            "outputs": outputs,
            "depends_on": [],
        }
        selected_args = {**args}
        if operator == "invoke_model":
            selected_args.update(prompt=prompt, output_media_type="text/plain")
            action.update(action_type="model", prompt=prompt, requirements=requirements)
            normalized = LogicalModelAction.model_validate(action)
        else:
            action.update(action_type="tool", operator=operator, arguments=args)
            normalized = LogicalToolAction.model_validate(action)
        action = normalized.model_dump(mode="json")
        selected_payload: dict[str, Any] = {"inputs": inputs, "arguments": selected_args}
        if operator == "invoke_model":
            selected_payload["requirements"] = requirements
        emit(
            "logical.action.selected",
            {
                "action_id": action_id,
                "decision_id": decision,
                "logical_agent_id": owner,
                "operator": operator,
                "selected_tool_arguments": selected_payload,
            },
        )
        if operator == "invoke_model":
            emit(
                "logical.model.requirements",
                {
                    "action_id": action_id,
                    "owner_agent_id": owner,
                    "requested": action["requirements"],
                    "matching_model_classes": ["model-class-01"],
                    "static_feasible": True,
                    "classification": "static_feasible",
                },
            )
        common = {
            "batch_id": batch_id,
            "decision_id": decision,
            "logical_agent_id": owner,
            "action_ids": [action_id],
        }
        emit(
            "logical.batch.validation",
            {
                **common,
                "input_artifact_ids": inputs,
                "same_batch_dependencies": [],
                "status": "accepted",
                "all_inputs_materialized": True,
            },
        )
        emit(
            "logical.action.prepared",
            {
                "action": action,
                "input_lineage": {
                    source: producer.get(source, "initial_task_artifact") for source in inputs
                },
            },
        )
        graph.add((normalized,))
        snapshot()
        graph.mark_running((action_id,))
        snapshot()
        emit("logical.batch.started", {**common, "agent_state": "waiting_on_physical"})
        emit(
            "action.started",
            {"action_id": action_id, "decision_id": decision, "logical_agent_id": owner},
        )
        obs: dict[str, Any] = {
            "action_id": action_id,
            "owner_agent_id": owner,
            "succeeded": success,
            "output": {},
            "produced_information": [],
            "failure_code": None,
            "failure_message": None,
            "physical_profile": None,
        }
        physical: dict[str, Any] = {"batch_id": batch_id, "action_id": action_id}
        if not context:
            physical["selection"] = {"selected_agent_id": "SYNTHETIC_PRIVATE_WORKER"}
        if success:
            produced: list[dict[str, Any]] = []
            for index, output in enumerate(outputs):
                meta = {
                    "artifact_id": output["artifact_id"],
                    "media_type": output["media_type"],
                    "size_bytes": len(text.encode("utf-8")) if operator == "invoke_model" else 99,
                    "sha256_hex": hashlib.sha256(text.encode("utf-8")).hexdigest()
                    if operator == "invoke_model"
                    else str(index % 10) * 64,
                }
                metadata.append(meta)
                produced.append(meta)
                producer[output["artifact_id"]] = action_id
            output_payload: dict[str, Any] = {"artifacts": produced}
            if operator == "invoke_model":
                output_payload["text"] = text
                if not produced:
                    output_payload.pop("artifacts")
                physical["selection"]["selected_deployment_id"] = "PRIVATE_DEPLOYMENT"
            elif operator == "read_artifact":
                output_payload = {"text": "PRIVATE_READ_ARTIFACT_BODY"}
            obs["output"] = output_payload
            obs["produced_information"] = [
                {**meta, "semantic_type": output["semantic_type"]}
                for meta, output in zip(produced, outputs, strict=True)
            ]
            physical["execution"] = {
                "operator": operator,
                "output": output_payload,
                "deployment_id": "PRIVATE_DEPLOYMENT" if operator == "invoke_model" else None,
                "model_telemetry": {
                    "service_latency_ms": 5,
                    "input_tokens": 20,
                    "output_tokens": 10,
                    "finish_reason": "stop",
                }
                if operator == "invoke_model"
                else None,
            }
        else:
            code = "context_limit_exceeded" if context else "validation_failed"
            message = (
                (
                    "context limit exceeded before transfer: estimated_input=41552, "
                    "reserved_output=2048, context_window=32768"
                )
                if context
                else ("artifact is not JSON: " + inputs[0])
            )
            obs.update(failure_code=code, failure_message=message)
            physical["failure"] = {
                "operator": operator,
                "failure_code": code,
                "failure_message": message,
                "stage": "selection" if context else "execution",
                "duration_ms": 1,
                "exception_type": None,
            }
        graph.mark_finished((action_id,) if success else (), () if success else (action_id,))
        snapshot()
        emit("logical.observation", obs)
        emit("physical.execution", physical)
        if operator == "invoke_model":
            emit(
                "logical.model.outcome",
                {
                    "action_id": action_id,
                    "owner_agent_id": owner,
                    "succeeded": success,
                    "failure_code": obs["failure_code"],
                    "static_feasible": True,
                    "physical_selection_succeeded": not context,
                    "reached_model_inference": success,
                },
            )
        emit(
            "action.completed",
            {
                "action_id": action_id,
                "decision_id": decision,
                "logical_agent_id": owner,
                "succeeded": success,
            },
        )
        emit(
            "logical.batch.completed",
            {
                **common,
                "succeeded_action_ids": [action_id] if success else [],
                "failed_action_ids": [] if success else [action_id],
                "agent_state": "ready_for_reasoning",
            },
        )

    snapshot()
    frames = [
        {
            "artifact_id": "frames/" + str(index),
            "media_type": "image/jpeg",
            "semantic_type": "sampled_video_frame",
        }
        for index in range(10)
    ]
    append("frames", "sample_frames", ["video"], frames)
    append(
        "context",
        "invoke_model",
        [item["artifact_id"] for item in frames],
        [
            {
                "artifact_id": "failed-context",
                "media_type": "text/plain",
                "semantic_type": "invoke_model_result",
            }
        ],
        success=False,
        context=True,
        prompt="x" * 592,
    )
    notes: list[str] = []
    for index in range(3):
        identifier = "note-" + str(index)
        notes.append(identifier)
        append(
            identifier,
            "invoke_model",
            [frames[index]["artifact_id"]],
            [
                {
                    "artifact_id": identifier,
                    "media_type": "text/plain",
                    "semantic_type": "invoke_model_result",
                }
            ],
            text="SYNTHETIC_PRIVATE_RESPONSE " + str(index),
        )
    append("read-note", "read_artifact", [notes[0]], [])
    append(
        "bad-aggregate",
        "aggregate_artifacts",
        notes,
        [
            {
                "artifact_id": "failed-aggregate",
                "media_type": "application/json",
                "semantic_type": "aggregate_artifacts_result",
            }
        ],
        success=False,
    )
    append("terminal", "invoke_model", notes, [], text="PRIVATE_TERMINAL_ANSWER")
    result = {
        "execution_completed": True,
        "failure": None,
        "evaluation": {"benchmark_score": 0, "format_valid": True},
        "loop": {
            "graph_snapshots": [
                copy.deepcopy(item["payload"])
                for item in trace
                if item["event_type"] == "workflow.graph.snapshot"
            ]
        },
        "final_answer": "PRIVATE_TERMINAL_ANSWER",
    }
    return (
        trace,
        result,
        {"worker1": {"artifacts": metadata}, "worker2": {"artifacts": copy.deepcopy(metadata)}},
    )


def event(trace: list[dict[str, Any]], kind: str, identifier: str) -> dict[str, Any]:
    for item in trace:
        value = item["payload"].get("action", item["payload"])
        if item["event_type"] == kind and value.get("action_id") == "manager:" + identifier:
            return value
    raise AssertionError("fixture event missing")


def run(inputs: tuple[Any, ...], cost: Any = 4096) -> dict[str, Any]:
    return reviewer.review(*inputs, image_context_tokens=cost)


def test_exact_closed_text_artifact_misuse_and_image_context_are_metadata_proven() -> None:
    inputs = fixture()
    before = copy.deepcopy(inputs)
    proof = run(inputs)
    assert inputs == before
    assert proof["covered_original_findings"] == [reviewer.GATE]
    assert len(proof["artifact_type_misuse_proof"]) == 1
    assert len(proof["model_output_materialization_proof"]) == 3
    assert all(
        item["reached_model_inference"] for item in proof["model_output_materialization_proof"]
    )
    context = proof["context_preflight_proof"][0]
    assert (context["prompt_bytes"], context["image_count"], context["estimated_input"]) == (
        592,
        10,
        41552,
    )
    assert context["reserved_output"] == 2048 and context["context_window"] == 32768
    assert not context["reached_model_inference"]
    assert not proof["new_store_or_corpus_body_decoded"]
    assert not proof["formal_execution_changed"]
    assert not proof["replacement_authorized"]
    assert "PRIVATE" not in json.dumps(proof)
    assert "benchmark_score" not in json.dumps(proof)


@pytest.mark.parametrize("cost", [None, 0, -1, 1, 4095, True, "4096"])
def test_image_context_cost_is_never_guessed(cost: Any) -> None:
    with pytest.raises(RuntimeError):
        run(fixture(), cost)


@pytest.mark.parametrize(
    "damage",
    [
        "incomplete",
        "no-evaluation",
        "result-failure",
        "result-graph",
        "graph-owner",
        "graph-input",
        "graph-status",
        "graph-edge",
        "graph-duplicate",
        "graph-version",
        "graph-extra-node",
        "extra-failure",
        "unknown-code",
        "wrong-message",
        "wrong-stage",
        "failure-exception",
        "failure-duration",
        "failed-execution",
        "failed-output",
        "failed-produced",
        "failed-materialized",
        "missing-replica",
        "replica-hash",
        "replica-media",
        "duplicate-replica",
        "physical-output-hash",
        "logical-output-hash",
        "produced-hash",
        "produced-semantic",
        "response-text",
        "no-telemetry",
        "no-deployment",
        "wrong-deployment",
        "no-selection",
        "completed-state",
        "observation-owner",
        "private-profile",
        "producer-after-consumer",
        "input-lineage",
        "unknown-input",
        "wrong-operator",
        "aggregate-args",
        "aggregate-output-id",
        "aggregate-output-media",
        "wrong-producer-type",
        "selected-input",
        "selected-owner",
        "selected-operator",
        "selected-output",
        "selected-prompt",
        "selected-requirements",
        "selected-media",
        "selected-semantic",
        "selected-extra",
        "batch-rejected",
        "batch-owner",
        "batch-readiness",
        "batch-dependency",
        "batch-incomplete",
        "batch-failure-list",
        "requirements-static",
        "requirements-request",
        "requirements-empty",
        "model-outcome",
        "context-count",
        "context-reserve",
        "context-window",
        "context-prompt",
        "context-image-media",
        "context-selection",
        "context-inference",
        "duplicate-event",
        "missing-prepared",
        "missing-observation",
        "missing-physical",
        "missing-completed",
        "missing-selected",
        "missing-started",
        "missing-requirements",
        "missing-outcome",
        "reordered-lifecycle",
        "explicit-dependency",
        "unclosed-graph",
        "graph-edge-extra-key",
    ],
)
def test_every_tampered_or_unproven_lifecycle_fails_closed(damage: str) -> None:
    inputs = fixture()
    trace, result, states = inputs
    prepared = event(trace, "logical.action.prepared", "bad-aggregate")
    obs = event(trace, "logical.observation", "bad-aggregate")
    physical = event(trace, "physical.execution", "bad-aggregate")
    producer = event(trace, "logical.action.prepared", "note-0")
    producer_obs = event(trace, "logical.observation", "note-0")
    producer_physical = event(trace, "physical.execution", "note-0")
    selected = event(trace, "logical.action.selected", "note-0")
    final_graph = next(
        item["payload"]
        for item in reversed(trace)
        if item["event_type"] == "workflow.graph.snapshot"
    )
    node = next(
        item for item in final_graph["nodes"] if item["action_id"] == "manager:bad-aggregate"
    )
    if damage == "incomplete":
        result["execution_completed"] = False
    elif damage == "no-evaluation":
        result["evaluation"] = None
    elif damage == "result-failure":
        result["failure"] = {"code": "unknown"}
    elif damage == "result-graph":
        result["loop"]["graph_snapshots"].pop()
    elif damage.startswith("graph-") or damage == "unclosed-graph":
        if damage == "graph-owner":
            node["owner_agent_id"] = "other"
        elif damage == "graph-input":
            node["inputs"] = ["video"]
        elif damage in {"graph-status", "unclosed-graph"}:
            node["status"] = "running"
        elif damage == "graph-edge":
            final_graph["edges"].pop()
        elif damage == "graph-duplicate":
            final_graph["nodes"].append(copy.deepcopy(node))
        elif damage == "graph-version":
            final_graph["version"] += 1
        elif damage == "graph-edge-extra-key":
            final_graph["edges"][0]["unknown"] = 1
        else:
            final_graph["nodes"].append({**node, "action_id": "manager:unknown"})
        result["loop"]["graph_snapshots"][-1] = copy.deepcopy(final_graph)
    elif damage == "extra-failure":
        trace.append(
            {"event_type": "logical.observation", "payload": {**obs, "action_id": "extra"}}
        )
    elif damage == "unknown-code":
        obs["failure_code"] = physical["failure"]["failure_code"] = "unknown"
    elif damage == "wrong-message":
        obs["failure_message"] = physical["failure"]["failure_message"] = (
            "artifact contains invalid JSON"
        )
    elif damage == "wrong-stage":
        physical["failure"]["stage"] = "transfer"
    elif damage == "failure-exception":
        physical["failure"]["exception_type"] = "ValueError"
    elif damage == "failure-duration":
        physical["failure"]["duration_ms"] = float("nan")
    elif damage == "failed-execution":
        physical["execution"] = {}
    elif damage == "failed-output":
        obs["output"] = {"text": "unexpected"}
    elif damage == "failed-produced":
        obs["produced_information"] = [producer_obs["produced_information"][0]]
    elif damage == "failed-materialized":
        states["worker1"]["artifacts"].append(
            {
                "artifact_id": "failed-aggregate",
                "media_type": "application/json",
                "size_bytes": 2,
                "sha256_hex": "f" * 64,
            }
        )
    elif damage in {"missing-replica", "replica-hash", "replica-media", "duplicate-replica"}:
        values = states["worker1"]["artifacts"]
        target = next(item for item in values if item["artifact_id"] == "note-0")
        if damage == "missing-replica":
            for state in states.values():
                state["artifacts"][:] = [
                    item for item in state["artifacts"] if item["artifact_id"] != "note-0"
                ]
        elif damage == "duplicate-replica":
            values.append(copy.deepcopy(target))
        else:
            target["sha256_hex" if damage == "replica-hash" else "media_type"] = (
                "f" * 64 if damage == "replica-hash" else "application/json"
            )
    elif damage in {"physical-output-hash", "logical-output-hash", "produced-hash"}:
        value = (
            producer_physical["execution"]["output"]["artifacts"][0]
            if damage == "physical-output-hash"
            else producer_obs["output"]["artifacts"][0]
            if damage == "logical-output-hash"
            else producer_obs["produced_information"][0]
        )
        value["sha256_hex"] = "f" * 64
    elif damage == "produced-semantic":
        producer_obs["produced_information"][0]["semantic_type"] = "unknown"
    elif damage == "response-text":
        producer_obs["output"]["text"] = producer_physical["execution"]["output"]["text"] = (
            "altered"
        )
    elif damage == "no-telemetry":
        producer_physical["execution"]["model_telemetry"] = None
    elif damage == "no-deployment":
        producer_physical["execution"]["deployment_id"] = None
    elif damage == "wrong-deployment":
        producer_physical["selection"]["selected_deployment_id"] = "other"
    elif damage == "no-selection":
        physical["selection"] = {}
    elif damage == "completed-state":
        event(trace, "action.completed", "bad-aggregate")["succeeded"] = True
    elif damage == "observation-owner":
        obs["owner_agent_id"] = "other"
    elif damage == "private-profile":
        obs["physical_profile"] = {"bandwidth": 100}
    elif damage == "producer-after-consumer":
        completed = next(
            item
            for item in trace
            if item["event_type"] == "action.completed"
            and item["payload"]["action_id"] == "manager:note-0"
        )
        trace.remove(completed)
        trace.append(completed)
    elif damage == "input-lineage":
        item = next(
            item
            for item in trace
            if item["event_type"] == "logical.action.prepared"
            and item["payload"]["action"]["action_id"] == "manager:bad-aggregate"
        )
        item["payload"]["input_lineage"]["note-0"] = "initial_task_artifact"
    elif damage == "unknown-input":
        prepared["inputs"][0] = "unknown"
    elif damage == "wrong-operator":
        prepared["operator"] = "filter_records"
    elif damage == "aggregate-args":
        prepared["arguments"]["unknown"] = 1
    elif damage == "aggregate-output-id":
        prepared["outputs"][0]["artifact_id"] = "other"
    elif damage == "aggregate-output-media":
        prepared["outputs"][0]["media_type"] = "text/plain"
    elif damage == "wrong-producer-type":
        producer["action_type"] = "tool"
    elif damage.startswith("selected-"):
        args = selected["selected_tool_arguments"]
        if damage == "selected-input":
            args["inputs"] = ["video"]
        elif damage == "selected-owner":
            selected["logical_agent_id"] = "other"
        elif damage == "selected-operator":
            selected["operator"] = "aggregate_artifacts"
        elif damage == "selected-output":
            args["arguments"]["output_artifact_id"] = "wrong"
        elif damage == "selected-prompt":
            args["arguments"]["prompt"] = "wrong"
        elif damage == "selected-requirements":
            args["requirements"]["reserved_output_tokens"] = 1
        elif damage == "selected-media":
            args["arguments"]["output_media_type"] = "application/json"
        elif damage == "selected-semantic":
            args["arguments"]["output_semantic_type"] = "other"
        else:
            args["unknown"] = 1
    elif damage.startswith("batch-"):
        kind = (
            "logical.batch.completed"
            if damage in {"batch-incomplete", "batch-failure-list"}
            else "logical.batch.validation"
        )
        item = next(
            item["payload"]
            for item in trace
            if item["event_type"] == kind
            and item["payload"]["action_ids"] == ["manager:bad-aggregate"]
        )
        key, value = {
            "batch-rejected": ("status", "rejected"),
            "batch-owner": ("logical_agent_id", "other"),
            "batch-readiness": ("all_inputs_materialized", False),
            "batch-dependency": ("same_batch_dependencies", ["manager:note-0"]),
            "batch-incomplete": ("agent_state", "waiting_on_physical"),
            "batch-failure-list": ("failed_action_ids", []),
        }[damage]
        item[key] = value
    elif damage.startswith("requirements-"):
        item = event(trace, "logical.model.requirements", "note-0")
        if damage == "requirements-static":
            item["static_feasible"] = False
        elif damage == "requirements-request":
            item["requested"]["reserved_output_tokens"] = 1
        else:
            item["matching_model_classes"] = []
    elif damage == "model-outcome":
        event(trace, "logical.model.outcome", "note-0")["reached_model_inference"] = False
    elif damage.startswith("context-"):
        ctx_action = event(trace, "logical.action.prepared", "context")
        ctx_obs = event(trace, "logical.observation", "context")
        ctx_phys = event(trace, "physical.execution", "context")
        if damage == "context-count":
            ctx_action["inputs"].pop()
        elif damage in {"context-reserve", "context-window"}:
            text = ctx_obs["failure_message"].replace(
                "2048" if damage == "context-reserve" else "32768", "1"
            )
            ctx_obs["failure_message"] = ctx_phys["failure"]["failure_message"] = text
        elif damage == "context-prompt":
            ctx_action["prompt"] += "x"
        elif damage == "context-image-media":
            for state in states.values():
                next(item for item in state["artifacts"] if item["artifact_id"] == "frames/0")[
                    "media_type"
                ] = "image/png"
        elif damage == "context-selection":
            ctx_phys["selection"] = {"selected_agent_id": "other"}
        else:
            event(trace, "logical.model.outcome", "context")["reached_model_inference"] = True
    elif damage == "duplicate-event":
        trace.append(
            copy.deepcopy(
                next(item for item in trace if item["event_type"] == "logical.action.prepared")
            )
        )
    elif damage.startswith("missing-"):
        kind = {
            "prepared": "logical.action.prepared",
            "observation": "logical.observation",
            "physical": "physical.execution",
            "completed": "action.completed",
            "selected": "logical.action.selected",
            "started": "action.started",
            "requirements": "logical.model.requirements",
            "outcome": "logical.model.outcome",
        }[damage[8:]]
        trace.remove(next(item for item in trace if item["event_type"] == kind))
    elif damage == "reordered-lifecycle":
        indices = [
            index
            for index, item in enumerate(trace)
            if item["event_type"] in {"logical.observation", "physical.execution"}
            and item["payload"]["action_id"] == "manager:note-0"
        ]
        trace[indices[0]], trace[indices[1]] = trace[indices[1]], trace[indices[0]]
    elif damage == "explicit-dependency":
        prepared["depends_on"] = ["manager:context"]
    else:
        raise AssertionError("unimplemented tamper")
    with pytest.raises((RuntimeError, KeyError)):
        run(inputs)


def test_source_closure_contains_actual_json_type_gate_and_model_materialization() -> None:
    assert {
        "src/infra_joint/operators/artifacts.py",
        "src/infra_joint/operators/structured.py",
        "src/infra_joint/worker/server.py",
        "src/infra_joint/runtime/resolver.py",
        "src/infra_joint/control/native_agents.py",
        "src/infra_joint/control/graph.py",
    } <= set(reviewer.SOURCE_PATHS)


def test_successful_inline_model_and_read_tool_need_no_fake_materialized_outputs() -> None:
    inputs = fixture()
    trace, _, _ = inputs
    assert event(trace, "logical.action.prepared", "terminal")["outputs"] == []
    assert event(trace, "logical.action.prepared", "read-note")["outputs"] == []
    assert event(trace, "logical.observation", "read-note")["produced_information"] == []
    assert event(trace, "physical.execution", "read-note")["execution"]["model_telemetry"] is None
    assert run(inputs)["model_output_materialization_proof"]


def test_text_plain_response_is_not_semantically_parsed_as_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = fixture()
    trace, _, states = inputs
    text = '[{"synthetic": "PRIVATE_CONTENT"}]'
    meta = event(trace, "logical.observation", "note-0")["output"]["artifacts"][0]
    meta.update(
        size_bytes=len(text.encode("utf-8")),
        sha256_hex=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )
    for state in states.values():
        next(item for item in state["artifacts"] if item["artifact_id"] == "note-0").update(meta)
    event(trace, "logical.observation", "note-0")["produced_information"][0].update(meta)
    event(trace, "logical.observation", "note-0")["output"]["text"] = text
    physical = event(trace, "physical.execution", "note-0")["execution"]
    physical["output"] = copy.deepcopy(event(trace, "logical.observation", "note-0")["output"])

    def forbidden_decode(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("semantic JSON/body decoding forbidden")

    monkeypatch.setattr(json, "loads", forbidden_decode)
    proof = run(inputs)
    assert (
        proof["artifact_type_misuse_proof"][0]["input_model_output_proofs"][0]["output_media_type"]
        == "text/plain"
    )
    assert "PRIVATE_CONTENT" not in json.dumps(proof)
