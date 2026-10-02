import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from infra_joint.config import EnvironmentSpec
from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.operators.catalog import build_operator_catalog

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import blind_3family_validation_v1 as validation  # noqa: E402
from blind_3family_validation_v1 import (  # noqa: E402
    REPO,
    _model_service_timeout_seconds,
    _operations,
    _revision,
    _validate_harness_manifest_hash,
    _yaml,
    load_harness,
    validate_harness,
    validate_runtime_import_root,
)


def frozen_components() -> tuple[object, EnvironmentSpec, object, tuple[str, ...]]:
    harness = load_harness(REPO / "configs/experiments/blind-harness-v1.3.1.yaml")
    base = _yaml(REPO / "configs/experiments/blind-baseline-6task-semantic-cleanup-v1.yaml")
    fresh = _yaml(REPO / "configs/experiments/blind-3family-video-environment-v1.3.yaml")
    environment = EnvironmentSpec.model_validate(fresh["environment"])
    operations = _operations(base)
    capabilities = build_static_capability_contract(
        environment,
        build_operator_catalog(),
        operations,
    )
    return harness, environment, capabilities, operations


def test_committed_blind_harness_v1_3_1_is_internally_consistent() -> None:
    harness, environment, capabilities, operations = frozen_components()
    validate_historical_harness(harness, environment, capabilities, operations)


def validate_historical_harness(
    harness: object, environment: EnvironmentSpec, capabilities: object,
    operations: tuple[str, ...],
) -> None:
    # Historical freezes must reject a newly versioned runtime, not silently follow HEAD.
    with pytest.raises(RuntimeError) as error:
        validate_harness(harness, environment, capabilities, operations)  # type: ignore[arg-type]
    assert str(error.value) == "frozen Blind harness validation failed: native runtime source drift"
    historical_source = subprocess.run(
        ["git", "show", "597ac33:src/infra_joint/control/native_agents.py"],
        cwd=REPO, check=True, capture_output=True,
    ).stdout
    assert sha256(historical_source).hexdigest() == harness.runtime["source_sha256"]  # type: ignore[attr-defined]


def test_qwen_sanity_harness_changes_only_cloud_control_plane() -> None:
    previous, environment, capabilities, operations = frozen_components()
    qwen = load_harness(REPO / "configs/experiments/qwen-infra-sanity-v1.yaml")
    validate_historical_harness(qwen, environment, capabilities, operations)
    previous_payload = previous.model_dump(mode="json")
    qwen_payload = qwen.model_dump(mode="json")
    for key in (
        "harness_id",
        "frozen_from_revision",
        "positive_baseline_run_id",
        "manager",
        "verifier",
    ):
        previous_payload.pop(key)
        qwen_payload.pop(key)
    assert qwen_payload == previous_payload
    assert qwen.manager["model"] == qwen.verifier["model"]
    assert qwen.manager["api_key_env"] == "DASHSCOPE_API_KEY"
    assert qwen.manager["max_retries"] == 0
    assert qwen.verifier["result_transport"] == "required_function_tool"


def test_qwen38max_sanity_harness_pins_non_thinking_tool_transport() -> None:
    previous, environment, capabilities, operations = frozen_components()
    qwen = load_harness(REPO / "configs/experiments/qwen-infra-sanity-v2.yaml")
    validate_historical_harness(qwen, environment, capabilities, operations)
    previous_payload = previous.model_dump(mode="json")
    qwen_payload = qwen.model_dump(mode="json")
    for key in (
        "harness_id",
        "frozen_from_revision",
        "positive_baseline_run_id",
        "manager",
        "verifier",
    ):
        previous_payload.pop(key)
        qwen_payload.pop(key)
    assert qwen_payload == previous_payload
    assert qwen.manager["model"] == qwen.verifier["model"] == "qwen3.8-max"
    assert qwen.manager["request_extra_body"] == {"enable_thinking": False}


def test_qwen38max_preliminary_freezes_sanity_control_plane() -> None:
    sanity = load_harness(REPO / "configs/experiments/qwen-infra-sanity-v2.yaml")
    frozen = load_harness(REPO / "configs/experiments/qwen-infra-preliminary-v1.yaml")
    sanity_payload = sanity.model_dump(mode="json")
    frozen_payload = frozen.model_dump(mode="json")
    for key in ("harness_id", "frozen_from_revision", "positive_baseline_run_id"):
        sanity_payload.pop(key)
        frozen_payload.pop(key)
    assert frozen_payload == sanity_payload
    assert frozen.positive_baseline_run_id == (
        "qwen38max-sanity-multihop-fast-blind-replacement-1"
    )


