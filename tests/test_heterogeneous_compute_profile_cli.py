import importlib.util
import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from infra_joint.heterogeneous.profiling import (
    ModelProfileSample,
    profile_point_from_samples,
)

_SCRIPT = Path(__file__).parents[1] / "scripts" / "heterogeneous_compute_profile.py"
_SPEC = importlib.util.spec_from_file_location("heterogeneous_compute_profile", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

PROFILE_CONTEXT_WINDOW = _MODULE.PROFILE_CONTEXT_WINDOW
PROFILE_POINTS = _MODULE.PROFILE_POINTS
ComputeProfileRecord = _MODULE.ComputeProfileRecord
DeviceKind = _MODULE.DeviceKind
DeviceTelemetrySnapshot = _MODULE.DeviceTelemetrySnapshot
ProfileRunConfig = _MODULE.ProfileRunConfig
TelemetryCommandResult = _MODULE.TelemetryCommandResult
build_profile_prompt = _MODULE.build_profile_prompt
collect_profile = _MODULE.collect_profile
telemetry_commands = _MODULE.telemetry_commands
write_atomic_json = _MODULE.write_atomic_json


def _sample(input_tokens: int, output_tokens: int, value: float) -> ModelProfileSample:
    return ModelProfileSample(
        wall_service_ms=value,
        ttft_ms=value / 2,
        prompt_tokens=input_tokens,
        output_tokens=output_tokens,
        prompt_eval_ms=value / 3,
        decode_ms=value / 4,
        output_tokens_per_second=50,
        load_ms=1,
        total_runtime_ms=value,
        done_reason="length",
    )


class FakeProfiler:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, int, int, int, int]] = []

    async def profile_point(
        self,
        model: str,
        prompt: str,
        *,
        requested_input_tokens: int,
        requested_output_tokens: int,
        context_window: int,
        warmup_runs: int = 10,
        measured_runs: int = 30,
    ) -> tuple[object, tuple[ModelProfileSample, ...]]:
        self.calls.append(
            (
                model,
                len(prompt.split()),
                requested_input_tokens,
                requested_output_tokens,
                warmup_runs,
                measured_runs,
            )
        )
        samples = tuple(
            _sample(requested_input_tokens, requested_output_tokens, float(index + 1))
            for index in range(measured_runs)
        )
        point = profile_point_from_samples(
            requested_input_tokens,
            requested_output_tokens,
            warmup_runs,
            samples,
        )
        assert context_window == PROFILE_CONTEXT_WINDOW
        return point, samples


class FakeTelemetry:
    def __init__(self) -> None:
        self.captures = 0

    async def capture(
        self, ssh_target: str, device_kind: DeviceKind
    ) -> DeviceTelemetrySnapshot:
        self.captures += 1
        assert ssh_target == "profile-host"
        return DeviceTelemetrySnapshot(
            captured_at_utc="2026-09-22T00:00:00Z",
            device_kind=device_kind,
            commands=(
                TelemetryCommandResult(
                    name="fake",
                    command="fake --read-only",
                    return_code=0,
                    duration_ms=1,
                    stdout=f"snapshot-{self.captures}",
                    stderr="",
                ),
            ),
        )


def _config(**overrides: object) -> ProfileRunConfig:
    values: dict[str, object] = {
        "ssh_target": "profile-host",
        "model": "equal-model",
        "replica_id": "replica-a28",
        "profile_id": "compute-a28-v1",
        "device_kind": DeviceKind.AGX,
        "base_url": "http://127.0.0.1:11435",
        "context_window": PROFILE_CONTEXT_WINDOW,
        "warmup_runs": 10,
        "measured_runs": 30,
    }
    values.update(overrides)
    return ProfileRunConfig.model_validate(values)


def test_prompt_is_deterministic_direct_and_whitespace_budgeted() -> None:
    first = build_profile_prompt(1024, 128)
    second = build_profile_prompt(1024, 128)

    assert first == second
    assert len(first.split()) == 1024
    assert "without analysis or reasoning" in first
    assert "configured generation limit of 128 tokens" in first


def test_formal_thresholds_and_largest_context_are_fail_closed() -> None:
    with pytest.raises(ValidationError, match="greater than or equal to 10"):
        _config(warmup_runs=9)
    with pytest.raises(ValidationError, match="greater than or equal to 30"):
        _config(measured_runs=29)
    with pytest.raises(ValidationError, match="context window must be"):
        _config(context_window=8192)


def test_device_kind_selects_read_only_telemetry_surface() -> None:
    agx = telemetry_commands(DeviceKind.AGX)
    rtx = telemetry_commands(DeviceKind.RTX)

    assert [item.name for item in agx] == ["tegrastats", "nvpmodel", "jetson_clocks"]
    assert agx[0].argv[0] == "timeout"
    assert [item.name for item in rtx] == ["nvidia_smi"]
    assert rtx[0].argv[0] == "nvidia-smi"


@pytest.mark.asyncio
async def test_collect_profile_preserves_matrix_samples_and_snapshots() -> None:
    profiler = FakeProfiler()
    telemetry = FakeTelemetry()

    record = await collect_profile(_config(), profiler=profiler, telemetry=telemetry)

    assert telemetry.captures == 2
    assert tuple(
        (point.input_tokens, point.requested_output_tokens) for point in record.raw_points
    ) == PROFILE_POINTS
    assert tuple(len(point.samples) for point in record.raw_points) == (30, 30, 30, 30)
    assert record.compute_profile.profile_id == "compute-a28-v1"
    assert record.compute_profile.replica_id == "replica-a28"
    assert [(call[1], call[2], call[3]) for call in profiler.calls] == [
        (input_tokens, input_tokens, output_tokens)
        for input_tokens, output_tokens in PROFILE_POINTS
    ]


@pytest.mark.asyncio
async def test_atomic_json_round_trips_complete_record(tmp_path: Path) -> None:
    record = await collect_profile(
        _config(),
        profiler=FakeProfiler(),
        telemetry=FakeTelemetry(),
    )
    output = tmp_path / "nested" / "profile.json"

    write_atomic_json(output, record)

    restored = ComputeProfileRecord.model_validate(json.loads(output.read_text("utf-8")))
    assert restored == record
    assert not tuple(output.parent.glob("*.tmp"))
