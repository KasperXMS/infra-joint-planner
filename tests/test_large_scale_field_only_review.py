import importlib
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from test_large_scale_field_policy_review import fixture as field_fixture

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import AttemptLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
review = importlib.import_module("large_scale_field_only_review_v1")


def fixture(root: Path) -> tuple[dict, list, dict]:
    original, events, shapes, _ = field_fixture(root)
    original["problems"] = [review.GATE]
    original["execution_completed"] = True
    original["original_evaluation"] = {"benchmark_score": 1.0, "format_valid": True}
    original["terminal_failure"] = None
    events[1]["payload"]["action"]["owner_agent_id"] = "manager"
    events[2]["payload"]["owner_agent_id"] = "manager"
    return original, events, shapes


def test_exact_root_field_misuse_keeps_quality_without_inventing_provider_failure(tmp_path: Path):
    original, events, shapes = fixture(tmp_path)
    before = deepcopy((original, events, shapes))
    result = review.review(original, events, shapes)
    assert result["covered_original_findings"] == [review.GATE]
    assert result["field_misuse_proof"][0]["root_received_correct_schema"]
    assert result["field_misuse_proof"][0]["reached_model_inference"] is False
    assert result["reviewed_admission"]["failure_class"] == "root_operator_argument_misuse"
    assert result["reviewed_admission"]["original_evaluation"] == original["original_evaluation"]
    assert result["reviewed_admission"]["replacement_authorized"] is False
    assert "provider_policy_proof" not in result
    assert "PRIVATE" not in json.dumps(result)
    assert (original, events, shapes) == before


@pytest.mark.parametrize("damage", [
    "extra-finding", "policy-finding", "operational", "no-root", "hidden-schema",
    "duplicate-observation", "duplicate-prepared", "duplicate-physical", "wrong-tool",
    "model-action", "specialist-action", "specialist-observation", "generated-input",
    "two-inputs", "field-declared", "field-present", "wrong-message", "wrong-physical-message",
    "wrong-stage", "no-selection", "not-completed", "graph-open", "uncovered-physical",
    "missing-physical", "no-failure",
])
def test_no_broad_validation_waiver(tmp_path: Path, damage: str):
    original, events, shapes = fixture(tmp_path)
    if damage == "extra-finding":
        original["problems"].append("privacy_violation")
    elif damage == "policy-finding":
        original["problems"].append("unclassified_API_failure_requires_audit")
    elif damage == "operational":
        original["operational_incidents"] = ["timeout"]
    elif damage == "no-root":
        events.pop(0)
    elif damage == "hidden-schema":
        events[0]["payload"]["input_items"][0]["content"] = '{"task":{"artifacts":[]}}'
    elif damage.startswith("duplicate-"):
        position = {"duplicate-observation": 2, "duplicate-prepared": 1,
                    "duplicate-physical": 3}[damage]
        events.append(deepcopy(events[position]))
    elif damage == "wrong-tool":
        events[1]["payload"]["action"]["operator"] = "filter_records"
    elif damage == "model-action":
        events[1]["payload"]["action"]["action_type"] = "model"
    elif damage == "specialist-action":
        events[1]["payload"]["action"]["owner_agent_id"] = "specialist"
    elif damage == "specialist-observation":
        events[2]["payload"]["owner_agent_id"] = "specialist"
    elif damage == "generated-input":
        events[1]["payload"]["action"]["inputs"] = ["generated"]
    elif damage == "two-inputs":
        events[1]["payload"]["action"]["inputs"] *= 2
    elif damage in ("field-declared", "field-present"):
        key = "all_declared_fields" if damage == "field-declared" else "actual_union_fields"
        shapes["corpus"][key].append("text")
    elif damage == "wrong-message":
        events[2]["payload"]["failure_message"] = "artifact missing"
    elif damage == "wrong-physical-message":
        events[3]["payload"]["failure"]["failure_message"] = "backend error"
    elif damage == "wrong-stage":
        events[3]["payload"]["failure"]["stage"] = "selection"
    elif damage == "no-selection":
        events[3]["payload"]["selection"] = {}
    elif damage == "not-completed":
        events.pop(4)
    elif damage == "graph-open":
        events[5]["payload"]["nodes"][0]["status"] = "running"
    elif damage == "uncovered-physical":
        extra = deepcopy(events[3])
        extra["payload"]["action_id"] = "unobserved-action"
        events.append(extra)
    elif damage == "missing-physical":
        events.pop(3)
    else:
        events = events[:1]
    with pytest.raises((RuntimeError, KeyError)):
        review.review(original, events, shapes)


