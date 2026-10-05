"""Guard the inactive, prospective pool specification; never start model services."""

from pathlib import Path

import yaml

MANIFEST = Path(__file__).resolve().parents[1] / (
    "configs/preparation/resident-model-pool-v1.yaml"
)


def test_manifest_cannot_be_mistaken_for_an_enabled_experiment() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["status"] == "isolated_stores_prepared_not_deployed"
    assert manifest["activation_allowed"] is False
    assert manifest["old_experiment_pool_modified"] is False
    assert manifest["matrix_replacement_authorized"] is False
    assert "environment" not in manifest
    assert "deployments" not in manifest
    assert "worker_urls" not in manifest


def test_three_artifacts_five_instances_cover_all_devices() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    artifacts = manifest["artifacts"]
    instances = manifest["proposed_instances"]
    assert len(artifacts) == 3
    assert len(instances) == 5
    assert len({item["instance_id"] for item in instances}) == 5
    assert {item["artifact"] for item in instances} == set(artifacts)
    assert {item["worker"] for item in instances} == {"A4", "A5", "A28", "strong-4090"}
    assert len({(item["worker"], item["dedicated_ollama_port"]) for item in instances}) == 5
    gpu_instances = [item for item in instances if item["worker"] == "strong-4090"]
    assert len({item["gpu_binding"] for item in gpu_instances}) == 2
    assert all(item["gpu_binding"].startswith("GPU-") for item in gpu_instances)


def test_replicas_preserve_model_identity_across_device_classes() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    instances = {item["instance_id"]: item for item in manifest["proposed_instances"]}
    assert instances["resident-a5-vl8b-v1"]["artifact"] == (
        instances["resident-4090-gpu1-vl8b-v1"]["artifact"]
    )
    assert instances["resident-a28-qwen35-27b-v1"]["artifact"] == (
        instances["resident-4090-gpu0-qwen35-27b-v1"]["artifact"]
    )


def test_instruct_variant_is_not_installed_thinking_alias() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    artifact = manifest["artifacts"]["vl-8b-instruct"]
    excluded = artifact["excluded_installed_variant"]
    assert artifact["variant"] == "instruct"
    assert excluded["variant"] == "thinking"
    assert artifact["source_manifest_sha256"] != excluded["manifest_sha256"]
    assert artifact["source_available_on_4090"] is True
    assert artifact["acquisition_status"] == "downloaded_on_4090_not_loaded_or_deployed"
    assert artifact["full_blob_verification"] == "all_source_descriptors_verified_on_4090"
    assert len(artifact["content_verification_sha256"]) == 64


def test_calibration_targets_are_not_claimed_as_validated_contracts() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    for instance in manifest["proposed_instances"]:
        assert instance["validated_contract"] is None
        assert instance["calibration_status"].startswith("pending")
    target = manifest["calibration_target"]
    assert target["context_window"] == 32768
    assert target["reserved_output_tokens"] == 2048
    assert target["image_token_cost"] is None
    assert target["quality_classes"] is None
    assert target["max_output_bytes"] is None
    assert target["benchmark_gold_used"] is False


def test_residency_and_measurement_do_not_hide_execution_cost() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    service = manifest["resident_service_target"]
    assert service["OLLAMA_KEEP_ALIVE"] == "-1"
    assert service["separate_server_per_instance"] is True
    assert service["legacy_model_allocation_reconciliation_required"] is True
    measurement = manifest["measurement_contract"]
    assert measurement["include_request_prefill_vision_queue_decode_time"] is True
    assert measurement["subtract_guessed_startup_constant"] is False
    assert measurement["unexpected_eviction_or_reload"].startswith("experimental_confounder")
    assert measurement["pool_old_and_new_environment_results"] is False


def test_payloads_stay_remote_and_no_new_routing_or_prompt_change() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    scope = manifest["scope"]
    assert scope["payload_download_and_distribution_host"] == "strong-4090"
    assert scope["development_pc_payload_transfer_allowed"] is False
    for field in (
        "cloud_manager_models_changed",
        "verifier_changed",
        "scheduler_changed",
        "model_routing_method_added",
    ):
        assert scope[field] is False
    assert manifest["measurement_contract"]["blind_visible_physical_identity"] is False


def test_activation_requires_real_calibration_not_metadata_alone() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    gates = set(manifest["activation_gates"])
    assert {
        "old_queue_cutover_decision_recorded",
        "no_atomic_benchmark_run_active",
        "text_and_image_inference_calibrated_per_instance",
        "context_and_output_preflight_backend_agreement_verified",
        "simultaneous_five_instance_residency_verified",
        "worker_state_matches_new_environment_spec",
        "shared_anonymous_static_contract_privacy_verified",
    } <= gates


def test_source_content_verification_does_not_activate_a_deployment() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    assert len(manifest["source_content_verification_sha256"]) == 64
    assert all(artifact["full_blob_verification"] == "all_source_descriptors_verified_on_4090"
               for artifact in manifest["artifacts"].values())
    assert manifest["activation_allowed"] is False
    assert all(instance["validated_contract"] is None
               for instance in manifest["proposed_instances"])


def test_five_verified_isolated_stores_do_not_claim_live_services() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    assert len(manifest["isolated_store_verification_sha256"]) == 64
    for instance in manifest["proposed_instances"]:
        assert instance["store_content_verified"] is True
        assert "resident-model-pool-v1" in instance["isolated_model_store"]
        assert instance["validated_contract"] is None
        assert instance["calibration_status"].startswith("pending")
    assert manifest["activation_allowed"] is False


def test_isolated_runtime_version_preparation_does_not_certify_inference() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    runtime = manifest["runtime_preparation"]
    assert runtime["version_target"] == "0.34.0"
    assert runtime["status"] == "isolated_arm64_copies_verified_not_started"
    assert runtime["source_node"] == "A28"
    assert set(runtime["verified_isolated_copy_nodes"]) == {"A4", "A5"}
    assert len(runtime["verification_sha256"]) == 64
    assert runtime["regular_files_per_copy"] == 36
    assert runtime["in_root_symlinks_per_copy"] == 20
    assert runtime["default_runtimes_modified"] is False
    assert runtime["new_services_started"] is False
    assert runtime["inference_calibrated"] is False
    for instance in manifest["proposed_instances"]:
        if instance["worker"] in {"A4", "A5"}:
            assert instance["prepared_runtime_executable"].startswith(
                "/mnt/ssd/resident-model-pool-v1/runtime/"
            )
            assert instance["prepared_runtime_executable"].endswith("/bin/ollama")
        assert instance["validated_contract"] is None
    assert manifest["activation_allowed"] is False
