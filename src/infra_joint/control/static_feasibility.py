from __future__ import annotations

from collections import defaultdict
from math import ceil

from pydantic import Field

from infra_joint.control.contracts import (
    LogicalAction,
    LogicalModelAction,
    StaticCapabilityContract,
    StaticModelCapabilityClass,
)
from infra_joint.control.workflow import SemanticWorkflowPlan
from infra_joint.core.base import ContractModel
from infra_joint.core.task import ArtifactContentSchema, TaskContract
from infra_joint.worker.model_backend import is_text_media_type


class StaticFeasibilityError(ValueError):
    pass


class ArtifactEnvelope(ContractModel):
    artifact_id: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    size_upper_bound_bytes: int | None = Field(default=None, ge=0)
    content_schema: ArtifactContentSchema | None = None
    unknown_reasons: tuple[str, ...] = ()


class ModelContextEnvelope(ContractModel):
    action_id: str = Field(min_length=1)
    prompt_token_upper_bound: int = Field(ge=0)
    artifact_token_upper_bound: int = Field(ge=0)
    feasible_model_classes: tuple[str, ...]


class StaticWorkflowFeasibility(ContractModel):
    artifacts: tuple[ArtifactEnvelope, ...]
    model_contexts: tuple[ModelContextEnvelope, ...]

    def artifact_map(self) -> dict[str, ArtifactEnvelope]:
        return {item.artifact_id: item for item in self.artifacts}


def analyze_static_workflow(
    plan: SemanticWorkflowPlan,
    task: TaskContract,
    capabilities: StaticCapabilityContract,
) -> StaticWorkflowFeasibility:
    """Propagate conservative artifact bounds and reject context-infeasible model actions."""

    envelopes = {
        item.artifact_id: ArtifactEnvelope(
            artifact_id=item.artifact_id,
            media_type=item.media_type,
            size_upper_bound_bytes=item.size_bytes,
            content_schema=item.content_schema,
        )
        for item in task.artifacts
    }
    contexts: list[ModelContextEnvelope] = []
    for action in _topological_actions(plan):
        inputs = tuple(envelopes[item] for item in action.inputs)
        _validate_schema_arguments(action, inputs)
        _validate_output_media_types(action)
        feasible_classes: tuple[StaticModelCapabilityClass, ...] = ()
        if isinstance(action, LogicalModelAction):
            feasible_classes, context = _model_context(action, inputs, capabilities)
            contexts.append(context)
        outputs = derive_output_envelopes(action, inputs, feasible_classes)
        for output in outputs:
            envelopes[output.artifact_id] = output
    return StaticWorkflowFeasibility(
        artifacts=tuple(envelopes.values()),
        model_contexts=tuple(contexts),
    )


