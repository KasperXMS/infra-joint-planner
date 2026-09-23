from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from infra_joint.agents.action import AgentAction, AgentActionType
from infra_joint.agents.context import AgentExecutionContext, AgentTaskView
from infra_joint.agents.information import InformationObject, InformationObjectRef
from infra_joint.agents.state import AgentState, AgentStatus, AgentStepRecord
from infra_joint.core.base import ContractModel
from infra_joint.core.state import InfrastructureState
from infra_joint.core.task import TaskContract
from infra_joint.core.workflow import WorkflowNode, WorkflowPlan
from infra_joint.operators.artifacts import ProducedArtifact
from infra_joint.runtime.executor import ExecutionResult

TraceEmitter = Callable[[str, dict[str, Any]], None]


class PreparedAgentAction(ContractModel):
    context: AgentExecutionContext
    action: AgentAction


class AgentManager:
    """Workflow-scoped logical-agent state and explicit communication manager."""

    def __init__(
        self,
        task: TaskContract,
        plan: WorkflowPlan,
        *,
        emit: TraceEmitter | None = None,
    ) -> None:
        self._task = AgentTaskView.from_contract(task)
        self._agents = {item.agent_id: item for item in plan.agents}
        self._nodes = {item.node_id: item for item in plan.nodes}
        self._owned_nodes = {
            agent_id: frozenset(node.node_id for node in plan.nodes if node.agent_id == agent_id)
            for agent_id in self._agents
        }
        self._completed_nodes: dict[str, set[str]] = {agent_id: set() for agent_id in self._agents}
        self._states = {
            agent_id: AgentState(agent_id=agent_id, status=AgentStatus.IDLE)
            for agent_id in self._agents
        }
        self._information = {
            item.artifact_id: InformationObject(
                object_id=item.artifact_id,
                producer_agent_id="task",
                producer_node_id="task",
                semantic_type=item.logical_type,
                media_type=item.media_type,
                size_bytes=item.size_bytes,
                locations=(),
                provenance=(f"task:{task.task_id}",),
            )
            for item in task.artifacts
        }
        self._emit = emit
        for agent in plan.agents:
            self._trace("agent.created", {"agent": agent.model_dump(mode="json")})
            self._trace_state(agent.agent_id, None, AgentStatus.IDLE)

    @property
    def states(self) -> tuple[AgentState, ...]:
        return tuple(self._states[key] for key in sorted(self._states))

    def mark_ready(self, agent_id: str) -> None:
        state = self._states[agent_id]
        if state.status in {AgentStatus.IDLE, AgentStatus.WAITING}:
            self._replace_status(agent_id, AgentStatus.READY)

    def prepare(
        self,
        node: WorkflowNode,
        infrastructure: InfrastructureState,
    ) -> PreparedAgentAction:
        agent = self._agents[node.agent_id]
        state = self._states[agent.agent_id]
        if state.status not in {AgentStatus.IDLE, AgentStatus.READY, AgentStatus.WAITING}:
            raise RuntimeError(f"logical agent is not available: {agent.agent_id}/{state.status}")
        if node.operator not in agent.allowed_operations:
            raise ValueError(
                f"operator {node.operator} is not allowed for logical agent {agent.agent_id}"
            )
        observed = {item.artifact_id: item for item in infrastructure.artifacts}
        references: list[InformationObjectRef] = []
        for object_id in node.inputs:
            try:
                information = self._information[object_id]
            except KeyError as exc:
                raise ValueError(f"incoming information is not registered: {object_id}") from exc
            runtime = observed.get(object_id)
            if runtime is None:
                raise ValueError(f"incoming information is not materialized: {object_id}")
            information = information.model_copy(
                update={
                    "locations": runtime.locations,
                    "size_bytes": runtime.size_bytes
                    if runtime.size_bytes is not None
                    else information.size_bytes,
                    "sha256_hex": runtime.sha256_hex,
                    "media_type": runtime.media_type or information.media_type,
                }
            )
            self._information[object_id] = information
            references.append(information.reference())
        context = AgentExecutionContext(
            task=self._task,
            agent=agent,
            state=state,
            node=node,
            inputs=tuple(references),
        )
        arguments = dict(node.arguments)
        action_type = AgentActionType.TOOL
        if node.operator == "invoke_model":
            action_type = AgentActionType.REASON
            arguments = self._model_arguments(context)
        action = AgentAction(
            agent_id=agent.agent_id,
            node_id=node.node_id,
            action_type=action_type,
            operator=node.operator,
            inputs=node.inputs,
            arguments=arguments,
            outputs=node.outputs,
        )
        return PreparedAgentAction(context=context, action=action)

    def start(self, prepared: PreparedAgentAction) -> None:
        agent_id = prepared.action.agent_id
        if self._states[agent_id].status == AgentStatus.RUNNING:
            raise RuntimeError(f"logical agent already has an active action: {agent_id}")
        self._replace_status(agent_id, AgentStatus.RUNNING)
        for item in prepared.context.inputs:
            self._trace(
                "agent.information.received",
                {
                    "agent_id": agent_id,
                    "node_id": prepared.action.node_id,
                    "information": item.model_dump(mode="json"),
                },
            )
        self._trace(
            "agent.action.start",
            {
                "context": prepared.context.model_dump(mode="json"),
                "action": prepared.action.model_dump(mode="json"),
            },
        )

    def succeed(
        self,
        prepared: PreparedAgentAction,
        execution: ExecutionResult,
        infrastructure: InfrastructureState,
    ) -> tuple[InformationObject, ...]:
        action = prepared.action
        produced = self._produced_information(action, execution, infrastructure)
        for item in produced:
            self._information[item.object_id] = item
            self._trace(
                "agent.information.produced",
                {
                    "agent_id": action.agent_id,
                    "node_id": action.node_id,
                    "information": item.model_dump(mode="json"),
                },
            )
        state = self._states[action.agent_id]
        record = AgentStepRecord(
            node_id=action.node_id,
            action=action,
            succeeded=True,
            received_objects=action.inputs,
            produced_objects=tuple(item.object_id for item in produced),
        )
        self._completed_nodes[action.agent_id].add(action.node_id)
        next_status = (
            AgentStatus.DONE
            if self._completed_nodes[action.agent_id] == set(self._owned_nodes[action.agent_id])
            else AgentStatus.WAITING
        )
        self._states[action.agent_id] = state.model_copy(
            update={
                "status": next_status,
                "history": (*state.history, record),
                "inbox": self._ordered_union(state.inbox, action.inputs),
                "produced_objects": self._ordered_union(
                    state.produced_objects, tuple(item.object_id for item in produced)
                ),
            }
        )
        self._trace(
            "agent.action.end",
            {
                "agent_id": action.agent_id,
                "node_id": action.node_id,
                "succeeded": True,
                "produced_objects": list(record.produced_objects),
            },
        )
        self._trace_state(action.agent_id, AgentStatus.RUNNING, next_status)
        return produced

    def fail(self, prepared: PreparedAgentAction, failure_code: str) -> None:
        action = prepared.action
        state = self._states[action.agent_id]
        record = AgentStepRecord(
            node_id=action.node_id,
            action=action,
            succeeded=False,
            received_objects=action.inputs,
            failure_code=failure_code,
        )
        self._states[action.agent_id] = state.model_copy(
            update={
                "status": AgentStatus.FAILED,
                "history": (*state.history, record),
                "inbox": self._ordered_union(state.inbox, action.inputs),
            }
        )
        self._trace(
            "agent.action.end",
            {
                "agent_id": action.agent_id,
                "node_id": action.node_id,
                "succeeded": False,
                "failure_code": failure_code,
            },
        )
        self._trace_state(action.agent_id, AgentStatus.RUNNING, AgentStatus.FAILED)

    def fail_unprepared(self, node_id: str, failure_code: str) -> None:
        agent_id = self._nodes[node_id].agent_id
        self._replace_status(agent_id, AgentStatus.FAILED)
        self._trace(
            "agent.action.end",
            {
                "agent_id": agent_id,
                "node_id": node_id,
                "succeeded": False,
                "failure_code": failure_code,
                "action_prepared": False,
            },
        )

    def _model_arguments(self, context: AgentExecutionContext) -> dict[str, Any]:
        instruction = context.node.arguments.get("prompt")
        if not isinstance(instruction, str) or not instruction:
            raise ValueError("invoke_model requires a non-empty prompt")
        incoming = (
            "\n".join(
                f"- {item.object_id} ({item.semantic_type}, {item.media_type}) "
                f"from {item.producer_agent_id}/{item.producer_node_id}"
                for item in context.inputs
            )
            or "- none"
        )
        prior_steps = (
            ", ".join(
                f"{item.node_id}:{'ok' if item.succeeded else 'failed'}"
                for item in context.state.history
            )
            or "none"
        )
        effective_prompt = "\n".join(
            (
                f"Agent identity: {context.agent.agent_id}",
                f"Role: {context.agent.role}",
                f"Objective: {context.agent.objective}",
                f"Task: {context.task.objective}",
                f"Prior agent steps: {prior_steps}",
                f"Current step ({context.node.node_id}): {instruction}",
                "Available incoming information:",
                incoming,
            )
        )
        arguments = dict(context.node.arguments)
        arguments["prompt"] = effective_prompt
        if context.node.outputs:
            if len(context.node.outputs) != 1:
                raise ValueError("invoke_model supports exactly one materialized output")
            output_id = context.node.outputs[0]
            configured = arguments.get("output_artifact_id", output_id)
            if configured != output_id:
                raise ValueError("invoke_model output_artifact_id must match node output")
            arguments["output_artifact_id"] = output_id
            arguments.setdefault("output_semantic_type", "model_reasoning")
            arguments.setdefault("output_media_type", "text/plain")
        return arguments

    def _produced_information(
        self,
        action: AgentAction,
        execution: ExecutionResult,
        infrastructure: InfrastructureState,
    ) -> tuple[InformationObject, ...]:
        if not action.outputs:
            return ()
        runtime = {item.artifact_id: item for item in infrastructure.artifacts}
        metadata = self._produced_metadata(execution)
        values: list[InformationObject] = []
        for object_id in action.outputs:
            produced = metadata.get(object_id)
            observed = runtime.get(object_id)
            if produced is None or observed is None:
                raise ValueError(f"produced information is not materialized: {object_id}")
            semantic_type = (
                str(action.arguments.get("output_semantic_type", "model_reasoning"))
                if action.action_type == AgentActionType.REASON
                else action.operator
            )
            values.append(
                InformationObject(
                    object_id=object_id,
                    producer_agent_id=action.agent_id,
                    producer_node_id=action.node_id,
                    semantic_type=semantic_type,
                    media_type=produced.media_type,
                    size_bytes=produced.size_bytes,
                    sha256_hex=produced.sha256_hex,
                    locations=observed.locations,
                    provenance=(*action.inputs, action.node_id),
                )
            )
        return tuple(values)

    @staticmethod
    def _produced_metadata(execution: ExecutionResult) -> dict[str, ProducedArtifact]:
        output = execution.output
        if "artifacts" in output:
            raw = output["artifacts"]
            if not isinstance(raw, list):
                raise ValueError("artifacts output must be a list")
            values = tuple(
                ProducedArtifact.model_validate(item) for item in cast(list[object], raw)
            )
        elif "artifact_id" in output:
            values = (ProducedArtifact.model_validate(output),)
        else:
            values = ()
        return {item.artifact_id: item for item in values}

    def _replace_status(self, agent_id: str, status: AgentStatus) -> None:
        previous = self._states[agent_id].status
        if previous == status:
            return
        self._states[agent_id] = self._states[agent_id].model_copy(update={"status": status})
        self._trace_state(agent_id, previous, status)

    def _trace_state(
        self,
        agent_id: str,
        previous: AgentStatus | None,
        current: AgentStatus,
    ) -> None:
        self._trace(
            "agent.state.changed",
            {
                "agent_id": agent_id,
                "previous": previous.value if previous is not None else "created",
                "current": current.value,
            },
        )

    def _trace(self, event_type: str, payload: dict[str, Any]) -> None:
        if self._emit is not None:
            self._emit(event_type, payload)

    @staticmethod
    def _ordered_union(left: tuple[str, ...], right: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*left, *right)))
