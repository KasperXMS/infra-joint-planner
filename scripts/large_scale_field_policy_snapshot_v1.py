"""Offline field/policy projection; preserve base and compound history/unknowns."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import large_scale_field_policy_review_v1 as review
import large_scale_snapshot_v1 as base


def snapshot(root: Path) -> dict[str, Any]:
    old_ledger, old_admission = base.SnapshotAttemptLedger, base.effective_admission
    try:
        base.SnapshotAttemptLedger = review.FieldAttemptLedger
        base.effective_admission = review.effective_admission
        value = base.snapshot(root)
    finally:
        base.SnapshotAttemptLedger, base.effective_admission = old_ledger, old_admission
    counts = {"compound_adjudicated_attempts": 0, "field_policy_adjudicated_attempts": 0}
    for row in value["rows"]:
        for attempt in row["attempts"]:
            reason = attempt["admission_reason"]
            if reason not in (review.REASON, review.previous.REASON):
                continue
            field = reason == review.REASON
            directory = review.DIRECTORY if field else review.previous.DIRECTORY
            sidecar = json.loads((root / directory / (attempt["run_id"] + ".json")).read_text())
            attempt.update({"original_rejection_preserved": True,
                            "provider_policy_failure": True,
                            "compound_adjudication_sha256": base.provenance_sha256(sidecar)})
            if field:
                attempt["confirmed_initial_corpus_field_failures"] = len(
                    sidecar["field_misuse_proof"])
                counts["field_policy_adjudicated_attempts"] += 1
            else:
                attempt["confirmed_post_inference_json_failures"] = len(sidecar["model_json_proof"])
                attempt["post_inference_failed_service_tokens"] = None
                counts["compound_adjudicated_attempts"] += 1
    value.update(counts)
    value["collector_lineage"] = {"base_source_sha256": review.sha256(Path(base.__file__)),
                                  "field_projection_source_sha256": review.sha256(Path(__file__)),
                                  "reviewer_sources_sha256": review.sources(),
                                  "online_execution_changed": False}
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (sys.platform != "linux" or args.output.is_symlink()
            or args.output.resolve().parent != review.ROOT / "analysis"):
        raise RuntimeError("field analysis remains in the owned remote namespace")
    value = snapshot(review.ROOT)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in value.items() if k != "rows"}))
