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
        configuration_id=(
            configuration_id
            or f"tc-{bandwidth_mbps:g}mbit-rtt{added_rtt_ms:g}"
        ),
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
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "tc-preflight":
        asyncio.run(_tc_preflight(args))
        return
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    main()
