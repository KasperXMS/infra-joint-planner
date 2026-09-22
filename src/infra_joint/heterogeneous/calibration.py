import asyncio
import json
import re
from collections.abc import Sequence
from hashlib import sha256
from math import ceil
from statistics import fmean, median, pstdev
from time import perf_counter
from typing import Any

import httpx

from infra_joint.heterogeneous.contracts import (
    ArtifactTransferCalibration,
    DistributionSummary,
    NetworkCalibration,
    NetworkRegime,
)
from infra_joint.heterogeneous.traffic_control import RemoteCommandRunner

_PING_TIME = re.compile(r"time[=<]([0-9.]+)\s*ms")


def summarize(values: Sequence[float]) -> DistributionSummary:
    if not values:
        raise ValueError("distribution summary requires at least one value")
    ordered = sorted(values)
    return DistributionSummary(
        count=len(ordered),
        mean=fmean(ordered),
        median=median(ordered),
        std=pstdev(ordered),
        p90=_percentile(ordered, 90),
        p95=_percentile(ordered, 95),
    )


def parse_ping_latencies(output: str, *, warmup_samples: int = 0) -> tuple[float, ...]:
    values = tuple(float(match.group(1)) for match in _PING_TIME.finditer(output))
    if len(values) <= warmup_samples:
        raise ValueError("ping output contains too few measured replies")
    return values[warmup_samples:]


def parse_iperf_throughput_mbps(output: str) -> float:
    try:
        payload: Any = json.loads(output)
        bits_per_second = payload["end"]["sum_sent"]["bits_per_second"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError("iperf3 JSON lacks end.sum_sent.bits_per_second") from exc
    if not isinstance(bits_per_second, (int, float)) or bits_per_second <= 0:
        raise ValueError("iperf3 throughput must be positive")
    return float(bits_per_second) / 1_000_000


class NetworkCalibrator:
    def __init__(self, command_runner: RemoteCommandRunner) -> None:
        self._commands = command_runner

    async def measure_ping(
        self,
        source_ssh_target: str,
        target_address: str,
        *,
        warmup_samples: int = 5,
        measured_samples: int = 100,
    ) -> DistributionSummary:
        output = await self._commands.run(
            source_ssh_target,
            (
                "ping",
                "-n",
                "-c",
                str(warmup_samples + measured_samples),
                "-i",
                "0.05",
                target_address,
            ),
        )
        values = parse_ping_latencies(output, warmup_samples=warmup_samples)
        if len(values) != measured_samples:
            raise RuntimeError(
                f"ping calibration lost replies: expected={measured_samples}, got={len(values)}"
            )
        return summarize(values)

    async def measure_iperf(
        self,
        source_ssh_target: str,
        target_ssh_target: str,
        target_address: str,
        *,
        port: int = 5201,
        repetitions: int = 3,
        duration_seconds: int = 5,
    ) -> DistributionSummary:
        values: list[float] = []
        for _ in range(repetitions):
            server = asyncio.create_task(
                self._commands.run(
                    target_ssh_target,
                    (
                        "timeout",
                        str(duration_seconds + 15),
                        "iperf3",
                        "-s",
                        "-1",
                        "-p",
                        str(port),
                        "--json",
                    ),
                )
            )
            await asyncio.sleep(0.5)
            try:
                client = await self._commands.run(
                    source_ssh_target,
                    (
                        "iperf3",
                        "-c",
                        target_address,
                        "-p",
                        str(port),
                        "-t",
                        str(duration_seconds),
                        "--json",
                    ),
                )
                values.append(parse_iperf_throughput_mbps(client))
                await server
            except BaseException:
                server.cancel()
                await asyncio.gather(server, return_exceptions=True)
                raise
        return summarize(values)

    async def measure_artifact_transfers(
        self,
        source_agent_id: str,
        target_agent_id: str,
        source_url: str,
        target_url: str,
        sizes: Sequence[int],
        *,
        calibration_id: str,
        repetitions: int = 3,
        timeout_seconds: float = 900,
    ) -> tuple[ArtifactTransferCalibration, ...]:
        if repetitions < 1:
            raise ValueError("artifact calibration repetitions must be positive")
        results: list[ArtifactTransferCalibration] = []
        async with (
            httpx.AsyncClient(base_url=source_url, timeout=timeout_seconds) as source,
            httpx.AsyncClient(base_url=target_url, timeout=timeout_seconds) as target,
        ):
            source_state = await source.get("/state")
            target_state = await target.get("/state")
            source_state.raise_for_status()
            target_state.raise_for_status()
            if source_state.json().get("agent_id") != source_agent_id:
                raise RuntimeError("artifact calibration source Worker identity mismatch")
            if target_state.json().get("agent_id") != target_agent_id:
                raise RuntimeError("artifact calibration target Worker identity mismatch")
            for size in sizes:
                if size < 1:
                    raise ValueError("artifact calibration sizes must be positive")
                content = _calibration_payload(size)
                digest = sha256(content).hexdigest()
                artifact_id = f"{calibration_id}--{size}-bytes"
                put = await source.put(
                    f"/artifact/{artifact_id}",
                    content=content,
                    headers={"content-type": "application/octet-stream"},
                )
                put.raise_for_status()
                durations: list[float] = []
                throughputs: list[float] = []
                for _ in range(repetitions):
                    started = perf_counter()
                    pulled = await target.post(
                        "/artifact/pull",
                        json={
                            "artifact_id": artifact_id,
                            "source_url": f"{source_url}/artifact/{artifact_id}",
                            "expected_sha256": digest,
                        },
                    )
                    duration_ms = (perf_counter() - started) * 1000
                    pulled.raise_for_status()
                    response = pulled.json()
                    if (
                        response.get("size_bytes") != size
                        or response.get("sha256_hex") != digest
                    ):
                        raise RuntimeError("artifact calibration transfer integrity mismatch")
                    durations.append(duration_ms)
                    throughputs.append(size * 8 / (duration_ms * 1000))
                results.append(
                    ArtifactTransferCalibration(
                        source_agent_id=source_agent_id,
                        target_agent_id=target_agent_id,
                        artifact_bytes=size,
                        duration_ms=summarize(durations),
                        effective_throughput_mbps=summarize(throughputs),
                    )
                )
        return tuple(results)


def build_network_calibration(
    calibration_id: str,
    regime: NetworkRegime,
    source_agent_id: str,
    target_agent_id: str,
    rtt: DistributionSummary,
    throughput: DistributionSummary,
    artifacts: tuple[ArtifactTransferCalibration, ...],
) -> NetworkCalibration:
    return NetworkCalibration(
        calibration_id=calibration_id,
        regime=regime,
        source_agent_id=source_agent_id,
        target_agent_id=target_agent_id,
        median_rtt_ms=rtt.median,
        p95_rtt_ms=rtt.p95,
        achieved_throughput_mbps=throughput,
        artifact_transfers=artifacts,
    )


def _calibration_payload(size: int) -> bytes:
    marker = b"infra-joint-heterogeneous-v1-calibration\n"
    return (marker * ceil(size / len(marker)))[:size]


def _percentile(ordered: Sequence[float], percentile: int) -> float:
    rank = max(0, min(len(ordered) - 1, ceil(percentile * len(ordered) / 100) - 1))
    return ordered[rank]
