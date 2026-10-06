"""Worker-only readiness for execution003; zero task/model/Planner/tc calls."""

from __future__ import annotations

import asyncio
import json
from contextlib import AsyncExitStack
from pathlib import Path

import large_scale_resident_queue_v1 as frozen
import yaml
from large_scale_resident_cardinality_patch_v1 import APP_NAME, start_patched_worker
from large_scale_resident_private_evidence_v1 import assert_inactive
from prepare_resident_worker_v1 import worker_config
from resident_model_pool_attestation_v1 import compare_residency
from resource_blind_live_validation_v1 import _clients
from run_predecision_matrix_v1 import HOSTS, stop_worker, write_new

from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.core.state import EnvironmentSpec
from infra_joint.infrastructure.validation import validate_worker_surfaces
from infra_joint.operators.catalog import build_operator_catalog


async def run() -> None:
    frozen.require_remote()
    if frozen.APP.name != APP_NAME:
        raise RuntimeError("readiness must import the exact execution003 archive")
    root = frozen.ROOT
    assert_inactive(root)
    journal = (root / "phase1-attempts.jsonl").read_bytes()
    output = root / "readiness/worker-surface-003"
    output.mkdir(parents=True, exist_ok=False)
    pool = frozen.frozen._yaml(frozen.POOL_CONFIG)
    environment = EnvironmentSpec.model_validate(pool["environment"])
    registry = build_operator_catalog()
    operations = tuple(frozen.frozen._yaml(frozen.HARNESS)["available_operations"])
    capability = build_static_capability_contract(environment, registry, operations)
    frozen.frozen.validate_harness(frozen.frozen.load_harness(frozen.HARNESS), environment,
                                  capability, operations)
    before = frozen.residency()
    write_new(output / "residency-before.json", before)
    pids = {}
    try:
        for agent in HOSTS:
            prefix = Path("/home/super" if agent == "strong-4090" else "/mnt/ssd")
            store = prefix / "heterogeneous-v1/artifacts" / root.name / "surface-003" / agent
            original = frozen.APP / "configs/experiments/workers/blind-3family-video-v1.3" / (
                f"worker-{agent.lower()}.yaml")
            worker = worker_config(pool, frozen.frozen._yaml(original), agent, store)
            config = output / f"worker-surface-003-{agent}.yaml"
            with config.open("x", encoding="utf-8") as stream:
                yaml.safe_dump(worker.model_dump(mode="json"), stream, sort_keys=False)
            pids[agent] = start_patched_worker(root, config, agent, str(store))
            write_new(output / "worker-starts" / f"{agent}.json", {"pid": pids[agent]})
        await frozen.worker_states(pool, clean=True)
        async with AsyncExitStack() as stack:
            clients = await _clients(stack, pool["worker_urls"], timeout_seconds=10)
            states = await validate_worker_surfaces(environment, registry, clients)
        write_new(output / "worker-states.json", {
            agent: state.model_dump(mode="json") for agent, state in states.items()})
        write_new(output / "static-capability.json", capability.model_dump(mode="json"))
        write_new(output / "validation.json", {
            "passed": True, "workers": len(states), "deployments": len(environment.deployments),
            "capability_sha256": frozen.frozen._capability_sha256(capability),
            "execution_app": str(frozen.APP), "operator_contract_digests_verified": True,
            "fresh_empty_stores": True, "planner_calls": 0, "benchmark_cells": 0,
            "model_inference_calls": 0, "tc_shaping": 0,
        })
    finally:
        exited, errors = {}, {}
        for agent, pid in pids.items():
            try:
                stop_worker(root, agent, pid)
                for _ in range(30):
                    code = ("import json; from pathlib import Path; "
                            f"p=Path('/proc/{pid}/cmdline'); "
                            "v=p.read_bytes().decode() if p.exists() else ''; "
                            f"assert not v or {root.name!r} in v; "
                            "print(json.dumps({'live':bool(v)}))")
                    if not frozen.remote_json(agent, code)["live"]:
                        exited[agent] = True
                        break
                    await asyncio.sleep(1)
                else:
                    errors[agent] = "owned_worker_still_live"
            except Exception as error:
                errors[agent] = type(error).__name__
        after = frozen.residency()
        write_new(output / "residency-after.json", after)
        for agent in HOSTS:
            compare_residency(before[agent], after[agent])
            interval = frozen.remote_json(agent,
                "import json; from resident_model_pool_attestation_v1 import audit_log_interval; "
                f"print(json.dumps(audit_log_interval({before[agent]!r},{after[agent]!r})))")
            write_new(output / "residency-log-intervals" / f"{agent}.json", interval)
        unchanged = (root / "phase1-attempts.jsonl").read_bytes() == journal
        passed = len(exited) == 4 and not errors and unchanged
        write_new(output / "shutdown-verified.json", {
            "passed": passed, "owned_processes": pids, "exited": exited, "errors": errors,
            "journal_unchanged": unchanged, "models_kept_resident": True,
        })
        if not passed:
            raise RuntimeError("readiness cleanup/journal verification failed")
    print(json.dumps({"passed": True, "workers": 4, "deployments": 5,
                      "capability_sha256": frozen.frozen._capability_sha256(capability)}))


if __name__ == "__main__":
    asyncio.run(run())
