import copy
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import AttemptLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
review = importlib.import_module("large_scale_resident_phase2_field_review_v1")
field_fixture = importlib.import_module("test_large_scale_field_only_review").fixture


@pytest.fixture
def heldout_field(tmp_path, monkeypatch):
    original, events, shapes = field_fixture(tmp_path)
    root, directory = tmp_path, tmp_path / "evidence/cell4/attempt1"
    monkeypatch.setattr(review.core.frozen, "ROOT", root)
    monkeypatch.setattr(review.core.frozen, "require_remote", lambda: None)
    monkeypatch.setattr(review.core.frozen, "verify_freeze", lambda: "b" * 64)
    monkeypatch.setattr(review.core.previous.gate.evidence.private,
                        "assert_inactive", lambda _: None)
    task = json.loads(events[0]["payload"]["input_items"][0]["content"])["task"]
    shape = shapes["corpus"]
    historical = {"materialized_shapes": {"old-corpus": {
        "media_type": "application/json", "size_bytes": Path(shape["path"]).stat().st_size,
        "sha256_hex": shape["sha256"], "record_count": 2,
        "actual_union_fields": ["body"], "all_records_have_string_body": True}}}
    metadata = {"artifact_id": "corpus", "media_type": "application/json",
                "size_bytes": Path(shape["path"]).stat().st_size, "sha256_hex": shape["sha256"]}
    (directory / "private/worker-state-after.json").write_text(json.dumps({
        "A4": {"artifacts": [metadata]}}))
    (directory / "private/residency-validation.json").write_text('{"passed":true}')
    (directory / "worker-shutdown.json").write_text('{"verified_exited":true}')
    (directory / "process-exit.json").write_text('{"returncode":0}')
    (directory / "admission.json").write_text(json.dumps(original))
    trace = directory / "runs/run4/trace.jsonl"
    trace.parent.mkdir(parents=True)
    events[1]["payload"]["action"]["arguments"]["query"] += "\u2028PRIVATE_SEPARATOR"
    trace.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events),
                     encoding="utf-8")
    api = directory / "private/api"
    for path in api.glob("*"):
        path.unlink()
    (api / "call1-usage.json").write_text(json.dumps({"call_id": "call1",
                                                       "recipient": "manager"}))
    (api / "call1-request.json").write_text(json.dumps({"messages": [
        {"role": "user", "content": json.dumps({"task": task})}]}))
    paths = {}
    for relative in (*review.bindings.records.SOURCE_PATHS, review.core.SOURCES[0]):
        path = root / "app-input-cardinality-repair-003" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("frozen Worker source")
        paths[relative] = review.core.legacy.sha256(path)
    (root / "execution-freeze-003.json").write_text(json.dumps({"source_sha256": paths}))
    monkeypatch.setattr(review.bindings, "frozen_sources", lambda *_: copy.deepcopy(paths))
    monkeypatch.setattr(review.bindings, "verify_record", lambda *_: copy.deepcopy(historical))
    old_run = root.name + "-phase1-old-attempt1"
    old = root / review.bindings.RECORD_DIRECTORY / (old_run + ".json")
    old.parent.mkdir()
    old.write_text(json.dumps(historical))
    (root / "phase1-attempts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in [
        {"event": "reserved", "cell_id": "phase1-old", "run_id": old_run,
         "attempt_index": 1, "execution_sha256": "c" * 64},
        {"event": "settled", "run_id": old_run, "disposition": "confounder",
         "reason": review.field.GATE, "receipt_sha256": "d" * 64}]))
    saved = {"source_sha256": review.core.previous.source_bindings(),
             "execution_freeze_sha256": "b" * 64, "phase2_schedule_sha256": "a" * 64,
             "pricing_path": str(root / "prices"), "nominal_cells": 3}
    parent = root / "phase2-control-freeze-001.json"
    parent.write_text(json.dumps(saved))
    (root / "cell-configs").mkdir()
    (root / "cell-configs/run4.yaml").write_text("{}")
    cells = tuple(SimpleNamespace(cell_id=c) for c in ("cell4", "next", "future"))
    monkeypatch.setattr(review.core.previous, "checked_control", lambda _: (saved, cells))
    monkeypatch.setattr(review.core.previous.previous, "admission", lambda *_: original)
    ledger = AttemptLedger(root / "phase2-attempts.jsonl", ("cell4", "next", "future"), "a" * 64)
    ledger.reserve("cell4", "run4", "b" * 64)
    ledger.settle("run4", "confounder", review.field.GATE, provenance_sha256(original))
    # Proof must not depend on reading even the fixture's prepared corpus.
    Path(shape["path"]).unlink()
    return root, directory, ledger, parent, old, historical, original, task


def test_exact_field_review_reuses_hashes_preserves_history_and_forbids_retry(heldout_field):
    root, directory, ledger, parent, old, _, original, _ = heldout_field
    before = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    journal = ledger.path.read_bytes()
    value = review.create_review("run4", parent, old)
    assert value["confirmed_field_failures"] == value["actual_manager_requests"] == 1
    assert value["retry"] is False and value["new_store_or_corpus_body_decoded"] is False
    view = review.FieldReviewedAttemptLedger(ledger.path, ledger.cells, ledger.schedule_sha256)
    assert view.original_attempts[0].disposition == "confounder"
    assert view.attempts[0].disposition == "valid" and view.completed_cells == ("cell4",)
    receipt = review.effective_admission(root, view.attempts[0])
    assert receipt["original_evaluation"] == original["original_evaluation"]
    assert receipt["replacement_authorized"] is False
    sidecar = json.loads(Path(value["sidecar_path"]).read_text())
    assert "PRIVATE" not in json.dumps(sidecar)
    assert sidecar["formal_execution_changed"] is False
    assert ledger.path.read_bytes() == journal
    assert all(p.read_bytes() == content for p, content in before.items())
    with pytest.raises(RuntimeError, match="must not be repeated"):
        view.reserve("cell4", "forbidden-retry", "b" * 64)
    with pytest.raises(FileExistsError):
        review.create_review("run4", parent, old)


