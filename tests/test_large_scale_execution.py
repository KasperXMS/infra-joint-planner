import importlib
import inspect
import json
import sys
from pathlib import Path

import pytest
from test_native_agents import benchmark_task

from infra_joint.benchmarks.base import (
    AdaptationBundle,
    AdaptedExecutionCase,
    PreparedArtifact,
    PrivateChoiceEvaluation,
    assess_validity,
)
from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.large_scale_protocol import ScheduledCell, SelectedTask

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
execution = importlib.import_module("large_scale_execution_v1")
preparation = importlib.import_module("large_scale_task_selection_v1")


def frozen_fixture(tmp_path: Path) -> tuple[dict, Path]:
    task = benchmark_task()
    content = b'[{"body":"synthetic evidence"}]'
    spec = task.artifacts[0].model_copy(update={"size_bytes": len(content)})
    task = task.model_copy(update={"artifacts": (spec,)})
    bundle = AdaptationBundle(
        AdaptedExecutionCase(task=task, transformations=(), validity=assess_validity(
            (), query_equivalent=True, evaluator_equivalent=True)),
        PrivateChoiceEvaluation(task_id=task.task_id, evaluator_id=task.evaluator_id,
                                gold_answer="A"), (PreparedArtifact.create(spec, content),))
    row = preparation.persist_bundle(tmp_path, SelectedTask("longbench_v2", "synthetic", 1),
                                     bundle, {"revision": "synthetic"}, ("A4",))
    return {"tasks": [row]}, tmp_path / "longbench_v2-1"


@pytest.mark.asyncio
async def test_strict_frozen_reload_preserves_original_contract_and_bytes(tmp_path: Path) -> None:
    manifest, _ = frozen_fixture(tmp_path)
    bundle, row = execution.frozen_task(tmp_path, manifest, "longbench_v2", 1)
    assert bundle.execution.task.output_contract == benchmark_task().output_contract
    result = await bundle.private_evaluation.build_evaluator().evaluate(bundle.execution.task, "A")
    assert result.benchmark_score == 1 and result.format_valid
    assert row["artifacts"][0]["initial_worker"] == "A4"
    assert bundle.prepared_artifacts[0].content == b'[{"body":"synthetic evidence"}]'


@pytest.mark.parametrize("target", ["execution", "private", "artifact", "evaluator", "path"])
def test_frozen_reload_rejects_task_gold_artifact_evaluator_and_namespace_drift(
    tmp_path: Path, target: str,
) -> None:
    manifest, folder = frozen_fixture(tmp_path)
    if target == "execution":
        path = folder / "execution.json"
        value = json.loads(path.read_text())
        value["task"]["objective"] = "Changed query"
        path.write_text(json.dumps(value))
    elif target == "private":
        path = folder / "private-evaluation.json"
        value = json.loads(path.read_text())
        value["gold_answer"] = "B"
        path.write_text(json.dumps(value))
    elif target == "artifact":
        Path(manifest["tasks"][0]["artifacts"][0]["path"]).write_bytes(b"drift")
    else:
        row = manifest["tasks"][0]
        if target == "evaluator":
            row["evaluator_implementation_sha256"] = "0" * 64
        else:
            row["artifacts"][0]["path"] = str(tmp_path / "outside.json")
        (folder / "receipt.json").write_text(json.dumps(row))
    with pytest.raises((ValueError, RuntimeError)):
        execution.frozen_task(tmp_path, manifest, "longbench_v2", 1)


def test_new_store_namespace_and_visibility_preserve_shared_execution_contract() -> None:
    reference = execution.frozen.protocol()
    configs = []
    for method in execution.METHODS:
        cell = ScheduledCell(1, SelectedTask("multihop_rag", "synthetic", 1),
                             "deepseek-v4-pro", "slow", method, 0)
        configs.append(execution.cell_config(cell, cell.cell_id, reference))
    stores = {store for config in configs for store in config["fresh_worker_stores"].values()}
    assert len(stores) == 28
    assert len({provenance_sha256(config["execution"]) for config in configs}) == 1
    assert len({provenance_sha256(config["network"]) for config in configs}) == 1
    assert all(config["model_service_timeout_seconds"] == 1200 for config in configs)
    assert [config["profile_visibility"] for config in configs] == [
        "blind", "aware", "blind", "blind", "blind", "blind", "blind"]
    assert all(config["execution"]["retry"] is False for config in configs)


def test_formal_runner_never_calls_historical_task_rewriter_or_same_model_verifier() -> None:
    source = inspect.getsource(execution.execute_once)
    assert "frozen.task_bundle(" not in source
    assert 'model("qwen3.8-max"), recipient="verifier"' in source
    assert "_assert_fresh(clients)" in source
    assert "max_retries=0" in source
