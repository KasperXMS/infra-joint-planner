import json
from typing import Any

import pytest
from pydantic import ValidationError

from infra_joint.control.consequence_profiles import (
    CostHistory,
    EmpiricalConsequenceProfiles,
    EmpiricalLatency,
    ModelServiceSample,
    OperatorWorkSample,
    TransferSample,
)
from infra_joint.control.cost_history import extract_cost_history, surface_hash


def service(index: int, latency: float, **overrides: Any) -> ModelServiceSample:
    values: dict[str, Any] = {
        "sample_sha256": f"{index:064x}", "model_class": "model-class-01",
        "execution_surface_sha256": surface_hash("a28-private"),
        "conservative_input_tokens": 4096, "actual_input_tokens": 1000,
        "image_count": 0, "output_budget": 2048, "service_latency_ms": latency,
    }
    return ModelServiceSample.model_validate(values | overrides)


def estimate(profiles: EmpiricalConsequenceProfiles, **overrides: Any) -> EmpiricalLatency:
    values: dict[str, Any] = {
        "model_class": "model-class-01", "execution_surface_sha256": surface_hash("a28-private"),
        "conservative_input_tokens": 4096, "image_count": 0, "output_budget": 2048,
    }
    return profiles.model_service(**(values | overrides))


def test_support_threshold_quantiles_and_actual_tokens_are_not_prediction_feature() -> None:
    profiles = EmpiricalConsequenceProfiles(CostHistory(models=(service(1, 10), service(2, 30))))
    assert estimate(profiles).sample_count == 2
    assert estimate(profiles).p50_ms is None
    profiles = EmpiricalConsequenceProfiles(CostHistory(models=(
        service(1, 10), service(2, 30), service(3, 20, actual_input_tokens=6000),
    )))
    result = estimate(profiles)
    assert (result.sample_count, result.p50_ms, result.p90_ms) == (3, 20, 28)


@pytest.mark.parametrize("change", [
    {"conservative_input_tokens": 4097}, {"image_count": 1}, {"output_budget": 1024},
    {"model_class": "model-class-02"}, {"execution_surface_sha256": surface_hash("rtx-private")},
    {"execution_surface_sha256": None}, {"conservative_input_tokens": None},
    {"conservative_input_tokens": 65537},
])
def test_unsupported_model_features_do_not_pool_or_extrapolate(change: dict[str, Any]) -> None:
    profiles = EmpiricalConsequenceProfiles(CostHistory(models=tuple(
        service(i, 10) for i in range(3)
    )))
    result = estimate(profiles, **change)
    assert result.source == "unknown"
    assert result.p50_ms is None and result.p90_ms is None


def test_operator_and_transfer_require_exact_surface_regime_and_supported_size_bucket() -> None:
    operator_surface = surface_hash("a28-private")
    path_surface = surface_hash("a4-private", "a28-private")
    profiles = EmpiricalConsequenceProfiles(CostHistory(
        operators=tuple(OperatorWorkSample(
            sample_sha256=f"{i:064x}", operator="bm25_retrieve", input_bytes=65536,
            execution_surface_sha256=operator_surface, wrapper_latency_ms=10,
        ) for i in range(3)),
        transfers=tuple(TransferSample(
            sample_sha256=f"{i + 3:064x}", network_category="constrained",
            path_surface_sha256=path_surface, bytes_transferred=65536, latency_ms=20,
        ) for i in range(3)),
    ))
    assert profiles.operator_work(
        "bm25_retrieve", 65535, execution_surface_sha256=operator_surface,
    ).p50_ms == 10
    assert profiles.operator_work(
        "bm25_retrieve", 65537, execution_surface_sha256=operator_surface,
    ).source == "unknown"
    assert profiles.transfer("constrained", 65536, path_surface_sha256=path_surface).p50_ms == 20
    assert profiles.transfer("fast", 65536, path_surface_sha256=path_surface).source == "unknown"
    assert profiles.transfer("constrained", 65536, path_surface_sha256=None).source == "unknown"
    assert profiles.transfer("constrained", 268435457,
                             path_surface_sha256=path_surface).source == "unknown"


