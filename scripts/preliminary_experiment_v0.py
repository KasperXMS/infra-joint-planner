"""Run one frozen cell of preliminary experiment v0.

Worker processes and their per-run artifact roots are prepared separately. This
driver intentionally executes exactly one task attempt and never retries it.
"""

import argparse
import asyncio
import json
from contextlib import AsyncExitStack
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx

from infra_joint.benchmarks.base import (
    AdaptationBundle,
    AdaptedExecutionCase,
    PreparedArtifact,
    TransformationRecord,
    assess_validity,
)
from infra_joint.benchmarks.longbench_v2 import (
    FixedWidthColumn,
    FixedWidthStructuredContext,
    FixedWidthType,
    LongBenchV2Adapter,
    LongBenchV2Sample,
)
from infra_joint.benchmarks.multihop_rag import (
    CandidateSelectionRecord,
    FixedCandidate,
    FixedCandidateSetting,
    MultiHopCorpusDocument,
    MultiHopRAGAdapter,
    MultiHopRAGSample,
)
from infra_joint.benchmarks.video_mme import (
    SourceArtifact,
    VideoMMEAdapter,
    VideoMMEOption,
    VideoMMESample,
)
from infra_joint.config import RunnerConfig, load_runner_config
from infra_joint.core.action import (
    FinishDecision,
    JointAction,
    PhysicalDecision,
    PhysicalPolicy,
    SemanticAction,
)
from infra_joint.core.state import ArtifactPlacement, EnvironmentSpec, LinkSpec
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.experiments.preliminary import (
    AwarePlanningGraph,
    LLMNaiveAwarePlanner,
    NetworkRegime,
    ShapedWorkerClient,
    build_no_retry_model_backend,
)
from infra_joint.experiments.runner import BenchmarkRunner, PersistedRunResult
from infra_joint.infrastructure.observer import LiveWorkerObserver
from infra_joint.infrastructure.validation import validate_worker_surfaces
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.planning.finalize import ContractAwareFinalizer
from infra_joint.planning.graph import PlanningGraph
from infra_joint.planning.planner import LLMBlindPlanner, ScriptedBlindPlanner
from infra_joint.runtime.client import HttpWorkerClient, WorkerClient
from infra_joint.runtime.executor import RuntimeExecutor

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "configs" / "local" / "data"
SUBSTRATE_COMMIT = "bccef0744bf9270f6d689401ad91885c7c130a28"
EDGE_AGENT = "EDGE"
GPU_AGENT = "GPU"
TEXT_DEPLOYMENT = "gpu-deepseek-chat"
VISION_DEPLOYMENT = "gpu-qwen3-vl-m4-32k"

REGIMES = {
    "h_fast": NetworkRegime("H_fast", 100.0, 0.0),
    "h_constrained": NetworkRegime("H_constrained", 3.0, 50.0),
}

PRIMARY_CASES = (
    "a-video-v1-h-fast",
    "a-video-v1-h-constrained",
    "a-video-v2-h-fast",
    "a-video-v2-h-constrained",
    "a-longbench-l1-h-fast",
    "a-longbench-l1-h-constrained",
    "a-longbench-l2-h-fast",
    "a-longbench-l2-h-constrained",
    "b-video-blind",
    "b-video-aware",
    "b-longbench-blind",
    "b-longbench-aware",
    "b-multihop-blind",
    "b-multihop-aware",
)


