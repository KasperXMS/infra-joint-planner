"""Operational driver for Heterogeneous Infrastructure Experiment v1.

The script intentionally exposes phase-sized commands. It never falls back to
the v0 application-layer emulator when ``tc-preflight`` or later v1 commands
are requested.
"""

import argparse
import asyncio
import json
from contextlib import AsyncExitStack
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any, Self, cast
from urllib.parse import quote

import httpx
import yaml
from pydantic import Field, model_validator

from infra_joint.core.base import ContractModel
from infra_joint.core.state import EnvironmentSpec
from infra_joint.heterogeneous.calibration import (
    NetworkCalibrator,
    build_network_calibration,
)
from infra_joint.heterogeneous.contracts import (
    EquivalentModelReplicaSet,
    NetworkControlMethod,
    NetworkRegime,
)
from infra_joint.heterogeneous.hardware import collect_hardware_preflight_evidence
from infra_joint.heterogeneous.preflight import validate_heterogeneous_preflight
from infra_joint.heterogeneous.traffic_control import (
    RemoteCommandRunner,
    SshCommandRunner,
    TcController,
    TcEndpoint,
    TcRegime,
    build_tc_command_plan,
)
from infra_joint.infrastructure.validation import validate_worker_surfaces
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.runtime.client import HttpWorkerClient, WorkerClient
from infra_joint.worker.server import WorkerStateResponse


class ArtifactProbeMode(StrEnum):
    EXISTING = "existing"
    DETERMINISTIC_NAMESPACED = "deterministic_namespaced"


class ArtifactProbeConfig(ContractModel):
    mode: ArtifactProbeMode = ArtifactProbeMode.EXISTING
    artifact_ids: dict[str, str] = Field(default_factory=dict)
    allow_namespaced_write: bool = False

    @model_validator(mode="after")
    def writes_require_explicit_acknowledgement(self) -> Self:
        if self.mode == ArtifactProbeMode.DETERMINISTIC_NAMESPACED:
            if not self.allow_namespaced_write:
                raise ValueError(
                    "deterministic artifact probing requires allow_namespaced_write=true"
                )
            if self.artifact_ids:
                raise ValueError("deterministic artifact probing does not accept artifact_ids")
        elif self.allow_namespaced_write:
            raise ValueError("existing artifact probing must not enable namespaced writes")
        return self


class OperationalPreflightConfig(ContractModel):
    environment: EnvironmentSpec
    worker_urls: dict[str, str]
    equivalent_replicas: EquivalentModelReplicaSet
    required_agent_ids: frozenset[str] = Field(min_length=2)
    rtx_agent_id: str = Field(min_length=1)
    tc_endpoints: tuple[TcEndpoint, ...] = Field(min_length=1)
    artifact_probe: ArtifactProbeConfig = ArtifactProbeConfig()

    @model_validator(mode="after")
    def references_match(self) -> Self:
        environment_agents = {item.agent_id for item in self.environment.agents}
        if set(self.worker_urls) != environment_agents:
            raise ValueError("worker_urls must exactly cover EnvironmentSpec agents")
        endpoint_agents = {item.agent_id for item in self.tc_endpoints}
        if len(endpoint_agents) != len(self.tc_endpoints):
            raise ValueError("tc endpoint agent IDs must be unique")
        if endpoint_agents != set(self.required_agent_ids):
            raise ValueError("tc_endpoints must exactly cover required_agent_ids")
        if self.rtx_agent_id not in self.required_agent_ids:
            raise ValueError("rtx_agent_id must be a required agent")
        unknown_probe_agents = set(self.artifact_probe.artifact_ids) - environment_agents
        if unknown_probe_agents:
            raise ValueError(
                f"artifact probe references unknown agents: {sorted(unknown_probe_agents)}"
            )
        return self


class ArtifactEndpointEvidence(ContractModel):
    agent_id: str = Field(min_length=1)
    artifact_id: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    sha256_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    probe_mode: ArtifactProbeMode


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise ValueError("heterogeneous v1 configuration must be a mapping")
    return cast(dict[str, Any], value)


def _operational_preflight_config(path: Path) -> OperationalPreflightConfig:
    raw = _load_yaml(path)
    required = (
        "environment",
        "worker_urls",
        "equivalent_replicas",
        "required_agent_ids",
        "rtx_agent_id",
        "tc_endpoints",
    )
    missing = [key for key in required if key not in raw]
    if missing:
        raise ValueError(f"hard preflight configuration is missing keys: {missing}")
    return OperationalPreflightConfig.model_validate(
        {
            "environment": raw["environment"],
            "worker_urls": raw["worker_urls"],
            "equivalent_replicas": raw["equivalent_replicas"],
            "required_agent_ids": raw["required_agent_ids"],
            "rtx_agent_id": raw["rtx_agent_id"],
            "tc_endpoints": raw["tc_endpoints"],
            "artifact_probe": raw.get("artifact_probe", {}),
        }
    )


