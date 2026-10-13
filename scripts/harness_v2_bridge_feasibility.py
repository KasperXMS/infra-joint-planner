# pyright: reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
"""H2 KEEP-only bridge feasibility on two frozen dependency-heavy tasks."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

import harness_v2_stage1 as stage1
import lightweight_planner_pilot_v1 as pilot
import yaml
from sdk_native_infra_preliminary_v1_3 import _load_control_plane_key

from infra_joint.control.adaptation import KeepWorkflow
from infra_joint.control.contracts import LogicalModelAction
from infra_joint.control.native_agents import OpenAIAgentsNativeRuntime
from infra_joint.control.native_workflow_bridge import NativeFormalWorkflowBridge
from infra_joint.control.workflow import SemanticWorkflowPlan
from infra_joint.control.workflow_state import VersionedPendingWorkflow
from infra_joint.control.workflow_validation import WorkflowValidationError

ROOT = stage1.ROOT / "stage1_5"
PORTS = {"A4": 63504, "A5": 63505, "A28": 63528, "strong-4090": 63612}


class BridgeRuntime(OpenAIAgentsNativeRuntime):
    def __init__(self, **kwargs: Any) -> None:
        self._formal_registry = kwargs["registry"]
        super().__init__(**kwargs)

    async def run(self, task: Any, gateway: Any, **kwargs: Any) -> Any:
        capabilities = kwargs["static_capabilities"]
        trace = kwargs["trace"]
        workflow = VersionedPendingWorkflow(
            workflow_id=f"harness-v2-h2-{task.task_id}",
            task=task,
            capabilities=capabilities,
            registry=self._formal_registry,
        )
        bridge = NativeFormalWorkflowBridge(workflow, gateway, trace=trace)
        result = None
        try:
            result = await super().run(task, gateway, formal_bridge=bridge, **kwargs)
            return result
        finally:
            sealed = isinstance(workflow.plan, SemanticWorkflowPlan)
            seal_error = None
            keep_success = False
            # This is a post-run feasibility attempt on Manager-proposed actions.
            # It does not invent a future action or claim that Manager planned ahead.
            if result is not None and not sealed:
                candidates = [
                    action
                    for action in workflow.plan.actions
                    if isinstance(action, LogicalModelAction)
                ]
                if candidates:
                    try:
                        workflow.append_fragment(
                            (),
                            expected_version=workflow.plan.version,
                            terminal_action_id=candidates[-1].action_id,
                        )
                        sealed = True
                    except (WorkflowValidationError, ValueError) as exc:
                        seal_error = f"{type(exc).__name__}: {exc}"
                else:
                    seal_error = "no Manager-proposed terminal model action"
            if sealed:
                try:
                    bridge.keep_or_patch(
                        KeepWorkflow(reason="KEEP-only feasibility check"),
                        expected_version=workflow.plan.version,
                    )
                    keep_success = True
                except (WorkflowValidationError, ValueError) as exc:
                    seal_error = f"KEEP {type(exc).__name__}: {exc}"
            status = workflow.execution.statuses
            diagnostics = {
                "pending_action_count": sum(value == "pending" for value in status.values()),
                "pending_dependency_count": sum(
                    status.get(edge.consumer_action_id) == "pending"
                    for edge in workflow.plan.dependencies
                ),
                "proposed_action_count": len(workflow.plan.actions),
                "declared_dependency_count": len(workflow.plan.dependencies),
                "seal_success": sealed,
                "seal_failure_reason": seal_error,
                "patchable_frontier_count": sum(value == "pending" for value in status.values()),
                "unknown_provenance_block_count": sum(
                    item.relation == "unknown" for item in workflow.provenance.entries
                ),
                "keep_success": keep_success,
                "posthoc_terminal_designation": True,
                "future_actions_fabricated": False,
                "actions_immediately_dispatched": True,
            }
            trace.emit("workflow.v2.feasibility", diagnostics)


async def main(key: Path) -> None:
    if not (stage1.STAGE1 / "complete.json").exists():
        raise RuntimeError("Stage 1 basic engineering condition is incomplete")
    stage0, original, pool = stage1.configure()
    _load_control_plane_key(key, "DASHSCOPE_API_KEY")
    baseline = await pilot.residency()
    pilot.CONTEXT = stage1.context_from_residency(stage0, baseline)
    stage1.force_manager_sampling()
    pilot.ROOT = ROOT
    pilot.EDGE_ROOT = Path("/mnt/ssd/harness-v2-baseline-requalification/run-001/stage1_5")
    pilot.ARTIFACT_NAMESPACE = "harness-v2-baseline-requalification/run-001/stage1_5"
    pilot.RUN_PREFIX = "harness-v2-h2-001"
    pilot.PORTS = PORTS
    stage1.STAGE1 = ROOT
    stage1.PORTS = PORTS
    pilot.OpenAIAgentsNativeRuntime = BridgeRuntime
    p = stage1.protocol(original)
    p["order"] = [
        {
            "cell_id": "H2-multihop-1",
            "task_index": 1,
            "family": "multihop_rag",
            "position": 1,
            "group": "L1",
        },
        {
            "cell_id": "H2-longbench-1",
            "task_index": 3,
            "family": "longbench_v2",
            "position": 1,
            "group": "L1",
        },
    ]
    freeze = ROOT / "execution-freeze.json"
    if freeze.exists():
        raise RuntimeError("H2 already claimed; no selective rerun")
    stage1.write(
        freeze,
        {
            "condition": "SDK-native v2, formal bridge enabled, KEEP-only",
            "stage0_sha256": stage1.sha(stage1.STAGE0),
            "stage1_complete_sha256": stage1.sha(stage1.ROOT / "stage1-attempt-002/complete.json"),
            "order": p["order"],
            "future_actions_fabricated": False,
            "semantic_prompt_changed": False,
        },
    )
    network_path = ROOT / "batch-network.yaml"
    network_path.write_text(
        yaml.safe_dump(
            {
                "run_id": "harness-v2-h2-fast",
                "worker_urls": {
                    agent: url.rsplit(":", 1)[0] + ":" + str(PORTS[agent])
                    for agent, url in pool["worker_urls"].items()
                },
                "network": {"regime": "fast", "bandwidth_mbps": 100, "added_rtt_ms": 5},
            }
        )
    )
    rows = []

    async def cells(_args: argparse.Namespace) -> None:
        for cell in p["order"]:
            if (ROOT / "STOP").exists():
                raise RuntimeError("H2 STOP")
            row = await asyncio.wait_for(stage1.run_cell(cell, p, pool, baseline), timeout=5100)
            rows.append(row)
            with (ROOT / "journal.jsonl").open("a") as stream:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            print(json.dumps({"H2": cell["cell_id"], "finished": len(rows)}), flush=True)

    await pilot.run_shaped(
        argparse.Namespace(
            config=network_path,
            output=ROOT,
            endpoint_config=pilot.DEFAULT_ENDPOINTS,
        ),
        execute_cell=cells,
    )
    stage1.write(ROOT / "complete.json", {"cells": len(rows), "system_problems": []})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key-file", type=Path, required=True)
    asyncio.run(main(parser.parse_args().api_key_file))
