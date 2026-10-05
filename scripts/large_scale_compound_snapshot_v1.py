"""Read-only compound-sidecar projection over the unchanged settled collector."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import large_scale_compound_review_v1 as review
import large_scale_snapshot_v1 as base


class CompoundSnapshotLedger(review.CompoundAttemptLedger):
    @property
    def completed_cells(self) -> tuple[str, ...]:
        admitted = {a.cell_id for a in self.attempts if a.disposition == "valid"}
        return tuple(c for c in self.cells if c in admitted)


def snapshot(root: Path) -> dict[str, Any]:
    old_ledger, old_admission = base.SnapshotAttemptLedger, base.effective_admission
    try:
        base.SnapshotAttemptLedger = CompoundSnapshotLedger
        base.effective_admission = review.effective_admission
        value = base.snapshot(root)
    finally:
        base.SnapshotAttemptLedger, base.effective_admission = old_ledger, old_admission
    count = 0
    for row in value["rows"]:
        for attempt in row["attempts"]:
            if attempt["admission_reason"] != review.REASON:
                continue
            path = root / review.DIRECTORY / (attempt["run_id"] + ".json")
            sidecar = json.loads(path.read_text())
            attempt.update({
                "original_rejection_preserved": True,
                "provider_policy_failure": True,
                "compound_adjudication_sha256": base.provenance_sha256(sidecar),
                "confirmed_post_inference_json_failures": len(sidecar["model_json_proof"]),
                "post_inference_failed_service_tokens": None,
            })
            count += 1
    value["compound_adjudicated_attempts"] = count
    value["collector_lineage"] = {
        "base_source_sha256": review.sha256(Path(base.__file__)),
        "compound_projection_source_sha256": review.sha256(Path(__file__)),
        "reviewer_sources_sha256": review.reviewer_sources(),
        "online_execution_changed": False,
    }
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if (sys.platform != "linux" or arguments.output.is_symlink()
            or arguments.output.resolve().parent != review.ROOT / "analysis"):
        raise RuntimeError("compound analysis remains in the owned remote namespace")
    value = snapshot(review.ROOT)
    with arguments.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in value.items() if k != "rows"}))
