from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from statistics import median

from pydantic import Field

from infra_joint.core.base import ContractModel
from infra_joint.evaluation.trace import TraceEvent
from infra_joint.heterogeneous.calibration import summarize
from infra_joint.heterogeneous.contracts import DistributionSummary, ExperimentMetadata
from infra_joint.heterogeneous.scheduler import SynthesisStageEstimate
from infra_joint.workflow.runner import PersistedWorkflowRunResult

STAGE_NODE_IDS = (
    "placement-group-bm25-reduce",
    "placement-group-project-context",
    "same-model-synthesis",
)


def validate_trace_reconstruction(path: Path, run_id: str) -> int:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"trace is empty: {run_id}")
    events = [TraceEvent.model_validate_json(line) for line in lines]
    previous: str | None = None
    step_ids: set[str] = set()
    for event in events:
        if event.run_id != run_id:
            raise ValueError(f"trace run ID mismatch: {run_id}")
        if event.step_id in step_ids:
            raise ValueError(f"trace step ID is duplicated: {event.step_id}")
        if event.parent_id != previous:
            raise ValueError(f"trace parent chain is broken: {event.step_id}")
        step_ids.add(event.step_id)
        previous = event.step_id
    if events[-1].event_type not in {"run.end", "run.failed"}:
        raise ValueError(f"trace lacks a terminal run event: {run_id}")
    required = {"task.start", "workflow.planner.end", "infra.snapshot"}
    observed = {item.event_type for item in events}
    if required - observed:
        raise ValueError(f"trace lacks required reconstruction events: {run_id}")
    return len(events)


class PlacementRunObservation(ContractModel):
    run_id: str = Field(min_length=1)
    payload_class: str = Field(min_length=1)
    placement_policy: str = Field(min_length=1)
    network_calibration_id: str = Field(min_length=1)
    selected_agent_id: str = Field(min_length=1)
    stage_cost_ms: float = Field(ge=0)
    stage_compute_ms: float = Field(ge=0)
    stage_transfer_bytes: int = Field(ge=0)
    stage_transfer_ms: float = Field(ge=0)
    model_service_ms: float = Field(ge=0)
    model_input_tokens: int | None = Field(default=None, ge=0)
    model_output_tokens: int | None = Field(default=None, ge=0)
    model_finish_reason: str | None = None
    workflow_e2e_ms: float = Field(ge=0)
    critical_path_ms: float = Field(ge=0)
    scheduler_overhead_ms: float = Field(ge=0)
    benchmark_score: float = Field(ge=0, le=1)
    format_valid: bool


class OracleCellSummary(ContractModel):
    payload_class: str
    network_calibration_id: str
    a28_cost_ms: DistributionSummary
    rtx_cost_ms: DistributionSummary
    oracle_agent_id: str


class SchedulerRegretObservation(ContractModel):
    run_id: str
    payload_class: str
    placement_policy: str
    network_calibration_id: str
    selected_agent_id: str
    oracle_agent_id: str
    selected_empirical_cost_ms: float = Field(ge=0)
    oracle_empirical_cost_ms: float = Field(ge=0)
    routing_regret_ms: float = Field(ge=0)
    oracle_selected: bool


def observe_run(
    result: PersistedWorkflowRunResult,
    metadata: ExperimentMetadata,
    *,
    scheduler_overhead_ms: float,
) -> PlacementRunObservation:
    if not result.execution_completed or result.workflow is None or result.evaluation is None:
        raise ValueError(f"only valid completed runs can be observed: {result.run_id}")
    by_node = {item.node_id: item for item in result.workflow.records}
    if set(STAGE_NODE_IDS) - set(by_node):
        raise ValueError(f"run is missing synthesis stage records: {result.run_id}")
    stage = [by_node[node_id] for node_id in STAGE_NODE_IDS]
    if any(item.execution is None for item in stage):
        raise ValueError(f"run has incomplete synthesis stage: {result.run_id}")
    executions = [item.execution for item in stage if item.execution is not None]
    leader = by_node[STAGE_NODE_IDS[0]]
    selected_agent = leader.scheduler_decision.selected_agent_id
    if selected_agent is None:
        raise ValueError("synthesis stage leader lacks selected agent")
    transfers = [item for execution in executions for item in execution.transfers]
    model_telemetry = next(
        (
            execution.model_telemetry
            for execution in executions
            if execution.model_telemetry is not None
        ),
        None,
    )
    if model_telemetry is None:
        raise ValueError("synthesis stage lacks model telemetry")
    non_model_compute = sum(
        execution.operator_latency_ms
        for execution in executions
        if execution.model_telemetry is None
    )
    return PlacementRunObservation(
        run_id=result.run_id,
        payload_class=metadata.payload_class.value,
        placement_policy=metadata.placement_policy,
        network_calibration_id=metadata.network_calibration_id,
        selected_agent_id=selected_agent,
        stage_cost_ms=sum(item.duration_ms for item in stage),
        stage_compute_ms=non_model_compute + model_telemetry.service_latency_ms,
        stage_transfer_bytes=sum(item.bytes_transferred for item in transfers),
        stage_transfer_ms=sum(item.duration_ms for item in transfers),
        model_service_ms=model_telemetry.service_latency_ms,
        model_input_tokens=model_telemetry.input_tokens,
        model_output_tokens=model_telemetry.output_tokens,
        model_finish_reason=model_telemetry.finish_reason,
        workflow_e2e_ms=result.workflow.telemetry.e2e_latency_ms,
        critical_path_ms=result.workflow.telemetry.critical_path_latency_ms,
        scheduler_overhead_ms=scheduler_overhead_ms,
        benchmark_score=result.evaluation.benchmark_score,
        format_valid=result.evaluation.format_valid,
    )


