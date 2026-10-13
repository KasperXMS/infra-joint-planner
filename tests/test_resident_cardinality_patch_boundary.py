import importlib
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.core.state import EnvironmentSpec
from infra_joint.operators.catalog import build_operator_catalog

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
patch = importlib.import_module("large_scale_resident_cardinality_patch_v1")
resident = importlib.import_module("large_scale_resident_queue_v1")
controller = importlib.import_module("large_scale_resident_cardinality_queue_v1")
collector = importlib.import_module("large_scale_resident_cardinality_snapshot_v1")


def maps() -> tuple[dict, dict]:
    parent = {"src/infra_joint/worker/server.py": "unchanged-worker",
              patch.STRUCTURED_PATH: "old-structured", "configs/old.yaml": "old-config"}
    current = {**parent, **{p: "accounting-only" for p in patch.ALLOWED_DELTA},
               patch.STRUCTURED_PATH: patch.STRUCTURED_SHA256}
    return parent, current


def test_cardinality_archive_is_only_exact_reviewed_delta() -> None:
    parent, current = maps()
    assert set(patch.validate_source_delta(parent, current)) == patch.ALLOWED_DELTA
    assert patch.APP_NAME != resident.REPAIR_APP_NAME


@pytest.mark.parametrize("damage", ["handler", "prompt", "config", "missing", "fix"])
def test_cardinality_freeze_rejects_unrelated_drift(damage: str) -> None:
    parent, current = maps()
    if damage == "missing":
        del current[patch.HARNESS]
    elif damage == "fix":
        current[patch.STRUCTURED_PATH] = "other-fix"
    else:
        current[{"handler": "src/infra_joint/worker/server.py",
                 "prompt": "scripts/resource_blind_live_validation_v1.py",
                 "config": "configs/old.yaml"}[damage]] = "changed"
    with pytest.raises(RuntimeError, match="exact audited source delta"):
        patch.validate_source_delta(parent, current)


def test_new_manifest_changes_only_cardinality_capability_hash() -> None:
    app = Path(__file__).resolve().parents[1]
    original = resident.frozen._yaml(app / resident.ResidentBlock.harness_manifest)
    current = yaml.safe_load((app / patch.HARNESS).read_text(encoding="utf-8"))
    patch.validate_harness_delta(original, current)
    assert original["static_capability_contract_sha256"] != patch.CAPABILITY_SHA256
    environment = EnvironmentSpec.model_validate(resident.frozen._yaml(resident.POOL_CONFIG)[
        "environment"])
    operations = tuple(current["available_operations"])
    capability = build_static_capability_contract(environment, build_operator_catalog(), operations)
    assert resident.frozen._capability_sha256(capability) == patch.CAPABILITY_SHA256
    with pytest.raises(RuntimeError) as error:
        resident.frozen.validate_harness(resident.frozen.load_harness(app / patch.HARNESS),
                                         environment, capability, operations)
    assert "native runtime source drift" in str(error.value)
    assert "Verifier source drift" in str(error.value)
    assert "static capability contract drift" not in str(error.value)


@pytest.mark.parametrize("section", ["manager", "verifier", "budget", "available_operations",
                                     "anonymous_model_contract", "runtime"])
def test_cardinality_manifest_rejects_tuning(section: str) -> None:
    app = Path(__file__).resolve().parents[1]
    original = resident.frozen._yaml(app / resident.ResidentBlock.harness_manifest)
    current = deepcopy(original)
    current["static_capability_contract_sha256"] = patch.CAPABILITY_SHA256
    current[section] = "changed"
    with pytest.raises(RuntimeError, match="cannot tune"):
        patch.validate_harness_delta(original, current)


def test_patched_worker_launcher_cannot_execute_on_development_pc() -> None:
    with pytest.raises(RuntimeError, match="remote resident-block"):
        patch.start_patched_worker(Path("/unfrozen"), Path("/config"), "A4", "/store")


@pytest.mark.parametrize("run,digest,boundary", [
    ("original", collector.resident.EXECUTION_FREEZE_SHA256, "original-execution-001"),
    ("quote", patch.PARENT_SHA256, "quote-integrity-repair-002"),
    ("cardinality", "f" * 64, "input-cardinality-repair-003"),
])
def test_three_epochs_remain_source_bound(run: str, digest: str, boundary: str) -> None:
    row = {"run_id": run, "execution_sha256": digest, "attempt_index": 1}
    assert collector.validate_attempt_source(row, {"original"}, {"quote"}, "f" * 64) == boundary
    row["execution_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="durable source boundary"):
        collector.validate_attempt_source(row, {"original"}, {"quote"}, "f" * 64)


def test_stopped_prefix_is_immutable_but_future_appends_are_allowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import hashlib

    lines = [json.dumps({"sequence": n}).encode() + b"\n" for n in range(229)]
    prefix = b"".join(lines)
    monkeypatch.setattr(controller, "PREFIX_SHA256", hashlib.sha256(prefix).hexdigest())
    journal = tmp_path / "phase1-attempts.jsonl"
    journal.write_bytes(prefix + b'{"event":"generic_repair"}\n')
    controller.verify_prefix(tmp_path)
    journal.write_bytes(b"X" + prefix[1:])
    with pytest.raises(RuntimeError, match="stopped journal prefix drift"):
        controller.verify_prefix(tmp_path)