def _artifact_metadata(
    state: WorkerStateResponse,
    artifact_id: str,
) -> tuple[str, int, str]:
    artifacts = {item.artifact_id: item for item in state.artifacts}
    try:
        artifact = artifacts[artifact_id]
    except KeyError as exc:
        raise RuntimeError(
            f"artifact probe target is absent on {state.agent_id}: {artifact_id}"
        ) from exc
    return artifact.media_type, artifact.size_bytes, artifact.sha256_hex


async def _get_and_validate_artifact(
    agent_id: str,
    artifact_id: str,
    expected_media_type: str,
    expected_size: int,
    expected_sha256: str,
    client: httpx.AsyncClient,
    mode: ArtifactProbeMode,
) -> ArtifactEndpointEvidence:
    response = await client.get(f"/artifact/{quote(artifact_id, safe='')}")
    response.raise_for_status()
    actual_sha256 = sha256(response.content).hexdigest()
    header_sha256 = response.headers.get("x-artifact-sha256")
    media_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0]
    if (
        len(response.content) != expected_size
        or actual_sha256 != expected_sha256
        or header_sha256 != expected_sha256
        or media_type != expected_media_type
    ):
        raise RuntimeError(f"artifact endpoint integrity mismatch on Worker: {agent_id}")
    return ArtifactEndpointEvidence(
        agent_id=agent_id,
        artifact_id=artifact_id,
        media_type=media_type,
        size_bytes=len(response.content),
        sha256_hex=actual_sha256,
        probe_mode=mode,
    )


async def _probe_artifact_endpoints(
    config: OperationalPreflightConfig,
    states: dict[str, WorkerStateResponse],
    clients: dict[str, WorkerClient],
    http_clients: dict[str, httpx.AsyncClient],
) -> tuple[ArtifactEndpointEvidence, ...]:
    evidence: list[ArtifactEndpointEvidence] = []
    deterministic_content = b"infra-joint heterogeneous-v1 hard-preflight artifact\n"
    deterministic_sha256 = sha256(deterministic_content).hexdigest()
    deterministic_id = f"__infra_joint_preflight__--{deterministic_sha256[:16]}"
    formal_artifact_ids = {
        item.artifact_id for item in config.environment.initial_placements
    }
    if deterministic_id in formal_artifact_ids:
        raise RuntimeError("reserved preflight artifact ID collides with a formal artifact")

    for agent_id in sorted(states):
        state = states[agent_id]
        if config.artifact_probe.mode == ArtifactProbeMode.EXISTING:
            configured = config.artifact_probe.artifact_ids.get(agent_id)
            if configured is None:
                available = sorted(item.artifact_id for item in state.artifacts)
                if not available:
                    raise RuntimeError(
                        "Worker has no existing artifact for a read-only endpoint probe: "
                        f"{agent_id}"
                    )
                artifact_id = available[0]
            else:
                artifact_id = configured
            media_type, size_bytes, checksum = _artifact_metadata(state, artifact_id)
        else:
            artifact_id = deterministic_id
            response = await clients[agent_id].put_artifact(
                artifact_id,
                "text/plain",
                deterministic_content,
                deterministic_sha256,
            )
            if (
                response.size_bytes != len(deterministic_content)
                or response.sha256_hex != deterministic_sha256
            ):
                raise RuntimeError(f"artifact PUT integrity mismatch on Worker: {agent_id}")
            media_type = "text/plain"
            size_bytes = len(deterministic_content)
            checksum = deterministic_sha256
        evidence.append(
            await _get_and_validate_artifact(
                agent_id,
                artifact_id,
                media_type,
                size_bytes,
                checksum,
                http_clients[agent_id],
                config.artifact_probe.mode,
            )
        )
    return tuple(evidence)


