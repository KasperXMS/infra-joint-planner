import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from blind_3family_validation_v1 import (  # noqa: E402
    REPO,
    _validate_harness_manifest_hash,
    _yaml,
    load_harness,
)
from predecision_crossbenchmark_v1 import validate_protocol  # noqa: E402


def test_backend_patch_keeps_every_logical_and_physical_semantic_contract() -> None:
    directory = REPO / "configs/experiments"
    previous = load_harness(directory / "infra-aware-predecision-v1-transport-patch1.yaml")
    current = load_harness(directory / "infra-aware-predecision-v1-backend-client-patch1.yaml")
    for field in (
        "manager", "verifier", "budget", "available_operations",
        "anonymous_model_contract", "static_capability_contract_sha256",
        "model_service_timeout_seconds",
    ):
        assert getattr(current, field) == getattr(previous, field)
    for field in (
        "implementation", "source_sha256", "profile_timing", "record_input_provenance",
        "terminal_canonical_labels", "profile_schema", "worker_http_keepalive_expiry_seconds",
    ):
        assert current.runtime[field] == previous.runtime[field]
    assert current.runtime["worker_backend_max_retries"] == 0
    assert current.runtime["worker_backend_read_timeout_seconds"] == 1200
    assert current.runtime["worker_backend_connect_timeout_seconds"] == 5


def test_backend_patch_protocol_changes_only_manifest_identity() -> None:
    directory = REPO / "configs/experiments"
    previous = _yaml(directory / "predecision-crossbenchmark-v1-transport-patch1.yaml")
    current = _yaml(directory / "predecision-crossbenchmark-v1-backend-client-patch1.yaml")
    validate_protocol(current)
    _validate_harness_manifest_hash(current, REPO / current["harness_manifest"])
    for field in ("harness_manifest", "harness_manifest_sha256"):
        previous.pop(field)
        current.pop(field)
    assert current == previous
