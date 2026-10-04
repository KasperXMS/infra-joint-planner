"""4090-only eighteen-task preparation and schedule freeze; no experiment calls.

All source/evaluation bodies stay remote. This module reuses existing adapters
and lossless text chunking, never uses a task outcome to select/replace a task.
The task/schedule freeze is not an execution/provider/accounting admission.
"""

from __future__ import annotations

import argparse
import inspect
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from blind_baseline_6task_v1 import (
    _legacy_multihop_task_id,
    _longbench_multidoc_bundle,
    _multihop_bundle,
    _public_bundle_digest,
    _sha256,
)
from large_scale_video_sources_v1 import DATASET, REVISION, require_remote, write_new

from infra_joint.agents.context import AgentTaskView
from infra_joint.benchmarks.base import AdaptationBundle, PreparedArtifact
from infra_joint.benchmarks.longbench_v2 import LongBenchV2Sample
from infra_joint.benchmarks.multihop_rag import MultiHopCorpusDocument
from infra_joint.benchmarks.video_mme import (
    SourceArtifact,
    VideoMMEAdapter,
    VideoMMEOption,
    VideoMMESample,
)
from infra_joint.control.provenance import provenance_sha256
from infra_joint.core.task import ArtifactContentSchema
from infra_joint.experiments.large_scale_protocol import (
    SEED,
    SelectedTask,
    phase_one_schedule,
    schedule_sha256,
    validate_task_set,
)

MULTIHOP_ROOT = Path("/home/super/xiaoming/blind_baseline_6task_v1/data")
LONGBENCH_SOURCE = Path(
    "/home/super/xiaoming/infra-bench/scenario-mining/data/longbench_v2/selected.jsonl"
)
MULTIHOP_REVISION = "71ac0d0bd1f951d2d6b70311f7d2ae404e1ffa82"
LONGBENCH_REVISION = "2b48e494f2c7a2f0af81aae178e05c7e1dde0fe9"
E_HISTORY = (
    ("longbench_v2", "66f7c780bb02136c067c35e8"),
    ("longbench_v2", "66faa8efbb02136c067c7357"),
    ("video_mme", "795-3"),
)
MULTIHOP_SELECTION = (
    (3, "multihop-rag-train-4b6de4acbde051fee1f727f3", "two-document cross-shard comparison"),
    (8, "multihop-rag-train-fe71f374676e35359d12c83e", "four-document inference; high volume"),
    (0, "multihop-rag-train-facda0bcd2ae340c909be414", "three-document, three-shard inference"),
    (17, "multihop-rag-train-29a31b9c1104c2e563cc501f", "three-document temporal reasoning"),
    (133, "multihop-rag-train-77510aa6e6be8914ec641d33", "three-document cross-shard comparison"),
    (4, "multihop-rag-train-9833c1c381017ce6e94f30e6", "three-document single-shard contrast"),
)
LONGBENCH_SELECTION = (
    ("66f2c44e821e116aacb2b826", (0, 5712), 2, "audited two-document Academic; hard medium"),
    ("66f94f9ebb02136c067c4fde", (0,), None, "Governmental Multi-Document QA; hard very long"),
    ("66fa0d88bb02136c067c5a8a", (0,), None, "Financial Multi-Document QA; hard long"),
    ("66fcf2f2bb02136c067c9169", (0,), None, "Multi-news Multi-Document QA; short-input contrast"),
    ("66f016e6821e116aacb25497", (0,), None, "Legal Multi-Document QA; hard medium"),
    ("66fa208bbb02136c067c5fc1", (0,), None, "Code Repository QA; large, symbol-focused proxy"),
)


def source_groups(boundaries: tuple[int, ...], audited_count: int | None) -> dict[str, Any]:
    """Prepared containers are not claimed to be an audited original source count."""
    if audited_count is not None and audited_count != len(boundaries):
        raise RuntimeError("Audited original document count differs from declared boundaries")
    return {
        "original_document_count": audited_count,
        "prepared_document_groups": len(boundaries),
        "boundary_lines": list(boundaries),
        "boundary_semantics": (
            "previously audited natural document starts"
            if audited_count is not None else
            "complete original context as one logical container; internal source boundaries unknown"
        ),
        "not_arbitrary_partition_claimed_as_natural_document": True,
    }


