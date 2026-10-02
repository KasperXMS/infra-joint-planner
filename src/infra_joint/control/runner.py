from __future__ import annotations

import json
from contextlib import AsyncExitStack
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Protocol, cast
from uuid import uuid4

import httpx
from pydantic import Field

from infra_joint.benchmarks.base import AdaptationBundle, PreparedArtifact
from infra_joint.config import RunnerConfig
from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.contracts import (
    LogicalAgentSpec,
    ProfileVisibility,
    StaticCapabilityContract,
)
from infra_joint.control.gateway import RuntimeActionGateway
from infra_joint.control.loop import (
    AgentLoopBudget,
    AgentLoopError,
    AgentLoopResult,
    ManagerPolicy,
    PersistentManagerLoop,
    SubagentPolicyFactory,
)
from infra_joint.control.physical import PhysicalExecutionService, PhysicalProfiler
from infra_joint.control.validation import SemanticActionValidator, SemanticValidationError
from infra_joint.core.base import ContractModel
from infra_joint.core.task import TaskContract
from infra_joint.evaluation.evaluator import EvaluationResult
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.infrastructure.diagnostics import JsonlObserverDiagnostics
from infra_joint.infrastructure.observer import LiveWorkerObserver
from infra_joint.infrastructure.validation import validate_worker_surfaces
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.runtime.client import HttpWorkerClient, WorkerClient
from infra_joint.runtime.executor import (
    ArtifactTransferTelemetry,
    ExecutionResult,
    RuntimeExecutor,
)
from infra_joint.workflow.costing import ExecutionCostProfile
from infra_joint.workflow.trace import WorkflowTraceRecorder


class LogicalRuntime(Protocol):
    async def run(
        self,
        task: TaskContract,
        gateway: RuntimeActionGateway,
        *,
        root_agent: LogicalAgentSpec | None,
        profile_visibility: ProfileVisibility,
        budget: AgentLoopBudget | None,
        trace: WorkflowTraceRecorder,
        static_capabilities: StaticCapabilityContract,
    ) -> AgentLoopResult: ...


class ControlPlaneRunFailure(ContractModel):
    code: str = Field(min_length=1)
    exception_type: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ControlPlaneRunTelemetry(ContractModel):
    e2e_latency_ms: float = Field(ge=0)
    initial_transfer_bytes: int = Field(ge=0)
    initial_transfer_latency_ms: float = Field(ge=0)
    action_transfer_bytes: int = Field(ge=0)
    action_transfer_latency_ms: float = Field(ge=0)
    operator_latency_ms: float = Field(ge=0)
    planner_latency_ms: float = Field(ge=0)


class PersistedControlPlaneResult(ContractModel):
    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    benchmark_id: str = Field(min_length=1)
    setting_kind: str = Field(min_length=1)
    execution_completed: bool
    loop: AgentLoopResult | None = None
    final_answer: str | None = None
    evaluation: EvaluationResult | None = None
    initial_transfers: tuple[ArtifactTransferTelemetry, ...] = ()
    telemetry: ControlPlaneRunTelemetry | None = None
    failure: ControlPlaneRunFailure | None = None
    trace_path: str = Field(min_length=1)


