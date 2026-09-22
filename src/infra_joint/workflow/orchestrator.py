import asyncio
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, cast

from pydantic import Field, ValidationError

from infra_joint.core.action import JointAction
from infra_joint.core.base import ContractModel
from infra_joint.core.errors import TypedExecutionError
from infra_joint.core.state import EnvironmentSpec, InfrastructureState
from infra_joint.core.task import TaskContract
from infra_joint.core.workflow import (
    LogicalAgent,
    NodeStatus,
    WorkflowNode,
    WorkflowPlan,
    WorkflowState,
)
from infra_joint.infrastructure.observer import InfrastructureObserver
from infra_joint.operators.artifacts import ProducedArtifact
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.runtime.executor import ActionExecutor, ExecutionResult
from infra_joint.runtime.resolver import BindingResolutionError, DeterministicResolver
from infra_joint.workflow.scheduler import (
    SchedulerDecision,
    SchedulingError,
    WorkflowScheduler,
)
from infra_joint.workflow.trace import WorkflowTraceRecorder


class WorkflowFailure(ContractModel):
    code: str = Field(min_length=1)
    node_id: str = Field(min_length=1)
    exception_type: str = Field(min_length=1)
    message: str = Field(min_length=1)


class WorkflowNodeRecord(ContractModel):
    node_id: str = Field(min_length=1)
    scheduling_batch: int = Field(ge=0)
    started_at: datetime
    ended_at: datetime
    duration_ms: float = Field(ge=0)
    scheduler_decision: SchedulerDecision
    action: JointAction
    execution: ExecutionResult | None = None
    failure: WorkflowFailure | None = None


class WorkflowExecutionTelemetry(ContractModel):
    e2e_latency_ms: float = Field(ge=0)
    critical_path_latency_ms: float = Field(ge=0)
    parallel_overlap_ms: float = Field(ge=0)
    max_parallelism: int = Field(ge=0)
    total_transfer_bytes: int = Field(ge=0)
    total_transfer_duration_ms: float = Field(ge=0)
    total_operator_latency_ms: float = Field(ge=0)
    total_model_service_latency_ms: float = Field(ge=0)


class WorkflowExecutionResult(ContractModel):
    completed: bool
    state: WorkflowState
    records: tuple[WorkflowNodeRecord, ...]
    telemetry: WorkflowExecutionTelemetry
    failure: WorkflowFailure | None = None


class WorkflowOutputContractError(RuntimeError):
    pass


class _ScheduledNode(ContractModel):
    node: WorkflowNode
    decision: SchedulerDecision
    action: JointAction
    resolved_agent_id: str = Field(min_length=1)


