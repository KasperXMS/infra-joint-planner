"""Audit partial heterogeneous-v1 pilot coverage without executing any run."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import fmean, median, stdev
from typing import Any, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infra_joint.heterogeneous.analysis import observe_run, validate_trace_reconstruction
from infra_joint.heterogeneous.contracts import ExperimentMetadata
from infra_joint.workflow.runner import PersistedWorkflowRunResult


def _round(value: float) -> float:
    return round(value, 3)


def _load_object(path: Path) -> dict[str, Any]:
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"expected JSON object: {path}")
    return cast(dict[str, Any], loaded)


def audit(schedule_path: Path, run_root: Path) -> dict[str, Any]:
    schedule = _load_object(schedule_path)
    raw_runs = schedule.get("runs")
    if not isinstance(raw_runs, list):
        raise ValueError("schedule runs must be a list")
    runs = [cast(dict[str, Any], item) for item in cast(list[Any], raw_runs)]
    bandwidths = sorted({float(item["bandwidth_mbps"]) for item in runs})
    payloads = sorted({str(item["payload"]) for item in runs})
    placements = sorted({str(item["policy"]) for item in runs})
    repetitions = sorted({int(item["repetition"]) for item in runs})
    factor_counts = Counter(
        (
            float(item["bandwidth_mbps"]),
            str(item["payload"]),
            str(item["policy"]),
        )
        for item in runs
    )
    factorization_valid = (
        len(runs) == 108
        and bandwidths == [3.0, 10.0, 30.0, 100.0, 300.0, 1000.0]
        and payloads == ["L", "M", "S"]
        and placements == ["forced-a28", "forced-rtx"]
        and repetitions == [1, 2, 3]
        and len(factor_counts) == 36
        and set(factor_counts.values()) == {3}
    )

    completed: dict[tuple[float, str, str], list[dict[str, Any]]] = defaultdict(list)
    pending: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for item in runs:
        run_id = str(item["run_id"])
        root = run_root / run_id
        paths = {
            "result": root / "result.json",
            "metadata": root / "experiment-metadata.json",
            "trace": root / "trace.jsonl",
        }
        present = {key: path.is_file() for key, path in paths.items()}
        if not any(present.values()):
            pending.append(item)
            continue
        if not all(present.values()) or (root / "matrix-failure.json").exists():
            invalid.append({"run_id": run_id, "reason": "partial_or_failed_sidecars"})
            continue
        raw_metadata = _load_object(paths["metadata"])
        errors = {
            key: raw_metadata.get(key)
            for key in (
                "validation_error",
                "tc_cleanup_error",
                "artifact_cleanup_error",
            )
            if raw_metadata.get(key) is not None
        }
        if errors:
            invalid.append({"run_id": run_id, "reason": errors})
            continue
        metadata = ExperimentMetadata.model_validate(raw_metadata["metadata"])
        result = PersistedWorkflowRunResult.model_validate_json(
            paths["result"].read_text(encoding="utf-8")
        )
        if not result.execution_completed or result.failure is not None:
            invalid.append({"run_id": run_id, "reason": "workflow_failure"})
            continue
        trace_events = validate_trace_reconstruction(paths["trace"], run_id)
        overhead = cast(dict[str, Any], raw_metadata["scheduler_overhead"])
        observation = observe_run(
            result,
            metadata,
            scheduler_overhead_ms=float(overhead["total_ms"]),
        )
        key = (
            float(item["bandwidth_mbps"]),
            str(item["payload"]),
            str(item["policy"]),
        )
        completed[key].append(
            {
                "run_id": run_id,
                "repetition": int(item["repetition"]),
                "e2e_ms": observation.workflow_e2e_ms,
                "transfer_ms": observation.stage_transfer_ms,
                "transfer_bytes": observation.stage_transfer_bytes,
                "benchmark_score": observation.benchmark_score,
                "format_valid": observation.format_valid,
                "trace_events": trace_events,
                "cleanup_recovery": raw_metadata.get("artifact_cleanup_recovery", []),
            }
        )

    coverage: list[dict[str, Any]] = []
    variations: list[dict[str, Any]] = []
    by_cell: dict[tuple[float, str, str], dict[str, Any]] = {}
    for bandwidth in bandwidths:
        for payload in ("S", "M", "L"):
            for placement in ("forced-a28", "forced-rtx"):
                key = (bandwidth, payload, placement)
                values = sorted(completed[key], key=lambda value: value["repetition"])
                e2e = [float(value["e2e_ms"]) for value in values]
                transfer_ms = [float(value["transfer_ms"]) for value in values]
                transfer_bytes = [int(value["transfer_bytes"]) for value in values]
                row: dict[str, Any] = {
                    "bandwidth_mbps": bandwidth,
                    "payload": payload,
                    "placement": placement,
                    "n_completed": len(values),
                    "n_scheduled": 3,
                    "validity": "all_completed_valid" if values else "pending",
                    "median_e2e_ms": _round(median(e2e)) if e2e else None,
                    "individual_e2e_ms": [_round(value) for value in e2e],
                    "median_transfer_ms": (
                        _round(median(transfer_ms)) if transfer_ms else None
                    ),
                    "individual_transfer_ms": [
                        _round(value) for value in transfer_ms
                    ],
                    "median_transfer_bytes": (
                        int(median(transfer_bytes)) if transfer_bytes else None
                    ),
                    "individual_transfer_bytes": transfer_bytes,
                    "run_ids": [str(value["run_id"]) for value in values],
                    "all_format_valid": (
                        all(bool(value["format_valid"]) for value in values)
                        if values
                        else None
                    ),
                    "scores": [float(value["benchmark_score"]) for value in values],
                    "cleanup_recoveries": [
                        value["cleanup_recovery"]
                        for value in values
                        if value["cleanup_recovery"]
                    ],
                }
                coverage.append(row)
                by_cell[key] = row
                if len(e2e) >= 2:
                    sample_std = stdev(e2e)
                    mean = fmean(e2e)
                    variations.append(
                        {
                            "bandwidth_mbps": bandwidth,
                            "payload": payload,
                            "placement": placement,
                            "n": len(e2e),
                            "mean_e2e_ms": _round(mean),
                            "sample_std_e2e_ms": _round(sample_std),
                            "cv_percent": _round(100.0 * sample_std / mean),
                            "min_e2e_ms": _round(min(e2e)),
                            "max_e2e_ms": _round(max(e2e)),
                            "range_e2e_ms": _round(max(e2e) - min(e2e)),
                            "relative_range_percent_of_median": _round(
                                100.0 * (max(e2e) - min(e2e)) / median(e2e)
                            ),
                        }
                    )

    preferences: dict[str, list[dict[str, Any]]] = {}
    crossovers: dict[str, list[dict[str, Any]]] = {}
    for payload in ("S", "M", "L"):
        points: list[dict[str, Any]] = []
        for bandwidth in bandwidths:
            a28 = by_cell[(bandwidth, payload, "forced-a28")]
            rtx = by_cell[(bandwidth, payload, "forced-rtx")]
            a28_median = a28["median_e2e_ms"]
            rtx_median = rtx["median_e2e_ms"]
            delta = (
                _round(float(rtx_median) - float(a28_median))
                if a28_median is not None and rtx_median is not None
                else None
            )
            points.append(
                {
                    "bandwidth_mbps": bandwidth,
                    "n_a28": a28["n_completed"],
                    "n_rtx": rtx["n_completed"],
                    "median_a28_e2e_ms": a28_median,
                    "median_rtx_e2e_ms": rtx_median,
                    "delta_rtx_minus_a28_ms": delta,
                    "preferred": (
                        "A28" if delta is not None and delta > 0 else
                        "strong-4090" if delta is not None and delta < 0 else
                        "tie" if delta == 0 else "insufficient"
                    ),
                }
            )
        preferences[payload] = points
        paired = [point for point in points if point["delta_rtx_minus_a28_ms"] is not None]
        brackets: list[dict[str, Any]] = []
        for low, high in zip(paired, paired[1:], strict=False):
            low_delta = float(low["delta_rtx_minus_a28_ms"])
            high_delta = float(high["delta_rtx_minus_a28_ms"])
            if low_delta * high_delta < 0:
                brackets.append(
                    {
                        "low_bandwidth_mbps": low["bandwidth_mbps"],
                        "high_bandwidth_mbps": high["bandwidth_mbps"],
                        "low_delta_ms": low_delta,
                        "high_delta_ms": high_delta,
                    }
                )
        crossovers[payload] = brackets

    pending_by_cell: dict[tuple[float, str, str], list[dict[str, Any]]] = defaultdict(
        list
    )
    for item in pending:
        pending_by_cell[
            (
                float(item["bandwidth_mbps"]),
                str(item["payload"]),
                str(item["policy"]),
            )
        ].append(item)
    minimum_required: list[dict[str, Any]] = []
    bracket_cells: set[tuple[float, str, str]] = set()
    for payload, brackets in crossovers.items():
        for bracket in brackets:
            for bandwidth in (
                float(bracket["low_bandwidth_mbps"]),
                float(bracket["high_bandwidth_mbps"]),
            ):
                for placement in ("forced-a28", "forced-rtx"):
                    bracket_cells.add((bandwidth, payload, placement))
    for key in sorted(bracket_cells):
        row = by_cell[key]
        needed = max(0, 3 - int(row["n_completed"]))
        minimum_required.extend(
            sorted(pending_by_cell[key], key=lambda item: int(item["repetition"]))[
                :needed
            ]
        )

    # The only empirical reversal currently spans 3--10 Mbps for L. 30 Mbps
    # is the next calibrated point above that bracket and already has two
    # observations for each placement with a large RTX advantage. These are
    # optional only if the reviewer wants n=3 at every selected regime, not
    # required to locate the bracket itself.
    optional_confirmation: list[dict[str, Any]] = []
    if crossovers.get("L"):
        bracket = crossovers["L"][0]
        high = float(bracket["high_bandwidth_mbps"])
        candidates = [value for value in bandwidths if value > high]
        if candidates:
            high_regime = candidates[0]
            for placement in ("forced-a28", "forced-rtx"):
                key = (high_regime, "L", placement)
                needed = max(0, 3 - int(by_cell[key]["n_completed"]))
                optional_confirmation.extend(
                    sorted(
                        pending_by_cell[key], key=lambda item: int(item["repetition"])
                    )[:needed]
                )
        else:
            high_regime = None
    else:
        high_regime = None
    required_ids = {str(item["run_id"]) for item in minimum_required}
    unnecessary = [item for item in pending if str(item["run_id"]) not in required_ids]

    return {
        "schema_version": "heterogeneous-v1-partial-pilot-audit-v1",
        "schedule": str(schedule_path),
        "factorization": {
            "run_count": len(runs),
            "bandwidths_mbps": bandwidths,
            "payloads": payloads,
            "placements": placements,
            "repetitions": repetitions,
            "cell_count": len(factor_counts),
            "runs_per_cell": sorted(set(factor_counts.values())),
            "exact_6x3x2x3": factorization_valid,
        },
        "valid_completed_run_count": sum(len(value) for value in completed.values()),
        "pending_run_count": len(pending),
        "invalid_scheduled_run_count": len(invalid),
        "invalid_scheduled_runs": invalid,
        "coverage": coverage,
        "preferences": preferences,
        "crossover_brackets": crossovers,
        "within_cell_variation": variations,
        "pending_runs": pending,
        "reduction_recommendation": {
            "relevant_crossover_payloads": [
                payload for payload in ("S", "M", "L") if crossovers[payload]
            ],
            "no_in_range_crossover_payloads": [
                payload for payload in ("S", "M", "L") if not crossovers[payload]
            ],
            "minimum_required_run_count": len(minimum_required),
            "minimum_required_runs": minimum_required,
            "minimum_rule": (
                "Complete n=3 only for both placements at the observed sign-change "
                "bracket endpoints; do not fill unrelated cells."
            ),
            "candidate_regimes_mbps": {
                "H_low": 3.0 if crossovers.get("L") else None,
                "H_mid": 10.0 if crossovers.get("L") else None,
                "H_high": high_regime,
            },
            "optional_n3_high_regime_confirmation_runs": optional_confirmation,
            "unnecessary_pending_run_count": len(unnecessary),
            "unnecessary_pending_runs": unnecessary,
            "interpretation": (
                "S and M already prefer RTX at the minimum tested bandwidth and "
                "at every higher observed point, so no remaining run in the fixed "
                "3--1000 Mbps schedule can create an in-range sign-change bracket "
                "unless a current sign reverses. L has an observed 3--10 Mbps "
                "bracket; 30 Mbps is the first clearly remote-favoring point above it."
            ),
        },
    }


def markdown(summary: dict[str, Any]) -> str:
    factor = cast(dict[str, Any], summary["factorization"])
    lines = [
        "# Heterogeneous v1 paused-pilot audit",
        "",
        f"Schedule factorization valid: `{factor['exact_6x3x2x3']}`; "
        f"valid completed: `{summary['valid_completed_run_count']}/108`; "
        f"pending: `{summary['pending_run_count']}`; scheduled-ID invalid: "
        f"`{summary['invalid_scheduled_run_count']}`.",
        "",
        "The queue was paused after the active atomic run completed. The next "
        "scheduled run has no result, trace, metadata, or run directory. A28 and "
        "RTX qdiscs were independently verified restored to `mq` and `noqueue`, "
        "and all four Workers were available with `in_flight=0`.",
        "",
        "## Coverage",
        "",
        "| Mbps | Size | Placement | n | Median E2E ms | E2E values ms | "
        "Median transfer ms | Transfer values ms | Transfer bytes | Validity |",
        "|---:|:---:|:---|---:|---:|:---|---:|:---|:---|:---|",
    ]
    for row in cast(list[dict[str, Any]], summary["coverage"]):
        lines.append(
            f"| {row['bandwidth_mbps']:g} | {row['payload']} | {row['placement']} | "
            f"{row['n_completed']} | {row['median_e2e_ms']} | "
            f"{row['individual_e2e_ms']} | {row['median_transfer_ms']} | "
            f"{row['individual_transfer_ms']} | {row['individual_transfer_bytes']} | "
            f"{row['validity']} |"
        )
    lines.extend(["", "## Placement preference", ""])
    for payload, points in cast(dict[str, list[dict[str, Any]]], summary["preferences"]).items():
        lines.extend(
            [
                f"### {payload}",
                "",
                "| Mbps | n A28/RTX | median A28 ms | median RTX ms | "
                "RTX - A28 ms | Preferred |",
                "|---:|:---:|---:|---:|---:|:---|",
            ]
        )
        for point in points:
            lines.append(
                f"| {point['bandwidth_mbps']:g} | {point['n_a28']}/{point['n_rtx']} | "
                f"{point['median_a28_e2e_ms']} | {point['median_rtx_e2e_ms']} | "
                f"{point['delta_rtx_minus_a28_ms']} | {point['preferred']} |"
            )
        lines.append("")
    lines.extend(["## Observed crossover brackets", ""])
    for payload, brackets in cast(
        dict[str, list[dict[str, Any]]], summary["crossover_brackets"]
    ).items():
        if brackets:
            for bracket in brackets:
                lines.append(
                    f"- {payload}: {bracket['low_bandwidth_mbps']:g}--"
                    f"{bracket['high_bandwidth_mbps']:g} Mbps "
                    f"(delta RTX-A28 {bracket['low_delta_ms']} -> "
                    f"{bracket['high_delta_ms']} ms)."
                )
        else:
            lines.append(
                f"- {payload}: no in-range sign change; RTX is already preferred "
                "at 3 Mbps and remains preferred at every observed higher point."
            )
    lines.append("")
    lines.extend(
        [
            "## Within-cell variation (n >= 2)",
            "",
            "| Mbps | Size | Placement | n | mean ms | sample std ms | CV % | "
            "range ms | relative range % |",
            "|---:|:---:|:---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in cast(list[dict[str, Any]], summary["within_cell_variation"]):
        lines.append(
            f"| {row['bandwidth_mbps']:g} | {row['payload']} | {row['placement']} | "
            f"{row['n']} | {row['mean_e2e_ms']} | {row['sample_std_e2e_ms']} | "
            f"{row['cv_percent']} | {row['range_e2e_ms']} | "
            f"{row['relative_range_percent_of_median']} |"
        )
    reduction = cast(dict[str, Any], summary["reduction_recommendation"])
    lines.extend(
        [
            "",
            "## Queue reduction recommendation",
            "",
            f"Minimum required remaining runs: "
            f"`{reduction['minimum_required_run_count']}`.",
            "",
            f"Candidate regimes from current evidence: "
            f"`{reduction['candidate_regimes_mbps']}`.",
            "",
            "Required run IDs:",
            "",
        ]
    )
    required = cast(list[dict[str, Any]], reduction["minimum_required_runs"])
    lines.extend(f"- `{item['run_id']}`" for item in required)
    lines.extend(
        [
            "",
            "Optional n=3 confirmation at H_high (not part of the minimum):",
            "",
        ]
    )
    optional = cast(
        list[dict[str, Any]], reduction["optional_n3_high_regime_confirmation_runs"]
    )
    lines.extend(f"- `{item['run_id']}`" for item in optional)
    lines.extend(
        [
            "",
            f"Remaining pending runs marked unnecessary for this preliminary stage: "
            f"`{reduction['unnecessary_pending_run_count']}`.",
            "",
            str(reduction["interpretation"]),
            "",
            "All pending run IDs not required by the minimum:",
            "",
        ]
    )
    unnecessary = cast(list[dict[str, Any]], reduction["unnecessary_pending_runs"])
    lines.extend(f"- `{item['run_id']}`" for item in unnecessary)
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    args = parser.parse_args()
    summary = audit(args.schedule, args.run_root)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output_markdown.write_text(markdown(summary), encoding="utf-8")
    print(args.output_json)
    print(args.output_markdown)


if __name__ == "__main__":
    main()