async def run_hard_preflight(
    config: OperationalPreflightConfig,
    *,
    ssh_runner: RemoteCommandRunner | None = None,
) -> dict[str, Any]:
    async with AsyncExitStack() as stack:
        http_clients: dict[str, httpx.AsyncClient] = {}
        worker_clients: dict[str, WorkerClient] = {}
        for agent_id, base_url in config.worker_urls.items():
            client = await stack.enter_async_context(
                httpx.AsyncClient(base_url=base_url, timeout=120)
            )
            http_clients[agent_id] = client
            worker_clients[agent_id] = HttpWorkerClient(agent_id, client)

        states = await validate_worker_surfaces(
            config.environment,
            build_operator_catalog(),
            worker_clients,
        )
        validate_heterogeneous_preflight(
            config.environment,
            states,
            config.equivalent_replicas,
            required_agent_ids=config.required_agent_ids,
            rtx_agent_id=config.rtx_agent_id,
        )
        artifact_evidence = await _probe_artifact_endpoints(
            config,
            states,
            worker_clients,
            http_clients,
        )

    hardware = await collect_hardware_preflight_evidence(
        config.tc_endpoints,
        config.rtx_agent_id,
        ssh_runner or SshCommandRunner(),
    )
    return {
        "schema_version": "heterogeneous-v1-hard-preflight-v1",
        "status": "ok",
        "required_agent_ids": sorted(config.required_agent_ids),
        "rtx_agent_id": config.rtx_agent_id,
        "workers": {
            agent_id: {
                "identity": state.agent_id,
                "available": state.available,
                "operators": list(state.operators),
                "deployments": [
                    item.model_dump(mode="json") for item in state.deployments
                ],
            }
            for agent_id, state in sorted(states.items())
        },
        "equivalent_replicas": config.equivalent_replicas.model_dump(mode="json"),
        "artifact_endpoints": [
            item.model_dump(mode="json") for item in artifact_evidence
        ],
        "artifact_probe_isolated": (
            config.artifact_probe.mode == ArtifactProbeMode.EXISTING
            or all(
                item.artifact_id.startswith("__infra_joint_preflight__--")
                for item in artifact_evidence
            )
        ),
        "hardware": hardware.model_dump(mode="json"),
    }


async def _hard_preflight(args: argparse.Namespace) -> None:
    result = await run_hard_preflight(_operational_preflight_config(args.config))
    serialized = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output is not None:
        write_text_atomic(args.output, serialized + "\n")
    print(serialized)


