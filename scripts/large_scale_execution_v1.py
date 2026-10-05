"""Remote-only formal execution using frozen tasks, native runtimes and raw API metering.

Task preparation, selection and historical experiments are never replayed or
rewritten. This is the common execution entry point for the seven existing methods.
Queue admission and phase gates are separate from an individual attempt.
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
import sys
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import agents
import cost_guidance_exploration_v1 as frozen
import httpx
from large_scale_repair_freeze_v1 import verified_prices
from openai import AsyncOpenAI
from resource_blind_live_validation_v1 import MANAGER_INSTRUCTIONS, _clients
from run_predecision_matrix_v1 import write_new
from sdk_native_blind_multihop_v1 import _assert_fresh
from sdk_native_infra_preliminary_v1_3 import (
    ModelRequestBodyAdapter,
    _freeze_cell,
    _load_control_plane_key,
)

from infra_joint.agents.context import AgentTaskView
from infra_joint.benchmarks.base import (
    AdaptationBundle,
    AdaptedExecutionCase,
    PreparedArtifact,
    PrivateChoiceEvaluation,
)
from infra_joint.benchmarks.multihop_rag import PrivateMultiHopEvaluation
from infra_joint.config import PlannerConfig, RunnerConfig, StaticBackendConfig
from infra_joint.control.bde_native import BDENativeRuntime
from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.contracts import ProfileVisibility
from infra_joint.control.method_usage import MeasuredLedgerRuntime
from infra_joint.control.native_agents import OpenAIAgentsNativeRuntime
from infra_joint.control.provenance import provenance_sha256
from infra_joint.control.quote_native import QuoteNativeRuntime
from infra_joint.control.runner import ControlPlaneBenchmarkRunner
from infra_joint.control.verification import OpenAIAgentsBlindVerifier
from infra_joint.core.state import LinkSpec
from infra_joint.experiments.api_cost import APIPriceCard, FXReference
from infra_joint.experiments.large_scale_protocol import METHODS, PLANNERS, ScheduledCell
from infra_joint.experiments.sdk_api_meter import RawSDKAPIMeter, metered_sdk
from infra_joint.operators.catalog import build_operator_catalog

ROOT = Path("/home/super/xiaoming/large-scale-cost-guidance-v1")
RESIDENT_ROOT = Path("/home/super/xiaoming/large-scale-cost-guidance-resident-v1")
TASK_FREEZE_SHA256 = "25e65b22b452bc164efe61ad895d20e5fcf3c8d407e4e9c7380a204bbec9b3ad"


@dataclass(frozen=True)
class ResidentBlock:
    """Explicit new physical block; never mutate historical module globals."""

    root: Path = RESIDENT_ROOT
    environment_config: str = "configs/experiments/resident-diverse-environment-v1.yaml"
    harness_manifest: str = "configs/experiments/infra-aware-predecision-resident-v1.yaml"

    def validate(self, deployment_root: Path) -> None:
        if (sys.platform != "linux" or self.root != RESIDENT_ROOT
                or deployment_root.resolve() != RESIDENT_ROOT
                or self.environment_config != ResidentBlock.environment_config
                or self.harness_manifest != ResidentBlock.harness_manifest):
            raise RuntimeError("resident execution must use the separately frozen 4090 block")


def require_remote(root: Path) -> None:
    if sys.platform != "linux" or root.resolve() != ROOT:
        raise RuntimeError("benchmark execution and payloads must remain in the 4090 namespace")


def frozen_task(
    selection_root: Path, manifest: dict[str, Any], family: str, position: int,
) -> tuple[AdaptationBundle, dict[str, Any]]:
    """Strict reload plus original task, evaluator and prepared-byte verification."""
    rows = [row for row in manifest["tasks"]
            if row["family"] == family and row["position"] == position]
    if len(rows) != 1:
        raise RuntimeError("frozen task identity is missing or ambiguous")
    row = rows[0]
    folder = selection_root / f"{family}-{position}"
    if folder.resolve().parent != selection_root.resolve():
        raise RuntimeError("frozen task path escapes selection namespace")
    if json.loads((folder / "receipt.json").read_text()) != row:
        raise RuntimeError("task receipt/manifest drift")
    execution = AdaptedExecutionCase.model_validate(
        json.loads((folder / "execution.json").read_text()))
    private_file = folder / "private-evaluation.json"
    if frozen._sha256(private_file) != row["private_evaluation_sha256"]:
        raise RuntimeError("private evaluation drift")
    private = (PrivateMultiHopEvaluation if family == "multihop_rag" else PrivateChoiceEvaluation
               ).model_validate(json.loads(private_file.read_text()))
    if (private.task_id != execution.task.task_id
            or private.evaluator_id != execution.task.evaluator_id):
        raise RuntimeError("execution/private evaluator identity mismatch")
    evaluator_source = inspect.getsourcefile(type(private.build_evaluator()))
    if evaluator_source is None or frozen._sha256(Path(evaluator_source)) != row[
        "evaluator_implementation_sha256"
    ]:
        raise RuntimeError("original evaluator implementation drift")
    specs = {spec.artifact_id: spec for spec in execution.task.artifacts}
    if len(specs) != len(row["artifacts"]):
        raise RuntimeError("prepared artifacts and task contract disagree")
    prepared = []
    for artifact in row["artifacts"]:
        file = Path(artifact["path"])
        if file.resolve().parent != folder.resolve():
            raise RuntimeError("prepared artifact escapes frozen task folder")
        prepared.append(PreparedArtifact(spec=specs[artifact["artifact_id"]],
                                         content=file.read_bytes(),
                                         sha256_hex=artifact["sha256"]))
        if (prepared[-1].spec.media_type != artifact["media_type"]
                or prepared[-1].spec.size_bytes != artifact["bytes"]):
            raise RuntimeError("prepared artifact media/size receipt drift")
    bundle = AdaptationBundle(execution, private, tuple(prepared))
    view = AgentTaskView.from_contract(execution.task).model_dump(mode="json", by_alias=True)
    if (frozen._public_bundle_digest(bundle) != row["task_bundle_sha256"]
            or provenance_sha256(view) != row["agent_task_sha256"]
            or execution.task.output_contract.model_dump(mode="json", by_alias=True)
            != row["output_contract"]):
        raise RuntimeError("frozen task semantic/output contract drift")
    return bundle, row


def cell_config(
    cell: ScheduledCell, run_id: str, reference: dict[str, Any], *, root: Path = ROOT,
) -> dict[str, Any]:
    if cell.method not in METHODS or cell.planner not in PLANNERS:
        raise ValueError("unfrozen method or Planner")
    if root not in {ROOT, RESIDENT_ROOT}:
        raise ValueError("unfrozen experiment namespace")
    stores = {agent: str((Path("/home/super") if agent == "strong-4090" else Path("/mnt/ssd"))
                         / "heterogeneous-v1/artifacts" / root.name / run_id / agent)
              for agent in reference["worker_urls"]}
    return {"experiment_id": root.name, "task": f"{cell.task.family}-{cell.task.position}",
            "cell_id": cell.cell_id, "run_id": run_id, "planner": cell.planner,
            "method": cell.method,
            "profile_visibility": "aware" if cell.method == "B1" else "blind",
            "network": reference["network_regimes"][cell.network],
            "worker_urls": reference["worker_urls"], "fresh_worker_stores": stores,
            "model_service_timeout_seconds": 1200, "execution": reference["execution"]}


def build_native_runtime(
    method: str, *, model: object, verifier: object, sdk: object, registry: object,
    operations: tuple[str, ...], environment: object, history: object,
    network: str, rules: dict[str, Any] | None, physical: object | None = None,
) -> OpenAIAgentsNativeRuntime:
    options = dict(name="sdk-native-manager", instructions=MANAGER_INSTRUCTIONS, model=model,
                   sdk_module=sdk, registry=registry, available_operations=operations,
                   blind_verifier=verifier, record_input_provenance=True)
    if method in {"B0", "B1"}:
        return OpenAIAgentsNativeRuntime(**options, predecision_profiles=True)
    if method == "A":
        return MeasuredLedgerRuntime(**options)
    extra = dict(physical=physical, environment=environment, cost_history=history,
                 network_category="fast" if network == "fast" else "constrained",
                 reachable_workers=frozenset(frozen.HOSTS))
    if method == "C":
        return QuoteNativeRuntime(**options, **extra)
    if method in {"B", "D", "E"}:
        return BDENativeRuntime(**options, **extra, route=method,
                                rules=rules if method == "E" else None)
    raise ValueError("unknown frozen method")


async def execute_once(args: argparse.Namespace, *, block: ResidentBlock | None = None) -> None:
    """Attempt only. Caller must own reservation, fresh Workers, tc and admission."""
    if block is None:
        require_remote(args.deployment_root)
    else:
        block.validate(args.deployment_root)
    frozen.validate_runtime_import_root()
    config = frozen._yaml(args.config)
    if config["method"] not in METHODS or config["planner"] not in PLANNERS:
        raise RuntimeError("method/model drift")
    selection_root = ROOT / "preparation/task-freeze-002"
    if frozen._sha256(selection_root / "manifest.json") != TASK_FREEZE_SHA256:
        raise RuntimeError("18-task freeze drift")
    manifest = json.loads((selection_root / "manifest.json").read_text())
    family, position = config["task"].rsplit("-", 1)
    bundle, row = frozen_task(selection_root, manifest, family, int(position))
    reference = frozen.protocol()
    if block is not None:
        pool = frozen._yaml(frozen.REPO / block.environment_config)
        reference = {**reference, "environment_config": block.environment_config,
                     "harness_manifest": block.harness_manifest,
                     "worker_urls": pool["worker_urls"]}
    base = frozen.base_config(reference)
    if block is not None:
        base["environment_config"] = block.environment_config
    base["execution"]["initial_placement"][config["task"]] = [
        artifact["initial_worker"] for artifact in row["artifacts"]]
    environment = frozen._environment(base, config["task"], bundle)
    environment = environment.model_copy(update={"links": tuple(
        LinkSpec(source_agent_id=a.agent_id, target_agent_id=b.agent_id,
                 bandwidth_mbps=config["network"]["bandwidth_mbps"],
                 rtt_ms=config["network"]["added_rtt_ms"])
        for a in environment.agents for b in environment.agents if a.agent_id != b.agent_id)})
    registry, operations = build_operator_catalog(), frozen._operations(base)
    capability = build_static_capability_contract(environment, registry, operations)
    harness_path = frozen.REPO / reference["harness_manifest"]
    execution_path = getattr(args, "execution_freeze", None)
    if (block is None and execution_path is not None
            and execution_path.name == "execution-freeze-003.json"):
        from large_scale_transport_freeze_v1 import harness_for_attempt

        harness_path = harness_for_attempt(ROOT, frozen.REPO, execution_path)
    harness = frozen.load_harness(harness_path)
    # Validate the shared frozen harness, then explicitly choose the experimental
    # Manager model. Never relax the historical same-stack validator or its files.
    frozen.validate_harness(harness, environment, capability, operations)
    _freeze_cell(args, config, frozen.REPO / reference["environment_config"],
                 harness_path, harness, bundle, row["source"],
                 frozen._capability_sha256(capability), base)
    history = frozen.load_history(args)
    rules = json.loads(args.rules_manifest.read_text())
    if (frozen._sha256(args.rules_manifest) != manifest["e_rules_manifest_sha256"]
            or provenance_sha256(rules["rules"]) != manifest["e_rules_sha256"]):
        raise RuntimeError("independent shared E rule freeze drift")
    prices_path, pricing_sha256 = verified_prices(ROOT, Path(__file__).resolve().parents[1])
    price_data = json.loads(prices_path.read_text())
    price_cards = {name: APIPriceCard.model_validate(value)
                   for name, value in price_data["prices"].items()}
    fx = FXReference.model_validate(price_data["fx"])
    write_new(args.output / "attempt-freeze.json", {
        "code_revision": frozen._revision(), "config_sha256": frozen._sha256(args.config),
        "task_selection_sha256": TASK_FREEZE_SHA256, "task_receipt": row,
        "pricing_sha256": pricing_sha256, "capability_sha256": frozen._capability_sha256(
            capability), "static_capability_contract": capability.model_dump(mode="json"),
        "harness": harness.model_dump(mode="json"), "manager_model": config["planner"],
        "verifier_model": "qwen3.8-max", "fresh_worker_stores": config["fresh_worker_stores"],
        "history_sha256": frozen.HISTORY_SHA256, "rules_sha256": manifest["e_rules_sha256"],
    })
    api_root = args.output / "private/api"
    meter = RawSDKAPIMeter(provider="aliyun-model-studio", region="cn-beijing", prices=price_cards,
                          fx=fx, private_sink=lambda kind, identifier, value:
                          write_new(api_root / f"{identifier}-{kind}.json", value))
    _load_control_plane_key(args.api_key_file, "DASHSCOPE_API_KEY")
    agents.set_tracing_disabled(True)
    try:
        async with AsyncExitStack() as stack:
            http_client = await stack.enter_async_context(httpx.AsyncClient(event_hooks={
                "request": [meter.request_hook], "response": [meter.response_hook]}))
            api_client = await stack.enter_async_context(AsyncOpenAI(
                base_url=harness.manager["base_url"], api_key=os.environ["DASHSCOPE_API_KEY"],
                timeout=180, max_retries=0, http_client=http_client))

            def model(identifier: str) -> object:
                return ModelRequestBodyAdapter(agents.OpenAIChatCompletionsModel(
                    model=identifier, openai_client=api_client),
                    dict(harness.manager["request_extra_body"]))

            verifier = OpenAIAgentsBlindVerifier(model=meter.model(
                model("qwen3.8-max"), recipient="verifier", agent_name="blind_evidence_verifier",
                requested_model="qwen3.8-max"))
            runtime = build_native_runtime(
                config["method"], model=model(config["planner"]), verifier=verifier,
                sdk=metered_sdk(agents, meter, manager_model=config["planner"]), registry=registry,
                operations=operations, environment=environment, history=history,
                network=config["network"]["regime"], rules=rules["rules"],
            )
            clients = await _clients(stack, config["worker_urls"], timeout_seconds=1200)
            await _assert_fresh(clients)
            runner = ControlPlaneBenchmarkRunner(
                RunnerConfig(environment=environment, worker_urls=config["worker_urls"],
                             planner=PlannerConfig(model=StaticBackendConfig(response="unused")),
                             output_root=args.output / "runs", max_planning_steps=20,
                             http_timeout_seconds=1200), None, operations, worker_clients=clients,
                profile_visibility=ProfileVisibility(config["profile_visibility"]),
                loop_budget=harness.budget, logical_runtime=runtime)
            result = await runner.run(bundle, run_id=config["run_id"])
            write_new(args.output / "summary.json", {
                "run_id": config["run_id"], "cell_id": config["cell_id"],
                "execution_completed": result.execution_completed,
                "final_answer": result.final_answer,
                "evaluation": None if result.evaluation is None else result.evaluation.model_dump(
                    mode="json"),
                "failure": None if result.failure is None else result.failure.model_dump(
                    mode="json"),
                "initial_transfer_bytes": sum(
                    t.bytes_transferred for t in result.initial_transfers),
                "initial_transfer_latency_ms": sum(t.duration_ms for t in result.initial_transfers),
            })
    finally:
        write_new(args.output / "api-accounting.json", meter.summary())


def audit_prepared(args: argparse.Namespace) -> dict[str, Any]:
    """Read-only full frozen-task reload on 4090, without Workers/tc/model calls."""
    require_remote(args.deployment_root)
    frozen.validate_runtime_import_root()
    selection = ROOT / "preparation/task-freeze-002"
    if frozen._sha256(selection / "manifest.json") != TASK_FREEZE_SHA256:
        raise RuntimeError("frozen task selection drift")
    manifest = json.loads((selection / "manifest.json").read_text())
    rows = []
    for receipt in manifest["tasks"]:
        bundle, row = frozen_task(selection, manifest, receipt["family"], receipt["position"])
        rows.append({"family": row["family"], "position": row["position"],
                     "source_task_id": row["source_task_id"],
                     "task_bundle_sha256": frozen._public_bundle_digest(bundle),
                     "artifact_count": len(bundle.prepared_artifacts),
                     "prepared_bytes": sum(
                         len(item.content) for item in bundle.prepared_artifacts)})
    result = {"code_revision": frozen._revision(), "task_selection_sha256": TASK_FREEZE_SHA256,
              "tasks": rows, "formal_cells": 0, "model_calls": 0, "workers": False, "tc": False,
              "passed": len(rows) == 18}
    write_new(args.output, result)
    return {key: value for key, value in result.items() if key != "tasks"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deployment-root", type=Path, default=ROOT)
    parser.add_argument("--audit-prepared", action="store_true", required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    require_remote(arguments.deployment_root)
    if arguments.output.resolve().parent != ROOT / "readiness":
        raise RuntimeError("prepared-task audit must stay in the append-only readiness namespace")
    print(json.dumps(audit_prepared(arguments), sort_keys=True))
