from __future__ import annotations

import hashlib
import json
from collections import deque
from collections.abc import Callable, Iterable
from enum import StrEnum
from typing import Annotated, Any, Literal, Protocol

from pydantic import Field, TypeAdapter, ValidationError

from infra_joint.core.base import ContractModel
from infra_joint.core.state import EnvironmentSpec, InfrastructureState
from infra_joint.core.task import TaskContract
from infra_joint.core.workflow import (
    NodeStatus,
    WorkflowEdge,
    WorkflowPlan,
    feasible_operations_for_model_instance,
)
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.planning.planner import CompletionBackend, logical_task_payload
from infra_joint.worker.model_backend import ModelCallTelemetry, ModelRequest
from infra_joint.workflow.orchestrator import (
    WorkflowExecutionResult,
    WorkflowOrchestrator,
)
from infra_joint.workflow.planner import LLMWorkflowPlanner
from infra_joint.workflow.trace import WorkflowTraceRecorder
from infra_joint.workflow.workload import WorkloadSpec


class ReplanTrigger(StrEnum):
    EVIDENCE_INSUFFICIENT = "evidence_insufficient"
    EVIDENCE_CONFLICT_OR_INCOMPLETE = "evidence_conflict_or_incomplete"
    FUTURE_PATH_FEEDBACK = "future_path_feedback"


class SemanticNodeObservation(ContractModel):
    """Completed-node output with all physical execution fields removed."""

    node_id: str = Field(min_length=1)
    operator: str = Field(min_length=1)
    output: dict[str, Any]


class FuturePathFeedback(ContractModel):
    """Explicit feedback supplied to a replanner for still-pending work.

    Resource-blind callers leave this empty. An infrastructure-aware experiment may
    populate it later without changing the semantic observation contract.
    """

    feedback_type: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    affected_node_ids: tuple[str, ...] = ()


class TransferCostEstimate(ContractModel):
    node_id: str = Field(min_length=1)
    target_agent_id: str = Field(min_length=1)
    artifact_ids: tuple[str, ...]
    transfer_bytes: int = Field(ge=0)
    estimated_latency_ms: float | None = Field(default=None, ge=0)
    basis: str = Field(min_length=1)


class ExecutionCostProfile(ContractModel):
    operator: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    deployment_id: str | None = None
    input_units: int | None = Field(default=None, ge=0)
    output_units: int | None = Field(default=None, ge=0)
    service_latency_ms: float = Field(ge=0)
    source: str = Field(min_length=1)


class InfrastructureReplanView(ContractModel):
    """Explicit physical state visible only to the infra-aware replanner arm."""

    environment: EnvironmentSpec
    state: InfrastructureState
    relevant_artifact_ids: tuple[str, ...]
    pending_transfer_estimates: tuple[TransferCostEstimate, ...] = ()
    execution_cost_profiles: tuple[ExecutionCostProfile, ...] = ()


class InfrastructureReplanViewProvider(Protocol):
    async def observe(
        self,
        context: WorkflowReplanContext,
    ) -> InfrastructureReplanView: ...


class WorkflowReplanContext(ContractModel):
    revision_index: int = Field(ge=0)
    current_plan: WorkflowPlan
    completed_node_ids: tuple[str, ...]
    pending_node_ids: tuple[str, ...]
    semantic_observations: tuple[SemanticNodeObservation, ...]
    future_path_feedback: tuple[FuturePathFeedback, ...] = ()

    @classmethod
    def from_execution(
        cls,
        revision_index: int,
        plan: WorkflowPlan,
        execution: WorkflowExecutionResult,
        *,
        future_path_feedback: tuple[FuturePathFeedback, ...] = (),
    ) -> WorkflowReplanContext:
        completed = tuple(
            sorted(
                node_id
                for node_id, status in execution.state.node_status.items()
                if status == NodeStatus.DONE
            )
        )
        pending = tuple(sorted(set(execution.state.node_status) - set(completed)))
        observations = tuple(
            SemanticNodeObservation(
                node_id=record.node_id,
                operator=record.action.semantic.operator,
                output=record.execution.output,
            )
            for record in execution.records
            if record.failure is None and record.execution is not None
        )
        return cls(
            revision_index=revision_index,
            current_plan=plan,
            completed_node_ids=completed,
            pending_node_ids=pending,
            semantic_observations=observations,
            future_path_feedback=future_path_feedback,
        )


