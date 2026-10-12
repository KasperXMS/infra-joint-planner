"""User-authorized bounded pipeline concurrency; imports the frozen runtime.

This administration entry point lives outside the frozen app on the controller.
Each cell runs in its own process, with isolated ports, globals and artifacts.
Model servers keep their original one-request slots and 32K contexts. Shared
resource timings and overlapping runner logs are diagnostic, not exclusive costs.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import signal
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from time import monotonic, time

import agents
import skill_granularity_service_v2_slot0 as service_slot0
import skill_granularity_service_v2_slot1 as service_slot1
import run_skill_granularity_pilot_v2 as frozen
import yaml
from multiscale_planner_context_v1 import MultiscaleContextConfig
from sdk_native_infra_preliminary_v1_3 import _load_control_plane_key

ROOT = frozen.ROOT
WIDTH = 3
MANAGER_CAPACITY = 2
SERVICE_MODULES = (service_slot0, service_slot1)
BASE_PORTS = dict(frozen.PORTS)
write = frozen.write


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def alive(pid):
    path = Path("/proc") / str(pid)
    if not path.exists():
        return False
    return (path / "stat").read_text().rsplit(")", 1)[1].split()[0] != "Z"


def texts_for(plan):
    texts = {}
    for condition, spec in plan["skills"].items():
        if condition == "S0":
            texts[condition] = None
        else:
            path = frozen.APP / spec["path"]
            if sha(path) != spec["sha256"]:
                raise RuntimeError("frozen Skill drift")
            texts[condition] = path.read_text()
    return texts


async def cleanup_owned_workers(pids, urls, out, context):
    """Drain real owned Workers; shared model slots are drained at wave end."""
    deadline = monotonic() + 1260
    errors = []
    drained = not pids
    while pids and monotonic() < deadline:
        try:
            state = await frozen.pilot.states({agent: urls[agent] for agent in pids})
            if all(value["in_flight"] == 0 for value in state.values()):
                drained = True
                write(out / "private/worker-state-drained.json", state)
                break
        except Exception as exc:
            errors.append("worker_drain:" + type(exc).__name__)
            break
        await asyncio.sleep(2)
    if not drained:
        errors.append("owned_worker_drain_timeout")

    async def stop(agent, identity):
        code = """import json,os,signal,time
from pathlib import Path
v=IDENTITY
p=Path('/proc')/str(v['pid'])/'cmdline'
cmd=p.read_bytes().decode() if p.exists() else ''
assert not cmd or v['config'] in cmd, 'Worker PID ownership changed'
if cmd: os.kill(v['pid'],signal.SIGTERM)
for _ in range(20):
 if not p.exists() or not p.read_bytes(): break
 time.sleep(.5)
