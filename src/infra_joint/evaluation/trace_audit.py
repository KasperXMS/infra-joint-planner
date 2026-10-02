"""Read-only analysis of execution intervals and SDK-native cost telemetry.

Summed service work is not wall-clock critical-path time. In particular, operator
latency for invoke_model includes model service and must never be added to it.
"""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from typing import Any, cast

Event = dict[str, Any]


@dataclass(frozen=True)
class ActionInterval:
    action_id: str
    decision_id: str
    owner: str
    start: float
    end: float


def timestamp_seconds(value: str) -> float:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("audit timestamps must be timezone-aware")
    return parsed.timestamp()


def action_intervals(events: list[Event]) -> tuple[list[ActionInterval], list[str]]:
    """Native singleton batches are action lifetimes, not sequentiality evidence.

    Multi-action legacy batches cannot supply exact per-action lifetimes and are
    reported unknown unless explicit action events exist. Touching intervals do
    not overlap. Incomplete, duplicate, and reversed intervals fail closed.
    """
    starts: dict[str, tuple[float, str, str]] = {}
    ends: dict[str, float] = {}
    invalid: set[str] = set()
    explicit = {
        str(e["payload"]["action_id"]) for e in events if e["event_type"] == "action.started"
    }
    for event in events:
        kind = event["event_type"]
        if kind not in {
            "action.started",
            "action.completed",
            "logical.batch.started",
            "logical.batch.completed",
        }:
            continue
        payload = event["payload"]
        if kind.startswith("logical.batch."):
            ids = payload.get("action_ids", [])
            if len(ids) != 1:
                invalid.update(str(a) for a in ids if str(a) not in explicit)
                continue
            action_id = str(ids[0])
            if action_id in explicit:
                continue
        else:
            action_id = str(payload["action_id"])
        if "timestamp" not in event:
            invalid.add(action_id)
            continue
        timestamp = timestamp_seconds(event["timestamp"])
        if kind.endswith("started"):
            if action_id in starts:
                invalid.add(action_id)
            starts[action_id] = (
                timestamp,
                str(payload.get("decision_id", "unknown")),
                str(payload.get("logical_agent_id", "unknown")),
            )
        else:
            if action_id in ends:
                invalid.add(action_id)
            ends[action_id] = timestamp
    invalid.update(set(starts) ^ set(ends))
    result: list[ActionInterval] = []
    for action_id in sorted(set(starts) & set(ends)):
        start, decision, owner = starts[action_id]
        end = ends[action_id]
        if end < start:
            invalid.add(action_id)
        if action_id not in invalid:
            result.append(ActionInterval(action_id, decision, owner, start, end))
    return result, sorted(invalid)


def interval_union_ms(intervals: list[tuple[float, float]]) -> float:
    total = 0.0
    end: float | None = None
    for start, finish in sorted(intervals):
        if finish < start:
            raise ValueError("negative interval")
        total += (
            finish - max(start, end if end is not None else start)
            if (end is None or finish > end)
            else 0.0
        )
        end = finish if end is None else max(end, finish)
    return total * 1000


def summarize_concurrency(events: list[Event]) -> dict[str, Any]:
    intervals, invalid = action_intervals(events)
    parallel: set[str] = set()
    turns: set[str] = set()
    pairs = 0
    cross_owner_pairs = 0
    groups: dict[str, set[str]] = {}
    for left, right in combinations(intervals, 2):
        if max(left.start, right.start) < min(left.end, right.end):
            pairs += 1
            parallel.update((left.action_id, right.action_id))
            if left.owner != right.owner:
                cross_owner_pairs += 1
            if left.decision_id == right.decision_id and left.decision_id != "unknown":
                turns.add(left.decision_id)
                groups.setdefault(left.decision_id, set()).update((left.action_id, right.action_id))
    sweep = sorted(
        (time, delta)
        for item in intervals
        if item.end > item.start
        for time, delta in ((item.start, 1), (item.end, -1))
    )
    active = peak = 0
    overlap_seconds = 0.0
    previous: float | None = None
    for time, delta in sweep:
        if previous is not None and active > 1:
            overlap_seconds += time - previous
        active += delta
        peak = max(peak, active)
        previous = time
    return {
        "concurrency_metric_version": "action-interval-overlap-v1",
        "interval_source": "explicit action events or native singleton batch lifetimes",
        "max_concurrent_actions": peak,
        "number_of_overlapping_action_pairs": pairs,
        "number_of_reasoning_turns_with_parallel_execution": len(turns),
        "total_parallelized_actions": len(parallel),
        "cross_owner_overlapping_pairs": cross_owner_pairs,
        "overlap_wall_ms": overlap_seconds * 1000,
        "action_wall_union_ms": interval_union_ms([(a.start, a.end) for a in intervals]),
        "parallel_groups": [
            {"decision_id": key, "action_ids": sorted(value)}
            for key, value in sorted(groups.items())
        ],
        "unknown_action_intervals": invalid,
    }