class KeepWorkflowProposal(ContractModel):
    decision: Literal["keep"] = "keep"
    reason: str = Field(min_length=1)


class ReviseWorkflowProposal(ContractModel):
    decision: Literal["revise"] = "revise"
    trigger: ReplanTrigger
    reason: str = Field(min_length=1)
    plan: WorkflowPlan


WorkflowReplanProposal = Annotated[
    KeepWorkflowProposal | ReviseWorkflowProposal,
    Field(discriminator="decision"),
]
WORKFLOW_REPLAN_ADAPTER: TypeAdapter[WorkflowReplanProposal] = TypeAdapter(
    WorkflowReplanProposal
)


class WorkflowReplanOutcome(ContractModel):
    proposal: KeepWorkflowProposal | ReviseWorkflowProposal
    model_telemetry: ModelCallTelemetry | None = None


class WorkflowReplanningError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        execution: WorkflowExecutionResult | None = None,
        versions: tuple[WorkflowVersion, ...] = (),
        revisions: tuple[WorkflowRevisionRecord, ...] = (),
        current_plan: WorkflowPlan | None = None,
    ) -> None:
        super().__init__(message)
        self.execution = execution
        self.versions = versions
        self.revisions = revisions
        self.current_plan = current_plan


class WorkflowReplanner(Protocol):
    async def replan(
        self,
        task: TaskContract,
        workload: WorkloadSpec,
        context: WorkflowReplanContext,
    ) -> WorkflowReplanOutcome: ...


class ScriptedWorkflowReplanner:
    def __init__(self, proposals: Iterable[WorkflowReplanProposal]) -> None:
        self._proposals = deque(proposals)

    async def replan(
        self,
        task: TaskContract,
        workload: WorkloadSpec,
        context: WorkflowReplanContext,
    ) -> WorkflowReplanOutcome:
        del task, workload, context
        if not self._proposals:
            raise RuntimeError("scripted workflow replanner has no proposal remaining")
        return WorkflowReplanOutcome(proposal=self._proposals.popleft())


def validate_workflow_revision(
    current: WorkflowPlan,
    proposed: WorkflowPlan,
    completed_node_ids: Iterable[str],
) -> None:
    """Fail closed if a revision changes any already-executed semantics."""

    completed = frozenset(completed_node_ids)
    current_nodes = {node.node_id: node for node in current.nodes}
    proposed_nodes = {node.node_id: node for node in proposed.nodes}
    unknown = sorted(completed - set(current_nodes))
    if unknown:
        raise ValueError(f"completed nodes are absent from current plan: {unknown}")
    removed = sorted(completed - set(proposed_nodes))
    if removed:
        raise ValueError(f"revision removed completed nodes: {removed}")
    modified = sorted(
        node_id
        for node_id in completed
        if current_nodes[node_id] != proposed_nodes[node_id]
    )
    if modified:
        raise ValueError(f"revision modified completed nodes: {modified}")

    current_agents = {agent.agent_id: agent for agent in current.agents}
    proposed_agents = {agent.agent_id: agent for agent in proposed.agents}
    completed_agents = {current_nodes[node_id].agent_id for node_id in completed}
    changed_agents = sorted(
        agent_id
        for agent_id in completed_agents
        if proposed_agents.get(agent_id) != current_agents[agent_id]
    )
    if changed_agents:
        raise ValueError(
            f"revision changed agents that own completed nodes: {changed_agents}"
        )

    def incoming_completed_edges(plan: WorkflowPlan) -> frozenset[WorkflowEdge]:
        return frozenset(
            edge for edge in plan.edges if edge.consumer_node in completed
        )

    if incoming_completed_edges(current) != incoming_completed_edges(proposed):
        raise ValueError("revision changed dependencies of completed nodes")