def write_text_atomic(output: Path, content: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(f"{output.suffix}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(output)


def _tc_inputs(
    path: Path,
    bandwidth_mbps: float,
    added_rtt_ms: float,
    configuration_id: str | None = None,
) -> tuple[tuple[TcEndpoint, ...], TcRegime]:
    raw = _load_yaml(path)
    endpoints_raw = raw.get("tc_endpoints")
    ports_raw = raw.get("worker_ports")
    if not isinstance(endpoints_raw, list) or not isinstance(ports_raw, list):
        raise ValueError("configuration requires tc_endpoints and worker_ports lists")
    endpoint_values = cast(list[object], endpoints_raw)
    port_values = cast(list[int | str], ports_raw)
    endpoints = tuple(TcEndpoint.model_validate(item) for item in endpoint_values)
    regime = TcRegime(
        configuration_id=(configuration_id or f"tc-{bandwidth_mbps:g}mbit-rtt{added_rtt_ms:g}"),
        bandwidth_mbps=bandwidth_mbps,
        added_rtt_ms=added_rtt_ms,
        worker_ports=tuple(int(item) for item in port_values),
    )
    return endpoints, regime


async def _tc_preflight(args: argparse.Namespace) -> None:
    endpoints, regime = _tc_inputs(
        args.config,
        args.bandwidth_mbps,
        args.added_rtt_ms,
        args.configuration_id,
    )
    runner = SshCommandRunner()
    controller = TcController(runner)
    plans = tuple(build_tc_command_plan(endpoint, regime) for endpoint in endpoints)
    states = await controller.apply(plans)
    observations: dict[str, Any] = {
        "configuration_id": regime.configuration_id,
        "network_control": "tc",
        "applied": [
            {
                "agent_id": state.endpoint.agent_id,
                "interface": state.endpoint.interface,
                "original_qdisc": state.original_qdisc,
                "shaped_qdisc": state.shaped_qdisc,
            }
            for state in states
        ],
    }
    try:
        if args.ping_source and args.ping_target:
            observations["ping"] = await runner.run(
                args.ping_source,
                ("ping", "-n", "-c", "20", "-i", "0.1", args.ping_target),
            )
    finally:
        await controller.cleanup()
    observations["restored"] = {
        endpoint.agent_id: await runner.run(
            endpoint.ssh_target,
            ("sudo", "-n", "tc", "qdisc", "show", "dev", endpoint.interface),
        )
        for endpoint in endpoints
    }
    print(json.dumps(observations, indent=2, sort_keys=True))


async def _network_calibrate(args: argparse.Namespace) -> None:
    endpoints, tc_regime = _tc_inputs(
        args.config,
        args.bandwidth_mbps,
        args.added_rtt_ms,
        args.tc_configuration_id,
    )
    by_agent = {item.agent_id: item for item in endpoints}
    source = by_agent[args.source_agent]
    target = by_agent[args.target_agent]
    runner = SshCommandRunner()
    controller = TcController(runner)
    calibrator = NetworkCalibrator(runner)
    states = await controller.apply(
        tuple(build_tc_command_plan(endpoint, tc_regime) for endpoint in endpoints)
    )
    try:
        rtt = await calibrator.measure_ping(
            target.ssh_target,
            source.address,
            warmup_samples=args.ping_warmup,
            measured_samples=args.ping_samples,
        )
        throughput = await calibrator.measure_iperf(
            source.ssh_target,
            target.ssh_target,
            target.address,
            repetitions=args.iperf_repetitions,
            duration_seconds=args.iperf_duration_seconds,
        )
        artifacts = await calibrator.measure_artifact_transfers(
            source.agent_id,
            target.agent_id,
            args.source_worker_url,
            args.target_worker_url,
            tuple(size * 1024 * 1024 for size in args.artifact_mib),
            calibration_id=args.calibration_id,
            repetitions=args.artifact_repetitions,
        )
        tc_statistics = {
            state.endpoint.agent_id: await runner.run(
                state.endpoint.ssh_target,
                (
                    "sudo",
                    "-n",
                    "tc",
                    "-s",
                    "qdisc",
                    "show",
                    "dev",
                    state.endpoint.interface,
                ),
            )
            for state in states
        }
    finally:
        await controller.cleanup()
    regime = NetworkRegime(
        regime_id=args.regime_id,
        bandwidth_mbps=args.bandwidth_mbps,
        added_rtt_ms=args.added_rtt_ms,
        control_method=NetworkControlMethod.TC,
        tc_configuration_id=args.tc_configuration_id,
    )
    calibration = build_network_calibration(
        args.calibration_id,
        regime,
        source.agent_id,
        target.agent_id,
        rtt,
        throughput,
        artifacts,
    )
    record = {
        "calibration": calibration.model_dump(mode="json"),
        "tc_statistics": tc_statistics,
        "restored_qdisc": {
            endpoint.agent_id: await runner.run(
                endpoint.ssh_target,
                (
                    "sudo",
                    "-n",
                    "tc",
                    "qdisc",
                    "show",
                    "dev",
                    endpoint.interface,
                ),
            )
            for endpoint in endpoints
        },
    }
    output = args.output_root / "network_calibration" / f"{args.calibration_id}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(output, json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(output)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)
    hard = subcommands.add_parser("hard-preflight")
    hard.add_argument("--config", type=Path, required=True)
    hard.add_argument("--output", type=Path)

    tc = subcommands.add_parser("tc-preflight")
    tc.add_argument("--config", type=Path, required=True)
    tc.add_argument("--bandwidth-mbps", type=float, required=True)
    tc.add_argument("--added-rtt-ms", type=float, required=True)
    tc.add_argument("--configuration-id")
    tc.add_argument("--ping-source")
    tc.add_argument("--ping-target")

    calibration = subcommands.add_parser("network-calibrate")
    calibration.add_argument("--config", type=Path, required=True)
    calibration.add_argument("--calibration-id", required=True)
    calibration.add_argument("--tc-configuration-id", required=True)
    calibration.add_argument("--regime-id", required=True)
    calibration.add_argument("--bandwidth-mbps", type=float, required=True)
    calibration.add_argument("--added-rtt-ms", type=float, required=True)
    calibration.add_argument("--source-agent", required=True)
    calibration.add_argument("--target-agent", required=True)
    calibration.add_argument("--source-worker-url", required=True)
    calibration.add_argument("--target-worker-url", required=True)
    calibration.add_argument("--ping-warmup", type=int, default=5)
    calibration.add_argument("--ping-samples", type=int, default=100)
    calibration.add_argument("--iperf-repetitions", type=int, default=3)
    calibration.add_argument("--iperf-duration-seconds", type=int, default=5)
    calibration.add_argument("--artifact-mib", type=int, nargs="+", default=[1, 8, 32, 128])
    calibration.add_argument("--artifact-repetitions", type=int, default=3)
    calibration.add_argument("--output-root", type=Path, default=Path("results"))
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "hard-preflight":
        try:
            asyncio.run(_hard_preflight(args))
        except Exception as exc:  # noqa: BLE001 - CLI must emit a machine-readable failure
            print(
                json.dumps(
                    {
                        "schema_version": "heterogeneous-v1-hard-preflight-v1",
                        "status": "failed",
                        "error": {
                            "type": type(exc).__name__,
                            "message": str(exc) or type(exc).__name__,
                        },
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            raise SystemExit(1) from None
        return
    if args.command == "tc-preflight":
        asyncio.run(_tc_preflight(args))
        return
    if args.command == "network-calibrate":
        asyncio.run(_network_calibrate(args))
        return
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    main()
