"""Build a prompt-free audit summary from Blind budget-diagnostic traces."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, cast


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _events(path: Path) -> list[dict[str, Any]]:
    return [
        cast(dict[str, Any], json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _final_nodes(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    snapshots = [
        cast(dict[str, Any], item["payload"])
        for item in events
        if item["event_type"] == "workflow.graph.snapshot"
    ]
    if not snapshots:
        return {}
    return {
        str(item["action_id"]): item
        for item in cast(list[dict[str, Any]], snapshots[-1]["nodes"])
    }


def _action_order(events: list[dict[str, Any]]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for event in events:
        if event["event_type"] != "logical.batch.validation":
            continue
        payload = cast(dict[str, Any], event["payload"])
        for raw in cast(list[object], payload.get("action_ids", [])):
            action_id = str(raw)
            if action_id not in seen:
                seen.add(action_id)
                result.append(action_id)
    return result


def _model_audit(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    requirements = {
        str(payload["action_id"]): payload
        for event in events
        if event["event_type"] == "logical.model.requirements"
        for payload in [cast(dict[str, Any], event["payload"])]
    }
    outcomes = {
        str(payload["action_id"]): payload
        for event in events
        if event["event_type"] == "logical.model.outcome"
        for payload in [cast(dict[str, Any], event["payload"])]
    }
    physical = {
        str(payload["action_id"]): payload
        for event in events
        if event["event_type"] == "physical.execution"
        for payload in [cast(dict[str, Any], event["payload"])]
    }
    result: list[dict[str, Any]] = []
    for action_id, request in requirements.items():
        outcome = outcomes.get(action_id, {})
        failure_code = outcome.get("failure_code")
        static_feasible = bool(request["static_feasible"])
        reached = bool(outcome.get("reached_model_inference", False))
        if not static_feasible:
            classification = "static_impossible_request"
        elif reached:
            classification = "static_feasible_reached_inference"
        elif failure_code in {"deployment_unavailable", "physical_feasibility_failed"}:
            classification = "dynamic_physical_feasibility_failure"
        elif failure_code is not None:
            classification = "static_or_artifact_aware_preflight_misuse"
        else:
            classification = "no_outcome_before_loop_stop"
        selection = physical.get(action_id, {}).get("selection")
        selected = cast(dict[str, Any], selection) if isinstance(selection, dict) else {}
        result.append(
            {
                "action_id": action_id,
                "owner_agent_id": request["owner_agent_id"],
                "requested": request["requested"],
                "matching_model_classes": request["matching_model_classes"],
                "static_feasible": static_feasible,
                "succeeded": outcome.get("succeeded"),
                "failure_code": failure_code,
                "physical_selection_succeeded": outcome.get(
                    "physical_selection_succeeded"
                ),
                "reached_model_inference": reached,
                "classification": classification,
                "selected_agent_id": selected.get("selected_agent_id"),
                "selected_deployment_id": selected.get("selected_deployment_id"),
            }
        )
    return result


def _ordered_actions(
    events: list[dict[str, Any]],
    nodes: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    failures = {
        str(payload["action_id"]): payload.get("failure_code")
        for event in events
        if event["event_type"] == "logical.observation"
        for payload in [cast(dict[str, Any], event["payload"])]
        if not bool(payload["succeeded"])
    }
    return [
        {
            "ordinal": ordinal,
            "action_id": action_id,
            "owner_agent_id": nodes.get(action_id, {}).get("owner_agent_id"),
            "action_type": nodes.get(action_id, {}).get("action_type"),
            "operator": nodes.get(action_id, {}).get("operator"),
            "status": nodes.get(action_id, {}).get("status"),
            "failure_code": failures.get(action_id),
            "input_count": len(nodes.get(action_id, {}).get("inputs", [])),
            "output_count": len(nodes.get(action_id, {}).get("outputs", [])),
        }
        for ordinal, action_id in enumerate(_action_order(events), start=1)
    ]


def _longbench_diagnostic(
    actions: list[dict[str, Any]],
    models: list[dict[str, Any]],
) -> dict[str, Any]:
    context_failures = [
        item for item in actions if item["failure_code"] == "context_limit_exceeded"
    ]
    reached_ids = {
        str(item["action_id"])
        for item in models
        if item["reached_model_inference"]
    }
    reached = [item for item in actions if item["action_id"] in reached_ids]
    first_failure = context_failures[0] if context_failures else None
    first_reached = reached[0] if reached else None
    between: list[dict[str, Any]] = []
    distance: int | None = None
    if first_failure is not None:
        upper = (
            int(first_reached["ordinal"])
            if first_reached is not None
            else len(actions) + 1
        )
        between = [
            item
            for item in actions
            if int(first_failure["ordinal"]) < int(item["ordinal"]) < upper
        ]
        if first_reached is not None:
            distance = int(first_reached["ordinal"]) - int(first_failure["ordinal"])
    return {
        "context_failure_ordinals": [item["ordinal"] for item in context_failures],
        "first_reached_inference_ordinal": (
            None if first_reached is None else first_reached["ordinal"]
        ),
        "calls_from_first_context_failure_to_inference": distance,
        "actions_between_first_failure_and_inference_or_stop": between,
    }


def _multihop_diagnostic(actions: list[dict[str, Any]]) -> dict[str, Any]:
    operators = Counter(
        str(item["operator"])
        for item in actions
        if item["operator"] is not None
    )
    return {
        "operator_counts": dict(sorted(operators.items())),
        "retrieval_calls": operators["bm25_retrieve"],
        "aggregation_calls": operators["aggregate_artifacts"]
        + operators["aggregate_records"],
        "filter_calls": operators["filter_records"],
        "read_calls": operators["read_artifact"],
        "model_calls": operators["invoke_model"],
    }


def _logical_leakage_hits(events: list[dict[str, Any]]) -> list[str]:
    logical = json.dumps(
        [
            event
            for event in events
            if str(event["event_type"]).startswith("logical.")
        ],
        ensure_ascii=False,
        sort_keys=True,
    )
    forbidden = (
        '"source_ref"',
        '"evaluator_id"',
        "supporting_evidence",
        '"gold"',
        "192.168.0.104",
        "192.168.0.105",
        "192.168.0.128",
        "192.168.0.12",
        "a28-qwen3.8-27b-q4km-v1",
        "strong-4090-qwen3.8-27b-q4km-v1",
        '"selected_agent_id"',
        '"selected_deployment_id"',
    )
    return [token for token in forbidden if token in logical]


def analyze(root: Path) -> dict[str, Any]:
    summaries = cast(list[dict[str, Any]], _read_json(root / "summary.json"))
    runs: list[dict[str, Any]] = []
    for summary in summaries:
        run_id = str(summary["run_id"])
        events = _events(root / "runs" / run_id / "trace.jsonl")
        nodes = _final_nodes(events)
        actions = _ordered_actions(events, nodes)
        models = _model_audit(events)
        item: dict[str, Any] = {
            "run_id": run_id,
            "label": summary["label"],
            "action_call_budget": summary["action_call_budget"],
            "execution_completed": summary["execution_completed"],
            "failure_code": summary["failure_code"],
            "failure_message": summary["failure_message"],
            "telemetry": summary["telemetry"],
            "operator_counts": dict(
                sorted(
                    Counter(
                        str(node["operator"])
                        for node in nodes.values()
                        if node.get("operator") is not None
                    ).items()
                )
            ),
            "model_requests": models,
            "blind_logical_leakage_hits": _logical_leakage_hits(events),
        }
        if summary["label"] == "longbench-multidoc":
            item["longbench_diagnostic"] = _longbench_diagnostic(actions, models)
        if summary["label"] == "multihop-multisource":
            item["multihop_diagnostic"] = _multihop_diagnostic(actions)
        runs.append(item)
    video_requests = [
        request
        for run in runs
        if run["label"] == "video-cross-temporal"
        for request in cast(list[dict[str, Any]], run["model_requests"])
    ]
    return {
        "schema_version": "blind-budget-diagnostic-analysis-v1",
        "run_count": len(runs),
        "video_model_request_totals": {
            "requests": len(video_requests),
            "static_impossible": sum(
                item["classification"] == "static_impossible_request"
                for item in video_requests
            ),
            "dynamic_physical_feasibility_failures": sum(
                item["classification"] == "dynamic_physical_feasibility_failure"
                for item in video_requests
            ),
            "reached_inference": sum(
                bool(item["reached_model_inference"]) for item in video_requests
            ),
        },
        "blind_logical_leakage_free": all(
            not cast(list[str], run["blind_logical_leakage_hits"])
            for run in runs
        ),
        "runs": runs,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(args.root)
    encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(encoded, end="")
    else:
        args.output.write_text(encoded, encoding="utf-8")


if __name__ == "__main__":
    main()
