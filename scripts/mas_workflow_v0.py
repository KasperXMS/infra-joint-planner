import argparse
import asyncio
import json
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, cast

import httpx

from infra_joint.benchmarks.base import (
    AdaptationBundle,
    AdaptedExecutionCase,
    PreparedArtifact,
    TransformationRecord,
    assess_validity,
)
from infra_joint.benchmarks.multihop_rag import (
    MULTIHOP_EVALUATOR_ID,
    MultiHopCorpusDocument,
    PrivateMultiHopEvaluation,
)
from infra_joint.config import RunnerConfig, load_runner_config
from infra_joint.core.state import ArtifactPlacement, LinkSpec
from infra_joint.core.task import ArtifactSpec, OutputContract, OutputFormat, TaskContract
from infra_joint.core.workflow import WorkflowPlan
from infra_joint.runtime.client import HttpWorkerClient, WorkerClient
from infra_joint.workflow.network import NetworkRegime, RegimeWorkerClient
from infra_joint.workflow.planner import ScriptedWorkflowPlanner
from infra_joint.workflow.runner import PersistedWorkflowRunResult, WorkflowBenchmarkRunner
from infra_joint.workflow.scheduler import OperatorDeviceProfile, build_scheduler
from infra_joint.workflow.workload import AvailableModelInstance, WorkloadArtifact, WorkloadSpec

FAST = NetworkRegime(regime_id="H_fast", bandwidth_mbps=100, added_rtt_ms=0)
CONSTRAINED = NetworkRegime(
    regime_id="H_constrained",
    bandwidth_mbps=3,
    added_rtt_ms=50,
)
TASK_ID = "multihop-rag-train-9bae0079038050a37a1ae583"
DEPLOYMENT_ID = "a28-deepseek-chat"


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def load_case(case_path: Path) -> tuple[AdaptationBundle, dict[str, str]]:
    raw = cast(dict[str, Any], json.loads(case_path.read_text(encoding="utf-8")))
    if raw.get("task_id") != TASK_ID:
        raise ValueError(f"unexpected case task_id: {raw.get('task_id')}")
    documents = cast(list[dict[str, Any]], raw["documents"])
    if len(documents) != 2:
        raise ValueError("MAS smoke case must contain exactly two frozen documents")
    prepared: list[PreparedArtifact] = []
    placements: dict[str, str] = {}
    for branch, item in zip(("a", "b"), documents, strict=True):
        document_path = (case_path.parent / str(item["path"])).resolve()
        document = MultiHopCorpusDocument.model_validate_json(
            document_path.read_text(encoding="utf-8")
        )
        artifact_id = f"mas-v0-corpus-{branch}"
        content = _canonical_json(
            [
                {
                    "document": document.model_dump(),
                    "rank": int(item["rank"]),
                    "score": float(item["score"]),
                    "text": document.body,
                }
            ]
        )
        prepared.append(
            PreparedArtifact.create(
                ArtifactSpec(
                    artifact_id=artifact_id,
                    logical_type="derived_gold_independent_candidate_shard;text_field=text",
                    media_type="application/json",
                    size_bytes=len(content),
                    source_ref=f"local-derived://{TASK_ID}/{artifact_id}",
                ),
                content,
            )
        )
        placements[artifact_id] = str(item["initial_agent"])

    task = TaskContract(
        task_id=f"mas-workflow-v0-{TASK_ID}",
        benchmark_id="multihop_rag_mas_workflow_derived_smoke",
        objective=str(raw["query"]),
        artifacts=tuple(item.spec for item in prepared),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
        evaluator_id=MULTIHOP_EVALUATOR_ID,
    )
    transformation = TransformationRecord(
        benchmark_id=task.benchmark_id,
        source_revision=str(raw["source_revision"]),
        source_task_id=TASK_ID,
        transformation="gold_independent_bm25_top2_split_into_two_single_document_shards",
        information_preserved=False,
        order_preserved=True,
        gold_independent=True,
        notes="Derived MAS execution smoke only; not a formal MultiHop-RAG benchmark claim.",
        audit={
            "document_ids": [str(item["document_id"]) for item in documents],
            "selection": "frozen query-only BM25 rank 1 and 2",
            "shard_count": 2,
        },
    )
    bundle = AdaptationBundle(
        execution=AdaptedExecutionCase(
            task=task,
            transformations=(transformation,),
            validity=assess_validity(
                (transformation,),
                query_equivalent=True,
                evaluator_equivalent=True,
            ),
        ),
        private_evaluation=PrivateMultiHopEvaluation(
            task_id=task.task_id,
            gold_answer=str(raw["answer"]),
            question_type=raw["question_type"],
            supporting_evidence=(),
        ),
        prepared_artifacts=tuple(prepared),
    )
    return bundle, placements


