import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from cost_guidance_cell_analysis_v1 import analyze, measured_sum, profile_error  # noqa: E402


def test_usage_unknown_is_not_measured_zero_and_profiles_do_not_extrapolate() -> None:
    assert measured_sum([{"tokens": None}, {"tokens": 3}], "tokens") == {
        "observed_sum": 3, "measured_receipts": 1, "unknown_receipts": 1,
        "complete_total": None,
    }
    assert profile_error({"source": "unknown"}, 30)["p50_error_ms"] is None
    assert profile_error({"source": "empirical", "sample_count": 3,
                          "p50_ms": 20, "p90_ms": 25}, 30)["p50_error_ms"] == 10


def test_quote_accuracy_compares_work_not_joint_quantiles_or_wall_time() -> None:
    profile = {"source": "empirical", "sample_count": 3, "p50_ms": 20, "p90_ms": 30}
    consequence = {"operator": "invoke_model", "movement": {
        "configured_serialization_ms": 2, "empirical_transfer_receipts": [profile]},
        "model_service": profile, "context": {"envelope_fits": True}}
    events = [{"event_type": "logical.cost_quote.created", "payload": {
        "quote": {"quote_id": "q", "action_sha256": "h"}, "action": {}}},
        {"event_type": "logical.cost_quote.observed", "payload": {
            "quote_id": "q", "action_id": "a", "succeeded": True,
            "predicted_consequence": consequence, "predicted_transfer_bytes": 10,
            "actual_transfer_bytes": 10, "transfer_bytes_error": 0,
            "actual_transfer_work_ms": 22, "actual_model_service_ms": 40}},
        {"event_type": "physical.execution", "payload": {
            "action_id": "a", "execution": {"transfers": [
                {"duration_ms": 22, "bytes_transferred": 10}]}}}]
    result = analyze(events)["estimated_vs_observed"][0]
    assert result["transfer_p50_work_error_ms"] == 2
    assert result["model_service_error"]["p50_error_ms"] == 20
    assert result["context_preflight_prediction_match"] is True
    assert result["transfer_estimate_is_joint_quantile_or_wall_time"] is False
    events[-1]["payload"]["execution"]["transfers"] = []
    result = analyze(events)["estimated_vs_observed"][0]
    assert result["transfer_p50_work_error_ms"] is None
    assert result["transfer_prediction_error_unknown_reason"] is not None
