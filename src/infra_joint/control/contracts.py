from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Annotated, Any, Literal, Self, cast

from pydantic import Field, field_validator, model_validator

from infra_joint.agents.context import AgentTaskView
from infra_joint.core.base import ContractModel

_IPV4 = re.compile(r"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])")
_FORBIDDEN_PHYSICAL_KEYS = frozenset(
    {
        "agent_id",
        "worker_id",
        "target_agent_id",
        "deployment_id",
        "target_deployment_id",
        "device_id",
        "ip",
        "ip_address",
        "host",
        "hostname",
        "route",
        "network_route",
        "placement",
        "physical_policy",
    }
)


class ProfileVisibility(StrEnum):
    BLIND = "blind"
    AWARE = "aware"


class LogicalAgentSpec(ContractModel):
    """A semantic role. It intentionally has no model or deployment binding."""

    logical_agent_id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    objective: str = Field(min_length=1)


class LogicalOutput(ContractModel):
    artifact_id: str = Field(min_length=1)
    semantic_type: str = Field(min_length=1)
    media_type: str = Field(min_length=1)


class ExecutionRequirements(ContractModel):
    """Semantic requirements used by the physical layer to select a model."""

    modalities: frozenset[str] = frozenset({"text"})
    min_context_tokens: int = Field(default=1, gt=0)
    reserved_output_tokens: int = Field(default=1, gt=0)
    required_capabilities: frozenset[str] = frozenset({"model"})
    quality_class: Literal["standard", "high_quality", "low_latency"] | None = None

    @field_validator("modalities")
    @classmethod
    def modalities_are_non_empty(cls, value: frozenset[str]) -> frozenset[str]:
        if not value or any(not item for item in value):
            raise ValueError("execution requirements need non-empty modalities")
        return value


class _LogicalActionBase(ContractModel):
    action_id: str = Field(min_length=1)
    owner_agent_id: str = Field(min_length=1)
    inputs: tuple[str, ...] = ()
    outputs: tuple[LogicalOutput, ...] = ()
    depends_on: tuple[str, ...] = ()

    @field_validator("inputs", "depends_on")
    @classmethod
    def identifiers_are_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item for item in values):
            raise ValueError("logical action identifiers must be non-empty")
        if len(values) != len(set(values)):
            raise ValueError("logical action identifiers must be unique")
        return values

    @field_validator("outputs")
    @classmethod
    def output_ids_are_unique(
        cls, values: tuple[LogicalOutput, ...]
    ) -> tuple[LogicalOutput, ...]:
        identifiers = tuple(item.artifact_id for item in values)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("logical output artifact IDs must be unique")
        return values


class LogicalToolAction(_LogicalActionBase):
    action_type: Literal["tool"] = "tool"
    operator: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def contains_no_physical_directives(self) -> Self:
        _reject_physical_content(self.arguments)
        if self.operator == "invoke_model":
            raise ValueError("invoke_model must use LogicalModelAction")
        return self


class LogicalModelAction(_LogicalActionBase):
    action_type: Literal["model"] = "model"
    prompt: str = Field(min_length=1)
    requirements: ExecutionRequirements = Field(default_factory=ExecutionRequirements)

    @model_validator(mode="after")
    def validate_model_output(self) -> Self:
        if len(self.outputs) > 1:
            raise ValueError("a model action supports at most one materialized output")
        if self.outputs and self.outputs[0].media_type not in {
            "text/plain",
            "application/json",
        }:
            raise ValueError("model output must be text/plain or application/json")
        if _IPV4.search(self.prompt):
            raise ValueError("logical model prompts must not contain IP addresses")
        return self


LogicalAction = Annotated[
    LogicalToolAction | LogicalModelAction,
    Field(discriminator="action_type"),
]


class ProducedInformation(ContractModel):
    artifact_id: str = Field(min_length=1)
    semantic_type: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    sha256_hex: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class PhysicalProfileView(ContractModel):
    """Identifier-free, bounded summary optionally exposed to the logical layer."""

    schema_version: Literal["physical-profile-v1"] = "physical-profile-v1"
    candidate_count: int = Field(ge=0)
    input_bytes: int = Field(ge=0)
    remote_input_count_range: tuple[int, int]
    transfer_latency_ms_range: tuple[float, float] | None = None
    service_latency_ms_range: tuple[float, float] | None = None
    queue_pressure_range: tuple[int, int] | None = None
    network_class: Literal["local", "constrained", "moderate", "fast", "unknown"]
    unknown_reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def ranges_are_ordered(self) -> Self:
        _ordered_range(self.remote_input_count_range, "remote input")
        if self.transfer_latency_ms_range is not None:
            _ordered_range(self.transfer_latency_ms_range, "transfer latency")
        if self.service_latency_ms_range is not None:
            _ordered_range(self.service_latency_ms_range, "service latency")
        if self.queue_pressure_range is not None:
            _ordered_range(self.queue_pressure_range, "queue pressure")
        return self


