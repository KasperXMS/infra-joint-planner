"""Run the 6-task open-ended infrastructure-aware preliminary experiment."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import socket
from collections import defaultdict
from contextlib import AsyncExitStack
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any, cast

import blind_baseline_6task_v1 as base
from infra_aware_replanning_preliminary_v1 import _regime_environment, _tc_surface
from open_ended_mas_preliminary_v1 import PrepositionedWorkflowRunner, _canonical_hash, _load_key

from infra_joint.benchmarks.base import (
    AdaptationBundle,
    AdaptedExecutionCase,
    PreparedArtifact,
    PrivateChoiceEvaluation,
    TransformationRecord,
    ValidityAssessment,
)
from infra_joint.config import RunnerConfig, build_model_backend, load_planner_config
from infra_joint.core.state import EnvironmentSpec, InfrastructureState
from infra_joint.core.task import TaskContract
from infra_joint.heterogeneous.traffic_control import (
    SshCommandRunner,
    TcController,
    TcRegime,
    build_tc_command_plan,
)
from infra_joint.infrastructure.observer import LiveWorkerObserver
from infra_joint.infrastructure.validation import validate_worker_surfaces
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.planning.planner import CompletionBackend
from infra_joint.runtime.client import WorkerClient
from infra_joint.worker.model_backend import ModelCompletion, ModelRequest
from infra_joint.workflow.costing import (
    ExecutionCostProfile,
    InfrastructurePlanningView,
    WorkflowCostEvaluator,
)
from infra_joint.workflow.planner import LLMInfrastructureAwareWorkflowPlanner
from infra_joint.workflow.replanning import (
    InfrastructureReplanView,
    LLMInfrastructureAwareWorkflowReplanner,
    WorkflowReplanContext,
)
from infra_joint.workflow.runner import PersistedWorkflowRunResult
from infra_joint.workflow.scheduler import LocalityAwareMyopicScheduler

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO / "configs/experiments/open-ended-infra-aware-preliminary-v1.yaml"
DEFAULT_OUTPUT = REPO / "results/open-ended-infra-aware-preliminary-v1"
DEFAULT_KEY = REPO.parent / "api_key.txt"


class CapturingBackend:
    def __init__(self, backend: CompletionBackend) -> None:
        self._backend = backend
        self.requests: list[ModelRequest] = []
        self.completions: list[ModelCompletion] = []
        self.wall_latency_ms: list[float] = []

    async def invoke(self, request: ModelRequest) -> ModelCompletion:
        self.requests.append(request)
        started = perf_counter()
        completion = await self._backend.invoke(request)
        self.wall_latency_ms.append((perf_counter() - started) * 1000)
        self.completions.append(completion)
        return completion


class LiveCostViewProvider:
    def __init__(
        self,
        task: TaskContract,
        environment: EnvironmentSpec,
        clients: dict[str, WorkerClient],
        profiles: tuple[ExecutionCostProfile, ...],
        registry: Any,
    ) -> None:
        self._task = task
        self._environment = environment
        self._observer = LiveWorkerObserver(environment, clients)
        self._profiles = profiles
        self._registry = registry
        self.planning_views: list[InfrastructurePlanningView] = []
        self.replan_views: list[InfrastructureReplanView] = []
        self.planning_evaluators: list[WorkflowCostEvaluator] = []
        self.replan_evaluators: list[WorkflowCostEvaluator] = []
        self.replan_contexts: list[WorkflowReplanContext] = []

    @property
    def task(self) -> TaskContract:
        return self._task

    async def observe_for_planning(self) -> InfrastructurePlanningView:
        relevant = tuple(item.artifact_id for item in self._task.artifacts)
        state = await self._state(relevant)
        evaluator = WorkflowCostEvaluator(
            self._environment,
            state,
            self._registry,
            self._profiles,
        )
        view = InfrastructurePlanningView(
            environment=self._environment,
            state=state,
            relevant_artifact_ids=relevant,
            cost_guidance=evaluator.guidance(relevant),
        )
        self.planning_evaluators.append(evaluator)
        self.planning_views.append(view)
        return view

    async def observe(self, context: WorkflowReplanContext) -> InfrastructureReplanView:
        relevant = tuple(
            sorted(
                {
                    artifact_id
                    for node in context.current_plan.nodes
                    for artifact_id in (*node.inputs, *node.outputs)
                }
            )
        )
        state = await self._state(relevant)
        evaluator = WorkflowCostEvaluator(
            self._environment,
            state,
            self._registry,
            self._profiles,
        )
        view = InfrastructureReplanView(
            environment=self._environment,
            state=state,
            relevant_artifact_ids=relevant,
            execution_cost_profiles=self._profiles,
            cost_guidance=evaluator.guidance(
                relevant,
                current_plan=context.current_plan,
                task=self._task,
                node_ids=context.pending_node_ids,
            ),
        )
        self.replan_evaluators.append(evaluator)
        self.replan_contexts.append(context)
        self.replan_views.append(view)
        return view

    async def _state(self, relevant: tuple[str, ...]) -> InfrastructureState:
        raw = await self._observer.observe()
        admitted = set(relevant)
        return raw.model_copy(
            update={
                "artifacts": tuple(
                    item for item in raw.artifacts if item.artifact_id in admitted
                )
            }
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _assert_controller(config: dict[str, Any]) -> None:
    expected = str(config["required_controller_hostname"]).lower()
    actual = socket.gethostname().lower()
    if actual != expected:
        raise RuntimeError(
            f"experiment controller must be {expected!r}, got {actual!r}; "
            "dataset materialization from this host is forbidden"
        )


def _load_bundles(
    config: dict[str, Any],
    source_evidence: Path,
    args: argparse.Namespace,
) -> dict[str, AdaptationBundle]:
    source_config = base._yaml(REPO / str(config["source_baseline_config"]))
    manifest = cast(
        dict[str, Any],
        json.loads((source_evidence / "freeze/manifest.json").read_text("utf-8")),
    )
    rows = {
        str(item["label"]): cast(dict[str, Any], item)
        for item in cast(list[dict[str, Any]], source_config["dataset"]["tasks"])
    }
    revisions = cast(dict[str, str], source_config["dataset"]["revisions"])
    bundles: dict[str, AdaptationBundle] = {}
    for label in ("video-long-payload", "video-cross-temporal"):
        frozen = cast(dict[str, Any], manifest["tasks"][label])
        task = TaskContract.model_validate_json(
            (source_evidence / "private" / label / "task-contract.json").read_text("utf-8")
        )
        private = PrivateChoiceEvaluation.model_validate_json(
            (source_evidence / "private" / label / "private-evaluation.json").read_text(
                "utf-8"
            )
        )
        provenance = cast(dict[str, Any], frozen["adaptation_provenance"])
        execution = AdaptedExecutionCase(
            task=task,
            transformations=tuple(
                TransformationRecord.model_validate(item)
                for item in cast(list[dict[str, Any]], provenance["transformations"])
            ),
            validity=ValidityAssessment.model_validate(provenance["validity"]),
        )
        source = args.video_sources / str(rows[label]["source_filename"])
        prepared = PreparedArtifact.create(task.artifacts[0], source.read_bytes())
        bundles[label] = AdaptationBundle(execution, private, (prepared,))

    longbench_ids = {
        str(rows[label]["source_task_id"])
        for label in ("longbench-multidoc", "longbench-structured")
    }
    samples = base._load_longbench_samples(args.longbench_samples, longbench_ids)
    multidoc_row = rows["longbench-multidoc"]
    bundles["longbench-multidoc"] = base._longbench_multidoc_bundle(
        samples[str(multidoc_row["source_task_id"])],
        revisions["longbench_v2"],
        tuple(int(value) for value in multidoc_row["boundary_lines"]),
    )
    structured_row = rows["longbench-structured"]
    bundles["longbench-structured"] = base._longbench_structured_bundle(
        samples[str(structured_row["source_task_id"])],
        revisions["longbench_v2"],
    )
    corpus_rows = cast(
        list[dict[str, Any]], json.loads(args.multihop_corpus.read_text("utf-8"))
    )
    query_rows = cast(
        list[dict[str, Any]], json.loads(args.multihop_queries.read_text("utf-8"))
    )
    for label in ("multihop-multisource", "multihop-reasoning"):
        bundles[label] = base._multihop_bundle(
            rows[label],
            corpus_rows,
            query_rows,
            revisions["multihop_rag"],
        )
    ordered_labels = [str(item["label"]) for item in source_config["dataset"]["tasks"]]
    bundles = {label: bundles[label] for label in ordered_labels}
    for label, bundle in bundles.items():
        frozen = cast(dict[str, Any], manifest["tasks"][label])
        frozen_task = TaskContract.model_validate_json(
            (source_evidence / "private" / label / "task-contract.json").read_text("utf-8")
        )
        frozen_private = json.loads(
            (source_evidence / "private" / label / "private-evaluation.json").read_text(
                "utf-8"
            )
        )
        actual = {
            item.spec.artifact_id: (item.spec.size_bytes, item.sha256_hex)
            for item in bundle.prepared_artifacts
        }
        expected = {
            str(item["artifact_id"]): (int(item["size_bytes"]), str(item["sha256"]))
            for item in cast(list[dict[str, Any]], frozen["artifacts"])
        }
        private_evaluation = cast(Any, bundle.private_evaluation)
        if (
            actual != expected
            or bundle.execution.task != frozen_task
            or private_evaluation.model_dump(mode="json") != frozen_private
        ):
            raise RuntimeError(f"task or artifact drift from frozen baseline: {label}")
        if not (
            bundle.execution.validity.information_equivalent
            and bundle.execution.validity.query_equivalent
            and bundle.execution.validity.evaluator_equivalent
        ):
            raise RuntimeError(f"benchmark adaptation is not equivalent: {label}")
    return bundles


def _observed_operator_profiles(source_evidence: Path) -> tuple[ExecutionCostProfile, ...]:
    observations: dict[tuple[str, str], list[tuple[float, int | None]]] = defaultdict(list)
    for path in sorted((source_evidence / "runs").glob("*/result.json")):
        result = cast(dict[str, Any], json.loads(path.read_text("utf-8")))
        workflow = result.get("workflow")
        if not isinstance(workflow, dict):
            continue
        for record in cast(list[dict[str, Any]], workflow.get("records", [])):
            execution = record.get("execution")
            action = record.get("action")
            if not isinstance(execution, dict) or not isinstance(action, dict):
                continue
            operator = str(execution["operator"])
            if operator == "invoke_model":
                continue
            agent_ids = cast(list[str], execution["agent_ids"])
            if len(agent_ids) != 1:
                continue
            output = execution.get("output")
            artifacts = (
                cast(list[dict[str, Any]], output.get("artifacts", []))
                if isinstance(output, dict)
                else []
            )
            output_bytes = (
                sum(int(item["size_bytes"]) for item in artifacts)
                if artifacts
                else None
            )
            observations[(operator, agent_ids[0])].append(
                (float(execution["operator_latency_ms"]), output_bytes)
            )
    profiles: list[ExecutionCostProfile] = []
    by_operator: dict[str, list[tuple[float, int | None]]] = defaultdict(list)
    for (operator, agent_id), values in sorted(observations.items()):
        by_operator[operator].extend(values)
        output_values = [item[1] for item in values if item[1] is not None]
        profiles.append(
            ExecutionCostProfile(
                operator=operator,
                agent_id=agent_id,
                unit_kind="fixed",
                estimated_output_bytes=(
                    int(median(output_values)) if output_values else None
                ),
                service_latency_ms=median(item[0] for item in values),
                source="frozen-blind-baseline-observation-median",
            )
        )
    for operator, values in sorted(by_operator.items()):
        output_values = [item[1] for item in values if item[1] is not None]
        profiles.append(
            ExecutionCostProfile(
                operator=operator,
                agent_id="*",
                unit_kind="fixed",
                estimated_output_bytes=(
                    int(median(output_values)) if output_values else None
                ),
                service_latency_ms=median(item[0] for item in values),
                source="frozen-blind-baseline-cross-agent-median",
            )
        )
    return tuple(profiles)


def _profiles(
    config: dict[str, Any], source_evidence: Path
) -> tuple[ExecutionCostProfile, ...]:
    configured = tuple(
        ExecutionCostProfile.model_validate(item)
        for item in config["cost_model"]["model_profiles"]
    )
    return (*configured, *_observed_operator_profiles(source_evidence))


def _capture(capture: CapturingBackend) -> dict[str, Any] | None:
    if not capture.requests:
        return None
    if not (
        len(capture.requests)
        == len(capture.completions)
        == len(capture.wall_latency_ms)
        == 1
    ):
        raise RuntimeError("each planner stage permits exactly one model call")
    prompt = capture.requests[0].prompt
    leakage = base._private_structural_leakage(prompt)
    if leakage:
        raise RuntimeError(f"private fields leaked into infra-aware prompt: {leakage}")
    return {
        "request": capture.requests[0].model_dump(mode="json"),
        "completion": capture.completions[0].model_dump(mode="json"),
        "wall_latency_ms": capture.wall_latency_ms[0],
    }


def _costs(
    result: PersistedWorkflowRunResult,
    provider: LiveCostViewProvider,
) -> dict[str, Any]:
    if result.plan is None or not provider.planning_evaluators:
        return {}
    initial_plan = (
        result.replanning.versions[0].plan
        if result.replanning is not None and result.replanning.versions
        else result.plan
    )
    initial = provider.planning_evaluators[0].estimate(initial_plan, provider.task)
    payload: dict[str, Any] = {"g0": initial.model_dump(mode="json")}
    if provider.replan_views and provider.replan_evaluators and provider.replan_contexts:
        guidance = provider.replan_views[-1].cost_guidance
        context = provider.replan_contexts[-1]
        future_ids = tuple(
            item.node_id
            for item in result.plan.nodes
            if item.node_id not in set(context.completed_node_ids)
        )
        final = provider.replan_evaluators[-1].estimate(
            result.plan,
            provider.task,
            node_ids=future_ids,
        )
        current = guidance.current_plan_cost if guidance is not None else None
        payload.update(
            {
                "checkpoint_current_pending": (
                    current.model_dump(mode="json") if current is not None else None
                ),
                "checkpoint_final_pending": final.model_dump(mode="json"),
                "predicted_delta": (
                    {
                        "critical_path_ms": (
                            final.predicted_critical_path_ms
                            - current.predicted_critical_path_ms
                        ),
                        "transfer_bytes": (
                            final.predicted_transfer_bytes
                            - current.predicted_transfer_bytes
                        ),
                        "transfer_latency_ms": (
                            final.predicted_transfer_latency_ms
                            - current.predicted_transfer_latency_ms
                        ),
                    }
                    if current is not None
                    else None
                ),
            }
        )
    return payload


def _audit(
    label: str,
    regime_id: str,
    bandwidth_mbps: float,
    result: PersistedWorkflowRunResult,
    planner_capture: CapturingBackend,
    replanner_capture: CapturingBackend,
    planner: LLMInfrastructureAwareWorkflowPlanner,
    provider: LiveCostViewProvider,
) -> dict[str, Any]:
    workflow = result.workflow
    records = workflow.records if workflow is not None else ()
    transfers = [
        transfer
        for record in records
        if record.execution is not None
        for transfer in record.execution.transfers
    ]
    versions = result.replanning.versions if result.replanning is not None else ()
    revisions = result.replanning.revisions if result.replanning is not None else ()
    model_calls = {
        record.node_id: record.execution.model_telemetry.model_dump(mode="json")
        for record in records
        if record.execution is not None
        and record.execution.model_telemetry is not None
    }
    operator_latency = {
        record.node_id: record.execution.operator_latency_ms
        for record in records
        if record.execution is not None
    }
    return {
        "task": label,
        "regime": regime_id,
        "bandwidth_mbps": bandwidth_mbps,
        "g0_sha256": (
            versions[0].canonical_sha256
            if versions
            else (_canonical_hash(result.plan.model_dump(mode="json")) if result.plan else None)
        ),
        "g_final_sha256": (
            _canonical_hash(result.plan.model_dump(mode="json")) if result.plan else None
        ),
        "workflow_versions": [item.model_dump(mode="json") for item in versions],
        "workflow_revisions": [item.model_dump(mode="json") for item in revisions],
        "predicted_cost": _costs(result, provider),
        "planner": _capture(planner_capture),
        "replanner": _capture(replanner_capture),
        "planner_infrastructure_views": [
            item.model_dump(mode="json") for item in planner.observed_views
        ],
        "replanner_infrastructure_views": [
            item.model_dump(mode="json") for item in provider.replan_views
        ],
        "operator_placements": {
            record.node_id: list(record.execution.agent_ids)
            for record in records
            if record.execution is not None
        },
        "information_movement": [item.model_dump(mode="json") for item in transfers],
        "transfer_bytes": sum(item.bytes_transferred for item in transfers),
        "transfer_time_ms": sum(item.duration_ms for item in transfers),
        "operator_latency_ms": operator_latency,
        "model_telemetry": model_calls,
        "planner_latency_ms": (
            result.telemetry.planner.latency_ms if result.telemetry is not None else None
        ),
        "replanner_latency_ms": (
            replanner_capture.wall_latency_ms[0]
            if replanner_capture.wall_latency_ms
            else None
        ),
        "workflow_latency_ms": (
            workflow.telemetry.e2e_latency_ms if workflow is not None else None
        ),
        "critical_path_latency_ms": (
            workflow.telemetry.critical_path_latency_ms if workflow is not None else None
        ),
        "parallel_overlap_ms": (
            workflow.telemetry.parallel_overlap_ms if workflow is not None else None
        ),
        "e2e_latency_ms": result.runner_e2e_latency_ms,
        "execution_completed": result.execution_completed,
        "format_valid": result.evaluation.format_valid if result.evaluation else None,
        "benchmark_score": (
            result.evaluation.benchmark_score if result.evaluation else None
        ),
        "terminal_answer": result.final_answer,
        "failure": result.failure.model_dump(mode="json") if result.failure else None,
        "trace_path": result.trace_path,
        "trace_sha256": _sha256(Path(result.trace_path)),
    }


def _freeze(
    config: dict[str, Any],
    source_evidence: Path,
    bundles: dict[str, AdaptationBundle],
    profiles: tuple[ExecutionCostProfile, ...],
    output: Path,
) -> None:
    final = cast(
        dict[str, Any],
        json.loads(
            (source_evidence / "freeze/blind-baseline-final.json").read_text("utf-8")
        ),
    )
    if final["status"] != config["source_baseline_status"]:
        raise RuntimeError("source Blind baseline is not frozen")
    task_status = {str(item["task"]): item for item in final["tasks"]}
    payload = {
        "experiment_id": config["experiment_id"],
        "substrate_revision": config["substrate_revision"],
        "source_baseline_final_sha256": _sha256(
            source_evidence / "freeze/blind-baseline-final.json"
        ),
        "source_baseline_manifest_sha256": _sha256(
            source_evidence / "freeze/manifest.json"
        ),
        "semantic_contract": "frozen; no semantic prompt or action-space tuning",
        "workflow_candidates": "none; Planner/Replanner generate arbitrary valid DAGs",
        "network_regimes": config["network"],
        "tasks": {
            label: {
                "task_id": bundle.execution.task.task_id,
                "blind_status": task_status[label],
                "artifacts": [
                    {
                        "artifact_id": item.spec.artifact_id,
                        "size_bytes": item.spec.size_bytes,
                        "sha256": item.sha256_hex,
                    }
                    for item in bundle.prepared_artifacts
                ],
            }
            for label, bundle in bundles.items()
        },
        "cost_profiles": [item.model_dump(mode="json") for item in profiles],
        "implementation_sha256": {
            str(path.relative_to(REPO)): _sha256(path)
            for path in (
                Path(__file__).resolve(),
                REPO / "src/infra_joint/workflow/costing.py",
                REPO / "src/infra_joint/workflow/planner.py",
                REPO / "src/infra_joint/workflow/replanning.py",
                REPO / "src/infra_joint/workflow/orchestrator.py",
                REPO / "src/infra_joint/workflow/runner.py",
            )
        },
    }
    base._write_json(output / "freeze/manifest.json", payload)


async def run(args: argparse.Namespace) -> None:
    config = base._yaml(args.config)
    _assert_controller(config)
    source_config = base._yaml(REPO / str(config["source_baseline_config"]))
    bundles = _load_bundles(config, args.source_evidence, args)
    profiles = _profiles(config, args.source_evidence)
    regimes = cast(list[dict[str, Any]], config["network"]["regimes"])
    schedule = [
        (label, str(regime["id"]), float(regime["bandwidth_mbps"]))
        for label in bundles
        for regime in regimes
    ]
    if args.validate_only:
        print(
            json.dumps(
                {
                    "controller_hostname": socket.gethostname(),
                    "task_count": len(bundles),
                    "expected_runs": len(schedule),
                    "tasks": {
                        label: {
                            "task_id": bundle.execution.task.task_id,
                            "artifacts": {
                                item.spec.artifact_id: {
                                    "size_bytes": item.spec.size_bytes,
                                    "sha256": item.sha256_hex,
                                }
                                for item in bundle.prepared_artifacts
                            },
                        }
                        for label, bundle in bundles.items()
                    },
                    "cost_profile_count": len(profiles),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return
    if args.output.exists():
        if not args.resume:
            raise RuntimeError("output exists; refusing overwrite or implicit retry")
        manifest = cast(
            dict[str, Any],
            json.loads((args.output / "matrix-manifest.json").read_text("utf-8")),
        )
    else:
        _freeze(config, args.source_evidence, bundles, profiles, args.output)
        manifest = {
            "experiment_id": config["experiment_id"],
            "expected_runs": len(schedule),
            "completed_runs": [],
            "n": 1,
            "retry": False,
            "replacement": False,
            "stopped_on_confounder": None,
        }
        base._write_json(args.output / "matrix-manifest.json", manifest)
    completed = {str(item["run_id"]) for item in manifest["completed_runs"]}
    registry = build_operator_catalog()
    operations = tuple(str(item) for item in config["planner"]["available_operations"])
    max_agents = int(config["planner"]["max_agents"])
    endpoints, ports = _tc_surface()
    planner_config = load_planner_config(REPO / str(config["planner"]["config"]))
    _load_key(args.api_key_file)
    backend, planner_client = build_model_backend(planner_config.model)
    try:
        async with AsyncExitStack() as stack:
            clients = await base._configured_clients(stack, source_config)
            for index, (label, regime_id, bandwidth) in enumerate(schedule, start=1):
                run_id = f"{index:02d}-{label}-{regime_id}-infra-aware-open"
                if args.only_run_id is not None and run_id != args.only_run_id:
                    continue
                if run_id in completed:
                    continue
                bundle = bundles[label]
                environment = _regime_environment(
                    source_config,
                    label,
                    bundle,
                    bandwidth,
                    float(config["network"]["added_rtt_ms"]),
                )
                initial_ids = tuple(
                    item.spec.artifact_id for item in bundle.prepared_artifacts
                )
                await base._delete_artifacts(clients, initial_ids)
                await base._preload(
                    source_config,
                    label,
                    bundle,
                    clients,
                    remove_existing=False,
                )
                await base._assert_placement(source_config, label, bundle, clients)
                await validate_worker_surfaces(environment, registry, clients)
                provider = LiveCostViewProvider(
                    bundle.execution.task,
                    environment,
                    clients,
                    profiles,
                    registry,
                )
                planner_capture = CapturingBackend(backend)
                replanner_capture = CapturingBackend(backend)
                planner = LLMInfrastructureAwareWorkflowPlanner(
                    planner_capture,
                    registry,
                    environment,
                    provider,
                )
                replanner = LLMInfrastructureAwareWorkflowReplanner(
                    replanner_capture,
                    registry,
                    environment,
                    provider,
                )
                runner_config = RunnerConfig(
                    environment=environment,
                    worker_urls=cast(
                        dict[str, str], base._infrastructure(source_config)["worker_urls"]
                    ),
                    planner=planner_config,
                    output_root=args.output / "runs",
                    http_timeout_seconds=1800,
                )
                tc_regime = TcRegime(
                    configuration_id=f"open-infra-v1-{run_id}",
                    bandwidth_mbps=bandwidth,
                    added_rtt_ms=float(config["network"]["added_rtt_ms"]),
                    worker_ports=ports,
                )
                controller = (
                    None
                    if args.external_tc
                    else TcController(SshCommandRunner(command_timeout_seconds=120))
                )
                result: PersistedWorkflowRunResult | None = None
                metadata: dict[str, Any] = {
                    "run_id": run_id,
                    "task": label,
                    "regime": regime_id,
                    "bandwidth_mbps": bandwidth,
                    "tc_cleanup_error": None,
                    "artifact_cleanup_error": None,
                    "tc_control": "external" if args.external_tc else "in_process",
                }
                confounder: Exception | None = None
                try:
                    if controller is not None:
                        await controller.apply(
                            tuple(
                                build_tc_command_plan(item, tc_regime)
                                for item in endpoints
                            )
                        )
                    result = await PrepositionedWorkflowRunner(
                        runner_config,
                        base._workload(bundle, environment, operations, max_agents),
                        LocalityAwareMyopicScheduler(),
                        worker_clients=clients,
                        planner=planner,
                        replanner=replanner,
                    ).run(bundle, run_id=run_id)
                    audit = _audit(
                        label,
                        regime_id,
                        bandwidth,
                        result,
                        planner_capture,
                        replanner_capture,
                        planner,
                        provider,
                    )
                    base._write_json(args.output / "runs" / run_id / "audit.json", audit)
                    metadata["audit"] = audit
                    if result.failure is not None and result.failure.code not in {
                        "workflow_plan_invalid",
                        "workflow_replan_invalid",
                    }:
                        confounder = RuntimeError(
                            f"system/runtime failure: {result.failure.model_dump(mode='json')}"
                        )
                except Exception as exc:  # fail closed on harness defects
                    confounder = exc
                    metadata["error"] = f"{type(exc).__name__}: {exc}"
                finally:
                    if controller is not None:
                        try:
                            metadata["tc_class_statistics"] = {
                                endpoint.agent_id: await SshCommandRunner(
                                    command_timeout_seconds=120
                                ).run(
                                    endpoint.ssh_target,
                                    (
                                        "sudo",
                                        "-n",
                                        "tc",
                                        "-s",
                                        "class",
                                        "show",
                                        "dev",
                                        endpoint.interface,
                                    ),
                                )
                                for endpoint in endpoints
                            }
                        except Exception as exc:
                            metadata["tc_statistics_error"] = (
                                f"{type(exc).__name__}: {exc}"
                            )
                            confounder = confounder or exc
                        try:
                            await controller.cleanup()
                        except Exception as exc:
                            metadata["tc_cleanup_error"] = (
                                f"{type(exc).__name__}: {exc}"
                            )
                            confounder = confounder or exc
                    try:
                        generated = (
                            base._generated_ids(result.plan)
                            if result is not None and result.plan is not None
                            else ()
                        )
                        await base._delete_artifacts(
                            clients,
                            tuple(dict.fromkeys((*initial_ids, *generated))),
                        )
                    except Exception as exc:
                        metadata["artifact_cleanup_error"] = f"{type(exc).__name__}: {exc}"
                        confounder = confounder or exc
                base._write_json(
                    args.output / "runs" / run_id / "experiment-metadata.json",
                    metadata,
                )
                manifest["completed_runs"].append(
                    {
                        "run_id": run_id,
                        "task": label,
                        "regime": regime_id,
                        "bandwidth_mbps": bandwidth,
                        "execution_completed": (
                            result.execution_completed if result is not None else False
                        ),
                        "failure": (
                            result.failure.model_dump(mode="json")
                            if result is not None and result.failure is not None
                            else None
                        ),
                    }
                )
                if confounder is not None:
                    manifest["stopped_on_confounder"] = run_id
                base._write_json(args.output / "matrix-manifest.json", manifest)
                if confounder is not None:
                    raise RuntimeError(
                        f"matrix stopped fail-closed at {run_id}: {confounder}"
                    ) from confounder
    finally:
        if planner_client is not None:
            await planner_client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source-evidence", type=Path, required=True)
    parser.add_argument("--api-key-file", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--video-sources", type=Path, required=True)
    parser.add_argument("--longbench-samples", type=Path, required=True)
    parser.add_argument("--multihop-corpus", type=Path, required=True)
    parser.add_argument("--multihop-queries", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--only-run-id")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--external-tc", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
