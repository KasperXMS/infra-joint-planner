import importlib
import json
import sys
from pathlib import Path

import pytest
from test_resident_record_review import field_case as field_case

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import AttemptLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
reviewer = importlib.import_module("large_scale_resident_method_contract_review_v1")


def fixture(root: Path, monkeypatch: pytest.MonkeyPatch) -> tuple:
    source = root / "app" / reviewer.SOURCE
    source.parent.mkdir(parents=True)
    source.write_text("wrong E tool registration", encoding="utf-8")
    source_hash = reviewer.sha256(source)
    monkeypatch.setattr(reviewer, "OLD_SOURCE_SHA256", source_hash)
    freeze = {"source_sha256": {reviewer.SOURCE: source_hash}}
    (root / "execution-freeze-001.json").write_text(json.dumps(freeze), encoding="utf-8")
    cell, run = "phase1-test-E", "original"
    ledger = reviewer.MethodContractAttemptLedger(root / "phase1-attempts.jsonl",
                                                  (cell, "next-B"), "a" * 64)
    original = {"disposition": "valid", "reason": "ordinary_outcome", "problems": [],
                "original_evaluation": {"benchmark_score": 0}}
    ledger.reserve(cell, run, provenance_sha256(freeze))
    ledger.settle(run, "valid", original["reason"], provenance_sha256(original))
    directory = root / "evidence" / cell / "attempt1"
    api = directory / "private/api"
    api.mkdir(parents=True)
    (directory / "admission.json").write_text(json.dumps(original), encoding="utf-8")
    events = [{"event_type": "method.variant.start", "payload": {"variant": "route-e-v0"}}]
    run_path = directory / "runs" / run
    run_path.mkdir(parents=True)
    (run_path / "trace.jsonl").write_text(json.dumps(events[0]) + "\n", encoding="utf-8")
    for call, recipient in (("first", "manager"), ("second", "manager"), ("third", "verifier")):
        tools = (["invoke_model", "estimate_invoke_model"] if recipient == "manager"
                 else ["submit_verification"])
        (api / (call + "-usage.json")).write_text(json.dumps({
            "call_id": call, "recipient": recipient}), encoding="utf-8")
        (api / (call + "-request.json")).write_text(json.dumps({
            "tools": [{"function": {"name": tool}} for tool in tools]}), encoding="utf-8")
    proof = root / reviewer.BUG_PROOF
    proof.parent.mkdir()
    proof.write_text(json.dumps({"affected_effective_run_ids": [run]}), encoding="utf-8")
    monkeypatch.setattr(reviewer, "BUG_SHA256", reviewer.sha256(proof))
    attempt = ledger.attempts[0]
    value = {**reviewer.review_e(original, events, api), "run_id": run,
             "original_admission_sha256": attempt.receipt_sha256,
             "original_raw_admission_sha256": provenance_sha256(original),
             "original_execution_sha256": attempt.execution_sha256,
             "frozen_source_sha256": source_hash, "bug_proof_sha256": reviewer.BUG_SHA256,
             "reviewer_source_sha256": reviewer.sha256(Path(reviewer.__file__)),
             "original_evidence_file_sha256": reviewer.evidence_files(directory)}
    value["reviewed_admission_sha256"] = provenance_sha256(value["reviewed_admission"])
    sidecar = root / reviewer.DIRECTORY / (run + ".json")
    sidecar.parent.mkdir()
    sidecar.write_text(json.dumps(value), encoding="utf-8")
    return ledger, sidecar, directory, events


def test_e_tool_exposure_excludes_even_wrong_answer_without_query_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger, sidecar, directory, _ = fixture(tmp_path, monkeypatch)
    before = (tmp_path / "phase1-attempts.jsonl").read_bytes()
    files = reviewer.evidence_files(directory)
    ledger.invalidate_e("original")
    assert (tmp_path / "phase1-attempts.jsonl").read_bytes().startswith(before)
    assert ledger.completed_cells == ()
    assert reviewer.evidence_files(directory) == files
    assert ledger.attempts[0].reason == reviewer.REASON
    with pytest.raises(RuntimeError, match="confounder"):
        ledger.reserve("phase1-test-E", "unauthorized", "b" * 64)
    value = json.loads(sidecar.read_text())
    ledger.authorize_generic_repair("original", original_admission_sha256=
                                    value["reviewed_admission_sha256"],
                                    repair_audit_sha256="c" * 64, new_execution_sha256="d" * 64)
    with pytest.raises(RuntimeError, match="audited new freeze"):
        ledger.reserve("phase1-test-E", "wrong-freeze", "b" * 64)
    ledger.reserve("phase1-test-E", "repair", "d" * 64)
    ledger.settle("repair", "valid", "wrong_answer", "e" * 64)
    loaded = reviewer.MethodContractAttemptLedger(ledger.path, ledger.cells, "a" * 64)
    assert loaded.completed_cells == ("phase1-test-E",)
    with pytest.raises(RuntimeError, match="must not be repeated"):
        loaded.reserve("phase1-test-E", "quality-retry", "d" * 64)
    loaded.reserve("next-B", "next", "d" * 64)
    assert reviewer.evidence_files(directory) == files


