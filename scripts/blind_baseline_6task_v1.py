"""Freeze, run, and audit the six-task native-network Blind baseline."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
from contextlib import AsyncExitStack
from itertools import pairwise
from pathlib import Path
from time import perf_counter
from typing import Any, cast

import yaml
from open_ended_mas_preliminary_v1 import (
    CapturingCompletionBackend,
    PrepositionedWorkflowRunner,
    _alias_environment,
    _alias_workload,
    _canonical_hash,
    _clients,
    _code_revision,
    _generated_ids,
    _load_key,
    _native_network_snapshot,
    _remove_artifacts,
    _translate_plan,
    _workflow_shape,
    _write_json,
)

from infra_joint.benchmarks.base import (
    AdaptationBundle,
    AdaptedExecutionCase,
    PreparedArtifact,
    TransformationRecord,
    assess_validity,
)
from infra_joint.benchmarks.longbench_v2 import (
    LongBenchV2Adapter,
    LongBenchV2Sample,
)
from infra_joint.benchmarks.multihop_rag import (
    FullCorpusSetting,
    MultiHopCorpusDocument,
    MultiHopEvidence,
    MultiHopRAGAdapter,
    MultiHopRAGSample,
)
from infra_joint.benchmarks.video_mme import (
    SourceArtifact,
    VideoMMEAdapter,
    VideoMMEOption,
    VideoMMESample,
)
from infra_joint.config import RunnerConfig, build_model_backend, load_planner_config
from infra_joint.core.state import ArtifactPlacement, EnvironmentSpec
from infra_joint.core.task import ArtifactContentSchema, ArtifactSpec
from infra_joint.core.workflow import WorkflowPlan
from infra_joint.infrastructure.validation import validate_worker_surfaces
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.planning.planner import logical_task_payload
from infra_joint.workflow.planner import LLMWorkflowPlanner, ScriptedWorkflowPlanner
from infra_joint.workflow.runner import PersistedWorkflowRunResult
from infra_joint.workflow.scheduler import LocalityAwareMyopicScheduler
from infra_joint.workflow.workload import WorkloadSpec

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO / "configs/experiments/blind-baseline-6task-v1.yaml"
DEFAULT_OUTPUT = REPO / "results/blind-baseline-6task-v1"
DEFAULT_KEY = REPO.parent / "api_key.txt"
LONGBENCH_CHUNK_CHARS = 3_000
MULTIHOP_CHUNK_CHARS = 2_500


def _yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return cast(dict[str, Any], value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _public_bundle_digest(bundle: AdaptationBundle) -> str:
    value = {
        "execution": bundle.execution.model_dump(mode="json"),
        "artifacts": [
            {
                "artifact_id": item.spec.artifact_id,
                "media_type": item.spec.media_type,
                "size_bytes": item.spec.size_bytes,
                "sha256": item.sha256_hex,
            }
            for item in bundle.prepared_artifacts
        ],
    }
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _load_longbench_samples(path: Path, wanted: set[str]) -> dict[str, LongBenchV2Sample]:
    found: dict[str, LongBenchV2Sample] = {}
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            raw = json.loads(line)
            sample_id = str(raw.get("_id", raw.get("sample_id", "")))
            if sample_id in wanted:
                found[sample_id] = LongBenchV2Sample.model_validate(raw)
    missing = wanted - set(found)
    if missing:
        raise RuntimeError(f"LongBench samples are missing: {sorted(missing)}")
    return found


def _text_chunks(value: str, limit: int) -> list[str]:
    """Split losslessly with a hard per-record character bound."""

    return [value[start : start + limit] for start in range(0, len(value), limit)]


def _longbench_multidoc_bundle(
    sample: LongBenchV2Sample,
    source_revision: str,
    boundary_lines: tuple[int, ...],
) -> AdaptationBundle:
    lines = sample.context.splitlines(keepends=True)
    if not boundary_lines or boundary_lines[0] != 0:
        raise RuntimeError("LongBench document boundary list must begin at line zero")
    if tuple(sorted(set(boundary_lines))) != boundary_lines:
        raise RuntimeError("LongBench document boundaries must be unique and ordered")
    boundaries = (*boundary_lines, len(lines))
    if boundaries[-2] >= len(lines):
        raise RuntimeError("LongBench natural-document boundary is outside the source context")
    prepared: list[PreparedArtifact] = []
    reconstructed: list[str] = []
    chunk_count = 0
    for document_index, (start, end) in enumerate(pairwise(boundaries), start=1):
        document = "".join(lines[start:end])
        records = []
        for chunk_index, text in enumerate(
            _text_chunks(document, LONGBENCH_CHUNK_CHARS),
            start=1,
        ):
            records.append(
                {
                    "document_index": document_index,
                    "chunk_index": chunk_index,
                    "text": text,
                }
            )
            reconstructed.append(text)
            chunk_count += 1
        content = _canonical_bytes(records)
        artifact_id = f"longbench-multidoc-{document_index:02d}"
        spec = ArtifactSpec(
            artifact_id=artifact_id,
            logical_type=(
                "document_chunks;fields=document_index,chunk_index,text;text_field=text"
            ),
            media_type="application/json",
            size_bytes=len(content),
            content_schema=ArtifactContentSchema(
                kind="record_array",
                fields={
                    "document_index": "integer",
                    "chunk_index": "integer",
                    "text": "string",
                },
                text_field="text",
                record_count=len(records),
                max_record_bytes=max(
                    (len(_canonical_bytes(record)) for record in records),
                    default=0,
                ),
            ),
            source_ref=f"prepared://longbench-v2/{sample.sample_id}/{artifact_id}",
        )
        prepared.append(PreparedArtifact.create(spec, content))
    source = sample.context.encode("utf-8")
    restored = "".join(reconstructed).encode("utf-8")
    if restored != source:
        raise RuntimeError("LongBench multi-document representation is not byte-reconstructable")
    identity = LongBenchV2Adapter(source_revision).adapt(sample)
    transformation = TransformationRecord(
        benchmark_id="longbench_v2",
        source_revision=source_revision,
        source_task_id=sample.sample_id,
        transformation="audited_natural_documents_to_ordered_lossless_text_chunks",
        information_preserved=True,
        order_preserved=True,
        gold_independent=True,
        notes="Declared document boundaries and every source character are preserved.",
        audit={
            "boundary_lines": list(boundary_lines),
            "document_count": len(boundary_lines),
            "chunk_count": chunk_count,
            "chunk_character_limit": LONGBENCH_CHUNK_CHARS,
            "source_sha256": hashlib.sha256(source).hexdigest(),
            "reconstructed_sha256": hashlib.sha256(restored).hexdigest(),
        },
    )
    task = identity.execution.task.model_copy(
        update={"artifacts": tuple(item.spec for item in prepared)}
    )
    execution = AdaptedExecutionCase(
        task=task,
        transformations=(transformation,),
        validity=assess_validity(
            (transformation,),
            query_equivalent=True,
            evaluator_equivalent=True,
        ),
    )
    return AdaptationBundle(execution, identity.private_evaluation, tuple(prepared))


def _longbench_structured_bundle(
    sample: LongBenchV2Sample,
    source_revision: str,
) -> AdaptationBundle:
    lines = sample.context.splitlines()
    header = lines[0]
    names = (
        "Symbol",
        "EndDate",
        "IndustryCode",
        "TotalAssets",
        "TotalLiability",
        "IntangibleAsset",
        "NetProfit",
        "OperatingEvenue",
        "OperatingCost",
        "OperationProfit",
    )
    if tuple(header.split()) != names:
        raise RuntimeError("LongBench structured header drift")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        raw_values = line.split()
        if len(raw_values) != len(names):
            raise RuntimeError(
                f"LongBench structured row {line_number} has {len(raw_values)} fields"
            )
        values = dict(zip(names, raw_values, strict=True))
        record: dict[str, Any] = {
            "Symbol": values["Symbol"],
            "EndDate": values["EndDate"],
            "IndustryCode": (
                None if values["IndustryCode"] == "NaN" else values["IndustryCode"]
            ),
        }
        for name in names[3:]:
            raw = values[name]
            record[name] = None if raw in {"", "NaN"} else float(raw)
        records.append(record)
    if len(records) != 17_071:
        raise RuntimeError(f"unexpected LongBench structured record count: {len(records)}")
    content = _canonical_bytes(records)
    artifact_id = "longbench-structured-records"
    spec = ArtifactSpec(
        artifact_id=artifact_id,
        logical_type=(
            "structured_records;fields="
            + ",".join(
                f"{name}:{'string' if index < 3 else 'number'}"
                f"{'?' if index >= 2 else ''}"
                for index, name in enumerate(names)
            )
        ),
        media_type="application/json",
        size_bytes=len(content),
        content_schema=ArtifactContentSchema(
            kind="record_array",
            fields={
                name: (
                    "string"
                    if index < 2
                    else "string|null"
                    if index == 2
                    else "number|null"
                )
                for index, name in enumerate(names)
            },
            record_count=len(records),
            max_record_bytes=max(
                (len(_canonical_bytes(record)) for record in records),
                default=0,
            ),
        ),
        source_ref=f"prepared://longbench-v2/{sample.sample_id}/{artifact_id}",
    )
    prepared = PreparedArtifact.create(spec, content)
    identity = LongBenchV2Adapter(source_revision).adapt(sample)
    transformation = TransformationRecord(
        benchmark_id="longbench_v2",
        source_revision=source_revision,
        source_task_id=sample.sample_id,
        transformation="whitespace_table_to_typed_json_records",
        information_preserved=True,
        order_preserved=True,
        gold_independent=True,
        notes=(
            "Every natural source row and field is preserved; source NaN missing-value "
            "sentinels are deterministically represented as JSON null."
        ),
        audit={
            "source_sha256": hashlib.sha256(sample.context.encode()).hexdigest(),
            "adapted_sha256": prepared.sha256_hex,
            "record_count": len(records),
            "columns": list(names),
            "missing_value_normalization": "NaN or empty -> JSON null",
        },
    )
    execution = AdaptedExecutionCase(
        task=identity.execution.task.model_copy(update={"artifacts": (spec,)}),
        transformations=(transformation,),
        validity=assess_validity(
            (transformation,), query_equivalent=True, evaluator_equivalent=True
        ),
    )
    return AdaptationBundle(execution, identity.private_evaluation, (prepared,))


def _load_video_bundles(
    rows: list[dict[str, Any]],
    *,
    task_path: Path,
    answer_path: Path,
    source_root: Path,
    source_revision: str,
) -> dict[str, AdaptationBundle]:
    raw = _yaml(task_path)
    task_index = {str(item["task_id"]): item for item in raw["tasks"]}
    private_raw = json.loads(answer_path.read_text(encoding="utf-8"))
    answer_index = {str(item["task_id"]): item for item in private_raw["records"]}
    bundles: dict[str, AdaptationBundle] = {}
    for row in rows:
        source_task_id = str(row["source_task_id"])
        question_id = str(row["question_id"])
        source_task = task_index[source_task_id]
        questions = {str(item["question_id"]): item for item in source_task["questions"]}
        question = questions[question_id]
        answers = {
            str(item["question_id"]): str(item["correct_option"])
            for item in answer_index[source_task_id]["answers"]
        }
        source_path = source_root / str(row["source_filename"])
        content = source_path.read_bytes()
        artifact_id = f"video-mme-{source_task_id.rsplit(':', 1)[-1]}-complete-original"
        spec = SourceArtifact(
            artifact_id=artifact_id,
            logical_type=(
                "complete_original_video;full_timeline;"
                f"duration_seconds={float(source_task['duration_s']):g}"
            ),
            media_type="video/mp4",
            size_bytes=len(content),
            source_ref=f"dataset://video-mme/{source_task_id}/complete-video",
            content_schema=ArtifactContentSchema(
                kind="video",
                codec="av1",
                duration_seconds=float(source_task["duration_s"]),
            ),
        )
        options = tuple(
            VideoMMEOption(label=str(label), text=str(text))
            for label, text in cast(dict[str, Any], question["options"]).items()
        )
        sample = VideoMMESample(
            sample_id=question_id,
            video=spec,
            question=str(question["prompt"]),
            options=options,
            answer_label=answers[question_id],
        )
        adapted = VideoMMEAdapter(source_revision).adapt(sample)
        prepared = PreparedArtifact.create(adapted.execution.task.artifacts[0], content)
        bundles[str(row["label"])] = AdaptationBundle(
            adapted.execution,
            adapted.private_evaluation,
            (prepared,),
        )
    return bundles


def _legacy_multihop_task_id(query: str) -> str:
    data = _canonical_bytes({"query": query})
    return f"multihop-rag-train-{hashlib.sha256(data).hexdigest()[:24]}"


def _multihop_bundle(
    row: dict[str, Any],
    corpus_rows: list[dict[str, Any]],
    query_rows: list[dict[str, Any]],
    source_revision: str,
) -> AdaptationBundle:
    ordinal = int(row["source_row_ordinal"])
    query_row = query_rows[ordinal]
    expected_id = str(row["source_task_id"])
    if _legacy_multihop_task_id(str(query_row["query"])) != expected_id:
        raise RuntimeError(f"MultiHop source row identity drift: {expected_id}")
    sample = MultiHopRAGSample(
        sample_id=expected_id,
        query=str(query_row["query"]),
        evidence_list=tuple(
            MultiHopEvidence.model_validate(item) for item in query_row["evidence_list"]
        ),
        question_type=str(query_row["question_type"]),
        answer=str(query_row["answer"]),
    )
    corpus = tuple(MultiHopCorpusDocument.model_validate(item) for item in corpus_rows)
    adapted = MultiHopRAGAdapter(source_revision).adapt(
        sample,
        FullCorpusSetting(
            corpus=corpus,
            shard_count=3,
            artifact_prefix="full-corpus-shard",
            max_chunk_chars=MULTIHOP_CHUNK_CHARS,
        ),
    )
    prepared: list[PreparedArtifact] = []
    specs: list[ArtifactSpec] = []
    for item in adapted.prepared_artifacts:
        spec = item.spec.model_copy(
            update={
                "logical_type": (
                    "corpus_shard;fields=title,body,author,source,published_at,"
                    "category,url;text_field=body"
                )
            }
        )
        specs.append(spec)
        prepared.append(
            PreparedArtifact(spec=spec, content=item.content, sha256_hex=item.sha256_hex)
        )
    execution = adapted.execution.model_copy(
        update={"task": adapted.execution.task.model_copy(update={"artifacts": tuple(specs)})}
    )
    return AdaptationBundle(execution, adapted.private_evaluation, tuple(prepared))


def load_bundles(config: dict[str, Any], args: argparse.Namespace) -> dict[str, AdaptationBundle]:
    task_rows = cast(list[dict[str, Any]], config["dataset"]["tasks"])
    revisions = cast(dict[str, str], config["dataset"]["revisions"])
    by_family: dict[str, list[dict[str, Any]]] = {}
    for row in task_rows:
        by_family.setdefault(str(row["family"]), []).append(row)
    bundles = _load_video_bundles(
        by_family["video_mme"],
        task_path=args.video_tasks,
        answer_path=args.video_answers,
        source_root=args.video_sources,
        source_revision=revisions["video_mme"],
    )
    longbench_ids = {
        str(row["source_task_id"])
        for family in ("longbench_multidoc", "longbench_structured")
        for row in by_family.get(family, [])
    }
    samples = _load_longbench_samples(args.longbench_samples, longbench_ids)
    for multidoc_row in by_family.get("longbench_multidoc", []):
        multidoc_id = str(multidoc_row["source_task_id"])
        bundles[str(multidoc_row["label"])] = _longbench_multidoc_bundle(
            samples[multidoc_id],
            revisions["longbench_v2"],
            tuple(int(value) for value in multidoc_row["boundary_lines"]),
        )
    for structured_row in by_family.get("longbench_structured", []):
        structured_id = str(structured_row["source_task_id"])
        bundles[str(structured_row["label"])] = _longbench_structured_bundle(
            samples[structured_id],
            revisions["longbench_v2"],
        )
    corpus_rows = cast(list[dict[str, Any]], json.loads(args.multihop_corpus.read_text("utf-8")))
    query_rows = cast(list[dict[str, Any]], json.loads(args.multihop_queries.read_text("utf-8")))
    if len(corpus_rows) != 609:
        raise RuntimeError(
            f"expected complete 609-document MultiHop corpus, got {len(corpus_rows)}"
        )
    for row in by_family.get("multihop_rag", []):
        bundles[str(row["label"])] = _multihop_bundle(
            row,
            corpus_rows,
            query_rows,
            revisions["multihop_rag"],
        )
    expected_order = [str(row["label"]) for row in task_rows]
    if set(bundles) != set(expected_order):
        raise RuntimeError("loaded bundles do not exactly match frozen task labels")
    return {label: bundles[label] for label in expected_order}


def _placement_map(
    config: dict[str, Any],
    label: str,
    bundle: AdaptationBundle,
) -> dict[str, str]:
    agents = [str(item) for item in config["execution"]["initial_placement"][label]]
    artifacts = [item.spec.artifact_id for item in bundle.prepared_artifacts]
    if len(agents) != len(artifacts):
        raise RuntimeError(f"initial-placement arity mismatch: {label}")
    return dict(zip(artifacts, agents, strict=True))


def _environment(
    config: dict[str, Any],
    label: str,
    bundle: AdaptationBundle,
) -> EnvironmentSpec:
    base = EnvironmentSpec.model_validate(
        _yaml(REPO / "configs/local/heterogeneous-v1-preflight.yaml")["environment"]
    )
    placements = _placement_map(config, label, bundle)
    return base.model_copy(
        update={
            "initial_placements": tuple(
                ArtifactPlacement(artifact_id=artifact_id, agent_id=agent_id)
                for artifact_id, agent_id in placements.items()
            )
        }
    )


def _workload(
    bundle: AdaptationBundle,
    environment: EnvironmentSpec,
    operations: tuple[str, ...],
    max_agents: int,
) -> WorkloadSpec:
    return WorkloadSpec.from_task_environment(
        bundle.execution.task,
        environment,
        available_operations=operations,
        max_agents=max_agents,
    )


def _source_manifest(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    video_filenames = {
        str(row["source_filename"])
        for row in config["dataset"]["tasks"]
        if row["family"] == "video_mme"
    }
    return {
        "video_tasks_sha256": _sha256(args.video_tasks),
        "video_answers_sha256": _sha256(args.video_answers),
        "video_sources": {
            path.name: {"size_bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in sorted(args.video_sources.glob("*.mp4"))
            if path.name in video_filenames
        },
        "longbench_samples": {
            "size_bytes": args.longbench_samples.stat().st_size,
            "sha256": _sha256(args.longbench_samples),
        },
        "multihop_corpus": {
            "size_bytes": args.multihop_corpus.stat().st_size,
            "sha256": _sha256(args.multihop_corpus),
        },
        "multihop_queries": {
            "size_bytes": args.multihop_queries.stat().st_size,
            "sha256": _sha256(args.multihop_queries),
        },
    }


def prepare(
    config: dict[str, Any],
    bundles: dict[str, AdaptationBundle],
    args: argparse.Namespace,
) -> None:
    freeze_root = args.output / "freeze"
    if freeze_root.exists():
        raise RuntimeError("freeze already exists; refusing overwrite")
    manifest: dict[str, Any] = {
        "experiment_id": config["experiment_id"],
        "code_revision": _code_revision(),
        "network": "native_unshaped",
        "scheduler": "B0_LOCALITY_AWARE_MYOPIC",
        "planner_calls_per_task": 1,
        "retry": False,
        "replacement": False,
        "planner_visibility": {
            "visible": [
                "sanitized_task",
                "available_model_instances",
                "system_derived_feasible_operators",
            ],
            "hidden": [
                "bandwidth",
                "rtt",
                "physical_placement",
                "load",
                "queue",
                "gold",
                "supporting_evidence",
                "evaluator_metadata",
                "source_ref",
            ],
        },
        "source_files": {
            key: value
            for key, value in _source_manifest(args, config).items()
            if key != "video_answers_sha256"
        },
        "tasks": {},
    }
    _write_json(
        args.output / "private/source-manifest.json",
        _source_manifest(args, config),
    )
    task_rows = cast(list[dict[str, Any]], config["dataset"]["tasks"])
    for row in task_rows:
        label = str(row["label"])
        bundle = bundles[label]
        if not (
            bundle.execution.validity.information_equivalent
            and bundle.execution.validity.query_equivalent
            and bundle.execution.validity.evaluator_equivalent
        ):
            raise RuntimeError(f"representation is not benchmark-faithful: {label}")
        task_root = freeze_root / label
        _write_json(
            task_root / "task-planner-view.json",
            logical_task_payload(bundle.execution.task),
        )
        private_evaluation = cast(Any, bundle.private_evaluation)
        _write_json(
            args.output / "private" / label / "task-contract.json",
            bundle.execution.task.model_dump(mode="json"),
        )
        _write_json(
            args.output / "private" / label / "private-evaluation.json",
            private_evaluation.model_dump(mode="json"),
        )
        manifest["tasks"][label] = {
            "source_task_id": row["source_task_id"],
            "task_id": bundle.execution.task.task_id,
            "family": row["family"],
            "selection_reason": row["selection_reason"],
            "public_representation_sha256": _public_bundle_digest(bundle),
            "initial_artifact_placement": _placement_map(config, label, bundle),
            "adaptation_provenance": {
                "transformations": [
                    item.model_dump(mode="json")
                    for item in bundle.execution.transformations
                ],
                "validity": bundle.execution.validity.model_dump(mode="json"),
            },
            "artifacts": [
                {
                    "artifact_id": item.spec.artifact_id,
                    "logical_type": item.spec.logical_type,
                    "media_type": item.spec.media_type,
                    "size_bytes": item.spec.size_bytes,
                    "sha256": item.sha256_hex,
                }
                for item in bundle.prepared_artifacts
            ],
            "planning_status": "pending",
        }
    _write_json(freeze_root / "manifest.json", manifest)


def _private_structural_leakage(text: str) -> list[str]:
    return sorted(
        key
        for key in (
            "source_ref",
            "evaluator_id",
            "gold_answer",
            "gold_answers",
            "supporting_evidence",
            "evidence_list",
        )
        if re.search(rf'\b{re.escape(key)}\b', text)
    )


async def freeze_plans(
    config: dict[str, Any],
    bundles: dict[str, AdaptationBundle],
    args: argparse.Namespace,
) -> None:
    manifest_path = args.output / "freeze/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["planner_execution_revision"] = _code_revision()
    _write_json(manifest_path, manifest)
    _load_key(args.api_key_file)
    aliases = {
        str(key): str(value)
        for key, value in config["planner"]["model_instance_aliases"].items()
    }
    operations = tuple(str(item) for item in config["planner"]["available_operations"])
    max_agents = int(config["planner"]["max_agents"])
    alias_environment = _alias_environment(aliases)
    registry = build_operator_catalog()
    planner_config = load_planner_config(REPO / str(config["planner"]["config"]))
    backend, client = build_model_backend(planner_config.model)
    try:
        for label, bundle in bundles.items():
            attempt_root = args.output / "planner-attempts" / label
            if attempt_root.exists():
                raise RuntimeError(f"Planner attempt exists; retry forbidden: {label}")
            planner_workload = _alias_workload(bundle, aliases, operations, max_agents)
            capturing_backend = CapturingCompletionBackend(backend)
            planner = LLMWorkflowPlanner(capturing_backend, registry, alias_environment)
            prompt = planner.render_prompt(bundle.execution.task, planner_workload)
            leakage = _private_structural_leakage(prompt)
            if leakage:
                raise RuntimeError(f"private fields leaked into Planner prompt: {label}/{leakage}")
            attempt_root.mkdir(parents=True, exist_ok=False)
            (attempt_root / "planner-prompt.txt").write_text(prompt, encoding="utf-8")
            task_root = args.output / "freeze" / label
            _write_json(
                task_root / "workload-planner-view.json",
                planner_workload.model_dump(mode="json"),
            )
            started = perf_counter()
            try:
                outcome = await planner.plan(bundle.execution.task, planner_workload)
                execution_plan = _translate_plan(outcome.plan, aliases)
                environment = _environment(config, label, bundle)
                execution_plan.validate_against(
                    bundle.execution.task,
                    environment,
                    registry,
                    operations,
                )
                execution_plan.terminal_model_node()
            except Exception as exc:  # one-shot invalid Planner output is evidence
                completion = capturing_backend.completion
                _write_json(
                    attempt_root / "planner-attempt.json",
                    {
                        "call_count": 1,
                        "status": "invalid",
                        "latency_ms": (perf_counter() - started) * 1000,
                        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                        "raw_response": completion.text if completion else None,
                        "model_telemetry": (
                            completion.telemetry.model_dump(mode="json")
                            if completion
                            else None
                        ),
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                )
                manifest["tasks"][label]["planning_status"] = "invalid"
                manifest["tasks"][label]["planning_error"] = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
                _write_json(manifest_path, manifest)
                continue
            latency_ms = (perf_counter() - started) * 1000
            planner_json = outcome.plan.model_dump(mode="json")
            execution_json = execution_plan.model_dump(mode="json")
            planner_hash = _canonical_hash(planner_json)
            execution_hash = _canonical_hash(execution_json)
            execution_workload = _workload(
                bundle,
                environment,
                operations,
                max_agents,
            )
            _write_json(task_root / "planner-workflow-plan.json", planner_json)
            _write_json(task_root / "workflow-plan.json", execution_json)
            _write_json(
                task_root / "workload-execution.json",
                execution_workload.model_dump(mode="json"),
            )
            _write_json(
                task_root / "planner-call.json",
                {
                    "call_count": 1,
                    "latency_ms": latency_ms,
                    "model_telemetry": (
                        outcome.model_telemetry.model_dump(mode="json")
                        if outcome.model_telemetry
                        else None
                    ),
                    "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                    "planner_plan_sha256": planner_hash,
                    "workflow_plan_sha256": execution_hash,
                },
            )
            _write_json(
                attempt_root / "planner-attempt.json",
                {
                    "call_count": 1,
                    "status": "valid",
                    "latency_ms": latency_ms,
                    "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                    "raw_response": capturing_backend.completion.text,
                    "model_telemetry": (
                        outcome.model_telemetry.model_dump(mode="json")
                        if outcome.model_telemetry
                        else None
                    ),
                },
            )
            manifest["tasks"][label].update(
                {
                    "planning_status": "valid",
                    "planner_plan_sha256": planner_hash,
                    "workflow_plan_sha256": execution_hash,
                }
            )
            _write_json(manifest_path, manifest)
    finally:
        if client is not None:
            await client.close()


def _load_plan(output: Path, label: str) -> WorkflowPlan:
    return WorkflowPlan.model_validate_json(
        (output / "freeze" / label / "workflow-plan.json").read_text(encoding="utf-8")
    )


async def preflight(
    config: dict[str, Any],
    bundles: dict[str, AdaptationBundle],
    output: Path,
    native_network_snapshot: Path | None,
) -> None:
    if native_network_snapshot is None:
        network = await _native_network_snapshot()
    else:
        network = cast(
            dict[str, str],
            json.loads(native_network_snapshot.read_text(encoding="utf-8")),
        )
        shaped = {
            agent_id: value
            for agent_id, value in network.items()
            if "qdisc htb 1:" in value or "netem" in value
        }
        if shaped:
            raise RuntimeError(
                f"provided native snapshot contains active shaping: {sorted(shaped)}"
            )
    base = EnvironmentSpec.model_validate(
        _yaml(REPO / "configs/local/heterogeneous-v1-preflight.yaml")["environment"]
    )
    async with AsyncExitStack() as stack:
        clients = await _clients(stack)
        await validate_worker_surfaces(base, build_operator_catalog(), clients)
        states = {
            key: (await value.get_state()).model_dump(mode="json")
            for key, value in clients.items()
        }
    if any(not state["available"] or state["in_flight"] != 0 for state in states.values()):
        raise RuntimeError("all workers must be idle and available before the baseline")
    _write_json(
        output / "preflight.json",
        {
            "code_revision": _code_revision(),
            "network": "native_unshaped",
            "qdisc_snapshot": network,
            "worker_states": states,
            "bundle_count": len(bundles),
            "all_representations_official_equivalent": all(
                item.execution.validity.setting_kind == "official_equivalent"
                for item in bundles.values()
            ),
            "scheduler": config["execution"]["scheduler"],
        },
    )


async def _preload(
    config: dict[str, Any],
    label: str,
    bundle: AdaptationBundle,
    clients: dict[str, Any],
    *,
    remove_existing: bool,
) -> None:
    artifact_ids = tuple(item.spec.artifact_id for item in bundle.prepared_artifacts)
    if remove_existing:
        await _remove_artifacts(("A4", "A5", "A28", "strong-4090"), artifact_ids)
    else:
        states = {key: await value.get_state() for key, value in clients.items()}
        stale = sorted(
            (agent_id, item.artifact_id)
            for agent_id, state in states.items()
            for item in state.artifacts
            if item.artifact_id in artifact_ids
        )
        if stale:
            raise RuntimeError(f"experiment artifact IDs are not clean before preload: {stale}")
    placements = _placement_map(config, label, bundle)
    for item in bundle.prepared_artifacts:
        response = await clients[placements[item.spec.artifact_id]].put_artifact(
            item.spec.artifact_id,
            item.spec.media_type,
            item.content,
            item.sha256_hex,
        )
        if response.sha256_hex != item.sha256_hex:
            raise RuntimeError(f"preload checksum mismatch: {item.spec.artifact_id}")


async def _assert_placement(
    config: dict[str, Any],
    label: str,
    bundle: AdaptationBundle,
    clients: dict[str, Any],
) -> None:
    placements = _placement_map(config, label, bundle)
    states = {key: await value.get_state() for key, value in clients.items()}
    for item in bundle.prepared_artifacts:
        locations = []
        for agent_id, state in states.items():
            observed = {value.artifact_id: value for value in state.artifacts}.get(
                item.spec.artifact_id
            )
            if observed is not None:
                if observed.sha256_hex != item.sha256_hex:
                    raise RuntimeError(
                        f"artifact checksum mismatch: {agent_id}/{item.spec.artifact_id}"
                    )
                locations.append(agent_id)
        expected = [placements[item.spec.artifact_id]]
        if locations != expected:
            raise RuntimeError(
                f"initial placement mismatch: {item.spec.artifact_id}/{locations}/{expected}"
            )


def _trace_audit(path: Path, run_id: str) -> dict[str, Any]:
    events = [
        cast(dict[str, Any], json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    chain = bool(events) and all(
        item["run_id"] == run_id
        and item["step_id"].startswith(f"{index:06d}-")
        and item["parent_id"] == (events[index - 1]["step_id"] if index else None)
        for index, item in enumerate(events)
    )
    serialized_agents = json.dumps(
        [item for item in events if str(item["event_type"]).startswith("agent.")],
        ensure_ascii=False,
        sort_keys=True,
    )
    terminal = str(events[-1]["event_type"]) if events else None
    handoffs = [
        item["payload"]
        for item in events
        if item["event_type"] == "agent.information.received"
    ]
    return {
        "event_count": len(events),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "parent_chain_valid": chain,
        "terminal_event": terminal,
        "reconstructable": chain and terminal in {"run.end", "run.failed"},
        "agent_private_field_leakage": _private_structural_leakage(serialized_agents),
        "information_object_handoffs": handoffs,
    }


def _run_audit(
    label: str,
    bundle: AdaptationBundle,
    plan: WorkflowPlan,
    result: PersistedWorkflowRunResult,
    planner_call: dict[str, Any],
) -> dict[str, Any]:
    trace = _trace_audit(Path(result.trace_path), result.run_id)
    workflow = result.workflow
    shape = _workflow_shape(plan)
    records = workflow.records if workflow else ()
    operators = {item.node_id: item.operator for item in plan.nodes}
    model_calls = [
        {
            "node_id": item.node_id,
            "agent_id": item.scheduler_decision.logical_agent_id,
            "deployment_id": (
                item.execution.deployment_id if item.execution is not None else None
            ),
            "telemetry": (
                item.execution.model_telemetry.model_dump(mode="json")
                if item.execution is not None and item.execution.model_telemetry is not None
                else None
            ),
        }
        for item in records
        if operators[item.node_id] == "invoke_model"
    ]
    tool_calls = [
        {
            "node_id": item.node_id,
            "operator": operators[item.node_id],
            "agent_id": item.scheduler_decision.logical_agent_id,
            "physical_agent_ids": (
                list(item.execution.agent_ids) if item.execution is not None else []
            ),
            "operator_latency_ms": (
                item.execution.operator_latency_ms if item.execution is not None else None
            ),
        }
        for item in records
        if operators[item.node_id] != "invoke_model"
    ]
    transfers = [
        {"node_id": item.node_id, **transfer.model_dump(mode="json")}
        for item in records
        if item.execution is not None
        for transfer in item.execution.transfers
    ]
    faithful = bool(
        bundle.execution.validity.information_equivalent
        and bundle.execution.validity.query_equivalent
        and bundle.execution.validity.evaluator_equivalent
        and not trace["agent_private_field_leakage"]
    )
    execution_valid = bool(
        result.execution_completed
        and workflow is not None
        and workflow.completed
        and result.evaluation is not None
        and result.evaluation.format_valid
        and trace["reconstructable"]
    )
    telemetry = result.telemetry
    workflow_telemetry = workflow.telemetry if workflow else None
    return {
        "task": label,
        "task_id": bundle.execution.task.task_id,
        "benchmark_faithful": faithful,
        "plan_valid": True,
        "execution_valid": execution_valid,
        "retained_valid_blind_sample": faithful and execution_valid,
        "workflow_plan_sha256": _canonical_hash(plan.model_dump(mode="json")),
        "workflow_shape": shape,
        "nodes": [item.model_dump(mode="json") for item in plan.nodes],
        "edges": [item.model_dump(mode="json") for item in plan.edges],
        "node_final_states": workflow.state.node_status if workflow else None,
        "agent_final_states": (
            {item.agent_id: item.status for item in workflow.agent_states}
            if workflow
            else None
        ),
        "model_calls": model_calls,
        "tool_calls": tool_calls,
        "information_object_handoffs": trace["information_object_handoffs"],
        "actual_placements": {
            item.node_id: list(item.execution.agent_ids)
            for item in records
            if item.execution is not None
        },
        "transfers": transfers,
        "transfer_bytes": telemetry.total_transfer_bytes if telemetry else None,
        "transfer_time_ms": telemetry.total_transfer_duration_ms if telemetry else None,
        "e2e_latency_ms": result.runner_e2e_latency_ms,
        "critical_path_latency_ms": (
            workflow_telemetry.critical_path_latency_ms if workflow_telemetry else None
        ),
        "parallel_overlap_ms": (
            workflow_telemetry.parallel_overlap_ms if workflow_telemetry else None
        ),
        "planner": planner_call,
        "terminal_answer": result.final_answer,
        "format_valid": result.evaluation.format_valid if result.evaluation else None,
        "benchmark_score": (
            result.evaluation.benchmark_score if result.evaluation else None
        ),
        "evaluator_details": result.evaluation.details if result.evaluation else None,
        "failure": result.failure.model_dump(mode="json") if result.failure else None,
        "trace": trace,
    }


async def run(
    config: dict[str, Any],
    bundles: dict[str, AdaptationBundle],
    output: Path,
    *,
    task_label: str | None,
    defer_artifact_cleanup: bool,
    recover_existing_run: bool,
) -> None:
    if not (output / "preflight.json").exists():
        raise RuntimeError("preflight evidence is missing")
    manifest_path = output / "freeze/manifest.json"
    freeze = json.loads(manifest_path.read_text(encoding="utf-8"))
    baseline_path = output / "baseline-manifest.json"
    operations = tuple(str(item) for item in config["planner"]["available_operations"])
    max_agents = int(config["planner"]["max_agents"])
    planner_config = load_planner_config(REPO / str(config["planner"]["config"]))
    if baseline_path.exists():
        baseline = cast(
            dict[str, Any],
            json.loads(baseline_path.read_text(encoding="utf-8")),
        )
    else:
        baseline = {
            "experiment_id": config["experiment_id"],
            "execution_revision": _code_revision(),
            "network": "native_unshaped",
            "scheduler": "B0_LOCALITY_AWARE_MYOPIC",
            "n": 1,
            "retry": False,
            "replacement": False,
            "tasks": [],
        }
        _write_json(baseline_path, baseline)
    completed_labels = {str(item["task"]) for item in baseline["tasks"]}
    labels = list(bundles)
    if task_label is not None:
        if task_label not in bundles:
            raise ValueError(f"unknown task label: {task_label}")
        labels = [task_label]
    task_order = {
        str(row["label"]): index
        for index, row in enumerate(config["dataset"]["tasks"], start=1)
    }
    for label in labels:
        if label in completed_labels:
            raise RuntimeError(f"task outcome exists; retry forbidden: {label}")
        bundle = bundles[label]
        index = task_order[label]
        frozen = freeze["tasks"][label]
        if frozen["planning_status"] != "valid":
            row = {
                "task": label,
                "task_id": bundle.execution.task.task_id,
                "plan_valid": False,
                "execution_attempted": False,
                "retained_valid_blind_sample": False,
                "planning_error": frozen.get("planning_error"),
            }
            baseline["tasks"].append(row)
            _write_json(output / "baseline-manifest.json", baseline)
            continue
        run_id = f"{index:02d}-{label}-native"
        plan = _load_plan(output, label)
        if frozen["workflow_plan_sha256"] != _canonical_hash(plan.model_dump(mode="json")):
            raise RuntimeError(f"frozen workflow hash drift: {label}")
        environment = _environment(config, label, bundle)
        run_root = output / "runs" / run_id
        if run_root.exists():
            if not recover_existing_run:
                raise RuntimeError(f"run exists; retry forbidden: {run_id}")
            result = PersistedWorkflowRunResult.model_validate_json(
                (run_root / "result.json").read_text(encoding="utf-8")
            )
            planner_call = json.loads(
                (output / "freeze" / label / "planner-call.json").read_text(
                    encoding="utf-8"
                )
            )
            audit = _run_audit(label, bundle, plan, result, planner_call)
            _write_json(run_root / "audit.json", audit)
            baseline["tasks"].append(
                {
                    "task": label,
                    "task_id": bundle.execution.task.task_id,
                    "run_id": run_id,
                    "plan_valid": True,
                    "execution_attempted": True,
                    "execution_valid": audit["execution_valid"],
                    "retained_valid_blind_sample": audit[
                        "retained_valid_blind_sample"
                    ],
                    "benchmark_score": audit["benchmark_score"],
                    "format_valid": audit["format_valid"],
                    "failure": audit["failure"],
                    "artifact_cleanup_deferred": True,
                    "audit_recovered_without_reexecution": True,
                }
            )
            _write_json(baseline_path, baseline)
            continue
        runner_config = RunnerConfig(
            environment=environment,
            worker_urls={
                "A4": "http://192.168.0.104:9104",
                "A5": "http://192.168.0.105:9105",
                "A28": "http://192.168.0.128:9128",
                "strong-4090": "http://192.168.0.12:9212",
            },
            planner=planner_config,
            output_root=output / "runs",
            http_timeout_seconds=1800,
        )
        result: PersistedWorkflowRunResult | None = None
        driver_error: Exception | None = None
        cleanup_error: Exception | None = None
        try:
            async with AsyncExitStack() as stack:
                clients = await _clients(stack)
                await validate_worker_surfaces(environment, build_operator_catalog(), clients)
                await _preload(
                    config,
                    label,
                    bundle,
                    clients,
                    remove_existing=not defer_artifact_cleanup,
                )
                await _assert_placement(config, label, bundle, clients)
                result = await PrepositionedWorkflowRunner(
                    runner_config,
                    _workload(bundle, environment, operations, max_agents),
                    LocalityAwareMyopicScheduler(),
                    worker_clients=clients,
                    planner=ScriptedWorkflowPlanner((plan,)),
                ).run(bundle, run_id=run_id)
        except Exception as exc:  # driver errors are harness confounders
            driver_error = exc
        finally:
            if not defer_artifact_cleanup:
                try:
                    await _remove_artifacts(
                        ("A4", "A5", "A28", "strong-4090"),
                        (
                            *_generated_ids(plan),
                            *(item.spec.artifact_id for item in bundle.prepared_artifacts),
                        ),
                    )
                except Exception as exc:
                    cleanup_error = exc
        if driver_error is not None or cleanup_error is not None or result is None:
            failure = {
                "task": label,
                "run_id": run_id,
                "system_harness_confounder": True,
                "driver_error": (
                    f"{type(driver_error).__name__}: {driver_error}" if driver_error else None
                ),
                "cleanup_error": (
                    f"{type(cleanup_error).__name__}: {cleanup_error}" if cleanup_error else None
                ),
            }
            baseline["tasks"].append(failure)
            baseline["stopped_on_system_harness_confounder"] = run_id
            _write_json(output / "baseline-manifest.json", baseline)
            raise RuntimeError(f"system/harness confounder at {run_id}: {failure}")
        planner_call = json.loads(
            (output / "freeze" / label / "planner-call.json").read_text(encoding="utf-8")
        )
        audit = _run_audit(label, bundle, plan, result, planner_call)
        _write_json(output / "runs" / run_id / "audit.json", audit)
        baseline["tasks"].append(
            {
                "task": label,
                "task_id": bundle.execution.task.task_id,
                "run_id": run_id,
                "plan_valid": True,
                "execution_attempted": True,
                "execution_valid": audit["execution_valid"],
                "retained_valid_blind_sample": audit["retained_valid_blind_sample"],
                "benchmark_score": audit["benchmark_score"],
                "format_valid": audit["format_valid"],
                "failure": audit["failure"],
                "artifact_cleanup_deferred": defer_artifact_cleanup,
            }
        )
        _write_json(baseline_path, baseline)


def report(config: dict[str, Any], bundles: dict[str, AdaptationBundle], output: Path) -> None:
    baseline = json.loads((output / "baseline-manifest.json").read_text(encoding="utf-8"))
    if len(baseline["tasks"]) != 6:
        raise RuntimeError("six one-shot task outcomes are required before reporting")
    rows: list[str] = []
    agent_counts: list[int] = []
    valid_count = 0
    quality_failures: list[str] = []
    replay_candidates: list[str] = []
    for item in baseline["tasks"]:
        label = item["task"]
        if not item.get("plan_valid"):
            error = item.get("planning_error") or {}
            rows.append(
                f"| {label} | invalid | — | — | — | — | — | — | "
                f"Planner `{error.get('type', 'unknown')}` |"
            )
            quality_failures.append(f"{label}: no quality observation because the plan was invalid")
            continue
        run_id = item["run_id"]
        audit = json.loads((output / "runs" / run_id / "audit.json").read_text("utf-8"))
        shape = audit["workflow_shape"]
        agents = int(shape["active_logical_agent_count"])
        agent_counts.append(agents)
        if audit["retained_valid_blind_sample"]:
            valid_count += 1
        score = audit["benchmark_score"]
        if score is not None and float(score) < 1.0:
            quality_failures.append(f"{label}: original benchmark score {score:g}")
        transfer_bytes = audit["transfer_bytes"]
        e2e = audit["e2e_latency_ms"]
        critical = audit["critical_path_latency_ms"]
        overlap = audit["parallel_overlap_ms"]
        outcome = "valid" if audit["retained_valid_blind_sample"] else "execution-invalid"
        rows.append(
            f"| {label} | {outcome} | {agents} | {len(audit['nodes'])} | "
            f"{len(audit['edges'])} | {score if score is not None else '—'} | "
            f"{e2e:.1f} | {transfer_bytes if transfer_bytes is not None else '—'} | "
            f"critical={critical if critical is not None else '—'}, "
            f"overlap={overlap if overlap is not None else '—'} |"
        )
        if audit["retained_valid_blind_sample"] and (
            transfer_bytes or shape["cross_agent_edges"] or agents > 1
        ):
            replay_candidates.append(label)
    single = sum(value == 1 for value in agent_counts)
    multi = sum(value > 1 for value in agent_counts)
    family_notes: list[str] = []
    for family in ("video_mme", "longbench", "multihop"):
        labels = [
            str(row["label"])
            for row in config["dataset"]["tasks"]
            if family in str(row["family"])
        ]
        descriptions = []
        for label in labels:
            item = next(value for value in baseline["tasks"] if value["task"] == label)
            if not item.get("plan_valid"):
                descriptions.append(f"{label}=invalid plan")
                continue
            audit = json.loads(
                (output / "runs" / item["run_id"] / "audit.json").read_text("utf-8")
            )
            sequence = " → ".join(node["operator"] for node in audit["nodes"])
            descriptions.append(
                f"{label}={audit['workflow_shape']['active_logical_agent_count']} agents, "
                f"`{sequence}`"
            )
        family_notes.append(f"- {family}: " + "; ".join(descriptions))
    report_path = REPO / "docs/blind-baseline-6task-v1-audit.md"
    report_path.write_text(
        "\n".join(
            [
                "# Six-task Blind Baseline v1 audit",
                "",
                "## Scope",
                "",
                "Six preselected tasks were attempted once with one Cloud Blind Planner call per "
                "task, no retry, no replacement, native/unshaped networking, and the unchanged B0 "
                "Locality-Aware Myopic scheduler. No 3/10/30 Mbps replay was started.",
                "",
                "Planner inputs contained only the sanitized task, opaque available model "
                "instances, and system-derived feasible operators. Physical placement, network "
                "state, worker load/queue, evaluator metadata, source references, gold, and "
                "supporting evidence remained private.",
                "",
                "All six representations passed information/query/evaluator equivalence before "
                "planning: original complete Video-MME files, lossless LongBench representations, "
                "and the complete 609-document MultiHop-RAG corpus. Exact hashes, provenance, "
                "placements, one-shot Planner evidence, result JSON, and reconstructable JSONL "
                f"traces are under `{output}`.",
                "",
                "## Outcomes",
                "",
                "| Task | Baseline validity | Agents | Nodes | Edges | Score | E2E ms | "
                "Transfer B | Timing detail |",
                "|---|---|---:|---:|---:|---:|---:|---:|---|",
                *rows,
                "",
                f"Retained valid Blind samples: {valid_count}/6. Among valid plans, single-agent "
                f"versus multi-agent distribution was {single}/{multi}.",
                "",
                "## Natural workflow characteristics",
                "",
                *family_notes,
                "",
                "## Quality failures",
                "",
                *(f"- {item}" for item in quality_failures),
                *(
                    []
                    if quality_failures
                    else ["- None; this is not a benchmark-level claim at n=1."]
                ),
                "",
                "Quality is reported separately and was not an acceptance gate. A sample was "
                "retained only when benchmark-faithful, plan-valid, and execution-valid.",
                "",
                "## Frozen-workflow replay candidates",
                "",
                *(
                    [f"- {item}" for item in replay_candidates]
                    if replay_candidates
                    else ["- None passed the validity and infrastructure-interest criteria."]
                ),
                "",
                "These are candidates only. No bandwidth shaping or replay was executed.",
                "",
            ]
        ),
        encoding="utf-8",
    )


async def main_async(args: argparse.Namespace) -> None:
    config = _yaml(args.config)
    bundles = load_bundles(config, args)
    if args.command == "prepare":
        prepare(config, bundles, args)
    elif args.command == "freeze":
        await freeze_plans(config, bundles, args)
    elif args.command == "preflight":
        await preflight(config, bundles, args.output, args.native_network_snapshot)
    elif args.command == "run":
        await run(
            config,
            bundles,
            args.output,
            task_label=args.task_label,
            defer_artifact_cleanup=args.defer_artifact_cleanup,
            recover_existing_run=args.recover_existing_run,
        )
    elif args.command == "report":
        report(config, bundles, args.output)
    elif args.command == "all":
        prepare(config, bundles, args)
        await freeze_plans(config, bundles, args)
        await preflight(config, bundles, args.output, args.native_network_snapshot)
        await run(
            config,
            bundles,
            args.output,
            task_label=args.task_label,
            defer_artifact_cleanup=args.defer_artifact_cleanup,
            recover_existing_run=args.recover_existing_run,
        )
        report(config, bundles, args.output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("prepare", "freeze", "preflight", "run", "report", "all"),
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--api-key-file", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--video-tasks", type=Path, required=True)
    parser.add_argument("--video-answers", type=Path, required=True)
    parser.add_argument("--video-sources", type=Path, required=True)
    parser.add_argument("--longbench-samples", type=Path, required=True)
    parser.add_argument("--multihop-corpus", type=Path, required=True)
    parser.add_argument("--multihop-queries", type=Path, required=True)
    parser.add_argument("--native-network-snapshot", type=Path)
    parser.add_argument("--task-label")
    parser.add_argument("--defer-artifact-cleanup", action="store_true")
    parser.add_argument("--recover-existing-run", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main_async(parse_args()))