class WorkflowOrchestrator:
    """Execute a validated plan-once DAG through the existing M4 RuntimeExecutor."""

    def __init__(
        self,
        registry: OperatorRegistry,
        environment: EnvironmentSpec,
        observer: InfrastructureObserver,
        executor: ActionExecutor,
        scheduler: WorkflowScheduler,
        *,
        trace: WorkflowTraceRecorder | None = None,
        resolver: DeterministicResolver | None = None,
    ) -> None:
        self._registry = registry
        self._environment = environment
        self._observer = observer
        self._executor = executor
        self._scheduler = scheduler
        self._trace = trace
        self._resolver = resolver or DeterministicResolver()

    async def execute(
        self,
        task: TaskContract,
        plan: WorkflowPlan,
    ) -> WorkflowExecutionResult:
        plan.validate_against(task, self._environment, self._registry)
        started = perf_counter()
        statuses = WorkflowState.initialize(plan).node_status.copy()
        nodes = {node.node_id: node for node in plan.nodes}
        agents = {agent.agent_id: agent for agent in plan.agents}
        predecessors = self._predecessors(plan)
        records: list[WorkflowNodeRecord] = []
        batch_index = 0
        failure: WorkflowFailure | None = None
        self._emit("workflow.execution.start", {"node_count": len(nodes)})

        while any(status != NodeStatus.DONE for status in statuses.values()):
            if failure is not None:
                break
            ready: list[str] = sorted(
                node_id
                for node_id, status in statuses.items()
                if status == NodeStatus.PENDING
                and all(statuses[item] == NodeStatus.DONE for item in predecessors[node_id])
            )
            for node_id in ready:
                statuses[node_id] = NodeStatus.READY
            ready = sorted(
                node_id for node_id, status in statuses.items() if status == NodeStatus.READY
            )
            if not ready:
                failure = WorkflowFailure(
                    code="workflow_stalled",
                    node_id=min(
                        node_id
                        for node_id, status in statuses.items()
                        if status != NodeStatus.DONE
                    ),
                    exception_type="RuntimeError",
                    message="workflow has unfinished nodes but no READY node",
                )
                break

            remaining: list[str] = ready
            while remaining and failure is None:
                infrastructure = await self._observer.observe()
                self._emit(
                    "infra.snapshot",
                    {
                        "scheduling_batch": batch_index,
                        "state": infrastructure.model_dump(mode="json"),
                    },
                )
                scheduled, scheduling_failure = self._schedule_batch(
                    remaining,
                    nodes,
                    agents,
                    infrastructure,
                )
                if scheduling_failure is not None:
                    failure = scheduling_failure
                    statuses[failure.node_id] = NodeStatus.FAILED
                    self._emit(
                        "workflow.node.failed",
                        {"failure": failure.model_dump(mode="json")},
                    )
                    break
                selected_ids = {item.node.node_id for item in scheduled}
                remaining = [node_id for node_id in remaining if node_id not in selected_ids]
                for item in scheduled:
                    statuses[item.node.node_id] = NodeStatus.RUNNING
                    self._emit(
                        "scheduler.decision",
                        item.decision.model_dump(mode="json"),
                    )
                    self._emit(
                        "workflow.node.start",
                        {
                            "node_id": item.node.node_id,
                            "scheduling_batch": batch_index,
                            "dag_predecessors": sorted(predecessors[item.node.node_id]),
                            "action": item.action.model_dump(mode="json"),
                        },
                    )

                completed = await asyncio.gather(
                    *(
                        self._execute_node(item, infrastructure, batch_index)
                        for item in scheduled
                    ),
                )
                after = await self._observer.observe()
                for record in sorted(completed, key=lambda item: item.node_id):
                    if record.failure is None and record.execution is not None:
                        try:
                            self._validate_outputs(
                                nodes[record.node_id],
                                record.execution,
                                after,
                            )
                        except Exception as exc:  # noqa: BLE001 - persisted typed boundary
                            record = record.model_copy(
                                update={"failure": self._failure(record.node_id, exc)}
                            )
                    records.append(record)
                    if record.failure is None:
                        statuses[record.node_id] = NodeStatus.DONE
                        if record.execution is None:
                            raise RuntimeError("successful node record has no execution")
                        for transfer in record.execution.transfers:
                            self._emit(
                                "artifact.transfer.end",
                                {
                                    "node_id": record.node_id,
                                    **transfer.model_dump(mode="json"),
                                },
                            )
                        self._emit(
                            "workflow.node.end",
                            record.model_dump(mode="json"),
                        )
                    else:
                        statuses[record.node_id] = NodeStatus.FAILED
                        self._emit(
                            "workflow.node.failed",
                            record.model_dump(mode="json"),
                        )
                        if failure is None:
                            failure = record.failure
                batch_index += 1

        state = WorkflowState(node_status=statuses).validate_against(plan)
        telemetry = self._telemetry(plan, records, (perf_counter() - started) * 1000)
        completed = failure is None and all(
            status == NodeStatus.DONE for status in statuses.values()
        )
        self._emit(
            "workflow.execution.end" if completed else "workflow.execution.failed",
            {
                "completed": completed,
                "state": state.model_dump(mode="json"),
                "failure": failure.model_dump(mode="json") if failure else None,
                "telemetry": telemetry.model_dump(mode="json"),
            },
        )
        return WorkflowExecutionResult(
            completed=completed,
            state=state,
            records=tuple(records),
            telemetry=telemetry,
            failure=failure,
        )

    def _schedule_batch(
        self,
        node_ids: list[str],
        nodes: dict[str, WorkflowNode],
        agents: dict[str, LogicalAgent],
        infrastructure: InfrastructureState,
    ) -> tuple[list[_ScheduledNode], WorkflowFailure | None]:
        scheduled: list[_ScheduledNode] = []
        occupied_agents: set[str] = set()
        for node_id in node_ids:
            node = nodes[node_id]
            try:
                decision = self._scheduler.schedule(
                    node,
                    agents[node.agent_id],
                    self._environment,
                    infrastructure,
                    self._registry,
                )
                action = JointAction(
                    semantic=node.semantic_action(),
                    physical=decision.physical,
                )
                operator = self._registry.binding(node.operator).spec
                binding = self._resolver.resolve(
                    decision.physical,
                    action.semantic,
                    operator,
                    self._environment,
                    infrastructure,
                )
                if len(binding.agent_ids) != 1:
                    raise SchedulingError("workflow nodes require exactly one physical agent")
                resolved_agent = binding.agent_ids[0]
            except Exception as exc:  # noqa: BLE001 - typed scheduling boundary
                return [], self._failure(node_id, exc)
            if resolved_agent in occupied_agents:
                continue
            occupied_agents.add(resolved_agent)
            scheduled.append(
                _ScheduledNode(
                    node=node,
                    decision=decision,
                    action=action,
                    resolved_agent_id=resolved_agent,
                )
            )
        if not scheduled:
            node_id = node_ids[0]
            return [], WorkflowFailure(
                code="scheduler_stalled",
                node_id=node_id,
                exception_type="SchedulingError",
                message="scheduler could not select a non-conflicting node",
            )
        return scheduled, None

    async def _execute_node(
        self,
        scheduled: _ScheduledNode,
        infrastructure: InfrastructureState,
        batch_index: int,
    ) -> WorkflowNodeRecord:
        started_at = datetime.now(UTC)
        started = perf_counter()
        try:
            execution = await self._executor.execute(scheduled.action, infrastructure)
            failure = None
        except Exception as exc:  # noqa: BLE001 - all remote failures must be persisted
            execution = None
            failure = self._failure(scheduled.node.node_id, exc)
        ended_at = datetime.now(UTC)
        return WorkflowNodeRecord(
            node_id=scheduled.node.node_id,
            scheduling_batch=batch_index,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=(perf_counter() - started) * 1000,
            scheduler_decision=scheduled.decision,
            action=scheduled.action,
            execution=execution,
            failure=failure,
        )

    @staticmethod
    def _validate_outputs(
        node: WorkflowNode,
        execution: ExecutionResult,
        infrastructure: InfrastructureState,
    ) -> None:
        produced: tuple[ProducedArtifact, ...]
        output = execution.output
        try:
            if "artifacts" in output:
                raw = output["artifacts"]
                if not isinstance(raw, list):
                    raise WorkflowOutputContractError("artifacts output must be a list")
                raw_artifacts = cast(list[object], raw)
                produced = tuple(
                    ProducedArtifact.model_validate(item) for item in raw_artifacts
                )
            elif "artifact_id" in output:
                produced = (ProducedArtifact.model_validate(output),)
            else:
                produced = ()
        except (ValidationError, TypeError, ValueError) as exc:
            raise WorkflowOutputContractError(
                f"node returned malformed artifact metadata: {node.node_id}"
            ) from exc

        actual_ids = tuple(item.artifact_id for item in produced)
        if set(actual_ids) != set(node.outputs) or len(actual_ids) != len(node.outputs):
            raise WorkflowOutputContractError(
                f"declared outputs differ from runtime outputs for {node.node_id}: "
                f"declared={list(node.outputs)}, actual={list(actual_ids)}"
            )
        observed = {item.artifact_id: item for item in infrastructure.artifacts}
        for item in produced:
            state = observed.get(item.artifact_id)
            if state is None:
                raise WorkflowOutputContractError(
                    f"produced artifact is absent after execution: {item.artifact_id}"
                )
            if (
                state.media_type != item.media_type
                or state.size_bytes != item.size_bytes
                or state.sha256_hex != item.sha256_hex
            ):
                raise WorkflowOutputContractError(
                    f"produced artifact metadata mismatch: {item.artifact_id}"
                )
            if not set(execution.agent_ids).intersection(state.locations):
                raise WorkflowOutputContractError(
                    f"produced artifact location mismatch: {item.artifact_id}"
                )

    @staticmethod
    def _predecessors(plan: WorkflowPlan) -> dict[str, set[str]]:
        values: dict[str, set[str]] = {
            node.node_id: set() for node in plan.nodes
        }
        for edge in plan.edges:
            values[edge.consumer_node].add(edge.producer_node)
        return values

    @classmethod
    def _telemetry(
        cls,
        plan: WorkflowPlan,
        records: list[WorkflowNodeRecord],
        e2e_latency_ms: float,
    ) -> WorkflowExecutionTelemetry:
        successful = [item for item in records if item.execution is not None]
        by_node = {item.node_id: item.duration_ms for item in successful}
        critical_path = cls._critical_path(plan, by_node)
        intervals = sorted(
            (item.started_at.timestamp() * 1000, item.ended_at.timestamp() * 1000)
            for item in records
        )
        union_ms = 0.0
        if intervals:
            start, end = intervals[0]
            for next_start, next_end in intervals[1:]:
                if next_start <= end:
                    end = max(end, next_end)
                else:
                    union_ms += end - start
                    start, end = next_start, next_end
            union_ms += end - start
        total_node_ms = sum(item.duration_ms for item in records)
        max_parallelism = cls._max_parallelism(intervals)
        executions = [item.execution for item in successful if item.execution is not None]
        transfers = [transfer for item in executions for transfer in item.transfers]
        return WorkflowExecutionTelemetry(
            e2e_latency_ms=e2e_latency_ms,
            critical_path_latency_ms=critical_path,
            parallel_overlap_ms=max(0.0, total_node_ms - union_ms),
            max_parallelism=max_parallelism,
            total_transfer_bytes=sum(item.bytes_transferred for item in transfers),
            total_transfer_duration_ms=sum(item.duration_ms for item in transfers),
            total_operator_latency_ms=sum(item.operator_latency_ms for item in executions),
            total_model_service_latency_ms=sum(
                item.model_telemetry.service_latency_ms
                for item in executions
                if item.model_telemetry is not None
            ),
        )

    @staticmethod
    def _critical_path(plan: WorkflowPlan, durations: dict[str, float]) -> float:
        predecessors = WorkflowOrchestrator._predecessors(plan)
        memo: dict[str, float] = {}

        def visit(node_id: str) -> float:
            if node_id in memo:
                return memo[node_id]
            prefix = max((visit(item) for item in predecessors[node_id]), default=0.0)
            memo[node_id] = prefix + durations.get(node_id, 0.0)
            return memo[node_id]

        return max((visit(node.node_id) for node in plan.nodes), default=0.0)

    @staticmethod
    def _max_parallelism(intervals: list[tuple[float, float]]) -> int:
        events = [
            event
            for started, ended in intervals
            for event in ((started, 1), (ended, -1))
        ]
        current = 0
        maximum = 0
        for _, delta in sorted(events, key=lambda item: (item[0], item[1])):
            current += delta
            maximum = max(maximum, current)
        return maximum

    @staticmethod
    def _failure(node_id: str, exc: Exception) -> WorkflowFailure:
        if isinstance(exc, (TypedExecutionError, BindingResolutionError)):
            code = exc.code.value
        elif isinstance(exc, SchedulingError):
            code = "scheduling_failed"
        elif isinstance(exc, WorkflowOutputContractError):
            code = "output_contract_mismatch"
        else:
            code = "node_execution_failed"
        return WorkflowFailure(
            code=code,
            node_id=node_id,
            exception_type=type(exc).__name__,
            message=str(exc) or type(exc).__name__,
        )

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        if self._trace is not None:
            self._trace.emit(event_type, payload)