@pytest.mark.parametrize("damage", ["source", "request", "usage", "scope", "review",
                                     "symlink", "original", "freeze"])
def test_e_exclusion_rejects_identity_scope_and_evidence_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str,
) -> None:
    ledger, sidecar, directory, _ = fixture(tmp_path, monkeypatch)
    if damage == "source":
        (tmp_path / "app" / reviewer.SOURCE).write_text("changed")
    elif damage in {"request", "usage"}:
        (directory / "private/api" / ("first-" + damage + ".json")).write_text("{}")
    elif damage == "scope":
        (tmp_path / reviewer.BUG_PROOF).write_text("{}")
    elif damage == "original":
        (directory / "admission.json").write_text("{}")
    elif damage == "freeze":
        (tmp_path / "execution-freeze-001.json").write_text("{}")
    elif damage == "symlink":
        try:
            (directory / "escaped").symlink_to(sidecar)
        except OSError:
            # Still exercise the fail-closed guard on Windows without granting
            # link-creation rights; Linux uses an actual filesystem symlink.
            escaped = directory / "escaped"
            escaped.write_text("synthetic link marker")
            original_is_symlink = Path.is_symlink
            monkeypatch.setattr(Path, "is_symlink",
                                lambda p: p == escaped or original_is_symlink(p))
    else:
        value = json.loads(sidecar.read_text())
        value["proof"] = []
        sidecar.write_text(json.dumps(value))
    with pytest.raises((RuntimeError, KeyError)):
        ledger.invalidate_e("original")


def test_e_review_requires_each_actual_manager_request_not_verifier_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, directory, events = fixture(tmp_path, monkeypatch)
    original = json.loads((directory / "admission.json").read_text())
    value = reviewer.review_e(original, events, directory / "private/api")
    assert len(value["proof"]) == 2
    path = directory / "private/api/second-request.json"
    path.write_text(json.dumps({"tools": [{"function": {"name": "invoke_model"}}]}))
    with pytest.raises(RuntimeError, match="every affected"):
        reviewer.review_e(original, events, directory / "private/api")


@pytest.mark.parametrize("damage", ["other-finding", "other-route", "no-request"])
def test_review_cannot_waive_unrelated_failures_or_other_methods(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str,
) -> None:
    _, _, directory, events = fixture(tmp_path, monkeypatch)
    original = json.loads((directory / "admission.json").read_text())
    if damage == "other-finding":
        original["problems"] = ["privacy_leak"]
    elif damage == "other-route":
        events[0]["payload"]["variant"] = "route-b-v0"
    else:
        for p in (directory / "private/api").glob("*-usage.json"):
            p.unlink()
    with pytest.raises(RuntimeError):
        reviewer.review_e(original, events, directory / "private/api")


def test_live_attempt_prohibits_retrospective_invalidations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger, _, _, _ = fixture(tmp_path, monkeypatch)
    ledger.reserve("next-B", "active", "b" * 64)
    before = ledger.path.read_bytes()
    with pytest.raises(RuntimeError, match="still be live"):
        ledger.invalidate_e("original")
    assert ledger.path.read_bytes() == before


@pytest.mark.parametrize("epoch,damage", [(3, None), (3, "source"), (3, "shape"),
                                         (3, "replica"), (1, None)])