def workload_for(config: RunnerConfig, bundle: AdaptationBundle) -> WorkloadSpec:
    deployment = next(
        item for item in config.environment.deployments if item.deployment_id == DEPLOYMENT_ID
    )
    return WorkloadSpec(
        available_operations=("bm25_retrieve", "aggregate_artifacts", "invoke_model"),
        available_model_instances=(
            AvailableModelInstance(
                model_instance_id=deployment.deployment_id,
                model_id=deployment.model_id,
                modalities=deployment.modalities,
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
        min_agents=3,
        max_agents=3,
    )


def config_for(
    base: RunnerConfig,
    placements: dict[str, str],
    regime: NetworkRegime,
    output_root: Path,
) -> RunnerConfig:
    environment = base.environment.model_copy(
        update={
            "initial_placements": tuple(
                ArtifactPlacement(artifact_id=artifact_id, agent_id=agent_id)
                for artifact_id, agent_id in sorted(placements.items())
            ),
            "links": tuple(
                LinkSpec(
                    source_agent_id=link.source_agent_id,
                    target_agent_id=link.target_agent_id,
                    bandwidth_mbps=regime.bandwidth_mbps,
                    rtt_ms=regime.added_rtt_ms,
                )
                for link in base.environment.links
            ),
        }
    )
    return base.model_copy(update={"environment": environment, "output_root": output_root})


def validate_mas_smoke_plan(plan: WorkflowPlan) -> None:
    if len(plan.agents) < 3:
        raise ValueError("MAS smoke requires at least three logical agents")
    predecessors: dict[str, set[str]] = {
        node.node_id: set() for node in plan.nodes
    }
    for edge in plan.edges:
        predecessors[edge.consumer_node].add(edge.producer_node)
    roots = [node for node in plan.nodes if not predecessors[node.node_id]]
    if len(roots) < 2 or len({node.agent_id for node in roots}) < 2:
        raise ValueError("MAS smoke requires two independent ready branches")
    fan_in = [node for node in plan.nodes if len(predecessors[node.node_id]) >= 2]
    if not fan_in:
        raise ValueError("MAS smoke requires a fan-in node")
    if not any(node.operator == "invoke_model" for node in plan.nodes):
        raise ValueError("MAS smoke requires fixed-deployment model synthesis")


def profiles_for(config: RunnerConfig) -> tuple[OperatorDeviceProfile, ...]:
    devices = sorted({item.device for item in config.environment.agents})
    estimates = {
        "bm25_retrieve": 100.0,
        "aggregate_artifacts": 25.0,
        "invoke_model": 1000.0,
    }
    return tuple(
        OperatorDeviceProfile(
            operator_id=operator,
            device=device,
            compute_latency_ms=latency,
        )
        for device in devices
        for operator, latency in estimates.items()
    )


async def worker_clients(
    stack: AsyncExitStack,
    config: RunnerConfig,
    regime: NetworkRegime,
) -> dict[str, WorkerClient]:
    values: dict[str, WorkerClient] = {}
    for agent_id, url in config.worker_urls.items():
        http_client = await stack.enter_async_context(
            httpx.AsyncClient(base_url=url, timeout=config.http_timeout_seconds)
        )
        raw = HttpWorkerClient(agent_id, http_client)
        values[agent_id] = RegimeWorkerClient(raw, regime, config.worker_urls)
    return values


async def run_one(
    base: RunnerConfig,
    bundle: AdaptationBundle,
    placements: dict[str, str],
    output_root: Path,
    run_id: str,
    regime: NetworkRegime,
    scheduler_mode: str,
    plan: WorkflowPlan | None,
) -> PersistedWorkflowRunResult:
    config = config_for(base, placements, regime, output_root)
    scheduler = build_scheduler(
        cast(Any, scheduler_mode),
        profiles=profiles_for(config),
    )
    workload = workload_for(config, bundle)
    async with AsyncExitStack() as stack:
        clients = await worker_clients(stack, config, regime)
        runner = WorkflowBenchmarkRunner(
            config,
            workload,
            scheduler,
            worker_clients=clients,
            planner=(ScriptedWorkflowPlanner((plan,)) if plan is not None else None),
        )
        return await runner.run(bundle, run_id=run_id)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("smoke", "matrix"))
    parser.add_argument("--runner-config", type=Path, required=True)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path)
    arguments = parser.parse_args()

    base = load_runner_config(arguments.runner_config)
    bundle, placements = load_case(arguments.case)
    output_root: Path = arguments.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    if arguments.mode == "smoke":
        result = await run_one(
            base,
            bundle,
            placements,
            output_root,
            "mas-v0-smoke",
            FAST,
            "b0",
            None,
        )
        if not result.execution_completed or result.plan is None:
            raise RuntimeError(f"MAS smoke failed: {result.failure}")
        validate_mas_smoke_plan(result.plan)
        plan_path = output_root / "frozen-workflow-plan.json"
        plan_path.write_text(
            json.dumps(result.plan.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(plan_path)
        return

    if arguments.plan is None:
        raise ValueError("matrix mode requires --plan")
    plan = WorkflowPlan.model_validate_json(arguments.plan.read_text(encoding="utf-8"))
    validate_mas_smoke_plan(plan)
    results: list[PersistedWorkflowRunResult] = []
    for scheduler_mode, regime in (
        ("b0", FAST),
        ("b0", CONSTRAINED),
        ("b1", FAST),
        ("b1", CONSTRAINED),
    ):
        run_id = f"mas-v0-{scheduler_mode}-{regime.regime_id.lower()}"
        result = await run_one(
            base,
            bundle,
            placements,
            output_root,
            run_id,
            regime,
            scheduler_mode,
            plan,
        )
        results.append(result)
        if not result.execution_completed:
            raise RuntimeError(f"matrix stopped at {run_id}: {result.failure}")
    summary_path = output_root / "matrix-summary.json"
    summary_path.write_text(
        json.dumps(
            [item.model_dump(mode="json") for item in results],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(summary_path)


if __name__ == "__main__":
    asyncio.run(main())
