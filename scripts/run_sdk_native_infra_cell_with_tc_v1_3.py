"""Apply one attested tc regime around one frozen SDK-native v1.3 cell."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

import yaml
from sdk_native_infra_preliminary_v1_3 import run_once

from infra_joint.heterogeneous.traffic_control import (
    SshCommandRunner,
    TcController,
    TcEndpoint,
    TcRegime,
    build_tc_command_plan,
)

REPO = Path(__file__).resolve().parents[1]
DEFAULT_ENDPOINTS = (
    REPO / "configs/experiments/sdk-native-infra-v1.3-tc-endpoints.yaml"
)


def _yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"configuration must be a mapping: {path}")
    return cast(dict[str, Any], value)


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


async def _snapshot(
    runner: SshCommandRunner,
    endpoints: tuple[TcEndpoint, ...],
) -> dict[str, str]:
    values = await asyncio.gather(
        *(
            runner.run(
                item.ssh_target,
                ("sudo", "-n", "tc", "qdisc", "show", "dev", item.interface),
            )
            for item in endpoints
        )
    )
    return {item.agent_id: value for item, value in zip(endpoints, values, strict=True)}


async def run(
    args: argparse.Namespace,
    execute_cell: Callable[[argparse.Namespace], Awaitable[None]] = run_once,
) -> None:
    evidence = args.output / "tc-attestation.json"
    if evidence.exists():
        raise FileExistsError("tc evidence already exists; refusing retry or overwrite")
    config = _yaml(args.config)
    network = cast(dict[str, Any], config["network"])
    worker_urls = cast(dict[str, str], config["worker_urls"])
    ports = tuple(
        sorted(
            {
                cast(int, urlparse(value).port)
                for value in worker_urls.values()
                if urlparse(value).port is not None
            }
        )
    )
    endpoints = tuple(
        TcEndpoint.model_validate(item)
        for item in cast(
            list[dict[str, Any]],
            _yaml(args.endpoint_config)["tc_endpoints"],
        )
    )
    regime = TcRegime(
        configuration_id=f"sdk-native-infra-v1.3-{config['run_id']}",
        bandwidth_mbps=float(network["bandwidth_mbps"]),
        added_rtt_ms=float(network["added_rtt_ms"]),
        worker_ports=ports,
    )
    runner = SshCommandRunner(command_timeout_seconds=120)
    controllers = tuple(TcController(runner) for _ in endpoints)
    record: dict[str, object] = {
        "run_id": str(config["run_id"]),
        "network": network,
        "worker_ports": ports,
        "original_qdisc": await _snapshot(runner, endpoints),
        "applied_qdisc": None,
        "restored_qdisc": None,
        "cleanup_error": None,
    }
    run_error: BaseException | None = None
    try:
        applied = await asyncio.gather(
            *(
                controller.apply((build_tc_command_plan(endpoint, regime),))
                for controller, endpoint in zip(controllers, endpoints, strict=True)
            )
        )
        record["applied_qdisc"] = {
            item.endpoint.agent_id: item.shaped_qdisc
            for group in applied
            for item in group
        }
        await execute_cell(args)
    except BaseException as exc:  # noqa: BLE001 - cleanup and evidence are mandatory
        run_error = exc
    finally:
        cleanup = await asyncio.gather(
            *(controller.cleanup() for controller in controllers),
            return_exceptions=True,
        )
        failures = [
            f"{type(item).__name__}: {item}"
            for item in cleanup
            if isinstance(item, BaseException)
        ]
        if failures:
            record["cleanup_error"] = "; ".join(failures)
        record["restored_qdisc"] = await _snapshot(runner, endpoints)
        _write(evidence, record)
    if record["cleanup_error"] is not None:
        raise RuntimeError(str(record["cleanup_error"]))
    if run_error is not None:
        raise run_error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--multihop-corpus", type=Path, required=True)
    parser.add_argument("--multihop-queries", type=Path, required=True)
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--endpoint-config", type=Path, default=DEFAULT_ENDPOINTS)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
