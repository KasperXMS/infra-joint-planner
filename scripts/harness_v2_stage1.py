# pyright: reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportMissingTypeArgument=false, reportMissingParameterType=false
"""Continuous Harness v2 H1 blind requalification on six frozen tasks.

This administration layer reuses the frozen task loader, SDK roles, context
preflight, request quotas, Worker preparation, evaluator and Physical Scheduler.
It never retries a claimed model attempt. Raw evidence remains on the controller.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import signal
import sys
from dataclasses import asdict, replace
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
from typing import Any, cast

import lightweight_planner_pilot_v1 as pilot
import yaml
from multiscale_planner_context_v1 import MultiscaleContextConfig, MultiscaleContextPreflight
from sdk_native_infra_preliminary_v1_3 import _load_control_plane_key

ROOT = Path("/home/super/xiaoming/harness-v2-baseline-requalification/run-001")
STAGE1 = ROOT / "stage1-attempt-002"
APP = ROOT / "app"
SELECTION = Path("/home/super/xiaoming/large-scale-cost-guidance-v1/preparation/task-freeze-002")
EDGE_APP = "/mnt/ssd/harness-v2-baseline-requalification/run-001/app"
EDGE_ROOT = Path("/mnt/ssd/harness-v2-baseline-requalification/run-001")
PORTS = {"A4": 63004, "A5": 63005, "A28": 63028, "strong-4090": 63112}
STAGE0 = ROOT / "stage0-private.json"
H1 = "configs/experiments/harness-v2-requalification-h1.yaml"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def configure() -> tuple[dict, dict, dict]:
    if sys.platform != "linux" or Path(__file__).resolve().parents[1] != APP:
        raise RuntimeError("isolated controller app required")
    if not all(0 < port < 65536 for port in PORTS.values()):
        raise RuntimeError("Worker port is outside the TCP port range")
    stage0 = json.loads(STAGE0.read_text())
    for name, expected in stage0["source_sha256"].items():
        if sha(APP / name) != expected:
            raise RuntimeError(f"Stage-0 source drift: {name}")
    if sha(SELECTION / "manifest.json") != stage0["task_manifest_sha256"]:
        raise RuntimeError("task freeze drift")
    original = json.loads(
        (APP / "configs/experiments/lightweight-planner-competence-v1.json").read_text()
    )
    expected = [
        (task["family"], task["position"], task["source_task_id"])
        for task in stage0["task_selection"]
    ]
    actual = [
        (task["family"], task["position"], task["source_task_id"])
        for task in json.loads((SELECTION / "manifest.json").read_text())["tasks"]
        if task["position"] in (1, 2)
    ]
    if actual != expected or len(original["tasks"]) != 6:
        raise RuntimeError("six-task selection drift")
    pool = yaml.safe_load((APP / original["infrastructure_design"]["model_pool_path"]).read_text())
    pilot.ROOT = ROOT
    pilot.APP = APP
    pilot.SELECTION = SELECTION
    pilot.EDGE_ROOT = EDGE_ROOT
    pilot.ARTIFACT_NAMESPACE = "harness-v2-baseline-requalification/run-001-attempt-002"
    pilot.RUN_PREFIX = "harness-v2-h1-002"
    pilot.PORTS = PORTS
    pilot.WORKER_APPS = {
        name: str(APP if host is None else EDGE_APP) for name, host in pilot.HOSTS.items()
    }
    pilot.OllamaManagerContextPreflight = MultiscaleContextPreflight
    pilot.protected_hashes = lambda: {
        str(SELECTION / "manifest.json"): sha(SELECTION / "manifest.json"),
    }
    return stage0, original, pool


def context_from_residency(stage0: dict, residency: dict) -> MultiscaleContextConfig:
    instance = residency["strong-4090"]["instances"][0]
    command = instance["runner"]["command"]
    port = command[command.index("--port") + 1]
    model_blob = Path(command[command.index("--model") + 1]).name
    if model_blob != "sha256-f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d":
        raise RuntimeError("GPU0 model blob drift")
    service = stage0["services"]["strong-4090-gpu0"]
    return MultiscaleContextConfig(
        model="qwen35-27b-resident-32k-v1",
        digest=service["digest"],
        model_blob=model_blob,
        template_sha256=service["template_sha256"],
        ollama_url="http://127.0.0.1:11436",
        runner_url=f"http://127.0.0.1:{port}",
        renderer="qwen3.8",
        parser="qwen3.5",
        disable_thinking=True,
    )


def protocol(original: dict) -> dict:
    p = {**original, "infrastructure_design": dict(original["infrastructure_design"])}
    p["infrastructure_design"]["frozen_harness_path"] = H1
    p["groups"] = {
        "B0": {"manager_model": "qwen3.8-max", "skills": None},
        "L1": {
            "manager_model": "qwen35-27b-resident-32k-v1",
            "skills": None,
            "request_extra_body": {"reasoning_effort": "none"},
        },
        "L2": {
            "manager_model": "qwen35-27b-resident-32k-v1",
            "skills": None,
            "request_extra_body": {"reasoning_effort": "none"},
        },
    }
    p["order"] = [
        {
            "cell_id": f"H1-{i:02d}-{group}",
            "task_index": i,
            "family": task["family"],
            "position": task["position"],
            "group": group,
        }
        for i, task in enumerate(original["tasks"], start=1)
        for group in ("L1", "L2", "B0")
    ]
    return p


def force_manager_sampling() -> None:
    original = pilot.role_isolated_sdk

    def roles(*args, **kwargs):
        result = cast(Any, original(*args, **kwargs))
        base = result.Agent

        def make(**agent_kwargs):
            if agent_kwargs["name"] == "manager":
                agent_kwargs["model_settings"] = replace(
                    agent_kwargs["model_settings"],
                    max_tokens=2048,
                    temperature=1,
                    top_p=0.95,
                )
            return base(**agent_kwargs)

        return SimpleNamespace(**{**vars(result), "Agent": make})

    pilot.role_isolated_sdk = roles


async def run_cell(cell: dict, p: dict, pool: dict, baseline: dict) -> dict:
    out = STAGE1 / "cells" / cell["cell_id"]
    out.mkdir(parents=True, exist_ok=False)
    run_id = f"{pilot.RUN_PREFIX}-{cell['cell_id']}"
    stores = {
        agent: str(
            (Path("/home/super") if host is None else Path("/mnt/ssd"))
            / "heterogeneous-v1/artifacts"
            / pilot.ARTIFACT_NAMESPACE
            / cell["cell_id"]
            / agent
        )
        for agent, host in pilot.HOSTS.items()
    }
    urls = {
        agent: url.rsplit(":", 1)[0] + ":" + str(PORTS[agent])
        for agent, url in pool["worker_urls"].items()
    }
    config = {
        "run_id": run_id,
        "cell_id": cell["cell_id"],
        "worker_urls": urls,
        "fresh_worker_stores": stores,
        "network": {"regime": "fast", "bandwidth_mbps": 100, "added_rtt_ms": 5},
    }
    write(out / "claim.json", {"cell": cell, "run_id": run_id, "no_retry": True})
    starts = {}
    cleanup = None
    started = monotonic()
    try:
        for agent in pilot.HOSTS:
            original = pilot.frozen._yaml(
                APP
                / "configs/experiments/workers/blind-3family-video-v1.3"
                / f"worker-{agent.lower()}.yaml"
            )
            worker = pilot.worker_config(
                {**pool, "worker_urls": urls}, original, agent, Path(stores[agent])
            )
            path = ROOT / "worker-configs" / f"{run_id}-{agent}.yaml"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x") as stream:
                yaml.safe_dump(worker.model_dump(mode="json"), stream, sort_keys=False)
            starts[agent] = await pilot.start_owned_worker(agent, path, stores[agent], run_id)
            write(out / "worker-starts" / (agent + ".json"), starts[agent])
        await pilot.states(urls, fresh=True)
        await pilot.execute(cell, out, config, p)
    finally:
        cleanup = await pilot.cleanup_workers(starts, urls, out, baseline)
    result_path = out / "runs" / run_id / "result.json"
    result = json.loads(result_path.read_text()) if result_path.exists() else None
    system = []
    if not cleanup["drained"] or not cleanup["verified_exited"] or cleanup["errors"]:
        system.append("worker_cleanup_failed")
    if result is None and not (out / "administrative-outcome.json").exists():
        system.append("missing_result_and_administrative_outcome")
    summary = {
        "cell": cell,
        "run_id": run_id,
        "wall_ms": (monotonic() - started) * 1000,
        "completion": None if result is None else result["execution_completed"],
        "score": None
        if result is None or result.get("evaluation") is None
        else result["evaluation"]["benchmark_score"],
        "failure": None if result is None else result.get("failure"),
        "system_problems": system,
        "worker_cleanup": cleanup,
    }
    write(out / "cell-finished.json", summary)
    if system:
        raise RuntimeError("system boundary: " + ",".join(system))
    return summary


async def main(key: Path) -> None:
    stage0, original, pool = configure()
    _load_control_plane_key(key, "DASHSCOPE_API_KEY")
    baseline = await pilot.residency()
    pilot.CONTEXT = context_from_residency(stage0, baseline)
    force_manager_sampling()
    p = protocol(original)
    freeze = ROOT / "execution-freeze.json"
    if freeze.exists():
        raise RuntimeError("Stage 1 already claimed; no automatic model reruns")
    write(
        freeze,
        {
            "harness": "H1 SDK-native v2, bridge disabled",
            "stage0_sha256": sha(STAGE0),
            "h1_manifest_sha256": sha(APP / H1),
            "task_manifest_sha256": sha(SELECTION / "manifest.json"),
            "order": p["order"],
            "context": asdict(pilot.CONTEXT),
            "baseline_residency": baseline,
            "max_attempts": 18,
            "task_timeout_seconds": 3600,
            "no_selective_reruns": True,
        },
    )
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: (ROOT / "STOP").touch(exist_ok=True))
    STAGE1.mkdir(parents=True, exist_ok=False)
    network_path = STAGE1 / "batch-network.yaml"
    network_path.write_text(
        yaml.safe_dump(
            {
                "run_id": "harness-v2-stage1-fast",
                "worker_urls": {
                    agent: url.rsplit(":", 1)[0] + ":" + str(PORTS[agent])
                    for agent, url in pool["worker_urls"].items()
                },
                "network": {"regime": "fast", "bandwidth_mbps": 100, "added_rtt_ms": 5},
            }
        )
    )

    rows = []

    async def all_cells(_args: argparse.Namespace) -> None:
        for cell in p["order"]:
            if (ROOT / "STOP").exists():
                raise RuntimeError("STOP before next cell")
            row = await asyncio.wait_for(run_cell(cell, p, pool, baseline), timeout=5100)
            rows.append(row)
            with (STAGE1 / "journal.jsonl").open("a") as stream:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            print(
                json.dumps(
                    {
                        "cell": cell["cell_id"],
                        "completion": row["completion"],
                        "score": row["score"],
                        "finished": len(rows),
                    }
                ),
                flush=True,
            )

    await pilot.run_shaped(
        argparse.Namespace(
            config=network_path, output=STAGE1, endpoint_config=pilot.DEFAULT_ENDPOINTS
        ),
        execute_cell=all_cells,
    )
    write(STAGE1 / "complete.json", {"cells": len(rows), "system_problems": []})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key-file", type=Path, required=True)
    asyncio.run(main(parser.parse_args().api_key_file))