class LogicalObservation(ContractModel):
    """Physical execution result with implementation identity deliberately removed."""

    action_id: str = Field(min_length=1)
    owner_agent_id: str = Field(min_length=1)
    succeeded: bool
    output: dict[str, Any] = Field(default_factory=dict)
    produced_information: tuple[ProducedInformation, ...] = ()
    failure_code: str | None = None
    failure_message: str | None = None
    physical_profile: PhysicalProfileView | None = None

    @model_validator(mode="after")
    def failure_fields_match_status(self) -> Self:
        if self.succeeded and (self.failure_code is not None or self.failure_message is not None):
            raise ValueError("successful observation cannot contain failure details")
        if not self.succeeded and not self.failure_code:
            raise ValueError("failed observation requires a failure code")
        _reject_physical_content(self.output, scan_string_values=False)
        return self


class SubagentCall(ContractModel):
    call_id: str = Field(min_length=1)
    agent: LogicalAgentSpec
    instruction: str = Field(min_length=1)
    input_artifacts: tuple[str, ...] = ()


class ContinueDecision(ContractModel):
    decision_type: Literal["continue"] = "continue"
    rationale: str = Field(min_length=1)
    actions: tuple[LogicalAction, ...] = ()
    subagent_calls: tuple[SubagentCall, ...] = ()
    resolved_requirements: tuple[str, ...] = ()
    new_requirements: tuple[str, ...] = ()

    @field_validator("resolved_requirements", "new_requirements")
    @classmethod
    def requirements_are_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item for item in values) or len(values) != len(set(values)):
            raise ValueError("requirements must be non-empty and unique")
        return values

    @model_validator(mode="after")
    def has_work(self) -> Self:
        if not self.actions and not self.subagent_calls:
            raise ValueError("continue decision must schedule actions or subagents")
        return self


class FinishDecision(ContractModel):
    decision_type: Literal["finish"] = "finish"
    reason: str = Field(min_length=1)
    source_action_id: str = Field(min_length=1)


ManagerDecision = Annotated[
    ContinueDecision | FinishDecision,
    Field(discriminator="decision_type"),
]


class GraphNodeView(ContractModel):
    action_id: str = Field(min_length=1)
    owner_agent_id: str = Field(min_length=1)
    action_type: Literal["tool", "model"]
    operator: str = Field(min_length=1)
    status: Literal["pending", "running", "succeeded", "failed"]
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()


class GraphEdgeView(ContractModel):
    producer_action_id: str = Field(min_length=1)
    consumer_action_id: str = Field(min_length=1)
    information_id: str = Field(min_length=1)


class WorkflowGraphSnapshot(ContractModel):
    version: int = Field(ge=0)
    nodes: tuple[GraphNodeView, ...]
    edges: tuple[GraphEdgeView, ...]


class SubagentResult(ContractModel):
    call_id: str = Field(min_length=1)
    logical_agent_id: str = Field(min_length=1)
    terminal_action_id: str = Field(min_length=1)
    answer: str


class ManagerContext(ContractModel):
    task: AgentTaskView
    agent: LogicalAgentSpec
    assigned_artifacts: tuple[str, ...]
    unresolved_requirements: tuple[str, ...]
    observations: tuple[LogicalObservation, ...]
    subagent_results: tuple[SubagentResult, ...]
    workflow: WorkflowGraphSnapshot
    physical_profile: PhysicalProfileView | None = None


def _reject_physical_content(
    value: object,
    *,
    scan_string_values: bool = True,
) -> None:
    if isinstance(value, dict):
        mapping = cast(Mapping[object, object], value)
        for raw_key, nested in mapping.items():
            key = str(raw_key).lower()
            if key in _FORBIDDEN_PHYSICAL_KEYS:
                raise ValueError(f"logical action contains forbidden physical field: {key}")
            _reject_physical_content(nested, scan_string_values=scan_string_values)
    elif isinstance(value, (list, tuple)):
        for nested in cast(Sequence[object], value):
            _reject_physical_content(nested, scan_string_values=scan_string_values)
    elif scan_string_values and isinstance(value, str) and _IPV4.search(value):
        raise ValueError("logical action contains an IP address")


def _ordered_range(values: tuple[int, int] | tuple[float, float], label: str) -> None:
    if values[0] < 0 or values[1] < values[0]:
        raise ValueError(f"invalid {label} range")
