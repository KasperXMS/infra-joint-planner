import copy
import importlib
import json
import sys
from pathlib import Path

import pytest
from test_resident_E_query_phase2_gate import four_epoch_bundle
from test_resident_phase2_evidence_gate import file_bundle

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
gate = importlib.import_module("large_scale_resident_current_phase2_gate_v1")


def current_bundle() -> dict:
    value = four_epoch_bundle()
    value["private"]["version"] = gate.evidence.VERSION
    return value


def test_current_gate_keeps_exact_source004_and_existing_cap_guards():
    value = current_bundle()
    before = copy.deepcopy(value)
    receipt = gate.core.validate_bundle(**value, evidence_module=gate.evidence)
    assert receipt["phase2_execution_sha256"] == gate.evidence.sources.EXECUTIONS[4]
    assert receipt["phase2_cells"] == 144
    assert receipt["planned_cumulative_substantive_cells"] == 354
    assert value == before


@pytest.mark.parametrize("defect", ["historical_private_version", "missing_manual_review",
                                     "incomplete", "pending", "five_survivors"])
def test_current_gate_cannot_be_released_by_stale_or_partial_proofs(defect):
    value = current_bundle()
    if defect == "historical_private_version":
        value["private"]["version"] = "resident-four-epoch-private-evidence-paths-v1"
    elif defect == "missing_manual_review":
        value["audit"]["records"][0]["semantic_review_complete"] = False
    elif defect == "incomplete":
        value["snapshot"]["admitted_cells"] = 124
    elif defect == "pending":
        value["snapshot"]["pending_count"] = 1
    else:
        for entry in value["pruning"]["methods"][:5]:
            entry["status"] = "retain"
    with pytest.raises((RuntimeError, ValueError)):
        gate.core.validate_bundle(**value, evidence_module=gate.evidence)


def test_current_gate_blocks_live_queue_before_any_input_file_read(monkeypatch, tmp_path):
    def live(_):
        raise RuntimeError("queue live")

    monkeypatch.setattr(gate.evidence.private, "assert_inactive", live)
    monkeypatch.setattr(gate.core, "digest", lambda *_: pytest.fail("input read"))
    with pytest.raises(RuntimeError, match="queue live"):
        gate.freeze_gate({}, tmp_path / "unused.json")


def test_actual_file_gate_uses_current_collector_and_preserves_append_only_semantics(
    monkeypatch, tmp_path,
):
    # Synthetic file-backed complete audit only; never a claim about live168.
    paths, output = file_bundle(monkeypatch, tmp_path)
    values = {name: json.loads(path.read_text()) for name, path in paths.items()}
    freezes = {str(k): v for k, v in gate.evidence.sources.EXECUTIONS.items()}
    for name in ("snapshot", "private", "audit"):
        values[name]["execution_freezes"] = freezes
    values["private"]["version"] = gate.evidence.VERSION
    for i, row in enumerate(values["snapshot"]["rows"]):
        attempt = row["attempts"][0]
        attempt.pop("execution_source_boundary")
        attempt["execution_source_epoch"] = i % 4 + 1
        attempt["execution_sha256"] = freezes[str(i % 4 + 1)]
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
