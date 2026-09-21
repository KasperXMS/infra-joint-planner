import asyncio
import json
import os
from dataclasses import dataclass
from time import perf_counter
from typing import Any, cast

from openai import AsyncOpenAI
from pydantic import TypeAdapter, ValidationError

from infra_joint.config import BackendConfig, StaticBackendConfig
from infra_joint.core.action import JointAction, JointDecision, SemanticAction
from infra_joint.core.state import EnvironmentSpec, InfrastructureState
from infra_joint.core.task import TaskContract
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.planning.graph import PlannerCallTelemetry, PlanningGraph, PlanningState
from infra_joint.planning.planner import (
    CompletionBackend,
    PlannerDecisionError,
    PlannerObservation,
    PlannerOutcome,
    logical_task_payload,
)
from infra_joint.runtime.client import WorkerClient
from infra_joint.worker.model_backend import (
    ModelBackend,
    ModelRequest,
    OpenAICompatibleModelBackend,
    StaticModelBackend,
)
from infra_joint.worker.server import (
    ExecuteOperatorResponse,
    PullArtifactResponse,
    PutArtifactResponse,
    WorkerStateResponse,
)


@dataclass(frozen=True, slots=True)
class NetworkRegime:
    regime_id: str
    bandwidth_mbps: float
    added_rtt_ms: float

    def __post_init__(self) -> None:
        if not self.regime_id:
            raise ValueError("regime_id must not be empty")
        if self.bandwidth_mbps <= 0:
            raise ValueError("bandwidth_mbps must be positive")
        if self.added_rtt_ms < 0:
            raise ValueError("added_rtt_ms must not be negative")


class ShapedWorkerClient:
    """Apply a minimum wall-clock transfer time to worker-to-worker artifact pulls."""

    def __init__(self, delegate: WorkerClient, regime: NetworkRegime) -> None:
        self.agent_id = delegate.agent_id
        self._delegate = delegate
        self._regime = regime

    async def get_state(self) -> WorkerStateResponse:
        return await self._delegate.get_state()

    def artifact_url(self, artifact_id: str) -> str:
        return self._delegate.artifact_url(artifact_id)

    async def pull_artifact(
        self,
        artifact_id: str,
        source_url: str,
        expected_sha256: str | None = None,
    ) -> PullArtifactResponse:
        started = perf_counter()
        response = await self._delegate.pull_artifact(
            artifact_id,
            source_url,
            expected_sha256,
        )
        minimum_seconds = self._regime.added_rtt_ms / 1000 + response.size_bytes * 8 / (
            self._regime.bandwidth_mbps * 1_000_000
        )
        remaining = minimum_seconds - (perf_counter() - started)
        if remaining > 0:
            await asyncio.sleep(remaining)
        return response

    async def put_artifact(
        self,
        artifact_id: str,
        media_type: str,
        content: bytes,
        expected_sha256: str,
    ) -> PutArtifactResponse:
        return await self._delegate.put_artifact(
            artifact_id,
            media_type,
            content,
            expected_sha256,
        )

    async def execute_operator(
        self,
        action: SemanticAction,
        deployment_id: str | None,
    ) -> ExecuteOperatorResponse:
        return await self._delegate.execute_operator(action, deployment_id)


@dataclass(frozen=True, slots=True)
class AwarePlannerContext:
    task: TaskContract
    decisions: tuple[JointDecision, ...]
    observations: tuple[PlannerObservation, ...]
    infrastructure: InfrastructureState
    remaining_steps: int


JOINT_DECISION_ADAPTER: TypeAdapter[JointDecision] = TypeAdapter(JointDecision)


