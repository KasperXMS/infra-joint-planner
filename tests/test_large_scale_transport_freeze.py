import importlib
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from infra_joint.control.provenance import provenance_sha256

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
repair = importlib.import_module("large_scale_transport_freeze_v1")
queue = importlib.import_module("large_scale_queue_v1")
REPO = Path(__file__).resolve().parents[1]


def executions() -> tuple[dict, dict]:
    parent = {"source_sha256": {p: "old" for p in repair.CHANGED} | {"protected.py": "same"},
              "commit_sha": "parent", "phase1_schedule_sha256": "schedule",
              "fixed_verifier": "qwen3.8-max", "formal_runs_at_execution_freeze": 0}
    current = deepcopy(parent)
    current["source_sha256"].update({p: "new" for p in repair.CHANGED | repair.ADDED})
    current["source_sha256"].update(repair.TESTED_CORE)
    current["commit_sha"] = "tested-repair"
    return parent, current


def test_transport_source_delta_is_exactly_the_tested_overlay() -> None:
    parent, current = executions()
    repair.validate_execution_repair(parent, current)
    assert repair.source_delta(parent["source_sha256"], current["source_sha256"]) == {
        "changed": sorted(repair.CHANGED), "added": sorted(repair.ADDED), "removed": []}


@pytest.mark.parametrize("mutation", ["extra_source", "missing_source", "operator",
                                     "model", "schedule", "network", "history", "pricing",
                                     "old_commit", "untested_native", "untested_physical"])
def test_transport_freeze_rejects_unrelated_or_untested_changes(mutation: str) -> None:
    parent, current = executions()
    if mutation == "extra_source":
        current["source_sha256"]["extra.py"] = "new"
    elif mutation == "missing_source":
        del current["source_sha256"]["protected.py"]
    elif mutation == "operator":
        current["source_sha256"]["protected.py"] = "changed"
    elif mutation == "old_commit":
        current["commit_sha"] = parent["commit_sha"]
    elif mutation.startswith("untested_"):
        current["source_sha256"][repair.NATIVE if mutation.endswith("native")
                                  else repair.PHYSICAL] = "untested"
    else:
        current[mutation] = "changed"
    with pytest.raises(RuntimeError):
        repair.validate_execution_repair(parent, current)


def harnesses() -> tuple[dict, dict]:
    return tuple(yaml.safe_load((REPO / path).read_text(encoding="utf-8"))
                 for path in (repair.HARNESS_PARENT, repair.HARNESS))


def test_supplemental_harness_changes_only_source_pins_and_patch_lineage() -> None:
    parent, current = harnesses()
    repair.validate_harness_repair(parent, current)


@pytest.mark.parametrize("field", ["manager", "verifier", "budget", "available_operations",
                                  "anonymous_model_contract", "model_service_timeout_seconds"])
def test_supplemental_harness_does_not_waive_frozen_contracts(field: str) -> None:
    parent, current = harnesses()
    current[field] = "changed"
    with pytest.raises(RuntimeError, match="harness semantics"):
        repair.validate_harness_repair(parent, current)


def test_old_harness_remains_immutable_not_rewritten_by_validation() -> None:
    parent, current = harnesses()
    original = deepcopy(parent)
    repair.validate_harness_repair(parent, current)
    assert parent == original


