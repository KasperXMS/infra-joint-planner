"""Freeze and execute the v1 pilot or formal randomized run schedule."""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
from argparse import Namespace
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infra_joint.heterogeneous.analysis import validate_trace_reconstruction
from scripts.heterogeneous_experiment_v1 import run_one


@dataclass(frozen=True, slots=True)
class ScheduledRun:
    phase: Literal["pilot", "formal"]
    run_id: str
    condition_label: str
    bandwidth_mbps: float
    calibration: str
    payload: Literal["S", "M", "L"]
    policy: Literal["b0", "b1", "forced-a28", "forced-rtx"]
    repetition: int
    stage_estimates: str | None


def _calibrations(root: Path, bandwidths: tuple[int, ...]) -> dict[int, Path]:
    values = {
        bandwidth: root / f"netcal-bw{bandwidth}-rtt20-v1-audit1.json"
        for bandwidth in bandwidths
    }
    missing = [str(path) for path in values.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"network calibration files are missing: {missing}")
    return values


def pilot_schedule(
    calibration_root: Path,
    *,
    repetitions: int,
    seed: int,
) -> tuple[ScheduledRun, ...]:
    if repetitions < 3:
        raise ValueError("crossover pilot requires at least 3 repetitions")
    bandwidths = (3, 10, 30, 100, 300, 1000)
    calibrations = _calibrations(calibration_root, bandwidths)
    runs = [
        ScheduledRun(
            phase="pilot",
            run_id=(
                f"hetero-v1-pilot-bw{bandwidth}-{payload.lower()}-{policy}-r{repetition:02d}"
            ),
            condition_label=f"pilot-bw{bandwidth}",
            bandwidth_mbps=float(bandwidth),
            calibration=str(calibrations[bandwidth]),
            payload=payload,
            policy=policy,
            repetition=repetition,
            stage_estimates=None,
        )
        for bandwidth in bandwidths
        for payload in ("S", "M", "L")
        for policy in ("forced-a28", "forced-rtx")
        for repetition in range(1, repetitions + 1)
    ]
    random.Random(seed).shuffle(runs)
    return tuple(runs)


def formal_schedule(
    regime_path: Path,
    stage_estimates_root: Path,
    *,
    repetitions: int,
    seed: int,
) -> tuple[ScheduledRun, ...]:
    if repetitions < 10:
        raise ValueError("formal matrix requires at least 10 repetitions")
    loaded: object = json.loads(regime_path.read_text(encoding="utf-8"))
    expected = {"H_low", "H_mid", "H_high"}
    if not isinstance(loaded, dict):
        raise ValueError("formal regimes must exactly define H_low/H_mid/H_high")
    regimes = cast(dict[str, object], loaded)
    if set(regimes) != expected:
        raise ValueError("formal regimes must exactly define H_low/H_mid/H_high")
    runs: list[ScheduledRun] = []
    for condition in ("H_low", "H_mid", "H_high"):
        raw_value = regimes[condition]
        if not isinstance(raw_value, dict):
            raise ValueError(f"formal regime must be an object: {condition}")
        raw = cast(dict[str, object], raw_value)
        bandwidth_value = raw.get("bandwidth_mbps")
        calibration_value = raw.get("calibration")
        if not isinstance(bandwidth_value, (int, float)) or bandwidth_value <= 0:
            raise ValueError(f"formal regime has invalid bandwidth: {condition}")
        if not isinstance(calibration_value, str) or not calibration_value:
            raise ValueError(f"formal regime has invalid calibration: {condition}")
        bandwidth = float(bandwidth_value)
        calibration = calibration_value
        for payload in ("S", "M", "L"):
            estimates = stage_estimates_root / f"stage-estimates-{payload}.json"
            if not estimates.is_file():
                raise FileNotFoundError(estimates)
            for policy in ("b0", "b1", "forced-a28", "forced-rtx"):
                for repetition in range(1, repetitions + 1):
                    runs.append(
                        ScheduledRun(
                            phase="formal",
                            run_id=(
                                f"hetero-v1-formal-{condition.lower()}-{payload.lower()}-"
                                f"{policy}-r{repetition:02d}"
                            ),
                            condition_label=condition,
                            bandwidth_mbps=bandwidth,
                            calibration=calibration,
                            payload=payload,
                            policy=policy,
                            repetition=repetition,
                            stage_estimates=str(estimates) if policy == "b1" else None,
                        )
                    )
    random.Random(seed).shuffle(runs)
    return tuple(runs)