def _longbench_source_context() -> tuple[str, tuple[FixedWidthColumn, ...], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    for path in sorted((DATA / "longbench").glob("lb2-artifact-*.json")):
        records.extend(json.loads(path.read_text(encoding="utf-8"))["records"])
    column_names = tuple(records[0])
    numeric = {
        name
        for name in column_names
        if any(
            isinstance(record[name], (int, float)) for record in records if record[name] is not None
        )
    }
    rendered = {
        name: ["" if record[name] is None else str(record[name]) for record in records]
        for name in column_names
    }
    widths = {
        name: max(len(name), *(len(value) for value in rendered[name])) + 1 for name in column_names
    }
    columns: list[FixedWidthColumn] = []
    offset = 0
    for name in column_names:
        end = offset + widths[name]
        columns.append(
            FixedWidthColumn(
                name=name,
                start_char=offset,
                end_char=end,
                value_type=FixedWidthType.NUMBER if name in numeric else FixedWidthType.STRING,
                nullable=name in numeric,
            )
        )
        offset = end
    lines = ["".join(name.ljust(widths[name]) for name in column_names)]
    lines.extend(
        "".join(rendered[name][index].ljust(widths[name]) for name in column_names)
        for index in range(len(records))
    )
    return "\n".join(lines), tuple(columns), records


def longbench_bundle() -> AdaptationBundle:
    context, columns, expected = _longbench_source_context()
    sample = LongBenchV2Sample(
        sample_id="longbench-v2-66f3ac0b821e116aacb2e203",
        domain="Long Structured Data Understanding",
        sub_domain="Table QA",
        difficulty="hard",
        length="long",
        question=(
            "For end dates on 2021-12-31, which company has the highest total "
            "asset/total liability ratio? Please provide the stock symbol of the company, "
            "and the value of the total asset/total liability ratio (rounded to the nearest "
            "whole number)."
        ),
        choice_A="600052;32",
        choice_B="000722;30",
        choice_C="000416;30",
        choice_D="000416;29",
        answer="D",
        context=context,
    )
    bundle = LongBenchV2Adapter("2b48e494f2c7a2f0af81aae178e05c7e1dde0fe9").adapt(
        sample,
        FixedWidthStructuredContext(columns=columns, artifact_id="longbench-structured-records"),
    )
    if json.loads(bundle.prepared_artifacts[0].content) != expected:
        raise RuntimeError("structured adaptation did not preserve the frozen records")
    return bundle


def video_bundle(video_path: Path) -> AdaptationBundle:
    content = video_path.read_bytes()
    sample = VideoMMESample(
        sample_id="video_mme:795:question:3",
        video=SourceArtifact(
            artifact_id="video-mme-795-complete-mjpeg-1fps-q3",
            logical_type=(
                "question_independent_complete_timeline_video;derived_mjpeg;fps=1;width=960;q=3"
            ),
            media_type="video/x-msvideo",
            size_bytes=len(content),
            source_ref="local-preliminary-v0://video-mme/795/derived",
        ),
        question="Which tool is used in the first magic?",
        options=(
            VideoMMEOption(label="A", text="String"),
            VideoMMEOption(label="B", text="Coin"),
            VideoMMEOption(label="C", text="Hat"),
            VideoMMEOption(label="D", text="Glasses"),
        ),
        answer_label="A",
    )
    adapted = VideoMMEAdapter("video-mme-2026-09-22-preliminary-v0").adapt(sample)
    record = TransformationRecord(
        benchmark_id="video_mme",
        source_revision="video-mme-2026-09-22-preliminary-v0",
        source_task_id=sample.sample_id,
        transformation="full_timeline_av1_to_mjpeg_1fps_960px_q3",
        information_preserved=False,
        order_preserved=True,
        gold_independent=True,
        notes=(
            "Pre-experiment derived execution setting only; not a formal Video-MME "
            "benchmark-quality representation claim."
        ),
        audit={
            "derived_sha256": sha256(content).hexdigest(),
            "ffmpeg_filter": "fps=1,scale=960:-2",
            "codec": "mjpeg",
            "qscale": 3,
            "audio_removed": True,
        },
    )
    execution = AdaptedExecutionCase(
        task=adapted.execution.task,
        transformations=(record,),
        validity=assess_validity((record,), query_equivalent=True, evaluator_equivalent=True),
    )
    return AdaptationBundle(execution, adapted.private_evaluation, ())


def multihop_bundle() -> AdaptationBundle:
    selection = json.loads((DATA / "multihop" / "candidates.json").read_text(encoding="utf-8"))
    selected = next(
        item
        for item in selection["candidates"]
        if item["task_id"] == "multihop-rag-train-9bae0079038050a37a1ae583"
    )
    identifiers = selected["candidate_document_ids"][:2]
    documents = tuple(
        MultiHopCorpusDocument.model_validate_json(
            (DATA / "multihop" / f"{artifact_id}.json").read_text(encoding="utf-8")
        )
        for artifact_id in identifiers
    )
    sample = MultiHopRAGSample(
        sample_id=selected["task_id"],
        query=selected["query"],
        evidence_list=(),
        question_type=selected["question_type"],
        answer=selected["evaluator_only"]["answer"],
    )
    revision = selection["source"]["dataset_revision"]
    setting = FixedCandidateSetting(
        candidates=tuple(
            FixedCandidate(
                rank=index,
                score=selected["candidate_scores"][index - 1],
                document=document,
            )
            for index, document in enumerate(documents, start=1)
        ),
        selection=CandidateSelectionRecord(
            selector_id=selection["retrieval"]["algorithm"],
            selector_revision="scope-expansion-v0",
            source_corpus_revision=revision,
            query_sha256=sha256(sample.query.encode("utf-8")).hexdigest(),
            top_n=selection["retrieval"]["top_n"],
            gold_independent=True,
        ),
        artifact_id="multihop-fixed-candidates-v2",
    )
    return MultiHopRAGAdapter(revision).adapt(sample, setting)


def action(
    operator: str,
    inputs: tuple[str, ...],
    arguments: dict[str, Any],
    *,
    agent: str | None = None,
    deployment: str | None = None,
) -> JointAction:
    if deployment is not None:
        physical = PhysicalDecision(
            policy=PhysicalPolicy.TARGET_DEPLOYMENT,
            target_deployment_id=deployment,
        )
    elif agent is not None:
        physical = PhysicalDecision(policy=PhysicalPolicy.TARGET_AGENT, target_agent_id=agent)
    else:
        physical = PhysicalDecision(policy=PhysicalPolicy.AUTO)
    return JointAction(
        semantic=SemanticAction(operator=operator, inputs=inputs, arguments=arguments),
        physical=physical,
    )


def video_script(workflow: str, run_id: str) -> tuple[JointAction | FinishDecision, ...]:
    processing_agent = GPU_AGENT if workflow == "v1" else EDGE_AGENT
    prefix = f"{run_id}-frames"
    sheet = f"{run_id}-contact-sheet"
    frames = tuple(f"{prefix}/frame-{index:06d}.jpg" for index in range(1, 63))
    return (
        action(
            "sample_frames",
            ("video-mme-795-complete-mjpeg-1fps-q3",),
            {"every_seconds": 40, "max_frames": 62, "output_prefix": prefix},
            agent=processing_agent,
        ),
        action(
            "make_contact_sheet",
            frames,
            {
                "columns": 8,
                "cell_width": 320,
                "cell_height": 180,
                "output_artifact_id": sheet,
            },
            agent=processing_agent,
        ),
        action(
            "invoke_model",
            (sheet,),
            {
                "prompt": (
                    "This image is a chronological contact sheet sampled every 40 seconds "
                    "from the complete derived timeline of Video-MME task 795. Question: "
                    "Which tool is used in the first magic? A. String B. Coin C. Hat "
                    "D. Glasses. Respond with only the option letter."
                )
            },
            deployment=VISION_DEPLOYMENT,
        ),
        FinishDecision(reason="The scripted workflow has produced its model answer."),
    )


def longbench_script(workflow: str, run_id: str) -> tuple[JointAction | FinishDecision, ...]:
    processing_agent = GPU_AGENT if workflow == "l1" else EDGE_AGENT
    filtered = f"{run_id}-filtered"
    derived = f"{run_id}-derived"
    top = f"{run_id}-top"
    selected = f"{run_id}-selected"
    return (
        action(
            "filter_records",
            ("longbench-structured-records",),
            {
                "field": "EndDate",
                "op": "eq",
                "value": "2021-12-31",
                "output_artifact_id": filtered,
            },
            agent=processing_agent,
        ),
        action(
            "derive_fields",
            (filtered,),
            {
                "derivations": [
                    {
                        "target": "asset_liability_ratio",
                        "operation": "divide",
                        "sources": ["TotalAssets", "TotalLiability"],
                    }
                ],
                "output_artifact_id": derived,
            },
            agent=processing_agent,
        ),
        action(
            "top_k_records",
            (derived,),
            {
                "field": "asset_liability_ratio",
                "k": 1,
                "descending": True,
                "output_artifact_id": top,
            },
            agent=processing_agent,
        ),
        action(
            "select_fields",
            (top,),
            {"fields": ["Symbol", "asset_liability_ratio"], "output_artifact_id": selected},
            agent=processing_agent,
        ),
        action(
            "invoke_model",
            (selected,),
            {
                "prompt": (
                    "The JSON artifact is the highest asset-to-liability-ratio record for "
                    "EndDate 2021-12-31. Match its Symbol and rounded ratio to: "
                    "A. 600052;32 B. 000722;30 C. 000416;30 D. 000416;29. "
                    "Respond with only the option letter."
                )
            },
            deployment=TEXT_DEPLOYMENT,
        ),
        FinishDecision(reason="The scripted workflow has produced its model answer."),
    )


def _case(case_id: str, video_path: Path, run_id: str) -> tuple[AdaptationBundle, str, str]:
    parts = case_id.split("-")
    if case_id.startswith("a-video-"):
        workflow = parts[2]
        regime = "h_constrained" if case_id.endswith("h-constrained") else "h_fast"
        return video_bundle(video_path), regime, workflow
    if case_id.startswith("a-longbench-"):
        workflow = parts[2]
        regime = "h_constrained" if case_id.endswith("h-constrained") else "h_fast"
        return longbench_bundle(), regime, workflow
    if case_id.startswith("b-video-"):
        return video_bundle(video_path), "h_constrained", parts[-1]
    if case_id.startswith("b-longbench-"):
        return longbench_bundle(), "h_constrained", parts[-1]
    if case_id.startswith("b-multihop-"):
        return multihop_bundle(), "h_constrained", parts[-1]
    raise ValueError(f"unknown case: {case_id}")


def _environment(
    base: EnvironmentSpec,
    bundle: AdaptationBundle,
    regime: NetworkRegime,
) -> EnvironmentSpec:
    placements = tuple(
        ArtifactPlacement(artifact_id=item.artifact_id, agent_id=EDGE_AGENT)
        for item in bundle.execution.task.artifacts
    )
    links = tuple(
        LinkSpec(
            source_agent_id=item.source_agent_id,
            target_agent_id=item.target_agent_id,
            bandwidth_mbps=regime.bandwidth_mbps,
            rtt_ms=regime.added_rtt_ms,
        )
        for item in base.links
    )
    return base.model_copy(update={"initial_placements": placements, "links": links})


def _artifact_bytes(
    bundle: AdaptationBundle,
    artifact_id: str,
    video_path: Path,
) -> tuple[bytes, str]:
    prepared = {item.spec.artifact_id: item for item in bundle.prepared_artifacts}
    if artifact_id in prepared:
        item: PreparedArtifact = prepared[artifact_id]
        return item.content, item.sha256_hex
    if bundle.execution.task.benchmark_id == "video_mme":
        content = video_path.read_bytes()
        return content, sha256(content).hexdigest()
    raise ValueError(f"no artifact bytes for {artifact_id}")


async def run_one(
    config: RunnerConfig,
    case_id: str,
    run_id: str,
    video_path: Path,
) -> PersistedRunResult:
    bundle, regime_key, arm = _case(case_id, video_path, run_id)
    regime = REGIMES[regime_key]
    environment = _environment(config.environment, bundle, regime)
    run_directory = config.output_root / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    trace_path = run_directory / "trace.jsonl"
    result_path = run_directory / "result.json"
    setup_path = run_directory / "setup.json"
    trace = JsonlTraceWriter(trace_path)
    registry = build_operator_catalog()
    planner_client = None
    started = perf_counter()
    try:
        async with AsyncExitStack() as stack:
            raw_clients: dict[str, WorkerClient] = {}
            for agent_id, url in config.worker_urls.items():
                http_client = await stack.enter_async_context(
                    httpx.AsyncClient(base_url=url, timeout=config.http_timeout_seconds)
                )
                raw_clients[agent_id] = HttpWorkerClient(agent_id, http_client)
            clients: dict[str, WorkerClient] = {
                agent_id: ShapedWorkerClient(client, regime)
                for agent_id, client in raw_clients.items()
            }
            states = await validate_worker_surfaces(environment, registry, clients)
            materialization = []
            for spec in bundle.execution.task.artifacts:
                content, checksum = _artifact_bytes(bundle, spec.artifact_id, video_path)
                if len(content) != spec.size_bytes:
                    raise ValueError(f"artifact size mismatch: {spec.artifact_id}")
                upload_started = perf_counter()
                response = await raw_clients[EDGE_AGENT].put_artifact(
                    spec.artifact_id,
                    spec.media_type,
                    content,
                    checksum,
                )
                materialization.append(
                    {
                        "artifact_id": spec.artifact_id,
                        "target_agent_id": EDGE_AGENT,
                        "bytes": response.size_bytes,
                        "sha256": response.sha256_hex,
                        "setup_latency_ms": (perf_counter() - upload_started) * 1000,
                    }
                )
            setup = {
                "schema_version": "preliminary-experiment-v0-setup-v1",
                "substrate_commit": SUBSTRATE_COMMIT,
                "case_id": case_id,
                "run_id": run_id,
                "attempt": 1,
                "retry_policy": "none; OpenAI-compatible clients max_retries=0",
                "task": bundle.execution.task.model_dump(mode="json"),
                "transformations": [
                    item.model_dump(mode="json") for item in bundle.execution.transformations
                ],
                "validity": bundle.execution.validity.model_dump(mode="json"),
                "network_regime": {
                    "regime_id": regime.regime_id,
                    "bandwidth_mbps": regime.bandwidth_mbps,
                    "added_rtt_ms": regime.added_rtt_ms,
                    "enforcement": "minimum worker-to-worker artifact pull wall clock",
                },
                "environment": environment.model_dump(mode="json"),
                "worker_surface": {
                    key: value.model_dump(mode="json") for key, value in states.items()
                },
                "initial_materialization_excluded_from_task_e2e": materialization,
            }
            setup_path.write_text(
                json.dumps(setup, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            backend, planner_client = build_no_retry_model_backend(config.planner.model)
            observer = LiveWorkerObserver(environment, clients)
            executor = RuntimeExecutor(registry, environment, clients)
            finalizer = ContractAwareFinalizer(backend)
            if case_id.startswith("a-video-"):
                planner = ScriptedBlindPlanner(video_script(arm, run_id))
                graph: PlanningGraph = PlanningGraph(
                    planner=planner,
                    observer=observer,
                    executor=executor,
                    finalizer=finalizer,
                    evaluator=bundle.private_evaluation.build_evaluator(),
                    max_planning_steps=config.max_planning_steps,
                    trace_sink=trace,
                )
            elif case_id.startswith("a-longbench-"):
                planner = ScriptedBlindPlanner(longbench_script(arm, run_id))
                graph = PlanningGraph(
                    planner=planner,
                    observer=observer,
                    executor=executor,
                    finalizer=finalizer,
                    evaluator=bundle.private_evaluation.build_evaluator(),
                    max_planning_steps=config.max_planning_steps,
                    trace_sink=trace,
                )
            elif arm == "blind":
                graph = PlanningGraph(
                    planner=LLMBlindPlanner(backend, registry),
                    observer=observer,
                    executor=executor,
                    finalizer=finalizer,
                    evaluator=bundle.private_evaluation.build_evaluator(),
                    max_planning_steps=config.max_planning_steps,
                    trace_sink=trace,
                )
            else:
                aware = LLMNaiveAwarePlanner(backend, registry, environment)
                graph = AwarePlanningGraph(
                    aware_planner=aware,
                    observer=observer,
                    executor=executor,
                    finalizer=finalizer,
                    evaluator=bundle.private_evaluation.build_evaluator(),
                    max_planning_steps=config.max_planning_steps,
                    trace_sink=trace,
                )
            task_started = perf_counter()
            result = await graph.run(bundle.execution.task, run_id=run_id)
            persisted = PersistedRunResult(
                run_id=run_id,
                task_id=bundle.execution.task.task_id,
                benchmark_id=bundle.execution.task.benchmark_id,
                setting_kind=bundle.execution.validity.setting_kind,
                execution_completed=True,
                final_answer=result["final_answer"],
                evaluation=result["evaluation"],
                decisions=tuple(item.model_dump(mode="json") for item in result["decisions"]),
                observations=result["observations"],
                initial_transfers=(),
                telemetry=result["telemetry"],
                runner_e2e_latency_ms=(perf_counter() - task_started) * 1000,
                trace_path=str(trace_path),
            )
    except Exception as exc:  # noqa: BLE001 - the single attempt must always be persisted
        failure = BenchmarkRunner._failure(exc)
        elapsed = (perf_counter() - started) * 1000
        BenchmarkRunner._append_failure_trace(trace, run_id, failure, elapsed)
        persisted = PersistedRunResult(
            run_id=run_id,
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
    BenchmarkRunner._write_result(result_path, persisted)
    return persisted


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--case", choices=PRIMARY_CASES, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--video", type=Path, required=True)
    arguments = parser.parse_args()
    config = load_runner_config(arguments.config)
    result = asyncio.run(run_one(config, arguments.case, arguments.run_id, arguments.video))
    print(result.model_dump_json())
    if not result.execution_completed:
        raise SystemExit(2)
    if result.evaluation is None or not result.evaluation.format_valid:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
