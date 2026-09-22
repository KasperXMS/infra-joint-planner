import asyncio
import json
import subprocess
import sys
from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path

import pytest

import scripts.heterogeneous_matrix_v1 as matrix_module
from infra_joint.evaluation.trace import TraceEvent
from scripts.heterogeneous_matrix_v1 import (
    ScheduledRun,
    execute,
    existing_run_is_valid,
    formal_schedule,
    pilot_schedule,
    replace_run_ids,
)


def write_valid_trace(path: Path, run_id: str) -> None:
    previous: str | None = None
    events: list[TraceEvent] = []
    for index, event_type in enumerate(
        ("task.start", "workflow.planner.end", "infra.snapshot", "run.end")
    ):
        step_id = f"{index:06d}-{event_type}"
        events.append(
            TraceEvent(
                run_id=run_id,
                step_id=step_id,
                parent_id=previous,
                event_type=event_type,
                timestamp=datetime.now(UTC),
            )
        )
        previous = step_id
    path.write_text("\n".join(item.model_dump_json() for item in events) + "\n")


def write_calibrations(root: Path) -> None:
    root.mkdir()
    for bandwidth in (3, 10, 30, 100, 300, 1000):
        (root / f"netcal-bw{bandwidth}-rtt20-v1-audit1.json").write_text("{}")


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


def test_matrix_resume_only_accepts_complete_valid_run(tmp_path: Path) -> None:
    result = tmp_path / "run" / "result.json"
    metadata = result.with_name("experiment-metadata.json")
    result.parent.mkdir()

    assert not existing_run_is_valid(result, metadata)

    result.write_text(json.dumps({"execution_completed": True, "failure": None}))
    with pytest.raises(RuntimeError, match="partial run"):
        existing_run_is_valid(result, metadata)
    trace = result.with_name("trace.jsonl")
    write_valid_trace(trace, "run")

    metadata.write_text(
        json.dumps({"validation_error": "bad finish", "tc_cleanup_error": None})
    )
    with pytest.raises(RuntimeError, match="invalid run"):
        existing_run_is_valid(result, metadata)

    metadata.write_text(
        json.dumps(
            {
                "validation_error": None,
                "tc_cleanup_error": None,
                "artifact_cleanup_error": None,
            }
        )
    )
    trace.unlink()
    with pytest.raises(RuntimeError, match="partial run"):
        existing_run_is_valid(result, metadata)

    write_valid_trace(trace, "run")
    assert existing_run_is_valid(result, metadata)

    trace.write_text("{}\n")
    with pytest.raises(RuntimeError, match="unreconstructable trace"):
        existing_run_is_valid(result, metadata)
    write_valid_trace(trace, "run")

    metadata.write_text(
        json.dumps(
            {
                "validation_error": None,
                "tc_cleanup_error": None,
                "artifact_cleanup_error": "ssh timeout",
            }
        )
    )
    with pytest.raises(RuntimeError, match="artifact cleanup failure"):
        existing_run_is_valid(result, metadata)


def test_matrix_persists_early_failure_marker_and_refuses_same_id_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = ScheduledRun(
        phase="pilot",
        run_id="early-failure",
        condition_label="pilot-bw3",
        bandwidth_mbps=3,
        calibration="calibration.json",
        payload="S",
        policy="forced-a28",
        repetition=1,
        stage_estimates=None,
    )

    async def fail_before_output(_: Namespace) -> None:
        raise RuntimeError("preflight failed")

    monkeypatch.setattr(matrix_module, "run_one", fail_before_output)
    args = Namespace(
        schedule=tmp_path / "schedule.json",
        output_root=tmp_path / "runs",
        manifest=tmp_path / "manifest.json",
        compute_profile_id="profile",
        preflight_config=tmp_path / "preflight.json",
        tc_config=tmp_path / "tc.json",
        planner_config=tmp_path / "planner.yaml",
        api_key_file=None,
    )

    with pytest.raises(RuntimeError, match="preflight failed"):
        asyncio.run(execute(args, (run,)))

    marker = args.output_root / run.run_id / "matrix-failure.json"
    saved = json.loads(marker.read_text())
    assert saved["exception_type"] == "RuntimeError"
    assert saved["resume_policy"].startswith("explicit-replacement")
    with pytest.raises(RuntimeError, match="explicit replacement run ID"):
        existing_run_is_valid(
            marker.with_name("result.json"),
            marker.with_name("experiment-metadata.json"),
        )


def test_matrix_script_entrypoint_exposes_help() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/heterogeneous_matrix_v1.py", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "pilot" in result.stdout
    assert "formal" in result.stdout


def test_replacement_run_id_is_explicit_and_collision_safe(tmp_path: Path) -> None:
    root = tmp_path / "calibrations"
    write_calibrations(root)
    schedule = pilot_schedule(root, repetitions=3, seed=42)
    old = schedule[0].run_id
    replacement = f"{old}-replacement-audit1"

    updated = replace_run_ids(schedule, {old: replacement})

    assert updated[0].run_id == replacement
    assert updated[1:] == schedule[1:]
    with pytest.raises(ValueError, match="collides"):
        replace_run_ids(schedule, {old: schedule[1].run_id})