def _canonical_plan_hash(plan: WorkflowPlan) -> str:
    payload = json.dumps(
        plan.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class WorkflowVersion(ContractModel):
    revision_index: int = Field(ge=0)
    canonical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    plan: WorkflowPlan

    @classmethod
    def create(cls, revision_index: int, plan: WorkflowPlan) -> WorkflowVersion:
        return cls(
            revision_index=revision_index,
            canonical_sha256=_canonical_plan_hash(plan),
            plan=plan,
        )


class WorkflowChangeSet(ContractModel):
    added_agents: tuple[str, ...]
    removed_agents: tuple[str, ...]
    modified_agents: tuple[str, ...]
    added_nodes: tuple[str, ...]
    removed_nodes: tuple[str, ...]
    modified_nodes: tuple[str, ...]
    added_edges: tuple[WorkflowEdge, ...]
    removed_edges: tuple[WorkflowEdge, ...]

    @classmethod
    def between(cls, current: WorkflowPlan, proposed: WorkflowPlan) -> WorkflowChangeSet:
        current_agents = {agent.agent_id: agent for agent in current.agents}
        proposed_agents = {agent.agent_id: agent for agent in proposed.agents}
        current_nodes = {node.node_id: node for node in current.nodes}
        proposed_nodes = {node.node_id: node for node in proposed.nodes}
        current_edges = frozenset(current.edges)
        proposed_edges = frozenset(proposed.edges)
        return cls(
            added_agents=tuple(sorted(set(proposed_agents) - set(current_agents))),
            removed_agents=tuple(sorted(set(current_agents) - set(proposed_agents))),
            modified_agents=tuple(
                sorted(
                    agent_id
                    for agent_id in set(current_agents).intersection(proposed_agents)
                    if current_agents[agent_id] != proposed_agents[agent_id]
                )
            ),
            added_nodes=tuple(sorted(set(proposed_nodes) - set(current_nodes))),
            removed_nodes=tuple(sorted(set(current_nodes) - set(proposed_nodes))),
            modified_nodes=tuple(
                sorted(
                    node_id
                    for node_id in set(current_nodes).intersection(proposed_nodes)
                    if current_nodes[node_id] != proposed_nodes[node_id]
                )
            ),
            added_edges=tuple(
                sorted(
                    proposed_edges - current_edges,
                    key=lambda edge: (
                        edge.producer_node,
                        edge.consumer_node,
                        edge.artifact_id,
                    ),
                )
            ),
            removed_edges=tuple(
                sorted(
                    current_edges - proposed_edges,
                    key=lambda edge: (
                        edge.producer_node,
                        edge.consumer_node,
                        edge.artifact_id,
                    ),
                )
            ),
        )

    def is_empty(self) -> bool:
        return not any(
            (
                self.added_agents,
                self.removed_agents,
                self.modified_agents,
                self.added_nodes,
                self.removed_nodes,
                self.modified_nodes,
                self.added_edges,
                self.removed_edges,
            )
        )


class WorkflowRevisionRecord(ContractModel):
    from_revision: int = Field(ge=0)
    to_revision: int = Field(ge=0)
    decision: Literal["keep", "revise"]
    trigger: ReplanTrigger | None = None
    reason: str = Field(min_length=1)
    changes: WorkflowChangeSet | None = None
    planner_telemetry: ModelCallTelemetry | None = None


class ReplanningWorkflowExecution(ContractModel):
    versions: tuple[WorkflowVersion, ...]
    revisions: tuple[WorkflowRevisionRecord, ...]
    final_plan: WorkflowPlan
    workflow: WorkflowExecutionResult


class LLMWorkflowReplanner:
    """Semantic workflow reviser with the same fixed action/model contracts as G0."""

    def __init__(
        self,
        backend: CompletionBackend,
        registry: OperatorRegistry,
        environment: EnvironmentSpec,
    ) -> None:
        self._backend = backend
        self._registry = registry
        self._environment = environment

    async def replan(
        self,
        task: TaskContract,
        workload: WorkloadSpec,
        context: WorkflowReplanContext,
    ) -> WorkflowReplanOutcome:
        return await self._invoke_and_validate(
            task,
            workload,
            context,
            self.render_prompt(task, workload, context),
        )

    async def _invoke_and_validate(
        self,
        task: TaskContract,
        workload: WorkloadSpec,
        context: WorkflowReplanContext,
        prompt: str,
    ) -> WorkflowReplanOutcome:
        completion = await self._backend.invoke(ModelRequest(prompt=prompt))
        try:
            proposal = WORKFLOW_REPLAN_ADAPTER.validate_python(json.loads(completion.text))
            if isinstance(proposal, ReviseWorkflowProposal):
                validate_workflow_revision(
                    context.current_plan,
                    proposal.plan,
                    context.completed_node_ids,
                )
                self._validate_plan(proposal.plan, task, workload)
                changes = WorkflowChangeSet.between(context.current_plan, proposal.plan)
                if changes.is_empty():
                    raise ValueError("revise proposal must change the pending workflow")
        except (json.JSONDecodeError, ValidationError, KeyError, ValueError) as exc:
            raise WorkflowReplanningError(
                "workflow replanner must return one valid keep/revise JSON object: "
                f"{exc}"
            ) from exc
        return WorkflowReplanOutcome(
            proposal=proposal,
            model_telemetry=completion.telemetry,
        )

    def _validate_plan(
        self,
        plan: WorkflowPlan,
        task: TaskContract,
        workload: WorkloadSpec,
    ) -> None:
        plan.validate_against(
            task,
            self._environment,
            self._registry,
            workload.available_operations,
        )
        plan.terminal_model_node()
        available = {
            instance.model_instance_id for instance in workload.available_model_instances
        }
        if any(agent.model_instance_id not in available for agent in plan.agents):
            raise ValueError("revised workflow uses an unavailable model instance")
        if workload.min_agents is not None and len(plan.agents) < workload.min_agents:
            raise ValueError("revised workflow has fewer agents than workload minimum")
        if workload.max_agents is not None and len(plan.agents) > workload.max_agents:
            raise ValueError("revised workflow has more agents than workload maximum")

    def render_prompt(
        self,
        task: TaskContract,
        workload: WorkloadSpec,
        context: WorkflowReplanContext,
    ) -> str:
        return self._render_prompt(task, workload, context, infrastructure=None)

    def _render_prompt(
        self,
        task: TaskContract,
        workload: WorkloadSpec,
        context: WorkflowReplanContext,
        *,
        infrastructure: InfrastructureReplanView | None,
    ) -> str:
        available = set(workload.available_operations)
        tools = [
            tool
            for tool in self._registry.planner_tools()
            if tool["function"]["name"] in available
        ]
        workload_payload = workload.model_dump(mode="json")
        for instance in workload_payload["available_model_instances"]:
            instance["modalities"] = sorted(instance["modalities"])
        payload = {
            "task": logical_task_payload(task),
            "workload": workload_payload,
            "system_feasible_operations_by_model_instance": {
                instance.model_instance_id: sorted(
                    feasible_operations_for_model_instance(
                        instance.model_instance_id,
                        self._environment,
                        self._registry,
                        workload.available_operations,
                    )
                )
                for instance in workload.available_model_instances
            },
            "available_operator_schemas": tools,
            "system_context_preflight_guidance": (
                LLMWorkflowPlanner.context_preflight_guidance(task, workload)
            ),
            "execution_observation": context.model_dump(mode="json"),
        }
        if infrastructure is not None:
            payload["infrastructure_state"] = infrastructure.model_dump(mode="json")
        revision_scope = (
            "Revise only for evidence_insufficient, evidence_conflict_or_incomplete, or "
            "explicit future_path_feedback present in the input."
            if infrastructure is None
            else (
                "Revise only for evidence_insufficient, evidence_conflict_or_incomplete, "
                "or when the explicit infrastructure snapshot makes a different pending "
                "workflow materially cheaper while preserving evidence coverage and answer "
                "quality. Use future_path_feedback as the trigger for an infrastructure-only "
                "revision."
            )
        )
        visibility = (
            "The input contains no physical placement, bandwidth, RTT, load, queue, gold, "
            "supporting evidence, source_ref, or evaluator metadata. Do not infer or request "
            "those fields."
            if infrastructure is None
            else (
                "The infrastructure_state object is authoritative for current artifact "
                "locations, bandwidth/RTT, worker load, transfer estimates, and measured "
                "execution-cost profiles. It contains no gold, supporting evidence, "
                "source_ref, or evaluator metadata. Preserve semantic correctness; never trade "
                "away required evidence merely to reduce cost."
            )
        )
        return "\n".join(
            (
                "Decide whether the unexecuted part of the workflow needs one semantic revision.",
                "Return keep when the completed evidence is sufficient and consistent for the "
                "pending terminal path. Do not make cosmetic or speculative changes.",
                revision_scope,
                "A revision is a complete next WorkflowPlan. Every completed node and its owning "
                "agent must remain exactly unchanged. Completed artifacts remain available. Only "
                "pending nodes, future dependencies, and new retrieval/reasoning branches may "
                "change. Never retry or replay a completed node.",
                "The completed_node_ids list is an immutable prefix contract. Copy those node "
                "objects byte-for-byte in the next plan and do not add, remove, or redirect any "
                "edge whose consumer is completed. If an existing completed evidence note is "
                "insufficient, do not attach new inputs to it: add a new retrieval node and a new "
                "reasoning node with fresh IDs, then modify only a pending downstream node to "
                "consume the new artifact alongside the preserved completed artifact.",
                "Use only the fixed operator vocabulary and model instances in the input. Do not "
                "invent operators, silently summarize/truncate, substitute models, or use "
                "task-specific rules.",
                "Every new invoke_model node must satisfy the same conservative context bound "
                "as G0. Use system_context_preflight_guidance for multi-shard BM25 fan-in. A "
                "zero equal top-k cap means that direct fan-in is illegal; use separately "
                "bounded new reasoning nodes. Validation will reject an oversized revision "
                "before execution and will not lower top_k or repair the graph.",
                "Collection metadata is authoritative: non_semantic partitions do not divide the "
                "corpus by topic, and union_is_complete means all listed partitions together form "
                "the complete collection. Use this only for semantic coverage reasoning.",
                visibility,
                "Keep form: {\"decision\":\"keep\",\"reason\":\"...\"}.",
                "Revise form: {\"decision\":\"revise\",\"trigger\":"
                "\"evidence_insufficient|evidence_conflict_or_incomplete|future_path_feedback\","
                "\"reason\":\"...\",\"plan\":{\"agents\":[],\"nodes\":[],\"edges\":[]}}.",
                "Return exactly one JSON object with no Markdown or surrounding text.",
                "Replanning input:",
                json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
            )
        )


class LLMInfrastructureAwareWorkflowReplanner(LLMWorkflowReplanner):
    """The same workflow reviser with one explicit, current infrastructure view."""

    def __init__(
        self,
        backend: CompletionBackend,
        registry: OperatorRegistry,
        environment: EnvironmentSpec,
        view_provider: InfrastructureReplanViewProvider,
    ) -> None:
        super().__init__(backend, registry, environment)
        self._view_provider = view_provider
        self.observed_views: list[InfrastructureReplanView] = []

    async def replan(
        self,
        task: TaskContract,
        workload: WorkloadSpec,
        context: WorkflowReplanContext,
    ) -> WorkflowReplanOutcome:
        view = await self._view_provider.observe(context)
        self.observed_views.append(view)
        prompt = self._render_prompt(
            task,
            workload,
            context,
            infrastructure=view,
        )
        return await self._invoke_and_validate(task, workload, context, prompt)


FeedbackProvider = Callable[
    [WorkflowPlan, WorkflowExecutionResult], tuple[FuturePathFeedback, ...]
]


class ReplanningWorkflowExecutor:
    """Minimal plan-execute-observe-revise loop with bounded revision count."""

    def __init__(
        self,
        orchestrator: WorkflowOrchestrator,
        replanner: WorkflowReplanner,
        *,
        max_replans: int = 1,
        feedback_provider: FeedbackProvider | None = None,
        pause_before_operators: Iterable[str] = (),
        trace: WorkflowTraceRecorder | None = None,
    ) -> None:
        if max_replans < 1:
            raise ValueError("max_replans must be at least one")
        self._orchestrator = orchestrator
        self._replanner = replanner
        self._max_replans = max_replans
        self._feedback_provider = feedback_provider
        self._pause_before_operators = tuple(pause_before_operators)
        self._trace = trace

    async def execute(
        self,
        task: TaskContract,
        workload: WorkloadSpec,
        initial_plan: WorkflowPlan,
    ) -> ReplanningWorkflowExecution:
        current = initial_plan
        versions = [WorkflowVersion.create(0, current)]
        revisions: list[WorkflowRevisionRecord] = []
        prior: WorkflowExecutionResult | None = None

        for revision_index in range(self._max_replans):
            stage = await self._orchestrator.execute_revision(
                task,
                current,
                prior=prior,
                pause_before_terminal=True,
                pause_before_operators=self._pause_before_operators,
            )
            if stage.failure is not None:
                return ReplanningWorkflowExecution(
                    versions=tuple(versions),
                    revisions=tuple(revisions),
                    final_plan=current,
                    workflow=stage,
                )
            feedback = (
                self._feedback_provider(current, stage)
                if self._feedback_provider is not None
                else ()
            )
            context = WorkflowReplanContext.from_execution(
                revision_index,
                current,
                stage,
                future_path_feedback=feedback,
            )
            self._emit(
                "workflow.replanner.start",
                {"revision_index": revision_index, "context": context.model_dump(mode="json")},
            )
            try:
                outcome = await self._replanner.replan(task, workload, context)
            except WorkflowReplanningError as exc:
                raise WorkflowReplanningError(
                    str(exc),
                    execution=stage,
                    versions=tuple(versions),
                    revisions=tuple(revisions),
                    current_plan=current,
                ) from exc
            proposal = outcome.proposal
            if isinstance(proposal, KeepWorkflowProposal):
                record = WorkflowRevisionRecord(
                    from_revision=revision_index,
                    to_revision=revision_index,
                    decision="keep",
                    reason=proposal.reason,
                    planner_telemetry=outcome.model_telemetry,
                )
                revisions.append(record)
                self._emit("workflow.replanner.end", record.model_dump(mode="json"))
                prior = stage
                break

            try:
                validate_workflow_revision(
                    current, proposal.plan, context.completed_node_ids
                )
            except ValueError as exc:
                raise WorkflowReplanningError(
                    str(exc),
                    execution=stage,
                    versions=tuple(versions),
                    revisions=tuple(revisions),
                    current_plan=current,
                ) from exc
            changes = WorkflowChangeSet.between(current, proposal.plan)
            if changes.is_empty():
                raise WorkflowReplanningError(
                    "revise proposal must change the pending workflow"
                )
            next_revision = revision_index + 1
            record = WorkflowRevisionRecord(
                from_revision=revision_index,
                to_revision=next_revision,
                decision="revise",
                trigger=proposal.trigger,
                reason=proposal.reason,
                changes=changes,
                planner_telemetry=outcome.model_telemetry,
            )
            revisions.append(record)
            current = proposal.plan
            versions.append(WorkflowVersion.create(next_revision, current))
            self._emit("workflow.replanner.end", record.model_dump(mode="json"))
            prior = stage

        if prior is None:
            raise RuntimeError("replanning loop produced no execution stage")
        final = await self._orchestrator.execute_revision(task, current, prior=prior)
        return ReplanningWorkflowExecution(
            versions=tuple(versions),
            revisions=tuple(revisions),
            final_plan=current,
            workflow=final,
        )

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        if self._trace is not None:
            self._trace.emit(event_type, payload)