def test_record_review_binds_actual_source_epoch_and_preserves_historical_review(
    field_case, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, epoch: int, damage: str | None,
) -> None:
    original, events, shapes = field_case
    events.insert(0, {"event_type": "method.variant.start", "payload": {"variant": "route-e-v0"}})
    original["reason"] = reviewer.records.GATE_PROBLEM
    cell, run = "phase1-test-E", "run"
    directory = tmp_path / "evidence" / cell / "attempt1"
    run_path = directory / "runs" / run
    run_path.mkdir(parents=True)
    (directory / "admission.json").write_text(json.dumps(original))
    (run_path / "trace.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    shapes["merged"].update(media_type="application/json", size_bytes=100)
    metadata = {k: shapes["merged"][k] for k in (
        "artifact_id", "media_type", "size_bytes", "sha256_hex")}
    private = directory / "private"
    private.mkdir()
    state = private / "worker-state-after.json"
    state.write_text(json.dumps({"A28": {"artifacts": [metadata]}}))
    app = tmp_path / reviewer.APPS[epoch - 1]
    for relative in (*reviewer.records.SOURCE_PATHS, reviewer.SOURCE):
        file = app / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("synthetic original source\n")
    sources = {p: reviewer.sha256(app / p) for p in
               (*reviewer.records.SOURCE_PATHS, reviewer.SOURCE)}
    freeze = {"source_sha256": sources}
    (tmp_path / f"execution-freeze-{epoch:03d}.json").write_text(json.dumps(freeze))
    raw = AttemptLedger(tmp_path / "phase1-attempts.jsonl", (cell, "next"), "a" * 64)
    raw.reserve(cell, run, provenance_sha256(freeze))
    raw.settle(run, "confounder", reviewer.records.GATE_PROBLEM, provenance_sha256(original))
    attempt = raw.attempts[0]
    review = reviewer.records.review(original, events, shapes)
    value = {"run_id": run, "original_admission_sha256": attempt.receipt_sha256,
             "original_execution_sha256": attempt.execution_sha256,
             "reviewer_source_sha256": reviewer.sha256(Path(
                 reviewer.records.__file__ if epoch == 1 else reviewer.__file__)),
             "record_reviewer_source_sha256": reviewer.sha256(Path(reviewer.records.__file__)),
             "execution_sources_sha256": {p: sources[p] for p in reviewer.records.SOURCE_PATHS},
             "materialized_shapes": shapes, "original_evidence_file_sha256":
             reviewer.evidence_files(directory), **review,
             "reviewed_admission_sha256": provenance_sha256(review["reviewed_admission"])}
    sidecar = tmp_path / (reviewer.records.DIRECTORY if epoch == 1 else
                          reviewer.RECORD_DIRECTORY) / (run + ".json")
    sidecar.parent.mkdir()
    sidecar.write_text(json.dumps(value))
    before = raw.path.read_bytes()
    if damage == "source":
        (app / reviewer.records.SOURCE_PATHS[0]).write_text("drift")
    elif damage == "shape":
        value["materialized_shapes"]["merged"]["actual_union_fields"].append("text")
        sidecar.write_text(json.dumps(value))
    elif damage == "replica":
        state.write_text('{"A28":{"artifacts":[]}}')
    ledger = reviewer.MethodContractAttemptLedger(raw.path, raw.cells, raw.schedule_sha256)
    if damage:
        with pytest.raises(RuntimeError):
            _ = ledger.completed_cells
        return
    assert ledger.completed_cells == (cell,)
    assert reviewer.effective_admission(tmp_path, ledger.attempts[0])["disposition"] == "valid"
    assert raw.path.read_bytes() == before
    with pytest.raises(RuntimeError, match="must not be repeated"):
        ledger.reserve(cell, "retry", "b" * 64)
    if epoch == 3:
        return
    # An E sample already adjudicated as valid must retain that old review;
    # the new method-contract defect layers on top, not on its raw settlement.
    api = private / "api"
    api.mkdir()
    (api / "first-usage.json").write_text(json.dumps({"call_id": "first", "recipient": "manager"}))
    (api / "first-request.json").write_text(json.dumps({"tools": [
        {"function": {"name": "invoke_model"}}, {"function": {"name": "estimate_invoke_model"}}]}))
    # The old proof's immutable file set must include the newly assembled fixture API.
    value["original_evidence_file_sha256"] = reviewer.evidence_files(directory)
    sidecar.write_text(json.dumps(value))
    proof = tmp_path / reviewer.BUG_PROOF
    proof.parent.mkdir()
    proof.write_text(json.dumps({"affected_effective_run_ids": [run]}))
    monkeypatch.setattr(reviewer, "BUG_SHA256", reviewer.sha256(proof))
    monkeypatch.setattr(reviewer, "OLD_SOURCE_SHA256", sources[reviewer.SOURCE])
    effective = ledger.attempts[0]
    e = {**reviewer.review_e(review["reviewed_admission"], events, api), "run_id": run,
         "original_admission_sha256": effective.receipt_sha256,
         "original_raw_admission_sha256": provenance_sha256(original),
         "original_execution_sha256": attempt.execution_sha256,
         "reviewer_source_sha256": reviewer.sha256(Path(reviewer.__file__)),
         "frozen_source_sha256": sources[reviewer.SOURCE], "bug_proof_sha256": reviewer.BUG_SHA256,
         "original_evidence_file_sha256": reviewer.evidence_files(directory)}
    e["reviewed_admission_sha256"] = provenance_sha256(e["reviewed_admission"])
    path = tmp_path / reviewer.DIRECTORY / (run + ".json")
    path.parent.mkdir()
    path.write_text(json.dumps(e))
    old_review = sidecar.read_bytes()
    ledger.invalidate_e(run)
    assert ledger.attempts[0].reason == reviewer.REASON
    ledger.authorize_generic_repair(run, original_admission_sha256=e["reviewed_admission_sha256"],
                                    repair_audit_sha256="c" * 64, new_execution_sha256="d" * 64)
    ledger.reserve(cell, "repaired", "d" * 64)
    ledger.settle("repaired", "valid", "wrong_answer", "e" * 64)
    loaded = reviewer.MethodContractAttemptLedger(raw.path, raw.cells, raw.schedule_sha256)
    assert loaded.completed_cells == (cell,)
    assert loaded.original_attempts[0].disposition == "confounder"
    assert sidecar.read_bytes() == old_review
