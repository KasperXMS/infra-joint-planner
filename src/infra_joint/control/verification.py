from __future__ import annotations

import importlib
import re
from collections.abc import Mapping, Sequence
from time import perf_counter
from typing import Any, Literal, Protocol, Self, cast

from pydantic import Field, model_validator

from infra_joint.agents.context import AgentTaskView
from infra_joint.control.contracts import (
    ExecutionRequirements,
    LogicalOutput,
    ProducedInformation,
    WorkflowGraphSnapshot,
)
from infra_joint.core.base import ContractModel


class VerificationResult(ContractModel):
    """A Blind evidence-sufficiency verdict; never a benchmark answer."""

    status: Literal["continue", "ready_for_synthesis", "complete"]
    failure_stage: Literal[
        "evidence_collection", "execution", "synthesis", "none"
    ]
    reason: str = Field(min_length=1)
    missing_requirements: tuple[str, ...] = ()

    @model_validator(mode="after")
    def status_matches_stage(self) -> Self:
        if self.status in {"ready_for_synthesis", "complete"} and (
            self.failure_stage != "none"
        ):
            raise ValueError("ready_for_synthesis and complete require failure_stage=none")
        if self.status == "continue" and self.failure_stage == "none":
            raise ValueError("continue requires a concrete failure_stage")
        if len(self.missing_requirements) != len(set(self.missing_requirements)):
            raise ValueError("missing requirements must be unique")
        return self


class VerifierBudgetView(ContractModel):
    remaining_manager_turns: int = Field(ge=0)
    remaining_tool_model_calls: int = Field(ge=0)
    remaining_created_subagents: int = Field(ge=0)
    remaining_verifier_calls: int = Field(ge=0)


class VerifierObservation(ContractModel):
    action_id: str = Field(min_length=1)
    owner_agent_id: str = Field(min_length=1)
    succeeded: bool
    output: dict[str, Any] = Field(default_factory=dict)
    produced_information: tuple[ProducedInformation, ...] = ()
    failure_code: str | None = None
    failure_message: str | None = None


class VerifierActionView(ContractModel):
    """Physical-identity-free semantic intent of one accepted logical action."""

    action_id: str = Field(min_length=1)
    owner_agent_id: str = Field(min_length=1)
    action_type: Literal["tool", "model"]
    operator: str = Field(min_length=1)
    description: str = Field(min_length=1)
    inputs: tuple[str, ...] = ()
    outputs: tuple[LogicalOutput, ...] = ()
    arguments: dict[str, Any] = Field(default_factory=dict)
    prompt: str | None = None
    requirements: ExecutionRequirements | None = None

    @model_validator(mode="after")
    def semantic_request_matches_action_type(self) -> Self:
        if self.action_type == "tool" and (
            self.prompt is not None or self.requirements is not None
        ):
            raise ValueError("tool action view cannot contain a model request")
        if self.action_type == "model" and (
            self.operator != "invoke_model"
            or self.prompt is None
            or self.requirements is None
            or self.arguments
        ):
            raise ValueError("model action view requires only prompt and requirements")
        _reject_private_or_physical(self.model_dump(mode="json", exclude_none=True))
        return self


class VerificationContext(ContractModel):
    """Resource-blind semantic state provided to the independent verifier."""

    task: AgentTaskView
    workflow: WorkflowGraphSnapshot
    actions: tuple[VerifierActionView, ...]
    observations: tuple[VerifierObservation, ...]
    produced_artifacts: tuple[ProducedInformation, ...]
    phase: Literal["evidence_collection", "synthesis"]
    remaining_budget: VerifierBudgetView

    @model_validator(mode="after")
    def contains_no_private_or_physical_state(self) -> Self:
        _reject_private_or_physical(self.model_dump(mode="json", exclude_none=True))
        return self


class VerificationResponse(ContractModel):
    result: VerificationResult
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)


class VerificationTelemetry(ContractModel):
    verification_index: int = Field(gt=0)
    graph_version: int = Field(ge=0)
    result: VerificationResult
    latency_ms: float = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    remaining_budget: VerifierBudgetView


class BlindVerifier(Protocol):
    async def verify(self, context: VerificationContext) -> VerificationResponse: ...


