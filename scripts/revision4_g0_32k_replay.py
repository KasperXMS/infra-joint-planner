"""Validate and replay the immutable Revision-3 G0 under the 32K contract."""

# This one-purpose harness never calls a Planner or Prior backend. It promotes
# the durable, previously rejected constructed G0 only after validation under
# the Revision-4 static capability contract.
# pyright: reportPrivateUsage=false

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from open_ended_infra_aware_preliminary_v1 import _observed_operator_profiles
from workflow_formal_preliminary_2x2_v1 import (
    DEFAULT_CONFIG,
    _assert_empty_workers,
    _environment,
    _load_bundle,
    _operations,
    _runner_config,
    _worker_urls,
    _yaml,
)

from infra_joint.control.adaptation import KeepWorkflowPolicy
from infra_joint.control.adaptive_runner import AdaptiveWorkflowBenchmarkRunner
from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.contracts import StaticCapabilityContract
from infra_joint.control.prior import (
    FrozenPriorWorkflow,
    PriorGenerationResult,
    PriorGeneratorProvenance,
    PriorWorkflowStore,
)
from infra_joint.control.workflow import SemanticWorkflowPlan, canonical_sha256
from infra_joint.control.workflow_validation import validate_semantic_workflow
from infra_joint.core.task import TaskContract
from infra_joint.operators.catalog import build_operator_catalog

EXPECTED_PLAN_SHA256 = "c964883c32fa4b144bffdf77a153e57c438d802adb361c6d9e3739c8617b459f"


class RecordedPriorGenerator:
    """Expose recorded provenance while making generation impossible."""

    def __init__(self, provenance: PriorGeneratorProvenance) -> None:
        self._provenance = provenance
        self.generate_calls = 0

    def provenance(
        self,
        task: TaskContract,
        capabilities: StaticCapabilityContract,
    ) -> PriorGeneratorProvenance:
        del task, capabilities
        return self._provenance

    async def generate(
        self,
        task: TaskContract,
        capabilities: StaticCapabilityContract,
        *,
        public_bundle_sha256: str | None = None,
    ) -> PriorGenerationResult:
        del task, capabilities, public_bundle_sha256
        self.generate_calls += 1
        raise RuntimeError("Revision-4 replay forbids Prior generation")


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _recorded_provenance(metadata: dict[str, Any]) -> PriorGeneratorProvenance:
    return PriorGeneratorProvenance(
        generator_id=str(metadata["generator_id"]),
        generator_version=str(metadata["generator_version"]),
        model_id=str(metadata["model_id"]),
        prompt_sha256=str(metadata["prompt_sha256"]),
    )


def _inputs(args: argparse.Namespace) -> tuple[
    dict[str, Any],
    Any,
    SemanticWorkflowPlan,
    StaticCapabilityContract,
    str,
    PriorGeneratorProvenance,
]:
    config = _yaml(args.config)
    bundle = _load_bundle(config, args)
    plan = SemanticWorkflowPlan.model_validate_json(args.plan.read_text("utf-8"))
    if plan.canonical_sha256() != EXPECTED_PLAN_SHA256:
        raise RuntimeError("durable rejected G0 canonical hash mismatch")
    registry = build_operator_catalog()
    capabilities = build_static_capability_contract(
        _environment(config, bundle, "fast"),
        registry,
        _operations(config),
    )
    validate_semantic_workflow(plan, bundle.execution.task, capabilities, registry)
    bundle_sha256 = AdaptiveWorkflowBenchmarkRunner._public_bundle_hash(bundle)
    metadata = cast(
        dict[str, Any],
        json.loads(args.request_metadata.read_text(encoding="utf-8")),
    )
    if str(metadata["public_bundle_sha256"]) != bundle_sha256:
        raise RuntimeError("public artifact bundle differs from the rejected Prior attempt")
    if str(metadata["task_id"]) != bundle.execution.task.task_id:
        raise RuntimeError("task identity differs from the rejected Prior attempt")
    return (
        config,
        bundle,
        plan,
        capabilities,
        bundle_sha256,
        _recorded_provenance(metadata),
    )