def test_blind_harness_v1_2_changes_only_generic_budget() -> None:
    previous = load_harness(REPO / "configs/experiments/blind-harness-v1.1.yaml")
    current = load_harness(REPO / "configs/experiments/blind-harness-v1.2.yaml")
    previous_payload = previous.model_dump(mode="json")
    current_payload = current.model_dump(mode="json")
    for key in ("harness_id", "frozen_from_revision", "positive_baseline_run_id", "budget"):
        previous_payload.pop(key)
        current_payload.pop(key)
    assert current_payload == previous_payload
    assert current.budget.model_dump(mode="json") == {
        "max_manager_turns": 20,
        "max_subagent_turns": 8,
        "max_tool_model_calls": 64,
        "max_created_subagents": 4,
        "max_active_subagents": 2,
        "max_verifier_calls": 20,
    }


def test_blind_harness_v1_3_changes_only_terminal_contract_and_timeout() -> None:
    previous = load_harness(REPO / "configs/experiments/blind-harness-v1.2.yaml")
    current = load_harness(REPO / "configs/experiments/blind-harness-v1.3.yaml")
    previous_payload = previous.model_dump(mode="json")
    current_payload = current.model_dump(mode="json")
    for key in (
        "harness_id",
        "frozen_from_revision",
        "positive_baseline_run_id",
        "runtime",
        "model_service_timeout_seconds",
    ):
        previous_payload.pop(key)
        current_payload.pop(key)
    assert current_payload == previous_payload
    assert current.runtime["implementation"] == previous.runtime["implementation"]
    assert current.runtime["source_sha256"] != previous.runtime["source_sha256"]
    assert previous.model_service_timeout_seconds == 900
    assert current.model_service_timeout_seconds == 1200


def test_blind_harness_v1_3_1_changes_only_cross_mode_verifier_compatibility() -> None:
    previous = load_harness(REPO / "configs/experiments/blind-harness-v1.3.yaml")
    current = load_harness(REPO / "configs/experiments/blind-harness-v1.3.1.yaml")
    previous_payload = previous.model_dump(mode="json")
    current_payload = current.model_dump(mode="json")
    for key in ("harness_id", "frozen_from_revision", "runtime"):
        previous_payload.pop(key)
        current_payload.pop(key)
    assert current_payload == previous_payload
    assert current.runtime["implementation"] == previous.runtime["implementation"]
    assert current.runtime["source_sha256"] != previous.runtime["source_sha256"]


def test_blind_harness_rejects_manager_instruction_drift() -> None:
    harness, environment, capabilities, operations = frozen_components()
    changed_manager = {**harness.manager, "instructions_sha256": "0" * 64}  # type: ignore[union-attr]
    drifted = harness.model_copy(update={"manager": changed_manager})  # type: ignore[union-attr]
    with pytest.raises(RuntimeError, match="Manager instructions drift"):
        validate_harness(drifted, environment, capabilities, operations)  # type: ignore[arg-type]


def test_stage2_config_pins_harness_manifest_bytes(tmp_path: Path) -> None:
    config = _yaml(REPO / "configs/experiments/blind-3family-longbench-v1.yaml")
    harness_path = REPO / str(config["harness_manifest"])
    _validate_harness_manifest_hash(config, harness_path)
    changed = tmp_path / "blind-harness-v1.yaml"
    changed.write_bytes(harness_path.read_bytes() + b"\n")
    with pytest.raises(RuntimeError, match="manifest drift"):
        _validate_harness_manifest_hash(config, changed)


@pytest.mark.parametrize(
    "config_name",
    [
        "blind-3family-multihop-v1.2.yaml",
        "blind-3family-longbench-v1.2.yaml",
        "blind-3family-video-v1.2.yaml",
    ],
)
def test_blind_harness_v1_2_stage2_cells_share_frozen_contract(
    config_name: str,
) -> None:
    config = _yaml(REPO / "configs/experiments" / config_name)
    harness_path = REPO / str(config["harness_manifest"])
    _validate_harness_manifest_hash(config, harness_path)
    assert config["task"] in {
        "multihop-multisource",
        "longbench-multidoc",
        "video-long-payload",
    }
    assert config["execution"] == {
        "network": "native_unshaped",
        "scheduler": "auto_physical_locality_aware",
        "repetitions": 1,
        "retry": False,
        "replacement": False,
    }


def test_longbench_timeout1200_cell_changes_only_service_timeout() -> None:
    previous = _yaml(REPO / "configs/experiments/blind-3family-longbench-v1.2.yaml")
    current = _yaml(
        REPO
        / "configs/experiments/blind-3family-longbench-v1.2-timeout1200.yaml"
    )
    assert _model_service_timeout_seconds(previous) == 900
    assert _model_service_timeout_seconds(current) == 1200
    assert current["harness_manifest"] == previous["harness_manifest"]
    assert current["harness_manifest_sha256"] == previous["harness_manifest_sha256"]
    assert current["source_experiment_config"] == previous["source_experiment_config"]
    assert current["task"] == previous["task"]
    assert current["execution"] == previous["execution"]


