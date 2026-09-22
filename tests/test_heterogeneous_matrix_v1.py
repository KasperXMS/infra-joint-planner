import json
from pathlib import Path

import pytest

from scripts.heterogeneous_matrix_v1 import formal_schedule, pilot_schedule


def write_calibrations(root: Path) -> None:
    root.mkdir()
    for bandwidth in (3, 10, 30, 100, 300, 1000):
        (root / f"netcal-bw{bandwidth}-rtt20-v1.json").write_text("{}")


def test_pilot_schedule_is_frozen_randomized_and_complete(tmp_path: Path) -> None:
    root = tmp_path / "calibrations"
    write_calibrations(root)

    first = pilot_schedule(root, repetitions=3, seed=42)
    second = pilot_schedule(root, repetitions=3, seed=42)

    assert first == second
    assert len(first) == 6 * 3 * 2 * 3
    assert len({item.run_id for item in first}) == len(first)
    assert {item.policy for item in first} == {"forced-a28", "forced-rtx"}


def test_formal_schedule_has_180_scheduler_and_180_oracle_runs(tmp_path: Path) -> None:
    regimes = tmp_path / "regimes.json"
    regimes.write_text(
        json.dumps(
            {
                name: {
                    "bandwidth_mbps": bandwidth,
                    "calibration": f"netcal-{bandwidth}.json",
                }
                for name, bandwidth in (
                    ("H_low", 3),
                    ("H_mid", 30),
                    ("H_high", 100),
                )
            }
        )
    )
    estimates = tmp_path / "estimates"
    estimates.mkdir()
    for payload in ("S", "M", "L"):
        (estimates / f"stage-estimates-{payload}.json").write_text("[]")

    schedule = formal_schedule(regimes, estimates, repetitions=10, seed=7)

    assert len(schedule) == 360
    assert sum(item.policy in {"b0", "b1"} for item in schedule) == 180
    assert sum(item.policy.startswith("forced-") for item in schedule) == 180
    assert len({item.run_id for item in schedule}) == 360


def test_formal_and_pilot_repetition_floors_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "calibrations"
    write_calibrations(root)
    with pytest.raises(ValueError, match="at least 3"):
        pilot_schedule(root, repetitions=2, seed=1)

    with pytest.raises(ValueError, match="at least 10"):
        formal_schedule(tmp_path / "missing.json", tmp_path, repetitions=9, seed=1)
