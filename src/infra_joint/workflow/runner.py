import json
from collections.abc import Iterable
from contextlib import AsyncExitStack
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import httpx
from pydantic import Field

from infra_joint.benchmarks.base import AdaptationBundle, PreparedArtifact
from infra_joint.config import RunnerConfig, build_model_backend
from infra_joint.core.base import ContractModel
from infra_joint.core.errors import TypedExecutionError
from infra_joint.core.workflow import WorkflowPlan
from infra_joint.evaluation.evaluator import EvaluationResult
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.infrastructure.observer import LiveWorkerObserver
from infra_joint.infrastructure.validation import validate_worker_surfaces
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.planning.graph import FinalizerCallTelemetry
from infra_joint.planning.planner import CompletionBackend
from infra_joint.runtime.client import HttpWorkerClient, WorkerClient
from infra_joint.runtime.executor import ArtifactTransferTelemetry, RuntimeExecutor
from infra_joint.runtime.resolver import BindingResolutionError
from infra_joint.worker.model_backend import ModelCallTelemetry
from infra_joint.workflow.finalize import extract_terminal_answer
from infra_joint.workflow.orchestrator import (
    WorkflowExecutionResult,
    WorkflowFailure,
    WorkflowOrchestrator,
)
from infra_joint.workflow.planner import (
    LLMWorkflowPlanner,
    WorkflowPlanner,
    WorkflowPlanningError,
)
from infra_joint.workflow.replanning import (
    ReplanningWorkflowExecution,
    ReplanningWorkflowExecutor,
    WorkflowReplanner,
    WorkflowReplanningError,
)
from infra_joint.workflow.scheduler import WorkflowScheduler
from infra_joint.workflow.trace import WorkflowTraceRecorder
from infra_joint.workflow.workload import WorkloadSpec


class WorkflowPlannerTelemetry(ContractModel):
    latency_ms: float = Field(ge=0)
    model: ModelCallTelemetry | None = None


class WorkflowRunTelemetry(ContractModel):
    runner_e2e_latency_ms: float = Field(ge=0)
    planner: WorkflowPlannerTelemetry
    workflow: WorkflowExecutionResult
    finalizer: FinalizerCallTelemetry
    total_transfer_bytes: int = Field(ge=0)
    total_transfer_duration_ms: float = Field(ge=0)


class WorkflowRunFailure(ContractModel):
    code: str = Field(min_length=1)
    exception_type: str = Field(min_length=1)
    message: str = Field(min_length=1)
    node_id: str | None = None


class PersistedWorkflowRunResult(ContractModel):
    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    benchmark_id: str = Field(min_length=1)
    setting_kind: str = Field(min_length=1)
    execution_completed: bool
    workload: WorkloadSpec
    plan: WorkflowPlan | None = None
    workflow: WorkflowExecutionResult | None = None
    replanning: ReplanningWorkflowExecution | None = None
    final_answer: str | None = None
    evaluation: EvaluationResult | None = None
    initial_transfers: tuple[ArtifactTransferTelemetry, ...] = ()
    telemetry: WorkflowRunTelemetry | None = None
    runner_e2e_latency_ms: float = Field(ge=0)
    failure: WorkflowRunFailure | None = None
    trace_path: str = Field(min_length=1)


