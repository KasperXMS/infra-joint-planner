from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Iterator
from time import perf_counter
from typing import Protocol, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import Field

from infra_joint.agents.context import AgentTaskView
from infra_joint.control.contracts import (
    ContinueDecision,
    FinishDecision,
    LogicalAgentSpec,
    LogicalObservation,
    ManagerContext,
    ManagerDecision,
    ProfileVisibility,
    SubagentCall,
    SubagentResult,
    WorkflowGraphSnapshot,
)
from infra_joint.control.gateway import ActionGateway
from infra_joint.control.graph import ExecutionGrownGraph
from infra_joint.control.physical import PhysicalExecutionOutcome
from infra_joint.core.base import ContractModel
from infra_joint.core.task import OutputFormat, TaskContract
from infra_joint.workflow.trace import WorkflowTraceRecorder


class ManagerPolicy(Protocol):
    async def decide(self, context: ManagerContext) -> ManagerDecision: ...


class SubagentPolicyFactory(Protocol):
    def create(self, call: SubagentCall) -> ManagerPolicy: ...


class PlannerStepTelemetry(ContractModel):
    logical_agent_id: str = Field(min_length=1)
    latency_ms: float = Field(ge=0)


class AgentLoopResult(ContractModel):
    final_answer: str
    terminal_action_id: str = Field(min_length=1)
    observations: tuple[LogicalObservation, ...]
    subagent_results: tuple[SubagentResult, ...]
    graph_snapshots: tuple[WorkflowGraphSnapshot, ...]
    planner_steps: tuple[PlannerStepTelemetry, ...]


class AgentLoopError(RuntimeError):
    pass


