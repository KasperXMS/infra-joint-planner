from typing import Any

import pytest

from infra_joint.evaluation.trace_audit import (
    summarize_concurrency,
    summarize_cost,
    summarize_profiles,
)


def event(kind: str, second: int, **payload: Any) -> dict[str, Any]:
    return {
        "event_type": kind,
        "timestamp": f"2026-10-02T00:00:{second:02d}Z",
        "payload": payload,
    }


def action(action_id: str, start: int, end: int, decision: str = "turn-1") -> list[dict[str, Any]]:
    return [
        event(
            "logical.batch.started",
            start,
            action_ids=[action_id],
            decision_id=decision,
            logical_agent_id="manager",
        ),
        event(
            "logical.batch.completed",
            end,
            action_ids=[action_id],
            decision_id=decision,
            logical_agent_id="manager",
        ),
    ]


def test_singleton_batches_can_overlap() -> None:
    summary = summarize_concurrency(action("a", 1, 5) + action("b", 2, 4) + action("c", 5, 6))
    assert summary["max_concurrent_actions"] == 2
    assert summary["number_of_overlapping_action_pairs"] == 1
    assert summary["total_parallelized_actions"] == 2
    assert summary["number_of_reasoning_turns_with_parallel_execution"] == 1
    assert summary["overlap_wall_ms"] == 2000
    assert summary["action_wall_union_ms"] == 5000


def test_touching_intervals_are_sequential() -> None:
    summary = summarize_concurrency(action("a", 1, 2) + action("b", 2, 3, "turn-2"))
    assert summary["max_concurrent_actions"] == 1
    assert summary["number_of_overlapping_action_pairs"] == 0
    assert summary["number_of_reasoning_turns_with_parallel_execution"] == 0


def test_four_independent_actions_and_distinct_parallel_turns() -> None:
    events = [e for i in range(4) for e in action(str(i), 1, 3)]
    events.extend(action("later-a", 4, 7, "turn-2") + action("later-b", 5, 6, "turn-2"))
    summary = summarize_concurrency(events)
    assert summary["max_concurrent_actions"] == 4
    assert summary["number_of_overlapping_action_pairs"] == 7
    assert summary["number_of_reasoning_turns_with_parallel_execution"] == 2
    assert summary["total_parallelized_actions"] == 6


def test_incomplete_reversed_and_multi_action_batch_intervals_are_unknown() -> None:
    events = action("reverse", 5, 4) + action("incomplete", 1, 2)[:1]
    events += [event("logical.batch.started", 1, action_ids=["x", "y"])]
    summary = summarize_concurrency(events)
    assert summary["unknown_action_intervals"] == ["incomplete", "reverse", "x", "y"]
    assert summary["max_concurrent_actions"] == 0


def test_failed_run_profiles_are_counted_without_result_loop() -> None:
    summary = summarize_profiles(
        [
            event(
                "logical.observation",
                1,
                physical_profile={
                    "network_class": "constrained",
                    "service_latency_ms_range": None,
                },
            ),
            event("run.failed", 2),
        ]
    )
    assert summary["physical_profile_observations"] == 1
    assert summary["unknown_service_profiles"] == 1


def test_model_service_is_not_double_counted_as_tool_compute() -> None:
    summary = summarize_cost(
        [
            event(
                "physical.execution",
                5,
                execution={
                    "operator": "invoke_model",
                    "operator_latency_ms": 4100,
                    "model_telemetry": {
                        "service_latency_ms": 4000,
                        "input_tokens": 3,
                        "output_tokens": 1,
                    },
                    "transfers": [],
                },
            ),
            event("logical.observation", 6, failure_code="context_limit_exceeded"),
            event("run.end", 7, e2e_latency_ms=7000),
        ]
    )
    assert summary["completed_physical_model_inferences"] == 1
    assert summary["model_service_latency_ms"] == 4000
    assert summary["model_operator_wrapper_ms"] == 100
    assert summary["tool_operator_latency_ms"] == 0
    assert summary["tool_compute_only_ms"] is None
    assert summary["idle_wait_error_recovery_ms"] is None


def test_timezone_required() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        summarize_concurrency(
            [
                {
                    "event_type": "action.started",
                    "timestamp": "2026-10-02T00:00:00",
                    "payload": {"action_id": "x"},
                }
            ]
        )


@pytest.mark.parametrize("operator_ms", [None, 3000])
def test_missing_or_inconsistent_latency_is_unknown_not_zero(operator_ms: int | None) -> None:
    execution = {
        "operator": "invoke_model", "model_telemetry": {"service_latency_ms": 4000},
        "operator_latency_ms": operator_ms,
    }
    summary = summarize_cost([event("physical.execution", 5, execution=execution)])
    assert summary["model_operator_wrapper_ms"] is None
    assert summary["unknown_model_wrapper_latency_count"] == 1
