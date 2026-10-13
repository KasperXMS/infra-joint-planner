# pyright: reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportMissingTypeArgument=false, reportMissingParameterType=false
"""One continuous 36-cell H1 Blind/Raw-Aware/Ledger comparison.

The only method adaptation is selecting the historical native runtime variant and
profile visibility. Task, model, scheduler, evaluator and tool semantics are reused.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import socket
import subprocess
import time
from pathlib import Path
from time import monotonic
from typing import Any
from urllib.parse import urlparse

import harness_v2_anchor_freeze as anchors
import harness_v2_stage1 as stage1
import lightweight_planner_pilot_v1 as pilot
import yaml
from lightweight_planner_tc_v1 import batch_remote
from sdk_native_infra_preliminary_v1_3 import _load_control_plane_key

from infra_joint.control.contracts import ProfileVisibility
from infra_joint.control.method_usage import MeasuredLedgerRuntime
from infra_joint.control.native_agents import OpenAIAgentsNativeRuntime
from infra_joint.heterogeneous.traffic_control import (
    SshCommandRunner,
    TcEndpoint,
    TcRegime,
    _validate_restorable_root,
    build_tc_command_plan,
)

ROOT = stage1.ROOT / "stage2"
APP = stage1.APP
PORTS = {"A4": 63204, "A5": 63205, "A28": 63228, "strong-4090": 63312}
CALIBRATION_PORT = 63399
NETWORKS = {
    "slow": {"regime": "slow", "bandwidth_mbps": 3, "added_rtt_ms": 50},
    "fast": {"regime": "fast", "bandwidth_mbps": 100, "added_rtt_ms": 5},
}
METHODS = ("BLIND", "AWARE", "LEDGER")
ANCHOR_MANIFEST = ROOT / "anchor-freeze" / "manifest.json"
BASE_RUNTIME = OpenAIAgentsNativeRuntime
BASE_LINK = pilot.LinkSpec
BASE_PRICES = pilot.verified_prices


class RawAwareRuntime(BASE_RUNTIME):
    """Old Raw-Aware profile exposure, with unchanged Manager instructions."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs["predecision_profiles"] = True
        super().__init__(**kwargs)

    async def run(self, *args: Any, **kwargs: Any) -> Any:
        kwargs["profile_visibility"] = ProfileVisibility.AWARE
        return await super().run(*args, **kwargs)


def configure() -> tuple[dict, dict, dict, dict]:
    if not (stage1.STAGE1 / "complete.json").exists():
        raise RuntimeError("Stage 1 engineering qualification is incomplete")
    stage0, original, pool = stage1.configure()
    if not all(0 < port < 65536 for port in PORTS.values()):
        raise RuntimeError("Stage 2 Worker port out of range")
    cache, regenerated = anchors.load()
    frozen = json.loads(ANCHOR_MANIFEST.read_text())
    if regenerated != frozen:
        raise RuntimeError("Anchor task, evaluator or source freeze drift")
    by_key = {(row["family"], row["position"]): cache[row["label"]] for row in frozen["tasks"]}
    pilot.ROOT = ROOT
    pilot.SELECTION = ANCHOR_MANIFEST.parent
    pilot.EDGE_ROOT = Path("/mnt/ssd/harness-v2-baseline-requalification/run-001/stage2")
    pilot.ARTIFACT_NAMESPACE = "harness-v2-baseline-requalification/run-001/stage2"
    pilot.RUN_PREFIX = "harness-v2-stage2-001"
    pilot.PORTS = PORTS

    def frozen_task(
        _selection: Path, _manifest: dict[str, Any], family: str, position: int
    ) -> tuple[Any, dict[str, Any]]:
        return by_key[(family, position)]

    def verified_prices(*_args: Any) -> Any:
        return BASE_PRICES(stage1.SELECTION.parent.parent, APP)

    pilot.frozen_task = frozen_task
    pilot.verified_prices = verified_prices
    stage1.force_manager_sampling()
    return stage0, original, pool, frozen


