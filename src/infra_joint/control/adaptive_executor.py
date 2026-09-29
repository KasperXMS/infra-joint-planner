from __future__ import annotations

from typing import Any

from pydantic import Field

from infra_joint.agents.context import AgentTaskView
from infra_joint.control.adaptation import (
    PatchWorkflow,
    WorkflowAdaptationContext,
    WorkflowAdaptationPolicy,
    WorkflowAdaptationTelemetry,
)
from infra_joint.control.contracts import (
    LogicalAction,
    LogicalObservation,
    StaticCapabilityContract,
    WorkflowGraphSnapshot,
)
from infra_joint.control.gateway import ActionGateway
from infra_joint.control.graph import ExecutionGrownGraph
from infra_joint.control.output_validation import (
    TerminalOutputValidation,
    validate_terminal_output,
)
from infra_joint.control.workflow import (
    SemanticWorkflowPlan,
    SemanticWorkflowVersion,
    WorkflowPatchRecord,
    WorkflowRuntimeState,
)
from infra_joint.control.workflow_profile import WorkflowProfileProvider
from infra_joint.control.workflow_validation import (
    apply_workflow_patch,
    predecessor_ids,
    ready_frontier,
    validate_semantic_workflow,
)
from infra_joint.core.base import ContractModel
from infra_joint.core.task import TaskContract
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.workflow.trace import WorkflowTraceRecorder


