"""Prepare a bounded, source-owned development workload from original releases.

Raw source blobs and evaluator-only labels are written only to --private-root.
The public manifest contains references and checksums, never gold answers.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

from infra_joint.worker.artifact_store import FileArtifactStore, StoredArtifact

MULTIHOP_ROWS = (0, 1, 3, 7, 17, 26)
MULTIHOP_D2_ROWS = frozenset({3, 7, 17, 26})
MMQA_IDS = (
    "33cf75c43fb268f267002cf8b9c28313",  # text control
    "a33985b1e8b2502fc18cc8147dc27db8",  # table control
    "f5326b243eed1f858865df5e3337cb10",
    "0ed625390ca7f919b46fd99fe85d80b5",
    "710a6d2254076ea58756c6c7cc211f1e",
    "d17931e347af95c54d4acd295f91ea5d",
    "471a2c824769af89d5d77a881462c775",
)
MMQA_D2_IDS = frozenset(MMQA_IDS[2:])
NODES = ("source-a", "source-b")


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def owner(source_group: str) -> str:
    """Stable source-level assignment, independent of task/gold relevance."""
    if source_group == "mmqa:text-service":
        return "source-a"
    if source_group == "mmqa:table-service":
        return "source-b"
    return NODES[int(digest(source_group.encode("utf-8")), 16) % len(NODES)]


def read_gzip_jsonl(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]


def add_artifact(
    stores: dict[str, FileArtifactStore],
    records: dict[str, dict[str, Any]],
    *,
    artifact_id: str,
    source_group: str,
    payload: Any,
    media_type: str = "application/json",
    resident_agent: str | None = None,
) -> None:
    data = canonical(payload)
    node = resident_agent or owner(source_group)
    if node not in stores:
        raise ValueError(f"unknown resident agent: {node}")
    stored = StoredArtifact.create(artifact_id, media_type, data)
    stores[node].put(stored)
    item = {
        "artifact_id": artifact_id,
        "source_group": source_group,
        "resident_agent": node,
        "artifact_type": media_type,
        "artifact_size": len(data),
        "content_hash": stored.sha256_hex,
        "index_version": "none",
    }
    previous = records.setdefault(artifact_id, item)
    if previous != item:
        raise ValueError(f"conflicting artifact: {artifact_id}")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(canonical(row).decode("utf-8") + "\n")


def prepare(
    multihop_corpus: Path,
    multihop_questions: Path,
    mmqa_dataset: Path,
    public_root: Path,
    private_root: Path,
) -> dict[str, Any]:
    if public_root.resolve() == private_root.resolve():
        raise ValueError("public and private roots must differ")
    if public_root.exists() and any(public_root.iterdir()):
        raise FileExistsError(f"public output already populated: {public_root}")
    if private_root.exists() and any(private_root.iterdir()):
        raise FileExistsError(f"private output already populated: {private_root}")
    stores = {node: FileArtifactStore(private_root / node / "artifacts") for node in NODES}
    artifacts: dict[str, dict[str, Any]] = {}
    tasks: list[dict[str, Any]] = []
    private: list[dict[str, Any]] = []
    exclusions: list[dict[str, str]] = []
    exclusions.extend(
        (
            {
                "task_id": "crossvid:CC:0",
                "reason": "original multi-video media not staged on study-owned Workers",
            },
            {
                "task_id": "crossvid:BU:0",
                "reason": "behavior videos require separately licensed original media access",
            },
        )
    )

    corpus = json.loads(multihop_corpus.read_text(encoding="utf-8"))
    questions = json.loads(multihop_questions.read_text(encoding="utf-8"))
    if len(corpus) < 609 or len(questions) < max(MULTIHOP_ROWS) + 1:
        raise ValueError("MultiHop-RAG source is incomplete")
    by_url = {row["url"]: row for row in corpus}
    if len(by_url) != len(corpus):
        raise ValueError("duplicate MultiHop-RAG URL")
    for document in corpus:
        add_artifact(
            stores,
            artifacts,
            artifact_id=f"multihop:{digest(canonical(document))}",
            source_group=f"publisher:{document['source']}",
            payload=document,
        )
    for node in NODES:
        shard = [row for row in corpus if owner(f"publisher:{row['source']}") == node]
        add_artifact(
            stores,
            artifacts,
            artifact_id=f"multihop:corpus-shard:{node}",
            source_group=f"multihop:publisher-shard:{node}",
            payload=shard,
            resident_agent=node,
        )
    mh_id_by_url = {row["url"]: f"multihop:{digest(canonical(row))}" for row in corpus}
    for index in MULTIHOP_ROWS:
        sample = questions[index]
        task_id = f"multihop:{digest(sample['query'].encode('utf-8'))[:16]}"
        evidence = sample["evidence_list"]
        missing = sorted({item["url"] for item in evidence} - by_url.keys())
        if missing:
            exclusions.append({"task_id": task_id, "reason": "gold URL absent from corpus"})
            continue
        refs = sorted({mh_id_by_url[item["url"]] for item in evidence})
        groups = sorted({f"publisher:{item['source']}" for item in evidence})
        # Evidence references are private. Runtime searches the entire installed corpus.
        tasks.append(
            {
                "schema_version": "infra-evaluation-workload-v0.1",
                "task_id": task_id,
                "benchmark": "MultiHop-RAG",
                "benchmark_revision": "yixuantt/MultiHopRAG + local source hashes",
                "question_ref": task_id,
                "question": sample["query"],
                "source_artifact_refs": [],
                "source_collection_refs": sorted(
                    {f"publisher:{row['source']}" for row in corpus}
                ),
                "answer_contract": "short_text; native qa_evaluate.py overlap",
                "modality": ["text"],
                "reasoning_type": sample["question_type"],
                "source_dependency_class": "D2" if index in MULTIHOP_D2_ROWS else "D1",
                "source_dependency_note": (
                    "question explicitly compares named source reports; source text spot-checked"
                    if index in MULTIHOP_D2_ROWS
                    else "multiple annotated publishers; single-source sufficiency unresolved"
                ),
                "candidate_source_group_count": len(groups),
                "split": "development",
                "validity": "source_and_evaluator_available",
            }
        )
        private.append(
            {
                "task_id": task_id,
                "answer": sample["answer"],
                "gold_evidence_artifact_refs": refs,
                "gold_evidence_source_groups": groups,
                "evaluator_ref": "upstream-multihoprag/qa_evaluate.py:calculate_metrics",
            }
        )

    mmqa = {row["qid"]: row for row in read_gzip_jsonl(mmqa_dataset / "MMQA_dev.jsonl.gz")}
    selected = [mmqa[qid] for qid in MMQA_IDS]
    required_texts = {item for row in selected for item in row["metadata"]["text_doc_ids"]}
    required_tables = {row["metadata"]["table_id"] for row in selected}
    text_rows = {
        row["id"]: row
        for row in read_gzip_jsonl(mmqa_dataset / "MMQA_texts.jsonl.gz")
        if row["id"] in required_texts
    }
    table_rows = {
        row["id"]: row
        for row in read_gzip_jsonl(mmqa_dataset / "MMQA_tables.jsonl.gz")
        if row["id"] in required_tables
    }
    if set(text_rows) != required_texts or set(table_rows) != required_tables:
        raise ValueError("MultiModalQA candidate context is incomplete")
    for row in text_rows.values():
        add_artifact(
            stores,
            artifacts,
            artifact_id=f"mmqa:text:{row['id']}",
            source_group="mmqa:text-service",
            payload=row,
        )
    for row in table_rows.values():
        add_artifact(
            stores,
            artifacts,
            artifact_id=f"mmqa:table:{row['id']}",
            source_group="mmqa:table-service",
            payload=row,
        )
    for row in selected:
        task_id = f"mmqa:{row['qid']}"
        metadata = row["metadata"]
        refs = [f"mmqa:text:{item}" for item in metadata["text_doc_ids"]]
        refs.append(f"mmqa:table:{metadata['table_id']}")
        support = row["supporting_context"]
        support_groups = {item["doc_part"] for item in support}
        if any(item["doc_part"] == "image" for item in support):
            exclusions.append({"task_id": task_id, "reason": "image support not installed"})
            continue
        if any(
            f"mmqa:{item['doc_part']}:{item['doc_id']}" not in refs for item in support
        ):
            exclusions.append(
                {"task_id": task_id, "reason": "support context absent from candidate set"}
            )
            continue
        if row["qid"] == "f5326b243eed1f858865df5e3337cb10":
            exclusions.append(
                {
                    "task_id": task_id,
                    "reason": (
                        "three-answer list requires an unsupported native list-output contract"
                    ),
                }
            )
            continue
        tasks.append(
            {
                "schema_version": "infra-evaluation-workload-v0.1",
                "task_id": task_id,
                "benchmark": "MultiModalQA",
                "benchmark_revision": "allenai/multimodalqa:4dd14328",
                "question_ref": task_id,
                "question": row["question"],
                "source_artifact_refs": sorted(refs),
                "source_collection_refs": ["mmqa:text-service", "mmqa:table-service"],
                "answer_contract": "short_text; official list EM/F1",
                "modality": metadata["modalities"],
                "reasoning_type": metadata["type"],
                "source_dependency_class": (
                    "D2" if row["qid"] in MMQA_D2_IDS else "D0"
                ),
                "source_dependency_note": (
                    "compositional question joins text and table; both originals spot-checked"
                    if row["qid"] in MMQA_D2_IDS
                    else "original supporting context is within one modality"
                ),
                "candidate_source_group_count": len(support_groups),
                "split": "development",
                "validity": "text_table_context_and_evaluator_available",
            }
        )
        private.append(
            {
                "task_id": task_id,
                "answers": row["answers"],
                "supporting_context": support,
                "intermediate_answers": metadata.get("intermediate_answers", []),
                "evaluator_ref": "upstream-multimodalqa/baselines/evaluate.py:list_em,list_f1",
            }
        )

    public_root.mkdir(parents=True, exist_ok=True)
    write_jsonl(public_root / "task-candidates.jsonl", tasks)
    write_jsonl(
        public_root / "planner-view.jsonl",
        [
            {
                key: task[key]
                for key in (
                    "task_id",
                    "question",
                    "source_artifact_refs",
                    "source_collection_refs",
                    "answer_contract",
                )
            }
            for task in tasks
        ],
    )
    write_jsonl(public_root / "source-residency.jsonl", list(artifacts.values()))
    evaluator_by_id = {row["task_id"]: row for row in private}
    write_jsonl(
        public_root / "evaluation-definitions.jsonl",
        [
            {
                "task_id": task["task_id"],
                "original_evaluator_ref": evaluator_by_id[task["task_id"]]["evaluator_ref"],
                "evaluation_metadata_ref": (
                    f"private:evaluator-private.jsonl#{task['task_id']}"
                ),
                "scoring_contract": task["answer_contract"],
                "quality_threshold": None,
                "split": "development",
            }
            for task in tasks
        ],
    )
    write_jsonl(public_root / "excluded-candidates.jsonl", exclusions)
    write_jsonl(private_root / "evaluator-private.jsonl", private)
    source_files = (multihop_corpus, multihop_questions) + tuple(
        mmqa_dataset / f"MMQA_{name}.jsonl.gz" for name in ("dev", "texts", "tables")
    )
    receipt = {
        "schema_version": "infra-evaluation-workload-v0.1",
        "selection_policy": "frozen row IDs and QIDs; no model outputs used",
        "task_count": len(tasks),
        "artifact_count": len(artifacts),
        "excluded_count": len(exclusions),
        "source_files": {
            path.name: {"sha256": digest(path.read_bytes()), "size_bytes": path.stat().st_size}
            for path in source_files
        },
        "resident_artifact_counts": {
            node: sum(item["resident_agent"] == node for item in artifacts.values())
            for node in NODES
        },
    }
    (public_root / "preparation-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--multihop-corpus", type=Path, required=True)
    parser.add_argument("--multihop-questions", type=Path, required=True)
    parser.add_argument("--mmqa-dataset", type=Path, required=True)
    parser.add_argument("--public-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            prepare(
                args.multihop_corpus,
                args.multihop_questions,
                args.mmqa_dataset,
                args.public_root,
                args.private_root,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