def derive_output_envelopes(
    action: LogicalAction,
    inputs: tuple[ArtifactEnvelope, ...],
    feasible_model_classes: tuple[StaticModelCapabilityClass, ...] = (),
) -> tuple[ArtifactEnvelope, ...]:
    if not action.outputs:
        return ()
    input_bounds = tuple(item.size_upper_bound_bytes for item in inputs)
    schema = _single_record_schema(inputs)
    output_schema: ArtifactContentSchema | None = None
    output_bound: int | None = None
    unknown: tuple[str, ...] = ()
    operator = "invoke_model" if isinstance(action, LogicalModelAction) else action.operator
    arguments = {} if isinstance(action, LogicalModelAction) else action.arguments

    if operator == "bm25_retrieve" and schema is not None:
        top_k = int(arguments["top_k"])
        record_count = min(schema.record_count or top_k, top_k)
        max_record = (
            schema.max_record_bytes + 128
            if schema.max_record_bytes is not None
            else None
        )
        output_schema = schema.model_copy(
            update={
                "fields": {**schema.fields, "_bm25_score": "number"},
                "record_count": record_count,
                "max_record_bytes": max_record,
            }
        )
        if max_record is not None:
            output_bound = 2 + record_count * (max_record + 1)
    elif operator in {"filter_records", "select_fields", "top_k_records"}:
        output_schema = schema
        output_bound = input_bounds[0] if input_bounds else None
        if operator == "select_fields" and schema is not None:
            selected = tuple(arguments["fields"])
            output_schema = schema.model_copy(
                update={
                    "fields": {field: schema.fields[field] for field in selected},
                    "text_field": schema.text_field if schema.text_field in selected else None,
                }
            )
        elif operator == "top_k_records" and schema is not None:
            requested = int(arguments["k"])
            count = min(schema.record_count or requested, requested)
            output_schema = schema.model_copy(update={"record_count": count})
            if schema.max_record_bytes is not None:
                output_bound = 2 + count * (schema.max_record_bytes + 1)
    elif operator == "derive_fields" and schema is not None:
        output_schema = schema.model_copy(
            update={
                "fields": {
                    **schema.fields,
                    **{str(item["target"]): "number" for item in arguments["derivations"]},
                }
            }
        )
        if input_bounds and input_bounds[0] is not None:
            output_bound = input_bounds[0] + (schema.record_count or 0) * 128
    elif operator == "aggregate_records":
        output_bound = input_bounds[0] if input_bounds else None
    elif operator == "aggregate_artifacts":
        output_schema = _aggregate_schema(inputs)
        if input_bounds and all(item is not None for item in input_bounds):
            output_bound = sum(item for item in input_bounds if item is not None)
    elif operator == "sample_frames":
        output_schema = ArtifactContentSchema(kind="image")
        unknown = ("sampled frame encoded size has no static upper bound",)
    elif operator == "extract_clip":
        output_schema = ArtifactContentSchema(kind="video")
        if input_bounds and input_bounds[0] is not None:
            output_bound = input_bounds[0] + 1_048_576
        else:
            unknown = ("source video size bound is unavailable",)
    elif operator == "make_contact_sheet":
        output_schema = ArtifactContentSchema(kind="image")
        columns = int(arguments.get("columns", 4))
        width = int(arguments.get("cell_width", 320))
        height = int(arguments.get("cell_height", 180))
        rows = ceil(len(inputs) / columns)
        output_bound = columns * rows * width * height * 4 + 1_048_576
    elif operator == "invoke_model":
        output_schema = ArtifactContentSchema(kind="text")
        byte_bounds = tuple(
            item.max_output_bytes
            for item in feasible_model_classes
            if item.max_output_bytes is not None
        )
        if feasible_model_classes and len(byte_bounds) == len(feasible_model_classes):
            output_bound = max(byte_bounds)
        else:
            unknown = ("model_output_byte_bound_unavailable",)
    elif input_bounds and all(item is not None for item in input_bounds):
        output_bound = sum(item for item in input_bounds if item is not None)
        unknown = ("generic conservative copy bound",)
    else:
        unknown = (f"no static output bound for operator {operator}",)

    return tuple(
        ArtifactEnvelope(
            artifact_id=output.artifact_id,
            media_type=output.media_type,
            size_upper_bound_bytes=output_bound,
            content_schema=output_schema,
            unknown_reasons=unknown if output_bound is None else (),
        )
        for output in action.outputs
    )


def _model_context(
    action: LogicalModelAction,
    inputs: tuple[ArtifactEnvelope, ...],
    capabilities: StaticCapabilityContract,
) -> tuple[tuple[StaticModelCapabilityClass, ...], ModelContextEnvelope]:
    candidates = tuple(
        item for item in capabilities.model_classes if item.satisfies(action.requirements)
    )
    prompt_bound = len(action.prompt.encode("utf-8"))
    feasible: list[StaticModelCapabilityClass] = []
    artifact_bounds: list[int] = []
    unknown = [item.artifact_id for item in inputs if item.size_upper_bound_bytes is None]
    for model_class in candidates:
        artifact_tokens = 0
        valid = True
        for envelope in inputs:
            if envelope.media_type.startswith("image/"):
                if "image" not in model_class.modalities:
                    valid = False
                    break
                artifact_tokens += model_class.image_token_cost
            elif is_text_media_type(envelope.media_type):
                if envelope.size_upper_bound_bytes is None:
                    valid = False
                    break
                artifact_tokens += envelope.size_upper_bound_bytes
            else:
                valid = False
                break
        if valid and (
            prompt_bound + artifact_tokens + model_class.reserved_output_tokens
            <= model_class.context_window
        ):
            feasible.append(model_class)
            artifact_bounds.append(artifact_tokens)
    if not feasible:
        detail = f"; unknown input bounds={unknown}" if unknown else ""
        raise StaticFeasibilityError(
            "invoke_model has no static model class fitting its actual prompt/artifact "
            f"context envelope: action={action.action_id}{detail}"
        )
    return tuple(feasible), ModelContextEnvelope(
        action_id=action.action_id,
        prompt_token_upper_bound=prompt_bound,
        artifact_token_upper_bound=max(artifact_bounds),
        feasible_model_classes=tuple(item.capability_class for item in feasible),
    )