def protocol(original: dict, anchor: dict) -> dict:
    result = {**original, "infrastructure_design": dict(original["infrastructure_design"])}
    result["infrastructure_design"]["frozen_harness_path"] = stage1.H1
    result["tasks"] = anchor["tasks"]
    result["groups"] = {
        method: {
            "manager_model": "qwen35-27b-resident-32k-v1",
            "request_extra_body": {"reasoning_effort": "none"},
        }
        for method in METHODS
    }
    ordered = []
    for network in ("slow", "fast"):
        for index, task in enumerate(anchor["tasks"], start=1):
            for trial in (1, 2):
                offset = (index - 1 + trial - 1) % len(METHODS)
                methods = METHODS[offset:] + METHODS[:offset]
                for method in methods:
                    ordered.append(
                        {
                            "cell_id": f"S2-{network}-{index}-{trial}-{method}",
                            "task_index": index,
                            "family": task["family"],
                            "position": task["position"],
                            "source_task_id": task["source_task_id"],
                            "network": network,
                            "trial": trial,
                            "method": method,
                            "group": method,
                        }
                    )
    if len(ordered) != 36 or len({c["cell_id"] for c in ordered}) != 36:
        raise RuntimeError("36-cell matrix construction failed")
    result["order"] = ordered
    return result


async def network_block(regime: str, worker_urls: dict, execute: Any) -> None:
    endpoints = tuple(
        TcEndpoint.model_validate(row)
        for row in yaml.safe_load(pilot.DEFAULT_ENDPOINTS.read_text())["tc_endpoints"]
    )
    ports = tuple(sorted({urlparse(url).port for url in worker_urls.values()} | {CALIBRATION_PORT}))
    network = NETWORKS[regime]
    shape = TcRegime(
        configuration_id=f"harness-v2-stage2-{regime}",
        bandwidth_mbps=float(network["bandwidth_mbps"]),
        added_rtt_ms=float(network["added_rtt_ms"]),
        worker_ports=ports,
    )
    plans = [build_tc_command_plan(endpoint, shape) for endpoint in endpoints]
    runner = SshCommandRunner(command_timeout_seconds=90)

    async def snapshot() -> dict[str, str]:
        values = await asyncio.gather(
            *(
                runner.run(
                    endpoint.ssh_target,
                    ("sudo", "-n", "tc", "qdisc", "show", "dev", endpoint.interface),
                )
                for endpoint in endpoints
            )
        )
        return dict(zip((e.agent_id for e in endpoints), values, strict=True))

    before = await snapshot()
    for value in before.values():
        _validate_restorable_root(value)
    record: dict[str, Any] = {
        "network": network,
        "original_qdisc": before,
        "applied_qdisc": None,
        "restored_qdisc": None,
        "cleanup_error": None,
        "worker_ports": ports,
    }
    try:
        applied = await asyncio.gather(
            *(batch_remote(plan.endpoint.ssh_target, plan.apply) for plan in plans),
            return_exceptions=True,
        )
        if any(isinstance(value, BaseException) for value in applied):
            raise RuntimeError("tc batch apply failed")
        record["applied_qdisc"] = await snapshot()
        if not all("qdisc htb 1: root" in value for value in record["applied_qdisc"].values()):
            raise RuntimeError("traffic control did not become active on every node")
        record["calibration"] = calibrate_bandwidth(regime)
        stage1.write(ROOT / f"network-{regime}-calibration.json", record["calibration"])
        if not record["calibration"]["accepted"]:
            raise RuntimeError(f"{regime} link calibration failed; no formal cell started")
        await execute()
    finally:
        results = await asyncio.gather(
            *(runner.run(plan.endpoint.ssh_target, plan.cleanup) for plan in plans),
            return_exceptions=True,
        )
        restored = await snapshot()
        record["restored_qdisc"] = restored
        errors = [type(value).__name__ for value in results if isinstance(value, BaseException)]
        if restored != before:
            errors.append("qdisc_restoration_mismatch")
        record["cleanup_error"] = ",".join(errors) if errors else None
        stage1.write(ROOT / f"network-{regime}-attestation.json", record)
        if errors:
            raise RuntimeError("network cleanup failed: " + ",".join(errors))


