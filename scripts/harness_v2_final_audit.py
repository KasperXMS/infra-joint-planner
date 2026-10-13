"""Write the final redacted integrity receipt from completed Harness v2 exports."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def main(folder: Path) -> None:
    analysis = read(folder / "final-sanitized-analysis.json")
    aggregate = read(folder / "aggregate.json")
    rows = [row for row in analysis["cells"] if row["stage"] == "stage2"]
    group_counts = Counter((row["cell"]["network"], row["cell"]["method"]) for row in rows)
    network: dict[str, Any] = {}
    for regime in ("slow", "fast"):
        attestation = read(folder / f"network-{regime}-attestation.json")
        calibration = attestation["calibration"]
        network[regime] = {
            "calibration_accepted": calibration["accepted"],
            "calibration_issues": calibration["issues"],
            "measurements": calibration["measurements"],
            "cleanup_error": attestation["cleanup_error"],
            "original_qdisc_restored": attestation["original_qdisc"]
            == attestation["restored_qdisc"],
        }
    repeatable = aggregate["repeatable_structural_l2"]
    eligible = [
        row
        for row in repeatable
        if row["quality_preserved_both_trials"]
        and (
            row["e2e_lower_both_trials"]
            or row["cloud_api_lower_both_trials"]
            or row["physical_service_work_lower_both_trials"]
            or row["transfer_lower_both_trials"]
        )
    ]
    checks = {
        "stage_counts_exact": analysis["stage_counts"]
        == {"stage1": 18, "stage1_5": 2, "stage2": 36},
        "no_incomplete_claims": not analysis["incomplete_claims"],
        "unique_stage2_cells": len({row["cell"]["cell_id"] for row in rows}) == 36,
        "six_cells_per_condition": len(group_counts) == 6
        and all(count == 6 for count in group_counts.values()),
        "all_workers_drained_and_exited": all(
            row["worker_cleanup"]
            and row["worker_cleanup"]["drained"]
            and row["worker_cleanup"]["verified_exited"]
            and row["worker_cleanup"]["error_count"] == 0
            for row in rows
        ),
        "no_system_problems": all(not row["system_problems"] for row in rows),
        "no_context_integrity_failures": all(
            row["context_integrity_failures"] == 0 for row in rows
        ),
        "both_networks_restored": all(
            item["calibration_accepted"]
            and item["cleanup_error"] is None
            and item["original_qdisc_restored"]
            for item in network.values()
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"final integrity audit failed: {checks}")
    receipt = {
        "version": "harness-v2-final-audit-001",
        "stage_counts": analysis["stage_counts"],
        "checks": checks,
        "stage2_condition_counts": {
            f"{regime}/{method}": count for (regime, method), count in sorted(group_counts.items())
        },
        "stage2_physical_context_rejections": sum(
            row["physical_rejections"].get("context_limit_exceeded", 0) for row in rows
        ),
        "stage2_verifier_raw_schema_invalid": sum(row["verifier_schema_invalid"] for row in rows),
        "stage2_manager_raw_schema_invalid": sum(row["schema_invalid"] for row in rows),
        "stage2_unknown_cloud_cost_calls": sum(
            row["unknown_cloud_cost_calls"] or 0 for row in rows
        ),
        "network": network,
        "repeatable_structural_l2_count": len(repeatable),
        "stage3_eligible_mechanism_count": len(eligible),
        "stage3_decision": "GO" if eligible else "NO_GO",
        "raw_trace_exported": False,
        "local_gpu_usd": None,
    }
    write(folder / "audit-summary.json", receipt)
    print(json.dumps({"checks": checks, "stage3_decision": receipt["stage3_decision"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    main(parser.parse_args().folder)
