"""Analyze persisted v1 runs without re-executing models or evaluators."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import fmean, median
from typing import Any, cast

from infra_joint.heterogeneous.analysis import (
    PlacementRunObservation,
    build_stage_estimates,
    oracle_cells,
    predicted_break_even_mbps,
    routing_regrets,
    validate_trace_reconstruction,
)
from infra_joint.heterogeneous.contracts import ExperimentMetadata
from infra_joint.workflow.runner import PersistedWorkflowRunResult


def load_observations(root: Path) -> tuple[PlacementRunObservation, ...]:
    values: list[PlacementRunObservation] = []
    for metadata_path in sorted(root.glob("*/experiment-metadata.json")):
        raw = cast(dict[str, Any], json.loads(metadata_path.read_text(encoding="utf-8")))
        if raw.get("tc_cleanup_error") is not None or raw.get("validation_error") is not None:
            continue
        metadata = ExperimentMetadata.model_validate(raw["metadata"])
        result_path = metadata_path.parent / "result.json"
        result = PersistedWorkflowRunResult.model_validate_json(
            result_path.read_text(encoding="utf-8")
        )
        validate_trace_reconstruction(metadata_path.parent / "trace.jsonl", result.run_id)
        overhead = cast(dict[str, Any], raw["scheduler_overhead"])
        values.append(
            PlacementRunObservation.model_validate(
                {
                    **observe_payload(result, metadata),
                    "scheduler_overhead_ms": float(overhead["total_ms"]),
                }
            )
        )
    return tuple(values)


def observe_payload(
    result: PersistedWorkflowRunResult, metadata: ExperimentMetadata
) -> dict[str, Any]:
    from infra_joint.heterogeneous.analysis import observe_run

    value = observe_run(result, metadata, scheduler_overhead_ms=0)
    return value.model_dump(mode="json", exclude={"scheduler_overhead_ms"})


def pilot_summary(
    observations: tuple[PlacementRunObservation, ...],
    manifest_path: Path,
) -> dict[str, Any]:
    manifest = cast(dict[str, Any], json.loads(manifest_path.read_text(encoding="utf-8")))
    payload_bytes = {
        str(item["label"]): int(item["actual_bytes"]) for item in manifest["payloads"]
    }
    estimates = {
        payload: build_stage_estimates(
            observations,
            payload,
            profile_id=f"forced-pilot-stage-{payload.lower()}-v1",
        )
        for payload in ("S", "M", "L")
    }
    cells = oracle_cells(observations)
    break_even: dict[str, float | None] = {}
    for payload, points in estimates.items():
        by_replica = {item.replica_id: item for item in points}
        a28 = by_replica["a28-qwen3.8-27b-q4km-v1"].total_compute_latency_ms
        rtx = by_replica[
            "strong-4090-qwen3.8-27b-q4km-v1"
        ].total_compute_latency_ms
        break_even[payload] = predicted_break_even_mbps(
            payload_bytes[payload], a28, rtx, 20.0
        )
    return {
        "schema_version": "heterogeneous-v1-pilot-analysis-v1",
        "valid_run_count": len(observations),
        "stage_estimates": {
            key: [item.model_dump(mode="json") for item in value]
            for key, value in estimates.items()
        },
        "oracle_cells": [item.model_dump(mode="json") for item in cells],
        "predicted_break_even_mbps": break_even,
    }


def formal_summary(observations: tuple[PlacementRunObservation, ...]) -> dict[str, Any]:
    cells = oracle_cells(observations)
    regrets = routing_regrets(observations, cells)
    grouped: dict[str, list[float]] = defaultdict(list)
    correct: dict[str, list[bool]] = defaultdict(list)
    for item in regrets:
        grouped[item.placement_policy].append(item.routing_regret_ms)
        correct[item.placement_policy].append(item.oracle_selected)
    summaries = {
        policy: {
            "count": len(values),
            "mean_routing_regret_ms": fmean(values),
            "median_routing_regret_ms": median(values),
            "p95_routing_regret_ms": sorted(values)[
                max(0, (95 * len(values) + 99) // 100 - 1)
            ],
            "oracle_selection_accuracy": sum(correct[policy]) / len(correct[policy]),
        }
        for policy, values in grouped.items()
    }
    return {
        "schema_version": "heterogeneous-v1-formal-analysis-v1",
        "valid_run_count": len(observations),
        "oracle_cells": [item.model_dump(mode="json") for item in cells],
        "routing_regrets": [item.model_dump(mode="json") for item in regrets],
        "scheduler_summaries": summaries,
        "run_observations": [item.model_dump(mode="json") for item in observations],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("pilot", "formal"))
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage-estimates-root", type=Path)
    args = parser.parse_args()
    observations = load_observations(args.run_root)
    if args.mode == "pilot":
        summary = pilot_summary(observations, args.manifest)
        if args.stage_estimates_root is None:
            raise ValueError("pilot analysis requires --stage-estimates-root")
        args.stage_estimates_root.mkdir(parents=True, exist_ok=True)
        for payload, estimates in summary["stage_estimates"].items():
            path = args.stage_estimates_root / f"stage-estimates-{payload}.json"
            path.write_text(json.dumps(estimates, indent=2, sort_keys=True) + "\n")
    else:
        summary = formal_summary(observations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
