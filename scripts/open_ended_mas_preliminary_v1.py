"""Freeze and execute the six-run Open-ended MAS preliminary-v1 experiment."""

from __future__ import annotations

import argparse
import asyncio
import gzip
import hashlib
import json
import os
import subprocess
from contextlib import AsyncExitStack
from pathlib import Path
from time import perf_counter
from typing import Any, cast

import httpx
import yaml

from infra_joint.benchmarks.base import AdaptationBundle
from infra_joint.benchmarks.multimodalqa import (
    MultiModalQAAdapter,
    MultiModalQAImage,
    MultiModalQASample,
    MultiModalQATable,
    MultiModalQAText,
    PrivateMultiModalQAEvaluation,
    bundle_public_digest,
)
from infra_joint.config import RunnerConfig, build_model_backend, load_planner_config
from infra_joint.core.action import SemanticAction
from infra_joint.core.state import ArtifactPlacement, DeploymentSpec, EnvironmentSpec
from infra_joint.core.workflow import WorkflowPlan
from infra_joint.heterogeneous.traffic_control import (
    SshCommandRunner,
    TcController,
    TcEndpoint,
    TcRegime,
    build_tc_command_plan,
)
from infra_joint.infrastructure.validation import validate_worker_surfaces
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.planning.planner import logical_task_payload
from infra_joint.runtime.client import HttpWorkerClient, WorkerClient
from infra_joint.runtime.executor import ArtifactTransferTelemetry
from infra_joint.workflow.planner import LLMWorkflowPlanner, ScriptedWorkflowPlanner
from infra_joint.workflow.runner import PersistedWorkflowRunResult, WorkflowBenchmarkRunner
from infra_joint.workflow.scheduler import LocalityAwareMyopicScheduler
from infra_joint.workflow.workload import (
    AvailableModelInstance,
    WorkloadArtifact,
    WorkloadSpec,
)

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO / "configs/experiments/open-ended-mas-preliminary-v1.yaml"
DEFAULT_DATASET = REPO / "artifacts/multimodalqa-official/dataset"
DEFAULT_IMAGES = REPO / "artifacts/multimodalqa-selected-images"
DEFAULT_OUTPUT = REPO / "results/open-ended-mas-preliminary-v1"
DEFAULT_KEY = REPO.parent / "api_key.txt"
PREFLIGHT_CONFIG = REPO / "configs/local/heterogeneous-v1-preflight.yaml"
TC_CONFIG = REPO / "configs/local/heterogeneous-v1.yaml"

WORKER_URLS = {
    "A4": "http://192.168.0.104:9104",
    "A5": "http://192.168.0.105:9105",
    "A28": "http://192.168.0.128:9128",
    "strong-4090": "http://192.168.0.12:9212",
}
ARTIFACT_ROOTS = {
    "A4": ("edge@192.168.0.104", "/mnt/ssd/heterogeneous-v1/artifacts/a4"),
    "A5": ("edge@192.168.0.105", "/mnt/ssd/heterogeneous-v1/artifacts/a5"),
    "A28": ("edge@192.168.0.128", "/mnt/ssd/heterogeneous-v1/artifacts/a28"),
    "strong-4090": (
        "super@192.168.0.12",
        "/home/super/heterogeneous-v1/artifacts/strong-4090",
    ),
}


class PrepositionedWorkflowRunner(WorkflowBenchmarkRunner):
    async def _materialize(
        self,
        bundle: AdaptationBundle,
        worker_clients: dict[str, WorkerClient],
    ) -> tuple[ArtifactTransferTelemetry, ...]:
        specs = {item.artifact_id: item for item in bundle.execution.task.artifacts}
        prepared = {item.spec.artifact_id: item for item in bundle.prepared_artifacts}
        placements = self._config.environment.initial_placements
        if {item.artifact_id for item in placements} != set(specs):
            raise RuntimeError("prepositioned placements do not exactly cover task artifacts")
        for placement in placements:
            state = await worker_clients[placement.agent_id].get_state()
            artifacts = {item.artifact_id: item for item in state.artifacts}
            observed = artifacts.get(placement.artifact_id)
            expected = specs[placement.artifact_id]
            if (
                observed is None
                or observed.media_type != expected.media_type
                or observed.size_bytes != expected.size_bytes
                or observed.sha256_hex != prepared[placement.artifact_id].sha256_hex
            ):
                raise RuntimeError(
                    f"prepositioned artifact mismatch: {placement.agent_id}/{placement.artifact_id}"
                )
        return ()


def _yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return cast(dict[str, Any], value)