class OpenAIAgentsBlindVerifier:
    """Harness-owned Blind verifier using one schema-constrained function call."""

    INSTRUCTIONS = (
        "You are an independent resource-blind evidence sufficiency verifier. Judge only "
        "whether the materialized semantic evidence is sufficient for the manager to perform "
        "final synthesis under the task output contract. Return continue when evidence is "
        "missing, irrelevant, conflicting, when an execution failure still blocks the task, or "
        "when a failed synthesis needs recovery. Return ready_for_synthesis only when the "
        "available observations support a final synthesis attempt. Return complete only when a "
        "successful manager-owned model observation already contains a non-empty candidate that "
        "directly answers the task and satisfies its terminal output contract; never rewrite that "
        "candidate. Never answer the benchmark question, never reveal or infer gold/evaluator "
        "data, never prescribe an operator or "
        "physical action, and never reason about devices, deployments, placement, network, "
        "load, queue, latency, or routes. missing_requirements must describe semantic gaps, not "
        "commands. Successful evidence-producing actions materialize their declared outputs for "
        "later model consumption; do not require complete artifact bodies to be copied into your "
        "context when the semantic action intent and bounded observations establish useful task "
        "coverage. Use the remaining logical budget to avoid unnecessary expansion, but never "
        "declare readiness solely because budget is low. Apply this state machine strictly: "
        "(1) when task-relevant materialized evidence is sufficient but no successful candidate "
        "answer exists, return ready_for_synthesis; do not return continue merely because a model "
        "has not yet synthesized the evidence; (2) when a successful manager-owned candidate "
        "already directly answers the task and satisfies the output contract, return complete; "
        "(3) return continue only for a concrete evidence gap, conflict, failed synthesis, or "
        "recoverable execution blocker. ready_for_synthesis must use "
        "failure_stage=none; complete also requires failure_stage=none; continue must identify "
        "the current stage."
    )

    def __init__(
        self,
        *,
        model: object,
        sdk_module: object | None = None,
    ) -> None:
        sdk = sdk_module or _load_agents_sdk()
        agent_constructor = sdk.__dict__["Agent"]
        tool_constructor = sdk.__dict__["FunctionTool"]
        settings_constructor = cast(Any, sdk.__dict__.get("ModelSettings"))

        async def submit_verification(_context: object, input_json: str) -> str:
            verdict = VerificationResult.model_validate_json(input_json)
            return verdict.model_dump_json()

        verdict_tool = tool_constructor(
            name="submit_verification",
            description=(
                "Submit exactly one resource-blind semantic evidence-sufficiency verdict. "
                "This tool records a verdict; it does not execute task actions or produce "
                "the benchmark answer."
            ),
            params_json_schema=VerificationResult.model_json_schema(),
            on_invoke_tool=submit_verification,
            strict_json_schema=False,
        )
        settings = (
            settings_constructor(
                temperature=0,
                parallel_tool_calls=False,
                tool_choice="required",
            )
            if settings_constructor is not None
            else None
        )
        kwargs: dict[str, object] = {
            "name": "blind_evidence_verifier",
            "instructions": self.INSTRUCTIONS,
            "model": model,
            "tools": [verdict_tool],
            "tool_use_behavior": "stop_on_first_tool",
        }
        if settings is not None:
            kwargs["model_settings"] = settings
        self._agent = agent_constructor(**kwargs)
        self._runner = sdk.__dict__["Runner"]

    async def verify(self, context: VerificationContext) -> VerificationResponse:
        result = await self._runner.run(
            self._agent,
            input=context.model_dump_json(),
            max_turns=1,
        )
        raw = getattr(result, "final_output", None)
        if isinstance(raw, VerificationResult):
            verdict = raw
        elif isinstance(raw, str):
            verdict = VerificationResult.model_validate_json(raw)
        else:
            verdict = VerificationResult.model_validate(raw)
        usage = getattr(getattr(result, "context_wrapper", None), "usage", None)
        return VerificationResponse(
            result=verdict,
            input_tokens=int(getattr(usage, "input_tokens", 0)),
            output_tokens=int(getattr(usage, "output_tokens", 0)),
        )


async def invoke_verifier(
    verifier: BlindVerifier,
    context: VerificationContext,
    *,
    verification_index: int,
) -> VerificationTelemetry:
    started = perf_counter()
    response = await verifier.verify(context)
    return VerificationTelemetry(
        verification_index=verification_index,
        graph_version=context.workflow.version,
        result=response.result,
        latency_ms=(perf_counter() - started) * 1000,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        remaining_budget=context.remaining_budget,
    )


def _load_agents_sdk() -> object:
    try:
        return importlib.import_module("agents")
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI Agents SDK is not installed; install the project's 'agents' extra"
        ) from exc


_IPV4 = re.compile(r"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])")
_FORBIDDEN_KEYS = frozenset(
    {
        "worker_id",
        "agent_id",
        "deployment_id",
        "selected_agent_id",
        "selected_deployment_id",
        "source_ref",
        "evaluator_id",
        "gold",
        "gold_answer",
        "supporting_evidence",
        "physical_profile",
        "placement",
        "network",
        "bandwidth",
        "rtt",
        "queue",
        "load",
        "route",
    }
)


def _reject_private_or_physical(value: object) -> None:
    if isinstance(value, Mapping):
        for raw_key, nested in cast(Mapping[object, object], value).items():
            key = str(raw_key).lower()
            if key in _FORBIDDEN_KEYS:
                raise ValueError(f"Blind verifier context contains forbidden field: {key}")
            _reject_private_or_physical(nested)
        return
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for nested in cast(Sequence[object], value):
            _reject_private_or_physical(nested)
        return
    if isinstance(value, str) and ("private://" in value or _IPV4.search(value)):
        raise ValueError("Blind verifier context contains private or physical identity")


__all__ = [
    "BlindVerifier",
    "OpenAIAgentsBlindVerifier",
    "VerifierActionView",
    "VerificationContext",
    "VerificationResponse",
    "VerificationResult",
    "VerificationTelemetry",
    "VerifierBudgetView",
    "VerifierObservation",
    "invoke_verifier",
]
