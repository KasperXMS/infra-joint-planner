import sys
from importlib import import_module
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
audit = import_module("predecision_trace_audit_v1")


def test_model_action_is_not_assumed_to_have_tool_operator() -> None:
    assert audit.operator({"action_type": "model", "prompt": "answer"}) == "invoke_model"
    assert audit.operator({"action_type": "tool", "operator": "bm25_retrieve"}) == "bm25_retrieve"
    assert audit.execution({"payload": {"execution": None}}) == {}
    assert audit.known_sum([3, None]) is None
    assert audit.known_sum([3, 4]) == 7
    assert audit.known_sum([]) == 0


def test_aggregate_preserves_missing_evaluations_and_unknown_costs() -> None:
    keys = ("e2e_latency_ms", "action_transfer_bytes", "action_transfer_latency_ms",
            "model_service_latency_ms", "completed_physical_model_inferences",
            "manager_latency_ms", "specialist_latency_ms", "verifier_latency_ms",
            "tool_operator_latency_ms")
    rows: list[dict[str, Any]] = [{
        "condition": "fast-blind", "completion": done,
        "evaluation": {"benchmark_score": 0} if done else None,
        "first_actions": [{"payload": {"action": {"action_type": "model"}}}],
        "cost": dict.fromkeys(keys, value),
    } for done, value in ((True, 10), (False, None))]
    result = audit.aggregate(rows)["fast-blind"]
    assert result["completed"] == 1
    assert result["evaluated"] == 1
    assert result["missing_evaluation_count"] == 1
    assert result["mean_score_evaluated_only"] == 0
    assert result["e2e_latency_ms"] == {
        "individual": [10, None], "unknown": 1, "mean_known": 10, "median_known": 10,
    }
    assert result["first_operator_signatures"] == [["invoke_model"], ["invoke_model"]]
