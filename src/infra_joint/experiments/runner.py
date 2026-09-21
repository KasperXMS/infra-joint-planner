import json
from contextlib import AsyncExitStack
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

import httpx
from pydantic import Field

from infra_joint.benchmarks.base import AdaptationBundle, PreparedArtifact
from infra_joint.config import RunnerConfig, build_model_backend
from infra_joint.core.base import ContractModel
from infra_joint.core.errors import TypedExecutionError
from infra_joint.evaluation.evaluator import EvaluationResult
from infra_joint.evaluation.trace import JsonlTraceWriter, TraceEvent
from infra_joint.infrastructure.observer import LiveWorkerObserver
from infra_joint.infrastructure.validation import validate_worker_surfaces
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.planning.finalize import ContractAwareFinalizer
from infra_joint.planning.graph import PlanningGraph, RunTelemetry
from infra_joint.planning.planner import (
    CompletionBackend,
    LLMBlindPlanner,
    PlannerDecisionError,
)
from infra_joint.runtime.client import HttpWorkerClient, WorkerClient
from infra_joint.runtime.executor import (
    ArtifactTransferTelemetry,
    ExecutionResult,
    RuntimeExecutor,
)
from infra_joint.runtime.resolver import BindingResolutionError


class RunFailure(ContractModel):
    code: str = Field(min_length=1)
    exception_type: str = Field(min_length=1)
    message: str = Field(min_length=1)


class PersistedRunResult(ContractModel):
    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    benchmark_id: str = Field(min_length=1)
    setting_kind: str = Field(min_length=1)
    execution_completed: bool
    final_answer: str | None = None
    evaluation: EvaluationResult | None = None
    decisions: tuple[dict[str, Any], ...] = ()
    observations: tuple[ExecutionResult, ...] = ()
    initial_transfers: tuple[ArtifactTransferTelemetry, ...] = ()
    telemetry: RunTelemetry | None = None
    runner_e2e_latency_ms: float = Field(ge=0)
    failure: RunFailure | None = None
    trace_path: str = Field(min_length=1)


class BenchmarkRunner:
    def __init__(
        self,
        config: RunnerConfig,
        *,
        worker_clients: dict[str, WorkerClient] | None = None,
        planner_backend: CompletionBackend | None = None,
    ) -> None:
        self._config = config
        self._worker_clients = worker_clients
        self._planner_backend = planner_backend

    async def run(
        self,
        bundle: AdaptationBundle,
        *,
        run_id: str | None = None,
    ) -> PersistedRunResult:
        resolved_run_id = run_id or str(uuid4())
        run_directory = self._config.output_root / resolved_run_id
        run_directory.mkdir(parents=True, exist_ok=False)
        trace_path = run_directory / "trace.jsonl"
        result_path = run_directory / "result.json"
        trace = JsonlTraceWriter(trace_path)
        started = perf_counter()
        planner_client = None
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
                initial_transfers = await self._materialize(bundle, worker_clients)
                planner_backend = self._planner_backend
                if planner_backend is None:
                    planner_backend, planner_client = build_model_backend(
                        self._config.planner.model
                    )
                graph = PlanningGraph(
                    planner=LLMBlindPlanner(planner_backend, registry),
                    observer=LiveWorkerObserver(
                        self._config.environment,
                        worker_clients,
                    ),
                    executor=RuntimeExecutor(
                        registry,
                        self._config.environment,
                        worker_clients,
                    ),
                    finalizer=ContractAwareFinalizer(planner_backend),
                    evaluator=bundle.private_evaluation.build_evaluator(),
                    max_planning_steps=self._config.max_planning_steps,
                    trace_sink=trace,
                )
                result = await graph.run(
                    bundle.execution.task,
                    run_id=resolved_run_id,
                    initial_transfers=initial_transfers,
                )
            persisted = PersistedRunResult(
                run_id=resolved_run_id,
                task_id=bundle.execution.task.task_id,
                benchmark_id=bundle.execution.task.benchmark_id,
                setting_kind=bundle.execution.validity.setting_kind,
                execution_completed=True,
                final_answer=result["final_answer"],
                evaluation=result["evaluation"],
                decisions=tuple(
                    decision.model_dump(mode="json") for decision in result["decisions"]
                ),
                observations=result["observations"],
                initial_transfers=result["initial_transfers"],
                telemetry=result["telemetry"],
                runner_e2e_latency_ms=(perf_counter() - started) * 1000,
                trace_path=str(trace_path),
            )
        except Exception as exc:  # noqa: BLE001 - failures are persisted for audit
            failure = self._failure(exc)
            elapsed = (perf_counter() - started) * 1000
            self._append_failure_trace(trace, resolved_run_id, failure, elapsed)
            persisted = PersistedRunResult(
                run_id=resolved_run_id,
                task_id=bundle.execution.task.task_id,
                benchmark_id=bundle.execution.task.benchmark_id,
                setting_kind=bundle.execution.validity.setting_kind,
                execution_completed=False,
                runner_e2e_latency_ms=elapsed,
                failure=failure,
                trace_path=str(trace_path),
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
                started = perf_counter()
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
                        duration_ms=(perf_counter() - started) * 1000,
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

    @staticmethod
    def _failure(exc: Exception) -> RunFailure:
        if isinstance(exc, (TypedExecutionError, BindingResolutionError)):
            code = exc.code.value
        elif isinstance(exc, PlannerDecisionError):
            code = "planner_decision_invalid"
        else:
            code = "internal_error"
        return RunFailure(
            code=code,
            exception_type=type(exc).__name__,
            message=str(exc) or type(exc).__name__,
        )

    @staticmethod
    def _append_failure_trace(
        trace: JsonlTraceWriter,
        run_id: str,
        failure: RunFailure,
        elapsed_ms: float,
    ) -> None:
        events = trace.read_all()
        trace.append(
            TraceEvent(
                run_id=run_id,
                step_id=f"{len(events):06d}-run.failed",
                parent_id=events[-1]["step_id"] if events else None,
                event_type="run.failed",
                timestamp=datetime.now(UTC),
                payload={
                    "failure": failure.model_dump(mode="json"),
                    "runner_e2e_latency_ms": elapsed_ms,
                },
            )
        )

    @staticmethod
    def _write_result(path: Path, result: PersistedRunResult) -> None:
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
