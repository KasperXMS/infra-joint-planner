"""Apply tc locally, run one remote experiment cell, and persist tc evidence."""

from __future__ import annotations

import argparse
import asyncio
import re
import shlex
from pathlib import Path

from blind_baseline_6task_v1 import REPO, _write_json, _yaml

from infra_joint.heterogeneous.traffic_control import (
    SshCommandRunner,
    TcController,
    TcEndpoint,
    TcRegime,
    build_tc_command_plan,
)

RUN_ID = re.compile(r"^[0-9]{2}-[a-z0-9-]+-H_(?:low|mid|high)-(?:resource-blind|infra-aware)$")
TC_ENDPOINT_CONFIG = REPO / "configs/local/heterogeneous-v1-preflight.yaml"
TC_PORT_CONFIG = REPO / "configs/local/heterogeneous-v1.yaml"


def _surface() -> tuple[tuple[TcEndpoint, ...], tuple[int, ...]]:
    raw = _yaml(TC_ENDPOINT_CONFIG)
    endpoints = tuple(TcEndpoint.model_validate(item) for item in raw["tc_endpoints"])
    addresses = {item.agent_id: item.address for item in endpoints}
    all_paths = tuple(
        item.model_copy(
            update={
                "peer_addresses": tuple(
                    value
                    for agent_id, value in sorted(addresses.items())
                    if agent_id != item.agent_id
                )
            }
        )
        for item in endpoints
    )
    ports = tuple(int(item) for item in _yaml(TC_PORT_CONFIG)["worker_ports"])
    return all_paths, ports


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


async def _qdisc_snapshot(
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
    return {
        item.agent_id: value
        for item, value in zip(endpoints, values, strict=True)
    }


async def _class_snapshot(
    runner: SshCommandRunner,
    endpoints: tuple[TcEndpoint, ...],
) -> dict[str, str]:
    values = await asyncio.gather(
        *(
            runner.run(
                item.ssh_target,
                (
                    "sudo",
                    "-n",
                    "tc",
                    "-s",
                    "class",
                    "show",
                    "dev",
                    item.interface,
                ),
            )
            for item in endpoints
        )
    )
    return {
        item.agent_id: value
        for item, value in zip(endpoints, values, strict=True)
    }


async def run(args: argparse.Namespace) -> None:
    if RUN_ID.fullmatch(args.run_id) is None:
        raise ValueError("run-id does not match the frozen cell identifier contract")
    if args.evidence.exists():
        raise RuntimeError("tc evidence exists; refusing retry or overwrite")
    endpoints, ports = _surface()
    runner = SshCommandRunner(command_timeout_seconds=120)
    controllers = tuple(TcController(runner) for _ in endpoints)
    regime = TcRegime(
        configuration_id=f"infra-replan-v1-{args.run_id}",
        bandwidth_mbps=args.bandwidth_mbps,
        added_rtt_ms=0,
        worker_ports=ports,
    )
    record: dict[str, object] = {
        "run_id": args.run_id,
        "bandwidth_mbps": args.bandwidth_mbps,
        "added_rtt_ms": 0,
        "remote_target": args.remote_target,
        "remote_returncode": None,
        "remote_stdout": None,
        "remote_stderr": None,
        "cleanup_error": None,
    }
    record["original_qdisc"] = await _qdisc_snapshot(runner, endpoints)
    remote_returncode = 1
    try:
        applied_groups = await asyncio.gather(
            *(
                controller.apply((build_tc_command_plan(endpoint, regime),))
                for controller, endpoint in zip(controllers, endpoints, strict=True)
            )
        )
        record["applied_qdisc"] = {
            item.endpoint.agent_id: item.shaped_qdisc
            for group in applied_groups
            for item in group
        }
        record["class_before_run"] = await _class_snapshot(runner, endpoints)
        remote_command = shlex.join(
            (
                "cd",
                args.remote_app,
            )
        ) + " && " + shlex.join(
            (
                "env",
                f"PYTHONPATH={args.remote_app}/src:{args.remote_app}/scripts",
                f"{args.remote_app}/.venv/bin/python",
                f"{args.remote_app}/scripts/infra_aware_replanning_preliminary_v1.py",
                "--resume-matrix",
                "--reuse-prepositioned",
                "--external-tc",
                "--only-run-id",
                args.run_id,
                "--source-evidence",
                args.source_evidence,
                "--video-source",
                args.video_source,
                "--longbench-samples",
                args.longbench_samples,
                "--multihop-corpus",
                args.multihop_corpus,
                "--multihop-queries",
                args.multihop_queries,
                "--api-key-file",
                args.api_key_file,
                "--output",
                args.remote_output,
            )
        )
        remote_returncode, stdout, stderr = await _process(
            "ssh", "-T", "-o", "BatchMode=yes", args.remote_target, remote_command
        )
        record["remote_returncode"] = remote_returncode
        record["remote_stdout"] = stdout
        record["remote_stderr"] = stderr
        record["class_after_run"] = await _class_snapshot(runner, endpoints)
    finally:
        cleanup_results = await asyncio.gather(
            *(item.cleanup() for item in controllers), return_exceptions=True
        )
        cleanup_errors = [
            f"{type(item).__name__}: {item}"
            for item in cleanup_results
            if isinstance(item, BaseException)
        ]
        if cleanup_errors:
            record["cleanup_error"] = "; ".join(cleanup_errors)
        record["restored_qdisc"] = await _qdisc_snapshot(runner, endpoints)
        _write_json(args.evidence, record)
        remote_sidecar = f"{args.remote_output}/runs/{args.run_id}/tc-attestation.json"
        scp_code, _, scp_error = await _process(
            "scp", str(args.evidence), f"{args.remote_target}:{remote_sidecar}"
        )
        if scp_code != 0:
            raise RuntimeError(f"failed to persist remote tc attestation: {scp_error}")
    if record["cleanup_error"] is not None:
        raise RuntimeError(str(record["cleanup_error"]))
    if remote_returncode != 0:
        raise RuntimeError(f"remote cell failed: {record['remote_stderr']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--bandwidth-mbps", type=float, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--remote-target", default="super@192.168.0.12")
    parser.add_argument(
        "--remote-app",
        default="/home/super/xiaoming/infra_aware_replanning_preliminary_v1/app",
    )
    parser.add_argument(
        "--remote-output",
        default="/home/super/xiaoming/infra_aware_replanning_preliminary_v1/evidence-attempt2",
    )
    parser.add_argument(
        "--source-evidence",
        default="/home/super/xiaoming/blind_baseline_6task_competent_v2/evidence",
    )
    parser.add_argument(
        "--video-source",
        default="/home/super/xiaoming/calibration_v0/source/D97vMwfWxvI.mp4",
    )
    parser.add_argument(
        "--longbench-samples",
        default=(
            "/home/super/xiaoming/infra-bench/scenario-mining/data/"
            "longbench_v2/selected.jsonl"
        ),
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