def original_options(raw: list[str]) -> tuple[VideoMMEOption, ...]:
    result = []
    for option in raw:
        label, separator, text = option.partition(". ")
        if not separator or len(label) != 1 or not label.isupper() or not text:
            raise RuntimeError("Original option encoding is not safely parseable")
        result.append(VideoMMEOption(label=label, text=text))
    return tuple(result)


def prepare_video(row: dict[str, Any], preparation: Path) -> AdaptationBundle:
    question_id = row["question_id"]
    originals = json.loads((preparation / "original-videomme-annotation-001"
                            / "annotation-private.json").read_text(encoding="utf-8"))
    source_row = next(value for value in originals if value["question_id"] == question_id)
    path = preparation / f"video-original-{question_id}-001"
    provenance = json.loads((path / "provenance.json").read_text(encoding="utf-8"))
    media = json.loads((path / "media.json").read_text(encoding="utf-8"))
    source = path / Path(row["member"]).name
    if (provenance["dataset"] != DATASET or provenance["revision"] != REVISION
            or _sha256(source) != provenance["sha256"]
            or source.stat().st_size != row["source_bytes"]):
        raise RuntimeError("Pinned original Video-MME source drift")
    streams = [stream for stream in media["streams"] if stream["codec_type"] == "video"]
    if len(streams) != 1:
        raise RuntimeError("Expected exactly one original video stream")
    duration = float(media["format"]["duration"])
    artifact = SourceArtifact(
        artifact_id=f"video-mme-{question_id.split('-')[0]}-complete-original",
        logical_type=f"complete_original_video;full_timeline;duration_seconds={duration:g}",
        media_type="video/mp4", size_bytes=source.stat().st_size,
        source_ref=f"dataset://video-mme/{question_id}/complete-video",
        content_schema=ArtifactContentSchema(
            kind="video", codec=streams[0]["codec_name"], duration_seconds=duration),
    )
    sample = VideoMMESample(
        sample_id=question_id, video=artifact, question=source_row["question"],
        options=original_options(source_row["options"]), answer_label=source_row["answer"],
    )
    identity = VideoMMEAdapter(REVISION).adapt(sample)
    return AdaptationBundle(identity.execution, identity.private_evaluation, (
        PreparedArtifact.create(identity.execution.task.artifacts[0], source.read_bytes()),
    ))


def persist_bundle(
    output: Path, task: SelectedTask, bundle: AdaptationBundle,
    source: dict[str, Any], placements: tuple[str, ...],
) -> dict[str, Any]:
    folder = output / f"{task.family}-{task.position}"
    folder.mkdir()
    if len(placements) != len(bundle.prepared_artifacts):
        raise RuntimeError("Every initial artifact needs one frozen placement")
    private = bundle.private_evaluation
    private_value = private.model_dump(mode="json", by_alias=True)  # type: ignore[attr-defined]
    write_new(folder / "private-evaluation.json", private_value)
    write_new(folder / "execution.json", bundle.execution.model_dump(mode="json", by_alias=True))
    agent_view = AgentTaskView.from_contract(bundle.execution.task).model_dump(
        mode="json", by_alias=True)
    write_new(folder / "agent-task-view.json", agent_view)
    prepared = []
    for item, owner in zip(bundle.prepared_artifacts, placements, strict=True):
        suffix = ".mp4" if item.spec.media_type == "video/mp4" else ".json"
        file = folder / (item.spec.artifact_id + suffix)
        with file.open("xb") as stream:
            stream.write(item.content)
        prepared.append({"artifact_id": item.spec.artifact_id, "path": str(file),
                         "media_type": item.spec.media_type, "bytes": item.spec.size_bytes,
                         "sha256": item.sha256_hex, "initial_worker": owner})
    evaluator_file = inspect.getsourcefile(type(private.build_evaluator()))
    if evaluator_file is None:
        raise RuntimeError("Cannot hash the original evaluator implementation")
    receipt = {
        "family": task.family, "source_task_id": task.source_task_id, "position": task.position,
        "task_bundle_sha256": _public_bundle_digest(bundle),
        "agent_task_sha256": provenance_sha256(agent_view),
        "private_evaluation_sha256": _sha256(folder / "private-evaluation.json"),
        "evaluator_implementation_sha256": _sha256(Path(evaluator_file)),
        "source": source, "artifacts": prepared,
        "initial_bytes": sum(item["bytes"] for item in prepared),
        "output_contract": bundle.execution.task.output_contract.model_dump(
            mode="json", by_alias=True),
        "validity": bundle.execution.validity.model_dump(mode="json"),
        "candidate_reduction_ratio": None,
    }
    write_new(folder / "receipt.json", receipt)
    return receipt