class LLMNaiveAwarePlanner:
    """LLM planner that adds live physical state but no cost model or routing heuristic."""

    def __init__(
        self,
        backend: CompletionBackend,
        registry: OperatorRegistry,
        environment: EnvironmentSpec,
    ) -> None:
        self._backend = backend
        self._registry = registry
        self._environment = environment

    async def decide(self, context: AwarePlannerContext) -> PlannerOutcome:
        completion = await self._backend.invoke(ModelRequest(prompt=self.render_prompt(context)))
        try:
            decision = JOINT_DECISION_ADAPTER.validate_python(json.loads(completion.text))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise PlannerDecisionError(
                "aware planner must return exactly one valid JSON joint decision object"
            ) from exc
        if isinstance(decision, JointAction):
            try:
                self._registry.validate_action(decision.semantic)
            except (KeyError, ValueError) as exc:
                raise PlannerDecisionError(str(exc)) from exc
        return PlannerOutcome(decision=decision, model_telemetry=completion.telemetry)

    def render_prompt(self, context: AwarePlannerContext) -> str:
        state = context.infrastructure
        agent_state = {item.agent_id: item for item in state.agents}
        deployment_state = {item.deployment_id: item for item in state.deployments}
        infrastructure = {
            "agents": [
                {
                    "agent_id": item.agent_id,
                    "device": item.device,
                    "capabilities": sorted(item.capabilities),
                    "available": agent_state[item.agent_id].available,
                    "in_flight": agent_state[item.agent_id].in_flight,
                }
                for item in self._environment.agents
            ],
            "deployments": [
                {
                    **item.model_dump(mode="json"),
                    "available": deployment_state[item.deployment_id].available,
                }
                for item in self._environment.deployments
            ],
            "artifacts": [item.model_dump(mode="json") for item in state.artifacts],
            "links": [item.model_dump(mode="json") for item in state.links],
            "observed_at": state.observed_at.isoformat(),
        }
        tools = [
            tool
            for tool in self._registry.planner_tools()
            if tool["function"]["name"] != "read_artifact"
        ]
        payload = {
            "task": logical_task_payload(context.task),
            "available_operators": tools,
            "infrastructure": infrastructure,
            "decision_history": [item.model_dump(mode="json") for item in context.decisions],
            "observations": [item.model_dump(mode="json") for item in context.observations],
            "remaining_steps": context.remaining_steps,
        }
        action_shape: dict[str, Any] = {
            "decision_type": "action",
            "semantic": {
                "operator": "an available operator name",
                "inputs": ["logical artifact id"],
                "arguments": {},
            },
            "physical": {
                "policy": "auto|data_local|target_agent|target_deployment",
                "target_agent_id": None,
                "target_deployment_id": None,
            },
        }
        finish_shape = {"decision_type": "finish", "reason": "why evidence is sufficient"}
        return "\n".join(
            (
                "You are the infrastructure-aware joint planner in a controlled experiment.",
                "Choose exactly one next semantic action and physical decision, or finish.",
                "Use only the supplied current infrastructure state and logical evidence.",
                "Use only an available operator and satisfy its input and argument schemas.",
                "A target_agent policy requires target_agent_id only. A target_deployment policy "
                "requires target_deployment_id only. AUTO and data_local accept neither target.",
                "Return exactly one JSON object with no Markdown or surrounding text.",
                f"Action form: {json.dumps(action_shape, separators=(',', ':'))}",
                f"Finish form: {json.dumps(finish_shape, separators=(',', ':'))}",
                "State:",
                json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
            )
        )


class AwarePlanningGraph(PlanningGraph):
    """PlanningGraph variant whose only semantic change is the planner-visible H_t."""

    def __init__(self, *args: Any, aware_planner: LLMNaiveAwarePlanner, **kwargs: Any) -> None:
        self._aware_planner = aware_planner
        super().__init__(*args, planner=cast(Any, aware_planner), **kwargs)

    async def _plan(self, state: PlanningState) -> dict[str, object]:
        infrastructure = state["infrastructure"]
        if infrastructure is None:
            raise RuntimeError("aware plan node requires an infrastructure snapshot")
        context = AwarePlannerContext(
            task=state["task"],
            decisions=tuple(state["decisions"]),
            observations=tuple(
                PlannerObservation.from_execution(item) for item in state["observations"]
            ),
            infrastructure=infrastructure,
            remaining_steps=state["remaining_steps"],
        )
        trace_state = self._emit(
            state,
            "planner.start",
            {"remaining_steps": state["remaining_steps"]},
        )
        started = perf_counter()
        outcome = await self._aware_planner.decide(context)
        telemetry = PlannerCallTelemetry(
            latency_ms=(perf_counter() - started) * 1000,
            model=outcome.model_telemetry,
        )
        decision = outcome.decision
        trace_state = self._emit_from_values(
            run_id=state["run_id"],
            event_index=cast(int, trace_state["event_index"]),
            parent_event_id=cast(str, trace_state["parent_event_id"]),
            event_type="planner.end",
            payload={
                "decision": decision.model_dump(mode="json"),
                "telemetry": telemetry.model_dump(mode="json"),
            },
        )
        proposed = (
            "joint_action.proposed" if isinstance(decision, JointAction) else "finish.proposed"
        )
        trace_state = self._emit_from_values(
            run_id=state["run_id"],
            event_index=cast(int, trace_state["event_index"]),
            parent_event_id=cast(str, trace_state["parent_event_id"]),
            event_type=proposed,
            payload=decision.model_dump(mode="json"),
        )
        return {
            "pending_decision": decision,
            "decisions": [*state["decisions"], decision],
            "remaining_steps": state["remaining_steps"] - 1,
            "planner_telemetry": [*state["planner_telemetry"], telemetry],
            **trace_state,
        }


def build_no_retry_model_backend(
    config: BackendConfig,
) -> tuple[ModelBackend, AsyncOpenAI | None]:
    if isinstance(config, StaticBackendConfig):
        return StaticModelBackend(config.response), None
    try:
        api_key = os.environ[config.api_key_env]
    except KeyError as exc:
        raise RuntimeError(
            f"required API key environment variable is not set: {config.api_key_env}"
        ) from exc
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=config.base_url,
        max_retries=0,
    )
    return OpenAICompatibleModelBackend(client, config.model), client