@pytest.mark.parametrize("values", [
    {"source": "unknown", "sample_count": 0, "minimum_support": 3, "p50_ms": 0,
     "unknown_reason": "missing"},
    {"source": "empirical", "sample_count": 2, "minimum_support": 3,
     "p50_ms": 1, "p90_ms": 2},
    {"source": "empirical", "sample_count": 3, "minimum_support": 3,
     "p50_ms": 2, "p90_ms": 1},
])
def test_invalid_estimate_contract_is_rejected(values: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        EmpiricalLatency.model_validate(values)


def test_duplicate_and_nonfinite_cost_samples_fail_closed() -> None:
    with pytest.raises(ValidationError):
        CostHistory(models=(service(1, 10), service(1, 20)))
    with pytest.raises(ValidationError):
        service(1, float("inf"))
    with pytest.raises(ValueError):
        estimate(EmpiricalConsequenceProfiles(CostHistory()), conservative_input_tokens=-1)


def trace_event(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"run_id": "test-run", "event_type": kind, "payload": payload}


def history_events() -> list[dict[str, Any]]:
    return [
        trace_event("logical.loop.start", {
            "task": {"artifacts": [{"artifact_id": "source", "media_type": "text/plain",
                                     "size_bytes": 100}]},
            "static_capability_contract": {"model_classes": [{
                "capability_class": "model-class-01", "image_token_cost": 2048,
                "reserved_output_tokens": 2048,
            }]},
        }),
        trace_event("logical.action.prepared", {"action": {
            "action_id": "model", "action_type": "model", "inputs": ["source"],
            "prompt": "你好", "requirements": {"reserved_output_tokens": 1},
        }}),
        trace_event("physical.execution", {"action_id": "model", "execution": {
            "operator": "invoke_model", "deployment_id": "a28-private", "agent_ids": ["a28"],
            "output": {"text": "PRIVATE ANSWER"}, "model_telemetry": {
                "input_tokens": 25, "output_tokens": 2, "service_latency_ms": 80,
            }, "transfers": [{"source_agent_id": "a4-private", "target_agent_id": "a28-private",
                              "bytes_transferred": 100, "duration_ms": 10}],
        }}),
        trace_event("run.end", {"gold": "PRIVATE GOLD", "evaluation": {"score": 0}}),
    ]


def test_extraction_cost_only_actual_default_output_budget_and_deterministic_ids() -> None:
    events = history_events()
    result = extract_cost_history(events, run_id="test-run", network_category="fast")
    assert result == extract_cost_history(events, run_id="test-run", network_category="fast")
    assert result.models[0].conservative_input_tokens == 106
    assert result.models[0].actual_input_tokens == 25
    assert result.models[0].output_budget == 2048  # Requirements=1 is not backend max_tokens.
    exported = result.model_dump_json()
    for private in ("PRIVATE", "你好", "source", "a28-private", "a4-private", "score", "gold"):
        assert private not in exported


def test_failed_preflight_not_inference_or_zero_latency_sample() -> None:
    events = history_events()
    events[2]["payload"]["execution"] = None
    assert extract_cost_history(events, run_id="test-run", network_category="fast") == CostHistory()


def test_unknown_input_remains_unknown_without_future_artifact_lookahead() -> None:
    events = history_events()
    events[1]["payload"]["action"]["inputs"] = ["future"]
    events.insert(2, trace_event("logical.observation", {"produced_information": [{
        "artifact_id": "future", "media_type": "text/plain", "size_bytes": 100,
    }]}))
    result = extract_cost_history(events, run_id="test-run", network_category="fast")
    assert result.models[0].conservative_input_tokens is None


def test_duplicate_or_mixed_run_receipts_are_rejected() -> None:
    events = history_events()
    with pytest.raises(ValueError, match="duplicate physical"):
        extract_cost_history(events + [events[2]], run_id="test-run", network_category="fast")
    with pytest.raises(ValueError, match="mixed run"):
        extract_cost_history(json.loads(json.dumps(events)), run_id="different",
                             network_category="fast")
