"""Compare frozen Stage 2 workflows using ID-free structural features."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

EVIDENCE_OPERATORS = frozenset(
    {
        "select_fields",
        "top_k_records",
        "aggregate_artifacts",
        "sample_frames",
        "make_contact_sheet",
        "extract_clip",
        "read_artifact",
    }
)


def edit_distance(left: list[str], right: list[str]) -> int:
    previous = list(range(len(right) + 1))
    for index, item in enumerate(left, 1):
        current = [index]
        for column, other in enumerate(right, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (item != other),
                )
            )
        previous = current
    return previous[-1]


def collapse(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if not result or result[-1] != item:
            result.append(item)
    return result


def features(row: dict[str, Any]) -> dict[str, Any]:
    workflow = row["workflow"]
    actions = workflow["logical_signature"]
    sequence = workflow["operator_sequence"]
    counts = Counter(sequence)
    artifact_edges = [
        (int(source.split(":", 1)[1]), consumer_index)
        for consumer_index, action in enumerate(actions)
        for source in action["input_flow"]
        if source.startswith("produced:")
    ]
    model_inputs = [
        tuple(action["input_flow"]) for action in actions if action["action_type"] == "model"
    ]
    return {
        "cell_id": row["cell"]["cell_id"],
        "source_task_id": row["cell"]["source_task_id"],
        "family": row["cell"]["family"],
        "network": row["cell"]["network"],
        "method": row["cell"]["method"],
        "trial": row["cell"]["trial"],
        "operators": sequence,
        "operator_counts": dict(counts),
        "collapsed_operators": collapse(sequence),
        "action_count": len(actions),
        "model_action_count": counts["invoke_model"],
        "explicit_dependency_count": sum(len(action["depends_on"]) for action in actions),
        "explicit_dependency_edges": [
            (source, index)
            for index, action in enumerate(actions)
            for source in action["depends_on"]
        ],
        "artifact_dependency_edges": artifact_edges,
        "artifact_input_flow": [action["input_flow"] for action in actions],
        "artifact_input_edge_count": sum(len(action["input_flow"]) for action in actions),
        "model_input_arity": [len(inputs) for inputs in model_inputs],
        "model_input_flow": model_inputs,
        "evidence_operator_counts": {
            name: counts[name] for name in sorted(EVIDENCE_OPERATORS) if counts[name]
        },
        "consecutive_repetition_count": len(sequence) - len(collapse(sequence)),
        "specialist_decisions": workflow["specialist_decisions"],
        "physical_placements": workflow["physical_placements"],
        "score": row["score"],
        "completed": row["execution_completed"],
        "failure_reason": row["failure_reason"],
        "e2e_ms": row["e2e_ms"],
        "cloud_api_usd": row["cloud_api_usd"],
        "physical_service_work_ms": row["physical_service_work_ms"],
        "transfer_bytes": row["initial_bytes"] + row["action_transfer_bytes"],
        "physical_context_rejections": row["physical_rejections"].get("context_limit_exceeded", 0),
        "manager_calls": row["role_usage"].get("manager", {}).get("calls", 0),
        "verifier_calls": row["role_usage"].get("verifier", {}).get("calls", 0),
    }


def compare(kind: str, left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_ops = left["operators"]
    right_ops = right["operators"]
    distance = edit_distance(left_ops, right_ops)
    collapsed_distance = edit_distance(left["collapsed_operators"], right["collapsed_operators"])
    counts_left = Counter(left_ops)
    counts_right = Counter(right_ops)
    both_correct = left["score"] == right["score"] == 1
    cloud_lower = (
        Decimal(right["cloud_api_usd"]) < Decimal(left["cloud_api_usd"])
        if left["cloud_api_usd"] is not None and right["cloud_api_usd"] is not None
        else None
    )
    return {
        "kind": kind,
        "left_cell": left["cell_id"],
        "right_cell": right["cell_id"],
        "family": left["family"],
        "source_task_id": left["source_task_id"],
        "method_left": left["method"],
        "method_right": right["method"],
        "network_left": left["network"],
        "network_right": right["network"],
        "trial_left": left["trial"],
        "trial_right": right["trial"],
        "operator_edit_distance": distance,
        "normalized_operator_edit_distance": distance / max(len(left_ops), len(right_ops), 1),
        "collapsed_operator_edit_distance": collapsed_distance,
        "operator_multiset_l1": sum(
            abs(counts_left[name] - counts_right[name])
            for name in counts_left.keys() | counts_right.keys()
        ),
        "explicit_dependency_count_delta": right["explicit_dependency_count"]
        - left["explicit_dependency_count"],
        "artifact_dependency_graph_changed": left["artifact_dependency_edges"]
        != right["artifact_dependency_edges"],
        "artifact_input_edge_count_delta": right["artifact_input_edge_count"]
        - left["artifact_input_edge_count"],
        "model_input_arity_changed": left["model_input_arity"] != right["model_input_arity"],
        "model_input_flow_changed": left["model_input_flow"] != right["model_input_flow"],
        "evidence_operator_counts_changed": left["evidence_operator_counts"]
        != right["evidence_operator_counts"],
        "physical_placement_changed": left["physical_placements"] != right["physical_placements"],
        "both_correct": both_correct,
        "score_left": left["score"],
        "score_right": right["score"],
        "e2e_delta_ms": right["e2e_ms"] - left["e2e_ms"],
        "cloud_api_lower": cloud_lower,
        "physical_service_work_delta_ms": right["physical_service_work_ms"]
        - left["physical_service_work_ms"],
        "transfer_delta_bytes": right["transfer_bytes"] - left["transfer_bytes"],
    }


def main(source: Path, output: Path) -> None:
    data = json.loads(source.read_text(encoding="utf-8"))
    cells = [features(row) for row in data["cells"] if row["stage"] == "stage2"]
    by_key: dict[tuple[str, str, str, int], dict[str, Any]] = {
        (row["source_task_id"], row["network"], row["method"], row["trial"]): row for row in cells
    }
    comparisons: list[dict[str, Any]] = []
    tasks = sorted({row["source_task_id"] for row in cells})
    for task in tasks:
        for network in ("slow", "fast"):
            for method in ("BLIND", "AWARE", "LEDGER"):
                comparisons.append(
                    compare(
                        "within_condition_trial",
                        by_key[(task, network, method, 1)],
                        by_key[(task, network, method, 2)],
                    )
                )
                for trial in (1, 2):
                    if method != "BLIND":
                        comparisons.append(
                            compare(
                                "between_method",
                                by_key[(task, network, "BLIND", trial)],
                                by_key[(task, network, method, trial)],
                            )
                        )
        for method in ("BLIND", "AWARE", "LEDGER"):
            for trial in (1, 2):
                comparisons.append(
                    compare(
                        "across_infrastructure",
                        by_key[(task, "slow", method, trial)],
                        by_key[(task, "fast", method, trial)],
                    )
                )
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in comparisons:
        groups[item["kind"]].append(item)
    report = {
        "version": "harness-v2-workflow-variation-001",
        "cells": cells,
        "comparisons": comparisons,
        "summary": {
            name: {
                "pairs": len(items),
                "median_normalized_operator_edit_distance": median(
                    item["normalized_operator_edit_distance"] for item in items
                ),
                "nonzero_operator_distance": sum(
                    item["operator_edit_distance"] > 0 for item in items
                ),
                "evidence_operator_count_changed": sum(
                    item["evidence_operator_counts_changed"] for item in items
                ),
                "model_input_flow_changed": sum(item["model_input_flow_changed"] for item in items),
                "artifact_dependency_graph_changed": sum(
                    item["artifact_dependency_graph_changed"] for item in items
                ),
            }
            for name, items in sorted(groups.items())
        },
        "local_gpu_usd": None,
        "significance_claimed": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps(report["summary"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    main(arguments.source, arguments.output)