class AdaptiveExecutionFailure(ContractModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    action_id: str | None = None


class AdaptiveWorkflowExecution(ContractModel):
    workflow_id: str = Field(min_length=1)
    versions: tuple[SemanticWorkflowVersion, ...]
    patch_records: tuple[WorkflowPatchRecord, ...]
    final_plan: SemanticWorkflowPlan
    final_state: WorkflowRuntimeState
    observations: tuple[LogicalObservation, ...]
    execution_graph: tuple[WorkflowGraphSnapshot, ...]
    adaptation_telemetry: tuple[WorkflowAdaptationTelemetry, ...] = ()
    final_answer: str | None = None
    terminal_output_contract: TerminalOutputValidation | None = None
    failure: AdaptiveExecutionFailure | None = None

    @property
    def succeeded(self) -> bool:
        return self.failure is None and self.final_answer is not None


class AdaptiveWorkflowExecutor:
    """Execute and revise a semantic workflow at every newly-ready frontier."""

    def __init__(
        self,
        gateway: ActionGateway,
        profile_provider: WorkflowProfileProvider,
        adapter: WorkflowAdaptationPolicy,
        registry: OperatorRegistry,
        capabilities: StaticCapabilityContract,
        *,
        max_frontiers: int = 128,
    ) -> None:
        if max_frontiers < 1:
            raise ValueError("max_frontiers must be positive")
        self._gateway = gateway
        self._profiles = profile_provider
        self._adapter = adapter
        self._registry = registry
        self._capabilities = capabilities
        self._max_frontiers = max_frontiers

    async def execute(
        self,
        task: TaskContract,
        prior: SemanticWorkflowPlan,
        trace: WorkflowTraceRecorder,
    ) -> AdaptiveWorkflowExecution:
        validate_semantic_workflow(prior, task, self._capabilities, self._registry)
        plan = prior
        state = WorkflowRuntimeState.initialize(plan)
        versions = [SemanticWorkflowVersion.create(plan)]
        records: list[WorkflowPatchRecord] = []
        graph = ExecutionGrownGraph()
        observations: list[LogicalObservation] = []
        adaptation_telemetry: list[WorkflowAdaptationTelemetry] = []
        trace.emit("workflow.plan.version", self._version_payload(versions[-1]))

        for _ in range(self._max_frontiers):
            profile = await self._profiles.build(plan, state)
            adaptation = await self._adapter.adapt(
                WorkflowAdaptationContext(
                    task=AgentTaskView.from_contract(task),
                    plan=plan,
                    runtime=state,
                    observations=tuple(observations),
                    static_capabilities=self._capabilities,
                    physical=profile,
                )
            )
            decision = adaptation.decision
            adaptation_telemetry.append(adaptation.telemetry)
            trace.emit(
                "workflow.adaptation",
                adaptation.telemetry.model_dump(mode="json"),
            )
            if isinstance(decision, PatchWorkflow):
                revised = apply_workflow_patch(
                    plan,
                    state,
                    decision.patch,
                    task,
                    self._capabilities,
                    self._registry,
                )
                record = WorkflowPatchRecord(
                    from_version=plan.version,
                    to_version=revised.version,
                    decision="patch",
                    reason=decision.reason,
                    patch=decision.patch,
                )
                plan = revised
                state = state.model_copy(
                    update={
                        "pending_action_ids": tuple(
                            action.action_id
                            for action in plan.actions
                            if action.action_id
                            not in set(state.completed_action_ids) | set(state.running_action_ids)
                        )
                    }
                )
                version = SemanticWorkflowVersion.create(plan)
                versions.append(version)
                trace.emit("workflow.plan.patch", record.model_dump(mode="json"))
                trace.emit("workflow.plan.version", self._version_payload(version))
            else:
                record = WorkflowPatchRecord(
                    from_version=plan.version,
                    to_version=plan.version,
                    decision="keep",
                    reason=decision.reason,
                )
                trace.emit("workflow.plan.patch", record.model_dump(mode="json"))
            records.append(record)

            frontier = ready_frontier(plan, state)
            if not frontier:
                return self._result(
                    plan,
                    state,
                    versions,
                    records,
                    observations,
                    graph,
                    adaptation_telemetry,
                    failure=AdaptiveExecutionFailure(
                        code="workflow_stalled",
                        message="pending workflow has no newly-ready frontier",
                    ),
                )
            dispatched = tuple(self._with_dependencies(plan, action) for action in frontier)
            self._gateway.validate_batch(dispatched)
            self._snapshot(trace, graph.add(dispatched))
            running_ids = tuple(item.action_id for item in dispatched)
            state = state.model_copy(
                update={
                    "running_action_ids": running_ids,
                    "pending_action_ids": tuple(
                        item for item in state.pending_action_ids if item not in running_ids
                    ),
                }
            )
            self._snapshot(trace, graph.mark_running(running_ids))
            outcomes = await self._gateway.execute_batch(dispatched, expose_profile=False)
            succeeded = tuple(
                item.observation.action_id for item in outcomes if item.observation.succeeded
            )
            failed = tuple(
                item.observation.action_id for item in outcomes if not item.observation.succeeded
            )
            batch_observations = tuple(item.observation for item in outcomes)
            observations.extend(batch_observations)
            state = state.model_copy(
                update={
                    "completed_action_ids": state.completed_action_ids + running_ids,
                    "running_action_ids": (),
                    "observations": tuple(observations),
                }
            )
            self._snapshot(trace, graph.mark_finished(succeeded, failed))
            for outcome in outcomes:
                trace.emit(
                    "physical.execution",
                    outcome.model_dump(mode="json"),
                )
            if failed:
                failed_observation = next(item for item in batch_observations if not item.succeeded)
                return self._result(
                    plan,
                    state,
                    versions,
                    records,
                    observations,
                    graph,
                    adaptation_telemetry,
                    failure=AdaptiveExecutionFailure(
                        code=failed_observation.failure_code or "physical_execution_failed",
                        message=failed_observation.failure_message or "physical action failed",
                        action_id=failed_observation.action_id,
                    ),
                )
            if plan.terminal_action_id in succeeded:
                terminal = next(
                    item for item in batch_observations if item.action_id == plan.terminal_action_id
                )
                answer = terminal.output.get("text")
                if not isinstance(answer, str) or not answer.strip():
                    return self._result(
                        plan,
                        state,
                        versions,
                        records,
                        observations,
                        graph,
                        adaptation_telemetry,
                        failure=AdaptiveExecutionFailure(
                            code="terminal_output_invalid",
                            message="terminal model action returned no non-empty inline text",
                            action_id=terminal.action_id,
                        ),
                    )
                return self._result(
                    plan,
                    state,
                    versions,
                    records,
                    observations,
                    graph,
                    adaptation_telemetry,
                    final_answer=answer,
                    terminal_output_contract=validate_terminal_output(
                        answer,
                        task.output_contract,
                    ),
                )
        return self._result(
            plan,
            state,
            versions,
            records,
            observations,
            graph,
            adaptation_telemetry,
            failure=AdaptiveExecutionFailure(
                code="frontier_budget_exhausted",
                message="adaptive workflow exceeded the configured frontier budget",
            ),
        )

    @staticmethod
    def _with_dependencies(
        plan: SemanticWorkflowPlan,
        action: LogicalAction,
    ) -> LogicalAction:
        return action.model_copy(update={"depends_on": predecessor_ids(plan, action.action_id)})

    @staticmethod
    def _version_payload(version: SemanticWorkflowVersion) -> dict[str, Any]:
        return version.model_dump(mode="json")

    @staticmethod
    def _snapshot(
        trace: WorkflowTraceRecorder,
        snapshot: WorkflowGraphSnapshot,
    ) -> None:
        trace.emit("workflow.execution.snapshot", snapshot.model_dump(mode="json"))

    @staticmethod
    def _result(
        plan: SemanticWorkflowPlan,
        state: WorkflowRuntimeState,
        versions: list[SemanticWorkflowVersion],
        records: list[WorkflowPatchRecord],
        observations: list[LogicalObservation],
        graph: ExecutionGrownGraph,
        adaptation_telemetry: list[WorkflowAdaptationTelemetry],
        *,
        final_answer: str | None = None,
        terminal_output_contract: TerminalOutputValidation | None = None,
        failure: AdaptiveExecutionFailure | None = None,
    ) -> AdaptiveWorkflowExecution:
        return AdaptiveWorkflowExecution(
            workflow_id=plan.workflow_id,
            versions=tuple(versions),
            patch_records=tuple(records),
            final_plan=plan,
            final_state=state,
            observations=tuple(observations),
            execution_graph=graph.snapshots,
            adaptation_telemetry=tuple(adaptation_telemetry),
            final_answer=final_answer,
            terminal_output_contract=terminal_output_contract,
            failure=failure,
        )
