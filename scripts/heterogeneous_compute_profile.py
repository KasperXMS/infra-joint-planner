"""Collect a formal heterogeneous-v1 compute profile over SSH.

The command is intentionally single-replica and fail-fast. It uses the frozen
four-point matrix, deterministic non-thinking generation, and preserves every
measured Ollama sample alongside the summarized ``ComputeProfile`` contract.
"""

import argparse
import asyncio
import hashlib
import json
import os
import shlex
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from time import perf_counter
from typing import Protocol, Self

from pydantic import Field, model_validator

from infra_joint.core.base import ContractModel
from infra_joint.heterogeneous.contracts import ComputeProfile, ComputeProfilePoint
from infra_joint.heterogeneous.profiling import ModelProfileSample, SshOllamaProfiler

PROFILE_POINTS: tuple[tuple[int, int], ...] = (
    (1024, 128),
    (2048, 128),
    (4096, 256),
    (8192, 256),
)
PROFILE_CONTEXT_WINDOW = 16_384
MIN_WARMUP_RUNS = 10
MIN_MEASURED_RUNS = 30
PROMPT_TEMPLATE_ID = "heterogeneous-compute-profile-direct-v1"
GENERATION_CONFIG_ID = "ollama-deterministic-nonthinking-v1"


class DeviceKind(StrEnum):
    AGX = "agx"
    RTX = "rtx"


class ProfileRunConfig(ContractModel):
    ssh_target: str = Field(min_length=1)
    model: str = Field(min_length=1)
    replica_id: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    device_kind: DeviceKind
    base_url: str = Field(min_length=1)
    context_window: int = Field(gt=0)
    warmup_runs: int = Field(ge=MIN_WARMUP_RUNS)
    measured_runs: int = Field(ge=MIN_MEASURED_RUNS)

    @model_validator(mode="after")
    def context_fits_largest_point(self) -> Self:
        largest_request = max(
            input_tokens + output_tokens for input_tokens, output_tokens in PROFILE_POINTS
        )
        if self.context_window < largest_request:
            raise ValueError(
                f"context window must be >= {largest_request} for the frozen profile matrix"
            )
        return self


class TelemetryCommand(ContractModel):
    name: str = Field(min_length=1)
    argv: tuple[str, ...] = Field(min_length=1)


class TelemetryCommandResult(ContractModel):
    name: str = Field(min_length=1)
    command: str = Field(min_length=1)
    return_code: int
    duration_ms: float = Field(ge=0)
    stdout: str
    stderr: str


class DeviceTelemetrySnapshot(ContractModel):
    captured_at_utc: datetime
    device_kind: DeviceKind
    commands: tuple[TelemetryCommandResult, ...] = Field(min_length=1)


class RawProfilePoint(ContractModel):
    input_tokens: int = Field(gt=0)
    requested_output_tokens: int = Field(gt=0)
    context_window: int = Field(gt=0)
    prompt_template_id: str = Field(min_length=1)
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt: str = Field(min_length=1)
    samples: tuple[ModelProfileSample, ...] = Field(min_length=MIN_MEASURED_RUNS)


class ComputeProfileRecord(ContractModel):
    schema_version: str = Field(pattern=r"^heterogeneous-compute-profile-v1$")
    started_at_utc: datetime
    finished_at_utc: datetime
    ssh_target: str = Field(min_length=1)
    model: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    prompt_template_id: str = Field(min_length=1)
    generation_config_id: str = Field(min_length=1)
    context_window: int = Field(gt=0)
    warmup_runs: int = Field(ge=MIN_WARMUP_RUNS)
    measured_runs: int = Field(ge=MIN_MEASURED_RUNS)
    telemetry_before: DeviceTelemetrySnapshot
    telemetry_after: DeviceTelemetrySnapshot
    raw_points: tuple[RawProfilePoint, ...] = Field(min_length=len(PROFILE_POINTS))
    compute_profile: ComputeProfile

    @model_validator(mode="after")
    def matches_frozen_matrix(self) -> Self:
        observed = tuple(
            (point.input_tokens, point.requested_output_tokens) for point in self.raw_points
        )
        if observed != PROFILE_POINTS:
            raise ValueError("raw profile points do not match the frozen matrix")
        if any(len(point.samples) != self.measured_runs for point in self.raw_points):
            raise ValueError("raw profile sample count does not match measured_runs")
        summarized = tuple(
            (point.input_tokens, point.requested_output_tokens)
            for point in self.compute_profile.points
        )
        if summarized != PROFILE_POINTS:
            raise ValueError("raw samples and compute profile point identities disagree")
        if any(
            point.warmup_runs != self.warmup_runs
            or point.measured_runs != self.measured_runs
            for point in self.compute_profile.points
        ):
            raise ValueError("compute profile repetition counts disagree with the run record")
        if self.telemetry_before.device_kind != self.telemetry_after.device_kind:
            raise ValueError("before/after telemetry device kinds disagree")
        return self


class PointProfiler(Protocol):
    async def profile_point(
        self,
        model: str,
        prompt: str,
        *,
        requested_input_tokens: int,
        requested_output_tokens: int,
        context_window: int,
        warmup_runs: int = MIN_WARMUP_RUNS,
        measured_runs: int = MIN_MEASURED_RUNS,
    ) -> tuple[ComputeProfilePoint, tuple[ModelProfileSample, ...]]: ...


class TelemetryCollector(Protocol):
    async def capture(
        self, ssh_target: str, device_kind: DeviceKind
    ) -> DeviceTelemetrySnapshot: ...