def summarize_cost(events: list[Event]) -> dict[str, Any]:
    model_ms = tool_ms = model_wrapper_ms = transfer_ms = initial_ms = 0.0
    manager_ms = specialist_ms = verifier_ms = 0.0
    input_tokens = output_tokens = inference_count = action_bytes = initial_bytes = 0
    e2e_ms: float | None = None
    observed_intervals: list[tuple[float, float]] = []
    pending: dict[tuple[str, str], float] = {}
    missing_timestamps = 0
    unknown_tool_latencies = unknown_model_wrapper_latencies = 0
    for event in events:
        kind, payload = event["event_type"], event["payload"]
        time = timestamp_seconds(event["timestamp"]) if "timestamp" in event else None
        missing_timestamps += time is None
        if kind in {"run.end", "run.failed"}:
            value = payload.get("e2e_latency_ms")
            if isinstance(value, int | float):
                e2e_ms = float(value)
        if time is not None and kind in {
            "logical.reasoning.started", "logical.verification.started"
        }:
            key = "reasoning" if "reasoning" in kind else "verification"
            identity = str(payload.get("decision_id", payload.get("verification_index")))
            pending[key, identity] = time
        if time is not None and kind in {"logical.reasoning.completed", "logical.verification"}:
            key = "reasoning" if "reasoning" in kind else "verification"
            identity = str(payload.get("decision_id", payload.get("verification_index")))
            start = pending.pop((key, identity), None)
            if start is not None:
                observed_intervals.append((start, time))
        if kind == "logical.reasoning.completed":
            latency = float(payload["telemetry"]["latency_ms"])
            if payload.get("logical_agent_id") == "manager":
                manager_ms += latency
            else:
                specialist_ms += latency
        if kind == "logical.verification":
            verifier_ms += float(payload["latency_ms"])
        if kind == "artifact.materialize.end":
            initial_bytes += int(payload["bytes_transferred"])
            initial_ms += float(payload["duration_ms"])
        if kind != "physical.execution":
            continue
        raw_execution = payload.get("execution")
        if not isinstance(raw_execution, dict):
            continue
        execution = cast(dict[str, Any], raw_execution)
        raw_operator_ms = execution.get("operator_latency_ms")
        operator_ms = float(raw_operator_ms) if isinstance(raw_operator_ms, int | float) else None
        raw_model = execution.get("model_telemetry")
        if isinstance(raw_model, dict):
            model = cast(dict[str, Any], raw_model)
            inference_count += 1
            service = float(model["service_latency_ms"])
            model_ms += service
            if operator_ms is None or operator_ms < service:
                unknown_model_wrapper_latencies += 1
            else:
                model_wrapper_ms += operator_ms - service
            input_tokens += int(model.get("input_tokens") or 0)
            output_tokens += int(model.get("output_tokens") or 0)
        elif execution.get("operator") != "invoke_model":
            if operator_ms is None:
                unknown_tool_latencies += 1
            else:
                tool_ms += operator_ms
        for transfer in execution.get("transfers", []):
            transfer_ms += float(transfer["duration_ms"])
            action_bytes += int(transfer["bytes_transferred"])
    intervals, invalid = action_intervals(events)
    observed_intervals.extend((a.start, a.end) for a in intervals)
    union_ms = interval_union_ms(observed_intervals)
    return {
        "cost_metric_version": "trace-cost-decomposition-v1",
        "latency_accounting": "service/work sums are non-additive wall time",
        "e2e_latency_ms": e2e_ms,
        "manager_latency_ms": manager_ms,
        "specialist_latency_ms": specialist_ms,
        "verifier_latency_ms": verifier_ms,
        "tool_operator_latency_ms": None if unknown_tool_latencies else tool_ms,
        "tool_compute_only_ms": None,  # Historical timing includes the Worker HTTP call.
        "unknown_tool_latency_count": unknown_tool_latencies,
        "completed_physical_model_inferences": inference_count,
        "model_service_latency_ms": model_ms,
        "model_operator_wrapper_ms": None if unknown_model_wrapper_latencies else model_wrapper_ms,
        "unknown_model_wrapper_latency_count": unknown_model_wrapper_latencies,
        "model_input_tokens": input_tokens,
        "model_output_tokens": output_tokens,
        "action_transfer_bytes": action_bytes,
        "action_transfer_latency_ms": transfer_ms,
        "initial_transfer_bytes": initial_bytes,
        "initial_transfer_latency_ms": initial_ms,
        "measured_activity_wall_union_ms": union_ms,
        "unclassified_wall_time_ms": None if e2e_ms is None or missing_timestamps else max(
            0, e2e_ms - union_ms
        ),
        "idle_wait_error_recovery_ms": None,
        "other_harness_overhead_ms": None,
        "unknown_action_intervals": invalid,
        "unfinished_reasoning_or_verification_intervals": len(pending),
        "events_without_timestamps": missing_timestamps,
    }


def summarize_profiles(events: list[Event]) -> dict[str, Any]:
    """Read JSONL, including failed runs whose returned loop/result is absent."""
    profiles = [
        e["payload"]["physical_profile"]
        for e in events
        if e["event_type"] == "logical.observation"
        and isinstance(e["payload"].get("physical_profile"), dict)
    ]
    return {
        "physical_profile_observations": len(profiles),
        "observed_network_classes": sorted({p["network_class"] for p in profiles}),
        "network_class_counts": dict(Counter(p["network_class"] for p in profiles)),
        "unknown_service_profiles": sum(
            p.get("service_latency_ms_range") is None for p in profiles
        ),
    }
