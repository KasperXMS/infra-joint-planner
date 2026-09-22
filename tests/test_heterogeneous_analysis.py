import pytest

from infra_joint.heterogeneous.analysis import (
    PlacementRunObservation,
    build_stage_estimates,
    oracle_cells,
    predicted_break_even_mbps,
    routing_regrets,
)


def observation(
    run_id: str,
    policy: str,
    agent: str,
    cost: float,
    *,
    calibration: str = "netcal",
) -> PlacementRunObservation:
    return PlacementRunObservation(
        run_id=run_id,
        payload_class="S",
        placement_policy=policy,
        network_calibration_id=calibration,
        selected_agent_id=agent,
        stage_cost_ms=cost,
        stage_compute_ms=cost - 10,
        stage_transfer_bytes=0,
        stage_transfer_ms=0,
        model_service_ms=cost - 20,
        workflow_e2e_ms=cost + 100,
        critical_path_ms=cost,
        scheduler_overhead_ms=0.1,
        benchmark_score=1,
        format_valid=True,
    )


def test_stage_estimates_use_repeated_forced_compute_measurements() -> None:
    values = tuple(
        observation(f"a-{index}", "forced-a28", "A28", cost)
        for index, cost in enumerate((100, 110, 120), start=1)
    ) + tuple(
        observation(f"g-{index}", "forced-rtx", "strong-4090", cost)
        for index, cost in enumerate((30, 40, 50), start=1)
    )

    estimates = build_stage_estimates(values, "S", profile_id="pilot-S")

    assert estimates[0].median_reduction_latency_ms == 10
    assert estimates[0].median_model_service_latency_ms == 90
    assert estimates[1].median_model_service_latency_ms == 20


def test_oracle_and_regret_use_forced_cell_medians() -> None:
    forced = tuple(
        observation(f"a-{index}", "forced-a28", "A28", cost)
        for index, cost in enumerate((100, 110, 120), start=1)
    ) + tuple(
        observation(f"g-{index}", "forced-rtx", "strong-4090", cost)
        for index, cost in enumerate((40, 50, 60), start=1)
    )
    schedulers = (
        observation("b0", "b0", "A28", 105),
        observation("b1", "b1", "strong-4090", 55),
    )

    cells = oracle_cells(forced)
    regrets = routing_regrets(schedulers, cells)

    assert cells[0].oracle_agent_id == "strong-4090"
    assert regrets[0].routing_regret_ms == 60
    assert not regrets[0].oracle_selected
    assert regrets[1].routing_regret_ms == 0
    assert regrets[1].oracle_selected


def test_break_even_uses_bytes_compute_gap_and_rtt() -> None:
    value = predicted_break_even_mbps(
        8 * 1024 * 1024,
        a28_compute_ms=5000,
        rtx_compute_ms=500,
        rtt_ms=20,
    )
    assert value == pytest.approx(14.979, rel=1e-3)
    assert predicted_break_even_mbps(1, 500, 500, 20) is None