def audit_fixture(root: Path) -> tuple[dict, dict, Path]:
    parent, current = executions()
    directory = root / "evidence" / "cell" / "attempt1"
    directory.mkdir(parents=True)
    original = {"disposition": "confounder", "problems": [
        "typed_action_failure_requires_audit:physical_execution_failed"],
        "operational_incidents": []}
    (directory / "admission.json").write_text(json.dumps(original))
    (directory / "trace.jsonl").write_text("synthetic immutable evidence")
    audit = {"version": "transport-receipt-repair-audit-v1", "run_id": "synthetic",
             "cell_id": "cell", "attempt_index": 1,
             "parent_execution_sha256": provenance_sha256(parent),
             "repaired_execution_candidate_sha256": provenance_sha256(current),
             "original_admission_sha256": provenance_sha256(original),
             "allowed_source_delta": repair.source_delta(
                 parent["source_sha256"], current["source_sha256"]),
             "semantic_contracts_unchanged": True, "original_evidence_unchanged": True,
             "queue_and_attempt_absent": True,
             "test_gates": {k: "passed" for k in (
                 "pytest", "ruff", "strict_pyright", "diff_check")},
             "original_evidence_file_sha256": {p.name: repair.sha256(p)
                                               for p in directory.iterdir()}}
    path = root / "readiness" / repair.AUDIT_NAME
    path.parent.mkdir()
    path.write_text(json.dumps(audit))
    return parent, current, path


def test_repair_audit_binds_complete_original_evidence_without_modifying_it(tmp_path: Path) -> None:
    parent, current, path = audit_fixture(tmp_path)
    before = {p.name: p.read_bytes() for p in (tmp_path / "evidence/cell/attempt1").iterdir()}
    repair._read_audit(tmp_path, parent, current)
    after = {p.name: p.read_bytes() for p in (tmp_path / "evidence/cell/attempt1").iterdir()}
    assert before == after
    assert path.exists()


@pytest.mark.parametrize("mutation", ["evidence", "extra_evidence", "source_candidate",
                                     "semantic", "tests", "live", "mixed_admission"])
def test_repair_audit_rejects_incomplete_or_drifted_proof(tmp_path: Path, mutation: str) -> None:
    parent, current, path = audit_fixture(tmp_path)
    audit = json.loads(path.read_text())
    directory = tmp_path / "evidence/cell/attempt1"
    if mutation == "evidence":
        (directory / "trace.jsonl").write_text("tampered")
    elif mutation == "extra_evidence":
        (directory / "added.json").write_text("{}")
    elif mutation == "source_candidate":
        audit["repaired_execution_candidate_sha256"] = "wrong"
    elif mutation == "semantic":
        audit["semantic_contracts_unchanged"] = False
    elif mutation == "tests":
        audit["test_gates"]["pytest"] = "failed"
    elif mutation == "live":
        audit["queue_and_attempt_absent"] = False
    else:
        original = {"disposition": "confounder", "problems": ["privacy_violation"],
                    "operational_incidents": []}
        (directory / "admission.json").write_text(json.dumps(original))
        audit["original_admission_sha256"] = provenance_sha256(original)
        audit["original_evidence_file_sha256"]["admission.json"] = repair.sha256(
            directory / "admission.json")
    path.write_text(json.dumps(audit))
    with pytest.raises(RuntimeError):
        repair._read_audit(tmp_path, parent, current)


def test_transport_verify_requires_exact_owned_new_namespace(tmp_path: Path) -> None:
    for path in (tmp_path / "execution-freeze-002.json", tmp_path / "outside" / repair.NAME):
        with pytest.raises(RuntimeError, match="new exact owned namespace"):
            repair.verify(tmp_path, REPO, path)


def test_transport_namespace_delegation_does_not_relax_old_freeze(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    monkeypatch.setattr(repair, "verify", lambda root, app, path: calls.append(path) or "verified")
    path = tmp_path / repair.NAME
    assert queue.verify_execution_freeze(path) == "verified"
    assert calls == [path]
    with pytest.raises(RuntimeError, match="new owned namespace"):
        queue.verify_execution_freeze(tmp_path / "execution-freeze-004.json")


def test_child_harness_selection_requires_validated_new_execution_freeze(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    monkeypatch.setattr(repair, "verify", lambda root, app, path: calls.append(path) or "checked")
    assert repair.harness_for_attempt(tmp_path, REPO, None) == REPO / repair.HARNESS_PARENT
    assert not calls
    path = tmp_path / repair.NAME
    assert repair.harness_for_attempt(tmp_path, REPO, path) == REPO / repair.HARNESS
    assert calls == [path]