class SshTelemetryCollector:
    async def capture(
        self, ssh_target: str, device_kind: DeviceKind
    ) -> DeviceTelemetrySnapshot:
        results = tuple(
            [
                await self._run(ssh_target, command)
                for command in telemetry_commands(device_kind)
            ]
        )
        return DeviceTelemetrySnapshot(
            captured_at_utc=datetime.now(UTC),
            device_kind=device_kind,
            commands=results,
        )

    async def _run(
        self, ssh_target: str, command: TelemetryCommand
    ) -> TelemetryCommandResult:
        remote_command = shlex.join(command.argv)
        started = perf_counter()
        process = await asyncio.create_subprocess_exec(
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            ssh_target,
            remote_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return TelemetryCommandResult(
            name=command.name,
            command=remote_command,
            return_code=process.returncode or 0,
            duration_ms=(perf_counter() - started) * 1000,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
        )


def telemetry_commands(device_kind: DeviceKind) -> tuple[TelemetryCommand, ...]:
    if device_kind == DeviceKind.AGX:
        return (
            TelemetryCommand(
                name="tegrastats",
                argv=("timeout", "--signal=INT", "3s", "tegrastats", "--interval", "1000"),
            ),
            TelemetryCommand(name="nvpmodel", argv=("nvpmodel", "-q")),
            TelemetryCommand(name="jetson_clocks", argv=("jetson_clocks", "--show")),
        )
    if device_kind == DeviceKind.RTX:
        return (
            TelemetryCommand(
                name="nvidia_smi",
                argv=(
                    "nvidia-smi",
                    "--query-gpu=timestamp,index,name,uuid,temperature.gpu,utilization.gpu,"
                    "utilization.memory,memory.total,memory.used,memory.free,power.draw,"
                    "power.limit,clocks.current.sm,clocks.current.memory",
                    "--format=csv,noheader,nounits",
                ),
            ),
        )
    raise AssertionError(f"unhandled device kind: {device_kind}")


def build_profile_prompt(input_tokens: int, output_tokens: int) -> str:
    """Build a stable whitespace-token-budgeted prompt without hidden reasoning."""

    prefix = (
        "Deterministic inference throughput measurement. Respond directly without analysis "
        "or reasoning. Emit only the word profile separated by spaces until the configured "
        f"generation limit of {output_tokens} tokens stops you. Input payload follows."
    )
    prefix_tokens = prefix.split()
    if input_tokens <= len(prefix_tokens):
        raise ValueError("input token target is too small for the frozen prompt template")
    padding = ("profile",) * (input_tokens - len(prefix_tokens))
    return " ".join((*prefix_tokens, *padding))


async def collect_profile(
    config: ProfileRunConfig,
    *,
    profiler: PointProfiler | None = None,
    telemetry: TelemetryCollector | None = None,
) -> ComputeProfileRecord:
    active_profiler = profiler or SshOllamaProfiler(
        config.ssh_target,
        base_url=config.base_url,
    )
    active_telemetry = telemetry or SshTelemetryCollector()
    started_at = datetime.now(UTC)
    telemetry_before = await active_telemetry.capture(config.ssh_target, config.device_kind)
    summarized_points: list[ComputeProfilePoint] = []
    raw_points: list[RawProfilePoint] = []
    try:
        for input_tokens, output_tokens in PROFILE_POINTS:
            prompt = build_profile_prompt(input_tokens, output_tokens)
            point, samples = await active_profiler.profile_point(
                config.model,
                prompt,
                requested_input_tokens=input_tokens,
                requested_output_tokens=output_tokens,
                context_window=config.context_window,
                warmup_runs=config.warmup_runs,
                measured_runs=config.measured_runs,
            )
            summarized_points.append(point)
            raw_points.append(
                RawProfilePoint(
                    input_tokens=input_tokens,
                    requested_output_tokens=output_tokens,
                    context_window=config.context_window,
                    prompt_template_id=PROMPT_TEMPLATE_ID,
                    prompt_sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                    prompt=prompt,
                    samples=samples,
                )
            )
    finally:
        telemetry_after = await active_telemetry.capture(config.ssh_target, config.device_kind)
    return ComputeProfileRecord(
        schema_version="heterogeneous-compute-profile-v1",
        started_at_utc=started_at,
        finished_at_utc=datetime.now(UTC),
        ssh_target=config.ssh_target,
        model=config.model,
        base_url=config.base_url,
        prompt_template_id=PROMPT_TEMPLATE_ID,
        generation_config_id=GENERATION_CONFIG_ID,
        context_window=config.context_window,
        warmup_runs=config.warmup_runs,
        measured_runs=config.measured_runs,
        telemetry_before=telemetry_before,
        telemetry_after=telemetry_after,
        raw_points=tuple(raw_points),
        compute_profile=ComputeProfile(
            profile_id=config.profile_id,
            replica_id=config.replica_id,
            points=tuple(summarized_points),
        ),
    )


def write_atomic_json(output: Path, record: ComputeProfileRecord) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(record.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(output)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-target", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--replica-id", required=True)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--device-kind", choices=tuple(DeviceKind), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:11435")
    parser.add_argument("--context-window", type=int, default=PROFILE_CONTEXT_WINDOW)
    parser.add_argument("--warmup-runs", type=int, default=MIN_WARMUP_RUNS)
    parser.add_argument("--measured-runs", type=int, default=MIN_MEASURED_RUNS)
    return parser


async def _run(args: argparse.Namespace) -> None:
    config = ProfileRunConfig(
        ssh_target=args.ssh_target,
        model=args.model,
        replica_id=args.replica_id,
        profile_id=args.profile_id,
        device_kind=DeviceKind(args.device_kind),
        base_url=args.base_url,
        context_window=args.context_window,
        warmup_runs=args.warmup_runs,
        measured_runs=args.measured_runs,
    )
    record = await collect_profile(config)
    write_atomic_json(args.output, record)
    print(args.output)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
