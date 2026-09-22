"""Operational driver for Heterogeneous Infrastructure Experiment v1.

The script intentionally exposes phase-sized commands. It never falls back to
the v0 application-layer emulator when ``tc-preflight`` or later v1 commands
are requested.
"""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import yaml

from infra_joint.heterogeneous.calibration import (
    NetworkCalibrator,
    build_network_calibration,
)
from infra_joint.heterogeneous.contracts import NetworkControlMethod, NetworkRegime
from infra_joint.heterogeneous.traffic_control import (
    SshCommandRunner,
    TcController,
    TcEndpoint,
    TcRegime,
    build_tc_command_plan,
)


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise ValueError("heterogeneous v1 configuration must be a mapping")
    return value


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
    endpoints = tuple(TcEndpoint.model_validate(item) for item in endpoints_raw)
    regime = TcRegime(
        configuration_id=(configuration_id or f"tc-{bandwidth_mbps:g}mbit-rtt{added_rtt_ms:g}"),
        bandwidth_mbps=bandwidth_mbps,
        added_rtt_ms=added_rtt_ms,
        worker_ports=tuple(int(item) for item in ports_raw),
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
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(record, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(output)
    print(output)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)
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
    calibration.add_argument("--output-root", type=Path, default=Path("results"))
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "tc-preflight":
        asyncio.run(_tc_preflight(args))
        return
    if args.command == "network-calibrate":
        asyncio.run(_network_calibrate(args))
        return
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    main()