class PersistentManagerLoop:
    """Observation-driven manager loop; no complete future DAG is requested."""

    def __init__(
        self,
        gateway: ActionGateway,
        manager: ManagerPolicy,
        *,
        root_agent: LogicalAgentSpec | None = None,
        subagent_factory: SubagentPolicyFactory | None = None,
        profile_visibility: ProfileVisibility = ProfileVisibility.BLIND,
        max_steps_per_agent: int = 12,
        trace: WorkflowTraceRecorder | None = None,
    ) -> None:
        if max_steps_per_agent < 1:
            raise ValueError("max_steps_per_agent must be positive")
        self._gateway = gateway
        self._manager = manager
        self._root = root_agent or LogicalAgentSpec(
            logical_agent_id="manager",
            role="global task manager",
            objective="solve the task using bounded tools and specialist agents",
        )
        self._subagent_factory = subagent_factory
        self._visibility = profile_visibility
        self._max_steps = max_steps_per_agent
        self._trace = trace
        self._graph = ExecutionGrownGraph()
        self._task: AgentTaskView | None = None
        self._observations: list[LogicalObservation] = []
        self._observations_by_agent: dict[str, list[LogicalObservation]] = {}
        self._subagent_results: list[SubagentResult] = []
        self._planner_steps: list[PlannerStepTelemetry] = []
        self._known_agents: set[str] = {self._root.logical_agent_id}
        self._accessible_by_agent: dict[str, set[str]] = {}
        self._produced_by_agent: dict[str, set[str]] = {}
        self._requirements_by_agent: dict[str, list[str]] = {}

    async def run(self, task: TaskContract) -> AgentLoopResult:
        self._task = AgentTaskView.from_contract(task)
        self._emit(
            "logical.loop.start",
            {
                "task": self._task.model_dump(mode="json"),
                "profile_visibility": self._visibility.value,
                "root_agent": self._root.model_dump(mode="json"),
            },
        )
        self._emit(
            "workflow.graph.snapshot",
            self._graph.snapshot().model_dump(mode="json"),
        )
        root_artifacts = tuple(item.artifact_id for item in self._task.artifacts)
        answer, terminal = await self._run_agent(
            self._root,
            self._manager,
            self._task,
            root_artifacts,
        )
        result = AgentLoopResult(
            final_answer=answer,
            terminal_action_id=terminal,
            observations=tuple(self._observations),
            subagent_results=tuple(self._subagent_results),
            graph_snapshots=self._graph.snapshots,
            planner_steps=tuple(self._planner_steps),
        )
        self._emit(
            "logical.loop.end",
            {
                "terminal_action_id": terminal,
                "final_answer": answer,
                "graph_version": self._graph.snapshot().version,
            },
        )
        return result

    async def _run_agent(
        self,
        agent: LogicalAgentSpec,
        policy: ManagerPolicy,
        task_view: AgentTaskView,
        assigned_artifacts: tuple[str, ...],
    ) -> tuple[str, str]:
        local_subagents: list[SubagentResult] = []
        self._observations_by_agent.setdefault(agent.logical_agent_id, [])
        self._accessible_by_agent[agent.logical_agent_id] = set(assigned_artifacts)
        self._produced_by_agent[agent.logical_agent_id] = set()
        self._requirements_by_agent[agent.logical_agent_id] = [agent.objective]
        for step in range(self._max_steps):
            profile = None
            if self._visibility == ProfileVisibility.AWARE:
                profile = await self._gateway.profile_overview()
            context = ManagerContext(
                task=task_view,
                agent=agent,
                assigned_artifacts=tuple(
                    sorted(self._accessible_by_agent[agent.logical_agent_id])
                ),
                unresolved_requirements=tuple(
                    self._requirements_by_agent[agent.logical_agent_id]
                ),
                observations=tuple(self._observations_by_agent[agent.logical_agent_id]),
                subagent_results=tuple(local_subagents),
                workflow=self._graph.snapshot(),
                physical_profile=profile,
            )
            started = perf_counter()
            decision = await policy.decide(context)
            telemetry = PlannerStepTelemetry(
                logical_agent_id=agent.logical_agent_id,
                latency_ms=(perf_counter() - started) * 1000,
            )
            self._planner_steps.append(telemetry)
            self._emit(
                "logical.decision",
                {
                    "logical_agent_id": agent.logical_agent_id,
                    "iteration": step,
                    "decision": decision.model_dump(mode="json"),
                    "telemetry": telemetry.model_dump(mode="json"),
                },
            )
            if isinstance(decision, FinishDecision):
                answer = self._terminal_answer(agent, decision)
                return answer, decision.source_action_id
            self._validate_decision_owner(agent, decision)
            self._update_requirements(agent.logical_agent_id, decision)
            if decision.subagent_calls:
                results = await self._run_subagents(
                    agent.logical_agent_id,
                    decision.subagent_calls,
                )
                local_subagents.extend(results)
            if decision.actions:
                await self._execute_actions(decision)
        raise AgentLoopError(
            f"logical agent exceeded its step budget: {agent.logical_agent_id}"
        )

    async def _run_subagents(
        self,
        parent_agent_id: str,
        calls: tuple[SubagentCall, ...],
    ) -> tuple[SubagentResult, ...]:
        if self._subagent_factory is None:
            raise AgentLoopError("manager requested a subagent but no factory is configured")
        factory = self._subagent_factory
        call_ids = [item.call_id for item in calls]
        agent_ids = [item.agent.logical_agent_id for item in calls]
        if len(call_ids) != len(set(call_ids)):
            raise AgentLoopError("subagent call IDs must be unique within a manager step")
        if len(agent_ids) != len(set(agent_ids)):
            raise AgentLoopError("subagent IDs must be unique within a manager step")
        collisions = sorted(set(agent_ids) & self._known_agents)
        if collisions:
            raise AgentLoopError(f"logical agent IDs already exist: {collisions}")
        self._known_agents.update(agent_ids)
        parent_access = self._accessible_by_agent[parent_agent_id]
        for call in calls:
            missing = sorted(set(call.input_artifacts) - parent_access)
            if missing:
                raise AgentLoopError(
                    f"subagent call references unavailable artifacts: {missing}"
                )

        async def invoke(call: SubagentCall) -> SubagentResult:
            self._emit("logical.subagent.start", call.model_dump(mode="json"))
            answer, terminal = await self._run_agent(
                call.agent,
                factory.create(call),
                self._subagent_task_view(call),
                call.input_artifacts,
            )
            result = SubagentResult(
                call_id=call.call_id,
                logical_agent_id=call.agent.logical_agent_id,
                terminal_action_id=terminal,
                answer=answer,
            )
            self._subagent_results.append(result)
            self._accessible_by_agent[parent_agent_id].update(
                self._produced_by_agent[call.agent.logical_agent_id]
            )
            self._emit("logical.subagent.end", result.model_dump(mode="json"))
            return result

        return tuple(await asyncio.gather(*(invoke(call) for call in calls)))

    async def _execute_actions(self, decision: ContinueDecision) -> None:
        actions = decision.actions
        self._gateway.validate_batch(actions)
        snapshot = self._graph.add(actions)
        self._emit("workflow.graph.snapshot", snapshot.model_dump(mode="json"))
        running = self._graph.mark_running(tuple(item.action_id for item in actions))
        self._emit("workflow.graph.snapshot", running.model_dump(mode="json"))
        outcomes = await self._gateway.execute_batch(
            actions,
            expose_profile=self._visibility == ProfileVisibility.AWARE,
        )
        succeeded: list[str] = []
        failed: list[str] = []
        for action, outcome in zip(actions, outcomes, strict=True):
            observation = outcome.observation
            self._observations.append(observation)
            self._observations_by_agent[action.owner_agent_id].append(observation)
            if observation.succeeded:
                produced = {
                    item.artifact_id for item in observation.produced_information
                }
                self._accessible_by_agent[action.owner_agent_id].update(produced)
                self._produced_by_agent[action.owner_agent_id].update(produced)
            (succeeded if observation.succeeded else failed).append(action.action_id)
            self._emit_outcome(action.action_id, outcome)
        completed = self._graph.mark_finished(tuple(succeeded), tuple(failed))
        self._emit("workflow.graph.snapshot", completed.model_dump(mode="json"))

    def _terminal_answer(
        self,
        agent: LogicalAgentSpec,
        decision: FinishDecision,
    ) -> str:
        matches = [
            item
            for item in self._observations_by_agent[agent.logical_agent_id]
            if item.action_id == decision.source_action_id and item.succeeded
        ]
        if len(matches) != 1:
            raise AgentLoopError(
                "finish must reference one successful action owned by the finishing agent"
            )
        text = matches[0].output.get("text")
        if not isinstance(text, str):
            raise AgentLoopError("terminal action did not return model text")
        node = next(
            (
                item
                for item in self._graph.snapshot().nodes
                if item.action_id == decision.source_action_id
            ),
            None,
        )
        if node is None or node.action_type != "model":
            raise AgentLoopError("finish source must be a model action")
        self._validate_output_contract(text)
        return text

    def _validate_output_contract(self, answer: str) -> None:
        contract = self._require_task().output_contract
        if contract.format == OutputFormat.CHOICE:
            if contract.choices is None or answer not in contract.choices:
                raise AgentLoopError("terminal answer violates the choice output contract")
            return
        if contract.format == OutputFormat.SHORT_TEXT:
            if not answer.strip():
                raise AgentLoopError("terminal answer violates the short-text output contract")
            return
        try:
            parsed = json.loads(answer)
        except json.JSONDecodeError as exc:
            raise AgentLoopError("terminal answer is not valid JSON") from exc
        schema = contract.schema_definition
        if schema is None:
            raise AgentLoopError("structured output contract has no schema")
        errors = cast(
            Iterator[JsonSchemaValidationError],
            Draft202012Validator(schema).iter_errors(parsed),  # pyright: ignore[reportUnknownMemberType]
        )
        error = next(errors, None)
        if error is not None:
            raise AgentLoopError(f"terminal answer violates output schema: {error.message}")

    def _validate_decision_owner(
        self,
        agent: LogicalAgentSpec,
        decision: ContinueDecision,
    ) -> None:
        wrong = sorted(
            item.action_id
            for item in decision.actions
            if item.owner_agent_id != agent.logical_agent_id
        )
        if wrong:
            raise AgentLoopError(
                f"agent may only issue its own executable actions: {wrong}"
            )
        if len(decision.actions) > 1:
            raise AgentLoopError("one logical agent may have only one active action")
        inaccessible = sorted(
            {
                artifact_id
                for action in decision.actions
                for artifact_id in action.inputs
                if artifact_id not in self._accessible_by_agent[agent.logical_agent_id]
            }
        )
        if inaccessible:
            raise AgentLoopError(
                f"logical agent cannot access unassigned artifacts: {inaccessible}"
            )

    def _subagent_task_view(self, call: SubagentCall) -> AgentTaskView:
        task = self._require_task()
        admitted = set(call.input_artifacts)
        return task.model_copy(
            update={
                "artifacts": tuple(
                    item for item in task.artifacts if item.artifact_id in admitted
                )
            }
        )

    def _update_requirements(
        self,
        agent_id: str,
        decision: ContinueDecision,
    ) -> None:
        unresolved = self._requirements_by_agent[agent_id]
        missing = sorted(set(decision.resolved_requirements) - set(unresolved))
        if missing:
            raise AgentLoopError(
                f"decision resolves unknown requirements: {missing}"
            )
        resolved = set(decision.resolved_requirements)
        remaining = [item for item in unresolved if item not in resolved]
        for item in decision.new_requirements:
            if item not in remaining:
                remaining.append(item)
        self._requirements_by_agent[agent_id] = remaining

    def _emit_outcome(
        self,
        action_id: str,
        outcome: PhysicalExecutionOutcome,
    ) -> None:
        self._emit(
            "logical.observation",
            outcome.observation.model_dump(mode="json"),
        )
        payload: dict[str, object] = {"action_id": action_id}
        if outcome.selection is not None:
            payload["selection"] = outcome.selection.model_dump(mode="json")
        if outcome.execution is not None:
            payload["execution"] = outcome.execution.model_dump(mode="json")
        self._emit("physical.execution", payload)

    def _require_task(self) -> AgentTaskView:
        if self._task is None:
            raise RuntimeError("agent loop has not started")
        return self._task

    def _emit(self, event_type: str, payload: dict[str, object]) -> None:
        if self._trace is not None:
            self._trace.emit(event_type, payload)


class ScriptedManagerPolicy:
    """Deterministic policy for smoke tests and contract-level replay only."""

    def __init__(self, decisions: tuple[ManagerDecision, ...]) -> None:
        self._decisions = decisions
        self._index = 0
        self.contexts: list[ManagerContext] = []

    async def decide(self, context: ManagerContext) -> ManagerDecision:
        self.contexts.append(context)
        if self._index >= len(self._decisions):
            raise AgentLoopError("scripted manager has no remaining decisions")
        value = self._decisions[self._index]
        self._index += 1
        return value


class ScriptedSubagentFactory:
    def __init__(
        self,
        policies: dict[str, ManagerPolicy] | Callable[[SubagentCall], ManagerPolicy],
    ) -> None:
        self._policies = policies

    def create(self, call: SubagentCall) -> ManagerPolicy:
        if callable(self._policies):
            return self._policies(call)
        try:
            return self._policies[call.call_id]
        except KeyError as exc:
            raise AgentLoopError(f"no policy for subagent call: {call.call_id}") from exc
