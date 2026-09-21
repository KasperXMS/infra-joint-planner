import json
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Annotated, Any, Literal, Protocol

from pydantic import Field, TypeAdapter, ValidationError

from infra_joint.core.action import (
    FinishDecision,
    JointAction,
    JointDecision,
    PhysicalDecision,
    PhysicalPolicy,
    SemanticAction,
)
from infra_joint.core.base import ContractModel
from infra_joint.core.task import TaskContract
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.runtime.executor import ExecutionResult
from infra_joint.worker.model_backend import (
    ModelCallTelemetry,
    ModelCompletion,
    ModelRequest,
)


class CompletionBackend(Protocol):
    async def invoke(self, request: ModelRequest) -> ModelCompletion: ...


class PlannerOutcome(ContractModel):
    decision: JointDecision
    model_telemetry: ModelCallTelemetry | None = None


class PlannerObservation(ContractModel):
    """Logical execution result with all physical binding fields removed."""

    operator: str = Field(min_length=1)
    output: dict[str, Any]

    @classmethod
    def from_execution(cls, result: ExecutionResult) -> "PlannerObservation":
        return cls(operator=result.operator, output=result.output)


@dataclass(frozen=True, slots=True)
class BlindPlannerContext:
    """Planner view that deliberately contains no infrastructure state."""

    task: TaskContract
    decisions: tuple[JointDecision, ...]
    observations: tuple[PlannerObservation, ...]
    remaining_steps: int


class BlindPlanner(Protocol):
    async def decide(self, context: BlindPlannerContext) -> PlannerOutcome: ...


class ScriptedBlindPlanner:
    """Deterministic planner used to validate the execution substrate."""

    def __init__(self, decisions: Iterable[JointDecision]) -> None:
        self._decisions = deque(decisions)

    async def decide(self, context: BlindPlannerContext) -> PlannerOutcome:
        del context
        if not self._decisions:
            raise RuntimeError("scripted planner has no decision remaining")
        return PlannerOutcome(decision=self._decisions.popleft())


class BlindActionProposal(ContractModel):
    decision_type: Literal["action"] = "action"
    operator: str = Field(min_length=1)
    inputs: tuple[str, ...] = ()
    arguments: dict[str, Any] = Field(default_factory=dict)


class BlindFinishProposal(ContractModel):
    decision_type: Literal["finish"] = "finish"
    reason: str = Field(min_length=1)


BlindProposal = Annotated[
    BlindActionProposal | BlindFinishProposal,
    Field(discriminator="decision_type"),
]
BLIND_PROPOSAL_ADAPTER: TypeAdapter[BlindProposal] = TypeAdapter(BlindProposal)


class PlannerDecisionError(ValueError):
    pass


def logical_decision_payload(decision: JointDecision) -> dict[str, Any]:
    if isinstance(decision, JointAction):
        return {
            "decision_type": "action",
            "semantic": decision.semantic.model_dump(mode="json"),
        }
    return {"decision_type": "finish", "reason": decision.reason}


def logical_task_payload(task: TaskContract) -> dict[str, Any]:
    """Planner task view deliberately omits source refs and evaluator metadata."""

    return {
        "task_id": task.task_id,
        "benchmark_id": task.benchmark_id,
        "objective": task.objective,
        "artifacts": [
            {
                "artifact_id": artifact.artifact_id,
                "logical_type": artifact.logical_type,
                "media_type": artifact.media_type,
                "size_bytes": artifact.size_bytes,
            }
            for artifact in task.artifacts
        ],
        "output_contract": task.output_contract.model_dump(mode="json", by_alias=True),
    }


class LLMBlindPlanner:
    """LLM planner limited to logical state and AUTO physical placement."""

    def __init__(self, backend: CompletionBackend, registry: OperatorRegistry) -> None:
        self._backend = backend
        self._registry = registry

    async def decide(self, context: BlindPlannerContext) -> PlannerOutcome:
        completion = await self._backend.invoke(ModelRequest(prompt=self.render_prompt(context)))
        try:
            raw = json.loads(completion.text)
            proposal = BLIND_PROPOSAL_ADAPTER.validate_python(raw)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise PlannerDecisionError(
                "blind planner must return exactly one valid JSON decision object"
            ) from exc
        if isinstance(proposal, BlindFinishProposal):
            return PlannerOutcome(
                decision=FinishDecision(reason=proposal.reason),
                model_telemetry=completion.telemetry,
            )
        action = SemanticAction(
            operator=proposal.operator,
            inputs=proposal.inputs,
            arguments=proposal.arguments,
        )
        try:
            self._registry.validate_action(action)
        except (KeyError, ValueError) as exc:
            raise PlannerDecisionError(str(exc)) from exc
        return PlannerOutcome(
            decision=JointAction(
                semantic=action,
                physical=PhysicalDecision(policy=PhysicalPolicy.AUTO),
            ),
            model_telemetry=completion.telemetry,
        )

    def render_prompt(self, context: BlindPlannerContext) -> str:
        planner_tools = [
            tool
            for tool in self._registry.planner_tools()
            if tool["function"]["name"] != "read_artifact"
        ]
        payload = {
            "task": logical_task_payload(context.task),
            "available_operators": planner_tools,
            "decision_history": [
                logical_decision_payload(decision) for decision in context.decisions
            ],
            "observations": [
                observation.model_dump(mode="json") for observation in context.observations
            ],
            "remaining_steps": context.remaining_steps,
        }
        action_shape: dict[str, Any] = {
            "decision_type": "action",
            "operator": "an available operator name",
            "inputs": ["logical artifact id"],
            "arguments": {},
        }
        finish_shape: dict[str, Any] = {
            "decision_type": "finish",
            "reason": "why evidence is sufficient",
        }
        return "\n".join(
            (
                "You are the blind semantic planner in a controlled benchmark run.",
                "You have no infrastructure visibility. Choose only the next logical action.",
                "Physical placement is applied separately as AUTO; do not name agents, hosts, "
                "deployments, devices, networks, or physical policies.",
                "Use only an available operator and satisfy its inputs and arguments schema.",
                "Use invoke_model with relevant text/image artifacts for semantic reasoning. "
                "Use read_artifact only for tiny control or metadata text, never benchmark "
                "evidence. Reduce large structured or media artifacts before model invocation.",
                "When video sampling yields many frames, make a contact sheet before invoking "
                "the model so the image set remains bounded.",
                "Return exactly one JSON object with no Markdown or surrounding text.",
                f"Action form: {json.dumps(action_shape, separators=(',', ':'))}",
                f"Finish form: {json.dumps(finish_shape, separators=(',', ':'))}",
                "State:",
                json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
            )
        )
