import hashlib
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from scripts.resident_model_pool_service_v1 import (
    GPU0,
    GPU1,
    manifest_path,
    server_environment,
    targets,
    verify_derived_build,
)


def test_fixed_five_instances_separate_ports_stores_and_gpu_bindings() -> None:
    nodes = {node: targets(node) for node in ("A4", "A5", "A28", "strong-4090")}
    assert sum(map(len, nodes.values())) == 5
    strong = nodes["strong-4090"]
    assert {item["gpu"] for item in strong} == {GPU0, GPU1}
    assert len({item["store"] for item in strong}) == 2
    assert len({item["port"] for item in strong}) == 2
    assert all(item["source_tag"] != item["derived_tag"]
               for group in nodes.values() for item in group)
    with pytest.raises(ValueError, match="unknown"):
        targets("development-pc")


def test_environment_does_not_inherit_wrong_gpu_store_or_parallelism() -> None:
    target = targets("strong-4090")[0]
    inherited = {"CUDA_VISIBLE_DEVICES": "1", "OLLAMA_HOST": "0.0.0.0:11434",
                 "OLLAMA_MODELS": "/old", "OLLAMA_NUM_PARALLEL": "4", "PATH": "/bin"}
    environment = server_environment(target, inherited)
    assert environment["CUDA_VISIBLE_DEVICES"] == GPU0
    assert environment["OLLAMA_HOST"] == "127.0.0.1:11436"
    assert environment["OLLAMA_MODELS"] == target["store"]
    assert environment["OLLAMA_NUM_PARALLEL"] == "1"
    assert environment["OLLAMA_KEEP_ALIVE"] == "-1"
    assert environment["OLLAMA_NO_CLOUD"] == "1"
    assert environment["PATH"] == "/bin"
    assert inherited["CUDA_VISIBLE_DEVICES"] == "1"
    assert "CUDA_VISIBLE_DEVICES" not in server_environment(targets("A4")[0], inherited)


@pytest.mark.parametrize("tag", ["../x", "x:../y", "..", "x:..", "x:y:z", ""])
def test_manifest_path_rejects_escaping_or_unknown_tag_shapes(tag: str) -> None:
    with pytest.raises(ValueError):
        manifest_path(Path("/safe"), tag)


def test_derived_build_may_change_only_context_parameter() -> None:
    source = {"layers": [{"mediaType": "model", "digest": "weights"},
                         {"mediaType": "template", "digest": "template"},
                         {"mediaType": "application.params", "digest": "params-before"}]}
    derived = deepcopy(source)
    derived["layers"][-1]["digest"] = "params-after"
    show = {"template": "same", "details": {"quantization": "Q4_K_M"}}
    verify_derived_build(source, derived, {"temperature": 0.7},
                         {"temperature": 0.7, "num_ctx": 32768}, show, deepcopy(show))
    changed = deepcopy(derived)
    changed["layers"][0]["digest"] = "substitute"
    with pytest.raises(ValueError, match="weights"):
        verify_derived_build(source, changed, {}, {"num_ctx": 32768}, show, show)
    with pytest.raises(ValueError, match="parameters"):
        verify_derived_build(source, derived, {"temperature": 0.7},
                             {"num_ctx": 32768}, show, show)
    with pytest.raises(ValueError, match="metadata"):
        verify_derived_build(source, derived, {}, {"num_ctx": 32768},
                             show, {**show, "template": "hidden-instructions"})


def test_layer_provenance_rewrite_is_not_content_substitution() -> None:
    source = {"layers": [{"mediaType": "model", "digest": "same", "size": 7,
                          "from": "download-original"}]}
    derived = deepcopy(source)
    derived["layers"][0]["from"] = "local-source-tag:latest"
    verify_derived_build(source, derived, {}, {"num_ctx": 32768}, {}, {})
    for field, value in [("size", 8), ("unknown_execution_option", "change")]:
        changed = deepcopy(derived)
        changed["layers"][0][field] = value
        with pytest.raises(ValueError, match="weights"):
            verify_derived_build(source, changed, {}, {"num_ctx": 32768}, {}, {})
    changed = deepcopy(derived)
    changed["layers"].append(deepcopy(changed["layers"][0]))
    with pytest.raises(ValueError, match="weights"):
        verify_derived_build(source, changed, {}, {"num_ctx": 32768}, {}, {})


def test_config_transport_rewrite_cannot_hide_renderer_or_parser_substitution() -> None:
    manifest = {"layers": [{"mediaType": "model", "digest": "same"}]}
    source = {"renderer": "instruct", "parser": "instruct", "rootfs": {"old": "transport"}}
    derived = {"renderer": "instruct", "parser": "instruct"}
    verify_derived_build(manifest, manifest, {}, {"num_ctx": 32768}, {}, {}, source, derived)
    with pytest.raises(ValueError, match="renderer"):
        verify_derived_build(manifest, manifest, {}, {"num_ctx": 32768}, {}, {},
                             source, {**derived, "renderer": "different"})
    with pytest.raises(ValueError, match="both"):
        verify_derived_build(manifest, manifest, {}, {"num_ctx": 32768}, {}, {}, source)


def test_derived_parent_must_be_exact_source_without_semantic_detail_drift() -> None:
    manifest = {"layers": [{"mediaType": "model", "digest": "same"}]}
    source = {"details": {"parent_model": "", "family": "qwen35", "format": "gguf"}}
    derived = {"details": {**source["details"], "parent_model": "source:latest"}}
    verify_derived_build(manifest, manifest, {}, {"num_ctx": 32768}, source, derived,
                         expected_source_tag="source")
    with pytest.raises(ValueError, match="exact source"):
        verify_derived_build(manifest, manifest, {}, {"num_ctx": 32768}, source, derived,
                             expected_source_tag="other")
    with pytest.raises(ValueError, match="details"):
        verify_derived_build(manifest, manifest, {}, {"num_ctx": 32768}, source,
                             {"details": {**derived["details"], "family": "substituted"}},
                             expected_source_tag="source")


def test_cutover_keeps_full_screening_and_counts_old_samples() -> None:
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / "configs/preparation/resident-model-pool-v1-cutover.yaml")
                            .read_text(encoding="utf-8"))
    assert hashlib.sha256((root / config["pool_manifest"]).read_bytes()).hexdigest() == (
        config["pool_manifest_sha256"]
    )
    assert config["calibration_services_allowed"] is True
    assert config["benchmark_execution_allowed"] is False
    assert config["phase1_methods"] == ["B0", "B1", "A", "B", "C", "D", "E"]
    assert config["old_new_environment_results_pooled"] is False
    assert config["old_samples_count_toward_global_cap"] is True
    total = (config["old_nominal_samples_retained"] + config["phase1_new_cells"]
             + config["phase2_cells_per_method"]
             * config["phase2_max_full_methods_with_remaining_budget"])
    assert total == 402 <= config["global_substantive_cap"]