def freeze(output: Path, preparation: Path, rules_manifest: Path) -> dict[str, Any]:
    output = require_remote(output)
    preparation = require_remote(preparation / "task-freeze-access-guard").parent
    if output.exists():
        raise FileExistsError("Task freeze may not overwrite an earlier selection")
    rules = json.loads(rules_manifest.read_text(encoding="utf-8"))
    if (rules["rules_sha256"] !=
            "6b2152aaf9c3e1ba90deacd4031bddc8870e0ac01e32c72be68fb24dc0b43be9"
            or provenance_sha256(rules["rules"]) != rules["rules_sha256"]
            or rules["source_manifest_sha256"] !=
            "bd10d6b146c42fe32e0888ca2138584c389d439e7e45aef186563e5bb7e15481"
            or tuple(rules["source_tasks"]) != (
                "longbench-multidoc-financial", "longbench-multidoc-news", "video-mme-795-3")):
        raise RuntimeError("Independent frozen E rules/history identity mismatch")
    queries = json.loads((MULTIHOP_ROOT / "MultiHopRAG.json").read_text(encoding="utf-8"))
    corpus = json.loads((MULTIHOP_ROOT / "corpus.json").read_text(encoding="utf-8"))
    corpus_sha256 = _sha256(MULTIHOP_ROOT / "corpus.json")
    query_file_sha256 = _sha256(MULTIHOP_ROOT / "MultiHopRAG.json")
    corpus_index = {doc["url"]: doc for doc in corpus}
    if len(corpus_index) != len(corpus):
        raise RuntimeError("Ambiguous source URLs: private support mapping needs audit")
    longbench = {value["_id"]: value for value in (
        json.loads(line) for line in LONGBENCH_SOURCE.open(encoding="utf-8"))}
    video_selection = json.loads((preparation / "video-selection-001"
                                 / "selection.json").read_text(encoding="utf-8"))
    tasks = [SelectedTask("multihop_rag", source_id, position)
             for position, (_, source_id, _) in enumerate(MULTIHOP_SELECTION, start=1)]
    tasks += [SelectedTask("longbench_v2", source_id, position)
              for position, (source_id, _, _, _) in enumerate(LONGBENCH_SELECTION, start=1)]
    tasks += [SelectedTask("video_mme", row["question_id"], row["position"])
              for row in video_selection["tasks"]]
    selected = validate_task_set(tasks, e_history_tasks=E_HISTORY)
    output.mkdir(parents=True)
    receipts = []
    for position, (ordinal, source_id, rationale) in enumerate(MULTIHOP_SELECTION, start=1):
        query = queries[ordinal]
        if _legacy_multihop_task_id(query["query"]) != source_id:
            raise RuntimeError("Original MultiHop source identity drift")
        evidence_docs = [corpus_index[evidence["url"]] for evidence in query["evidence_list"]]
        if any(doc["title"] != evidence["title"] or doc["source"] != evidence["source"]
               for doc, evidence in zip(evidence_docs, query["evidence_list"], strict=True)):
            raise RuntimeError("Private supporting-document identity mismatch")
        shard_indices = sorted({int(MultiHopCorpusDocument.model_validate(doc).stable_id(), 16) % 3
                                for doc in evidence_docs})
        bundle = _multihop_bundle({"source_task_id": source_id, "source_row_ordinal": ordinal},
                                 corpus, queries, MULTIHOP_REVISION)
        receipts.append(persist_bundle(output, SelectedTask("multihop_rag", source_id, position),
            bundle, {
                "revision": MULTIHOP_REVISION, "source_row_ordinal": ordinal,
                "corpus_file_sha256": corpus_sha256,
                "query_file_sha256": query_file_sha256,
                "raw_sample_sha256": provenance_sha256(query), "rationale": rationale,
                "corpus_document_count": len(corpus),
                "corpus_source_bytes": (MULTIHOP_ROOT / "corpus.json").stat().st_size,
                "question_type": query["question_type"],
                "private_audit_only_required_document_count": len(evidence_docs),
                "private_audit_only_required_source_count": len(
                    {d["source"] for d in evidence_docs}),
                "private_audit_only_support_shard_count": len(shard_indices),
                "private_audit_only_support_document_bytes": sum(
                    len(doc["body"].encode()) for doc in evidence_docs),
            }, ("A4", "A5", "A28")))
    for position, (source_id, boundaries, count, rationale) in enumerate(
        LONGBENCH_SELECTION, start=1,
    ):
        raw = longbench[source_id]
        sample = LongBenchV2Sample.model_validate(raw)
        bundle = _longbench_multidoc_bundle(sample, LONGBENCH_REVISION, boundaries)
        receipts.append(persist_bundle(output, SelectedTask("longbench_v2", source_id, position),
            bundle, {
                "revision": LONGBENCH_REVISION, "rationale": rationale,
                "raw_sample_sha256": provenance_sha256(raw),
                "original_context_sha256": (
                    bundle.execution.transformations[0].audit["source_sha256"]),
                "original_context_bytes": len(sample.context.encode()),
                "original_domain": sample.domain, "original_sub_domain": sample.sub_domain,
                "original_length": sample.length, "original_difficulty": sample.difficulty,
                **source_groups(boundaries, count),
                "context_pressure_note": "Full source exceeds the 32K deployment input envelope",
            }, ("A4", "A5") if len(boundaries) == 2 else ("A4",)))
    for row in video_selection["tasks"]:
        bundle = prepare_video(row, preparation)
        receipts.append(persist_bundle(output,
            SelectedTask("video_mme", row["question_id"], row["position"]), bundle, {
                **row, "revision": REVISION,
                "duration_seconds": (
                    bundle.execution.task.artifacts[0].content_schema.duration_seconds),
                "video_setting": "full original source; frozen video-only/no-subtitle setting",
                "original_video_count": 1,
            }, ("A4",)))
    if sum(row["source"]["private_audit_only_support_shard_count"] > 1
           for row in receipts if row["family"] == "multihop_rag") < 4:
        raise RuntimeError("A majority of MultiHop cases must require cross-shard evidence")
    schedule = phase_one_schedule(selected, e_history_tasks=E_HISTORY)
    write_new(output / "phase1-schedule.json", [
        {"cell_id": cell.cell_id, **asdict(cell)} for cell in schedule])
    manifest = {
        "experiment_id": "large-scale-cost-guidance-v1", "tasks": receipts,
        "task_selection_outcome_independent": True, "formal_runs_at_freeze": 0,
        "e_rules_manifest_sha256": _sha256(rules_manifest),
        "e_rules_sha256": rules["rules_sha256"], "e_history_task_identities": E_HISTORY,
        "schedule_seed": SEED, "phase1_schedule_sha256": schedule_sha256(schedule),
        "phase1_cells": len(schedule), "execution_admission_passed": False,
    }
    write_new(output / "manifest.json", manifest)
    return {"task_count": len(receipts), "phase1_cells": len(schedule),
            "manifest_sha256": _sha256(output / "manifest.json"),
            "phase1_schedule_sha256": schedule_sha256(schedule), "formal_runs": 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preparation", type=Path, required=True)
    parser.add_argument("--rules-manifest", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(freeze(args.output, args.preparation, args.rules_manifest), sort_keys=True))


if __name__ == "__main__":
    main()