def validate(args: argparse.Namespace) -> None:
    config, bundle, plan, capabilities, bundle_sha256, provenance = _inputs(args)
    generation = PriorGenerationResult(plan=plan, provenance=provenance)
    frozen = FrozenPriorWorkflow.create(
        task=bundle.execution.task,
        generation=generation,
        capabilities=capabilities,
        public_bundle_sha256=bundle_sha256,
    )
    frozen_path = PriorWorkflowStore(args.evidence / "frozen-prior").save(frozen)
    context_windows = sorted({item.context_window for item in capabilities.model_classes})
    if context_windows != [32_768]:
        raise RuntimeError(f"Revision-4 capability is not exactly 32K: {context_windows}")
    _write_json(
        args.evidence / "static-validation.json",
        {
            "validated_at": datetime.now(UTC).isoformat(),
            "planner_calls": 0,
            "prior_calls": 0,
            "matrix_cells": 0,
            "tc_shaping_calls": 0,
            "task_id": bundle.execution.task.task_id,
            "plan_path": str(args.plan),
            "plan_sha256": plan.canonical_sha256(),
            "plan_version": plan.version,
            "workflow_id": plan.workflow_id,
            "action_count": len(plan.actions),
            "dependency_count": len(plan.dependencies),
            "terminal_action_id": plan.terminal_action_id,
            "public_bundle_sha256": bundle_sha256,
            "recorded_prior_provenance": provenance.model_dump(mode="json"),
            "static_capability_sha256": canonical_sha256(
                capabilities.model_dump(mode="json")
            ),
            "model_classes": [
                item.model_dump(mode="json") for item in capabilities.model_classes
            ],
            "context_windows": context_windows,
            "reserved_output_tokens": sorted(
                {item.reserved_output_tokens for item in capabilities.model_classes}
            ),
            "semantic_validation": "passed",
            "static_feasibility": "passed",
            "frozen_prior_path": str(frozen_path),
            "frozen_prior_sha256": frozen.plan_sha256,
            "config_experiment_id": config["experiment_id"],
        },
    )
    print(plan.canonical_sha256(), flush=True)


async def run(args: argparse.Namespace) -> None:
    config, bundle, plan, _, _, provenance = _inputs(args)
    validation_path = args.evidence / "static-validation.json"
    if not validation_path.exists():
        raise FileNotFoundError("static validation evidence is required before replay")
    validation = cast(
        dict[str, Any],
        json.loads(validation_path.read_text(encoding="utf-8")),
    )
    if validation.get("static_feasibility") != "passed":
        raise RuntimeError("static validation did not pass")
    if validation.get("plan_sha256") != plan.canonical_sha256():
        raise RuntimeError("validated G0 differs from replay G0")
    worker_urls = _worker_urls(args.worker_url)
    worker_states = await _assert_empty_workers(worker_urls)
    generator = RecordedPriorGenerator(provenance)
    profiles_config = cast(dict[str, Any], config["profiles"])
    runner = AdaptiveWorkflowBenchmarkRunner(
        _runner_config(
            _environment(config, bundle, "fast"),
            worker_urls,
            args.evidence,
        ),
        generator,
        KeepWorkflowPolicy("Revision-4 replay preserves the immutable rejected G0"),
        _operations(config),
        prior_store=PriorWorkflowStore(args.evidence / "frozen-prior"),
        require_frozen_prior=True,
        cost_profiles=_observed_operator_profiles(
            Path(str(profiles_config["operator_source_evidence"]))
        ),
    )
    started_at = datetime.now(UTC)
    result = await runner.run(bundle, run_id=args.run_id)
    ended_at = datetime.now(UTC)
    if generator.generate_calls != 0:
        raise RuntimeError("replay unexpectedly invoked Prior generation")
    _write_json(
        args.evidence / "replay-audit.json",
        {
            "run_id": args.run_id,
            "request_started_at": started_at.isoformat(),
            "request_ended_at": ended_at.isoformat(),
            "planner_calls": 0,
            "prior_calls": generator.generate_calls,
            "matrix_cells": 0,
            "tc_shaping_calls": 0,
            "plan_sha256": plan.canonical_sha256(),
            "worker_states_before": worker_states,
            "result": result.model_dump(mode="json"),
        },
    )
    print(result.model_dump_json(), flush=True)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    root.add_argument("command", choices=("validate", "run"))
    root.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    root.add_argument("--evidence", type=Path, required=True)
    root.add_argument("--plan", type=Path, required=True)
    root.add_argument("--request-metadata", type=Path, required=True)
    root.add_argument("--multihop-corpus", type=Path, required=True)
    root.add_argument("--multihop-queries", type=Path, required=True)
    root.add_argument("--run-id", default="revision4-g0-32k-replay")
    root.add_argument("--worker-url", action="append", default=[])
    return root


def main() -> None:
    args = parser().parse_args()
    if args.command == "validate":
        validate(args)
    else:
        asyncio.run(run(args))


if __name__ == "__main__":
    main()