class WorkflowBenchmarkRunner:
    """Real workflow pipeline over unchanged M4 workers and runtime."""

    def __init__(
        self,
        config: RunnerConfig,
        workload: WorkloadSpec,
        scheduler: WorkflowScheduler,
        *,
        worker_clients: dict[str, WorkerClient] | None = None,
        planner_backend: CompletionBackend | None = None,
        planner: WorkflowPlanner | None = None,
        replanner: WorkflowReplanner | None = None,
        replan_pause_before_operators: Iterable[str] = (),
    ) -> None:
        self._config = config
        self._workload = workload
        self._scheduler = scheduler
        self._worker_clients = worker_clients
        self._planner_backend = planner_backend
        self._planner = planner
        self._replanner = replanner
        self._replan_pause_before_operators = tuple(replan_pause_before_operators)

    async def run(
        self,
        bundle: AdaptationBundle,
        *,
        run_id: str | None = None,
    ) -> PersistedWorkflowRunResult:
        resolved_run_id = run_id or str(uuid4())
        run_directory = self._config.output_root / resolved_run_id
        run_directory.mkdir(parents=True, exist_ok=False)
        trace_path = run_directory / "trace.jsonl"
        result_path = run_directory / "result.json"
        trace = WorkflowTraceRecorder(resolved_run_id, JsonlTraceWriter(trace_path))
        started = perf_counter()
        planner_client = None
        plan: WorkflowPlan | None = None
        workflow_result: WorkflowExecutionResult | None = None
        replanning_result: ReplanningWorkflowExecution | None = None
        initial_transfers: tuple[ArtifactTransferTelemetry, ...] = ()
        try:
            async with AsyncExitStack() as stack:
                worker_clients = self._worker_clients or {}
                if self._worker_clients is None:
                    for agent_id, base_url in self._config.worker_urls.items():
                        http_client = await stack.enter_async_context(
                            httpx.AsyncClient(
                                base_url=base_url,
                                timeout=self._config.http_timeout_seconds,
                            )
                        )
                        worker_clients[agent_id] = HttpWorkerClient(agent_id, http_client)
                registry = build_operator_catalog()
                await validate_worker_surfaces(
                    self._config.environment,
                    registry,
                    worker_clients,
                )
                self._workload.validate_against(
                    bundle.execution.task,
                    self._config.environment,
                    registry,
                )
                trace.emit(
                    "task.start",
                    {
                        "task_id": bundle.execution.task.task_id,
                        "benchmark_id": bundle.execution.task.benchmark_id,
                    },
                )
                initial_transfers = await self._materialize(bundle, worker_clients)
                for transfer in initial_transfers:
                    trace.emit(
                        "artifact.materialize.end",
                        transfer.model_dump(mode="json"),
                    )

                if self._planner is not None:
                    planner = self._planner
                else:
                    planner_backend = self._planner_backend
                    if planner_backend is None:
                        planner_backend, planner_client = build_model_backend(
                            self._config.planner.model
                        )
                    planner = LLMWorkflowPlanner(
                        planner_backend,
                        registry,
                        self._config.environment,
                    )
                trace.emit("workflow.planner.start", {})
                planner_started = perf_counter()
                planning = await planner.plan(bundle.execution.task, self._workload)
                planner_telemetry = WorkflowPlannerTelemetry(
                    latency_ms=(perf_counter() - planner_started) * 1000,
                    model=planning.model_telemetry,
                )
                plan = planning.plan
                try:
                    plan.validate_against(
                        bundle.execution.task,
                        self._config.environment,
                        registry,
                        self._workload.available_operations,
                    )
                    terminal_node = plan.terminal_model_node()
                except (KeyError, ValueError) as exc:
                    raise WorkflowPlanningError(str(exc)) from exc
                trace.emit(
                    "workflow.planner.end",
                    {
                        "plan": plan.model_dump(mode="json"),
                        "telemetry": planner_telemetry.model_dump(mode="json"),
                    },
                )
                orchestrator = WorkflowOrchestrator(
                    registry,
                    self._config.environment,
                    LiveWorkerObserver(self._config.environment, worker_clients),
                    RuntimeExecutor(registry, self._config.environment, worker_clients),
                    self._scheduler,
                    available_operations=self._workload.available_operations,
                    trace=trace,
                )
                if self._replanner is None:
                    workflow_result = await orchestrator.execute(
                        bundle.execution.task, plan
                    )
                else:
                    try:
                        replanning_result = await ReplanningWorkflowExecutor(
                            orchestrator,
                            self._replanner,
                            max_replans=1,
                            pause_before_operators=self._replan_pause_before_operators,
                            trace=trace,
                        ).execute(bundle.execution.task, self._workload, plan)
                    except WorkflowReplanningError as exc:
                        workflow_result = exc.execution
                        if workflow_result is not None:
                            current_plan = exc.current_plan or plan
                            replanning_result = ReplanningWorkflowExecution(
                                versions=exc.versions,
                                revisions=exc.revisions,
                                final_plan=current_plan,
                                workflow=workflow_result,
                            )
                            plan = current_plan
                        raise
                    plan = replanning_result.final_plan
                    terminal_node = plan.terminal_model_node()
                    workflow_result = replanning_result.workflow
                if not workflow_result.completed:
                    if workflow_result.failure is None:
                        raise RuntimeError("incomplete workflow is missing a typed failure")
                    elapsed = (perf_counter() - started) * 1000
                    run_failure = self._workflow_failure(workflow_result.failure)
                    trace.emit(
                        "run.failed",
                        {
                            "failure": run_failure.model_dump(mode="json"),
                            "runner_e2e_latency_ms": elapsed,
                        },
                    )
                    persisted = self._failed_result(
                        bundle,
                        resolved_run_id,
                        trace_path,
                        elapsed,
                        plan=plan,
                        workflow=workflow_result,
                        replanning=replanning_result,
                        initial_transfers=initial_transfers,
                        failure=run_failure,
                    )
                    self._write_result(result_path, persisted)
                    return persisted

                trace.emit(
                    "finalize.start",
                    {
                        "mode": "deterministic_terminal_extraction",
                        "terminal_node_id": terminal_node.node_id,
                    },
                )
                finalizer_started = perf_counter()
                final_answer = extract_terminal_answer(plan, workflow_result)
                finalizer_telemetry = FinalizerCallTelemetry(
                    latency_ms=(perf_counter() - finalizer_started) * 1000,
                    model=None,
                )
                trace.emit(
                    "finalize.end",
                    {
                        "answer": final_answer,
                        "telemetry": finalizer_telemetry.model_dump(mode="json"),
                    },
                )
                evaluation = await bundle.private_evaluation.build_evaluator().evaluate(
                    bundle.execution.task,
                    final_answer,
                )
                trace.emit("evaluation.result", evaluation.model_dump(mode="json"))
                elapsed = (perf_counter() - started) * 1000
                initial_bytes = sum(item.bytes_transferred for item in initial_transfers)
                initial_duration = sum(item.duration_ms for item in initial_transfers)
                telemetry = WorkflowRunTelemetry(
                    runner_e2e_latency_ms=elapsed,
                    planner=planner_telemetry,
                    workflow=workflow_result,
                    finalizer=finalizer_telemetry,
                    total_transfer_bytes=(
                        initial_bytes + workflow_result.telemetry.total_transfer_bytes
                    ),
                    total_transfer_duration_ms=(
                        initial_duration
                        + workflow_result.telemetry.total_transfer_duration_ms
                    ),
                )
                trace.emit(
                    "run.end",
                    {
                        "execution_completed": True,
                        "telemetry": telemetry.model_dump(mode="json"),
                    },
                )
                persisted = PersistedWorkflowRunResult(
                    run_id=resolved_run_id,
                    task_id=bundle.execution.task.task_id,
                    benchmark_id=bundle.execution.task.benchmark_id,
                    setting_kind=bundle.execution.validity.setting_kind,
                    execution_completed=True,
                    workload=self._workload,
                    plan=plan,
                    workflow=workflow_result,
                    replanning=replanning_result,
                    final_answer=final_answer,
                    evaluation=evaluation,
                    initial_transfers=initial_transfers,
                    telemetry=telemetry,
                    runner_e2e_latency_ms=elapsed,
                    trace_path=str(trace_path),
                )
        except Exception as exc:  # noqa: BLE001 - all run failures must be persisted
            failure = self._failure(exc)
            trace.emit(
                "run.failed",
                {
                    "failure": failure.model_dump(mode="json"),
                    "runner_e2e_latency_ms": (perf_counter() - started) * 1000,
                },
            )
            persisted = self._failed_result(
                bundle,
                resolved_run_id,
                trace_path,
                (perf_counter() - started) * 1000,
                plan=plan,
                workflow=workflow_result,
                replanning=replanning_result,
                initial_transfers=initial_transfers,
                failure=failure,
            )
        finally:
            if planner_client is not None:
                await planner_client.close()
        self._write_result(result_path, persisted)
        return persisted

    async def _materialize(
        self,
        bundle: AdaptationBundle,
        worker_clients: dict[str, WorkerClient],
    ) -> tuple[ArtifactTransferTelemetry, ...]:
        task = bundle.execution.task
        prepared = {item.spec.artifact_id: item for item in bundle.prepared_artifacts}
        placements: dict[str, list[str]] = {}
        for placement in self._config.environment.initial_placements:
            placements.setdefault(placement.artifact_id, []).append(placement.agent_id)
        expected_ids = {artifact.artifact_id for artifact in task.artifacts}
        if set(placements) != expected_ids:
            raise ValueError("initial placements must cover exactly the current task artifacts")
        transfers: list[ArtifactTransferTelemetry] = []
        for spec in task.artifacts:
            content, checksum = self._artifact_content(spec.artifact_id, prepared)
            if len(content) != spec.size_bytes:
                raise ValueError(f"artifact size differs from TaskContract: {spec.artifact_id}")
            for agent_id in sorted(placements[spec.artifact_id]):
                transfer_started = perf_counter()
                response = await worker_clients[agent_id].put_artifact(
                    spec.artifact_id,
                    spec.media_type,
                    content,
                    checksum,
                )
                transfers.append(
                    ArtifactTransferTelemetry(
                        artifact_id=spec.artifact_id,
                        source_agent_id="controller",
                        target_agent_id=agent_id,
                        bytes_transferred=response.size_bytes,
                        duration_ms=(perf_counter() - transfer_started) * 1000,
                    )
                )
        return tuple(transfers)

    def _artifact_content(
        self,
        artifact_id: str,
        prepared: dict[str, PreparedArtifact],
    ) -> tuple[bytes, str]:
        adapted = prepared.get(artifact_id)
        if adapted is not None:
            return adapted.content, adapted.sha256_hex
        try:
            path = self._config.artifact_sources[artifact_id]
        except KeyError as exc:
            raise ValueError(f"no materialization source for artifact: {artifact_id}") from exc
        content = path.read_bytes()
        return content, sha256(content).hexdigest()

    def _failed_result(
        self,
        bundle: AdaptationBundle,
        run_id: str,
        trace_path: Path,
        elapsed_ms: float,
        *,
        plan: WorkflowPlan | None,
        workflow: WorkflowExecutionResult | None,
        replanning: ReplanningWorkflowExecution | None = None,
        initial_transfers: tuple[ArtifactTransferTelemetry, ...],
        failure: WorkflowRunFailure,
    ) -> PersistedWorkflowRunResult:
        return PersistedWorkflowRunResult(
            run_id=run_id,
            task_id=bundle.execution.task.task_id,
            benchmark_id=bundle.execution.task.benchmark_id,
            setting_kind=bundle.execution.validity.setting_kind,
            execution_completed=False,
            workload=self._workload,
            plan=plan,
            workflow=workflow,
            replanning=replanning,
            initial_transfers=initial_transfers,
            runner_e2e_latency_ms=elapsed_ms,
            failure=failure,
            trace_path=str(trace_path),
        )

    @staticmethod
    def _workflow_failure(failure: WorkflowFailure) -> WorkflowRunFailure:
        return WorkflowRunFailure(
            code=failure.code,
            exception_type=failure.exception_type,
            message=failure.message,
            node_id=failure.node_id,
        )

    @staticmethod
    def _failure(exc: Exception) -> WorkflowRunFailure:
        if isinstance(exc, (TypedExecutionError, BindingResolutionError)):
            code = exc.code.value
        elif isinstance(exc, WorkflowPlanningError):
            code = "workflow_plan_invalid"
        elif isinstance(exc, WorkflowReplanningError):
            code = "workflow_replan_invalid"
        else:
            code = "internal_error"
        return WorkflowRunFailure(
            code=code,
            exception_type=type(exc).__name__,
            message=str(exc) or type(exc).__name__,
        )

    @staticmethod
    def _write_result(path: Path, result: PersistedWorkflowRunResult) -> None:
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(
                result.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        temporary.replace(path)
