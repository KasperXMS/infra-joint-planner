from __future__ import annotations

from contextlib import AsyncExitStack
from hashlib import sha256
from time import perf_counter
from uuid import uuid4

import httpx
from pydantic import Field

from infra_joint.agents.context import AgentTaskView
from infra_joint.benchmarks.base import AdaptationBundle, PreparedArtifact
from infra_joint.config import RunnerConfig
from infra_joint.control.adaptation import WorkflowAdaptationPolicy
from infra_joint.control.adaptive_executor import (
    AdaptiveWorkflowExecution,
    AdaptiveWorkflowExecutor,
)
from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.contracts import StaticCapabilityContract
from infra_joint.control.gateway import RuntimeActionGateway
from infra_joint.control.physical import PhysicalExecutionService, PhysicalProfiler
from infra_joint.control.prior import (
    FrozenPriorWorkflow,
    PriorWorkflowGenerator,
    PriorWorkflowStore,
)
from infra_joint.control.validation import SemanticActionValidator
from infra_joint.control.workflow import canonical_sha256
from infra_joint.control.workflow_cost import (
    ConcurrentServiceProfile,
    ObservedWorkflowProfileProvider,
    SemanticWorkflowCostEvaluator,
)
from infra_joint.core.base import ContractModel
from infra_joint.core.task import TaskContract
from infra_joint.evaluation.evaluator import EvaluationResult
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.infrastructure.observer import LiveWorkerObserver
from infra_joint.infrastructure.validation import validate_worker_surfaces
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.runtime.client import HttpWorkerClient, WorkerClient
from infra_joint.runtime.executor import ArtifactTransferTelemetry, RuntimeExecutor
from infra_joint.workflow.costing import ExecutionCostProfile
from infra_joint.workflow.trace import WorkflowTraceRecorder


class AdaptiveRunFailure(ContractModel):
    code: str = Field(min_length=1)
    exception_type: str = Field(min_length=1)
    message: str = Field(min_length=1)


class PersistedAdaptiveWorkflowResult(ContractModel):
    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    benchmark_id: str = Field(min_length=1)
    execution_completed: bool
    prior_plan_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    execution: AdaptiveWorkflowExecution | None = None
    final_answer: str | None = None
    terminal_output_contract_valid: bool | None = None
    evaluation: EvaluationResult | None = None
    initial_transfers: tuple[ArtifactTransferTelemetry, ...] = ()
    e2e_latency_ms: float = Field(ge=0)
    trace_path: str = Field(min_length=1)
    failure: AdaptiveRunFailure | None = None


