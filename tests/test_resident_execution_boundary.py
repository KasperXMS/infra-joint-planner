import importlib
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.core.state import EnvironmentSpec
from infra_joint.experiments.large_scale_protocol import ScheduledCell, SelectedTask
from infra_joint.operators.catalog import build_operator_catalog

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
execution = importlib.import_module("large_scale_execution_v1")
resident = importlib.import_module("large_scale_resident_queue_v1")
attestation = importlib.import_module("resident_model_pool_attestation_v1")


def test_resident_scope_does_not_replace_historical_globals_and_is_remote_only() -> None:
    assert execution.ROOT != resident.ROOT
    with pytest.raises(RuntimeError):
        resident.require_remote()
    with pytest.raises(RuntimeError):
        execution.require_remote(resident.ROOT)
    with pytest.raises(RuntimeError):
        execution.ResidentBlock(root=execution.ROOT).validate(resident.ROOT)
    reference = resident.reference()
    cell = ScheduledCell(1, SelectedTask("multihop_rag", "synthetic", 1),
                         "deepseek-v4-pro", "slow", "B0", 0)
    old = execution.cell_config(cell, "old", execution.frozen.protocol())
    new = execution.cell_config(cell, "new", reference, root=resident.ROOT)
    assert new["execution"] == old["execution"]
    assert new["network"] == old["network"]
    assert new["profile_visibility"] == old["profile_visibility"] == "blind"
    assert all(resident.ROOT.name in p for p in new["fresh_worker_stores"].values())
    assert not set(new["fresh_worker_stores"].values()) & set(old["fresh_worker_stores"].values())
    with pytest.raises(ValueError, match="namespace"):
        execution.cell_config(cell, "wrong", reference, root=Path("/elsewhere"))


def test_resident_harness_changes_only_calibrated_visual_bound_and_static_hash() -> None:
    app = Path(__file__).resolve().parents[1]
    parent = yaml.safe_load((app / "configs/experiments/"
                            "infra-aware-predecision-v1-transport-receipts-patch2.yaml")
                           .read_text(encoding="utf-8"))
    new = yaml.safe_load(resident.HARNESS.read_text(encoding="utf-8"))
    expected = deepcopy(parent)
    expected["anonymous_model_contract"]["image_token_cost"] = 4096
    expected["static_capability_contract_sha256"] = (
        "1064a5e3446a1dbf0c99360751cc5e9604efa30cad9c548b650ac13d6963a4c0")
    assert new == expected
    resident.validate_harness_delta(parent, new)
    environment = EnvironmentSpec.model_validate(resident.frozen._yaml(
        resident.POOL_CONFIG)["environment"])
    registry = build_operator_catalog()
    operations = tuple(new["available_operations"])
    capabilities = build_static_capability_contract(environment, registry, operations)
    # The old receipt stays immutable and must not silently follow a corrected
    # operator contract. A separately frozen patch is required for new execution.
    with pytest.raises(RuntimeError, match="^frozen Blind harness validation failed: "
                       "static capability contract drift$"):
        resident.frozen.validate_harness(resident.frozen.load_harness(resident.HARNESS),
                                         environment, capabilities, operations)


@pytest.mark.parametrize("section", ["manager", "verifier", "budget", "available_operations"])
def test_resident_freeze_rejects_semantic_or_budget_tuning(section: str) -> None:
    app = Path(__file__).resolve().parents[1]
    parent = yaml.safe_load((app / "configs/experiments/"
                            "infra-aware-predecision-v1-transport-receipts-patch2.yaml")
                           .read_text(encoding="utf-8"))
    current = yaml.safe_load(resident.HARNESS.read_text(encoding="utf-8"))
    current[section] = "changed"
    with pytest.raises(RuntimeError, match="cannot tune"):
        resident.validate_harness_delta(parent, current)


def resident_state() -> dict:
    return {"models": [{"name": "synthetic:latest", "digest": "a" * 64,
                        "context_length": 32768, "size_vram": 123,
                        "expires_at": "2319-01-01T00:00:00Z"}]}


@pytest.mark.parametrize("command,expected", [
    (b"/isolated/lib/ollama/llama-server\0--model\0/blob\0", True),
    (b"/isolated/bin/ollama\0runner\0--port\01234\0", True),
    (b"/other/runner-monitor\0", False),
    (b"/isolated/bin/ollama\0serve\0", False),
])
def test_installed_runner_names_not_arbitrary_substrings(command: bytes, expected: bool) -> None:
    assert attestation.is_model_runner(command) is expected


@pytest.mark.parametrize("field,value", [
    ("name", "other:latest"), ("context_length", 16384), ("size_vram", 0),
    ("digest", "b" * 64), ("expires_at", "2026-10-05T00:00:00Z"),
])
def test_resident_preflight_rejects_eviction_identity_context_and_memory_drift(
    field: str, value: object,
) -> None:
    state = resident_state()
    attestation.validate_resident(state, "synthetic", "a" * 64)
    state["models"][0][field] = value
    with pytest.raises(RuntimeError):
        attestation.validate_resident(state, "synthetic", "a" * 64)


def test_residency_never_hides_reload_or_truncation(tmp_path: Path) -> None:
    import hashlib

    log = tmp_path / "server.log"
    log.write_bytes(b"setup\n")
    row = {"target": {"instance": "synthetic"}, "server": {"pid": 1},
           "runner": {"pid": 2}, "log_path": str(log), "log_bytes": 6,
           "log_prefix_sha256": hashlib.sha256(b"setup\n").hexdigest()}
    before = {"node": "synthetic", "instances": [row], "gpu_compute_processes": None}
    assert attestation.audit_log_interval(before, deepcopy(before))["passed"]
    after = deepcopy(before)
    after["instances"][0]["runner"]["pid"] = 3
    with pytest.raises(RuntimeError, match="reloaded"):
        attestation.compare_residency(before, after)
    for interval in (b"truncated = 2\n", b"starting runner\n", b"out of memory\n"):
        log.write_bytes(b"setup\n" + interval)
        with pytest.raises(RuntimeError, match="reload/OOM/truncation"):
            attestation.audit_log_interval(before, deepcopy(before))
