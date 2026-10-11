"""Apply unchanged Fast tc command plans in one SSH transaction per node."""

import asyncio
import json
import shlex
from urllib.parse import urlparse

import yaml

from infra_joint.heterogeneous.traffic_control import (
    SshCommandRunner,
    TcEndpoint,
    TcRegime,
    _validate_restorable_root,
    build_tc_command_plan,
)


async def batch_remote(target, commands):
    # Only fixed tc argv enter this shell, never task content or credentials.
    if any(tuple(command[:3]) != ("sudo", "-n", "tc") for command in commands):
        raise ValueError("only the frozen tc plan may enter the privileged batch")
    # tc's native batch preserves the command order and fails on the first error.
    # One authorized sudo invocation avoids this host's per-invocation DNS delay.
    script = "\n".join(shlex.join(command[3:]) for command in commands) + "\n"
    process = await asyncio.create_subprocess_exec(
        "ssh",
        "-T",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=5",
        target,
        "sudo -n tc -batch -",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _stdout, stderr = await asyncio.wait_for(process.communicate(script.encode()), timeout=90)
    except BaseException:
        if process.returncode is None:
            process.kill()
            await process.wait()
        raise
    if process.returncode:
        raise RuntimeError("tc batch failed: " + stderr.decode(errors="replace")[-1000:])


async def run_shaped(args, execute_cell):
    evidence = args.output / "tc-attestation.json"
    if evidence.exists():
        raise FileExistsError("refusing tc evidence overwrite")
    config = yaml.safe_load(args.config.read_text())
    endpoints = tuple(
        TcEndpoint.model_validate(row)
        for row in yaml.safe_load(args.endpoint_config.read_text())["tc_endpoints"]
    )
    ports = tuple(sorted({urlparse(url).port for url in config["worker_urls"].values()}))
    regime = TcRegime(
        configuration_id=config["run_id"], bandwidth_mbps=100, added_rtt_ms=5, worker_ports=ports
    )
    plans = tuple(build_tc_command_plan(endpoint, regime) for endpoint in endpoints)
    runner = SshCommandRunner(command_timeout_seconds=60)

    async def snapshot():
        values = await asyncio.gather(
            *(
                runner.run(
                    endpoint.ssh_target,
                    ("sudo", "-n", "tc", "qdisc", "show", "dev", endpoint.interface),
                )
                for endpoint in endpoints
            )
        )
        return {e.agent_id: value for e, value in zip(endpoints, values, strict=True)}

    before = await snapshot()
    for value in before.values():
        _validate_restorable_root(value)
    record = {
        "original_qdisc": before,
        "applied_qdisc": None,
        "restored_qdisc": None,
        "cleanup_error": None,
        "worker_ports": ports,
        "network": config["network"],
        "command_plans": [{"agent": p.endpoint.agent_id, "apply": p.apply} for p in plans],
        "same_original_command_plans": True,
    }
    touched = []
    try:
        touched.extend(plans)
        results = await asyncio.gather(
            *(batch_remote(p.endpoint.ssh_target, p.apply) for p in plans), return_exceptions=True
        )
        if any(isinstance(r, BaseException) for r in results):
            raise RuntimeError("tc apply failed; restoring all attempted nodes")
        record["applied_qdisc"] = await snapshot()
        if any("qdisc htb 1: root" not in value for value in record["applied_qdisc"].values()):
            raise RuntimeError("Fast tc root was not applied")
        await execute_cell(args)
    finally:
        failures = []
        for plan in touched:
            try:
                await runner.run(plan.endpoint.ssh_target, plan.cleanup)
            except BaseException as exc:
                failures.append(type(exc).__name__)
        record["restored_qdisc"] = await snapshot()
        if record["restored_qdisc"] != before:
            failures.append("qdisc restoration mismatch")
        record["cleanup_error"] = "; ".join(failures) if failures else None
        with evidence.open("x", encoding="utf-8") as stream:
            json.dump(record, stream, indent=2)
        if failures:
            raise RuntimeError("tc restoration failed")
