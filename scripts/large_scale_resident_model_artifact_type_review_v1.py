"""Pure closed-evidence proof of JSON aggregation of real text model outputs.

The caller binds immutable original evidence, admission, SDK selected arguments,
Worker state and the exact SOURCE_PATHS before using this offline proof. This
module performs no file reads, operator executions, semantic response decoding,
quality evaluation, feedback, replacement authorization or runtime alteration.
Hashing already-loaded response strings binds bytes; it does not interpret them.
An image context companion additionally requires the caller's source/config-bound
image_context_tokens. An absent binding remains unknown and is rejected.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any, cast

from pydantic import ValidationError

from infra_joint.control.contracts import (
    ExecutionRequirements,
    LogicalModelAction,
    LogicalToolAction,
)
from infra_joint.control.provenance import provenance_sha256
from infra_joint.operators.artifacts import ProducedArtifact
from infra_joint.operators.structured import AggregateArtifactsArguments
from infra_joint.worker.model_backend import ModelCallTelemetry

VERSION = "metadata-bound-model-text-artifact-type-proof-v1"
GATE = "typed_action_failure_requires_audit:validation_failed"
REASON = "audited_metadata_bound_model_text_artifact_type_misuse"
SOURCE_PATHS = (
    "src/infra_joint/operators/structured.py",
    "src/infra_joint/operators/artifacts.py",
    "src/infra_joint/worker/artifact_store.py",
    "src/infra_joint/worker/server.py",
    "src/infra_joint/worker/model_backend.py",
    "src/infra_joint/control/physical.py",
    "src/infra_joint/control/graph.py",
    "src/infra_joint/control/gateway.py",
    "src/infra_joint/control/native_agents.py",
    "src/infra_joint/control/contracts.py",
    "src/infra_joint/control/validation.py",
    "src/infra_joint/core/base.py",
    "src/infra_joint/runtime/resolver.py",
    "src/infra_joint/runtime/executor.py",
)


def _object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError("exact evidence object required")
    return cast(dict[str, Any], value)


def _array(value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise RuntimeError("exact evidence array required")
    return cast(list[Any], value)


def _names(value: Any) -> list[str]:
    values = _array(value)
    if any(not isinstance(item, str) or not item for item in values):
        raise RuntimeError("nonempty evidence identities required")
    if len(set(values)) != len(values):
        raise RuntimeError("unique evidence identities required")
    return cast(list[str], values)


def _metadata(value: Any) -> dict[str, Any]:
    try:
        return ProducedArtifact.model_validate(value).model_dump()
    except ValidationError as exc:
        raise RuntimeError("exact artifact metadata required") from exc


def _duration(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def review(
    trace: list[dict[str, Any]],
    result: dict[str, Any],
    replica_metadata: dict[str, dict[str, Any]],
    *,
    image_context_tokens: int | None = None,
) -> dict[str, Any]:
    """Require exact original closed lifecycle and all failure companions.

    Only metadata and hashes escape this function. Successful model responses
    are byte-bound to actual materialized text outputs, not assumed JSON records.
    Replica metadata must be the complete caller-bound Worker-state inventory.
    """
    if (
        result.get("execution_completed") is not True
        or not isinstance(result.get("evaluation"), dict)
        or result.get("failure")
    ):
        raise RuntimeError("completed original evaluated result required")
    kinds = (
        "logical.action.selected",
        "logical.action.prepared",
        "logical.observation",
        "physical.execution",
        "action.started",
        "action.completed",
        "logical.model.requirements",
        "logical.model.outcome",
    )
    index: dict[str, dict[str, dict[str, Any]]] = {kind: {} for kind in kinds}
    positions: dict[tuple[str, str], int] = {}
    batches: dict[str, dict[str, tuple[int, dict[str, Any]]]] = {
        kind: {}
        for kind in ("logical.batch.validation", "logical.batch.started", "logical.batch.completed")
    }
    snapshots: list[tuple[int, dict[str, Any]]] = []
    lineages: dict[str, dict[str, Any]] = {}
    for position, event in enumerate(trace):
        kind, payload = event["event_type"], _object(event["payload"])
        if kind in index:
            action = _object(payload.get("action")) if kind.endswith("prepared") else payload
            identifier = action.get("action_id")
            if not isinstance(identifier, str) or not identifier or identifier in index[kind]:
                raise RuntimeError("missing or duplicate action lifecycle")
            index[kind][identifier], positions[kind, identifier] = action, position
            if kind.endswith("prepared"):
                lineages[identifier] = _object(payload.get("input_lineage"))
        elif kind in batches:
            identifiers = _names(payload.get("action_ids"))
            if len(identifiers) != 1 or identifiers[0] in batches[kind]:
                raise RuntimeError("exact unique native singleton batch required")
            batches[kind][identifiers[0]] = position, payload
        elif kind == "workflow.graph.snapshot":
            snapshots.append((position, payload))
    actions = index["logical.action.prepared"]
    if not actions or any(set(index[kind]) != set(actions) for kind in kinds[:6]):
        raise RuntimeError("all selected/prepared/closed actions must match")
    if any(set(values) != set(actions) for values in batches.values()):
        raise RuntimeError("every action requires closed native batch evidence")
    models = {
        identifier for identifier, action in actions.items() if action.get("action_type") == "model"
    }
    if any(set(index[kind]) != models for kind in kinds[6:]):
        raise RuntimeError("every model requires exact requirements and outcome")
    if not snapshots or _array(_object(result.get("loop")).get("graph_snapshots")) != [
        graph for _, graph in snapshots
    ]:
        raise RuntimeError("result and complete trace graph evolution differ")
    replicas: dict[str, dict[str, Any]] = {}
    for state in replica_metadata.values():
        seen: set[str] = set()
        for value in _array(state.get("artifacts")):
            metadata = _metadata(value)
            identifier = metadata["artifact_id"]
            if identifier in seen or (identifier in replicas and replicas[identifier] != metadata):
                raise RuntimeError("duplicate or inconsistent artifact replicas")
            seen.add(identifier)
            replicas[identifier] = metadata
    if not replicas:
        raise RuntimeError("complete nonempty actual replica inventory required")
    producers: dict[str, str] = {}
    normalized: dict[str, LogicalModelAction | LogicalToolAction] = {}
    for identifier, action in actions.items():
        try:
            normalized[identifier] = (
                LogicalModelAction.model_validate(action)
                if identifier in models
                else LogicalToolAction.model_validate(action)
            )
        except ValidationError as exc:
            raise RuntimeError("exact finite logical action schema required") from exc
        for output in normalized[identifier].outputs:
            if output.artifact_id in producers:
                raise RuntimeError("unique declared artifact producer required")
            producers[output.artifact_id] = identifier
    observations, physical = index["logical.observation"], index["physical.execution"]
    expected_nodes: dict[str, dict[str, Any]] = {}
    expected_edges: set[tuple[str, str, str]] = set()
    for identifier, action in actions.items():
        obj = normalized[identifier]
        operator = "invoke_model" if identifier in models else action["operator"]
        selected = index["logical.action.selected"][identifier]
        owner, decision = action["owner_agent_id"], selected.get("decision_id")
        if (
            not identifier.startswith(owner + ":")
            or not isinstance(decision, str)
            or not decision.startswith(owner + ":native-turn:")
            or selected.get("logical_agent_id") != owner
            or selected.get("operator") != operator
            or _object(selected.get("selected_tool_arguments")).get("inputs", [])
            != action["inputs"]
        ):
            raise RuntimeError("selected owner/operator/input provenance differs")
        batch_id = decision + ":batch:" + identifier[len(owner) + 1 :]
        validation_position, validation = batches["logical.batch.validation"][identifier]
        start_position, start = batches["logical.batch.started"][identifier]
        finish_position, finish = batches["logical.batch.completed"][identifier]
        common = {
            "batch_id": batch_id,
            "decision_id": decision,
            "logical_agent_id": owner,
            "action_ids": [identifier],
        }
        success = observations[identifier].get("succeeded")
        if not isinstance(success, bool):
            raise RuntimeError("exact closed success state required")
        if (
            validation
            != {
                **common,
                "input_artifact_ids": action["inputs"],
                "same_batch_dependencies": [],
                "status": "accepted",
                "all_inputs_materialized": True,
            }
            or start != {**common, "agent_state": "waiting_on_physical"}
            or finish
            != {
                **common,
                "succeeded_action_ids": [identifier] if success else [],
                "failed_action_ids": [] if success else [identifier],
                "agent_state": "ready_for_reasoning",
            }
            or index["action.started"][identifier]
            != {"action_id": identifier, "decision_id": decision, "logical_agent_id": owner}
            or index["action.completed"][identifier]
            != {
                "action_id": identifier,
                "decision_id": decision,
                "logical_agent_id": owner,
                "succeeded": success,
            }
            or physical[identifier].get("batch_id") != batch_id
            or observations[identifier].get("owner_agent_id") != owner
            or observations[identifier].get("physical_profile") is not None
        ):
            raise RuntimeError("closed logical/physical batch lifecycle differs")
        order = [
            positions["logical.action.selected", identifier],
            validation_position,
            positions["logical.action.prepared", identifier],
            start_position,
            positions["action.started", identifier],
            positions["logical.observation", identifier],
            positions["physical.execution", identifier],
            positions["action.completed", identifier],
            finish_position,
        ]
        if any(left >= right for left, right in zip(order, order[1:], strict=False)):
            raise RuntimeError("reordered native action lifecycle")
        if identifier in models:
            requirement = index["logical.model.requirements"][identifier]
            outcome = index["logical.model.outcome"][identifier]
            if (
                requirement.get("owner_agent_id") != owner
                or requirement.get("requested") != action["requirements"]
                or requirement.get("static_feasible") is not True
                or not _names(requirement.get("matching_model_classes"))
                or requirement.get("classification") != "static_feasible"
                or not (
                    order[0]
                    < positions["logical.model.requirements", identifier]
                    < validation_position
                )
                or not (order[-3] < positions["logical.model.outcome", identifier] < order[-2])
                or outcome
                != {
                    "action_id": identifier,
                    "owner_agent_id": owner,
                    "succeeded": success,
                    "failure_code": observations[identifier].get("failure_code"),
                    "static_feasible": True,
                    "physical_selection_succeeded": bool(physical[identifier].get("selection")),
                    "reached_model_inference": bool(
                        _object(physical[identifier].get("execution", {})).get("model_telemetry")
                    ),
                }
            ):
                raise RuntimeError("exact model requirement/outcome evidence differs")
        expected_lineage: dict[str, str] = {}
        for source in obj.inputs:
            if source not in replicas:
                raise RuntimeError("unmaterialized action input")
            producer = producers.get(source)
            expected_lineage[source] = producer or "initial_task_artifact"
            if producer is not None:
                if (
                    producer == identifier
                    or observations[producer].get("succeeded") is not True
                    or positions["action.completed", producer] >= order[2]
                ):
                    raise RuntimeError("producer-consumer dependency not materialized and ready")
                if producer not in obj.depends_on:
                    expected_edges.add((producer, identifier, source))
        if lineages[identifier] != expected_lineage:
            raise RuntimeError("prepared input lineage differs from actual producer")
        for dependency in obj.depends_on:
            if (
                dependency not in actions
                or dependency == identifier
                or observations[dependency].get("succeeded") is not True
                or positions["action.completed", dependency] >= order[2]
            ):
                raise RuntimeError("explicit dependency not ready")
            expected_edges.add((dependency, identifier, "control-dependency"))
        expected_nodes[identifier] = {
            "action_id": identifier,
            "owner_agent_id": owner,
            "action_type": action["action_type"],
            "operator": operator,
            "inputs": action["inputs"],
            "outputs": [item.artifact_id for item in obj.outputs],
            "status": "succeeded" if success else "failed",
        }
        receipt, obs = physical[identifier], observations[identifier]
        if success:
            execution = _object(receipt.get("execution"))
            if (
                receipt.get("failure")
                or obs.get("failure_code")
                or obs.get("failure_message")
                or not _object(receipt.get("selection")).get("selected_agent_id")
                or execution.get("operator") != operator
                or execution.get("output") != obs["output"]
            ):
                raise RuntimeError("successful physical/logical execution differs")
            output = _object(obs.get("output"))
            raw_metadata = (
                output.get("artifacts", [])
                if "artifacts" in output
                else [output]
                if "artifact_id" in output
                else []
            )
            values = [_metadata(value) for value in _array(raw_metadata)]
            declared = {item.artifact_id: item for item in obj.outputs}
            produced = [_object(value) for value in _array(obs.get("produced_information"))]
            if (
                {value["artifact_id"] for value in values} != set(declared)
                or len(values) != len(declared)
                or len(produced) != len(values)
            ):
                raise RuntimeError("actual materialized outputs differ from declarations")
            for metadata, information in zip(values, produced, strict=True):
                contract = declared[metadata["artifact_id"]]
                if (
                    replicas.get(metadata["artifact_id"]) != metadata
                    or metadata["media_type"] != contract.media_type
                    or information != {**metadata, "semantic_type": contract.semantic_type}
                ):
                    raise RuntimeError("actual output replicas/information metadata differ")
            if identifier in models:
                try:
                    telemetry = ModelCallTelemetry.model_validate(execution.get("model_telemetry"))
                except ValidationError as exc:
                    raise RuntimeError("real model inference telemetry required") from exc
                text = output.get("text")
                if (
                    not isinstance(text, str)
                    or not text
                    or not telemetry.finish_reason
                    or not execution.get("deployment_id")
                    or _object(receipt["selection"]).get("selected_deployment_id")
                    != execution["deployment_id"]
                ):
                    raise RuntimeError("real successful model response/deployment required")
                if values and (
                    values[0]["size_bytes"] != len(text.encode("utf-8"))
                    or values[0]["sha256_hex"] != hashlib.sha256(text.encode("utf-8")).hexdigest()
                ):
                    raise RuntimeError("model response bytes differ from materialized output")
        elif (
            receipt.get("execution") is not None
            or obs.get("output") != {}
            or obs.get("produced_information") != []
            or any(item.artifact_id in replicas for item in obj.outputs)
        ):
            raise RuntimeError("failed action cannot have execution/materialized output")
    _graph_proof(snapshots, expected_nodes, expected_edges, positions)
    type_proof: list[dict[str, Any]] = []
    context_proof: list[dict[str, Any]] = []
    materialization: dict[str, dict[str, Any]] = {}
    for identifier, action in actions.items():
        obs, receipt = observations[identifier], physical[identifier]
        if obs["succeeded"]:
            continue
        failure = _object(receipt.get("failure"))
        if (
            failure.get("failure_code") != obs.get("failure_code")
            or failure.get("failure_message") != obs.get("failure_message")
            or failure.get("exception_type") is not None
            or not _duration(failure.get("duration_ms"))
        ):
            raise RuntimeError("failed physical/logical telemetry differs")
        if obs.get("failure_code") == "validation_failed":
            _selected_arguments_binding(action, index["logical.action.selected"][identifier])
            try:
                arguments = AggregateArtifactsArguments.model_validate(action.get("arguments"))
            except ValidationError as exc:
                raise RuntimeError("exact source-bound aggregate arguments required") from exc
            inputs, outputs = _names(action["inputs"]), _array(action["outputs"])
            if (
                action.get("action_type") != "tool"
                or action.get("operator") != "aggregate_artifacts"
                or len(inputs) != 3
                or len(outputs) != 1
                or _object(outputs[0]).get("artifact_id") != arguments.output_artifact_id
                or _object(outputs[0]).get("media_type") != "application/json"
                or obs["failure_message"] != f"artifact is not JSON: {inputs[0]}"
                or failure.get("operator") != "aggregate_artifacts"
                or failure.get("stage") != "execution"
                or not _object(receipt.get("selection")).get("selected_agent_id")
            ):
                raise RuntimeError("not an exact JSON aggregate of model text artifacts")
            input_proofs: list[dict[str, Any]] = []
            for source in inputs:
                producer = producers.get(source)
                if (
                    producer not in models
                    or observations[producer]["succeeded"] is not True
                    or replicas[source]["media_type"] != "text/plain"
                    or len(normalized[producer].outputs) != 1
                ):
                    raise RuntimeError(
                        "type misuse needs three real materialized text model outputs"
                    )
                _selected_arguments_binding(
                    actions[producer], index["logical.action.selected"][producer]
                )
                item = {
                    "action_id": producer,
                    "output_artifact_id": source,
                    "output_media_type": "text/plain",
                    "output_size_bytes": replicas[source]["size_bytes"],
                    "output_sha256": replicas[source]["sha256_hex"],
                    "action_sha256": provenance_sha256(actions[producer]),
                    "physical_receipt_sha256": provenance_sha256(physical[producer]),
                    "model_response_byte_bound": True,
                    "reached_model_inference": True,
                }
                materialization[producer] = item
                input_proofs.append(item)
            type_proof.append(
                {
                    "action_id": identifier,
                    "owner_agent_id": action["owner_agent_id"],
                    "action_sha256": provenance_sha256(action),
                    "physical_receipt_sha256": provenance_sha256(receipt),
                    "input_model_output_proofs": input_proofs,
                    "required_input_media_types": ["application/json", "application/jsonl"],
                    "failed_output_artifact_id": arguments.output_artifact_id,
                    "failed_output_absent": True,
                    "failure_code": "validation_failed",
                    "failure_stage": "execution",
                    "reached_model_inference": False,
                }
            )
        elif obs.get("failure_code") == "context_limit_exceeded":
            _selected_arguments_binding(action, index["logical.action.selected"][identifier])
            model = normalized[identifier]
            if not isinstance(model, LogicalModelAction):
                raise RuntimeError("context companion must be a model action")
            matched = re.fullmatch(
                r"context limit exceeded before transfer: estimated_input=([0-9]+), "
                r"reserved_output=([0-9]+), context_window=([0-9]+)",
                obs.get("failure_message", ""),
            )
            if (
                matched is None
                or failure.get("operator") != "invoke_model"
                or failure.get("stage") != "selection"
                or receipt.get("selection") is not None
                or not isinstance(image_context_tokens, int)
                or isinstance(image_context_tokens, bool)
                or image_context_tokens <= 0
                or not model.inputs
                or any(replicas[source]["media_type"] != "image/jpeg" for source in model.inputs)
            ):
                raise RuntimeError("source-bound image context preflight companion required")
            estimated, reserved, window = map(int, matched.groups())
            prompt_bytes = len(model.prompt.encode("utf-8"))
            if (
                estimated != prompt_bytes + len(model.inputs) * image_context_tokens
                or estimated + reserved <= window
                or reserved != model.requirements.reserved_output_tokens
                or window <= reserved
            ):
                raise RuntimeError("actual image context arithmetic contradicts failure")
            context_proof.append(
                {
                    "action_id": identifier,
                    "owner_agent_id": model.owner_agent_id,
                    "action_sha256": provenance_sha256(action),
                    "physical_receipt_sha256": provenance_sha256(receipt),
                    "prompt_bytes": prompt_bytes,
                    "image_count": len(model.inputs),
                    "image_context_tokens": image_context_tokens,
                    "input_metadata_sha256": provenance_sha256(
                        [replicas[source] for source in model.inputs]
                    ),
                    "estimated_input": estimated,
                    "reserved_output": reserved,
                    "context_window": window,
                    "failure_code": "context_limit_exceeded",
                    "reached_model_inference": False,
                    "physical_selection_succeeded": False,
                    "covers_original_audit_finding": False,
                }
            )
        else:
            raise RuntimeError("unknown or extra failure class cannot be covered")
    if len(type_proof) != 1 or len(context_proof) != 1 or len(materialization) != 3:
        raise RuntimeError("one exact type misuse and one context companion required")
    return {
        "version": VERSION,
        "covered_original_findings": [GATE],
        "artifact_type_misuse_proof": type_proof,
        "context_preflight_proof": context_proof,
        "model_output_materialization_proof": [
            materialization[key] for key in sorted(materialization)
        ],
        "trace_sha256": provenance_sha256(trace),
        "result_sha256": provenance_sha256(result),
        "replica_metadata_sha256": provenance_sha256(replica_metadata),
        "required_source_paths": list(SOURCE_PATHS),
        "new_store_or_corpus_body_decoded": False,
        "formal_execution_changed": False,
        "online_feedback": False,
        "replacement_authorized": False,
        "failure_class": "workflow_composition_model_text_artifact_type_misuse",
    }


def _graph_proof(
    snapshots: list[tuple[int, dict[str, Any]]],
    nodes: dict[str, dict[str, Any]],
    edges: set[tuple[str, str, str]],
    positions: dict[tuple[str, str], int],
) -> None:
    """Bind complete append-only pending/running/finished graph evolution."""
    if len(snapshots) != 1 + 3 * len(nodes):
        raise RuntimeError("complete native graph evolution required")
    statuses: dict[str, list[str]] = {}
    previous: set[str] = set()
    for version, (position, snapshot) in enumerate(snapshots):
        current: dict[str, dict[str, Any]] = {}
        changed: list[str] = []
        for value in _array(snapshot.get("nodes")):
            node = _object(value)
            identifier = node.get("action_id")
            if not isinstance(identifier, str) or identifier not in nodes or identifier in current:
                raise RuntimeError("graph has unknown/duplicate node")
            status = node.get("status")
            if (
                node != {**nodes[identifier], "status": status}
                or positions["logical.action.prepared", identifier] >= position
                or status not in {"pending", "running", nodes[identifier]["status"]}
            ):
                raise RuntimeError("graph node/action/position differs")
            seen = statuses.setdefault(identifier, [])
            if not seen or seen[-1] != status:
                seen.append(cast(str, status))
                changed.append(identifier)
                if status in {"pending", "running"}:
                    if position >= positions["action.started", identifier]:
                        raise RuntimeError("graph pending/running transition after action start")
                elif not (
                    positions["action.started", identifier]
                    < position
                    < positions["logical.observation", identifier]
                ):
                    raise RuntimeError("graph finish transition differs from actual execution")
            current[identifier] = node
        actual_edges: set[tuple[str, str, str]] = set()
        for value in _array(snapshot.get("edges")):
            edge = _object(value)
            key = (
                edge.get("producer_action_id"),
                edge.get("consumer_action_id"),
                edge.get("information_id"),
            )
            if (
                any(not isinstance(item, str) for item in key)
                or set(edge) != {"producer_action_id", "consumer_action_id", "information_id"}
                or key in actual_edges
                or key[0] not in current
                or key[1] not in current
            ):
                raise RuntimeError("graph has invalid/duplicate dependency edge")
            actual_edges.add(cast(tuple[str, str, str], key))
        if (
            snapshot.get("version") != version
            or not previous <= set(current)
            or actual_edges != {edge for edge in edges if edge[1] in current}
            or (version == 0 and current)
            or (version > 0 and len(changed) != 1)
        ):
            raise RuntimeError("graph evolution/dependencies differ")
        previous = set(current)
    if previous != set(nodes) or any(
        statuses[identifier] != ["pending", "running", node["status"]]
        for identifier, node in nodes.items()
    ):
        raise RuntimeError("graph did not close every exact action")


def _selected_arguments_binding(action: dict[str, Any], selected: dict[str, Any]) -> None:
    """Bind target raw SDK arguments through only declared output namespacing.

    Caller independently binds selected events to actual SDK request/response
    wire. Terminal-only generic choice prompt suffixes are not part of this
    target producer/preflight proof and remain caller/source-bound.
    """
    payload = _object(selected.get("selected_tool_arguments"))
    arguments = _object(payload.get("arguments"))
    if set(payload) - {"inputs", "arguments", "requirements"}:
        raise RuntimeError("unexpected selected tool argument fields")
    declared = _array(action.get("outputs"))
    if len(declared) != 1:
        raise RuntimeError("target action requires one declared output")
    raw_output, output = arguments.get("output_artifact_id"), _object(declared[0])["artifact_id"]
    if (
        not isinstance(raw_output, str)
        or not raw_output
        or not (output == raw_output or output.endswith("/" + raw_output.lstrip("/")))
    ):
        raise RuntimeError("raw selected output differs from namespaced declaration")
    if action["action_type"] == "model":
        try:
            requirement = ExecutionRequirements.model_validate(payload.get("requirements", {}))
        except ValidationError as exc:
            raise RuntimeError("invalid raw selected model requirements") from exc
        if (
            set(arguments)
            - {"prompt", "output_artifact_id", "output_media_type", "output_semantic_type"}
            or arguments.get("prompt") != action["prompt"]
            or requirement.model_dump(mode="json") != action["requirements"]
            or arguments.get("output_media_type", "text/plain")
            != _object(declared[0])["media_type"]
            or arguments.get("output_semantic_type", "invoke_model_result")
            != _object(declared[0])["semantic_type"]
        ):
            raise RuntimeError("selected model arguments differ from prepared target")
    else:
        try:
            AggregateArtifactsArguments.model_validate(arguments)
        except ValidationError as exc:
            raise RuntimeError("invalid raw aggregate arguments") from exc
        if action["arguments"] != {"output_artifact_id": output}:
            raise RuntimeError("prepared aggregate arguments differ from selected primitive")
