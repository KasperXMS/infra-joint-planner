import copy
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from infra_joint.control.provenance import provenance_sha256

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
wrapper = importlib.import_module("large_scale_resident_phase2_derived_field_review_v1")
heldout_field = importlib.import_module("test_resident_phase2_field_review").heldout_field


@pytest.fixture
def wrapped(heldout_field, monkeypatch):
    root, directory, ledger, parent, old, historical, original, task = heldout_field
    paths = (*wrapper.bindings.records.SOURCE_PATHS, wrapper.core.SOURCES[0])
    monkeypatch.setattr(wrapper.derived, "SOURCE_PATHS", paths)
    app = root / "app-input-cardinality-repair-003"
    monkeypatch.setattr(wrapper, "import_module", lambda name: SimpleNamespace(
        __file__=str(app / ("src/" + name.replace(".", "/") + ".py"))))
    monkeypatch.setattr(wrapper.derived, "review", lambda *_: {
        "derived_field_proof": [{"action_id": "synthetic-field-misuse"}]})
    (directory / "tc-attestation.json").write_text(json.dumps({
        "cleanup_error": None, "original_qdisc": {}, "restored_qdisc": {}}))
    result_path = directory / "runs/run4/result.json"
    result_path.write_text(json.dumps({"execution_completed": True,
                                      "evaluation": {"format_valid": True, "score": 0.0}}))
    return root, directory, ledger, parent, old, historical, original, task


def test_wrapper_preserves_raw_zero_score_history_and_forbids_repeated_creator(wrapped):
    root, directory, ledger, parent, old, _, original, _ = wrapped
    before = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    journal = ledger.path.read_bytes()
    created = wrapper.create_review("run4", parent, old)
    value = wrapper.verify_sidecar(Path(created["sidecar_path"]), ledger.attempts[0])
    assert value["reviewed_admission"]["original_evaluation"] == original["original_evaluation"]
    assert value["formal_execution_changed"] is value["replacement_authorized"] is False
    assert value["new_store_or_corpus_body_decoded"] is False
    assert "PRIVATE" not in json.dumps(value)
    assert ledger.path.read_bytes() == journal
    assert all(p.read_bytes() == content for p, content in before.items())
    with pytest.raises(FileExistsError):
        wrapper.create_review("run4", parent, old)
    assert len(list((root / wrapper.DIRECTORY).glob("*.json"))) == 1


@pytest.mark.parametrize("damage", ["historical", "worker", "imports", "evidence", "sidecar",
                                  "network", "residency", "shutdown", "admission"])
def test_wrapper_rejects_proof_source_evidence_and_cleanup_drift(wrapped, monkeypatch, damage):
    root, directory, ledger, parent, old, _, _, _ = wrapped
    created = wrapper.create_review("run4", parent, old)
    path = Path(created["sidecar_path"])
    if damage == "historical":
        def reject(*_):
            raise RuntimeError("historical drift")
        monkeypatch.setattr(wrapper.bindings, "verify_record", reject)
    elif damage == "worker":
        (root / "app-input-cardinality-repair-003" / wrapper.derived.SOURCE_PATHS[0]).write_text(
            "modified")
    elif damage == "imports":
        module = root / "another.py"
        module.write_text("different implementation")
        monkeypatch.setattr(wrapper, "import_module",
                            lambda _: SimpleNamespace(__file__=str(module)))
    elif damage == "evidence":
        (directory / "extra.json").write_text("{}")
    elif damage == "sidecar":
        value = json.loads(path.read_text())
        value["replacement_authorized"] = True
        path.write_text(json.dumps(value))
    elif damage == "network":
        value = json.loads((directory / "tc-attestation.json").read_text())
        value["cleanup_error"] = "failed"
        (directory / "tc-attestation.json").write_text(json.dumps(value))
    elif damage in {"residency", "shutdown"}:
        name, key = (("private/residency-validation.json", "passed") if damage == "residency"
                     else ("worker-shutdown.json", "verified_exited"))
        (directory / name).write_text(json.dumps({key: False}))
    else:
        value = json.loads((directory / "admission.json").read_text())
        value["problems"].append("another-finding")
        (directory / "admission.json").write_text(json.dumps(value))
    with pytest.raises((RuntimeError, KeyError)):
        wrapper.verify_sidecar(path, ledger.attempts[0])


def test_no_control_or_history_read_when_global_guard_rejects(wrapped, monkeypatch):
    _, _, _, parent, old, _, _, _ = wrapped
    def active(_):
        raise RuntimeError("active queue")
    monkeypatch.setattr(wrapper.core.previous.gate.evidence.private, "assert_inactive", active)
    with pytest.raises(RuntimeError, match="active queue"):
        wrapper.create_review("run4", parent, old)


def test_initial_shape_match_cannot_use_metadata_without_verified_shape(wrapped):
    _, directory, _, _, _, historical, _, task = wrapped
    states = json.loads((directory / "private/worker-state-after.json").read_text())
    damaged = copy.deepcopy(historical)
    damaged["materialized_shapes"]["old-corpus"]["sha256_hex"] = "wrong"
    with pytest.raises(RuntimeError):
        wrapper._initial_shapes(task, states, damaged)


def test_effective_receipt_digest_must_match_exact_admission(wrapped):
    root, _, ledger, parent, old, _, _, _ = wrapped
    created = wrapper.create_review("run4", parent, old)
    value = json.loads(Path(created["sidecar_path"]).read_text())
    attempt = SimpleNamespace(run_id="run4", reason=wrapper.REASON,
                              receipt_sha256=provenance_sha256(value["reviewed_admission"]))
    assert wrapper.effective_admission(root, attempt)["disposition"] == "valid"
    value["reviewed_admission"]["disposition"] = "confounder"
    Path(created["sidecar_path"]).write_text(json.dumps(value))
    with pytest.raises(RuntimeError):
        wrapper.effective_admission(root, attempt)
    assert ledger.attempts[0].disposition == "confounder"
