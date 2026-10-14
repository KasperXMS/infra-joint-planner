"""Private-label audit of reconstructed evidence; never sends labels to a model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-summary", type=Path, required=True)
    parser.add_argument("--private-evaluator", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    evidence = json.loads(args.evidence_summary.read_text())
    private = {
        row["task_id"]: row
        for row in map(json.loads, args.private_evaluator.read_text().splitlines())
    }
    public = []
    for condition in evidence:
        task_id = condition["task_id"]
        labels = private[task_id]
        records = condition["record_summaries"]
        if task_id.startswith("multihop:"):
            selected: dict[str, int] = {}
            ambiguous = 0
            for record in records:
                if condition["workflow"] == "G0":
                    original_id = record["origin_artifact_id"]
                else:
                    matches = record.get("original_article_matches", [])
                    if len(matches) != 1:
                        ambiguous += 1
                        continue
                    original_id = matches[0]["artifact_id"]
                selected[original_id] = record["body_characters"]
            gold_ids = set(labels["gold_evidence_artifact_refs"])
            result = {
                "task_id": task_id,
                "workflow": condition["workflow"],
                "support_document_count": len(gold_ids),
                "support_documents_in_full_body_evidence": len(gold_ids.intersection(selected)),
                "support_body_characters_in_evidence": sum(
                    selected[item] for item in gold_ids.intersection(selected)
                ),
                "total_body_characters_in_evidence": sum(selected.values()),
                "unmapped_or_ambiguous_records": ambiguous,
                "record_level_provenance_in_original_G1_trace": condition["workflow"] != "G1",
            }
        else:
            selected_ids = {record["source_document_id"] for record in records}
            gold_ids = {item["doc_id"] for item in labels["supporting_context"]}
            result = {
                "task_id": task_id,
                "workflow": condition["workflow"],
                "support_context_item_count": len(labels["supporting_context"]),
                "support_document_count": len(gold_ids),
                "support_document_ids_in_final_evidence": len(gold_ids.intersection(selected_ids)),
                "table_present": any(record.get("table_type") == "dict" for record in records),
                "table_header_count": next(
                    (
                        record["table_field_shapes"]["header"]
                        for record in records
                        if "table_field_shapes" in record
                    ),
                    None,
                ),
                "table_row_count": next(
                    (
                        record["table_field_shapes"]["table_rows"]
                        for record in records
                        if "table_field_shapes" in record
                    ),
                    None,
                ),
            }
        public.append(result)
    args.output.write_text(json.dumps(public, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"audited_conditions": len(public), "output": str(args.output)}))


if __name__ == "__main__":
    main()