def _single_record_schema(
    inputs: tuple[ArtifactEnvelope, ...],
) -> ArtifactContentSchema | None:
    if len(inputs) != 1:
        return None
    schema = inputs[0].content_schema
    return schema if schema is not None and schema.kind == "record_array" else None


def _validate_schema_arguments(
    action: LogicalAction,
    inputs: tuple[ArtifactEnvelope, ...],
) -> None:
    if isinstance(action, LogicalModelAction):
        return
    schema = _single_record_schema(inputs)
    if schema is None:
        return

    def require(field: object, label: str, *, text: bool = False) -> None:
        if not isinstance(field, str) or field not in schema.fields:
            raise StaticFeasibilityError(
                f"{action.operator} {label} must name an input artifact schema field"
            )
        if text and not schema.fields[field].startswith("string"):
            raise StaticFeasibilityError(
                f"{action.operator} {label} must name a string field"
            )

    if action.operator == "bm25_retrieve":
        require(action.arguments.get("text_field"), "text_field", text=True)
    elif action.operator in {"filter_records", "top_k_records"}:
        require(action.arguments.get("field"), "field")
    elif action.operator == "select_fields":
        for field in action.arguments.get("fields", ()):
            require(field, "fields item")
    elif action.operator == "derive_fields":
        for derivation in action.arguments.get("derivations", ()):
            for source in derivation.get("sources", ()):
                require(source, "derivation source")
    elif action.operator == "aggregate_records":
        for field in action.arguments.get("group_by", ()):
            require(field, "group_by item")
        for aggregation in action.arguments.get("aggregations", ()):
            field = aggregation.get("field")
            if field is not None:
                require(field, "aggregation field")


def _validate_output_media_types(action: LogicalAction) -> None:
    if isinstance(action, LogicalModelAction):
        return
    expected = {
        "aggregate_artifacts": "application/json",
        "aggregate_records": "application/json",
        "bm25_retrieve": "application/json",
        "derive_fields": "application/json",
        "filter_records": "application/json",
        "select_fields": "application/json",
        "top_k_records": "application/json",
        "sample_frames": "image/jpeg",
        "extract_clip": "video/mp4",
        "make_contact_sheet": "image/jpeg",
    }.get(action.operator)
    if expected is not None and any(item.media_type != expected for item in action.outputs):
        raise StaticFeasibilityError(
            f"{action.operator} output media type must be {expected}"
        )


def _aggregate_schema(inputs: tuple[ArtifactEnvelope, ...]) -> ArtifactContentSchema | None:
    schemas = [item.content_schema for item in inputs]
    first = schemas[0] if schemas else None
    if first is None or not all(
        item is not None
        and item.kind == first.kind
        and item.fields == first.fields
        and item.text_field == first.text_field
        for item in schemas
    ):
        return None
    return first.model_copy(
        update={
            "record_count": sum(item.record_count or 0 for item in schemas if item is not None),
            "max_record_bytes": max(
                (item.max_record_bytes or 0 for item in schemas if item is not None),
                default=0,
            ),
        }
    )


def _topological_actions(plan: SemanticWorkflowPlan) -> tuple[LogicalAction, ...]:
    actions = plan.action_map()
    order = {item.action_id: index for index, item in enumerate(plan.actions)}
    indegree = dict.fromkeys(actions, 0)
    successors: dict[str, list[str]] = defaultdict(list)
    for edge in plan.dependencies:
        indegree[edge.consumer_action_id] += 1
        successors[edge.producer_action_id].append(edge.consumer_action_id)
    ready = sorted(
        (action_id for action_id, count in indegree.items() if count == 0),
        key=order.__getitem__,
    )
    result: list[LogicalAction] = []
    while ready:
        action_id = ready.pop(0)
        result.append(actions[action_id])
        for successor in successors[action_id]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)
                ready.sort(key=order.__getitem__)
    return tuple(result)