def build_stage_estimates(
    observations: Iterable[PlacementRunObservation],
    payload_class: str,
    *,
    profile_id: str,
) -> tuple[SynthesisStageEstimate, ...]:
    values = [item for item in observations if item.payload_class == payload_class]
    by_agent: dict[str, list[PlacementRunObservation]] = defaultdict(list)
    for item in values:
        if item.placement_policy.startswith("forced-"):
            by_agent[item.selected_agent_id].append(item)
    expected = {"A28", "strong-4090"}
    if set(by_agent) != expected or any(len(by_agent[item]) < 3 for item in expected):
        raise ValueError("stage estimates require >=3 forced samples for both replicas")
    replica_ids = {
        "A28": "a28-qwen3.8-27b-q4km-v1",
        "strong-4090": "strong-4090-qwen3.8-27b-q4km-v1",
    }
    return tuple(
        SynthesisStageEstimate(
            compute_profile_id=profile_id,
            replica_id=replica_ids[agent_id],
            median_reduction_latency_ms=median(
                item.stage_compute_ms - item.model_service_ms
                for item in by_agent[agent_id]
            ),
            median_model_service_latency_ms=median(
                item.model_service_ms for item in by_agent[agent_id]
            ),
        )
        for agent_id in ("A28", "strong-4090")
    )


def oracle_cells(
    observations: Iterable[PlacementRunObservation],
) -> tuple[OracleCellSummary, ...]:
    grouped: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for item in observations:
        if item.placement_policy.startswith("forced-"):
            grouped[(item.payload_class, item.network_calibration_id)][
                item.selected_agent_id
            ].append(item.stage_cost_ms)
    cells: list[OracleCellSummary] = []
    for (payload, calibration), by_agent in sorted(grouped.items()):
        if set(by_agent) != {"A28", "strong-4090"}:
            raise ValueError("oracle cell lacks one forced placement")
        a28 = summarize(by_agent["A28"])
        rtx = summarize(by_agent["strong-4090"])
        cells.append(
            OracleCellSummary(
                payload_class=payload,
                network_calibration_id=calibration,
                a28_cost_ms=a28,
                rtx_cost_ms=rtx,
                oracle_agent_id=("A28" if a28.median <= rtx.median else "strong-4090"),
            )
        )
    return tuple(cells)


def routing_regrets(
    observations: Iterable[PlacementRunObservation],
    cells: Iterable[OracleCellSummary],
) -> tuple[SchedulerRegretObservation, ...]:
    oracle = {(item.payload_class, item.network_calibration_id): item for item in cells}
    result: list[SchedulerRegretObservation] = []
    for item in observations:
        if item.placement_policy not in {"b0", "b1"}:
            continue
        cell = oracle[(item.payload_class, item.network_calibration_id)]
        costs = {
            "A28": cell.a28_cost_ms.median,
            "strong-4090": cell.rtx_cost_ms.median,
        }
        selected_cost = costs[item.selected_agent_id]
        oracle_cost = costs[cell.oracle_agent_id]
        result.append(
            SchedulerRegretObservation(
                run_id=item.run_id,
                payload_class=item.payload_class,
                placement_policy=item.placement_policy,
                network_calibration_id=item.network_calibration_id,
                selected_agent_id=item.selected_agent_id,
                oracle_agent_id=cell.oracle_agent_id,
                selected_empirical_cost_ms=selected_cost,
                oracle_empirical_cost_ms=oracle_cost,
                routing_regret_ms=max(0.0, selected_cost - oracle_cost),
                oracle_selected=item.selected_agent_id == cell.oracle_agent_id,
            )
        )
    return tuple(result)


def predicted_break_even_mbps(
    payload_bytes: int,
    a28_compute_ms: float,
    rtx_compute_ms: float,
    rtt_ms: float,
) -> float | None:
    transfer_budget_ms = a28_compute_ms - rtx_compute_ms - rtt_ms
    if transfer_budget_ms <= 0:
        return None
    return payload_bytes * 8 / (transfer_budget_ms * 1000)
