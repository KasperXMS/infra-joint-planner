"""Pure, metadata-only v4 proof for absent text on retrieval/filter descendants.

The caller must bind the historical initial shapes, actual frozen SOURCE_PATHS,
original admission, complete evidence, exit and residency before using this proof.
This module opens no files, runs no operators and supplies no ledger or retry.
Possible fields are conservative supersets, never invented actual shape scans.
Exact synthesis/context guards, oversized reads and failed-output reservation
collisions are separate companion proofs. None covers the field audit finding.
The caller must additionally bind actual Worker settings to the 65536-byte
read limit and actual SDK requests to the selected-action event arguments.
Filter counts are conservative intervals, narrowed only by source-bound canonical
JSON metadata. This additive private copy leaves frozen v1/v2/v3 unchanged.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, cast

from pydantic import ValidationError

from infra_joint.control.contracts import LogicalModelAction
from infra_joint.control.provenance import provenance_sha256
from infra_joint.operators.artifacts import ProducedArtifact
from infra_joint.operators.retrieval import Bm25Arguments
from infra_joint.operators.structured import AggregateArtifactsArguments, FilterArguments

GATE = "typed_action_failure_requires_audit:validation_failed"
REASON = "audited_metadata_bound_derived_record_absent_field_misuse"
SOURCE_PATHS = (
    "src/infra_joint/operators/retrieval.py",
    "src/infra_joint/operators/structured.py",
    "src/infra_joint/operators/artifacts.py",
    "src/infra_joint/worker/artifact_store.py",
    "src/infra_joint/control/physical.py",
    "src/infra_joint/control/graph.py",
    "src/infra_joint/control/gateway.py",
    "src/infra_joint/control/native_agents.py",
    "src/infra_joint/control/contracts.py",
    "src/infra_joint/control/validation.py",
    "src/infra_joint/core/base.py",
    "src/infra_joint/runtime/resolver.py",
    "src/infra_joint/worker/server.py",
    "src/infra_joint/operators/builtin.py",
)


def _object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError("expected an evidence object")
    return cast(dict[str, Any], value)


def _items(value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise RuntimeError("expected an evidence array")
    return cast(list[Any], value)


def _names(value: Any) -> list[str]:
    items = _items(value)
    if any(not isinstance(item, str) or not item for item in items):
        raise RuntimeError("expected nonempty string identities")
    return cast(list[str], items)


def _metadata(value: Any) -> dict[str, Any]:
    try:
        return ProducedArtifact.model_validate(value).model_dump()
    except ValidationError as exc:
        raise RuntimeError("invalid exact artifact metadata") from exc


def review(
    trace: list[dict[str, Any]],
    result: dict[str, Any],
    visible_task: dict[str, Any],
    initial_shapes: dict[str, dict[str, Any]],
    replica_metadata: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Infer absent text only from exact, successful body-preserving producers.

    initial_shapes use current IDs and verified historical metadata/count/union/
    all_records_have_string_body facts. replica_metadata is worker-state-after.
    result is the original saved run result, not an admission or an effective view.
    All input objects are left untouched. Admission and source binding are the
    caller's responsibility; proof output itself grants no execution authority.
    """
    if result.get("execution_completed") is not True or not isinstance(
        result.get("evaluation"), dict
    ):
        raise RuntimeError("completed original result with evaluation required")
    indexes: dict[str, dict[str, dict[str, Any]]] = {
        kind: {}
        for kind in (
            "logical.action.prepared",
            "logical.observation",
            "physical.execution",
            "action.completed",
            "logical.model.requirements",
        )
    }
    positions: dict[tuple[str, str], int] = {}
    phase_changes: list[tuple[int, dict[str, Any]]] = []
    graph: dict[str, Any] | None = None
    manager_tasks: list[dict[str, Any]] = []
    for position, event in enumerate(trace):
        kind, payload = event["event_type"], _object(event["payload"])
        if kind in indexes:
            value = _object(payload.get("action")) if kind.endswith("prepared") else payload
            identifier = value.get("action_id")
            if not isinstance(identifier, str) or not identifier or identifier in indexes[kind]:
                raise RuntimeError("missing or duplicate action evidence")
            indexes[kind][identifier] = value
            positions[kind, identifier] = position
        elif kind == "workflow.graph.snapshot":
            graph = payload
        elif kind == "logical.phase.changed":
            phase_changes.append((position, payload))
        elif kind == "logical.reasoning.input" and payload.get("logical_agent_id") == "manager":
            try:
                item = _object(_items(payload["input_items"])[0])
                manager_tasks.append(_object(json.loads(item["content"])["task"]))
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                raise RuntimeError("exact Manager task input required") from exc
    if not manager_tasks or any(task != visible_task for task in manager_tasks):
        raise RuntimeError("visible task differs from actual Manager task")
    if graph is None:
        raise RuntimeError("closed workflow graph required")
    result_graphs = _items(_object(result.get("loop")).get("graph_snapshots"))
    if result.get("failure") or not result_graphs or result_graphs[-1] != graph:
        raise RuntimeError("original result and final trace graph disagree")
    actions = indexes["logical.action.prepared"]
    observations = indexes["logical.observation"]
    physical = indexes["physical.execution"]
    completed = indexes["action.completed"]
    nodes: dict[str, dict[str, Any]] = {}
    for value in _items(graph.get("nodes")):
        node = _object(value)
        identifier = node.get("action_id")
        if not isinstance(identifier, str) or identifier in nodes:
            raise RuntimeError("ambiguous workflow graph node")
        nodes[identifier] = node
    if not set(actions).issubset(observations) or any(
        set(index) != set(actions) for index in (physical, completed, nodes)
    ):
        raise RuntimeError("prepared actions and closed evidence identities disagree")
    selected: dict[str, tuple[int, dict[str, Any]]] = {}
    validations: dict[str, tuple[int, dict[str, Any]]] = {}
    for position, event in enumerate(trace):
        payload = _object(event["payload"])
        kind = event["event_type"]
        if kind == "logical.action.selected":
            identifier = payload.get("action_id")
            if not isinstance(identifier, str) or identifier in selected:
                raise RuntimeError("ambiguous actual selected action")
            selected[identifier] = position, payload
        elif kind == "logical.batch.validation":
            identifiers = _names(payload.get("action_ids"))
            if len(identifiers) != 1 or identifiers[0] in validations:
                raise RuntimeError("ambiguous actual native batch validation")
            validations[identifiers[0]] = position, payload
    collision_proof: list[dict[str, Any]] = []
    guard_proof: list[dict[str, Any]] = []
    for identifier in sorted(set(observations) - set(actions)):
        observation = observations[identifier]
        if observation.get("failure_code") == "semantic_validation_failed":
            collision_proof.append(
                _collision_companion(
                    identifier,
                    observation,
                    selected,
                    validations,
                    actions,
                    observations,
                    positions,
                    len(trace),
                )
            )
            continue
        expected_guard: dict[str, Any] = {
            "action_id": identifier,
            "owner_agent_id": "manager",
            "succeeded": False,
            "output": {},
            "produced_information": [],
            "failure_code": "phase_restricted",
            "failure_message": "synthesis phase permits only invoke_model or a final response",
            "physical_profile": None,
        }
        preceding = [
            change
            for position, change in phase_changes
            if position < positions["logical.observation", identifier]
        ]
        if (
            not identifier.startswith("manager:")
            or identifier == "manager:"
            or observation != expected_guard
            or not preceding
            or preceding[-1].get("to") != "synthesis"
        ):
            raise RuntimeError("unprepared observation is not an exact synthesis guard")
        guard_proof.append(
            {
                "action_id": identifier,
                "owner_agent_id": "manager",
                "observation_sha256": provenance_sha256(observation),
                "phase_transition_sha256": provenance_sha256(preceding[-1]),
                "failure_code": "phase_restricted",
                "pre_physical_guard": True,
                "physical_action_prepared": False,
                "reached_model_inference": False,
                "covers_original_audit_finding": False,
            }
        )
    edges: set[tuple[str, str, str]] = set()
    for value in _items(graph.get("edges")):
        edge = _object(value)
        key = tuple(
            _names(
                [
                    edge.get(name)
                    for name in (
                        "producer_action_id",
                        "consumer_action_id",
                        "information_id",
                    )
                ]
            )
        )
        typed_key = cast(tuple[str, str, str], key)
        if typed_key in edges or any(identifier not in nodes for identifier in typed_key[:2]):
            raise RuntimeError("duplicate or unprepared workflow dependency")
        edges.add(typed_key)
    initial: dict[str, dict[str, Any]] = {}
    for value in _items(visible_task.get("artifacts")):
        artifact = _object(value)
        identifier = artifact.get("artifact_id")
        if not isinstance(identifier, str) or not identifier or identifier in initial:
            raise RuntimeError("ambiguous initial artifact")
        initial[identifier] = artifact
    producers: dict[str, dict[str, Any]] = {}
    for action in actions.values():
        for value in _items(action.get("outputs", [])):
            identifier = _object(value).get("artifact_id")
            if (
                not isinstance(identifier, str)
                or not identifier
                or identifier in producers
                or identifier in initial
            ):
                raise RuntimeError("ambiguous or colliding artifact producer")
            producers[identifier] = action
    replicas: dict[str, list[dict[str, Any]]] = {}
    for state in replica_metadata.values():
        seen: set[str] = set()
        for value in _items(state.get("artifacts")):
            metadata = _metadata(value)
            identifier = metadata["artifact_id"]
            if identifier in seen:
                raise RuntimeError("duplicate artifact replica on one owner")
            seen.add(identifier)
            replicas.setdefault(identifier, []).append(metadata)

    def bind_replicas(metadata: dict[str, Any]) -> None:
        values = replicas.get(metadata["artifact_id"], [])
        if not values or any(value != metadata for value in values):
            raise RuntimeError("missing or inconsistent artifact replicas")

    def lifecycle(
        action: dict[str, Any],
        success: bool,
        *,
        require_selection: bool = True,
    ) -> None:
        identifier, owner = action["action_id"], action.get("owner_agent_id")
        operator = (
            "invoke_model" if action.get("action_type") == "model" else action.get("operator")
        )
        obs, receipt = observations.get(identifier, {}), physical.get(identifier, {})
        done, node = completed.get(identifier, {}), nodes.get(identifier, {})
        outputs = [_object(value)["artifact_id"] for value in _items(action.get("outputs"))]
        if (
            not isinstance(owner, str)
            or not owner
            or obs.get("owner_agent_id") != owner
            or obs.get("succeeded") is not success
            or done.get("logical_agent_id") != owner
            or done.get("succeeded") is not success
            or node.get("owner_agent_id") != owner
            or node.get("action_type") != action.get("action_type")
            or node.get("operator") != operator
            or node.get("inputs") != action.get("inputs")
            or node.get("outputs") != outputs
            or node.get("status") != ("succeeded" if success else "failed")
            or (
                require_selection
                and not _object(receipt.get("selection", {})).get("selected_agent_id")
            )
            or (
                success
                and (
                    receipt.get("failure") or obs.get("failure_code") or obs.get("failure_message")
                )
            )
        ):
            raise RuntimeError("action lacks exact closed logical/physical lifecycle")
        prepared_at = positions["logical.action.prepared", identifier]
        if any(
            positions[kind, identifier] <= prepared_at
            for kind in (
                "logical.observation",
                "physical.execution",
                "action.completed",
            )
        ):
            raise RuntimeError("action receipt precedes preparation")
        expected: set[tuple[str, str, str]] = set()
        explicit = _names(action.get("depends_on", []))
        if len(explicit) != len(set(explicit)):
            raise RuntimeError("duplicate explicit dependency")
        dependency_ids = set(explicit)
        for source in _names(action.get("inputs")):
            producer = producers.get(source)
            if producer is not None:
                dependency_ids.add(producer["action_id"])
                if producer["action_id"] not in explicit:
                    expected.add((producer["action_id"], identifier, source))
        expected.update((dependency, identifier, "control-dependency") for dependency in explicit)
        if {edge for edge in edges if edge[1] == identifier} != expected:
            raise RuntimeError("workflow dependencies differ from actual inputs")
        for dependency in dependency_ids:
            if (
                dependency == identifier
                or observations.get(dependency, {}).get("succeeded") is not True
                or completed.get(dependency, {}).get("succeeded") is not True
                or nodes.get(dependency, {}).get("status") != "succeeded"
                or positions.get(("action.completed", dependency), len(trace)) >= prepared_at
            ):
                raise RuntimeError("dependency missing, failed, cyclic or not ready")

    inferred: dict[str, dict[str, Any]] = {}

    def infer(identifier: str, visited: frozenset[str] = frozenset()) -> dict[str, Any]:
        if identifier in visited:
            raise RuntimeError("cyclic artifact provenance")
        if identifier in inferred:
            return inferred[identifier]
        if identifier in initial:
            shape = initial_shapes.get(identifier, {})
            metadata = _metadata(
                {
                    key: shape.get(key)
                    for key in (
                        "artifact_id",
                        "media_type",
                        "size_bytes",
                        "sha256_hex",
                    )
                }
            )
            schema = _object(initial[identifier].get("content_schema"))
            fields = _object(schema.get("fields"))
            possible = _names(shape.get("actual_union_fields"))
            count = shape.get("record_count")
            if (
                metadata["artifact_id"] != identifier
                or metadata["media_type"] != "application/json"
                or metadata["size_bytes"] != initial[identifier].get("size_bytes")
                or initial[identifier].get("media_type") != "application/json"
                or schema.get("kind") != "record_array"
                or schema.get("text_field") != "body"
                or fields.get("body") != "string"
                or "text" in fields
                or "text" in possible
                or sorted(fields) != sorted(possible)
                or not isinstance(count, int)
                or isinstance(count, bool)
                or count <= 0
                or schema.get("record_count") != count
                or shape.get("all_records_have_string_body") is not True
            ):
                raise RuntimeError("initial metadata/verified shape/schema mismatch")
            bind_replicas(metadata)
            value = {
                **metadata,
                "record_count": count,
                "record_count_lower_bound": count,
                "record_count_upper_bound": count,
                "possible_fields": sorted(possible),
                "all_records_have_string_body": True,
                "producer_action_id": None,
                "producer_operator": None,
                "producer_inputs": [],
            }
        else:
            action = producers.get(identifier)
            if action is None or action.get("action_type") != "tool":
                raise RuntimeError("missing supported record producer")
            inputs, operator = _names(action.get("inputs")), action.get("operator")
            if not inputs or operator not in {
                "bm25_retrieve",
                "aggregate_artifacts",
                "filter_records",
            }:
                raise RuntimeError("unknown record transformation")
            lifecycle(action, True)
            upstream = [infer(source, visited | {identifier}) for source in inputs]
            try:
                if operator == "bm25_retrieve":
                    args = Bm25Arguments.model_validate(action.get("arguments"))
                    if len(inputs) != 1 or args.text_field != "body":
                        raise RuntimeError("producer BM25 must use the original body field")
                    lower = min(upstream[0]["record_count_lower_bound"], args.top_k)
                    upper = min(upstream[0]["record_count_upper_bound"], args.top_k)
                    possible = sorted(set(upstream[0]["possible_fields"]) | {"_bm25_score"})
                    output_id = args.output_artifact_id
                elif operator == "filter_records":
                    filter_args = FilterArguments.model_validate(action.get("arguments"))
                    if len(inputs) != 1 or filter_args.field not in upstream[0]["possible_fields"]:
                        raise RuntimeError("filter must use one input and an existing source field")
                    lower, upper = 0, upstream[0]["record_count_upper_bound"]
                    possible = list(upstream[0]["possible_fields"])
                    output_id = filter_args.output_artifact_id
                else:
                    aggregate_args = AggregateArtifactsArguments.model_validate(
                        action.get("arguments")
                    )
                    lower = sum(source["record_count_lower_bound"] for source in upstream)
                    upper = sum(source["record_count_upper_bound"] for source in upstream)
                    possible = sorted(
                        {field for source in upstream for field in source["possible_fields"]}
                    )
                    output_id = aggregate_args.output_artifact_id
            except ValidationError as exc:
                raise RuntimeError("invalid source-bound producer arguments") from exc
            outputs = _items(action.get("outputs"))
            if (
                output_id != identifier
                or len(outputs) != 1
                or _object(outputs[0]).get("media_type") != "application/json"
            ):
                raise RuntimeError("producer output declaration mismatch")
            receipt = physical[action["action_id"]]
            execution = _object(receipt.get("execution"))
            obs = observations[action["action_id"]]
            metadata = _metadata(execution.get("output"))
            produced = _items(obs.get("produced_information"))
            if (
                execution.get("operator") != operator
                or execution.get("model_telemetry") is not None
                or metadata["artifact_id"] != identifier
                or metadata["media_type"] != "application/json"
                or metadata["size_bytes"] < 2
                or _metadata(obs.get("output")) != metadata
                or len(produced) != 1
                or {key: _object(produced[0]).get(key) for key in metadata} != metadata
                or _object(produced[0]).get("semantic_type")
                != _object(outputs[0]).get("semantic_type")
            ):
                raise RuntimeError("physical/logical output metadata mismatch")
            bind_replicas(metadata)
            # The source-bound operators emit canonical arrays via store_json.
            # Without that chain, size alone does not establish any record shape.
            empty_sha256 = hashlib.sha256(b"[]").hexdigest()
            if metadata["size_bytes"] == 2:
                if lower > 0 or metadata["sha256_hex"] != empty_sha256:
                    raise RuntimeError("empty canonical output contradicts record count bounds")
                lower = upper = 0
            else:
                if metadata["sha256_hex"] == empty_sha256:
                    raise RuntimeError("nonempty canonical output has empty-array digest")
                lower = max(lower, 1)
                if lower > upper:
                    raise RuntimeError("nonempty canonical output contradicts record count bounds")
            count = lower if lower == upper else None
            value = {
                **metadata,
                "record_count": count,
                "record_count_lower_bound": lower,
                "record_count_upper_bound": upper,
                "possible_fields": possible,
                "all_records_have_string_body": True,
                "producer_action_id": action["action_id"],
                "producer_operator": operator,
                "producer_inputs": inputs,
                "producer_action_sha256": provenance_sha256(action),
            }
        inferred[identifier] = value
        return value

    failed_logical = {
        identifier
        for identifier, obs in observations.items()
        if identifier in actions and (obs.get("succeeded") is False or obs.get("failure_code"))
    }
    failed_physical = {
        identifier for identifier, receipt in physical.items() if receipt.get("failure")
    }
    failed_completed = {
        identifier for identifier, done in completed.items() if done.get("succeeded") is False
    }
    failed_graph = {
        identifier for identifier, node in nodes.items() if node.get("status") == "failed"
    }
    if not failed_logical or any(
        failures != failed_logical for failures in (failed_physical, failed_completed, failed_graph)
    ):
        raise RuntimeError("every failure requires matching physical/logical proof")
    proof: list[dict[str, Any]] = []
    context_proof: list[dict[str, Any]] = []
    read_proof: list[dict[str, Any]] = []
    for identifier in sorted(failed_logical):
        action = actions.get(identifier, {})
        inputs = _names(action.get("inputs"))
        obs, receipt = observations[identifier], physical[identifier]
        failure = _object(receipt.get("failure"))
        if obs.get("failure_code") == "artifact_too_large":
            lifecycle(action, False)
            if (
                action.get("action_type") != "tool"
                or action.get("operator") != "read_artifact"
                or len(inputs) != 1
                or inputs[0] in initial
                or action.get("arguments") != {}
                or action.get("outputs") != []
            ):
                raise RuntimeError("read companion requires one derived input and no outputs")
            shape = infer(inputs[0])
            size = shape["size_bytes"]
            limit = 65_536
            message = f"artifact has {size} bytes; read limit is {limit}"
            duration = failure.get("duration_ms")
            if (
                size <= limit
                or obs.get("failure_message") != message
                or failure.get("failure_code") != "artifact_too_large"
                or failure.get("failure_message") != message
                or failure.get("operator") != "read_artifact"
                or failure.get("stage") != "execution"
                or failure.get("exception_type") is not None
                or not isinstance(duration, (int, float))
                or isinstance(duration, bool)
                or not (0 <= duration < float("inf"))
                or receipt.get("execution") is not None
                or obs.get("output") != {}
                or obs.get("produced_information") != []
                or obs.get("physical_profile") is not None
            ):
                raise RuntimeError("not an exact metadata-bound read-size companion")
            read_proof.append(
                {
                    "action_id": identifier,
                    "owner_agent_id": action["owner_agent_id"],
                    "action_sha256": provenance_sha256(action),
                    "observation_sha256": provenance_sha256(obs),
                    "physical_receipt_sha256": provenance_sha256(receipt),
                    "input_artifact_id": inputs[0],
                    "input_sha256": shape["sha256_hex"],
                    "input_contract_sha256": provenance_sha256(shape),
                    "size_bytes": size,
                    "max_read_artifact_bytes": limit,
                    "failure_code": "artifact_too_large",
                    "stage": "execution",
                    "reached_model_inference": False,
                    "physical_selection_succeeded": True,
                    "covers_original_audit_finding": False,
                }
            )
            continue
        if obs.get("failure_code") == "context_limit_exceeded":
            try:
                model_action = LogicalModelAction.model_validate(action)
            except ValidationError as exc:
                raise RuntimeError("context companion requires a valid model action") from exc
            lifecycle(action, False, require_selection=False)
            message = obs.get("failure_message")
            matched = re.fullmatch(
                r"context limit exceeded before transfer: estimated_input=([0-9]+), "
                r"reserved_output=([0-9]+), context_window=([0-9]+)",
                message if isinstance(message, str) else "",
            )
            requirement = indexes["logical.model.requirements"].get(identifier, {})
            duration = failure.get("duration_ms")
            if (
                matched is None
                or failure.get("failure_code") != "context_limit_exceeded"
                or failure.get("failure_message") != message
                or failure.get("operator") != "invoke_model"
                or failure.get("stage") != "selection"
                or failure.get("exception_type") is not None
                or not isinstance(duration, (int, float))
                or isinstance(duration, bool)
                or not (0 <= duration < float("inf"))
                or receipt.get("selection") is not None
                or receipt.get("execution") is not None
                or obs.get("output") != {}
                or obs.get("produced_information") != []
                or obs.get("physical_profile") is not None
                or requirement.get("owner_agent_id") != action["owner_agent_id"]
                or requirement.get("requested") != action.get("requirements")
                or requirement.get("static_feasible") is not True
                or not _names(requirement.get("matching_model_classes", []))
                or positions.get(("logical.model.requirements", identifier), len(trace))
                >= positions["physical.execution", identifier]
            ):
                raise RuntimeError("not an exact closed preflight context-limit companion")
            estimated, reserved, window = (int(value) for value in matched.groups())
            source_metadata = [infer(source) for source in inputs]
            actual_estimated = len(model_action.prompt.encode("utf-8")) + sum(
                source["size_bytes"] for source in source_metadata
            )
            if (
                reserved <= 0
                or window <= 0
                or estimated + reserved <= window
                or estimated != actual_estimated
                or any(output.artifact_id in replicas for output in model_action.outputs)
            ):
                raise RuntimeError("context companion budget/input metadata not established")
            context_proof.append(
                {
                    "action_id": identifier,
                    "owner_agent_id": action["owner_agent_id"],
                    "action_sha256": provenance_sha256(action),
                    "observation_sha256": provenance_sha256(obs),
                    "physical_receipt_sha256": provenance_sha256(receipt),
                    "requirements_sha256": provenance_sha256(requirement),
                    "failure_code": "context_limit_exceeded",
                    "stage": "selection",
                    "estimated_input": estimated,
                    "reserved_output": reserved,
                    "context_window": window,
                    "reached_model_inference": False,
                    "physical_selection_succeeded": False,
                    "covers_original_audit_finding": False,
                }
            )
            continue
        if (
            action.get("action_type") != "tool"
            or action.get("operator") != "bm25_retrieve"
            or len(inputs) != 1
            or inputs[0] in initial
        ):
            raise RuntimeError("only derived single-input BM25 field failures are reviewed")
        lifecycle(action, False)
        try:
            args = Bm25Arguments.model_validate(action.get("arguments"))
        except ValidationError as exc:
            raise RuntimeError("invalid failed BM25 arguments") from exc
        message = "document field must be text: text"
        if (
            args.text_field != "text"
            or obs.get("failure_code") != "validation_failed"
            or obs.get("failure_message") != message
            or failure.get("failure_code") != "validation_failed"
            or failure.get("failure_message") != message
            or failure.get("operator") != "bm25_retrieve"
            or failure.get("stage") != "execution"
            or receipt.get("execution") is not None
            or obs.get("output")
            or obs.get("produced_information")
        ):
            raise RuntimeError("not the exact execution-stage absent-text failure")
        shape = infer(inputs[0])
        if "text" in shape["possible_fields"] or shape["record_count_lower_bound"] <= 0:
            raise RuntimeError("requested field absence/nonempty input not established")
        outputs = _items(action.get("outputs"))
        if (
            len(outputs) != 1
            or _object(outputs[0]).get("artifact_id") != args.output_artifact_id
            or _object(outputs[0]).get("media_type") != "application/json"
            or args.output_artifact_id in replicas
        ):
            raise RuntimeError("failed action output is inconsistent or materialized")
        # Keep filter ancestry local to this failed field input. A filter on a
        # context-only branch cannot establish ancestry of the original finding.
        ancestors: set[str] = set()
        pending = [inputs[0]]
        visited_inputs: set[str] = set()
        while pending:
            source = pending.pop()
            if source in visited_inputs:
                continue
            visited_inputs.add(source)
            source_contract = inferred[source]
            if source_contract["producer_operator"] == "filter_records":
                ancestors.add(source_contract["producer_action_id"])
            pending.extend(source_contract["producer_inputs"])
        proof.append(
            {
                "action_id": identifier,
                "owner_agent_id": action["owner_agent_id"],
                "action_sha256": provenance_sha256(action),
                "input_artifact_id": inputs[0],
                "input_sha256": shape["sha256_hex"],
                "requested_field": "text",
                "missing_fields": ["text"],
                "specialist_received_artifact_schema": None,
                "source_preserving_filter_ancestors": sorted(ancestors),
                "reached_model_inference": False,
            }
        )
    if not proof:
        raise RuntimeError("at least one exact audited derived field failure is required")
    return {
        "version": "metadata-bound-derived-record-field-proof-v4",
        "covered_original_findings": [GATE],
        "derived_field_proof": proof,
        "prephysical_guard_proof": guard_proof,
        "context_preflight_proof": context_proof,
        "read_artifact_limit_proof": read_proof,
        "output_collision_proof": collision_proof,
        "propagation_proof": [
            {
                "operator": inferred[key]["producer_operator"],
                "action_id": inferred[key]["producer_action_id"],
                "action_sha256": inferred[key]["producer_action_sha256"],
                "input_artifact_ids": inferred[key]["producer_inputs"],
                "input_contract_sha256": {
                    source: provenance_sha256(inferred[source])
                    for source in inferred[key]["producer_inputs"]
                },
                "output_artifact_id": key,
                "output_sha256": inferred[key]["sha256_hex"],
                "output_size_bytes": inferred[key]["size_bytes"],
                "record_count_lower_bound": inferred[key]["record_count_lower_bound"],
                "record_count_upper_bound": inferred[key]["record_count_upper_bound"],
                "source_string_body_preserved": True,
                "possible_fields": inferred[key]["possible_fields"],
            }
            for key in sorted(inferred)
            if inferred[key]["producer_action_id"] is not None
        ],
        "inferred_record_contracts": {key: inferred[key] for key in sorted(inferred)},
        "trace_sha256": provenance_sha256(trace),
        "result_sha256": provenance_sha256(result),
        "visible_task_sha256": provenance_sha256(visible_task),
        "new_store_or_corpus_body_decoded": False,
        "formal_execution_changed": False,
        "online_feedback": False,
        "replacement_authorized": False,
        "failure_class": "workflow_composition_absent_field_misuse",
    }


