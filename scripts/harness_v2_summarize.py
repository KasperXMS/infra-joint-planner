"""Aggregate redacted Harness v2 cell evidence without reading raw traces."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "cells": len(rows),
        "completed": sum(row["execution_completed"] is True for row in rows),
        "tsr_successes": sum(row["score"] == 1 for row in rows),
        "known_score_sum": sum(float(row["score"] or 0) for row in rows),
        "failure_types": dict(
            Counter(row["failure_reason"] or row["failure_code"] or "none" for row in rows)
        ),
        "manager_schema_invalid": sum(row["schema_invalid"] for row in rows),
        "verifier_schema_invalid": sum(row["verifier_schema_invalid"] for row in rows),
        "context_integrity_failures": sum(row["context_integrity_failures"] for row in rows),
        "manager_turns_observed": sum(row["manager_turns_observed"] for row in rows),
        "specialist_turns_observed": sum(row["specialist_turns_observed"] for row in rows),
        "verifier_calls": sum(row["verification_calls"] for row in rows),
        "physical_inference_calls": sum(row["physical_inference_calls"] for row in rows),
        "physical_service_work_ms": sum(row["physical_service_work_ms"] for row in rows),
        "e2e_ms": sum(row["e2e_ms"] for row in rows),
        "transfer_bytes": sum(row["initial_bytes"] + row["action_transfer_bytes"] for row in rows),
        "ledger_guidance_calls": sum(row["ledger_guidance_calls"] for row in rows),
        "raw_profile_guidance_calls": sum(row["raw_profile_guidance_calls"] for row in rows),
        "unknown_cloud_cost_calls": sum(row["unknown_cloud_cost_calls"] or 0 for row in rows),
        "role_usage": {},
    }
    for role in ("manager", "specialist", "verifier"):
        output["role_usage"][role] = {
            "calls": sum(row["role_usage"].get(role, {}).get("calls", 0) for row in rows),
            "prompt_tokens": sum(
                row["role_usage"].get(role, {}).get("prompt_tokens", 0) for row in rows
            ),
            "completion_tokens": sum(
                row["role_usage"].get(role, {}).get("completion_tokens", 0) for row in rows
            ),
            "provider_latency_ms": sum(
                row["role_usage"].get(role, {}).get("provider_latency_ms", 0) for row in rows
            ),
        }
    if all(row["cloud_api_usd"] is not None for row in rows):
        output["cloud_api_usd"] = str(
            sum((Decimal(row["cloud_api_usd"]) for row in rows), start=Decimal(0))
        )
    else:
        output["cloud_api_usd"] = None
    output["local_gpu_usd"] = None
    return output


def summarize(source: Path, output: Path) -> None:
    data = json.loads(source.read_text(encoding="utf-8"))
    rows = data["cells"]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        cell = row["cell"]
        if row["stage"] == "stage1":
            key = f"stage1/{cell['group']}"
        elif row["stage"] == "stage1_5":
            key = "stage1_5/H2"
        elif row["stage"] == "stage2":
            key = f"stage2/{cell['network']}/{cell['method']}"
        else:
            key = row["stage"]
        grouped[key].append(row)

    levels = Counter(pair["change_level"] for pair in data["paired_workflow_differences"])
    by_pair: dict[tuple[str, str, str], dict[int, dict[str, Any]]] = defaultdict(dict)
    for pair in data["paired_workflow_differences"]:
        by_pair[(pair["source_task_id"], pair["network"], pair["method"])][pair["trial"]] = pair
    repeatable: list[dict[str, Any]] = []
    for (task, network, method), trials in sorted(by_pair.items()):
        if set(trials) != {1, 2} or any(row["change_level"] != "L2" for row in trials.values()):
            continue
        repeatable.append(
            {
                "source_task_id": task,
                "network": network,
                "method": method,
                "quality_preserved_both_trials": all(
                    row["blind_score"] == row["method_score"] == 1 for row in trials.values()
                ),
                "e2e_lower_both_trials": all(
                    row["method_e2e_ms"] < row["blind_e2e_ms"] for row in trials.values()
                ),
                "cloud_api_lower_both_trials": (
                    all(
                        Decimal(row["method_cloud_api_usd"]) < Decimal(row["blind_cloud_api_usd"])
                        for row in trials.values()
                    )
                    if all(
                        row["method_cloud_api_usd"] is not None
                        and row["blind_cloud_api_usd"] is not None
                        for row in trials.values()
                    )
                    else None
                ),
                "transfer_lower_both_trials": all(
                    row["method_transfer_bytes"] < row["blind_transfer_bytes"]
                    for row in trials.values()
                ),
                "physical_service_work_lower_both_trials": all(
                    row["method_physical_service_work_ms"] < row["blind_physical_service_work_ms"]
                    for row in trials.values()
                ),
            }
        )

    report: dict[str, Any] = {
        "version": "harness-v2-aggregate-001",
        "stage_counts": data["stage_counts"],
        "incomplete_claims": data["incomplete_claims"],
        "groups": {key: aggregate(value) for key, value in sorted(grouped.items())},
        "paired_change_levels": dict(levels),
        "repeatable_structural_l2": repeatable,
        "statistical_significance_claimed": False,
        "full_local_gpu_monetary_cost": None,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({"groups": list(report["groups"]), "output": str(output)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    summarize(arguments.source, arguments.output)