def test_stage2_timeout_rejects_unapproved_value() -> None:
    with pytest.raises(RuntimeError, match="unsupported model-service timeout"):
        _model_service_timeout_seconds({"model_service_timeout_seconds": 1201})


def test_video_v1_3_cell_pins_timeout_and_frozen_harness() -> None:
    config = _yaml(REPO / "configs/experiments/blind-3family-video-v1.3.yaml")
    harness_path = REPO / str(config["harness_manifest"])
    _validate_harness_manifest_hash(config, harness_path)
    harness = load_harness(harness_path)
    assert harness.harness_id == "blind-harness-v1.3"
    assert _model_service_timeout_seconds(config) == 1200
    assert harness.model_service_timeout_seconds == 1200


def test_archive_deployment_revision_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "blind_3family_validation_v1.subprocess.check_output",
        lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError()),
    )
    monkeypatch.setenv("INFRA_JOINT_CODE_REVISION", "a" * 40)
    assert _revision() == "a" * 40
    monkeypatch.setenv("INFRA_JOINT_CODE_REVISION", "not-a-commit")
    with pytest.raises(RuntimeError, match="code revision is unavailable"):
        _revision()


def test_longbench_stage2_loader_uses_existing_adapter_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    samples_path = tmp_path / "samples.jsonl"
    samples_path.write_text("{}\n", encoding="utf-8")
    sample = object()
    bundle = object()
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        validation,
        "_load_longbench_samples",
        lambda path, wanted: {"sample-1": sample},
    )

    def adapt(
        actual_sample: object,
        source_revision: str,
        boundaries: tuple[int, ...],
    ) -> object:
        captured.update(
            sample=actual_sample,
            source_revision=source_revision,
            boundaries=boundaries,
        )
        return bundle

    monkeypatch.setattr(validation, "_longbench_multidoc_bundle", adapt)
    config = {"task": "longbench-multidoc"}
    base = {
        "dataset": {
            "tasks": [
                {
                    "label": "longbench-multidoc",
                    "source_task_id": "sample-1",
                    "boundary_lines": [0, 3, 8],
                }
            ],
            "revisions": {"longbench_v2": "revision-1"},
        }
    }
    loaded, _ = validation._load_bundle(  # noqa: SLF001
        config,
        base,
        SimpleNamespace(longbench_samples=samples_path),
    )
    assert loaded is bundle
    assert captured == {
        "sample": sample,
        "source_revision": "revision-1",
        "boundaries": (0, 3, 8),
    }


def test_multihop_stage2_loader_uses_complete_remote_dataset_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    corpus_path = tmp_path / "corpus.json"
    queries_path = tmp_path / "queries.json"
    corpus = [{"id": index} for index in range(609)]
    queries = [{"id": "query"}]
    corpus_path.write_text(validation.json.dumps(corpus), encoding="utf-8")
    queries_path.write_text(validation.json.dumps(queries), encoding="utf-8")
    row = {"label": "multihop-multisource"}
    bundle = object()
    captured: dict[str, object] = {}

    def adapt(
        actual_row: object,
        actual_corpus: object,
        actual_queries: object,
        source_revision: str,
    ) -> object:
        captured.update(
            row=actual_row,
            corpus=actual_corpus,
            queries=actual_queries,
            source_revision=source_revision,
        )
        return bundle

    monkeypatch.setattr(validation, "_multihop_bundle", adapt)
    args = SimpleNamespace(
        multihop_corpus=corpus_path,
        multihop_queries=queries_path,
        longbench_samples=None,
        video_tasks=None,
        video_answers=None,
        video_sources=None,
    )
    loaded, source = validation._load_bundle(  # noqa: SLF001
        {"task": "multihop-multisource"},
        {
            "dataset": {
                "tasks": [row],
                "revisions": {"multihop_rag": "revision-1"},
            }
        },
        args,
    )

    assert loaded is bundle
    assert captured == {
        "row": row,
        "corpus": corpus,
        "queries": queries,
        "source_revision": "revision-1",
    }
    assert source["multihop_corpus"]["size_bytes"] == corpus_path.stat().st_size


def test_archive_deployment_rejects_editable_install_from_other_checkout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(validation.native_agents_module, "__file__", tmp_path / "native.py")
    with pytest.raises(RuntimeError, match="different checkout"):
        validate_runtime_import_root()