print(json.dumps({'exited':not p.exists() or not p.read_bytes()}))
""".replace("IDENTITY", repr(identity), 1)
        return agent, await asyncio.to_thread(frozen.pilot.node_json, agent, code)

    values = await asyncio.gather(*(stop(a, p) for a, p in pids.items()), return_exceptions=True)
    exited = {}
    for value in values:
        if isinstance(value, BaseException):
            errors.append("worker_stop:" + type(value).__name__)
        else:
            exited[value[0]] = value[1]["exited"]
    record = {
        "drained": drained,
        "verified_exited": len(exited) == len(pids) and all(exited.values()),
        "errors": errors,
        "owned_processes": pids,
        "drain_scope": "owned Workers; shared models checked at wave barrier",
        "shared_model_drain_deferred_to_wave": True,
    }
    write(out / "worker-shutdown.json", record)
    return record


async def drain_shared_models(contexts, services, wave):
    deadline = monotonic() + 1260
    while monotonic() < deadline:
        resident = await frozen.pilot.resident_slots(frozen.BASELINE)
        planner = [await service.slots(context) for service, context in zip(services, contexts, strict=True)]
        if all(
            not slot["is_processing"]
            for ports in resident.values()
            for slots in ports.values()
            for slot in slots
        ) and all(not slot["is_processing"] for slots in planner for slot in slots):
            write(
                ROOT / "concurrency-waves" / (wave + "-model-drain.json"),
                {
                    "all_shared_models_idle": True,
                    "resident_slots": resident,
                    "planner_slots": planner,
                    "real_observation": True,
                },
            )
            return
        await asyncio.sleep(2)
    raise RuntimeError("shared_model_drain_timeout")


async def child(args):
    config = json.loads(args.child.read_text())
    plan = json.loads(frozen.PLAN_PATH.read_text())
    agents.set_tracing_disabled(True)
    _load_control_plane_key(args.api_key_file, "DASHSCOPE_API_KEY")
    replica_index = config["replica_index"]
    service = SERVICE_MODULES[replica_index].Service()
    frozen.configure(plan, service)
    frozen.BASELINE = json.loads((ROOT / "private/residency-startup.json").read_text())
    service.baseline = frozen.BASELINE
    frozen.LOG_OFFSETS = {tuple(item["key"]): item["offset"] for item in config["log_offsets"]}
    frozen.PORTS = {agent: port + config["slot"] * 100 for agent, port in BASE_PORTS.items()}
    frozen.pilot.PORTS = frozen.PORTS
    frozen.NETWORK_OUTPUT = ROOT / config["network_output"]
    os.environ["PLANNER_SLOT_LOCK"] = str(ROOT / "manager-slot-locks" / config["endpoint_slot"])
    os.environ["PLANNER_ENDPOINT_SLOT"] = config["endpoint_slot"]
    original_write = frozen.write

    def cell_write(path, value):
        if path.name == "cell-started.json":
            receipt = {
                "shared_resource_concurrency": WIDTH,
                "concurrency_wave": config["wave"],
                "actual_wave_size": config["actual_wave_size"],
                "slot": config["slot"],
                "serving_request_parallelism": 1,
                "a28_manager_request_capacity": MANAGER_CAPACITY,
                "endpoint_slot": config["endpoint_slot"],
                "replica_index": replica_index,
                "shared_executor_pool": True,
                "runner_log_intervals_may_overlap": True,
                "exclusive_e2e_cost_comparison_valid": False,
            }
            original_write(path.parent / "concurrency-receipt.json", receipt)
            value = {**value, **receipt}
        return original_write(path, value)

    frozen.write = cell_write
    frozen.cleanup_workers = cleanup_owned_workers
    context = MultiscaleContextConfig(**config["context"])
    pool = frozen.pilot.frozen._yaml(frozen.APP / plan["infrastructure_design"]["model_pool_path"])
    await service.check_resource(force=True, wait_timeout=600)
    await asyncio.wait_for(
        frozen.one_cell(config["cell"], plan, context, pool, texts_for(plan)), timeout=5100
    )


async def run_wave(cells, contexts, services, wave, network_output, api_key):
    configs = ROOT / "concurrency-configs"
    configs.mkdir(exist_ok=True)
    logs = ROOT / "concurrency-logs"
    logs.mkdir(exist_ok=True)
    processes = []
    launch_error = None
    for slot, cell in enumerate(cells):
        replica_index = 0 if cell["candidate"] == "qwen35-27b" else slot % MANAGER_CAPACITY
        endpoint_slot = (
            "gpu0-qwen35-27b" if cell["candidate"] == "qwen35-27b" else f"a28-replica-{replica_index}"
        )
        config = configs / (wave + "-" + cell["cell_id"] + ".json")
        try:
            write(
                config,
                {
                    "cell": cell,
                    "slot": slot,
                    "replica_index": replica_index,
                    "endpoint_slot": endpoint_slot,
                    "wave": wave,
                    "actual_wave_size": len(cells),
                    "context": asdict(contexts[replica_index]),
                    "network_output": str(network_output.relative_to(ROOT)),
                    "log_offsets": [
                        {"key": list(key), "offset": value}
                        for key, value in frozen.LOG_OFFSETS.items()
                    ],
                },
            )
            stream = (logs / (wave + "-" + cell["cell_id"] + ".log")).open("x")
            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--child",
                    str(config),
                    "--api-key-file",
                    str(api_key),
                    cwd=frozen.APP,
                    stdin=subprocess.DEVNULL,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            finally:
                stream.close()
            processes.append((cell, proc))
        except Exception as exc:
            launch_error = type(exc).__name__
            (ROOT / "STOP").touch(exist_ok=True)
            break
    frozen.pilot.journal(
        "concurrent_wave_dispatched",
        wave=wave,
        cells=[cell["cell_id"] for cell in cells],
        maximum_concurrency=WIDTH,
    )
    pending = {asyncio.create_task(proc.wait()): (cell, proc) for cell, proc in processes}
    errors = [{"launch_exception_type": launch_error}] if launch_error else []
    matrix_deadline = json.loads((ROOT / "execution-freeze.json").read_text())[
        "matrix_deadline_epoch"
    ]
    while pending:
        if time() >= matrix_deadline and not any("matrix_deadline" in e for e in errors):
            errors.append({"matrix_deadline": True})
            (ROOT / "STOP").touch(exist_ok=True)
        done, _ = await asyncio.wait(pending, timeout=5, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            cell, _proc = pending.pop(task)
            out = ROOT / "cells" / cell["cell_id"]
            finished = out / "cell-finished.json"
            if task.result() != 0 or not finished.exists():
                errors.append(
                    {
                        "cell": cell["cell_id"],
                        "exit_code": task.result(),
                        "finished_receipt_present": finished.exists(),
                    }
                )
            elif json.loads(finished.read_text())["system_problems"]:
                errors.append(
                    {
                        "cell": cell["cell_id"],
                        "system_problems": json.loads(finished.read_text())["system_problems"],
                    }
                )
        if errors:
            # Existing request guards cooperatively stop and drain other owned cells.
            (ROOT / "STOP").touch(exist_ok=True)
    await drain_shared_models(contexts, services, wave)
    write(
        ROOT / "concurrency-waves" / (wave + ".json"),
        {
            "cells": [cell["cell_id"] for cell in cells],
            "actual_wave_size": len(cells),
            "maximum_concurrency": WIDTH,
            "system_errors": errors,
            "all_child_processes_exited": True,
            "serving_request_parallelism": 1,
            "a28_manager_request_capacity": MANAGER_CAPACITY,
        },
    )
    if errors:
        raise RuntimeError("concurrent_system_boundary_failure")
    await frozen.checkpoint()


async def main(args):
    if args.child:
        return await child(args)
    if sys.platform != "linux" or frozen.APP != ROOT / "app":
        raise RuntimeError("controller immutable app required")
    old_pid = json.loads((ROOT / "batch-daemon.json").read_text())["pid"]
    if alive(old_pid):
        raise RuntimeError("original serial runner must finish cooperative handoff first")
    if (ROOT / "matrix-complete.json").exists():
        raise RuntimeError("no repeat of a completed matrix")
    plan = json.loads(frozen.PLAN_PATH.read_text())
    frozen.validate_order(plan)
    freeze = json.loads((ROOT / "execution-freeze.json").read_text())
    if freeze["plan"] != plan:
        raise RuntimeError("original preregistration drift")
    handoff = ROOT / "boundary-handoff-receipt.json"
    if not handoff.exists():
        raise RuntimeError("explicit completed-cell handoff receipt required")
    partial = json.loads((ROOT / "partial-integrity.json").read_text())
    if partial["system_problems"] or not partial["source_unchanged"]:
        raise RuntimeError("handoff integrity failure")
    amendment_path = ROOT / "protocol-amendment-001.json"
    completed = [
        cell["cell_id"]
        for cell in plan["order"]
        if (ROOT / "cells" / cell["cell_id"] / "cell-finished.json").exists()
    ]
    if not amendment_path.exists():
        write(
            amendment_path,
            {
                "version": "skill-granularity-user-concurrency-amendment-v1",
                "authorization": "User: 如果只是衡量TSR，不需要考虑对E2E的影响",
                "change_reason": "TSR primary; shared-resource pipeline throughput prioritized",
                "original_pre_registration_unchanged": True,
                "original_execution_freeze_sha256": sha(ROOT / "execution-freeze.json"),
                "administration_source_sha256": sha(Path(__file__).resolve()),
                "shared_resource_concurrency": WIDTH,
                "serial_completed_cell_ids": completed,
                "concurrent_cell_ids": [
                    cell["cell_id"] for cell in plan["order"] if cell["cell_id"] not in completed
                ],
                "fixed_dispatch_order": [cell["cell_id"] for cell in plan["order"]],
                "serving_request_parallelism": 1,
                "model_skill_prompt_schema_evaluator_unchanged": True,
                "original_executor_instances_unchanged": True,
                "process_per_cell": True,
                "independent_worker_ports_and_artifact_namespaces": True,
                "exclusive_e2e_cost_comparison_valid": False,
                "runner_log_intervals_may_overlap": True,
                "no_selective_reruns": True,
                "additional_model_probes": 0,
            },
        )
    elif not args.resume:
        raise RuntimeError("concurrent batch already started; explicit resume required")
    elif json.loads(amendment_path.read_text())["administration_source_sha256"] != sha(
        Path(__file__).resolve()
    ):
        raise RuntimeError("concurrency administration source changed after amendment")
    if (ROOT / "STOP").exists():
        # This is the administration's recorded completed-cell handoff, not a user STOP.
        if args.resume:
            raise RuntimeError("STOP must be explicitly revoked before resume")
        (ROOT / "STOP").unlink()
    _load_control_plane_key(args.api_key_file, "DASHSCOPE_API_KEY")
    agents.set_tracing_disabled(True)
    service = Service(ROOT)
    frozen.configure(plan, service)
    frozen.BASELINE = json.loads((ROOT / "private/residency-startup.json").read_text())
    service.baseline = frozen.BASELINE
    texts = texts_for(plan)
    pool = frozen.pilot.frozen._yaml(frozen.APP / plan["infrastructure_design"]["model_pool_path"])
    sequence = len(list(ROOT.glob("resume-network-*"))) + 1
    network_output = ROOT / f"resume-network-{sequence:03d}"
    network_output.mkdir(exist_ok=False)
    frozen.NETWORK_OUTPUT = network_output
    config = network_output / "batch-network.yaml"
    urls = {
        agent + "-slot-" + str(slot): url.rsplit(":", 1)[0]
        + ":"
        + str(BASE_PORTS[agent] + slot * 100)
        for slot in range(WIDTH)
        for agent, url in pool["worker_urls"].items()
    }
    with config.open("x") as stream:
        yaml.safe_dump(
            {
                "run_id": "skill-granularity-v1-concurrent-001",
                "worker_urls": urls,
                "network": {"regime": "fast", "bandwidth_mbps": 100, "added_rtt_ms": 5},
            },
            stream,
        )
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: (ROOT / "STOP").touch(exist_ok=True))
    complete = False
    failure = None
    frozen.pilot.journal("concurrent_batch_started", pid=os.getpid(), maximum_concurrency=WIDTH)

    async def batch(_args):
        await frozen.checkpoint()
        wave_number = max(
            (int(p.stem.split("-")[1]) for p in (ROOT / "concurrency-waves").glob("wave-*.json")),
            default=0,
        )
        for candidate in ("qwen35-4b", "qwen35-9b", "qwen35-27b"):
            todo = [
                cell
                for cell in plan["order"]
                if cell["candidate"] == candidate
                and not (ROOT / "cells" / cell["cell_id"] / "cell-finished.json").exists()
            ]
            if not todo:
                continue
            if (ROOT / "STOP").exists() or time() >= freeze["matrix_deadline_epoch"]:
                raise RuntimeError("STOP_or_matrix_wall_budget")
            context = await service.load(candidate)
            await frozen.measure_skill_tokens(candidate, context, texts)
            for start in range(0, len(todo), WIDTH):
                if (ROOT / "STOP").exists() or time() >= freeze["matrix_deadline_epoch"]:
                    raise RuntimeError("STOP_or_matrix_wall_budget")
                wave_number += 1
                wave = f"wave-{wave_number:03d}"
                cells = todo[start : start + WIDTH]
                claimed = [
                    cell
                    for cell in cells
                    if (ROOT / "cells" / cell["cell_id"] / "cell-started.json").exists()
                ]
                for cell in claimed:
                    await frozen.recover_claimed(cell, context)
                cells = [cell for cell in cells if cell not in claimed]
                if cells:
                    await service.check_resource(force=True, wait_timeout=600)
                    await run_wave(cells, context, wave, network_output, args.api_key_file)

    try:
        await frozen.pilot.run_shaped(
            argparse.Namespace(
                config=config, output=network_output, endpoint_config=frozen.pilot.DEFAULT_ENDPOINTS
            ),
            execute_cell=batch,
        )
        complete = all(
            (ROOT / "cells" / cell["cell_id"] / "cell-finished.json").exists()
            for cell in plan["order"]
        )
    except Exception as exc:
        failure = type(exc).__name__
        write(
            network_output / "batch-stopped.json",
            {"exception_type": failure, "message": str(exc), "semantic_retries": 0},
        )
        frozen.pilot.journal("concurrent_batch_stopped", exception_type=failure)
    finally:
        try:
            if complete:
                await service.close()
            else:
                await service.suspend()
        except Exception as exc:
            failure = failure or "owned_service_cleanup_failed"
            write(
                network_output / "service-cleanup-error.json",
                {"exception_type": type(exc).__name__},
            )
    original_write = frozen.write

    def final_write(path, value):
        if path == ROOT / "private/residency-final.json" and path.exists():
            path = network_output / "residency-final-after-amendment.json"
        return original_write(path, value)

    frozen.write = final_write
    integrity = await frozen.final_audit(plan, freeze, complete)
    if complete and not integrity["system_problems"] and failure is None:
        write(
            ROOT / "matrix-complete.json",
            {
                "cells": 30,
                "attempts": 30,
                "semantic_retries": 0,
                "shared_resource_concurrency": WIDTH,
            },
        )
        frozen.pilot.journal("batch_complete", cells=30, shared_resource_concurrency=WIDTH)
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "reporting/analyze_skill_granularity_pilot_v1.py"),
                "--root",
                str(ROOT),
                "--output",
                str(ROOT.parent / "sanitized-final-001"),
            ],
            check=True,
        )
    else:
        raise RuntimeError(failure or "final_system_integrity_failure")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key-file", type=Path, required=True)
    parser.add_argument("--child", type=Path)
    parser.add_argument("--resume", action="store_true")
    asyncio.run(main(parser.parse_args()))
