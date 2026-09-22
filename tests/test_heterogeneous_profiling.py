from infra_joint.heterogeneous.profiling import (
    ModelProfileSample,
    profile_point_from_samples,
)


def sample(value: float) -> ModelProfileSample:
    return ModelProfileSample(
        wall_service_ms=value,
        ttft_ms=value / 2,
        prompt_tokens=1000,
        output_tokens=128,
        prompt_eval_ms=value / 3,
        decode_ms=value / 4,
        output_tokens_per_second=50,
        load_ms=1,
        total_runtime_ms=value - 1,
        done_reason="length",
    )


def test_profile_point_preserves_repetition_contract_and_statistics() -> None:
    point = profile_point_from_samples(
        1000,
        128,
        10,
        tuple(sample(float(value)) for value in range(1, 31)),
    )

    assert point.warmup_runs == 10
    assert point.measured_runs == 30
    assert point.total_service_ms.median == 15.5
    assert point.actual_input_tokens.median == 1000
    assert point.actual_output_tokens.median == 128