class ControlPlaneBenchmarkRunner:
    """The single formal pipeline for the persistent Agent Runtime control plane."""

    def __init__(
        self,
        config: RunnerConfig,
        manager: ManagerPolicy | None,
        available_operations: tuple[str, ...],
        *,
        worker_clients: dict[str, WorkerClient] | None = None,
        subagent_factory: SubagentPolicyFactory | None = None,
        root_agent: LogicalAgentSpec | None = None,
        profile_visibility: ProfileVisibility = ProfileVisibility.BLIND,
        cost_profiles: tuple[ExecutionCostProfile, ...] = (),
        loop_budget: AgentLoopBudget | None = None,
        logical_runtime: LogicalRuntime | None = None,
    ) -> None:
        if manager is None and logical_runtime is None:
            raise ValueError("manager or logical_runtime is required")
        self._config = config
        self._manager = manager
        self._available_operations = available_operations
        self._worker_clients = worker_clients
        self._subagent_factory = subagent_factory
        self._root_agent = root_agent
        self._profile_visibility = profile_visibility
        self._cost_profiles = cost_profiles
        self._loop_budget = loop_budget
        self._logical_runtime = logical_runtime

    async def run(
        self,
        bundle: AdaptationBundle,
        *,
        run_id: str | None = None,
    ) -> PersistedControlPlaneResult:
        resolved_run_id = run_id or str(uuid4())
        run_directory = self._config.output_root / resolved_run_id
        run_directory.mkdir(parents=True, exist_ok=False)
        trace_path = run_directory / "trace.jsonl"
        result_path = run_directory / "result.json"
        trace = WorkflowTraceRecorder(resolved_run_id, JsonlTraceWriter(trace_path))
        started = perf_counter()
        initial_transfers: tuple[ArtifactTransferTelemetry, ...] = ()
        try:
            async with AsyncExitStack() as stack:
                clients = dict(self._worker_clients or {})
                if self._worker_clients is None:
                    for agent_id, base_url in self._config.worker_urls.items():
                        client = await stack.enter_async_context(
                            httpx.AsyncClient(
                                base_url=base_url,
                                timeout=self._config.http_timeout_seconds,
                            )
                        )
                        clients[agent_id] = HttpWorkerClient(agent_id, client)
                registry = build_operator_catalog()
                await validate_worker_surfaces(
                    self._config.environment,
                    registry,
                    clients,
                )
                trace.emit(
                    "task.start",
                    {
                        "task_id": bundle.execution.task.task_id,
                        "benchmark_id": bundle.execution.task.benchmark_id,
                    },
                )
                initial_transfers = await self._materialize(bundle, clients)
                for transfer in initial_transfers:
                    trace.emit(
                        "artifact.materialize.end", transfer.model_dump(mode="json")
                    )
                observer = LiveWorkerObserver(
                    self._config.environment,
                    clients,
                    diagnostic_sink=JsonlObserverDiagnostics(
                        run_directory / "private" / "observer-diagnostics.jsonl"
                    ),
                    expected_artifact_ids=tuple(
                        item.artifact_id for item in bundle.execution.task.artifacts
                    ),
                )
                physical = PhysicalExecutionService(
                    registry,
                    self._config.environment,
                    observer,
                    RuntimeExecutor(registry, self._config.environment, clients),
                    profiler=PhysicalProfiler(
                        self._config.environment,
                        registry,
                        self._cost_profiles,
                    ),
                )
                gateway = RuntimeActionGateway(
                    SemanticActionValidator(
                        bundle.execution.task,
                        registry,
                        self._available_operations,
                    ),
                    physical,
                )
                if self._logical_runtime is not None:
                    static_capabilities = build_static_capability_contract(
                        self._config.environment,
                        registry,
                        self._available_operations,
                    )
                    loop = await self._logical_runtime.run(
                        bundle.execution.task,
                        gateway,
                        root_agent=self._root_agent,
                        profile_visibility=self._profile_visibility,
                        budget=self._loop_budget,
                        trace=trace,
                        static_capabilities=static_capabilities,
                    )
                else:
                    if self._manager is None:
                        raise RuntimeError("legacy manager policy is not configured")
                    loop = await PersistentManagerLoop(
                        gateway,
                        self._manager,
                        root_agent=self._root_agent,
                        subagent_factory=self._subagent_factory,
                        profile_visibility=self._profile_visibility,
                        max_steps_per_agent=self._config.max_planning_steps,
                        budget=self._loop_budget,
                        trace=trace,
                    ).run(bundle.execution.task)
                evaluation = await bundle.private_evaluation.build_evaluator().evaluate(
                    bundle.execution.task,
                    loop.final_answer,
                )
                trace.emit("evaluation.result", evaluation.model_dump(mode="json"))
                telemetry = self._telemetry(
                    started,
                    initial_transfers,
                    loop,
                    trace_path,
                )
                trace.emit("run.end", telemetry.model_dump(mode="json"))
                persisted = PersistedControlPlaneResult(
                    run_id=resolved_run_id,
                    task_id=bundle.execution.task.task_id,
                    benchmark_id=bundle.execution.task.benchmark_id,
                    setting_kind=bundle.execution.validity.setting_kind,
                    execution_completed=True,
                    loop=loop,
                    final_answer=loop.final_answer,
                    evaluation=evaluation,
                    initial_transfers=initial_transfers,
                    telemetry=telemetry,
                    trace_path=str(trace_path),
                )
        except Exception as exc:  # noqa: BLE001 - every run failure is evidence
            failure = ControlPlaneRunFailure(
                code=self._failure_code(exc),
                exception_type=type(exc).__name__,
                message=str(exc) or type(exc).__name__,
            )
            trace.emit(
                "run.failed",
                {
                    "failure": failure.model_dump(mode="json"),
                    "e2e_latency_ms": (perf_counter() - started) * 1000,
                },
            )
            persisted = PersistedControlPlaneResult(
                run_id=resolved_run_id,
                task_id=bundle.execution.task.task_id,
                benchmark_id=bundle.execution.task.benchmark_id,
                setting_kind=bundle.execution.validity.setting_kind,
                execution_completed=False,
                initial_transfers=initial_transfers,
                failure=failure,
                trace_path=str(trace_path),
            )
        self._write_result(result_path, persisted)
        return persisted

    async def _materialize(
        self,
        bundle: AdaptationBundle,
        clients: dict[str, WorkerClient],
    ) -> tuple[ArtifactTransferTelemetry, ...]:
        task = bundle.execution.task
        prepared = {item.spec.artifact_id: item for item in bundle.prepared_artifacts}
        placements: dict[str, list[str]] = {}
        for placement in self._config.environment.initial_placements:
            placements.setdefault(placement.artifact_id, []).append(placement.agent_id)
        expected = {item.artifact_id for item in task.artifacts}
        if set(placements) != expected:
            raise ValueError("initial placements must cover exactly the task artifacts")
        telemetry: list[ArtifactTransferTelemetry] = []
        for artifact in task.artifacts:
            content, checksum = self._artifact_content(artifact.artifact_id, prepared)
            if len(content) != artifact.size_bytes:
                raise ValueError(
                    f"artifact size differs from TaskContract: {artifact.artifact_id}"
                )
            for agent_id in sorted(placements[artifact.artifact_id]):
                transfer_started = perf_counter()
                response = await clients[agent_id].put_artifact(
                    artifact.artifact_id,
                    artifact.media_type,
                    content,
                    checksum,
                )
                telemetry.append(
                    ArtifactTransferTelemetry(
                        artifact_id=artifact.artifact_id,
                        source_agent_id="controller",
                        target_agent_id=agent_id,
                        bytes_transferred=response.size_bytes,
                        duration_ms=(perf_counter() - transfer_started) * 1000,
                    )
                )
        return tuple(telemetry)

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

    @staticmethod
    def _telemetry(
        started: float,
        initial: tuple[ArtifactTransferTelemetry, ...],
        loop: AgentLoopResult,
        trace_path: Path,
    ) -> ControlPlaneRunTelemetry:
        events = cast(list[dict[str, object]], JsonlTraceWriter(trace_path).read_all())
        executions: list[ExecutionResult] = []
        for event in events:
            if event.get("event_type") != "physical.execution":
                continue
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            execution = cast(dict[object, object], payload).get("execution")
            if execution is not None:
                executions.append(ExecutionResult.model_validate(execution))
        transfers = [transfer for execution in executions for transfer in execution.transfers]
        return ControlPlaneRunTelemetry(
            e2e_latency_ms=(perf_counter() - started) * 1000,
            initial_transfer_bytes=sum(item.bytes_transferred for item in initial),
            initial_transfer_latency_ms=sum(item.duration_ms for item in initial),
            action_transfer_bytes=sum(item.bytes_transferred for item in transfers),
            action_transfer_latency_ms=sum(item.duration_ms for item in transfers),
            operator_latency_ms=sum(item.operator_latency_ms for item in executions),
            planner_latency_ms=sum(item.latency_ms for item in loop.planner_steps),
        )

    @staticmethod
    def _failure_code(exc: Exception) -> str:
        code = getattr(exc, "code", None)
        if code is not None and isinstance(getattr(code, "value", None), str):
            return str(code.value)
        if isinstance(exc, SemanticValidationError):
            return "semantic_validation_failed"
        if isinstance(exc, AgentLoopError):
            return "logical_loop_failed"
        return "control_plane_failed"

    @staticmethod
    def _write_result(path: Path, result: PersistedControlPlaneResult) -> None:
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
