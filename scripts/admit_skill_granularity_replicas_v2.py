"""One-time, non-generating A28 replica admission before the v2 matrix."""

import argparse
import asyncio
import importlib
import json
from pathlib import Path

ROOT = Path("/home/super/xiaoming/skill-granularity-pilot-v2/run-001")
RESERVE_KIB = 8 * 1024**2


async def main():
    modules = [importlib.import_module(f"skill_granularity_service_v2_slot{i}") for i in range(3)]
    services = []
    observations = []
    try:
        for module in modules:
            if not (module.ROOT / "a28-service.json").exists():
                await asyncio.to_thread(module.bootstrap)
            services.append(module.Service())
        for index, (module, service) in enumerate(zip(modules, services, strict=True)):
            model = module.PINNED["qwen35-9b"]["model"]
            await asyncio.to_thread(
                module.api_json,
                module.URL + "/api/generate",
                {
                    "model": model,
                    "prompt": "",
                    "stream": False,
                    "keep_alive": -1,
                    "think": False,
                    "options": {"num_ctx": 32768, "num_predict": 0},
                },
                240,
            )
            service.current = "qwen35-9b"
            runner = await asyncio.to_thread(module.remote, "runner")
            argv = runner["argv"]
            slots = int(argv[argv.index("-np") + 1])
            context = int(argv[argv.index("-c") + 1])
            resident = await asyncio.to_thread(module.api_json, module.URL + "/api/ps")
            memory = await asyncio.to_thread(module.remote, "memory")
            observation = {
                "replica": index,
                "runner_pid": runner["pid"],
                "runner_slots": slots,
                "runner_context": context,
                "resident_digest": resident["models"][0]["digest"],
                "resident_context": resident["models"][0]["context_length"],
                "a28_mem_available_kib": memory["MemAvailable"],
            }
            observations.append(observation)
            if (slots, context, observation["resident_context"]) != (1, 32768, 32768):
                raise RuntimeError("replica_slot_or_context_mismatch")
            if observation["resident_digest"] != module.PINNED["qwen35-9b"]["digest"]:
                raise RuntimeError("replica_weight_mismatch")
            if memory["MemAvailable"] < RESERVE_KIB:
                break
        admitted = len(observations)
        if observations[-1]["a28_mem_available_kib"] < RESERVE_KIB:
            admitted -= 1
        if admitted < 2:
            raise RuntimeError("two_replica_memory_reserve_unavailable")
        for index, (module, service) in enumerate(zip(modules, services, strict=True)):
            if index >= admitted:
                await service.close()
            else:
                await service.suspend()
        receipt = {
            "version": "skill-granularity-replica-admission-v2",
            "serving": "independent Ollama 0.34.0 one-slot replicas",
            "replicas_admitted": admitted,
            "max_concurrent_workflow_cells": 3,
            "manager_request_capacity": admitted,
            "manager_context_per_replica": 32768,
            "qwen35_9b_non_generating_admission": observations,
            "minimum_a28_mem_available_kib": RESERVE_KIB,
            "executor_unchanged": True,
            "formal_cells_started": 0,
        }
        path = ROOT / "replica-admission.json"
        with path.open("x") as stream:
            json.dump(receipt, stream, indent=2)
        print(json.dumps(receipt))
    except BaseException:
        for service in reversed(services):
            try:
                if not (service.root / "owned-service-cleanup.json").exists():
                    await service.close()
            except BaseException:
                pass
        raise


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    asyncio.run(main())