def test_every_independent_shard_failure_is_bound(tmp_path: Path):
    original, events, shapes = fixture(tmp_path)
    for position in range(2):
        for source in deepcopy(events[1:5]):
            if source["event_type"] == "logical.action.prepared":
                source["payload"]["action"]["action_id"] = f"action-{position}"
            else:
                source["payload"]["action_id"] = f"action-{position}"
            events.append(source)
        events[5]["payload"]["nodes"].append(
            {"action_id": f"action-{position}", "status": "failed"})
    result = review.review(original, events, shapes)
    assert len(result["field_misuse_proof"]) == 3


def test_completion_membership_checks_attempt_proofs_once(tmp_path: Path, monkeypatch):
    from types import SimpleNamespace

    calls = []
    monkeypatch.setattr(review.FieldOnlyAttemptLedger, "attempts", property(lambda self: (
        calls.append(True) or (SimpleNamespace(cell_id="a", disposition="valid"),)
    )))
    ledger = review.FieldOnlyAttemptLedger(tmp_path / "journal.jsonl", ("a", "b", "c", "d"),
                                          "0" * 64)
    assert ledger.completed_cells == ("a",)
    assert calls == [True]


def ledger_fixture(root: Path):
    original, events, shapes = fixture(root)
    directory = root / "evidence/cell4/attempt1"
    trace = directory / "runs/run4/trace.jsonl"
    trace.parent.mkdir(parents=True)
    trace.write_text("".join(json.dumps(e) + "\n" for e in events))
    (directory / "admission.json").write_text(json.dumps(original))
    for source in review.previous.SOURCE_PATHS:
        path = root / "app" / source
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("frozen source")
    ledger = AttemptLedger(root / "journal.jsonl", ("cell4",), "0" * 64)
    ledger.reserve("cell4", "run4", "b" * 64)
    ledger.settle("run4", "confounder", review.GATE, provenance_sha256(original))
    proof = review.review(original, events, shapes)
    sidecar = root / review.DIRECTORY / "run4.json"
    sidecar.parent.mkdir()
    value = {"run_id": "run4", "original_admission_sha256": provenance_sha256(original),
             "original_execution_sha256": "b" * 64, "reviewer_sources_sha256": review.sources(),
             "execution_sources_sha256": {p: review.sha256(root / "app" / p)
                                           for p in review.previous.SOURCE_PATHS},
             "initial_artifact_shapes": shapes, "original_evidence_file_sha256": {
                 str(p.relative_to(directory)): review.sha256(p)
                 for p in directory.rglob("*") if p.is_file()}, **proof,
             "reviewed_admission_sha256": provenance_sha256(proof["reviewed_admission"])}
    sidecar.write_text(json.dumps(value))
    return sidecar, ledger, directory


def test_sidecar_changes_only_offline_membership_never_originals_or_retry_right(tmp_path: Path):
    _, ledger, directory = ledger_fixture(tmp_path)
    before = ledger.path.read_bytes(), (directory / "admission.json").read_bytes()
    view = review.FieldOnlyAttemptLedger(ledger.path, ledger.cells, ledger.schedule_sha256)
    assert view.completed_cells == ("cell4",)
    attempt = view.attempts[0]
    assert attempt.disposition == "valid"
    assert view.original_attempts[0].disposition == "confounder"
    admitted = review.effective_admission(tmp_path, attempt)
    assert admitted["original_evaluation"]["benchmark_score"] == 1
    assert before == (ledger.path.read_bytes(), (directory / "admission.json").read_bytes())
    with pytest.raises(RuntimeError, match="must not be repeated"):
        view.reserve("cell4", "replacement", "b" * 64)


@pytest.mark.parametrize("damage", ["body", "source", "evidence", "proof", "reviewer", "receipt"])
def test_direct_sidecar_proof_rejects_drift(tmp_path: Path, damage: str):
    sidecar, ledger, directory = ledger_fixture(tmp_path)
    attempt = ledger.attempts[0]
    review.verify_sidecar(sidecar, attempt)
    value = json.loads(sidecar.read_text())
    if damage == "body":
        Path(value["initial_artifact_shapes"]["corpus"]["path"]).write_text('[]')
    elif damage == "source":
        (tmp_path / "app" / review.previous.SOURCE_PATHS[0]).write_text("changed")
    elif damage == "evidence":
        (directory / "extra.json").write_text("{}")
    elif damage == "proof":
        value["field_misuse_proof"][0]["reached_model_inference"] = True
        sidecar.write_text(json.dumps(value))
    elif damage == "reviewer":
        value["reviewer_sources_sha256"]["field_only"] = "c" * 64
        sidecar.write_text(json.dumps(value))
    else:
        value["original_execution_sha256"] = "c" * 64
        sidecar.write_text(json.dumps(value))
    with pytest.raises(RuntimeError):
        review.verify_sidecar(sidecar, attempt)