def calibrate_bandwidth(regime: str) -> dict[str, Any]:
    """Measure the shaped controller-bound link before any formal cell is claimed."""
    with socket.socket() as probe:
        probe.bind(("0.0.0.0", CALIBRATION_PORT))
    server = subprocess.Popen(
        ["/usr/bin/iperf3", "-s", "-p", str(CALIBRATION_PORT)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    measurements: dict[str, Any] = {}
    issues: list[str] = []
    try:
        time.sleep(0.3)
        for agent in ("A4", "A5", "A28"):
            host = pilot.HOSTS[agent]
            if host is None:
                raise RuntimeError("edge calibration target is missing")
            measurements[agent] = {}
            for direction, reverse in (("edge_to_controller", False), ("controller_to_edge", True)):
                command = (
                    "iperf3 -c 192.168.0.12 -p "
                    + str(CALIBRATION_PORT)
                    + " -t 3 -J"
                    + (" -R" if reverse else "")
                )
                completed = subprocess.run(
                    ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host, command],
                    check=True,
                    text=True,
                    capture_output=True,
                    timeout=25,
                )
                raw = json.loads(completed.stdout)
                throughput = raw["end"]["sum_received"]["bits_per_second"] / 1_000_000
                stream = raw["end"]["streams"][0]["sender"]
                measurements[agent][direction] = {
                    "measured_mbps": throughput,
                    "tcp_mean_rtt_ms": stream.get("mean_rtt", 0) / 1000,
                }
                lower = 2.0 if regime == "slow" else 70.0
                upper = 4.5 if regime == "slow" else 130.0
                if not lower <= throughput <= upper:
                    issues.append(
                        f"{regime} {direction} outside {lower}-{upper}Mbps "
                        f"on {agent}: {throughput:.2f}Mbps"
                    )
    finally:
        server.terminate()
        server.wait(timeout=10)
    return {"measurements": measurements, "accepted": not issues, "issues": issues}


async def run_cell(cell: dict, protocol: dict, pool: dict, baseline: dict) -> dict:
    out = ROOT / "cells" / cell["cell_id"]
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
    network = NETWORKS[cell["network"]]
    config = {
        "run_id": run_id,
        "cell_id": cell["cell_id"],
        "worker_urls": urls,
        "fresh_worker_stores": stores,
        "network": network,
    }
    stage1.write(out / "claim.json", {"cell": cell, "config": config, "no_retry": True})
    stage1.write(
        out / "method-compatibility.json",
        {
            "method": cell["method"],
            "runtime": {
                "BLIND": "OpenAIAgentsNativeRuntime",
                "AWARE": "OpenAIAgentsNativeRuntime+RawAwareProfileVisibility",
                "LEDGER": "MeasuredLedgerRuntime",
            }[cell["method"]],
            "actual_profile_visibility": "aware" if cell["method"] == "AWARE" else "blind",
            "semantic_manager_instructions_unchanged": True,
            "formal_bridge_enabled": False,
        },
    )
    original_link = pilot.LinkSpec
    original_runtime = pilot.OpenAIAgentsNativeRuntime

    def link(**kwargs: Any) -> Any:
        kwargs["bandwidth_mbps"] = network["bandwidth_mbps"]
        kwargs["rtt_ms"] = network["added_rtt_ms"]
        return BASE_LINK(**kwargs)

    pilot.LinkSpec = link
    pilot.OpenAIAgentsNativeRuntime = {
        "BLIND": BASE_RUNTIME,
        "AWARE": RawAwareRuntime,
        "LEDGER": MeasuredLedgerRuntime,
    }[cell["method"]]
    starts: dict[str, dict] = {}
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
            stage1.write(out / "worker-starts" / (agent + ".json"), starts[agent])
        await pilot.states(urls, fresh=True)
        await pilot.execute(cell, out, config, protocol)
    finally:
        pilot.LinkSpec = original_link
        pilot.OpenAIAgentsNativeRuntime = original_runtime
        cleanup = await pilot.cleanup_workers(starts, urls, out, baseline)
    result_path = out / "runs" / run_id / "result.json"
    result = json.loads(result_path.read_text()) if result_path.exists() else None
    problems = []
    if not cleanup["drained"] or not cleanup["verified_exited"] or cleanup["errors"]:
        problems.append("worker_cleanup_failed")
    if result is None and not (out / "administrative-outcome.json").exists():
        problems.append("missing_result_and_administrative_outcome")
    for context in json.loads((out / "context-receipts.json").read_text()):
        if context.get("error_code") in {
            "context_integrity_failed",
            "context_preflight_unavailable",
        }:
            problems.append(context["error_code"])
        if (
            context.get("decision") == "allow"
            and context.get("http_status") == 200
            and not context.get("integrity_verified")
        ):
            problems.append("accepted_context_not_verified")
    summary = {
        "cell": cell,
        "run_id": run_id,
        "completion": None if result is None else result["execution_completed"],
        "score": None
        if result is None or result.get("evaluation") is None
        else result["evaluation"]["benchmark_score"],
        "wall_ms": (monotonic() - started) * 1000,
        "system_problems": sorted(set(problems)),
        "failure": None if result is None else result.get("failure"),
    }
    stage1.write(out / "cell-finished.json", summary)
    if problems:
        raise RuntimeError("system boundary: " + ",".join(sorted(set(problems))))
    return summary


async def main(key: Path) -> None:
    stage0, original, pool, anchor = configure()
    _load_control_plane_key(key, "DASHSCOPE_API_KEY")
    baseline = await pilot.residency()
    pilot.CONTEXT = stage1.context_from_residency(stage0, baseline)
    p = protocol(original, anchor)
    freeze = ROOT / "execution-freeze.json"
    if freeze.exists():
        raise RuntimeError("Stage 2 already claimed; no selective reruns")
    stage1.write(
        freeze,
        {
            "version": "harness-v2-stage2-001",
            "stage0_sha256": stage1.sha(stage1.STAGE0),
            "stage1_complete_sha256": stage1.sha(stage1.STAGE1 / "complete.json"),
            "anchor_manifest_sha256": stage1.sha(ANCHOR_MANIFEST),
            "h1_harness_sha256": stage1.sha(APP / stage1.H1),
            "order": p["order"],
            "networks": NETWORKS,
            "methods": METHODS,
            "source_sha256": {
                name: stage1.sha(APP / name)
                for name in (
                    "src/infra_joint/control/native_agents.py",
                    "src/infra_joint/control/ledger_native.py",
                    "src/infra_joint/control/method_usage.py",
                    "scripts/harness_v2_stage2.py",
                    "scripts/lightweight_planner_pilot_v1.py",
                )
            },
            "task_timeout_seconds": 3600,
            "no_selective_reruns": True,
            "seed": "not overridden; actual Ollama tag/default and provider randomness recorded",
        },
    )
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: (ROOT / "STOP").touch(exist_ok=True))
    rows = []
    for regime in ("slow", "fast"):

        async def block(active_regime: str = regime) -> None:
            for cell in (c for c in p["order"] if c["network"] == active_regime):
                if (ROOT / "STOP").exists():
                    raise RuntimeError("STOP before next cell")
                row = await asyncio.wait_for(run_cell(cell, p, pool, baseline), timeout=5100)
                rows.append(row)
                with (ROOT / "journal.jsonl").open("a") as stream:
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                print(
                    json.dumps(
                        {
                            "cell": cell["cell_id"],
                            "finished": len(rows),
                            "completion": row["completion"],
                            "score": row["score"],
                        }
                    ),
                    flush=True,
                )

        urls = {
            agent: url.rsplit(":", 1)[0] + ":" + str(PORTS[agent])
            for agent, url in pool["worker_urls"].items()
        }
        await network_block(regime, urls, block)
    stage1.write(ROOT / "complete.json", {"cells": len(rows), "system_problems": []})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key-file", type=Path, required=True)
    asyncio.run(main(parser.parse_args().api_key_file))