def replace_run_ids(
    schedule: tuple[ScheduledRun, ...], replacements: dict[str, str]
) -> tuple[ScheduledRun, ...]:
    if not replacements:
        return schedule
    existing = {item.run_id for item in schedule}
    missing = set(replacements) - existing
    if missing:
        raise ValueError(f"replacement source run IDs are absent: {sorted(missing)}")
    targets = tuple(replacements.values())
    if any(not item for item in targets) or len(set(targets)) != len(targets):
        raise ValueError("replacement run IDs must be non-empty and unique")
    if set(targets) & (existing - set(replacements)):
        raise ValueError("replacement run ID collides with an existing schedule run")
    return tuple(
        replace(item, run_id=replacements.get(item.run_id, item.run_id))
        for item in schedule
    )


def _write_schedule(
    path: Path,
    schedule: tuple[ScheduledRun, ...],
    seed: int,
    replacements: dict[str, str],
) -> None:
    payload: dict[str, object] = {
        "schema_version": "heterogeneous-v1-run-schedule-v1",
        "seed": seed,
        "run_count": len(schedule),
        "runs": [asdict(item) for item in schedule],
    }
    if replacements:
        payload["replacement_run_ids"] = replacements
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != serialized:
        raise RuntimeError("refusing to change an already frozen run schedule")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized, encoding="utf-8")


def existing_run_is_valid(result_path: Path, metadata_path: Path) -> bool:
    """Accept only a fully persisted, explicitly valid prior run.

    A partial or invalid run must stop a resumed matrix.  It must never be
    silently retried under the same run ID or skipped as if it were valid.
    """

    run_root = result_path.parent
    failure_marker_path = run_root / "matrix-failure.json"
    trace_path = run_root / "trace.jsonl"
    if failure_marker_path.exists():
        raise RuntimeError(
            f"refusing to resume matrix-failed run: {result_path.parent.name}; "
            "use an explicit replacement run ID and a new schedule"
        )
    present = (result_path.is_file(), metadata_path.is_file(), trace_path.is_file())
    if present == (False, False, False):
        return False
    if present != (True, True, True):
        raise RuntimeError(
            f"refusing to resume partial run: {result_path.parent.name}"
        )
    loaded_result: object = json.loads(result_path.read_text(encoding="utf-8"))
    loaded_metadata: object = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(loaded_result, dict) or not isinstance(loaded_metadata, dict):
        raise RuntimeError(f"invalid persisted run documents: {result_path.parent.name}")
    result = cast(dict[str, object], loaded_result)
    metadata = cast(dict[str, object], loaded_metadata)
    if result.get("execution_completed") is not True or result.get("failure") is not None:
        raise RuntimeError(f"refusing to resume after failed run: {result_path.parent.name}")
    if metadata.get("validation_error") is not None:
        raise RuntimeError(f"refusing to resume after invalid run: {result_path.parent.name}")
    if metadata.get("tc_cleanup_error") is not None:
        raise RuntimeError(
            f"refusing to resume after tc cleanup failure: {result_path.parent.name}"
        )
    if metadata.get("artifact_cleanup_error") is not None:
        raise RuntimeError(
            f"refusing to resume after artifact cleanup failure: "
            f"{result_path.parent.name}"
        )
    try:
        validate_trace_reconstruction(trace_path, result_path.parent.name)
    except (OSError, ValueError) as exc:
        raise RuntimeError(
            f"refusing to resume unreconstructable trace: {result_path.parent.name}: "
            f"{exc}"
        ) from exc
    return True