@pytest.mark.parametrize("damage", ["hash", "bytes", "media", "replicas", "count",
                                  "non-string-body", "fields", "missing", "ambiguous"])
def test_hash_reuse_never_assumes_body_or_declared_equivalence(heldout_field, damage):
    _, directory, _, _, _, historical, _, task = heldout_field
    states = json.loads((directory / "private/worker-state-after.json").read_text())
    known = historical["materialized_shapes"]["old-corpus"]
    if damage in {"hash", "bytes", "media"}:
        key = {"hash": "sha256_hex", "bytes": "size_bytes", "media": "media_type"}[damage]
        states["A4"]["artifacts"][0][key] = "wrong"
    elif damage == "replicas":
        states["A5"] = copy.deepcopy(states["A4"])
        states["A5"]["artifacts"][0]["sha256_hex"] = "wrong"
    elif damage == "count":
        known["record_count"] = 3
    elif damage == "non-string-body":
        known["all_records_have_string_body"] = False
    elif damage == "fields":
        known["actual_union_fields"].append("text")
    elif damage == "missing":
        states["A4"]["artifacts"] = []
    else:
        historical["materialized_shapes"]["duplicate"] = copy.deepcopy(known)
    with pytest.raises(RuntimeError):
        review.reuse_shapes(task, states, historical, {"corpus"})


@pytest.mark.parametrize("damage", ["wire", "extra-finding", "worker-source", "exit",
                                  "evidence", "review", "historical", "parent"])
def test_sidecar_revalidation_rejects_actual_evidence_or_source_drift(heldout_field, damage):
    root, directory, ledger, parent, old, _, _, _ = heldout_field
    result = review.create_review("run4", parent, old)
    path = Path(result["sidecar_path"])
    if damage == "wire":
        (directory / "private/api/call1-request.json").write_text('{"messages":[]}')
    elif damage == "extra-finding":
        admission = json.loads((directory / "admission.json").read_text())
        admission["problems"].append("privacy_violation")
        (directory / "admission.json").write_text(json.dumps(admission))
    elif damage == "worker-source":
        (root / "app-input-cardinality-repair-003" / review.core.SOURCES[0]).write_text("drift")
    elif damage == "exit":
        (directory / "process-exit.json").write_text('{"returncode":1}')
    elif damage == "evidence":
        (directory / "extra.json").write_text("{}")
    elif damage == "historical":
        old.write_text("{}")
    elif damage == "parent":
        parent.write_text("{}")
    else:
        sidecar = json.loads(path.read_text())
        sidecar["replacement_authorized"] = True
        path.write_text(json.dumps(sidecar))
    with pytest.raises((RuntimeError, KeyError)):
        review.verify_sidecar(path, ledger.attempts[0])


def test_strict_live_guard_precedes_any_control_or_historical_read(heldout_field, monkeypatch):
    _, _, _, parent, old, _, _, _ = heldout_field

    def active(_):
        raise RuntimeError("live queue")

    monkeypatch.setattr(review.core.previous.gate.evidence.private, "assert_inactive", active)
    monkeypatch.setattr(review.core.previous, "checked_control",
                        lambda *_: pytest.fail("read while live"))
    with pytest.raises(RuntimeError, match="live queue"):
        review.create_review("run4", parent, old)


def test_historical_receipt_is_fully_reverified_not_trusted_by_hash_alone(
    heldout_field, monkeypatch,
):
    _, _, ledger, parent, old, _, _, _ = heldout_field

    def drift(*_):
        raise RuntimeError("historical full proof drift")

    monkeypatch.setattr(review.bindings, "verify_record", drift)
    with pytest.raises(RuntimeError, match="historical full proof drift"):
        review.create_review("run4", parent, old)
    assert ledger.attempts[0].disposition == "confounder"


def test_existing_model_json_reviews_and_raw_ledger_remain_separate(heldout_field):
    root, _, ledger, parent, old, _, _, _ = heldout_field
    review.create_review("run4", parent, old)
    path = root / review.core.DIRECTORY / "run4.json"
    path.parent.mkdir()
    path.write_text("{}")
    with pytest.raises((RuntimeError, KeyError)):
        _ = review.FieldReviewedAttemptLedger(ledger.path, ledger.cells,
                                              ledger.schedule_sha256).attempts


def test_model_json_and_field_review_sources_are_not_modified():
    assert review.core.__name__ == "large_scale_resident_phase2_reviewed_queue_v1"
    assert review.parent.__name__ == "large_scale_resident_phase2_read_once_v1"
    assert review.FieldReviewedAttemptLedger._check_reservation is (
        review.parent.ReadOnceAttemptLedger._check_reservation)
    assert review.core.previous.execute_cell.__module__ == "large_scale_resident_phase2_queue_v1"
