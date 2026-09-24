"""Run the bounded resource-blind versus infra-aware replanning preliminary."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from contextlib import AsyncExitStack
from pathlib import Path
from time import perf_counter
from typing import Any, cast

from blind_baseline_6task_v1 import (
    REPO,
    _assert_placement,
    _configured_clients,
    _delete_artifacts,
    _environment,
    _generated_ids,
    _infrastructure,
    _load_longbench_samples,
    _load_plan,
    _longbench_multidoc_bundle,
    _multihop_bundle,
    _preload,
    _workload,
    _write_json,
    _yaml,
)
from open_ended_mas_preliminary_v1 import (
    PrepositionedWorkflowRunner,
    _canonical_hash,
    _load_key,
)

from infra_joint.benchmarks.base import (
    AdaptationBundle,
    AdaptedExecutionCase,
    PreparedArtifact,
    PrivateChoiceEvaluation,
    TransformationRecord,
    ValidityAssessment,
)
from infra_joint.config import RunnerConfig, build_model_backend, load_planner_config
from infra_joint.core.state import (
    EnvironmentSpec,
    InfrastructureState,
    LinkSpec,
)
from infra_joint.core.task import TaskContract
from infra_joint.heterogeneous.traffic_control import (
    SshCommandRunner,
    TcController,
    TcEndpoint,
    TcRegime,
    build_tc_command_plan,
)
from infra_joint.infrastructure.observer import LiveWorkerObserver
from infra_joint.infrastructure.validation import validate_worker_surfaces
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.planning.planner import CompletionBackend, logical_task_payload
from infra_joint.runtime.client import WorkerClient
from infra_joint.worker.model_backend import ModelCompletion, ModelRequest
from infra_joint.workflow.planner import ScriptedWorkflowPlanner
from infra_joint.workflow.replanning import (
    ExecutionCostProfile,
    InfrastructureReplanView,
    LLMInfrastructureAwareWorkflowReplanner,
    LLMWorkflowReplanner,
    TransferCostEstimate,
    WorkflowReplanContext,
)
from infra_joint.workflow.runner import PersistedWorkflowRunResult
from infra_joint.workflow.scheduler import LocalityAwareMyopicScheduler

DEFAULT_CONFIG = REPO / "configs/experiments/infra-aware-replanning-preliminary-v1.yaml"
DEFAULT_KEY = REPO.parent / "api_key.txt"
DEFAULT_OUTPUT = REPO / "results/infra-aware-replanning-preliminary-v1"
TC_ENDPOINT_CONFIG = REPO / "configs/local/heterogeneous-v1-preflight.yaml"
TC_PORT_CONFIG = REPO / "configs/local/heterogeneous-v1.yaml"


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


class LiveInfrastructureViewProvider:
    def __init__(
        self,
        environment: EnvironmentSpec,
        clients: dict[str, WorkerClient],
        profiles: tuple[ExecutionCostProfile, ...],
    ) -> None:
        self._environment = environment
        self._observer = LiveWorkerObserver(environment, clients)
        self._profiles = profiles

    async def observe(
        self,
        context: WorkflowReplanContext,
    ) -> InfrastructureReplanView:
        raw = await self._observer.observe()
        relevant = {
            artifact_id
            for node in context.current_plan.nodes
            for artifact_id in (*node.inputs, *node.outputs)
        }
        state = raw.model_copy(
            update={
                "artifacts": tuple(
                    item for item in raw.artifacts if item.artifact_id in relevant
                )
            }
        )
        estimates = self._transfer_estimates(context, state)
        return InfrastructureReplanView(
            environment=self._environment,
            state=state,
            relevant_artifact_ids=tuple(sorted(relevant)),
            pending_transfer_estimates=estimates,
            execution_cost_profiles=self._profiles,
        )

    def _transfer_estimates(
        self,
        context: WorkflowReplanContext,
        state: InfrastructureState,
    ) -> tuple[TransferCostEstimate, ...]:
        nodes = {item.node_id: item for item in context.current_plan.nodes}
        artifacts = {item.artifact_id: item for item in state.artifacts}
        links = {
            (item.source_agent_id, item.target_agent_id): item
            for item in state.links
            if item.available
        }
        deployments = {
            item.deployment_id: item for item in self._environment.deployments
        }
        estimates: list[TransferCostEstimate] = []
        for node_id in context.pending_node_ids:
            node = nodes[node_id]
            if node.operator != "invoke_model":
                continue
            targets = sorted({item.agent_id for item in deployments.values()})
            for target in targets:
                available_inputs = [
                    artifacts[item] for item in node.inputs if item in artifacts
                ]
                if len(available_inputs) != len(node.inputs):
                    continue
                transfer_bytes = 0
                latency_ms = 0.0
                unknown = False
                for artifact in available_inputs:
                    if target in artifact.locations:
                        continue
                    candidates: list[float] = []
                    for source in artifact.locations:
                        link = links.get((source, target))
                        if (
                            link is None
                            or link.bandwidth_mbps is None
                            or link.rtt_ms is None
                            or artifact.size_bytes is None
                        ):
                            continue
                        candidates.append(
                            link.rtt_ms
                            + artifact.size_bytes
                            * 8
                            / (link.bandwidth_mbps * 1_000_000)
                            * 1000
                        )
                    if not candidates:
                        unknown = True
                        continue
                    transfer_bytes += artifact.size_bytes or 0
                    latency_ms += min(candidates)
                estimates.append(
                    TransferCostEstimate(
                        node_id=node_id,
                        target_agent_id=target,
                        artifact_ids=tuple(node.inputs),
                        transfer_bytes=transfer_bytes,
                        estimated_latency_ms=None if unknown else latency_ms,
                        basis=(
                            "current artifact locations plus configured bandwidth/RTT; "
                            "unknown when no measured path exists"
                        ),
                    )
                )
        return tuple(estimates)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _source_rows(source_config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item["label"]): cast(dict[str, Any], item)
        for item in cast(list[dict[str, Any]], source_config["dataset"]["tasks"])
    }


def _video_bundle_from_freeze(
    source_evidence: Path,
    source_manifest: dict[str, Any],
    video_source: Path,
) -> AdaptationBundle:
    label = "video-long-payload"
    task = TaskContract.model_validate_json(
        (source_evidence / "private" / label / "task-contract.json").read_text("utf-8")
    )
    private = PrivateChoiceEvaluation.model_validate_json(
        (source_evidence / "private" / label / "private-evaluation.json").read_text(
            "utf-8"
        )
    )
    provenance = cast(
        dict[str, Any], source_manifest["tasks"][label]["adaptation_provenance"]
    )
    execution = AdaptedExecutionCase(
        task=task,
        transformations=tuple(
            TransformationRecord.model_validate(item)
            for item in cast(list[dict[str, Any]], provenance["transformations"])
        ),
        validity=ValidityAssessment.model_validate(provenance["validity"]),
    )
    content = video_source.read_bytes()
    prepared = PreparedArtifact.create(task.artifacts[0], content)
    expected = cast(
        list[dict[str, Any]], source_manifest["tasks"][label]["artifacts"]
    )[0]
    if prepared.sha256_hex != expected["sha256"]:
        raise RuntimeError("Video-MME source hash differs from the frozen baseline")
    return AdaptationBundle(execution, private, (prepared,))


def _load_bundles(
    config: dict[str, Any],
    source_evidence: Path,
    video_source: Path,
    longbench_samples: Path,
    multihop_corpus: Path,
    multihop_queries: Path,
) -> dict[str, AdaptationBundle]:
    source_config = _yaml(REPO / str(config["source_baseline_config"]))
    rows = _source_rows(source_config)
    revisions = cast(dict[str, str], source_config["dataset"]["revisions"])
    source_manifest = cast(
        dict[str, Any],
        json.loads((source_evidence / "freeze/manifest.json").read_text("utf-8")),
    )
    long_row = rows["longbench-multidoc"]
    long_id = str(long_row["source_task_id"])
    long_sample = _load_longbench_samples(longbench_samples, {long_id})[long_id]
    corpus_rows = cast(
        list[dict[str, Any]], json.loads(multihop_corpus.read_text("utf-8"))
    )
    query_rows = cast(
        list[dict[str, Any]], json.loads(multihop_queries.read_text("utf-8"))
    )
    bundles = {
        "video-long-payload": _video_bundle_from_freeze(
            source_evidence, source_manifest, video_source
        ),
        "longbench-multidoc": _longbench_multidoc_bundle(
            long_sample,
            revisions["longbench_v2"],
            tuple(int(value) for value in long_row["boundary_lines"]),
        ),
        "multihop-multisource": _multihop_bundle(
            rows["multihop-multisource"],
            corpus_rows,
            query_rows,
            revisions["multihop_rag"],
        ),
    }
    expected = {str(item["label"]) for item in config["tasks"]}
    if set(bundles) != expected:
        raise RuntimeError("loaded tasks differ from the frozen preliminary matrix")
    for label, bundle in bundles.items():
        frozen = cast(dict[str, Any], source_manifest["tasks"][label])
        expected_artifacts = {
            str(item["artifact_id"]): item
            for item in cast(list[dict[str, Any]], frozen["artifacts"])
        }
        actual_artifacts = {
            item.spec.artifact_id: {
                "size_bytes": item.spec.size_bytes,
                "sha256": item.sha256_hex,
            }
            for item in bundle.prepared_artifacts
        }
        if actual_artifacts != {
            artifact_id: {
                "size_bytes": int(item["size_bytes"]),
                "sha256": str(item["sha256"]),
            }
            for artifact_id, item in expected_artifacts.items()
        }:
            raise RuntimeError(f"prepared artifact drift from frozen baseline: {label}")
        if bundle.execution.task.task_id != frozen["task_id"]:
            raise RuntimeError(f"task identity drift from frozen baseline: {label}")
    return bundles


def _regime_environment(
    source_config: dict[str, Any],
    label: str,
    bundle: AdaptationBundle,
    bandwidth_mbps: float,
    added_rtt_ms: float,
) -> EnvironmentSpec:
    base = _environment(source_config, label, bundle)
    agent_ids = tuple(item.agent_id for item in base.agents)
    links = tuple(
        LinkSpec(
            source_agent_id=source,
            target_agent_id=target,
            bandwidth_mbps=bandwidth_mbps,
            rtt_ms=added_rtt_ms,
        )
        for source in agent_ids
        for target in agent_ids
        if source != target
    )
    return base.model_copy(update={"links": links})


def _tc_surface() -> tuple[tuple[TcEndpoint, ...], tuple[int, ...]]:
    raw = _yaml(TC_ENDPOINT_CONFIG)
    endpoints = tuple(TcEndpoint.model_validate(item) for item in raw["tc_endpoints"])
    addresses = {item.agent_id: item.address for item in endpoints}
    all_paths = tuple(
        item.model_copy(
            update={
                "peer_addresses": tuple(
                    value
                    for agent_id, value in sorted(addresses.items())
                    if agent_id != item.agent_id
                )
            }
        )
        for item in endpoints
    )
    ports = tuple(int(item) for item in _yaml(TC_PORT_CONFIG)["worker_ports"])
    return all_paths, ports


def _freeze(
    args: argparse.Namespace,
    config: dict[str, Any],
    bundles: dict[str, AdaptationBundle],
) -> None:
    freeze_root = args.output / "freeze"
    freeze_root.mkdir(parents=True, exist_ok=False)
    source_manifest = json.loads(
        (args.source_evidence / "freeze/manifest.json").read_text("utf-8")
    )
    manifest: dict[str, Any] = {
        "experiment_id": config["experiment_id"],
        "source_evidence": str(args.source_evidence),
        "source_manifest_sha256": _sha256(
            args.source_evidence / "freeze/manifest.json"
        ),
        "config_sha256": _sha256(args.config),
        "checkpoint": config["execution"]["replan_checkpoint"],
        "max_replans": config["execution"]["max_replans"],
        "tasks": {},
    }
    for item in config["tasks"]:
        label = str(item["label"])
        plan = _load_plan(args.source_evidence, label)
        expected_hash = str(source_manifest["tasks"][label]["workflow_plan_sha256"])
        actual_hash = _canonical_hash(plan.model_dump(mode="json"))
        if actual_hash != expected_hash:
            raise RuntimeError(f"source G0 hash drift: {label}")
        task_root = freeze_root / label
        _write_json(task_root / "workflow-plan-g0.json", plan.model_dump(mode="json"))
        _write_json(
            task_root / "task-public.json",
            logical_task_payload(bundles[label].execution.task),
        )
        manifest["tasks"][label] = {
            "g0_sha256": actual_hash,
            "task_id": bundles[label].execution.task.task_id,
            "benchmark_id": bundles[label].execution.task.benchmark_id,
            "initial_placement": source_manifest["tasks"][label][
                "initial_artifact_placement"
            ],
            "artifacts": source_manifest["tasks"][label]["artifacts"],
        }
    _write_json(freeze_root / "manifest.json", manifest)


def _execution_profiles(config: dict[str, Any]) -> tuple[ExecutionCostProfile, ...]:
    return tuple(
        ExecutionCostProfile.model_validate(item)
        for item in config["execution_cost_profiles"]
    )


def _replanner_call(capture: CapturingBackend) -> dict[str, Any]:
    if len(capture.requests) != 1 or len(capture.completions) != 1:
        raise RuntimeError("each matrix cell must make exactly one replanner call")
    return {
        "request": capture.requests[0].model_dump(mode="json"),
        "completion": capture.completions[0].model_dump(mode="json"),
        "wall_latency_ms": capture.wall_latency_ms[0],
    }


def _audit(
    label: str,
    arm: str,
    regime: str,
    bandwidth: float,
    result: PersistedWorkflowRunResult,
    capture: CapturingBackend,
    aware_views: list[InfrastructureReplanView],
) -> dict[str, Any]:
    workflow = result.workflow
    replanning = result.replanning
    records = workflow.records if workflow is not None else ()
    transfers = [
        transfer
        for record in records
        if record.execution is not None
        for transfer in record.execution.transfers
    ]
    placements = {
        record.node_id: list(record.execution.agent_ids)
        for record in records
        if record.execution is not None
    }
    operator_latency = {
        record.node_id: record.execution.operator_latency_ms
        for record in records
        if record.execution is not None
    }
    model_latency = {
        record.node_id: record.execution.model_telemetry.model_dump(mode="json")
        for record in records
        if record.execution is not None
        and record.execution.model_telemetry is not None
    }
    return {
        "task": label,
        "arm": arm,
        "regime": regime,
        "bandwidth_mbps": bandwidth,
        "execution_valid": bool(
            result.execution_completed
            and workflow is not None
            and workflow.completed
            and result.evaluation is not None
            and result.evaluation.format_valid
        ),
        "versions": (
            [item.model_dump(mode="json") for item in replanning.versions]
            if replanning is not None
            else []
        ),
        "revisions": (
            [item.model_dump(mode="json") for item in replanning.revisions]
            if replanning is not None
            else []
        ),
        "final_plan_sha256": (
            _canonical_hash(result.plan.model_dump(mode="json"))
            if result.plan is not None
            else None
        ),
        "operator_placements": placements,
        "transfers": [item.model_dump(mode="json") for item in transfers],
        "transfer_bytes": sum(item.bytes_transferred for item in transfers),
        "transfer_time_ms": sum(item.duration_ms for item in transfers),
        "operator_latency_ms": operator_latency,
        "model_telemetry": model_latency,
        "workflow_planner_overhead_ms": (
            result.telemetry.planner.latency_ms if result.telemetry is not None else None
        ),
        "replanner_wall_latency_ms": capture.wall_latency_ms[0],
        "replanner_model_telemetry": capture.completions[0].telemetry.model_dump(
            mode="json"
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
        "benchmark_score": (
            result.evaluation.benchmark_score if result.evaluation is not None else None
        ),
        "format_valid": (
            result.evaluation.format_valid if result.evaluation is not None else None
        ),
        "terminal_answer": result.final_answer,
        "failure": result.failure.model_dump(mode="json") if result.failure else None,
        "infra_views": [item.model_dump(mode="json") for item in aware_views],
        "trace_path": result.trace_path,
        "trace_sha256": _sha256(Path(result.trace_path)),
    }


async def run(args: argparse.Namespace) -> None:
    config = _yaml(args.config)
    source_config = _yaml(REPO / str(config["source_baseline_config"]))
    bundles = _load_bundles(
        config,
        args.source_evidence,
        args.video_source,
        args.longbench_samples,
        args.multihop_corpus,
        args.multihop_queries,
    )
    if args.validate_only:
        source_manifest = json.loads(
            (args.source_evidence / "freeze/manifest.json").read_text("utf-8")
        )
        validation = {
            "tasks": {
                label: {
                    "task_id": bundle.execution.task.task_id,
                    "artifact_sha256": {
                        item.spec.artifact_id: item.sha256_hex
                        for item in bundle.prepared_artifacts
                    },
                    "g0_sha256": _canonical_hash(
                        _load_plan(args.source_evidence, label).model_dump(mode="json")
                    ),
                    "expected_g0_sha256": source_manifest["tasks"][label][
                        "workflow_plan_sha256"
                    ],
                }
                for label, bundle in bundles.items()
            }
        }
        print(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if args.output.exists():
        if not args.resume_matrix:
            raise RuntimeError("output exists; refusing retry or overwrite")
        manifest = cast(
            dict[str, Any],
            json.loads((args.output / "matrix-manifest.json").read_text("utf-8")),
        )
    else:
        _freeze(args, config, bundles)
        manifest = {
            "experiment_id": config["experiment_id"],
            "expected_runs": 18,
            "completed_runs": [],
            "stopped_on_confounder": None,
            "n": 1,
            "retry": False,
            "replacement": False,
        }
        _write_json(args.output / "matrix-manifest.json", manifest)
    registry = build_operator_catalog()
    operations = tuple(str(item) for item in config["planner"]["available_operations"])
    max_agents = int(config["planner"]["max_agents"])
    profiles = _execution_profiles(config)
    endpoints, ports = _tc_surface()
    regimes = cast(list[dict[str, Any]], config["network"]["regimes"])
    arms = tuple(str(item) for item in config["arms"])
    task_labels = tuple(str(item["label"]) for item in config["tasks"])
    schedule = [
        (label, cast(str, regime["id"]), float(regime["bandwidth_mbps"]), arm)
        for label in task_labels
        for regime in regimes
        for arm in arms
    ]
    if manifest["expected_runs"] != len(schedule):
        raise RuntimeError("persisted matrix factorization differs from current config")
    if args.preposition_only:
        async with AsyncExitStack() as stack:
            clients = await _configured_clients(stack, source_config)
            for label, bundle in bundles.items():
                plan = _load_plan(args.source_evidence, label)
                environment = _regime_environment(
                    source_config, label, bundle, bandwidth_mbps=30, added_rtt_ms=0
                )
                await validate_worker_surfaces(environment, registry, clients)
                await _delete_artifacts(
                    clients,
                    (
                        *(item.spec.artifact_id for item in bundle.prepared_artifacts),
                        *_generated_ids(plan),
                    ),
                )
                await _preload(
                    source_config,
                    label,
                    bundle,
                    clients,
                    remove_existing=False,
                )
                await _assert_placement(source_config, label, bundle, clients)
        _write_json(
            args.output / "prepositioned-artifacts.json",
            {
                label: {
                    item.spec.artifact_id: {
                        "sha256": item.sha256_hex,
                        "size_bytes": item.spec.size_bytes,
                    }
                    for item in bundle.prepared_artifacts
                }
                for label, bundle in bundles.items()
            },
        )
        return
    _load_key(args.api_key_file)
    planner_config = load_planner_config(REPO / str(config["planner"]["config"]))
    backend, planner_client = build_model_backend(planner_config.model)
    completed_run_ids = {
        str(item["run_id"]) for item in manifest["completed_runs"]
    }
    try:
        async with AsyncExitStack() as stack:
            clients = await _configured_clients(stack, source_config)
            for index, (label, regime_id, bandwidth, arm) in enumerate(
                schedule, start=1
            ):
                run_id = f"{index:02d}-{label}-{regime_id}-{arm}"
                if args.only_run_id is not None and run_id != args.only_run_id:
                    continue
                if run_id in completed_run_ids:
                    raise RuntimeError(f"run outcome exists; retry forbidden: {run_id}")
                bundle = bundles[label]
                plan = _load_plan(args.source_evidence, label)
                environment = _regime_environment(
                    source_config,
                    label,
                    bundle,
                    bandwidth,
                    float(config["network"]["added_rtt_ms"]),
                )
                runner_config = RunnerConfig(
                    environment=environment,
                    worker_urls=cast(
                        dict[str, str], _infrastructure(source_config)["worker_urls"]
                    ),
                    planner=planner_config,
                    output_root=args.output / "runs",
                    http_timeout_seconds=1800,
                )
                capture = CapturingBackend(backend)
                aware = None
                if arm == "resource-blind":
                    replanner = LLMWorkflowReplanner(capture, registry, environment)
                elif arm == "infra-aware":
                    aware = LLMInfrastructureAwareWorkflowReplanner(
                        capture,
                        registry,
                        environment,
                        LiveInfrastructureViewProvider(environment, clients, profiles),
                    )
                    replanner = aware
                else:
                    raise RuntimeError(f"unknown experimental arm: {arm}")
                tc_regime = TcRegime(
                    configuration_id=f"infra-replan-v1-{run_id}",
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
                error: Exception | None = None
                metadata: dict[str, Any] = {
                    "run_id": run_id,
                    "task": label,
                    "regime": regime_id,
                    "bandwidth_mbps": bandwidth,
                    "arm": arm,
                    "tc_cleanup_error": None,
                    "artifact_cleanup_error": None,
                    "tc_control": "external" if args.external_tc else "in_process",
                }
                initial_ids = tuple(
                    item.spec.artifact_id for item in bundle.prepared_artifacts
                )
                await _delete_artifacts(clients, _generated_ids(plan))
                try:
                    if not args.reuse_prepositioned:
                        await _delete_artifacts(clients, initial_ids)
                        await _preload(
                            source_config,
                            label,
                            bundle,
                            clients,
                            remove_existing=False,
                        )
                    await _assert_placement(source_config, label, bundle, clients)
                    if controller is not None:
                        await controller.apply(
                            tuple(
                                build_tc_command_plan(item, tc_regime)
                                for item in endpoints
                            )
                        )
                    await validate_worker_surfaces(environment, registry, clients)
                    result = await PrepositionedWorkflowRunner(
                        runner_config,
                        _workload(bundle, environment, operations, max_agents),
                        LocalityAwareMyopicScheduler(),
                        worker_clients=clients,
                        planner=ScriptedWorkflowPlanner((plan,)),
                        replanner=replanner,
                        replan_pause_before_operators=("invoke_model",),
                    ).run(bundle, run_id=run_id)
                    call = _replanner_call(capture)
                    _write_json(
                        args.output / "runs" / run_id / "replanner-call.json", call
                    )
                    audit = _audit(
                        label,
                        arm,
                        regime_id,
                        bandwidth,
                        result,
                        capture,
                        aware.observed_views if aware is not None else [],
                    )
                    _write_json(args.output / "runs" / run_id / "audit.json", audit)
                    metadata["audit"] = audit
                    if not audit["execution_valid"]:
                        raise RuntimeError(
                            f"invalid runtime/evaluation result: {audit['failure']}"
                        )
                except Exception as exc:  # fail-closed matrix boundary
                    error = exc
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
                            if error is None and any(
                                "class htb 1:20" not in value
                                for value in metadata[
                                    "tc_class_statistics"
                                ].values()
                            ):
                                metadata["tc_statistics_error"] = (
                                    "shaped class 1:20 was absent before cleanup"
                                )
                        except Exception as exc:
                            metadata["tc_statistics_error"] = (
                                f"{type(exc).__name__}: {exc}"
                            )
                        try:
                            await controller.cleanup()
                        except Exception as exc:
                            metadata["tc_cleanup_error"] = (
                                f"{type(exc).__name__}: {exc}"
                            )
                    try:
                        final_plan = result.plan if result and result.plan else plan
                        await _delete_artifacts(
                            clients,
                            tuple(
                                dict.fromkeys(
                                    (
                                        *(() if args.reuse_prepositioned else initial_ids),
                                        *_generated_ids(plan),
                                        *_generated_ids(final_plan),
                                    )
                                )
                            ),
                        )
                    except Exception as exc:
                        metadata["artifact_cleanup_error"] = (
                            f"{type(exc).__name__}: {exc}"
                        )
                _write_json(
                    args.output / "runs" / run_id / "experiment-metadata.json",
                    metadata,
                )
                manifest["completed_runs"].append(
                    {
                        "run_id": run_id,
                        "task": label,
                        "regime": regime_id,
                        "arm": arm,
                        "valid": error is None,
                        "error": metadata.get("error"),
                    }
                )
                if (
                    error is not None
                    or metadata["tc_cleanup_error"] is not None
                    or metadata["artifact_cleanup_error"] is not None
                    or metadata.get("tc_statistics_error") is not None
                ):
                    manifest["stopped_on_confounder"] = run_id
                    _write_json(args.output / "matrix-manifest.json", manifest)
                    raise RuntimeError(f"matrix stopped fail-closed at {run_id}: {metadata}")
                _write_json(args.output / "matrix-manifest.json", manifest)
    finally:
        if planner_client is not None:
            await planner_client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source-evidence", type=Path, required=True)
    parser.add_argument("--video-source", type=Path, required=True)
    parser.add_argument("--longbench-samples", type=Path, required=True)
    parser.add_argument("--multihop-corpus", type=Path, required=True)
    parser.add_argument("--multihop-queries", type=Path, required=True)
    parser.add_argument("--api-key-file", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--preposition-only", action="store_true")
    parser.add_argument("--resume-matrix", action="store_true")
    parser.add_argument("--reuse-prepositioned", action="store_true")
    parser.add_argument("--external-tc", action="store_true")
    parser.add_argument("--only-run-id")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
