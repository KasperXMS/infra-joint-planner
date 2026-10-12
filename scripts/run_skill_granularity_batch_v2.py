"""One continuous 30-cell v2 batch with three workflows and two real A28 slots."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from time import time

import agents
import yaml

import run_skill_granularity_concurrent_v2 as concurrent
from sdk_native_infra_preliminary_v1_3 import _load_control_plane_key

frozen = concurrent.frozen
ROOT = frozen.ROOT
write = frozen.write


async def main(args):
    if sys.platform != "linux" or frozen.APP != ROOT / "app":
        raise RuntimeError("v2 controller app path changed")
    if (ROOT / "matrix-complete.json").exists():
        raise RuntimeError("completed matrix cannot be rerun")
    plan = json.loads(frozen.PLAN_PATH.read_text())
    frozen.validate_order(plan)
    admission = json.loads((ROOT / "replica-admission.json").read_text())
    if admission["replicas_admitted"] != 2 or admission["manager_request_capacity"] != 2:
        raise RuntimeError("frozen two-replica admission missing")
    _load_control_plane_key(args.api_key_file, "DASHSCOPE_API_KEY")
    agents.set_tracing_disabled(True)
    services = [module.Service() for module in concurrent.SERVICE_MODULES]
    frozen.configure(plan, services[0])
    current_residency = await frozen.pilot.residency()
    for service in services:
        service.baseline = current_residency
    frozen.BASELINE = current_residency
    frozen.PORTS = dict(concurrent.BASE_PORTS)
    frozen.pilot.PORTS = frozen.PORTS
    freeze_path = ROOT / "execution-freeze.json"
    source = frozen.source_hashes()
    protected = frozen.protected_hashes()
    if freeze_path.exists():
        if not args.resume:
            raise RuntimeError("batch already started; resume untouched cells only")
        freeze = json.loads(freeze_path.read_text())
        if freeze["plan"] != plan or freeze["source_sha256"] != source or freeze["protected_sha256"] != protected:
            raise RuntimeError("frozen source, task, skill or history drift")
        original = json.loads((ROOT / "private/residency-startup.json").read_text())
        if any(
            a[k] != b[k]
            for node in original
            for a, b in zip(original[node]["instances"], current_residency[node]["instances"], strict=True)
            for k in ("server", "runner", "target")
        ):
            raise RuntimeError("Executor deployment changed")
        if (ROOT / "STOP").exists():
            raise RuntimeError("STOP requires explicit revocation")
    else:
        if args.resume:
            raise RuntimeError("resume requires existing freeze")
        freeze = {
            "version": "skill-granularity-execution-freeze-v2",
            "plan": plan,
            "ordered_cells": plan["order"],
            "source_sha256": source,
            "protected_sha256": protected,
            "replica_admission": admission,
            "maximum_attempts": 30,
            "no_selective_reruns": True,
            "matrix_deadline_epoch": time() + plan["matrix_wall_ceiling_seconds"],
        }
        write(freeze_path, freeze)
        write(ROOT / "private/residency-startup.json", current_residency)
    administration = ROOT / "administration/run_skill_granularity_batch_v2.py"
    administration.parent.mkdir(parents=True, exist_ok=True)
    if not administration.exists():
        shutil.copy2(Path(__file__), administration)
    if concurrent.sha(administration) != concurrent.sha(Path(__file__)):
        raise RuntimeError("administration source drift")
    amendment = ROOT / "protocol-amendment-001.json"
    if not amendment.exists():
        write(
            amendment,
            {
                "version": "skill-granularity-v2-replica-serving-protocol",
                "original_pre_registration_unchanged": True,
                "original_execution_freeze_sha256": concurrent.sha(freeze_path),
                "administration_source_sha256": concurrent.sha(administration),
                "serial_completed_cell_ids": [],
                "concurrent_cell_ids": [cell["cell_id"] for cell in plan["order"]],
                "fixed_dispatch_order": [cell["cell_id"] for cell in plan["order"]],
                "shared_resource_concurrency": 3,
                "a28_manager_request_capacity": 2,
                "serving_request_parallelism_per_replica": 1,
                "manager_http_timeout_seconds": 300,
                "replica_admission_sha256": concurrent.sha(ROOT / "replica-admission.json"),
                "same_tasks_skills_models_evaluator_executor": True,
                "no_selective_reruns": True,
            },
        )
    (ROOT / "manager-slot-locks").mkdir(exist_ok=True)
    texts = concurrent.texts_for(plan)
    pool = frozen.pilot.frozen._yaml(frozen.APP / plan["infrastructure_design"]["model_pool_path"])
    sequence = len(list(ROOT.glob("resume-network-*"))) + 1
    network_output = ROOT if not args.resume else ROOT / f"resume-network-{sequence:03d}"
    network_output.mkdir(exist_ok=True)
    frozen.NETWORK_OUTPUT = network_output
    config = network_output / "batch-network.yaml"
    urls = {
        agent + "-slot-" + str(slot): url.rsplit(":", 1)[0] + ":" + str(concurrent.BASE_PORTS[agent] + slot * 100)
        for slot in range(3)
        for agent, url in pool["worker_urls"].items()
    }
    if not config.exists():
        with config.open("x") as stream:
            yaml.safe_dump(
                {
                    "run_id": "skill-granularity-v2-concurrent-001",
                    "worker_urls": urls,
                    "network": {"regime": "fast", "bandwidth_mbps": 100, "added_rtt_ms": 5},
                },
                stream,
            )
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: (ROOT / "STOP").touch(exist_ok=True))
    complete = False
    failure = None
    frozen.pilot.journal("v2_batch_started", pid=os.getpid(), manager_request_capacity=2)

    async def batch(_args):
        await frozen.checkpoint()
        wave_number = len(list((ROOT / "concurrency-waves").glob("wave-*.json")))
        for candidate in plan["candidate_order"]:
            todo = [
                cell for cell in plan["order"]
                if cell["candidate"] == candidate
                and not (ROOT / "cells" / cell["cell_id"] / "cell-finished.json").exists()
            ]
            if not todo:
                continue
            if (ROOT / "STOP").exists() or time() >= freeze["matrix_deadline_epoch"]:
                raise RuntimeError("STOP_or_matrix_wall_budget")
            if candidate == "qwen35-27b":
                await services[1].suspend()
                contexts = [await services[0].load(candidate)]
                active = services[:1]
            else:
                contexts = [await service.load(candidate) for service in services]
                active = services
            await frozen.measure_skill_tokens(candidate, contexts[0], texts)
            for start in range(0, len(todo), 3):
                if (ROOT / "STOP").exists() or time() >= freeze["matrix_deadline_epoch"]:
                    raise RuntimeError("STOP_or_matrix_wall_budget")
                wave_number += 1
                wave = f"wave-{wave_number:03d}"
                cells = todo[start : start + 3]
                for cell in cells:
                    if (ROOT / "cells" / cell["cell_id"] / "cell-started.json").exists():
                        await frozen.recover_claimed(cell, contexts[0])
                cells = [
                    cell for cell in cells
                    if not (ROOT / "cells" / cell["cell_id"] / "cell-finished.json").exists()
                ]
                if cells:
                    await services[0].check_resource(force=True, wait_timeout=600)
                    await concurrent.run_wave(cells, contexts, active, wave, network_output, args.api_key_file)

    try:
        await frozen.pilot.run_shaped(
            argparse.Namespace(config=config, output=network_output, endpoint_config=frozen.pilot.DEFAULT_ENDPOINTS),
            execute_cell=batch,
        )
        complete = all((ROOT / "cells" / cell["cell_id"] / "cell-finished.json").exists() for cell in plan["order"])
    except Exception as exc:
        failure = type(exc).__name__
        write(network_output / "batch-stopped.json", {"exception_type": failure, "message": str(exc)})
        frozen.pilot.journal("v2_batch_stopped", exception_type=failure)
    finally:
        for service in services:
            try:
                if complete:
                    await service.close()
                else:
                    await service.suspend()
            except Exception as exc:
                failure = failure or "owned_service_cleanup_failed"
                write(network_output / f"service-cleanup-error-{service.root.name}.json", {"exception_type": type(exc).__name__})
    integrity = await frozen.final_audit(plan, freeze, complete)
    if complete and not integrity["system_problems"] and failure is None:
        write(ROOT / "matrix-complete.json", {"cells": 30, "attempts": 30, "semantic_retries": 0, "max_concurrent_cells": 3, "a28_manager_request_capacity": 2})
        subprocess.run(
            [sys.executable, str(ROOT / "reporting/analyze_skill_granularity_pilot_v2.py"), "--root", str(ROOT), "--output", str(ROOT.parent / "sanitized-final-001")],
            check=True,
        )
    else:
        raise RuntimeError(failure or "final_system_integrity_failure")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key-file", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    asyncio.run(main(parser.parse_args()))