class AdaptiveWorkflowBenchmarkRunner:
    """Parallel formal path over the existing benchmark and physical substrate."""

    def __init__(
        self,
        config: RunnerConfig,
        prior_generator: PriorWorkflowGenerator,
        adaptation_policy: WorkflowAdaptationPolicy,
        available_operations: tuple[str, ...],
        *,
        prior_store: PriorWorkflowStore,
        require_frozen_prior: bool = True,
        worker_clients: dict[str, WorkerClient] | None = None,
        cost_profiles: tuple[ExecutionCostProfile, ...] = (),
        concurrent_service_profiles: tuple[ConcurrentServiceProfile, ...] = (),
    ) -> None:
        self._config = config
        self._prior_generator = prior_generator
        self._adapter = adaptation_policy
        self._available_operations = available_operations
        self._prior_store = prior_store
        self._require_frozen_prior = require_frozen_prior
        self._worker_clients = worker_clients
        self._cost_profiles = cost_profiles
        self._concurrent_service_profiles = concurrent_service_profiles

    async def run(
        self,
        bundle: AdaptationBundle,
        *,
        run_id: str | None = None,
    ) -> PersistedAdaptiveWorkflowResult:
        resolved_run_id = run_id or str(uuid4())
        run_directory = self._config.output_root / resolved_run_id
        run_directory.mkdir(parents=True, exist_ok=False)
        trace_path = run_directory / "trace.jsonl"
        result_path = run_directory / "result.json"
        trace = WorkflowTraceRecorder(resolved_run_id, JsonlTraceWriter(trace_path))
        started = perf_counter()
        transfers: tuple[ArtifactTransferTelemetry, ...] = ()
        frozen: FrozenPriorWorkflow | None = None
        task = bundle.execution.task
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
                await validate_worker_surfaces(self._config.environment, registry, clients)
                capabilities = build_static_capability_contract(
                    self._config.environment,
                    registry,
                    self._available_operations,
                )
                bundle_hash = self._public_bundle_hash(bundle)
                frozen = await self._resolve_prior(task, capabilities, bundle_hash)
                transfers = await self._materialize(bundle, clients)
                for transfer in transfers:
                    trace.emit("artifact.materialize.end", transfer.model_dump(mode="json"))
                observer = LiveWorkerObserver(self._config.environment, clients)
                profiler = PhysicalProfiler(
                    self._config.environment,
                    registry,
                    self._cost_profiles,
                )
                gateway = RuntimeActionGateway(
                    SemanticActionValidator(
                        task,
                        registry,
                        self._available_operations,
                    ),
                    PhysicalExecutionService(
                        registry,
                        self._config.environment,
                        observer,
                        RuntimeExecutor(registry, self._config.environment, clients),
                        profiler=profiler,
                    ),
                )
                execution = await AdaptiveWorkflowExecutor(
                    gateway,
                    ObservedWorkflowProfileProvider(
                        observer,
                        SemanticWorkflowCostEvaluator(
                            self._config.environment,
                            registry,
                            self._cost_profiles,
                            task,
                            capabilities,
                            concurrent_profiles=self._concurrent_service_profiles,
                        ),
                    ),
                    self._adapter,
                    registry,
                    capabilities,
                ).execute(task, frozen.plan, trace)
                evaluation = None
                if execution.final_answer is not None:
                    evaluation = await bundle.private_evaluation.build_evaluator().evaluate(
                        task,
                        execution.final_answer,
                    )
                    trace.emit("evaluation.result", evaluation.model_dump(mode="json"))
                persisted = PersistedAdaptiveWorkflowResult(
                    run_id=resolved_run_id,
                    task_id=task.task_id,
                    benchmark_id=task.benchmark_id,
                    execution_completed=execution.succeeded,
                    prior_plan_sha256=frozen.plan_sha256,
                    execution=execution,
                    final_answer=execution.final_answer,
                    terminal_output_contract_valid=(
                        execution.terminal_output_contract.valid
                        if execution.terminal_output_contract is not None
                        else None
                    ),
                    evaluation=evaluation,
                    initial_transfers=transfers,
                    e2e_latency_ms=(perf_counter() - started) * 1000,
                    trace_path=str(trace_path),
                )
        except Exception as exc:  # noqa: BLE001 - failed formal runs are evidence
            failure = AdaptiveRunFailure(
                code="adaptive_workflow_failed",
                exception_type=type(exc).__name__,
                message=str(exc) or type(exc).__name__,
            )
            persisted = PersistedAdaptiveWorkflowResult(
                run_id=resolved_run_id,
                task_id=task.task_id,
                benchmark_id=task.benchmark_id,
                execution_completed=False,
                prior_plan_sha256=frozen.plan_sha256 if frozen is not None else None,
                initial_transfers=transfers,
                e2e_latency_ms=(perf_counter() - started) * 1000,
                trace_path=str(trace_path),
                failure=failure,
            )
            trace.emit("run.failed", failure.model_dump(mode="json"))
        result_path.write_text(persisted.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return persisted

    async def prepare_prior_workflow(
        self,
        bundle: AdaptationBundle,
    ) -> FrozenPriorWorkflow:
        """Explicit development/preparation entry point; it performs no task execution."""

        registry = build_operator_catalog()
        capabilities = build_static_capability_contract(
            self._config.environment,
            registry,
            self._available_operations,
        )
        generation = await self._prior_generator.generate(
            bundle.execution.task,
            capabilities,
        )
        expected = self._prior_generator.provenance(bundle.execution.task, capabilities)
        if generation.provenance != expected:
            raise ValueError("prior generator returned inconsistent provenance")
        frozen = FrozenPriorWorkflow.create(
            task=bundle.execution.task,
            generation=generation,
            capabilities=capabilities,
            public_bundle_sha256=self._public_bundle_hash(bundle),
        )
        self._prior_store.save(frozen)
        return frozen

    async def _resolve_prior(
        self,
        task: TaskContract,
        capabilities: StaticCapabilityContract,
        bundle_hash: str,
    ) -> FrozenPriorWorkflow:
        expected = self._prior_generator.provenance(task, capabilities)
        prior_path = self._prior_store.path_for(task.task_id)
        if prior_path.exists():
            frozen = self._prior_store.load(task.task_id)
            frozen.verify(task, capabilities, bundle_hash, expected)
            return frozen
        if self._require_frozen_prior:
            raise FileNotFoundError(
                f"formal experiment requires a frozen prior workflow: {prior_path}"
            )
        generation = await self._prior_generator.generate(task, capabilities)
        if generation.provenance != expected:
            raise ValueError("prior generator returned inconsistent provenance")
        frozen = FrozenPriorWorkflow.create(
            task=task,
            generation=generation,
            capabilities=capabilities,
            public_bundle_sha256=bundle_hash,
        )
        self._prior_store.save(frozen)
        return frozen

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
        if set(placements) != {item.artifact_id for item in task.artifacts}:
            raise ValueError("initial placements must cover exactly the task artifacts")
        telemetry: list[ArtifactTransferTelemetry] = []
        for artifact in task.artifacts:
            content, checksum = self._artifact_content(artifact.artifact_id, prepared)
            if len(content) != artifact.size_bytes:
                raise ValueError(f"artifact size differs from TaskContract: {artifact.artifact_id}")
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
    def _public_bundle_hash(bundle: AdaptationBundle) -> str:
        return canonical_sha256(
            {
                "task": AgentTaskView.from_contract(bundle.execution.task).model_dump(
                    mode="json", by_alias=True
                ),
                "prepared_artifacts": [
                    {
                        "spec": item.spec.model_dump(mode="json", exclude={"source_ref"}),
                        "sha256": item.sha256_hex,
                    }
                    for item in bundle.prepared_artifacts
                ],
            }
        )
