"""Offline reconstruction of the frozen H1 evidence interface.

This script runs outside the isolated Controller, never calls the model, and
keeps reconstructed task prompts and private labels on the experiment machine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
import urllib.request
from pathlib import Path
from typing import Any

from run_hypothesis_cell_v1 import PUBLISHERS, SYSTEM, bm25

from infra_joint.operators.retrieval import _bm25_scores, _tokenize

TASK_IDS = (
    "multihop:a647807d9a1d0efd",
    "multihop:667f4ac48afef820",
    "mmqa:0ed625390ca7f919b46fd99fe85d80b5",
)


class ArchiveStore:
    def __init__(self, *paths: Path):
        self.files: dict[str, bytes] = {}
        for path in paths:
            with tarfile.open(path, "r:gz") as archive:
                for member in archive:
                    if member.isfile() and member.name.startswith("artifacts/"):
                        content = archive.extractfile(member)
                        if content is None:
                            raise RuntimeError(f"archive read failed: {member.name}")
                        self.files[member.name] = content.read()

    def get(self, artifact_id: str) -> tuple[Any, str, int]:
        basename = hashlib.sha256(artifact_id.encode()).hexdigest()
        blob_name = f"artifacts/{basename}.blob"
        meta_name = f"artifacts/{basename}.json"
        if blob_name not in self.files or meta_name not in self.files:
            raise KeyError(artifact_id)
        blob = self.files[blob_name]
        meta = json.loads(self.files[meta_name])
        digest = hashlib.sha256(blob).hexdigest()
        if meta["artifact_id"] != artifact_id or meta["sha256_hex"] != digest:
            raise RuntimeError(f"archived artifact integrity failed: {artifact_id}")
        return json.loads(blob), digest, len(blob)


def sorted_record_roundtrip(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return json.loads(
        json.dumps(records, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    )


def worker_bm25(
    records: list[dict[str, Any]], query: str, count: int, field: str
) -> list[dict[str, Any]]:
    scores = _bm25_scores(
        [_tokenize(record[field]) for record in records], _tokenize(query), k1=1.5, b=0.75
    )
    ranked = sorted(range(len(records)), key=lambda index: (-scores[index], index))[:count]
    return sorted_record_roundtrip(
        [{**records[index], "_bm25_score": scores[index]} for index in ranked]
    )


def reconstruct(
    task: dict[str, Any],
    workflow: str,
    residency: list[dict[str, Any]],
    stores: dict[str, ArchiveStore],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    acquired = 0
    if task["benchmark"] == "MultiHop-RAG":
        if workflow == "G0":
            publishers = PUBLISHERS[task["task_id"]]
            originals = []
            for row in residency:
                if row["source_group"] not in publishers or not row["artifact_id"].startswith(
                    "multihop:"
                ):
                    continue
                record, digest, _ = stores[row["resident_agent"]].get(row["artifact_id"])
                if digest != row["content_hash"]:
                    raise RuntimeError("source manifest hash mismatch")
                record["_origin_artifact_id"] = row["artifact_id"]
                record["_source_group"] = row["source_group"]
                originals.append(record)
            acquired = len(originals)
            for publisher in publishers:
                evidence.extend(
                    bm25(
                        [row for row in originals if row["_source_group"] == publisher],
                        task["question"],
                        3,
                        "body",
                    )
                )
        else:
            for node in ("source-a", "source-b"):
                shard, _, _ = stores[node].get("multihop:corpus-shard:" + node)
                records = worker_bm25(shard, task["question"], 4, "body")
                for record in records:
                    record["_origin_shard"] = "multihop:corpus-shard:" + node
                evidence.extend(records)
            acquired = len(evidence)
    else:
        text_refs = [ref for ref in task["source_artifact_refs"] if ref.startswith("mmqa:text:")]
        texts = []
        for ref in text_refs:
            record, _, _ = stores["source-a"].get(ref)
            record["_origin_artifact_id"] = ref
            texts.append(record)
        if workflow == "G0":
            evidence.extend(bm25(texts, task["question"], 3, "text"))
            acquired = len(texts) + 1
        else:
            index = sorted_record_roundtrip(texts)
            evidence.extend(worker_bm25(index, task["question"], 3, "text"))
            acquired = len(evidence) + 1
        table_ref = next(
            ref for ref in task["source_artifact_refs"] if ref.startswith("mmqa:table:")
        )
        table, _, _ = stores["source-b"].get(table_ref)
        table["_origin_artifact_id"] = table_ref
        evidence.append(table)
    return evidence, {"acquired_original_count": acquired}


def token_count(content: str) -> int | None:
    request = urllib.request.Request(
        "http://127.0.0.1:37797/tokenize",
        data=json.dumps({"content": content}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            tokens = json.loads(response.read()).get("tokens")
    except OSError:
        return None
    return len(tokens) if isinstance(tokens, list) else None


def summarize_record(record: dict[str, Any]) -> dict[str, Any]:
    value: dict[str, Any] = {
        "field_types": {key: type(item).__name__ for key, item in record.items()},
        "record_id_present": any(key in record for key in ("id", "doc_id", "_origin_artifact_id")),
        "source_document_id": record.get("id", record.get("doc_id")),
        "origin_artifact_id": record.get("_origin_artifact_id"),
        "origin_shard_only": "_origin_shard" in record and "_origin_artifact_id" not in record,
        "body_characters": len(record.get("body", "")),
        "text_characters": len(record.get("text", "")),
        "title_characters": len(record.get("title", "")),
    }
    if "table" in record:
        value["table_type"] = type(record["table"]).__name__
        if isinstance(record["table"], dict):
            value["table_keys"] = sorted(record["table"])
            value["table_field_shapes"] = {
                key: len(item) if isinstance(item, (list, dict, str)) else type(item).__name__
                for key, item in record["table"].items()
            }
    if "header" in record:
        value["header_type"] = type(record["header"]).__name__
    if "rows" in record:
        value["rows_count"] = len(record["rows"])
    return value


def article_fingerprint(record: dict[str, Any]) -> str:
    original_fields = ("author", "body", "category", "published_at", "source", "title", "url")
    content = json.dumps(
        {key: record.get(key) for key in original_fields},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(content).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-root", type=Path, required=True)
    parser.add_argument("--study-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    parent, study, output = args.parent_root, args.study_root, args.output_root
    output.mkdir(parents=True, exist_ok=True)
    private_output = output / "private-prompts"
    private_output.mkdir(exist_ok=True)
    stores = {
        "source-a": ArchiveStore(
            parent / "infra-evaluation-source-a.tgz", parent / "infra-evaluation-source-a-delta.tgz"
        ),
        "source-b": ArchiveStore(
            parent / "infra-evaluation-source-b.tgz", parent / "infra-evaluation-source-b-delta.tgz"
        ),
    }
    public = study / "controller" / "study"
    tasks = {
        row["task_id"]: row
        for row in map(json.loads, (public / "task-candidates.jsonl").read_text().splitlines())
    }
    residency = list(map(json.loads, (public / "source-residency.jsonl").read_text().splitlines()))
    article_index: dict[str, list[dict[str, str]]] = {}
    for item in residency:
        if not item["artifact_id"].startswith("multihop:") or not item["source_group"].startswith(
            "publisher:"
        ):
            continue
        article, digest, _ = stores[item["resident_agent"]].get(item["artifact_id"])
        article_index.setdefault(article_fingerprint(article), []).append(
            {
                "artifact_id": item["artifact_id"],
                "sha256": digest,
                "source_group": item["source_group"],
            }
        )
    historical = {
        row["run_id"]: row
        for row in map(
            json.loads, (study / "public" / "trial-outcomes.jsonl").read_text().splitlines()
        )
    }
    summary = []
    for task_id in TASK_IDS:
        task = tasks[task_id]
        for workflow in ("G0", "G1"):
            evidence, extra = reconstruct(task, workflow, residency, stores)
            user = (
                "Original question: "
                + task["question"]
                + "\nEvidence (JSON with original provenance):\n"
                + json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))
                + "\nShort answer:"
            )
            prompt = {"system": SYSTEM, "user": user}
            name = task_id.replace(":", "-") + "-" + workflow.lower()
            prompt_path = private_output / (name + ".json")
            if prompt_path.exists():
                raise FileExistsError(prompt_path)
            prompt_path.write_text(json.dumps(prompt, ensure_ascii=False, indent=2))
            payload = (SYSTEM + "\n" + user).encode()
            matching = [
                row
                for row in historical.values()
                if row["task_id"] == task_id and row["workflow"] == workflow
            ]
            row = matching[0] if matching else None
            record_summaries = [summarize_record(item) for item in evidence]
            if task_id.startswith("multihop:") and workflow == "G1":
                for item, record_summary in zip(evidence, record_summaries, strict=True):
                    matches = article_index.get(article_fingerprint(item), [])
                    record_summary["original_article_matches"] = matches
            summary.append(
                {
                    "task_id": task_id,
                    "workflow": workflow,
                    "prompt_sha256": hashlib.sha256(payload).hexdigest(),
                    "rendered_user_utf8_bytes": len(user.encode()),
                    "reconstructed_context_tokens": token_count(SYSTEM + "\n" + user),
                    "historical_context_tokens": row.get("context_tokens") if row else None,
                    "historical_final_evidence_count": row.get("final_evidence_count")
                    if row
                    else None,
                    "reconstructed_final_evidence_count": len(evidence),
                    "record_summaries": record_summaries,
                    **extra,
                }
            )
    (output / "evidence-interface-public.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(
        json.dumps(
            {
                "reconstructed_conditions": len(summary),
                "output": str(output / "evidence-interface-public.json"),
            }
        )
    )


if __name__ == "__main__":
    main()
