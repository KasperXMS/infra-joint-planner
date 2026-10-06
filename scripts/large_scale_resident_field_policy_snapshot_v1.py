"""Read-only source-bound projection including nominal compound policy failures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import large_scale_resident_field_policy_review_v1 as reviewer
import large_scale_resident_timeout_snapshot_v1 as previous

EXECUTIONS = previous.EXECUTIONS
resident = previous.resident


def collect(root: Path = resident.ROOT, predecessor: Path = resident.PREDECESSOR) -> dict[str, Any]:
    value = previous.previous.core.collect(root, predecessor, audit_view=reviewer)
    for row in value["rows"]:
        for attempt in row["attempts"]:
            for folder, key in ((reviewer.previous.TIMEOUT_DIRECTORY,
                                 "compound_cloud_timeout_review_file_sha256"),
                                (reviewer.POLICY_DIRECTORY,
                                 "compound_record_policy_review_file_sha256")):
                path = root / folder / (attempt["run_id"] + ".json")
                attempt[key] = resident.sha256(path) if path.exists() else None
                if path.exists():
                    proof = json.loads(path.read_text())
                    attempt.update(original_rejection_preserved=True,
                                   confirmed_absent_field_failures=len(proof["record_field_proof"]),
                                   benchmark_quality_unknown=True)
                    if folder == reviewer.POLICY_DIRECTORY:
                        attempt["confirmed_provider_policy_refusals"] = len(
                            proof["provider_policy_proof"])
    value["collector_source_sha256"].update({Path(p).name: resident.sha256(Path(p)) for p in (
        __file__, reviewer.previous.__file__, reviewer.previous.previous.__file__,
        reviewer.methods.__file__, reviewer.records.__file__, reviewer.policy.__file__)})
    value["version"] = "resident-four-epoch-exact-record-policy-projection-v1"
    if resident.sha256(root / "phase1-attempts.jsonl") != value["journal_sha256"]:
        raise RuntimeError("journal advanced; never publish a stale field/policy projection")
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (sys.platform != "linux" or args.output.is_symlink()
            or args.output.resolve().parent != resident.ROOT / "analysis"):
        raise RuntimeError("field/policy projection remains in the owned remote namespace")
    value = collect()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in value.items() if k != "rows"}))
