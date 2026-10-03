import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from blind_3family_validation_v1 import REPO, _yaml, load_harness  # noqa: E402
from predecision_crossbenchmark_v1 import (  # noqa: E402
    CONDITIONS,
    base_config,
    cell_config,
    ensure_remote,
    load_bundle,
    summarize_run_trace,
    validate_protocol,
)
from run_predecision_matrix_v1 import validate_cell  # noqa: E402
from test_predecision_queue_validation import fixture  # noqa: E402


def protocol() -> dict[str, Any]:
    return _yaml(REPO / "configs/experiments/predecision-crossbenchmark-v1.yaml")


def test_crossbenchmark_24_cells_preserve_harness_and_have_96_fresh_stores() -> None:
    value = protocol()
    validate_protocol(value)
    base = base_config(value)
    harness = load_harness(REPO / value["harness_manifest"])
    assert harness.harness_id == "infra-aware-predecision-v1"
    assert harness.manager["model"] == harness.verifier["model"] == "qwen3.8-max"
    assert harness.budget.max_manager_turns == 20
    assert harness.budget.max_tool_model_calls == 64
    assert harness.budget.max_verifier_calls == 20
    assert tuple(base["planner"]["available_operations"]) == harness.available_operations
    configs = [cell_config(value, row, condition)
               for row in value["tasks"] for condition in CONDITIONS]
    assert len({c["run_id"] for c in configs}) == 24
    assert len({s for c in configs for s in c["fresh_worker_stores"].values()}) == 96
    assert [r["family"] for r in value["tasks"]] == (
        ["longbench_multidoc"] * 3 + ["video_mme"] * 3
    )


@pytest.mark.parametrize("change", ["order", "duplicate", "network", "budget"])
def test_protocol_rejects_drift(change: str) -> None:
    value = copy.deepcopy(protocol())
    if change == "order":
        value["condition_order"].reverse()
    elif change == "duplicate":
        value["tasks"][1] = value["tasks"][0]
    elif change == "network":
        value["network_regimes"]["slow"]["bandwidth_mbps"] = 10
    else:
        value["execution"]["repetitions"] = 3
    with pytest.raises(ValueError):
        validate_protocol(value)


def test_choice_gate_is_task_declared_and_retains_wrong_answers(tmp_path: Path) -> None:
    fixture(tmp_path)
    path = tmp_path / "runs/test/result.json"
    result = json.loads(path.read_text())
    result["final_answer"] = "B"
    path.write_text(json.dumps(result))
    assert not validate_cell(tmp_path, "test", "blind", ("A", "B", "C", "D"))["problems"]
    assert validate_cell(tmp_path, "test", "blind")["problems"] == [
        "completed terminal/evaluator contract inconsistent"
    ]


@pytest.mark.asyncio
async def test_longbench_admission_is_lossless_preserves_choice_and_private_gold(
    tmp_path: Path,
) -> None:
    value = protocol()
    row = value["tasks"][1].copy()
    row["boundary_lines"] = [0, 2]
    original = "First natural report\nalpha\u2028beta\nSecond natural report\ngamma\n"
    sample = {"_id": row["source_task_id"], "domain": "Multi-Document QA",
              "sub_domain": "Academic", "difficulty": "hard", "length": "medium",
              "question": "Compare the reports", "context": original,
              "choice_A": "first", "choice_B": "second", "choice_C": "both",
              "choice_D": "neither", "answer": "C"}
    path = tmp_path / "samples.jsonl"
    path.write_text(json.dumps(sample, ensure_ascii=False) + "\n", encoding="utf-8")
    bundle, source = load_bundle(row, base_config(value), {"longbench_samples": str(path)})
    reconstructed = "".join(record["text"] for artifact in bundle.prepared_artifacts
                            for record in json.loads(artifact.content))
    assert reconstructed == original
    assert bundle.execution.validity.information_equivalent
    assert bundle.execution.validity.query_equivalent
    assert bundle.execution.validity.evaluator_equivalent
    assert bundle.execution.task.output_contract.choices == ("A", "B", "C", "D")
    evaluation = await bundle.private_evaluation.build_evaluator().evaluate(
        bundle.execution.task, "C",
    )
    assert evaluation.benchmark_score == 1
    assert source["longbench_samples"]["size_bytes"] == path.stat().st_size


def test_operational_attempt_has_new_identity_and_namespace() -> None:
    value = protocol()
    primary = cell_config(value, value["tasks"][0], "fast-blind")
    replacement = cell_config(value, value["tasks"][0], "fast-blind",
                              "operational-replacement-1")
    assert primary["run_id"] != replacement["run_id"]
    assert not set(primary["fresh_worker_stores"].values()) & set(
        replacement["fresh_worker_stores"].values()
    )
    assert replacement["execution"]["retry"] is False


def test_transport_patch_freeze_changes_only_transport_provenance() -> None:
    original = protocol()
    patched = _yaml(
        REPO / "configs/experiments/predecision-crossbenchmark-v1-transport-patch1.yaml",
    )
    validate_protocol(patched)
    assert {k: v for k, v in original.items() if not k.startswith("harness_manifest")} == {
        k: v for k, v in patched.items() if not k.startswith("harness_manifest")
    }
    original_harness = _yaml(REPO / original["harness_manifest"])
    patched_harness = _yaml(REPO / patched["harness_manifest"])
    assert {k: v for k, v in original_harness.items() if k not in {
        "runtime", "frozen_from_revision",
    }} == {k: v for k, v in patched_harness.items() if k not in {
        "runtime", "frozen_from_revision",
    }}
    old_runtime, new_runtime = original_harness["runtime"], patched_harness["runtime"]
    assert {k: new_runtime[k] for k in old_runtime if k != "component_sha256"} == {
        k: v for k, v in old_runtime.items() if k != "component_sha256"
    }
    assert new_runtime["worker_http_keepalive_expiry_seconds"] == 4
    for path, digest in old_runtime["component_sha256"].items():
        assert new_runtime["component_sha256"][path] == digest
    primary = cell_config(original, original["tasks"][0], "slow-aware")
    patch = cell_config(patched, patched["tasks"][0], "slow-aware", "transport-patch-1")
    assert primary["run_id"] != patch["run_id"]
    assert not set(primary["fresh_worker_stores"].values()) & set(
        patch["fresh_worker_stores"].values()
    )
    assert patch["execution"] == primary["execution"]


def test_dataset_entry_refuses_development_pc() -> None:
    with pytest.raises(RuntimeError):
        ensure_remote(Path("C:/datasets"))


def test_unicode_line_separator_in_evidence_does_not_break_jsonl_audit(tmp_path: Path) -> None:
    fixture(tmp_path)
    path = tmp_path / "runs/test/trace.jsonl"
    with path.open("a", encoding="utf-8") as stream:
        stream.write("\n" + json.dumps({"event_type": "logical.observation", "payload": {
            "succeeded": True, "output": {"text": "alpha\u2028beta\u2029gamma"},
        }}, ensure_ascii=False) + "\n")
    assert not validate_cell(tmp_path, "test", "blind")["problems"]
    assert summarize_run_trace(path)["logical_privacy_pass"]
