"""Remote-only, outcome-independent three-task freeze; no model or Worker calls.

Historical metadata and source files are read only. Questions and answers remain
on the experiment machine. Selection is the first unused row in each pinned
local source, with video-level exclusion in addition to question-level exclusion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path("/home/super/xiaoming/skill-granularity-pilot-v1")
HOME = Path("/home/super/xiaoming")
PREPARATION = HOME / "large-scale-cost-guidance-v1/preparation"
MULTIHOP = HOME / "blind_baseline_6task_v1/data"
LONG = HOME / "infra-bench/scenario-mining/data/longbench_v2/selected.jsonl"
ANNOTATION = PREPARATION / "original-videomme-annotation-001/annotation-private.json"
PREFIXES = (
    "blind_baseline",
    "predecision-crossbenchmark",
    "infra-aware-predecision",
    "naive_planner",
    "mas_validity",
    "cost-guidance-",
    "large-scale-cost-guidance",
    "sdk_native_blind_multihop",
    "lightweight-planner",
    "multiscale-planner",
    "infra-joint-m4-smoke",
)
PRUNE = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "data",
    "datasets",
    "models",
    "blobs",
    "context",
    "api",
    "tokenizers",
    ".ruff_cache",
    ".pytest_cache",
}
ID_PATTERN = re.compile(r"multihop-rag-train-[0-9a-f]{24}|\b[0-9a-f]{24}\b|\b\d{1,3}-[123]\b")


def sha(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            result.update(block)
    return result.hexdigest()


def write(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def history() -> tuple[set[str], list[str], dict[str, Any]]:
    """Finite project-scope census: metadata, run IDs, selection and Skills sources.

    API payloads, corpora, context renderings, dependencies and model blobs are
    excluded. For traces, only task/loop start records are read. File locators
    and receipts are retained privately; no source text is exported.
    """
    roots = sorted(p for p in HOME.iterdir() if p.is_dir() and p.name.startswith(PREFIXES))
    ids: set[str] = set()
    texts: list[str] = []
    files: list[dict[str, Any]] = []
    seen: set[str] = set()
    inventory_only: list[dict[str, str]] = []
    run_ids: set[str] = set()
    for root in roots:
        for directory, dirs, names in os.walk(root):
            dirs[:] = sorted(
                d for d in dirs if d not in PRUNE and not d.startswith("video-original-")
            )
            for name in sorted(names):
                p = Path(directory) / name
                if p.suffix not in {".json", ".jsonl", ".yaml", ".yml", ".md", ".py"}:
                    continue
                if name.startswith(("full-corpus", "longbench-multidoc", "annotation-private")):
                    continue
                size = p.stat().st_size
                if size > 512 * 1024 * 1024:
                    raise RuntimeError(f"Historical metadata exceeds audit bound: {p.name}")
                if name == "trace.jsonl":
                    kept = []
                    with p.open(encoding="utf-8") as stream:
                        for line in stream:
                            row = json.loads(line)
                            if row.get("event_type") in {"task.start", "logical.loop.start"}:
                                kept.append(line)
                            if row.get("event_type") == "logical.loop.start":
                                break
                    text = "".join(kept)
                else:
                    raw = p.read_bytes()
                    encoding = (
                        "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
                    )
                    text = raw.decode(encoding)
                digest = hashlib.sha256(text.encode()).hexdigest()
                files.append(
                    {
                        "path": str(p),
                        "source_bytes": size,
                        "scanned_content_sha256": digest,
                        "trace_task_records_only": name == "trace.jsonl",
                    }
                )
                if digest in seen:
                    continue
                seen.add(digest)
                if name == "scenario_mining_report.json":
                    inventory_only.append(
                        {
                            "path": str(p),
                            "sha256": digest,
                            "reason": (
                                "source inventory does not establish testing or Skills design"
                            ),
                        }
                    )
                    continue
                ids.update(ID_PATTERN.findall(text))
                texts.append(text)
                if name == "result.json":
                    value = json.loads(text)
                    if isinstance(value, dict) and isinstance(value.get("run_id"), str):
                        run_ids.add(value["run_id"])
    return (
        ids,
        texts,
        {
            "scanned_project_roots": [str(p) for p in roots],
            "scanned_files": files,
            "scanned_file_count": len(files),
            "distinct_scanned_content_count": len(seen),
            "distinct_run_ids": sorted(run_ids),
            "run_id_count": len(run_ids),
            "used_id_count": len(ids),
            "inventory_only_not_counted_as_prior_use": inventory_only,
            "scope": "All matching existing research-project roots; run results/task-start traces, "
            "selection/freeze receipts, repository scripts/configs/docs "
            "including Skills design material",
            "excluded_directory_names": sorted(PRUNE),
            "claim_limit": (
                "Project-evidence novelty only; "
                "no claim about pretraining or unrecorded external use"
            ),
        },
    )


def choose(ids: set[str], texts: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    from blind_baseline_6task_v1 import _legacy_multihop_task_id

    queries = json.loads((MULTIHOP / "MultiHopRAG.json").read_text())
    long_rows = [json.loads(line) for line in LONG.open(encoding="utf-8")]
    videos = json.loads(ANNOTATION.read_text())
    used_videos = {str(row["videoID"]) for row in videos if str(row["question_id"]) in ids}
    # Source-code references to a historical video are also excluded, regardless
    # of whether the same question ID was retained in a result.
    referenced_tokens = set(
        re.findall(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{11}(?![A-Za-z0-9_-])", "\n".join(texts))
    )
    for row in videos:
        if str(row["videoID"]) in referenced_tokens:
            used_videos.add(str(row["videoID"]))
    selected: dict[str, Any] = {}
    excluded: dict[str, Any] = {}
    sources = (
        ("multihop_rag", queries, lambda r: _legacy_multihop_task_id(r["query"]), "query"),
        ("longbench_v2", long_rows, lambda r: str(r["_id"]), "question"),
        ("video_mme", videos, lambda r: str(r["question_id"]), "question"),
    )
    for family, rows, identify, question_key in sources:
        skipped = []
        for ordinal, row in enumerate(rows):
            task_id = identify(row)
            reason = None
            if task_id in ids:
                reason = "historical_id_reference"
            elif family == "video_mme" and str(row["videoID"]) in used_videos:
                reason = "historical_video_reference"
            elif any(row[question_key] in text for text in texts):
                reason = "historical_question_text_reference"
            if reason:
                skipped.append(
                    {"source_row_ordinal": ordinal, "source_task_id": task_id, "reason": reason}
                )
                continue
            selected[family] = {
                "source_row_ordinal": ordinal,
                "source_task_id": task_id,
                "raw": row,
            }
            break
        else:
            raise RuntimeError(f"No unused original row remains in {family}")
        excluded[family] = skipped
    return selected, {
        "excluded_preceding_rows": excluded,
        "video_level_exclusion": True,
        "used_video_count": len(used_videos),
    }


def acquire_video(
    raw: dict[str, Any], destination: Path
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    from large_scale_video_sources_v1 import BASE, DATASET, REVISION, RangeZipReader

    matches = []
    for path in sorted((PREPARATION / "original-videomme-index-001").glob("*.index.json")):
        index = json.loads(path.read_text())
        for entry in index["entries"]:
            if Path(entry["name"]).stem == str(raw["videoID"]):
                matches.append((path, index, entry))
    if len(matches) != 1:
        raise RuntimeError("New video must map to exactly one pinned archive member")
    index_path, metadata, entry = matches[0]
    if metadata["dataset"] != DATASET or metadata["revision"] != REVISION:
        raise RuntimeError("Pinned Video-MME index identity mismatch")
    if entry["bytes"] > 1024**3:
        raise RuntimeError(
            "Selected first-unused video exceeds 1-GiB acquisition budget; do not replace it"
        )
    destination.mkdir(parents=True)
    path = destination / Path(entry["name"]).name
    reader = RangeZipReader(f"{BASE}/{metadata['archive']}")
    if reader.length != metadata["archive_bytes"] or reader.etag != metadata["etag"]:
        raise RuntimeError("Pinned archive identity drift")
    with zipfile.ZipFile(reader) as archive:
        actual = archive.getinfo(entry["name"])
        if actual.file_size != entry["bytes"] or entry["crc32"] != actual.CRC:
            raise RuntimeError("Pinned original video member identity drift")
        with archive.open(actual) as source, path.open("xb") as sink:
            while block := source.read(1024 * 1024):
                sink.write(block)
    receipt = {
        "dataset": DATASET,
        "revision": REVISION,
        "archive": metadata["archive"],
        "member": entry["name"],
        "index_sha256": sha(index_path),
        "size_bytes": path.stat().st_size,
        "sha256": sha(path),
        "crc32": entry["crc32"],
        "network_fetched_bytes": reader.fetched_bytes,
        "range_requests": reader.range_requests,
        "transformation": "lossless_original_zip_member_extraction",
        "formal_runs": 0,
    }
    if path.stat().st_size != entry["bytes"]:
        raise RuntimeError("Extracted original video size mismatch")
    media = json.loads(
        subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,codec_name,width,height",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        ).stdout
    )
    write(destination / "provenance.json", receipt)
    write(destination / "media.json", media)
    return path, receipt, media


def freeze(output: Path, selected: dict[str, Any], novelty: dict[str, Any]) -> dict[str, Any]:
    from blind_baseline_6task_v1 import _longbench_multidoc_bundle, _multihop_bundle
    from large_scale_execution_v1 import frozen_task
    from large_scale_task_selection_v1 import (
        LONGBENCH_REVISION,
        MULTIHOP_REVISION,
        original_options,
        persist_bundle,
        source_groups,
    )
    from large_scale_video_sources_v1 import REVISION

    from infra_joint.benchmarks.base import AdaptationBundle, PreparedArtifact
    from infra_joint.benchmarks.longbench_v2 import LongBenchV2Sample
    from infra_joint.benchmarks.video_mme import SourceArtifact, VideoMMEAdapter, VideoMMESample
    from infra_joint.control.provenance import provenance_sha256
    from infra_joint.core.task import ArtifactContentSchema
    from infra_joint.experiments.large_scale_protocol import SelectedTask

    if output.exists():
        raise FileExistsError("Task freeze is append-only")
    output.mkdir(parents=True)
    write(output / "novelty-private.json", novelty)
    write(
        output / "selection-before-adaptation.json",
        {
            "frozen_at_utc": datetime.now(UTC).isoformat(),
            "selection_policy": "first unused source row; no difficulty/answer/outcome selection",
            "tasks": [
                {
                    "family": f,
                    "position": 1,
                    "source_task_id": r["source_task_id"],
                    "source_row_ordinal": r["source_row_ordinal"],
                }
                for f, r in selected.items()
            ],
            "novelty_sha256": sha(output / "novelty-private.json"),
            "model_calls": 0,
            "answers_not_exposed_to_skill_design": True,
        },
    )
    receipts = []
    for family, row in selected.items():
        raw = row["raw"]
        source = {
            "source_row_ordinal": row["source_row_ordinal"],
            "raw_sample_sha256": provenance_sha256(raw),
            "rationale": (
                "earliest source row absent from historical IDs, question text and video references"
            ),
        }
        if family == "multihop_rag":
            corpus = json.loads((MULTIHOP / "corpus.json").read_text())
            queries = json.loads((MULTIHOP / "MultiHopRAG.json").read_text())
            bundle = _multihop_bundle(row, corpus, queries, MULTIHOP_REVISION)
            source.update(
                revision=MULTIHOP_REVISION,
                corpus_file_sha256=sha(MULTIHOP / "corpus.json"),
                query_file_sha256=sha(MULTIHOP / "MultiHopRAG.json"),
                corpus_document_count=len(corpus),
            )
            placements = ("A4", "A5", "A28")
        elif family == "longbench_v2":
            sample = LongBenchV2Sample.model_validate(raw)
            bundle = _longbench_multidoc_bundle(sample, LONGBENCH_REVISION, (0,))
            source.update(
                revision=LONGBENCH_REVISION,
                source_file_sha256=sha(LONG),
                original_context_sha256=hashlib.sha256(sample.context.encode()).hexdigest(),
                original_context_bytes=len(sample.context.encode()),
                **source_groups((0,), None),
            )
            placements = ("A4",)
        else:
            video, provenance, media = acquire_video(raw, output.parent / "video-original-new-001")
            streams = [s for s in media["streams"] if s["codec_type"] == "video"]
            if len(streams) != 1:
                raise RuntimeError("Expected exactly one original video stream")
            duration = float(media["format"]["duration"])
            artifact = SourceArtifact(
                artifact_id=f"video-mme-{row['source_task_id'].split('-')[0]}-complete-original",
                logical_type=f"complete_original_video;full_timeline;duration_seconds={duration:g}",
                media_type="video/mp4",
                size_bytes=video.stat().st_size,
                source_ref=f"dataset://video-mme/{row['source_task_id']}/complete-video",
                content_schema=ArtifactContentSchema(
                    kind="video", codec=streams[0]["codec_name"], duration_seconds=duration
                ),
            )
            identity = VideoMMEAdapter(REVISION).adapt(
                VideoMMESample(
                    sample_id=row["source_task_id"],
                    video=artifact,
                    question=raw["question"],
                    options=original_options(raw["options"]),
                    answer_label=raw["answer"],
                )
            )
            bundle = AdaptationBundle(
                identity.execution,
                identity.private_evaluation,
                (
                    PreparedArtifact.create(
                        identity.execution.task.artifacts[0], video.read_bytes()
                    ),
                ),
            )
            source.update(
                revision=REVISION,
                annotation_sha256=sha(ANNOTATION),
                acquisition=provenance,
                duration_seconds=duration,
                video_setting="full original source; frozen video-only/no-subtitle setting",
            )
            placements = ("A4",)
        receipts.append(
            persist_bundle(
                output, SelectedTask(family, row["source_task_id"], 1), bundle, source, placements
            )
        )
    manifest = {
        "version": "skill-granularity-task-freeze-v1",
        "tasks": receipts,
        "task_selection_outcome_independent": True,
        "formal_runs_at_freeze": 0,
        "novelty_private_sha256": sha(output / "novelty-private.json"),
        "selection_before_adaptation_sha256": sha(output / "selection-before-adaptation.json"),
        "preparation_script_sha256": sha(Path(__file__)),
        "new_task_count": 3,
        "historical_files_modified": False,
    }
    write(output / "manifest.json", manifest)
    for row in receipts:
        frozen_task(output, manifest, row["family"], row["position"])
    public = {
        "version": "skill-granularity-task-freeze-public-v1",
        "manifest_sha256": sha(output / "manifest.json"),
        "tasks": [
            {
                k: r[k]
                for k in (
                    "family",
                    "source_task_id",
                    "position",
                    "task_bundle_sha256",
                    "agent_task_sha256",
                    "evaluator_implementation_sha256",
                    "initial_bytes",
                )
            }
            | {"source_row_ordinal": r["source"]["source_row_ordinal"]}
            for r in receipts
        ],
        "novelty": {
            k: novelty[k]
            for k in (
                "scanned_file_count",
                "distinct_scanned_content_count",
                "run_id_count",
                "used_id_count",
                "scope",
                "claim_limit",
            )
        },
        "novelty_private_sha256": manifest["novelty_private_sha256"],
        "selection_before_adaptation_sha256": manifest["selection_before_adaptation_sha256"],
        "selection_policy": (
            "first unused source row; video-level exclusion; no answer/difficulty/outcome filtering"
        ),
        "frozen_task_reload_passed": True,
        "planner_calls": 0,
        "answers_exported": False,
    }
    write(output / "public-summary.json", public)
    return public


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "preparation/task-freeze-001")
    parser.add_argument("--inspect", action="store_true")
    args = parser.parse_args()
    if sys.platform != "linux" or args.output.resolve() != ROOT / "preparation/task-freeze-001":
        raise RuntimeError("Only the separately authorized remote preparation namespace is allowed")
    ids, texts, novelty = history()
    selected, exclusions = choose(ids, texts)
    novelty.update(exclusions)
    if args.inspect:
        result = {
            "tasks": [
                {
                    "family": family,
                    "source_task_id": row["source_task_id"],
                    "source_row_ordinal": row["source_row_ordinal"],
                }
                for family, row in selected.items()
            ],
            "scanned_files": novelty["scanned_file_count"],
            "run_ids": novelty["run_id_count"],
        }
    else:
        print(
            json.dumps(
                {
                    "selection_fixed_before_adaptation": [
                        {
                            "family": family,
                            "source_task_id": row["source_task_id"],
                            "source_row_ordinal": row["source_row_ordinal"],
                        }
                        for family, row in selected.items()
                    ]
                }
            ),
            flush=True,
        )
        result = freeze(args.output, selected, novelty)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
