"""Execute one audited heterogeneous-v1 controlled placement run.

The fixed semantic DAG and prepositioned source artifacts are v1 sidecars.  The
frozen M4 Worker API, RuntimeExecutor, finalizer, and evaluator are reused.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from contextlib import AsyncExitStack
from pathlib import Path
from time import perf_counter
from typing import Any, Literal, cast

import httpx
import yaml

from infra_joint.benchmarks.base import (
    AdaptationBundle,
    AdaptedExecutionCase,
    PreparedArtifact,
    TransformationRecord,
    assess_validity,
)
from infra_joint.benchmarks.multihop_rag import (
    MULTIHOP_EVALUATOR_ID,
    PrivateMultiHopEvaluation,
)
from infra_joint.config import PlannerConfig, RunnerConfig, load_planner_config
from infra_joint.core.state import (
    AgentSpec,
    ArtifactPlacement,
    DeploymentSpec,
    EnvironmentSpec,
    InfrastructureState,
    LinkSpec,
)
from infra_joint.core.task import ArtifactSpec, OutputContract, OutputFormat, TaskContract
from infra_joint.core.workflow import LogicalAgent, WorkflowEdge, WorkflowNode, WorkflowPlan
from infra_joint.heterogeneous.contracts import (
    EquivalentModelReplicaSet,
    ExperimentMetadata,
    NetworkCalibration,
    NetworkControlMethod,
    PayloadClass,
)
from infra_joint.heterogeneous.scheduler import (
    FixedPrefixScheduler,
    SynthesisStageEstimate,
    SynthesisStageScheduler,
)
from infra_joint.heterogeneous.traffic_control import (
    SshCommandRunner,
    TcController,
    TcEndpoint,
    TcRegime,
    build_tc_command_plan,
)
from infra_joint.heterogeneous.workload import FrozenPayload, SemanticWorkloadManifest
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.runtime.client import HttpWorkerClient, WorkerClient
from infra_joint.runtime.executor import ArtifactTransferTelemetry
from infra_joint.workflow.planner import ScriptedWorkflowPlanner
from infra_joint.workflow.runner import PersistedWorkflowRunResult, WorkflowBenchmarkRunner
from infra_joint.workflow.scheduler import SchedulerDecision, SchedulerKind, WorkflowScheduler
from infra_joint.workflow.workload import AvailableModelInstance, WorkloadArtifact, WorkloadSpec

WORKER_URLS = {
    "A4": "http://192.168.0.104:9104",
    "A5": "http://192.168.0.105:9105",
    "A28": "http://192.168.0.128:9128",
    "strong-4090": "http://192.168.0.12:9212",
}
ARTIFACT_ROOTS = {
    "A4": ("edge@192.168.0.104", "/mnt/ssd/heterogeneous-v1/artifacts/a4"),
    "A5": ("edge@192.168.0.105", "/mnt/ssd/heterogeneous-v1/artifacts/a5"),
    "A28": ("edge@192.168.0.128", "/mnt/ssd/heterogeneous-v1/artifacts/a28"),
    "strong-4090": (
        "super@192.168.0.12",
        "/home/super/heterogeneous-v1/artifacts/strong-4090",
    ),
}
CANONICAL_DEPLOYMENT = "a28-qwen3.8-27b-q4km-v1"
RTX_DEPLOYMENT = "strong-4090-qwen3.8-27b-q4km-v1"
CHECKPOINT_FINGERPRINT = (
    "sha256:b69fef4451445b2d5433388b20b9c03883521ca3f949b656e50d494cb29c2350"
)


class PrepositionedWorkflowRunner(WorkflowBenchmarkRunner):
    """Validate frozen initial placement without re-uploading it per repetition."""

    async def _materialize(
        self,
        bundle: AdaptationBundle,
        worker_clients: dict[str, WorkerClient],
    ) -> tuple[ArtifactTransferTelemetry, ...]:
        specs = {item.artifact_id: item for item in bundle.execution.task.artifacts}
        placements = self._config.environment.initial_placements
        if {item.artifact_id for item in placements} != set(specs):
            raise RuntimeError("prepositioned placements do not exactly cover task artifacts")
        for placement in placements:
            state = await worker_clients[placement.agent_id].get_state()
            artifacts = {item.artifact_id: item for item in state.artifacts}
            observed = artifacts.get(placement.artifact_id)
            expected = specs[placement.artifact_id]
            prepared = next(
                item
                for item in bundle.prepared_artifacts
                if item.spec.artifact_id == placement.artifact_id
            )
            if (
                observed is None
                or observed.media_type != expected.media_type
                or observed.size_bytes != expected.size_bytes
                or observed.sha256_hex != prepared.sha256_hex
            ):
                raise RuntimeError(
                    f"prepositioned artifact mismatch: {placement.agent_id}/"
                    f"{placement.artifact_id}"
                )
        return ()


class TimedScheduler:
    """Measure v1 scheduler wall time without changing scheduler decisions."""

    def __init__(self, delegate: WorkflowScheduler) -> None:
        self._delegate = delegate
        self.samples: list[dict[str, float | str]] = []

    def schedule(
        self,
        node: WorkflowNode,
        logical_agent: LogicalAgent,
        environment: EnvironmentSpec,
        infrastructure: InfrastructureState,
        registry: OperatorRegistry,
    ) -> SchedulerDecision:
        started = perf_counter()
        decision: SchedulerDecision = self._delegate.schedule(
            node, logical_agent, environment, infrastructure, registry
        )
        self.samples.append(
            {
                "node_id": node.node_id,
                "duration_ms": (perf_counter() - started) * 1000,
            }
        )
        return decision


def _read_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("configuration must be a YAML mapping")
    return cast(dict[str, Any], value)


def _load_replica_set(path: Path) -> EquivalentModelReplicaSet:
    raw = _read_yaml(path)
    return EquivalentModelReplicaSet.model_validate(raw["equivalent_replicas"])


def _load_tc_endpoints(path: Path) -> tuple[tuple[TcEndpoint, ...], tuple[int, ...]]:
    raw = _read_yaml(path)
    endpoints = tuple(TcEndpoint.model_validate(item) for item in raw["tc_endpoints"])
    return endpoints, tuple(int(item) for item in raw["worker_ports"])


def _load_calibration(path: Path) -> NetworkCalibration:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return NetworkCalibration.model_validate(raw["calibration"])


def _manifest(path: Path) -> SemanticWorkloadManifest:
    return SemanticWorkloadManifest.model_validate_json(path.read_text(encoding="utf-8"))


def _payload(manifest: SemanticWorkloadManifest, label: str) -> FrozenPayload:
    try:
        return next(item for item in manifest.payloads if item.label == label)
    except StopIteration as exc:
        raise ValueError(f"payload label is absent from manifest: {label}") from exc


def _artifact_specs(
    manifest_path: Path,
    manifest: SemanticWorkloadManifest,
    label: str,
) -> tuple[tuple[ArtifactSpec, ...], tuple[PreparedArtifact, ...]]:
    payload = _payload(manifest, label)
    specs: list[ArtifactSpec] = []
    prepared: list[PreparedArtifact] = []
    for shard in payload.shards:
        content = (manifest_path.parent / shard.path).read_bytes()
        if len(content) != shard.bytes or hashlib.sha256(content).hexdigest() != shard.sha256:
            raise RuntimeError(f"frozen payload checksum mismatch: {shard.path}")
        spec = ArtifactSpec(
            artifact_id=shard.artifact_id,
            logical_type=(
                "derived_semantic_document_corpus;question_independent_payload_axis;"
                "text_field=body"
            ),
            media_type=shard.media_type,
            size_bytes=shard.bytes,
            source_ref=(
                f"local-derived://{manifest.task.task_id}/heterogeneous-v1/{label}/"
                f"{shard.placement_agent}"
            ),
        )
        specs.append(spec)
        prepared.append(PreparedArtifact.create(spec, content))
    return tuple(specs), tuple(prepared)


def _bundle(
    manifest_path: Path,
    manifest: SemanticWorkloadManifest,
    label: str,
) -> AdaptationBundle:
    specs, prepared = _artifact_specs(manifest_path, manifest, label)
    private = json.loads(
        (manifest_path.parent / manifest.private_evaluation.path).read_text(encoding="utf-8")
    )
    task = TaskContract(
        task_id=f"heterogeneous-v1-{manifest.task.task_id}-{label.lower()}",
        benchmark_id="multihop_rag_heterogeneous_controlled_v1",
        objective=manifest.task.query,
        artifacts=specs,
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
        evaluator_id=MULTIHOP_EVALUATOR_ID,
    )
    transformation = TransformationRecord(
        benchmark_id=task.benchmark_id,
        source_revision="71ac0d0bd1f951d2d6b70311f7d2ae404e1ffa82",
        source_task_id=manifest.task.task_id,
        transformation="derived_deterministic_real_document_replication_payload_axis_v1",
        information_preserved=False,
        order_preserved=True,
        gold_independent=True,
        notes=(
            "Controlled systems workload, not a formal benchmark result. Public payloads and "
            "the scripted DAG contain no private evaluator fields."
        ),
        audit={
            "payload_class": label,
            "representation": manifest.representation,
            "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        },
    )
    return AdaptationBundle(
        execution=AdaptedExecutionCase(
            task=task,
            transformations=(transformation,),
            validity=assess_validity(
                (transformation,), query_equivalent=True, evaluator_equivalent=True
            ),
        ),
        private_evaluation=PrivateMultiHopEvaluation(
            task_id=task.task_id,
            gold_answer=str(private["gold_answer"]),
            question_type="comparison_query",
            supporting_evidence=(),
        ),
        prepared_artifacts=prepared,
    )


def _environment(
    bundle: AdaptationBundle,
    manifest: SemanticWorkloadManifest,
    label: str,
    calibration: NetworkCalibration,
) -> EnvironmentSpec:
    payload = _payload(manifest, label)
    transfer = min(
        calibration.artifact_transfers,
        key=lambda item: abs(item.artifact_bytes - payload.actual_bytes),
    )
    capabilities = frozenset(
        {"model", "retrieval", "structured", "media.ffmpeg", "media.image"}
    )
    agents = (
        AgentSpec(agent_id="A4", device="NVIDIA Jetson AGX Orin 32GB", capabilities=capabilities),
        AgentSpec(agent_id="A5", device="NVIDIA Jetson AGX Orin 32GB", capabilities=capabilities),
        AgentSpec(agent_id="A28", device="NVIDIA Jetson AGX Orin 64GB", capabilities=capabilities),
        AgentSpec(
            agent_id="strong-4090",
            device="2x NVIDIA GeForce RTX 4090",
            capabilities=capabilities,
        ),
    )
    deployments = (
        DeploymentSpec(
            deployment_id=CANONICAL_DEPLOYMENT,
            agent_id="A28",
            model_id="qwen3.8-27b-q4km-v1",
            modalities=frozenset({"text", "image"}),
            context_window=16_384,
            reserved_output_tokens=256,
            image_token_cost=2_048,
        ),
        DeploymentSpec(
            deployment_id=RTX_DEPLOYMENT,
            agent_id="strong-4090",
            model_id="qwen3.8-27b-q4km-v1",
            modalities=frozenset({"text", "image"}),
            context_window=16_384,
            reserved_output_tokens=256,
            image_token_cost=2_048,
        ),
    )
    placement_by_artifact = {
        shard.artifact_id: shard.placement_agent for shard in payload.shards
    }
    placements = tuple(
        ArtifactPlacement(
            artifact_id=spec.artifact_id,
            agent_id=placement_by_artifact[spec.artifact_id],
        )
        for spec in bundle.execution.task.artifacts
    )
    links = (
        LinkSpec(source_agent_id="A4", target_agent_id="A28"),
        LinkSpec(source_agent_id="A5", target_agent_id="A28"),
        LinkSpec(
            source_agent_id="A28",
            target_agent_id="strong-4090",
            bandwidth_mbps=transfer.effective_throughput_mbps.median,
            rtt_ms=calibration.median_rtt_ms,
        ),
        LinkSpec(
            source_agent_id="strong-4090",
            target_agent_id="A28",
            bandwidth_mbps=transfer.effective_throughput_mbps.median,
            rtt_ms=calibration.median_rtt_ms,
        ),
    )
    return EnvironmentSpec(
        agents=agents,
        deployments=deployments,
        initial_placements=placements,
        links=links,
    )


def _plan(
    bundle: AdaptationBundle,
    manifest: SemanticWorkloadManifest,
    label: str,
    run_id: str,
) -> WorkflowPlan:
    payload = _payload(manifest, label)
    by_agent = {shard.placement_agent: shard.artifact_id for shard in payload.shards}
    outputs = {
        "a4": f"{run_id}--a4-ranked",
        "a5": f"{run_id}--a5-ranked",
        "package": f"{run_id}--placement-package",
        "ranked": f"{run_id}--ranked-evidence",
        "context": f"{run_id}--context-ready",
    }
    agents = (
        LogicalAgent(
            agent_id="edge-a",
            role="fixed source-A retrieval",
            objective="rank and retain the frozen source-A corpus",
            model_instance_id=CANONICAL_DEPLOYMENT,
            allowed_operations=("bm25_retrieve",),
        ),
        LogicalAgent(
            agent_id="edge-b",
            role="fixed source-B retrieval",
            objective="rank and retain the frozen source-B corpus",
            model_instance_id=CANONICAL_DEPLOYMENT,
            allowed_operations=("bm25_retrieve",),
        ),
        LogicalAgent(
            agent_id="packager",
            role="fixed fan-in packager",
            objective="merge both ranked semantic corpora",
            model_instance_id=CANONICAL_DEPLOYMENT,
            allowed_operations=("aggregate_artifacts",),
        ),
        LogicalAgent(
            agent_id="synthesizer",
            role="equivalent-replica semantic synthesis stage",
            objective="retrieve both sources and synthesize a structured comparison",
            model_instance_id=CANONICAL_DEPLOYMENT,
            allowed_operations=("bm25_retrieve", "select_fields", "invoke_model"),
        ),
    )
    query = bundle.execution.task.objective
    nodes = (
        WorkflowNode(
            node_id="a4-local-retrieve-reduce",
            agent_id="edge-a",
            operator="bm25_retrieve",
            inputs=(by_agent["A4"],),
            outputs=(outputs["a4"],),
            arguments={
                "query": query,
                "text_field": "body",
                "top_k": 100_000,
                "output_artifact_id": outputs["a4"],
            },
        ),
        WorkflowNode(
            node_id="a5-local-retrieve-reduce",
            agent_id="edge-b",
            operator="bm25_retrieve",
            inputs=(by_agent["A5"],),
            outputs=(outputs["a5"],),
            arguments={
                "query": query,
                "text_field": "body",
                "top_k": 100_000,
                "output_artifact_id": outputs["a5"],
            },
        ),
        WorkflowNode(
            node_id="a28-merge-package",
            agent_id="packager",
            operator="aggregate_artifacts",
            inputs=(outputs["a4"], outputs["a5"]),
            outputs=(outputs["package"],),
            arguments={"output_artifact_id": outputs["package"]},
        ),
        WorkflowNode(
            node_id="a28-placement-group-bm25-reduce",
            agent_id="synthesizer",
            operator="bm25_retrieve",
            inputs=(outputs["package"],),
            outputs=(outputs["ranked"],),
            arguments={
                "query": query,
                "text_field": "retrieval_text",
                "top_k": 2,
                "output_artifact_id": outputs["ranked"],
            },
        ),
        WorkflowNode(
            node_id="a28-placement-group-project-context",
            agent_id="synthesizer",
            operator="select_fields",
            inputs=(outputs["ranked"],),
            outputs=(outputs["context"],),
            arguments={
                "fields": ["source_document_id", "title", "evidence_excerpt"],
                "output_artifact_id": outputs["context"],
            },
        ),
        WorkflowNode(
            node_id="a28-same-model-synthesis",
            agent_id="synthesizer",
            operator="invoke_model",
            inputs=(outputs["context"],),
            arguments={
                "prompt": (
                    f"{query}\nUse only the context artifact. Compare both sources in 120 to "
                    "180 words, then end with exactly ANSWER: Yes or ANSWER: No. Do not reveal "
                    "chain-of-thought."
                )
            },
        ),
    )
    edges = (
        WorkflowEdge(
            producer_node="a4-local-retrieve-reduce",
            consumer_node="a28-merge-package",
            artifact_id=outputs["a4"],
        ),
        WorkflowEdge(
            producer_node="a5-local-retrieve-reduce",
            consumer_node="a28-merge-package",
            artifact_id=outputs["a5"],
        ),
        WorkflowEdge(
            producer_node="a28-merge-package",
            consumer_node="a28-placement-group-bm25-reduce",
            artifact_id=outputs["package"],
        ),
        WorkflowEdge(
            producer_node="a28-placement-group-bm25-reduce",
            consumer_node="a28-placement-group-project-context",
            artifact_id=outputs["ranked"],
        ),
        WorkflowEdge(
            producer_node="a28-placement-group-project-context",
            consumer_node="a28-same-model-synthesis",
            artifact_id=outputs["context"],
        ),
    )
    return WorkflowPlan(agents=agents, nodes=nodes, edges=edges)


def _workload(bundle: AdaptationBundle) -> WorkloadSpec:
    return WorkloadSpec(
        available_operations=(
            "bm25_retrieve",
            "aggregate_artifacts",
            "select_fields",
            "invoke_model",
        ),
        available_model_instances=(
            AvailableModelInstance(
                model_instance_id=CANONICAL_DEPLOYMENT,
                model_id="qwen3.8-27b-q4km-v1",
                modalities=frozenset({"text", "image"}),
            ),
        ),
        artifacts=tuple(
            WorkloadArtifact(
                artifact_id=item.artifact_id,
                logical_type=item.logical_type,
                media_type=item.media_type,
            )
            for item in bundle.execution.task.artifacts
        ),
        min_agents=4,
        max_agents=4,
    )


def _scheduler(
    policy: Literal["b0", "b1", "forced-a28", "forced-rtx"],
    replica_set: EquivalentModelReplicaSet,
    estimates: tuple[SynthesisStageEstimate, ...],
) -> FixedPrefixScheduler:
    if policy == "b0":
        kind: Literal["b0", "b1", "forced"] = "b0"
        forced = None
        scheduler_kind = SchedulerKind.B0_LOCALITY_AWARE_MYOPIC
    elif policy == "b1":
        kind = "b1"
        forced = None
        scheduler_kind = SchedulerKind.B1_MYOPIC_COST_AWARE
    else:
        kind = "forced"
        forced = "A28" if policy == "forced-a28" else "strong-4090"
        scheduler_kind = SchedulerKind.B1_MYOPIC_COST_AWARE
    stage = SynthesisStageScheduler(
        kind,
        replica_set,
        leader_node_id="a28-placement-group-bm25-reduce",
        intermediate_node_ids=("a28-placement-group-project-context",),
        follower_node_id="a28-same-model-synthesis",
        stage_estimates=estimates,
        forced_agent_id=forced,
    )
    return FixedPrefixScheduler(
        stage,
        {
            "a4-local-retrieve-reduce": "A4",
            "a5-local-retrieve-reduce": "A5",
            "a28-merge-package": "A28",
        },
        scheduler_kind=scheduler_kind,
    )


async def _clients(stack: AsyncExitStack) -> dict[str, WorkerClient]:
    result: dict[str, WorkerClient] = {}
    for agent_id, url in WORKER_URLS.items():
        client = await stack.enter_async_context(httpx.AsyncClient(base_url=url, timeout=900))
        result[agent_id] = HttpWorkerClient(agent_id, client)
    return result


async def preload(manifest_path: Path, label: str) -> None:
    manifest = _manifest(manifest_path)
    bundle = _bundle(manifest_path, manifest, label)
    payload = _payload(manifest, label)
    placement = {item.artifact_id: item.placement_agent for item in payload.shards}
    async with AsyncExitStack() as stack:
        clients = await _clients(stack)
        for artifact in bundle.prepared_artifacts:
            agent_id = placement[artifact.spec.artifact_id]
            response = await clients[agent_id].put_artifact(
                artifact.spec.artifact_id,
                artifact.spec.media_type,
                artifact.content,
                artifact.sha256_hex,
            )
            if response.sha256_hex != artifact.sha256_hex:
                raise RuntimeError("preload checksum mismatch")


def _load_stage_estimates(path: Path | None) -> tuple[SynthesisStageEstimate, ...]:
    if path is None:
        return ()
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("stage estimates must be a JSON array")
    return tuple(
        SynthesisStageEstimate.model_validate(item) for item in cast(list[object], raw)
    )


def _load_deepseek_key(path: Path | None) -> None:
    if os.environ.get("DEEPSEEK_API_KEY"):
        return
    if path is None:
        raise RuntimeError("DEEPSEEK_API_KEY is unset and no API key file was provided")
    prefix = "DeepSeek API Key:"
    matches = [
        line.removeprefix(prefix).strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith(prefix)
    ]
    if len(matches) != 1 or not matches[0]:
        raise RuntimeError("API key file must contain exactly one non-empty DeepSeek key")
    os.environ["DEEPSEEK_API_KEY"] = matches[0]


def _produced_artifact_ids(plan: WorkflowPlan) -> tuple[str, ...]:
    return tuple(item for node in plan.nodes for item in node.outputs)


async def _cleanup_artifacts(artifact_ids: tuple[str, ...]) -> None:
    runner = SshCommandRunner()
    for agent_id, (ssh_target, root) in ARTIFACT_ROOTS.items():
        del agent_id
        paths: list[str] = []
        for artifact_id in artifact_ids:
            key = hashlib.sha256(artifact_id.encode("utf-8")).hexdigest()
            paths.extend((f"{root}/{key}.blob", f"{root}/{key}.json"))
        await runner.run(ssh_target, ("rm", "-f", "--", *paths))


def _model_finish_reasons(result: PersistedWorkflowRunResult) -> tuple[str, ...]:
    if result.workflow is None:
        return ()
    return tuple(
        finish_reason
        for record in result.workflow.records
        if record.execution is not None and record.execution.model_telemetry is not None
        if (finish_reason := record.execution.model_telemetry.finish_reason) is not None
    )


async def run_one(args: argparse.Namespace) -> None:
    _load_deepseek_key(args.api_key_file)
    manifest = _manifest(args.manifest)
    bundle = _bundle(args.manifest, manifest, args.payload)
    calibration = _load_calibration(args.calibration)
    if calibration.regime.control_method != NetworkControlMethod.TC:
        raise RuntimeError("primary v1 run requires network_control=tc")
    if calibration.regime.bandwidth_mbps != args.bandwidth_mbps:
        raise RuntimeError("run bandwidth differs from referenced calibration")
    environment = _environment(bundle, manifest, args.payload, calibration)
    plan = _plan(bundle, manifest, args.payload, args.run_id)
    workflow_hash = hashlib.sha256(
        json.dumps(
            plan.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    replica_set = _load_replica_set(args.preflight_config)
    estimates = _load_stage_estimates(args.stage_estimates)
    scheduler = TimedScheduler(_scheduler(args.policy, replica_set, estimates))
    planner_config: PlannerConfig = load_planner_config(args.planner_config)
    config = RunnerConfig(
        environment=environment,
        worker_urls=WORKER_URLS,
        planner=planner_config,
        output_root=args.output_root,
        http_timeout_seconds=900,
    )
    endpoints, ports = _load_tc_endpoints(args.tc_config)
    tc_regime = TcRegime(
        configuration_id=calibration.regime.tc_configuration_id or "missing",
        bandwidth_mbps=args.bandwidth_mbps,
        added_rtt_ms=calibration.regime.added_rtt_ms,
        worker_ports=ports,
    )
    command_runner = SshCommandRunner()
    controller = TcController(command_runner)
    started = perf_counter()
    result: PersistedWorkflowRunResult | None = None
    validation_error: str | None = None
    cleanup_error: str | None = None
    states = await controller.apply(
        tuple(build_tc_command_plan(endpoint, tc_regime) for endpoint in endpoints)
    )
    try:
        async with AsyncExitStack() as stack:
            clients = await _clients(stack)
            runner = PrepositionedWorkflowRunner(
                config,
                _workload(bundle),
                scheduler,
                worker_clients=clients,
                planner=ScriptedWorkflowPlanner((plan,)),
            )
            result = await runner.run(bundle, run_id=args.run_id)
        reasons = _model_finish_reasons(result)
        if reasons != ("stop",):
            validation_error = f"formal model finish reason is not stop: {reasons}"
    finally:
        try:
            await controller.cleanup()
        except Exception as exc:  # noqa: BLE001 - persist cleanup invalidity
            cleanup_error = f"{type(exc).__name__}: {exc}"
        await _cleanup_artifacts(_produced_artifact_ids(plan))
    if result.workflow is None:
        actual_replica_id = "not-executed"
    else:
        model_records = [
            item
            for item in result.workflow.records
            if item.node_id == "a28-same-model-synthesis"
        ]
        actual_replica_id = (
            model_records[0].scheduler_decision.selected_deployment_id
            if model_records
            else "not-executed"
        ) or "not-executed"
    metadata = ExperimentMetadata(
        experiment_version="heterogeneous-infrastructure-v1",
        hardware_topology_id="a4-a5-a28-strong4090-wifi-v1",
        network_control_method=NetworkControlMethod.TC,
        network_calibration_id=calibration.calibration_id,
        compute_profile_id=args.compute_profile_id,
        model_checkpoint_id="qwen3.8-27b-b69fef445144",
        model_replica_id=actual_replica_id,
        model_quantization="Q4_K_M",
        tc_configuration_id=tc_regime.configuration_id,
        payload_class=PayloadClass(args.payload),
        placement_policy=args.policy,
        workflow_hash=workflow_hash,
    )
    sidecar = {
        "metadata": metadata.model_dump(mode="json"),
        "configured_bandwidth_mbps": args.bandwidth_mbps,
        "configured_added_rtt_ms": calibration.regime.added_rtt_ms,
        "calibration": calibration.model_dump(mode="json"),
        "tc_applied": [
            {
                "agent_id": state.endpoint.agent_id,
                "interface": state.endpoint.interface,
                "original_qdisc": state.original_qdisc,
                "shaped_qdisc": state.shaped_qdisc,
            }
            for state in states
        ],
        "tc_cleanup_error": cleanup_error,
        "validation_error": validation_error,
        "scheduler_overhead": {
            "samples": scheduler.samples,
            "total_ms": sum(float(item["duration_ms"]) for item in scheduler.samples),
        },
        "driver_wall_ms": (perf_counter() - started) * 1000,
        "result_path": str(args.output_root / args.run_id / "result.json"),
        "trace_path": str(args.output_root / args.run_id / "trace.jsonl"),
    }
    sidecar_path = args.output_root / args.run_id / "experiment-metadata.json"
    sidecar_path.write_text(json.dumps(sidecar, indent=2, sort_keys=True), encoding="utf-8")
    if cleanup_error is not None:
        raise RuntimeError(f"tc cleanup failed: {cleanup_error}")
    if validation_error is not None:
        raise RuntimeError(validation_error)
    if not result.execution_completed:
        raise RuntimeError(f"controlled run failed: {result.failure}")
    print(sidecar_path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    preload_parser = sub.add_parser("preload")
    preload_parser.add_argument("--manifest", type=Path, required=True)
    preload_parser.add_argument("--payload", choices=("S", "M", "L"), required=True)

    run = sub.add_parser("run-one")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--payload", choices=("S", "M", "L"), required=True)
    run.add_argument(
        "--policy", choices=("b0", "b1", "forced-a28", "forced-rtx"), required=True
    )
    run.add_argument("--run-id", required=True)
    run.add_argument("--bandwidth-mbps", type=float, required=True)
    run.add_argument("--calibration", type=Path, required=True)
    run.add_argument("--compute-profile-id", required=True)
    run.add_argument("--stage-estimates", type=Path)
    run.add_argument("--preflight-config", type=Path, required=True)
    run.add_argument("--tc-config", type=Path, required=True)
    run.add_argument("--planner-config", type=Path, required=True)
    run.add_argument("--api-key-file", type=Path)
    run.add_argument("--output-root", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "preload":
        asyncio.run(preload(args.manifest, args.payload))
    else:
        asyncio.run(run_one(args))


if __name__ == "__main__":
    main()