def _jsonl_index(path: Path, wanted: set[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            value = json.loads(line)
            identifier = value.get("qid", value.get("id"))
            if identifier in wanted:
                found[str(identifier)] = cast(dict[str, Any], value)
    missing = wanted - set(found)
    if missing:
        raise RuntimeError(f"dataset records are missing from {path.name}: {sorted(missing)}")
    return found


def _load_bundles(
    config: dict[str, Any], dataset: Path, images: Path
) -> dict[str, AdaptationBundle]:
    task_rows = cast(list[dict[str, Any]], config["dataset"]["tasks"])
    qids = {str(item["qid"]) for item in task_rows}
    examples = _jsonl_index(dataset / "MMQA_dev.jsonl.gz", qids)
    text_ids = {str(item) for qid in qids for item in examples[qid]["metadata"]["text_doc_ids"]}
    table_ids = {str(examples[qid]["metadata"]["table_id"]) for qid in qids}
    texts = _jsonl_index(dataset / "MMQA_texts.jsonl.gz", text_ids)
    tables = _jsonl_index(dataset / "MMQA_tables.jsonl.gz", table_ids)
    adapter = MultiModalQAAdapter(str(config["dataset"]["source_revision"]))
    bundles: dict[str, AdaptationBundle] = {}
    for row in task_rows:
        label, qid = str(row["label"]), str(row["qid"])
        example = examples[qid]
        metadata = cast(dict[str, Any], example["metadata"])
        modalities = tuple(sorted(str(item) for item in metadata["modalities"]))
        expected = tuple(sorted(str(item) for item in row["exact_modalities"]))
        if modalities != expected or float(metadata["rephrasing_meta"]["accuracy"]) != 1.0:
            raise RuntimeError(f"frozen task selection invariant failed: {qid}")
        image_values: list[MultiModalQAImage] = []
        for image_id in metadata["image_doc_ids"]:
            candidates = list(images.glob(f"{image_id}.*"))
            if len(candidates) != 1:
                raise RuntimeError(f"expected exactly one image file for {image_id}")
            path = candidates[0]
            media_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
            image_values.append(
                MultiModalQAImage(
                    id=image_id,
                    filename=path.name,
                    media_type=media_type,
                    content=path.read_bytes(),
                )
            )
        text_values = tuple(
            MultiModalQAText.model_validate(texts[str(item)]) for item in metadata["text_doc_ids"]
        )
        table_id = str(metadata["table_id"])
        sample = MultiModalQASample(
            qid=qid,
            question=example["question"],
            question_type=metadata["type"],
            modalities=modalities,
            texts=text_values,
            table=MultiModalQATable(id=table_id, payload=tables[table_id]),
            images=tuple(image_values),
            answers=tuple(str(item["answer"]) for item in example["answers"]),
            supporting_context=tuple(example["supporting_context"]),
            intermediate_answers=tuple(metadata["intermediate_answers"]),
        )
        bundles[label] = adapter.adapt(sample)
    return bundles


def _base_environment() -> EnvironmentSpec:
    raw = _yaml(PREFLIGHT_CONFIG)
    return EnvironmentSpec.model_validate(raw["environment"])


def _execution_environment(bundle: AdaptationBundle) -> EnvironmentSpec:
    base = _base_environment()
    return base.model_copy(
        update={
            "initial_placements": tuple(
                ArtifactPlacement(artifact_id=item.artifact_id, agent_id="A28")
                for item in bundle.execution.task.artifacts
            )
        }
    )


def _workload(
    bundle: AdaptationBundle,
    environment: EnvironmentSpec,
    operations: tuple[str, ...],
    *,
    max_agents: int,
) -> WorkloadSpec:
    return WorkloadSpec.from_task_environment(
        bundle.execution.task,
        environment,
        available_operations=operations,
        max_agents=max_agents,
    )


def _alias_environment(aliases: dict[str, str]) -> EnvironmentSpec:
    base = _base_environment()
    deployments = {item.deployment_id: item for item in base.deployments}
    alias_deployments = tuple(
        DeploymentSpec(
            deployment_id=alias,
            agent_id=f"opaque-compute-{index + 1}",
            model_id=deployments[real].model_id,
            modalities=deployments[real].modalities,
            context_window=deployments[real].context_window,
            reserved_output_tokens=deployments[real].reserved_output_tokens,
            image_token_cost=deployments[real].image_token_cost,
        )
        for index, (alias, real) in enumerate(aliases.items())
    )
    agents = tuple(
        base.agents[0].model_copy(
            update={
                "agent_id": deployment.agent_id,
                "device": "opaque model service",
                "capabilities": frozenset({"model"}),
            }
        )
        for deployment in alias_deployments
    )
    return EnvironmentSpec(agents=agents, deployments=alias_deployments)


def _alias_workload(
    bundle: AdaptationBundle,
    aliases: dict[str, str],
    operations: tuple[str, ...],
    max_agents: int,
) -> WorkloadSpec:
    deployments = {item.deployment_id: item for item in _base_environment().deployments}
    return WorkloadSpec(
        available_operations=operations,
        available_model_instances=tuple(
            AvailableModelInstance(
                model_instance_id=alias,
                model_id=deployments[real].model_id,
                modalities=deployments[real].modalities,
            )
            for alias, real in aliases.items()
        ),
        artifacts=tuple(
            WorkloadArtifact(
                artifact_id=item.artifact_id,
                logical_type=item.logical_type,
                media_type=item.media_type,
            )
            for item in bundle.execution.task.artifacts
        ),
        max_agents=max_agents,
    )


def _translate_plan(plan: WorkflowPlan, aliases: dict[str, str]) -> WorkflowPlan:
    return plan.model_copy(
        update={
            "agents": tuple(
                agent.model_copy(update={"model_instance_id": aliases[agent.model_instance_id]})
                for agent in plan.agents
            )
        }
    )


def _canonical_hash(value: object) -> str:
    data = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _code_revision() -> str:
    completed = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _selected_image_provenance(config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    task_rows = cast(list[dict[str, Any]], config["dataset"]["tasks"])
    qids = {str(item["qid"]) for item in task_rows}
    examples = _jsonl_index(DEFAULT_DATASET / "MMQA_dev.jsonl.gz", qids)
    image_ids = {
        str(image_id)
        for qid in qids
        for image_id in examples[qid]["metadata"]["image_doc_ids"]
    }
    image_index = _jsonl_index(DEFAULT_DATASET / "MMQA_images.jsonl.gz", image_ids)
    result: dict[str, list[dict[str, Any]]] = {}
    for row in task_rows:
        label = str(row["label"])
        qid = str(row["qid"])
        values: list[dict[str, Any]] = []
        for raw_image_id in examples[qid]["metadata"]["image_doc_ids"]:
            image_id = str(raw_image_id)
            candidates = list(DEFAULT_IMAGES.glob(f"{image_id}.*"))
            if len(candidates) != 1:
                raise RuntimeError(f"expected exactly one selected image for {image_id}")
            local = candidates[0]
            values.append(
                {
                    "image_id": image_id,
                    "official_index_record": image_index[image_id],
                    "local_filename": local.name,
                    "local_sha256": _file_sha256(local),
                }
            )
        result[label] = values
    return result


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    temporary.replace(path)


def _load_key(path: Path) -> None:
    if os.environ.get("DEEPSEEK_API_KEY"):
        return
    prefix = "DeepSeek API Key:"
    values = [
        line.removeprefix(prefix).strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith(prefix)
    ]
    if len(values) != 1 or not values[0]:
        raise RuntimeError("API key file must contain exactly one DeepSeek key")
    os.environ["DEEPSEEK_API_KEY"] = values[0]


async def _clients(stack: AsyncExitStack) -> dict[str, WorkerClient]:
    clients: dict[str, WorkerClient] = {}
    for agent_id, url in WORKER_URLS.items():
        client = await stack.enter_async_context(httpx.AsyncClient(base_url=url, timeout=900))
        clients[agent_id] = HttpWorkerClient(agent_id, client)
    return clients


async def _remove_artifacts(agent_ids: tuple[str, ...], artifact_ids: tuple[str, ...]) -> None:
    runner = SshCommandRunner()
    for agent_id in agent_ids:
        ssh_target, root = ARTIFACT_ROOTS[agent_id]
        paths = [
            f"{root}/{hashlib.sha256(artifact_id.encode()).hexdigest()}{suffix}"
            for artifact_id in artifact_ids
            for suffix in (".blob", ".json")
        ]
        if paths:
            await runner.run(ssh_target, ("rm", "-f", "--", *paths))


async def _preload(bundle: AdaptationBundle, clients: dict[str, WorkerClient]) -> None:
    await _remove_artifacts(
        ("A4", "A5", "strong-4090"),
        tuple(item.spec.artifact_id for item in bundle.prepared_artifacts),
    )
    for item in bundle.prepared_artifacts:
        response = await clients["A28"].put_artifact(
            item.spec.artifact_id,
            item.spec.media_type,
            item.content,
            item.sha256_hex,
        )
        if response.sha256_hex != item.sha256_hex:
            raise RuntimeError(f"preload checksum mismatch: {item.spec.artifact_id}")


async def _assert_initial_placement(
    bundle: AdaptationBundle, clients: dict[str, WorkerClient]
) -> None:
    expected = {item.spec.artifact_id: item for item in bundle.prepared_artifacts}
    states = {agent_id: await client.get_state() for agent_id, client in clients.items()}
    for artifact_id, prepared in expected.items():
        locations: list[str] = []
        for agent_id, state in states.items():
            metadata = {item.artifact_id: item for item in state.artifacts}.get(artifact_id)
            if metadata is not None:
                if metadata.sha256_hex != prepared.sha256_hex:
                    raise RuntimeError(f"artifact checksum mismatch at {agent_id}/{artifact_id}")
                locations.append(agent_id)
        if locations != ["A28"]:
            raise RuntimeError(f"initial placement mismatch for {artifact_id}: {locations}")


def _load_tc() -> tuple[tuple[TcEndpoint, ...], tuple[int, ...]]:
    raw = _yaml(TC_CONFIG)
    return (
        tuple(TcEndpoint.model_validate(item) for item in raw["tc_endpoints"]),
        tuple(int(item) for item in raw["worker_ports"]),
    )


async def freeze(
    config: dict[str, Any], bundles: dict[str, AdaptationBundle], output: Path
) -> None:
    freeze_root = output / "freeze"
    if freeze_root.exists():
        raise RuntimeError("freeze already exists; refusing to overwrite or call Planner again")
    _load_key(DEFAULT_KEY)
    aliases = {str(k): str(v) for k, v in config["planner"]["model_instance_aliases"].items()}
    operations = tuple(str(item) for item in config["planner"]["available_operations"])
    max_agents = int(config["planner"]["max_agents"])
    alias_environment = _alias_environment(aliases)
    registry = build_operator_catalog()
    planner_config = load_planner_config(REPO / str(config["planner"]["config"]))
    backend, client = build_model_backend(planner_config.model)
    image_provenance = _selected_image_provenance(config)
    manifest: dict[str, Any] = {
        "experiment_id": config["experiment_id"],
        "code_revision": _code_revision(),
        "source_revision": config["dataset"]["source_revision"],
        "source_file_sha256": {
            name: _file_sha256(DEFAULT_DATASET / name)
            for name in (
                "MMQA_dev.jsonl.gz",
                "MMQA_texts.jsonl.gz",
                "MMQA_tables.jsonl.gz",
                "MMQA_images.jsonl.gz",
            )
        },
        "official_evaluator_source_sha256": _file_sha256(
            REPO / "artifacts/multimodalqa-official/baselines/evaluate.py"
        ),
        "selection_rule": config["dataset"]["selection_rule"],
        "planner_calls_per_task": 1,
        "planner_and_agent_views_exclude": [
            "source_ref",
            "evaluator_id",
            "answers",
            "supporting_context",
            "intermediate_answers",
        ],
        "tasks": {},
    }
    try:
        for label, bundle in bundles.items():
            task_root = freeze_root / label
            planner_workload = _alias_workload(bundle, aliases, operations, max_agents)
            planner = LLMWorkflowPlanner(backend, registry, alias_environment)
            prompt = planner.render_prompt(bundle.execution.task, planner_workload)
            started = perf_counter()
            outcome = await planner.plan(bundle.execution.task, planner_workload)
            latency_ms = (perf_counter() - started) * 1000
            execution_plan = _translate_plan(outcome.plan, aliases)
            execution_environment = _execution_environment(bundle)
            execution_plan.validate_against(bundle.execution.task, execution_environment, registry)
            execution_workload = _workload(
                bundle, execution_environment, operations, max_agents=max_agents
            )
            planner_json = outcome.plan.model_dump(mode="json")
            execution_json = execution_plan.model_dump(mode="json")
            planner_hash = _canonical_hash(planner_json)
            execution_hash = _canonical_hash(execution_json)
            _write_json(
                task_root / "task-planner-view.json",
                logical_task_payload(bundle.execution.task),
            )
            private_root = output / "private" / label
            _write_json(
                private_root / "task-contract.json",
                bundle.execution.task.model_dump(mode="json"),
            )
            _write_json(
                task_root / "workload-planner-view.json", planner_workload.model_dump(mode="json")
            )
            _write_json(
                task_root / "workload-execution.json", execution_workload.model_dump(mode="json")
            )
            _write_json(task_root / "planner-workflow-plan.json", planner_json)
            _write_json(task_root / "workflow-plan.json", execution_json)
            (task_root / "planner-prompt.txt").write_text(prompt, encoding="utf-8")
            _write_json(
                task_root / "planner-call.json",
                {
                    "call_count": 1,
                    "latency_ms": latency_ms,
                    "model_telemetry": (
                        outcome.model_telemetry.model_dump(mode="json")
                        if outcome.model_telemetry
                        else None
                    ),
                    "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                    "planner_plan_sha256": planner_hash,
                    "workflow_plan_sha256": execution_hash,
                },
            )
            private_evaluation = cast(PrivateMultiModalQAEvaluation, bundle.private_evaluation)
            _write_json(
                private_root / "private-evaluation.json",
                private_evaluation.model_dump(mode="json"),
            )
            manifest["tasks"][label] = {
                "task_id": bundle.execution.task.task_id,
                "public_representation_sha256": bundle_public_digest(bundle),
                "planner_plan_sha256": planner_hash,
                "workflow_plan_sha256": execution_hash,
                "artifact_placement": {
                    item.spec.artifact_id: "A28" for item in bundle.prepared_artifacts
                },
                "adaptation_provenance": {
                    "transformations": [
                        item.model_dump(mode="json")
                        for item in bundle.execution.transformations
                    ],
                    "validity": bundle.execution.validity.model_dump(mode="json"),
                },
                "selected_image_provenance": image_provenance[label],
                "artifacts": [
                    {
                        "artifact_id": item.spec.artifact_id,
                        "media_type": item.spec.media_type,
                        "size_bytes": item.spec.size_bytes,
                        "sha256": item.sha256_hex,
                    }
                    for item in bundle.prepared_artifacts
                ],
            }
    finally:
        if client is not None:
            await client.close()
    _write_json(freeze_root / "manifest.json", manifest)
    _write_json(freeze_root / "schedule.json", config["schedule"])


def _load_frozen_plan(output: Path, label: str) -> WorkflowPlan:
    return WorkflowPlan.model_validate_json(
        (output / "freeze" / label / "workflow-plan.json").read_text(encoding="utf-8")
    )


def _validate_freeze(
    config: dict[str, Any], bundles: dict[str, AdaptationBundle], output: Path
) -> None:
    manifest = json.loads((output / "freeze/manifest.json").read_text(encoding="utf-8"))
    if manifest["planner_calls_per_task"] != 1:
        raise RuntimeError("frozen planner call count is not exactly one")
    aliases = {str(k): str(v) for k, v in config["planner"]["model_instance_aliases"].items()}
    for label, bundle in bundles.items():
        entry = manifest["tasks"][label]
        if entry["public_representation_sha256"] != bundle_public_digest(bundle):
            raise RuntimeError(f"public representation drift: {label}")
        plan = _load_frozen_plan(output, label)
        plan.terminal_model_node()
        if entry["workflow_plan_sha256"] != _canonical_hash(plan.model_dump(mode="json")):
            raise RuntimeError(f"workflow plan hash mismatch: {label}")
        prompt = (output / "freeze" / label / "planner-prompt.txt").read_text(encoding="utf-8")
        private_evaluation = cast(PrivateMultiModalQAEvaluation, bundle.private_evaluation)
        private: dict[str, Any] = private_evaluation.model_dump(mode="json")
        private_tokens = [
            bundle.execution.task.evaluator_id,
            *(
                item.source_ref
                for item in bundle.execution.task.artifacts
                if item.source_ref is not None
            ),
        ]
        private_tokens.extend(str(item) for item in private.get("gold_answers", []))
        private_tokens.extend(
            json.dumps(item, ensure_ascii=False) for item in private.get("supporting_context", [])
        )
        private_tokens.extend(
            json.dumps(item, ensure_ascii=False) for item in private.get("intermediate_answers", [])
        )
        if any(token and token in prompt for token in private_tokens):
            raise RuntimeError(f"private evaluation leakage into planner prompt: {label}")
        if any(alias in json.dumps(plan.model_dump()) for alias in aliases):
            raise RuntimeError(f"untranslated planner alias in execution plan: {label}")


async def preflight(
    config: dict[str, Any], bundles: dict[str, AdaptationBundle], output: Path
) -> None:
    _validate_freeze(config, bundles, output)
    registry = build_operator_catalog()
    base = _base_environment()
    report: dict[str, Any] = {"workers": {}, "image_model_calls": {}}
    probe = next(
        item
        for item in bundles["image-table"].prepared_artifacts
        if item.spec.media_type.startswith("image/")
    )
    probe_id = "open-ended-mas-v1-image-capability-probe"
    try:
        async with AsyncExitStack() as stack:
            clients = await _clients(stack)
            await validate_worker_surfaces(base, registry, clients)
            for agent_id, deployment_id in (
                ("A28", "a28-qwen3.8-27b-q4km-v1"),
                ("strong-4090", "strong-4090-qwen3.8-27b-q4km-v1"),
            ):
                state = await clients[agent_id].get_state()
                if not state.available or state.in_flight != 0:
                    raise RuntimeError(f"worker is not idle and available: {agent_id}")
                report["workers"][agent_id] = state.model_dump(mode="json")
                await clients[agent_id].put_artifact(
                    probe_id, probe.spec.media_type, probe.content, probe.sha256_hex
                )
                response = await clients[agent_id].execute_operator(
                    SemanticAction(
                        operator="invoke_model",
                        inputs=(probe_id,),
                        arguments={
                            "prompt": "Confirm image input availability; answer only IMAGE_OK."
                        },
                    ),
                    deployment_id,
                )
                if response.model_telemetry is None:
                    raise RuntimeError(f"image model probe lacks telemetry: {agent_id}")
                report["image_model_calls"][agent_id] = response.model_dump(mode="json")
    finally:
        await _remove_artifacts(("A28", "strong-4090"), (probe_id,))
    _write_json(output / "preflight.json", report)


def _generated_ids(plan: WorkflowPlan) -> tuple[str, ...]:
    return tuple(value for node in plan.nodes for value in node.outputs)


def _result_validity_error(result: PersistedWorkflowRunResult) -> str | None:
    if not result.execution_completed:
        code = result.failure.code if result.failure else "missing_failure"
        return f"execution failed: {code}"
    if result.evaluation is None or not result.evaluation.format_valid:
        return "evaluator/output format invalid"
    if result.workflow is None or not result.workflow.completed:
        return "workflow did not complete"
    model_reasons = tuple(
        record.execution.model_telemetry.finish_reason
        for record in result.workflow.records
        if record.execution is not None and record.execution.model_telemetry is not None
    )
    if any(reason != "stop" for reason in model_reasons):
        return f"model finish reason is not stop: {model_reasons}"
    return None


async def _native_network_snapshot() -> dict[str, str]:
    raw = _yaml(PREFLIGHT_CONFIG)
    endpoints = tuple(TcEndpoint.model_validate(item) for item in raw["tc_endpoints"])
    runner = SshCommandRunner()
    snapshot = {
        endpoint.agent_id: await runner.run(
            endpoint.ssh_target,
            ("sudo", "-n", "tc", "qdisc", "show", "dev", endpoint.interface),
        )
        for endpoint in endpoints
    }
    shaped = {
        agent_id: value
        for agent_id, value in snapshot.items()
        if "qdisc htb 1:" in value or "netem" in value
    }
    if shaped:
        raise RuntimeError(f"native smoke found active traffic shaping: {sorted(shaped)}")
    return snapshot


def _trace_audit(
    trace_path: Path,
    run_id: str,
    bundle: AdaptationBundle,
) -> dict[str, Any]:
    events = [
        cast(dict[str, Any], json.loads(line))
        for line in trace_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    chain_valid = bool(events) and all(
        event["run_id"] == run_id
        and event["step_id"].startswith(f"{index:06d}-")
        and event["parent_id"] == (events[index - 1]["step_id"] if index else None)
        for index, event in enumerate(events)
    )
    event_types = {str(event["event_type"]) for event in events}
    required = {
        "workflow.planner.end",
        "workflow.execution.start",
        "workflow.execution.end",
        "finalize.end",
        "evaluation.result",
        "run.end",
    }
    agent_events = [event for event in events if str(event["event_type"]).startswith("agent.")]
    agent_payload = json.dumps(agent_events, ensure_ascii=False, sort_keys=True)
    forbidden_keys = {
        "source_ref",
        "evaluator_id",
        "gold_answers",
        "supporting_context",
        "intermediate_answers",
    }
    forbidden_values = {
        bundle.execution.task.evaluator_id,
        *(
            item.source_ref
            for item in bundle.execution.task.artifacts
            if item.source_ref is not None
        ),
    }
    leakage = sorted(
        value
        for value in (*forbidden_keys, *forbidden_values)
        if value and value in agent_payload
    )
    handoffs: list[dict[str, str]] = []
    for event in agent_events:
        if event["event_type"] != "agent.information.received":
            continue
        payload = cast(dict[str, Any], event["payload"])
        information = cast(dict[str, Any], payload["information"])
        producer = str(information["producer_agent_id"])
        consumer = str(payload["agent_id"])
        if producer not in {"task", consumer}:
            handoffs.append(
                {
                    "object_id": str(information["object_id"]),
                    "producer_agent_id": producer,
                    "consumer_agent_id": consumer,
                }
            )
    return {
        "event_count": len(events),
        "sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest(),
        "parent_chain_valid": chain_valid,
        "required_events_present": not (required - event_types),
        "missing_required_events": sorted(required - event_types),
        "agent_private_leakage": leakage,
        "explicit_cross_agent_information_handoffs": handoffs,
        "reconstructable": chain_valid and not (required - event_types),
    }


def _workflow_shape(plan: WorkflowPlan) -> dict[str, Any]:
    agents = {item.agent_id: item for item in plan.agents}
    fan_out: dict[str, int] = {item.node_id: 0 for item in plan.nodes}
    fan_in: dict[str, int] = {item.node_id: 0 for item in plan.nodes}
    cross_agent_edges: list[dict[str, str]] = []
    nodes = {item.node_id: item for item in plan.nodes}
    for edge in plan.edges:
        fan_out[edge.producer_node] += 1
        fan_in[edge.consumer_node] += 1
        producer = nodes[edge.producer_node].agent_id
        consumer = nodes[edge.consumer_node].agent_id
        if producer != consumer:
            cross_agent_edges.append(
                {
                    "artifact_id": edge.artifact_id,
                    "producer_agent_id": producer,
                    "consumer_agent_id": consumer,
                }
            )
    terminal = plan.terminal_model_node()
    invoke_model_agents = {
        item.agent_id for item in plan.nodes if item.operator == "invoke_model"
    }
    successors: dict[str, set[str]] = {item.node_id: set() for item in plan.nodes}
    for edge in plan.edges:
        successors[edge.producer_node].add(edge.consumer_node)

    def reaches_terminal(node_id: str) -> bool:
        pending = list(successors[node_id])
        visited: set[str] = set()
        while pending:
            current = pending.pop()
            if current == terminal.node_id:
                return True
            if current not in visited:
                visited.add(current)
                pending.extend(successors[current])
        return False

    model_handoffs_to_terminal = [
        {
            "artifact_id": edge.artifact_id,
            "producer_node_id": edge.producer_node,
            "producer_agent_id": nodes[edge.producer_node].agent_id,
            "consumer_agent_id": nodes[edge.consumer_node].agent_id,
        }
        for edge in plan.edges
        if nodes[edge.producer_node].operator == "invoke_model"
        and nodes[edge.producer_node].agent_id != nodes[edge.consumer_node].agent_id
        and reaches_terminal(edge.producer_node)
    ]
    return {
        "active_logical_agent_count": len(agents),
        "roles_objectives": {
            agent_id: {"role": item.role, "objective": item.objective}
            for agent_id, item in agents.items()
        },
        "model_bindings": {
            agent_id: item.model_instance_id for agent_id, item in agents.items()
        },
        "invoke_model_agents": sorted(invoke_model_agents),
        "fan_out_nodes": {
            node_id: count for node_id, count in fan_out.items() if count > 1
        },
        "fan_in_nodes": {node_id: count for node_id, count in fan_in.items() if count > 1},
        "cross_agent_edges": cross_agent_edges,
        "unique_terminal_model_node": terminal.node_id,
        "terminal_model_agent": terminal.agent_id,
        "model_handoffs_to_terminal": model_handoffs_to_terminal,
        "non_trivial_mas": (
            len(agents) > 1
            and len(invoke_model_agents) > 1
            and bool(model_handoffs_to_terminal)
        ),
    }


def _smoke_audit(
    output: Path,
    run_id: str,
    label: str,
    bundle: AdaptationBundle,
    plan: WorkflowPlan,
    result: PersistedWorkflowRunResult,
) -> dict[str, Any]:
    if result.workflow is None:
        raise RuntimeError("completed smoke result is missing workflow evidence")
    shape = _workflow_shape(plan)
    trace = _trace_audit(Path(result.trace_path), run_id, bundle)
    evaluation = result.evaluation
    validity = bundle.execution.validity
    benchmark_faithful = (
        validity.information_equivalent
        and validity.query_equivalent
        and validity.evaluator_equivalent
        and not trace["agent_private_leakage"]
    )
    quality_pass = bool(
        evaluation is not None
        and evaluation.format_valid
        and evaluation.benchmark_score == 1.0
    )
    audit: dict[str, Any] = {
        "run_id": run_id,
        "task": label,
        "task_id": bundle.execution.task.task_id,
        "workflow_plan_sha256": _canonical_hash(plan.model_dump(mode="json")),
        "benchmark_faithful": benchmark_faithful,
        "adaptation": bundle.execution.model_dump(mode="json"),
        "workflow_shape": shape,
        "information_objects": {
            "explicit_handoffs": trace["explicit_cross_agent_information_handoffs"],
            "handoff_observed": bool(trace["explicit_cross_agent_information_handoffs"]),
        },
        "node_final_states": result.workflow.state.node_status,
        "agent_final_states": {
            item.agent_id: item.status for item in result.workflow.agent_states
        },
        "actual_placements": {
            item.node_id: list(item.execution.agent_ids)
            for item in result.workflow.records
            if item.execution is not None
        },
        "execution_bindings": {
            item.node_id: {
                "logical_agent_id": item.scheduler_decision.logical_agent_id,
                "selected_agent_id": item.scheduler_decision.selected_agent_id,
                "selected_deployment_id": item.scheduler_decision.selected_deployment_id,
                "actual_agent_ids": list(item.execution.agent_ids),
                "actual_deployment_id": item.execution.deployment_id,
            }
            for item in result.workflow.records
            if item.execution is not None
        },
        "transfers": {
            "initial": [item.model_dump(mode="json") for item in result.initial_transfers],
            "workflow": [
                {
                    "node_id": record.node_id,
                    **transfer.model_dump(mode="json"),
                }
                for record in result.workflow.records
                if record.execution is not None
                for transfer in record.execution.transfers
            ],
        },
        "transfer_bytes": result.telemetry.total_transfer_bytes if result.telemetry else None,
        "transfer_time_ms": (
            result.telemetry.total_transfer_duration_ms if result.telemetry else None
        ),
        "trace": trace,
        "terminal_answer": result.final_answer,
        "format_valid": evaluation.format_valid if evaluation else None,
        "benchmark_score": evaluation.benchmark_score if evaluation else None,
        "evaluator_details": evaluation.details if evaluation else None,
        "execution_success": result.execution_completed and result.workflow.completed,
        "quality_pass": quality_pass,
        "quality_policy": {
            "metric": "multimodalqa_official_list_f1",
            "operator": "==",
            "threshold": 1.0,
        },
    }
    audit["freeze_accepted"] = bool(
        benchmark_faithful
        and shape["non_trivial_mas"]
        and audit["execution_success"]
        and quality_pass
        and trace["reconstructable"]
        and audit["information_objects"]["handoff_observed"]
    )
    if not shape["non_trivial_mas"]:
        audit["pause_reason"] = "planner produced a single-agent or trivial workflow"
    elif not quality_pass:
        audit["pause_reason"] = "terminal answer did not pass the original evaluator"
    elif not audit["freeze_accepted"]:
        audit["pause_reason"] = "smoke acceptance invariant failed"
    else:
        audit["pause_reason"] = None
        accepted_root = output / "accepted-freeze" / label
        _write_json(accepted_root / "workflow-plan.json", plan.model_dump(mode="json"))
        _write_json(
            accepted_root / "freeze-record.json",
            {
                "task_id": bundle.execution.task.task_id,
                "canonical_sha256": audit["workflow_plan_sha256"],
                "source": str(output / "freeze" / label / "workflow-plan.json"),
            },
        )
    return audit


async def run_native_smoke(
    config: dict[str, Any], bundles: dict[str, AdaptationBundle], output: Path
) -> None:
    _validate_freeze(config, bundles, output)
    operations = tuple(str(item) for item in config["planner"]["available_operations"])
    max_agents = int(config["planner"]["max_agents"])
    planner_config = load_planner_config(REPO / str(config["planner"]["config"]))
    network_snapshot = await _native_network_snapshot()
    task_labels = [str(item["label"]) for item in config["dataset"]["tasks"]]
    if len(task_labels) != 2 or set(task_labels) != set(bundles):
        raise RuntimeError("Blind Baseline Smoke requires exactly the two frozen tasks")
    manifest: dict[str, Any] = {
        "experiment": "blind-baseline-smoke",
        "code_revision": _code_revision(),
        "network": "native_unshaped",
        "qdisc_snapshot": network_snapshot,
        "scheduler": "B0_LOCALITY_AWARE_MYOPIC",
        "n": 1,
        "retry": False,
        "replacement": False,
        "runs": [],
        "stopped_on_confounder": None,
    }
    for index, label in enumerate(task_labels, start=1):
        run_id = f"{index:02d}-{label}-native"
        run_root = output / "runs" / run_id
        if run_root.exists():
            raise RuntimeError(f"run already exists; no retry or overwrite allowed: {run_id}")
        bundle = bundles[label]
        plan = _load_frozen_plan(output, label)
        shape = _workflow_shape(plan)
        environment = _execution_environment(bundle)
        runner_config = RunnerConfig(
            environment=environment,
            worker_urls=WORKER_URLS,
            planner=planner_config,
            output_root=output / "runs",
            http_timeout_seconds=900,
        )
        metadata: dict[str, Any] = {
            "run_id": run_id,
            "task": label,
            "network": "native_unshaped",
            "validity_error": None,
            "artifact_cleanup_error": None,
        }
        result: PersistedWorkflowRunResult | None = None
        if not shape["non_trivial_mas"]:
            metadata["paused_before_execution"] = True
            metadata["pause_reason"] = (
                "planner produced a single-agent or trivial workflow; no forced MAS execution"
            )
            metadata["workflow_shape"] = shape
            _write_json(run_root / "experiment-metadata.json", metadata)
            manifest["runs"].append(metadata)
            _write_json(output / "smoke-manifest.json", manifest)
            continue
        try:
            async with AsyncExitStack() as stack:
                clients = await _clients(stack)
                await validate_worker_surfaces(environment, build_operator_catalog(), clients)
                await _preload(bundle, clients)
                await _assert_initial_placement(bundle, clients)
                result = await PrepositionedWorkflowRunner(
                    runner_config,
                    _workload(bundle, environment, operations, max_agents=max_agents),
                    LocalityAwareMyopicScheduler(),
                    worker_clients=clients,
                    planner=ScriptedWorkflowPlanner((plan,)),
                ).run(bundle, run_id=run_id)
                metadata["validity_error"] = _result_validity_error(result)
        except Exception as exc:
            metadata["validity_error"] = f"{type(exc).__name__}: {exc}"
        finally:
            try:
                await _remove_artifacts(
                    ("A4", "A5", "A28", "strong-4090"), _generated_ids(plan)
                )
                await _remove_artifacts(
                    ("A4", "A5", "strong-4090"),
                    tuple(item.spec.artifact_id for item in bundle.prepared_artifacts),
                )
            except Exception as exc:
                metadata["artifact_cleanup_error"] = f"{type(exc).__name__}: {exc}"
        if result is not None and metadata["validity_error"] is None:
            audit = _smoke_audit(output, run_id, label, bundle, plan, result)
            _write_json(run_root / "smoke-audit.json", audit)
            metadata["audit"] = audit
        _write_json(run_root / "experiment-metadata.json", metadata)
        manifest["runs"].append(metadata)
        _write_json(output / "smoke-manifest.json", manifest)
        if metadata["validity_error"] or metadata["artifact_cleanup_error"]:
            manifest["stopped_on_confounder"] = run_id
            _write_json(output / "smoke-manifest.json", manifest)
            raise RuntimeError(f"fail-closed after {run_id}: {metadata}")
    _write_json(output / "smoke-manifest.json", manifest)


async def run_matrix(
    config: dict[str, Any], bundles: dict[str, AdaptationBundle], output: Path
) -> None:
    _validate_freeze(config, bundles, output)
    if not (output / "preflight.json").exists():
        raise RuntimeError("preflight evidence is missing")
    operations = tuple(str(item) for item in config["planner"]["available_operations"])
    max_agents = int(config["planner"]["max_agents"])
    planner_config = load_planner_config(REPO / str(config["planner"]["config"]))
    regimes = {str(item["id"]): item for item in config["network"]["regimes"]}
    endpoints, ports = _load_tc()
    schedule = cast(list[dict[str, str]], config["schedule"])
    matrix_manifest: dict[str, Any] = {
        "experiment_id": config["experiment_id"],
        "n": 1,
        "retry": False,
        "replacement": False,
        "scheduler": "B0_LOCALITY_AWARE_MYOPIC",
        "runs": [],
        "stopped_on_confounder": None,
    }
    for index, cell in enumerate(schedule, start=1):
        label, regime_id = cell["task"], cell["regime"]
        run_id = f"{index:02d}-{label}-{regime_id}"
        run_root = output / "runs" / run_id
        if run_root.exists():
            raise RuntimeError(f"run already exists; no retry or overwrite allowed: {run_id}")
        bundle = bundles[label]
        plan = _load_frozen_plan(output, label)
        environment = _execution_environment(bundle)
        runner_config = RunnerConfig(
            environment=environment,
            worker_urls=WORKER_URLS,
            planner=planner_config,
            output_root=output / "runs",
            http_timeout_seconds=900,
        )
        bandwidth = float(regimes[regime_id]["bandwidth_mbps"])
        tc_regime = TcRegime(
            configuration_id=f"open-ended-mas-v1-{regime_id}",
            bandwidth_mbps=bandwidth,
            added_rtt_ms=float(config["network"]["added_rtt_ms"]),
            worker_ports=ports,
        )
        controller = TcController(SshCommandRunner())
        metadata: dict[str, Any] = {
            "run_id": run_id,
            "task": label,
            "task_id": bundle.execution.task.task_id,
            "regime": regime_id,
            "bandwidth_mbps": bandwidth,
            "added_rtt_ms": tc_regime.added_rtt_ms,
            "workflow_plan_sha256": _canonical_hash(plan.model_dump(mode="json")),
            "tc_cleanup_error": None,
            "artifact_cleanup_error": None,
            "validity_error": None,
        }
        result: PersistedWorkflowRunResult | None = None
        run_error: Exception | None = None
        await controller.apply(tuple(build_tc_command_plan(item, tc_regime) for item in endpoints))
        try:
            async with AsyncExitStack() as stack:
                clients = await _clients(stack)
                await validate_worker_surfaces(environment, build_operator_catalog(), clients)
                await _preload(bundle, clients)
                await _assert_initial_placement(bundle, clients)
                result = await PrepositionedWorkflowRunner(
                    runner_config,
                    _workload(bundle, environment, operations, max_agents=max_agents),
                    LocalityAwareMyopicScheduler(),
                    worker_clients=clients,
                    planner=ScriptedWorkflowPlanner((plan,)),
                ).run(bundle, run_id=run_id)
                metadata["validity_error"] = _result_validity_error(result)
        except Exception as exc:  # persist driver-level failures and stop fail-closed
            run_error = exc
            metadata["validity_error"] = f"{type(exc).__name__}: {exc}"
        finally:
            try:
                metadata["tc_class_statistics"] = {
                    endpoint.agent_id: await SshCommandRunner().run(
                        endpoint.ssh_target,
                        ("sudo", "-n", "tc", "-s", "class", "show", "dev", endpoint.interface),
                    )
                    for endpoint in endpoints
                }
                if any(
                    "class htb 1:20" not in value
                    for value in metadata["tc_class_statistics"].values()
                ):
                    metadata["validity_error"] = "tc shaped class 1:20 was absent"
            except Exception as exc:
                metadata["validity_error"] = f"tc verification failed: {type(exc).__name__}: {exc}"
            try:
                await controller.cleanup()
            except Exception as exc:
                metadata["tc_cleanup_error"] = f"{type(exc).__name__}: {exc}"
            try:
                await _remove_artifacts(("A4", "A5", "A28", "strong-4090"), _generated_ids(plan))
                await _remove_artifacts(
                    ("A4", "A5", "strong-4090"),
                    tuple(item.spec.artifact_id for item in bundle.prepared_artifacts),
                )
            except Exception as exc:
                metadata["artifact_cleanup_error"] = f"{type(exc).__name__}: {exc}"
        _write_json(run_root / "experiment-metadata.json", metadata)
        matrix_manifest["runs"].append(metadata)
        _write_json(output / "matrix-manifest.json", matrix_manifest)
        invalid = (
            metadata["validity_error"]
            or metadata["tc_cleanup_error"]
            or metadata["artifact_cleanup_error"]
            or run_error is not None
        )
        if invalid:
            matrix_manifest["stopped_on_confounder"] = run_id
            _write_json(output / "matrix-manifest.json", matrix_manifest)
            raise RuntimeError(f"fail-closed after {run_id}: {metadata}")
        if result is None:
            raise RuntimeError(f"run produced no persisted result: {run_id}")


def _static_width(plan: WorkflowPlan) -> int:
    predecessors: dict[str, set[str]] = {node.node_id: set() for node in plan.nodes}
    for edge in plan.edges:
        predecessors[edge.consumer_node].add(edge.producer_node)
    levels: dict[str, int] = {}
    while len(levels) < len(plan.nodes):
        progress = False
        for node in plan.nodes:
            if node.node_id in levels or not predecessors[node.node_id] <= levels.keys():
                continue
            levels[node.node_id] = 1 + max(
                (levels[item] for item in predecessors[node.node_id]), default=-1
            )
            progress = True
        if not progress:
            raise RuntimeError("workflow is cyclic")
    return max((list(levels.values()).count(level) for level in set(levels.values())), default=0)


def report(config: dict[str, Any], output: Path) -> None:
    manifest_path = output / "matrix-manifest.json"
    if not manifest_path.exists():
        raise RuntimeError("matrix manifest is missing")
    matrix = json.loads(manifest_path.read_text(encoding="utf-8"))
    if matrix["stopped_on_confounder"] is not None or len(matrix["runs"]) != 6:
        raise RuntimeError("six valid primary runs are required before report generation")
    workflow_rows: list[str] = []
    for row in config["dataset"]["tasks"]:
        label = row["label"]
        plan = _load_frozen_plan(output, label)
        roles = "; ".join(f"{item.agent_id}: {item.role}" for item in plan.agents)
        bindings = "; ".join(f"{item.agent_id}→{item.model_instance_id}" for item in plan.agents)
        workflow_rows.append(
            f"| {label} | {len(plan.agents)} | {len(plan.nodes)} | {len(plan.edges)} | "
            f"{_static_width(plan)} | `{_canonical_hash(plan.model_dump(mode='json'))}` | "
            f"{roles} | {bindings} |"
        )
    run_rows: list[str] = []
    paths: list[str] = []
    failure_notes: list[str] = []
    for run in matrix["runs"]:
        result = json.loads(
            (output / "runs" / run["run_id"] / "result.json").read_text(encoding="utf-8")
        )
        workflow = result["workflow"]
        telemetry = result["telemetry"]
        placements = "; ".join(
            f"{item['node_id']}->{','.join(item['execution']['agent_ids'])}"
            for item in workflow["records"]
        )
        run_rows.append(
            f"| {run['run_id']} | {run['task']} | {run['regime']} | "
            f"{result['evaluation']['benchmark_score']:.2f} | "
            f"{result['evaluation']['format_valid']} | "
            f"{result['runner_e2e_latency_ms']:.1f} | {telemetry['total_transfer_bytes']} | "
            f"{telemetry['total_transfer_duration_ms']:.1f} | "
            f"{workflow['telemetry']['total_operator_latency_ms']:.1f} | "
            f"{workflow['telemetry']['total_model_service_latency_ms']:.1f} | "
            f"{workflow['telemetry']['parallel_overlap_ms']:.1f} | "
            f"{workflow['telemetry']['critical_path_latency_ms']:.1f} | {placements} |"
        )
        paths.append(
            f"- `{run['run_id']}`: " + " -> ".join(item["node_id"] for item in workflow["records"])
        )
    plans = [_load_frozen_plan(output, row["label"]) for row in config["dataset"]["tasks"]]
    if any(len(plan.agents) < 2 for plan in plans):
        failure_notes.append(
            "Planner did not create a genuinely multi-agent workflow for at least one task."
        )
    if any(_static_width(plan) < 2 for plan in plans):
        failure_notes.append("At least one frozen DAG has no nominal parallel branch.")
    results = [
        json.loads((output / "runs" / row["run_id"] / "result.json").read_text(encoding="utf-8"))
        for row in matrix["runs"]
    ]
    if any(item["workflow"]["telemetry"]["max_parallelism"] < 2 for item in results):
        failure_notes.append(
            "Nominal workflow parallelism did not consistently become physical overlap."
        )
    if not failure_notes:
        failure_notes.append(
            "No listed failure mode is asserted without a task-level timing comparison; "
            "see run table."
        )
    report_path = REPO / "docs/open-ended-mas-preliminary-v1-report.md"
    report_path.write_text(
        "\n".join(
            [
                "# Open-ended MAS Workflow Preliminary Experiment v1",
                "",
                "## Scope and exact settings",
                "",
                "Two deterministically selected MultiModalQA dev tasks; one Planner call per task; "
                "the resulting workflow is frozen and replayed unchanged at 3/10/30 Mbps with "
                "20 ms added RTT. All source artifacts begin only on A28. B0 Locality-Aware "
                "Myopic scheduling is unchanged. Each cell has n=1, no retry, no replacement.",
                "",
                "Planner input contains TaskContract, opaque available model instances, and "
                "logical "
                "operator schemas. It excludes bandwidth, RTT, physical placement, load, gold, "
                "supporting context, and intermediate answers. The exact freeze and hashes are in "
                f"`{output / 'freeze'}`.",
                "",
                "## Frozen workflows",
                "",
                "| Task | Agents | Nodes | Edges | Static width | SHA-256 | Roles | Bindings |",
                "|---|---:|---:|---:|---:|---|---|---|",
                *workflow_rows,
                "",
                "## Six primary runs",
                "",
                "| Run | Task | Regime | Score | Format | E2E ms | Transfer B | "
                "Transfer ms | Operator ms | Model ms | Overlap ms | Critical path ms | "
                "Actual placements |",
                "|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|",
                *run_rows,
                "",
                "## Execution paths",
                "",
                *paths,
                "",
                "## Orchestration failure-mode audit",
                "",
                *(f"- {item}" for item in failure_notes),
                "",
                "The audit checks: non-MAS or non-parallel planning, myopic placement, excessive "
                "movement, communication-critical branches, contention, and nominal parallelism "
                "without E2E benefit. With n=1 these observations are diagnostic, not causal or "
                "statistically stable claims.",
                "",
                "## B1 decision",
                "",
                "B1 is not implemented or run in this stage. The evidence above can justify a "
                "separate B1 study only if it shows a concrete B0 placement/communication failure; "
                "it cannot establish B1 superiority.",
                "",
                "## Limits",
                "",
                "This six-run preliminary experiment cannot support benchmark-level accuracy, a "
                "bandwidth crossover estimate, scheduler superiority, or generalization beyond the "
                "two frozen tasks and current hardware/model instances.",
                "",
            ]
        ),
        encoding="utf-8",
    )


async def main_async(args: argparse.Namespace) -> None:
    config = _yaml(args.config)
    bundles = _load_bundles(config, args.dataset, args.images)
    if args.command == "freeze":
        await freeze(config, bundles, args.output)
    elif args.command == "preflight":
        await preflight(config, bundles, args.output)
    elif args.command == "run":
        _load_key(args.api_key_file)
        await run_matrix(config, bundles, args.output)
    elif args.command == "native-smoke":
        await run_native_smoke(config, bundles, args.output)
    elif args.command == "report":
        report(config, args.output)
    elif args.command == "all":
        await freeze(config, bundles, args.output)
        await preflight(config, bundles, args.output)
        await run_matrix(config, bundles, args.output)
        report(config, args.output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("freeze", "preflight", "native-smoke", "run", "report", "all"),
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--images", type=Path, default=DEFAULT_IMAGES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--api-key-file", type=Path, default=DEFAULT_KEY)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main_async(parse_args()))
