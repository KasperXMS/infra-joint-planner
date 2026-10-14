"""One-shot, fixed logical-workflow comparison on the original Video-MME 795-3 task.

Run on the strong-4090 controller only. Sensitive task content and raw traces stay there.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

import httpx
from blind_3family_validation_v1 import _environment, _operations, _sha256, _yaml
from predecision_crossbenchmark_v1 import base_config, load_bundle
from prepare_sdk_native_infra_worker_v1_3 import prepare
from resource_blind_live_validation_v1 import _clients
from run_predecision_matrix_v1 import HOSTS, start_worker, stop_worker, write_new
from run_sdk_native_infra_cell_with_tc_v1_3 import DEFAULT_ENDPOINTS
from run_sdk_native_infra_cell_with_tc_v1_3 import run as run_shaped
from sdk_native_blind_multihop_v1 import _assert_fresh

from infra_joint.config import PlannerConfig, RunnerConfig, StaticBackendConfig
from infra_joint.control.contracts import (
    ContinueDecision,
    ExecutionRequirements,
    FinishDecision,
    LogicalModelAction,
    LogicalOutput,
    LogicalToolAction,
    ManagerContext,
    ProfileVisibility,
)
from infra_joint.control.loop import AgentLoopBudget, AgentLoopError
from infra_joint.control.runner import ControlPlaneBenchmarkRunner
from infra_joint.core.state import LinkSpec

REPO = Path(__file__).resolve().parents[1]
OWNER = "manager"


class FixedWorkflowPolicy:
    """Predetermined semantic actions; model answers remain unobserved until evaluation."""

    def __init__(self, workflow: str, settings: dict[str, Any]) -> None:
        self.workflow = workflow
        self.settings = settings

    async def decide(self, context: ManagerContext) -> ContinueDecision | FinishDecision:
        task = context.task
        video = tuple(a.artifact_id for a in task.artifacts)
        if len(video) != 1 or not task.artifacts[0].media_type.startswith("video/"):
            raise AgentLoopError("frozen Video-MME workflow requires one original video")
        if any(not item.succeeded for item in context.observations):
            raise AgentLoopError("fixed workflow action failed; retain failed execution")
        frame_ids = tuple(f"frames/frame-{i:06d}.jpg" for i in range(1, 9))
        completed = {item.action_id for item in context.observations}
        if "sample" not in completed:
            action = LogicalToolAction(
                action_id="sample",
                owner_agent_id=OWNER,
                operator="sample_frames",
                inputs=video,
                outputs=tuple(
                    LogicalOutput(
                        artifact_id=name,
                        semantic_type="video_frame",
                        media_type="image/jpeg",
                    )
                    for name in frame_ids
                ),
                arguments={
                    "every_seconds": self.settings["sample_every_seconds"],
                    "max_frames": self.settings["sample_max_frames"],
                    "output_prefix": "frames",
                },
            )
            return ContinueDecision(rationale="frozen eight-frame sampling", actions=(action,))
        if self.workflow == "sheet" and "sheet" not in completed:
            action = LogicalToolAction(
                action_id="sheet",
                owner_agent_id=OWNER,
                operator="make_contact_sheet",
                inputs=frame_ids,
                depends_on=("sample",),
                outputs=(
                    LogicalOutput(
                        artifact_id="sheet.jpg",
                        semantic_type="contact_sheet",
                        media_type="image/jpeg",
                    ),
                ),
                arguments={
                    "columns": self.settings["contact_columns"],
                    "cell_width": self.settings["contact_cell_width"],
                    "cell_height": self.settings["contact_cell_height"],
                    "output_artifact_id": "sheet.jpg",
                },
            )
            return ContinueDecision(rationale="frozen contact-sheet reduction", actions=(action,))
        if "answer" not in completed:
            inputs = frame_ids if self.workflow == "frames" else ("sheet.jpg",)
            options = task.output_contract.choices
            if options is None:
                raise AgentLoopError("frozen task requires a choice output contract")
            prompt = (
                "Answer the task using the attached visual evidence. "
                "The images show eight frames from the beginning of the same source video, "
                "in chronological order. Choose exactly one of the declared answer labels. "
                "Return only the label, with no explanation.\n\n"
                f"Task: {task.objective}\n"
                f"Allowed labels: {', '.join(options)}"
            )
            action = LogicalModelAction(
                action_id="answer",
                owner_agent_id=OWNER,
                inputs=inputs,
                depends_on=(("sample",) if self.workflow == "frames" else ("sheet",)),
                prompt=prompt,
                requirements=ExecutionRequirements(
                    modalities=frozenset({"text", "image"}),
                    min_context_tokens=32768,
                    reserved_output_tokens=2048,
                ),
            )
            return ContinueDecision(rationale="frozen physical-model answer", actions=(action,))
        return FinishDecision(
            reason="model observation is terminal source", source_action_id="answer"
        )


def _load(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    config = json.loads(args.master_config.read_text(encoding="utf-8"))
    source = _yaml(REPO / config["source_protocol"])
    base = base_config(source)
    row = next(r for r in source["tasks"] if r["label"] == config["task_label"])
    return config, base, row


def _freeze(
    args: argparse.Namespace, config: dict[str, Any], base: dict[str, Any], row: dict[str, Any]
) -> None:
    bundle, sources = load_bundle(row, base, _yaml(REPO / config["source_protocol"])["sources"])
    if sources["video_source"]["sha256"] != config["video_sha256"]:
        raise RuntimeError("original video hash mismatch")
    if (
        row["source_task_id"] != config["source_task_id"]
        or row["question_id"] != config["question_id"]
    ):
        raise RuntimeError("task identity mismatch")
    source_paths = [
        "src/infra_joint/control/runner.py",
        "src/infra_joint/control/loop.py",
        "src/infra_joint/control/physical.py",
        "src/infra_joint/control/validation.py",
        "src/infra_joint/operators/media.py",
        "src/infra_joint/worker/server.py",
        "configs/experiments/blind-baseline-environment-v2.yaml",
    ]
    manifest = {
        "source_revision": config["source_revision"],
        "task_id": bundle.execution.task.task_id,
        "task_contract_sha256": hashlib.sha256(
            bundle.execution.task.model_dump_json().encode()
        ).hexdigest(),
        "source_manifest": sources,
        "config_sha256": _sha256(args.master_config),
        "script_sha256": _sha256(Path(__file__)),
        "source_component_sha256": {name: _sha256(REPO / name) for name in source_paths},
        "worker_config_sha256": {
            agent: _sha256(
                REPO
                / "configs/experiments/workers/blind-3family-video-v1.3"
                / f"worker-{'strong-4090' if agent == 'strong-4090' else agent.lower()}.yaml"
            )
            for agent in HOSTS
        },
        "cells": config["execution_order"],
        "gold_access": "evaluator only after terminal answer",
    }
    write_new(args.root / f"source-freeze-{args.attempt}.json", manifest)


async def _execute(args: argparse.Namespace) -> None:
    config, base, row = _load(args)
    freeze = json.loads((args.root / f"source-freeze-{args.attempt}.json").read_text())
    if (
        _sha256(args.master_config) != freeze["config_sha256"]
        or _sha256(Path(__file__)) != freeze["script_sha256"]
    ):
        raise RuntimeError("frozen config or script drift")
    bundle, sources = load_bundle(row, base, _yaml(REPO / config["source_protocol"])["sources"])
    if sources != freeze["source_manifest"]:
        raise RuntimeError("frozen source drift")
    regime, workflow = args.cell.split("-", 1)
    network = config["conditions"][regime]
    environment = _environment(base, row["label"], bundle)
    environment = environment.model_copy(
        update={
            "links": tuple(
                LinkSpec(
                    source_agent_id=a.agent_id,
                    target_agent_id=b.agent_id,
                    bandwidth_mbps=network["bandwidth_mbps"],
                    rtt_ms=network["added_rtt_ms"],
                )
                for a in environment.agents
                for b in environment.agents
                if a.agent_id != b.agent_id
            )
        }
    )
    cell_config = _yaml(args.cell_config)
    async with AsyncExitStack() as stack:
        clients = await _clients(
            stack, config["worker_urls"], timeout_seconds=config["model_service_timeout_seconds"]
        )
        await _assert_fresh(clients)
        runner = ControlPlaneBenchmarkRunner(
            RunnerConfig(
                environment=environment,
                worker_urls=config["worker_urls"],
                planner=PlannerConfig(model=StaticBackendConfig(response="unused")),
                output_root=args.output / "runs",
                max_planning_steps=5,
                http_timeout_seconds=config["model_service_timeout_seconds"],
            ),
            FixedWorkflowPolicy(workflow, config["workflows"][workflow]),
            _operations(base),
            worker_clients=clients,
            profile_visibility=ProfileVisibility.BLIND,
            loop_budget=AgentLoopBudget(
                max_manager_turns=5,
                max_subagent_turns=1,
                max_tool_model_calls=3,
                max_created_subagents=0,
                max_active_subagents=0,
                max_verifier_calls=1,
            ),
        )
        result = await runner.run(bundle, run_id=cell_config["run_id"])
    write_new(
        args.output / "summary.json",
        {
            "cell": args.cell,
            "run_id": result.run_id,
            "execution_completed": result.execution_completed,
            "valid_output": result.execution_completed
            and result.final_answer in ("A", "B", "C", "D"),
            "original_evaluation": None
            if result.evaluation is None
            else result.evaluation.model_dump(mode="json"),
            "failure_code": None if result.failure is None else result.failure.code,
            "failure_type": None if result.failure is None else result.failure.exception_type,
            "telemetry": None
            if result.telemetry is None
            else result.telemetry.model_dump(mode="json"),
            "initial_transfer_bytes": sum(t.bytes_transferred for t in result.initial_transfers),
            "initial_transfer_latency_ms": sum(t.duration_ms for t in result.initial_transfers),
            "manager_turns": None if result.loop is None else result.loop.usage.manager_turns,
            "model_tool_calls": None if result.loop is None else result.loop.usage.tool_model_calls,
        },
    )


async def _with_workers(args: argparse.Namespace) -> None:
    config, _, _ = _load(args)
    cell_config = _yaml(args.cell_config)
    pids: dict[str, int] = {}
    try:
        for agent in HOSTS:
            worker_config = args.root / "worker-configs" / f"{args.cell}-{agent}.yaml"
            prepare(args.cell_config, agent, worker_config)
            pids[agent] = start_worker(
                args.root, worker_config, agent, cell_config["fresh_worker_stores"][agent]
            )
        write_new(args.output / "worker-pids-private.json", pids)
        async with httpx.AsyncClient(timeout=10) as client:
            for agent, url in config["worker_urls"].items():
                for attempt in range(60):
                    try:
                        response = await client.get(url + "/state")
                        response.raise_for_status()
                        state = response.json()
                        if state["agent_id"] != agent or state["artifacts"]:
                            raise RuntimeError("Worker identity or store not fresh")
                        break
                    except httpx.HTTPError:
                        if attempt == 59:
                            raise
                        await asyncio.sleep(1)
        await _execute(args)
    finally:
        errors = []
        for agent, pid in pids.items():
            try:
                stop_worker(args.root, agent, pid)
            except Exception as exc:
                errors.append(f"{agent}: {type(exc).__name__}")
        write_new(args.output / "worker-cleanup.json", {"errors": errors})
        if errors:
            raise RuntimeError("own Worker cleanup incomplete")


def main(args: argparse.Namespace) -> None:
    if (
        sys.platform != "linux"
        or args.root.parent != Path("/home/super/xiaoming")
        or args.root.name != "infra-workflow-opportunity-v1"
    ):
        raise RuntimeError("run only in the isolated controller namespace")
    args.master_config = args.config
    config, base, row = _load(args)
    if args.prepare:
        _freeze(args, config, base, row)
        return
    if not (args.root / f"source-freeze-{args.attempt}.json").is_file():
        raise RuntimeError("prepare and freeze before run")
    for cell in config["execution_order"]:
        regime, workflow = cell.split("-", 1)
        if regime not in config["conditions"] or workflow not in config["workflows"]:
            raise ValueError("invalid frozen cell")
        args.cell = cell
        args.output = args.root / "evidence" / args.attempt / cell
        args.output.mkdir(parents=True, exist_ok=False)
        stores = {
            agent: str(
                (Path("/home/super") if agent == "strong-4090" else Path("/mnt/ssd"))
                / "heterogeneous-v1/artifacts/infra-workflow-opportunity-v1"
                / args.attempt
                / cell
                / agent
            )
            for agent in HOSTS
        }
        args.cell_config = args.root / "cell-configs" / f"{args.attempt}-{cell}.yaml"
        args.cell_config.parent.mkdir(parents=True, exist_ok=True)
        import yaml

        with args.cell_config.open("x", encoding="utf-8") as stream:
            yaml.safe_dump(
                {
                    "run_id": f"infra-workflow-{args.attempt}-{cell}",
                    "worker_urls": config["worker_urls"],
                    "fresh_worker_stores": stores,
                    "model_service_timeout_seconds": config["model_service_timeout_seconds"],
                    "network": config["conditions"][regime],
                },
                stream,
            )
        with (args.root / "queue.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"event": "started", "cell": cell, "pid": os.getpid()}) + "\n")
        try:
            shaped_args = argparse.Namespace(**vars(args))
            shaped_args.config = args.cell_config
            asyncio.run(run_shaped(shaped_args, _with_workers))
        except BaseException as exc:
            with (args.root / "queue.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(
                    json.dumps({"event": "stopped", "cell": cell, "error_type": type(exc).__name__})
                    + "\n"
                )
            raise
        with (args.root / "queue.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"event": "finished", "cell": cell}) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--endpoint-config", type=Path, default=DEFAULT_ENDPOINTS)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--attempt", default="transport-fix-1")
    main(parser.parse_args())