def _collision_companion(
    identifier: str,
    observation: dict[str, Any],
    selected: dict[str, tuple[int, dict[str, Any]]],
    validations: dict[str, tuple[int, dict[str, Any]]],
    actions: dict[str, dict[str, Any]],
    observations: dict[str, dict[str, Any]],
    positions: dict[tuple[str, str], int],
    trace_length: int,
) -> dict[str, Any]:
    """Prove reuse of an earlier reservation, not a materialized artifact.

    RuntimeActionGateway.execute_batch reserves outputs before physical batch
    preparation; a selection failure does not roll back that reservation. The
    enclosing reviewer proves the earlier context failure independently against
    its exact metadata.
    """
    selected_at, selection = selected.get(identifier, (-1, {}))
    rejected_at, validation = validations.get(identifier, (-1, {}))
    owner = observation.get("owner_agent_id")
    payload = _object(selection.get("selected_tool_arguments"))
    arguments = _object(payload.get("arguments"))
    raw_id = arguments.get("output_artifact_id")
    if (
        not isinstance(owner, str)
        or not owner
        or not identifier.startswith(owner + ":")
        or selection.get("logical_agent_id") != owner
        or selection.get("operator") != "invoke_model"
        or not isinstance(raw_id, str)
        or not raw_id
        or set(payload) - {"inputs", "arguments", "requirements"}
        or set(arguments)
        - {"prompt", "output_artifact_id", "output_media_type", "output_semantic_type"}
        or not isinstance(arguments.get("prompt"), str)
        or not arguments["prompt"]
    ):
        raise RuntimeError("collision requires exact selected model arguments")
    inputs = _names(payload.get("inputs"))
    message = observation.get("failure_message")
    candidates: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for prior_id, prior in actions.items():
        for output_value in _items(prior.get("outputs")):
            output = _object(output_value)
            output_id = output.get("artifact_id")
            if isinstance(output_id, str) and (
                output_id == raw_id or output_id.endswith("/" + raw_id.lstrip("/"))
            ):
                candidates.append((prior_id, prior, output))
    if len(candidates) != 1:
        raise RuntimeError("collision has no unique earlier output reservation")
    prior_id, prior, output = candidates[0]
    prior_selected_at, prior_selection = selected.get(prior_id, (-1, {}))
    prior_payload = _object(prior_selection.get("selected_tool_arguments"))
    prior_arguments = _object(prior_payload.get("arguments"))
    accepted_at, accepted = validations.get(prior_id, (-1, {}))
    expected_message = f"logical outputs collide with existing artifacts: {[output['artifact_id']]}"
    expected_observation: dict[str, Any] = {
        "action_id": identifier,
        "owner_agent_id": owner,
        "succeeded": False,
        "output": {},
        "produced_information": [],
        "failure_code": "semantic_validation_failed",
        "failure_message": expected_message,
        "physical_profile": None,
    }
    decision = selection.get("decision_id")
    prior_decision = prior_selection.get("decision_id")
    if (
        observation != expected_observation
        or message != expected_message
        or observation["action_id"] != identifier
        or not isinstance(decision, str)
        or not decision.startswith(owner + ":native-turn:")
        or validation
        != {
            "batch_id": decision + ":batch:" + identifier[len(owner) + 1 :],
            "decision_id": decision,
            "logical_agent_id": owner,
            "action_ids": [identifier],
            "input_artifact_ids": inputs,
            "same_batch_dependencies": [],
            "status": "rejected",
            "reason": message,
        }
        or not isinstance(prior_decision, str)
        or prior_selection.get("operator") != "invoke_model"
        or prior_selection.get("logical_agent_id") != owner
        or prior_payload.get("inputs") != prior.get("inputs")
        or prior_arguments.get("output_artifact_id") != raw_id
        or prior.get("action_type") != "model"
        or prior.get("owner_agent_id") != owner
        or output.get("media_type") != arguments.get("output_media_type", "text/plain")
        or accepted
        != {
            "batch_id": prior_decision + ":batch:" + prior_id[len(owner) + 1 :],
            "decision_id": prior_decision,
            "logical_agent_id": owner,
            "action_ids": [prior_id],
            "input_artifact_ids": prior.get("inputs"),
            "same_batch_dependencies": [],
            "status": "accepted",
            "all_inputs_materialized": True,
        }
        or observations.get(prior_id, {}).get("failure_code") != "context_limit_exceeded"
        or not (
            0
            <= prior_selected_at
            < accepted_at
            < positions.get(("logical.action.prepared", prior_id), -1)
            < positions.get(("action.completed", prior_id), trace_length)
            < selected_at
            < rejected_at
            < positions["logical.observation", identifier]
        )
    ):
        raise RuntimeError("collision lacks exact reserved-output rejection lifecycle")
    try:
        LogicalModelAction.model_validate(
            {
                "action_id": identifier,
                "owner_agent_id": owner,
                "action_type": "model",
                "inputs": inputs,
                "outputs": [output],
                "depends_on": [],
                "prompt": arguments["prompt"],
                "requirements": payload.get("requirements", {}),
            }
        )
    except ValidationError as exc:
        raise RuntimeError("collision selected model action is otherwise invalid") from exc
    return {
        "action_id": identifier,
        "owner_agent_id": owner,
        "observation_sha256": provenance_sha256(observation),
        "selected_event_sha256": provenance_sha256(selection),
        "rejected_batch_sha256": provenance_sha256(validation),
        "reserved_action_id": prior_id,
        "reserved_action_sha256": provenance_sha256(prior),
        "reserved_selected_event_sha256": provenance_sha256(prior_selection),
        "accepted_batch_sha256": provenance_sha256(accepted),
        "output_artifact_id": output["artifact_id"],
        "reservation_survives_failed_physical_execution": True,
        "failure_code": "semantic_validation_failed",
        "pre_physical_guard": True,
        "physical_action_prepared": False,
        "reached_model_inference": False,
        "covers_original_audit_finding": False,
    }
