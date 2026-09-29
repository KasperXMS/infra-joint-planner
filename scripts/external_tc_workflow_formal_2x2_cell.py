"""Apply one attested network regime and run one remote formal 2x2 cell."""

# The local tc endpoint inventory is deliberately untracked machine configuration.
# pyright: reportPrivateUsage=false

from __future__ import annotations

import argparse
import asyncio
import json
import shlex
from pathlib import Path
from typing import Any, cast

import yaml

from infra_joint.heterogeneous.traffic_control import (
    SshCommandRunner,
    TcController,
    TcEndpoint,
    TcRegime,
    build_tc_command_plan,
)

REPO = Path(__file__).resolve().parents[1]
DEFAULT_ENDPOINTS = REPO / "configs/local/heterogeneous-v1-preflight.yaml"


def _yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"configuration must be a mapping: {path}")
    return cast(dict[str, Any], value)


def _endpoints(path: Path) -> tuple[TcEndpoint, ...]:
    raw = _yaml(path)
    endpoints = tuple(
        TcEndpoint.model_validate(item) for item in cast(list[dict[str, Any]], raw["tc_endpoints"])
    )
    addresses = {item.agent_id: item.address for item in endpoints}
    return tuple(
        item.model_copy(
            update={
                "peer_addresses": tuple(
                    address
                    for agent_id, address in sorted(addresses.items())
                    if agent_id != item.agent_id
                )
            }
        )
        for item in endpoints
    )


async def _process(*command: str) -> tuple[int, str, str]:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return (
        process.returncode or 0,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )


async def _snapshot(
    runner: SshCommandRunner,
    endpoints: tuple[TcEndpoint, ...],
    *,
    statistics: bool,
) -> dict[str, str]:
    prefix = (
        ("sudo", "-n", "tc", "-s", "class", "show", "dev")
        if statistics
        else (
            "sudo",
            "-n",
            "tc",
            "qdisc",
            "show",
            "dev",
        )
    )
    values = await asyncio.gather(
        *(runner.run(item.ssh_target, (*prefix, item.interface)) for item in endpoints)
    )
    return {item.agent_id: value for item, value in zip(endpoints, values, strict=True)}


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


async def run(args: argparse.Namespace) -> None:
    if args.evidence.exists():
        raise FileExistsError("tc evidence already exists; refusing retry or overwrite")
    endpoints = _endpoints(args.endpoint_config)
    runner = SshCommandRunner(command_timeout_seconds=120)
    controllers = tuple(TcController(runner) for _ in endpoints)
    regime = TcRegime(
        configuration_id=f"workflow-formal-2x2-{args.run_id}",
        bandwidth_mbps=args.bandwidth_mbps,
        added_rtt_ms=args.added_rtt_ms,
        worker_ports=tuple(args.worker_port),
    )
    record: dict[str, object] = {
        "run_id": args.run_id,
        "bandwidth_mbps": args.bandwidth_mbps,
        "added_rtt_ms": args.added_rtt_ms,
        "worker_ports": args.worker_port,
        "original_qdisc": await _snapshot(runner, endpoints, statistics=False),
        "remote_returncode": None,
        "remote_stdout": None,
        "remote_stderr": None,
        "cleanup_error": None,
    }
    returncode = 1
    try:
        applied = await asyncio.gather(
            *(
                controller.apply((build_tc_command_plan(endpoint, regime),))
                for controller, endpoint in zip(controllers, endpoints, strict=True)
            )
        )
        record["applied_qdisc"] = {
            item.endpoint.agent_id: item.shaped_qdisc for group in applied for item in group
        }
        record["class_before_run"] = await _snapshot(runner, endpoints, statistics=True)
        remote_parts = (
            "cd",
            args.remote_app,
        )
        run_parts = [
            "env",
            f"PYTHONPATH={args.remote_app}/src:{args.remote_app}/scripts",
            f"{args.remote_app}/.venv/bin/python",
            f"{args.remote_app}/scripts/workflow_formal_preliminary_2x2_v1.py",
            "run-cell",
            "--run-id",
            args.run_id,
            "--output",
            args.remote_output,
            "--multihop-corpus",
            args.multihop_corpus,
            "--multihop-queries",
            args.multihop_queries,
            "--api-key-file",
            args.api_key_file,
        ]
        for value in args.worker_url:
            run_parts.extend(("--worker-url", value))
        remote_command = shlex.join(remote_parts) + " && " + shlex.join(run_parts)
        returncode, stdout, stderr = await _process(
            "ssh",
            "-T",
            "-o",
            "BatchMode=yes",
            args.remote_target,
            remote_command,
        )
        record["remote_returncode"] = returncode
        record["remote_stdout"] = stdout
        record["remote_stderr"] = stderr
        record["class_after_run"] = await _snapshot(runner, endpoints, statistics=True)
    finally:
        cleanup = await asyncio.gather(
            *(controller.cleanup() for controller in controllers), return_exceptions=True
        )
        errors = [
            f"{type(value).__name__}: {value}"
            for value in cleanup
            if isinstance(value, BaseException)
        ]
        if errors:
            record["cleanup_error"] = "; ".join(errors)
        record["restored_qdisc"] = await _snapshot(runner, endpoints, statistics=False)
        _write(args.evidence, record)
        sidecar = f"{args.remote_output}/runs/{args.run_id}/tc-attestation.json"
        scp_code, _, scp_error = await _process(
            "scp", str(args.evidence), f"{args.remote_target}:{sidecar}"
        )
        if scp_code != 0:
            raise RuntimeError(f"failed to persist remote tc attestation: {scp_error}")
    if record["cleanup_error"] is not None:
        raise RuntimeError(str(record["cleanup_error"]))
    if returncode != 0:
        raise RuntimeError(f"remote formal cell failed: {record['remote_stderr']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--bandwidth-mbps", type=float, required=True)
    parser.add_argument("--added-rtt-ms", type=float, required=True)
    parser.add_argument("--worker-port", action="append", type=int, required=True)
    parser.add_argument("--worker-url", action="append", required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--endpoint-config", type=Path, default=DEFAULT_ENDPOINTS)
    parser.add_argument("--remote-target", default="super@192.168.0.12")
    parser.add_argument(
        "--remote-app",
        default="/home/super/xiaoming/workflow_formal_preliminary_2x2_v1/app",
    )
    parser.add_argument(
        "--remote-output",
        default="/home/super/xiaoming/workflow_formal_preliminary_2x2_v1/evidence",
    )
    parser.add_argument(
        "--multihop-corpus",
        default="/home/super/xiaoming/blind_baseline_6task_v1/data/corpus.json",
    )
    parser.add_argument(
        "--multihop-queries",
        default="/home/super/xiaoming/blind_baseline_6task_v1/data/MultiHopRAG.json",
    )
    parser.add_argument(
        "--api-key-file",
        default="/home/super/xiaoming/blind_baseline_6task_v1/api_key.txt",
    )
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
