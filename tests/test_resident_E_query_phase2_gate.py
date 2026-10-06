import copy
import importlib
import json
import sys
from pathlib import Path

import pytest
from test_resident_phase2_evidence_gate import bundle, file_bundle

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
gate = importlib.import_module("large_scale_resident_E_query_phase2_gate_v1")


def four_epoch_bundle() -> dict:
    value = bundle()
    freezes = {str(k): v for k, v in gate.evidence.sources.EXECUTIONS.items()}
    for name in ("snapshot", "private", "audit"):
        value[name]["execution_freezes"] = freezes
    value["private"]["version"] = gate.evidence.VERSION
    for i, row in enumerate(value["snapshot"]["rows"]):
        attempt = row["attempts"][0]
        attempt.pop("execution_source_boundary")
        attempt["execution_source_epoch"] = i % 4 + 1
        attempt["execution_sha256"] = freezes[str(i % 4 + 1)]
        support = value["private"]["records"][i]
        support.pop("execution_source_boundary")
        support["execution_source_epoch"] = attempt["execution_source_epoch"]
        support["execution_sha256"] = attempt["execution_sha256"]
        value["audit"]["records"][i]["execution_sha256"] = attempt["execution_sha256"]
    return value


def test_gate_selects_exact_source004_not_cardinality003() -> None:
    value = four_epoch_bundle()
    before = copy.deepcopy(value)
    result = gate.core.validate_bundle(**value, evidence_module=gate.evidence)
    assert result["phase2_execution_sha256"] == gate.evidence.sources.EXECUTIONS[4]
    assert result["phase2_cells"] == 144
    assert value == before


@pytest.mark.parametrize("defect", ["legacy_bundle", "private_version", "private_source",
                                     "missing_review", "pending", "fifth_survivor"])
def test_four_source_gate_cannot_be_released_by_stale_or_incomplete_audits(defect: str) -> None:
    value = four_epoch_bundle()
    if defect == "legacy_bundle":
        value = bundle()
    elif defect == "private_version":
        value["private"]["version"] = "resident-cardinality-private-evidence-paths-v1"
    elif defect == "private_source":
        value["private"]["records"][3]["execution_source_epoch"] = 3
    elif defect == "missing_review":
        value["audit"]["records"][3]["adoption_review_complete"] = False
    elif defect == "pending":
        value["snapshot"]["pending_count"] = 1
    else:
        for entry in value["pruning"]["methods"][:5]:
            entry["status"] = "retain"
    with pytest.raises((RuntimeError, ValueError)):
        gate.core.validate_bundle(**value, evidence_module=gate.evidence)


def test_new_gate_live_guard_precedes_every_input_read(monkeypatch, tmp_path: Path) -> None:
    def active(root):
        raise RuntimeError("live PhaseI")

    monkeypatch.setattr(gate.evidence.private, "assert_inactive", active)
    monkeypatch.setattr(gate.core, "digest", lambda _: pytest.fail("input read while live"))
    with pytest.raises(RuntimeError, match="live PhaseI"):
        gate.freeze_gate({}, tmp_path / "absent.json")


def test_four_source_actual_gate_persistence_equals_controller_verification(
    monkeypatch, tmp_path: Path,
) -> None:
    # Real synthetic file hashes and guards; no fabricated actual study result.
    paths, output = file_bundle(monkeypatch, tmp_path)
    values = {name: json.loads(path.read_text()) for name, path in paths.items()}
    replacement = four_epoch_bundle()
    for name in ("snapshot", "private", "audit"):
        values[name]["execution_freezes"] = replacement[name]["execution_freezes"]
    values["private"]["version"] = gate.evidence.VERSION
    for i, row in enumerate(values["snapshot"]["rows"]):
        attempt = row["attempts"][0]
        attempt.pop("execution_source_boundary")
        attempt["execution_source_epoch"] = i % 4 + 1
        attempt["execution_sha256"] = gate.evidence.sources.EXECUTIONS[i % 4 + 1]
        support = values["private"]["records"][i]
        support.pop("execution_source_boundary")
        support["execution_source_epoch"] = attempt["execution_source_epoch"]
        support["execution_sha256"] = attempt["execution_sha256"]
        values["audit"]["records"][i]["execution_sha256"] = attempt["execution_sha256"]
    values["private"]["audit_source_sha256"] = {Path(p).name: gate.digest(Path(p)) for p in (
        gate.evidence.__file__, gate.evidence.private.__file__,
        sys.modules[gate.evidence.resolved_membership.__module__].__file__,
        sys.modules[gate.evidence.private.scan_store.__module__].__file__,
    )}
    for name in ("snapshot", "private"):
        paths[name].write_text(json.dumps(values[name]))
    values["audit"]["source_projection_sha256"] = gate.digest(paths["snapshot"])
    values["audit"]["private_evidence_sha256"] = gate.digest(paths["private"])
    paths["audit"].write_text(json.dumps(values["audit"]))
    values["pruning"]["comprehensive_audit_sha256"] = gate.digest(paths["audit"])
    paths["pruning"].write_text(json.dumps(values["pruning"]))
    monkeypatch.setattr(gate.evidence.sources, "collect",
                        lambda: copy.deepcopy(values["snapshot"]))
    saved = gate.freeze_gate(paths, output)
    assert saved == gate.verify_gate_inputs(paths) == json.loads(output.read_text())
    assert saved["phase2_execution_sha256"] == gate.evidence.sources.EXECUTIONS[4]
    with pytest.raises(RuntimeError, match="append-only"):
        gate.freeze_gate(paths, output)