def _persist_matrix_failure(
    output_root: Path,
    item: ScheduledRun,
    schedule_index: int,
    exc: Exception,
) -> Path:
    """Atomically retain a run-level tombstone for failures before sidecar creation."""

    run_root = output_root / item.run_id
    run_root.mkdir(parents=True, exist_ok=True)
    path = run_root / "matrix-failure.json"
    temporary = path.with_suffix(".json.tmp")
    payload = {
        "schema_version": "heterogeneous-v1-matrix-failure-v1",
        "run_id": item.run_id,
        "schedule_index": schedule_index,
        "recorded_at": datetime.now(UTC).isoformat(),
        "exception_type": type(exc).__name__,
        "exception_message": str(exc),
        "resume_policy": "explicit-replacement-run-id-and-new-schedule-required",
    }
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)
    return path


async def execute(args: argparse.Namespace, schedule: tuple[ScheduledRun, ...]) -> None:
    progress_path = args.schedule.with_name(f"{args.schedule.stem}-progress.json")
    completed: list[str] = []
    for index, item in enumerate(schedule):
        result_path = args.output_root / item.run_id / "result.json"
        metadata_path = args.output_root / item.run_id / "experiment-metadata.json"
        if existing_run_is_valid(result_path, metadata_path):
            completed.append(item.run_id)
            continue
        invocation = Namespace(
            manifest=args.manifest,
            payload=item.payload,
            policy=item.policy,
            run_id=item.run_id,
            bandwidth_mbps=item.bandwidth_mbps,
            calibration=Path(item.calibration),
            compute_profile_id=args.compute_profile_id,
            stage_estimates=(Path(item.stage_estimates) if item.stage_estimates else None),
            preflight_config=args.preflight_config,
            tc_config=args.tc_config,
            planner_config=args.planner_config,
            api_key_file=args.api_key_file,
            output_root=args.output_root,
        )
        try:
            await run_one(invocation)
        except Exception as exc:
            _persist_matrix_failure(args.output_root, item, index, exc)
            raise
        completed.append(item.run_id)
        progress_path.write_text(
            json.dumps(
                {
                    "completed": completed,
                    "completed_count": len(completed),
                    "next_schedule_index": index + 1,
                    "total": len(schedule),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("pilot", "formal"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--calibration-root", type=Path, required=True)
    parser.add_argument("--regimes", type=Path)
    parser.add_argument("--stage-estimates-root", type=Path)
    parser.add_argument("--repetitions", type=int, required=True)
    parser.add_argument("--seed", type=int, default=20260922)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--compute-profile-id", required=True)
    parser.add_argument("--preflight-config", type=Path, required=True)
    parser.add_argument("--tc-config", type=Path, required=True)
    parser.add_argument("--planner-config", type=Path, required=True)
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--replacement",
        action="append",
        default=[],
        metavar="OLD_RUN_ID=NEW_RUN_ID",
    )
    return parser


def _parse_replacements(values: list[str]) -> dict[str, str]:
    replacements: dict[str, str] = {}
    for value in values:
        old, separator, new = value.partition("=")
        if not separator or not old or not new:
            raise ValueError("replacement must be OLD_RUN_ID=NEW_RUN_ID")
        if old in replacements:
            raise ValueError(f"duplicate replacement source run ID: {old}")
        replacements[old] = new
    return replacements


def main() -> None:
    args = _parser().parse_args()
    replacements = _parse_replacements(args.replacement)
    if args.mode == "pilot":
        schedule = pilot_schedule(
            args.calibration_root,
            repetitions=args.repetitions,
            seed=args.seed,
        )
    else:
        if args.regimes is None or args.stage_estimates_root is None:
            raise ValueError("formal mode requires --regimes and --stage-estimates-root")
        schedule = formal_schedule(
            args.regimes,
            args.stage_estimates_root,
            repetitions=args.repetitions,
            seed=args.seed,
        )
    schedule = replace_run_ids(schedule, replacements)
    _write_schedule(args.schedule, schedule, args.seed, replacements)
    asyncio.run(execute(args, schedule))


if __name__ == "__main__":
    main()
