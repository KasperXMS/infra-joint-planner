from datetime import UTC, datetime
from math import isclose
from pathlib import Path

import pytest

from infra_joint.evaluation.trace import TraceEvent
from infra_joint.heterogeneous.analysis import (
    PlacementRunObservation,
    build_stage_estimates,
    oracle_cells,
    predicted_break_even_mbps,
    routing_regrets,
    validate_trace_reconstruction,
)
from scripts.heterogeneous_analyze_v1 import (
    load_observations,
    validate_formal_matrix,
)


def observation(
    run_id: str,
    policy: str,
    agent: str,
    cost: float,
    *,
    calibration: str = "netcal",
    payload: str = "S",
) -> PlacementRunObservation:
    return PlacementRunObservation(
        run_id=run_id,
        payload_class=payload,
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
    assert value is not None and isclose(value, 14.979, rel_tol=1e-3)
    assert predicted_break_even_mbps(1, 500, 500, 20) is None


def test_trace_reconstruction_requires_linear_chain_and_terminal_event(
    tmp_path: Path,
) -> None:
    path = tmp_path / "trace.jsonl"
    events = (
        TraceEvent(
            run_id="run",
            step_id="000000-task.start",
            event_type="task.start",
            timestamp=datetime.now(UTC),
        ),
        TraceEvent(
            run_id="run",
            step_id="000001-workflow.planner.end",
            parent_id="000000-task.start",
            event_type="workflow.planner.end",
            timestamp=datetime.now(UTC),
        ),
        TraceEvent(
            run_id="run",
            step_id="000002-infra.snapshot",
            parent_id="000001-workflow.planner.end",
            event_type="infra.snapshot",
            timestamp=datetime.now(UTC),
        ),
        TraceEvent(
            run_id="run",
            step_id="000003-run.end",
            parent_id="000002-infra.snapshot",
            event_type="run.end",
            timestamp=datetime.now(UTC),
        ),
    )
    path.write_text("\n".join(item.model_dump_json() for item in events) + "\n")

    assert validate_trace_reconstruction(path, "run") == 4

    broken = events[-1].model_copy(update={"parent_id": "wrong"})
    path.write_text(
        "\n".join(item.model_dump_json() for item in (*events[:-1], broken)) + "\n"
    )
    with pytest.raises(ValueError, match="parent chain"):
        validate_trace_reconstruction(path, "run")


def test_analyzer_rejects_artifact_cleanup_failure(tmp_path: Path) -> None:
    run_root = tmp_path / "failed-run"
    run_root.mkdir()
    (run_root / "experiment-metadata.json").write_text(
        '{"artifact_cleanup_error": "ssh timeout"}'
    )

    with pytest.raises(RuntimeError, match="artifact cleanup failure: failed-run"):
        load_observations(tmp_path)


def test_formal_audit_requires_exactly_36_cells_of_10() -> None:
    values = tuple(
        observation(
            f"{calibration}-{payload}-{policy}-{repetition}",
            policy,
            "A28" if policy in {"b0", "forced-a28"} else "strong-4090",
            100,
            calibration=calibration,
            payload=payload,
        )
        for calibration in ("low", "mid", "high")
        for payload in ("S", "M", "L")
        for policy in ("b0", "b1", "forced-a28", "forced-rtx")
        for repetition in range(10)
    )

    validate_formal_matrix(values)
    with pytest.raises(ValueError, match="exactly 360 valid runs"):
        validate_formal_matrix(values[:-1])

    duplicated = (*values[:-1], values[0])
    with pytest.raises(ValueError, match="duplicate run IDs"):
        validate_formal_matrix(duplicated)
