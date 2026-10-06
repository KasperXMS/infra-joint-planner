"""All compound findings need independent unchanged validators; never retry policy."""

from __future__ import annotations

import copy
import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from test_resident_record_review import field_case as field_case
from test_resident_timeout_review import api_case

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import AttemptLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
reviewer = importlib.import_module("large_scale_resident_field_policy_review_v1")


def policy_case(api: Path, original: dict[str, Any], events: list[dict[str, Any]]) -> None:
    api_case(api, original, events)
    original["terminal_failure"]["message"] = (
        "Blind verifier failed: BadRequestError: Error code: 400 - data_inspection_failed")
    error = {"code": "data_inspection_failed", "type": "data_inspection_failed",
             "message": "Input text data may contain inappropriate content."}
    path = api / "deadline-usage.json"
    usage = json.loads(path.read_text())
    usage.update(status=400, error_type=None)
    path.write_text(json.dumps(usage))
    (api / "deadline-response.json").write_text(json.dumps({"error": error}))
    extra = {**usage, "call_id": "specialist", "recipient": "specialist",
             "requested_model": "deepseek-v4-pro", "finished_utc": "2026-10-06T08:00:02+00:00"}
    (api / "specialist-usage.json").write_text(json.dumps(extra))
    (api / "specialist-request.json").write_text('{"model":"deepseek-v4-pro"}')
    (api / "specialist-response.json").write_text(json.dumps({"error": error}))
    events.append({"event_type": "run.failed", "payload": {
        "failure": copy.deepcopy(original["terminal_failure"])}})


def test_record_and_policy_proofs_preserve_original_failed_sample_without_retry(
    field_case: tuple, tmp_path: Path,
) -> None:
    original, events, shapes = field_case
    api = tmp_path / "api"
    policy_case(api, original, events)
    before = copy.deepcopy((original, events, shapes))
    with pytest.raises(RuntimeError):
        reviewer.records.review(original, events, shapes)
    with pytest.raises(RuntimeError):
        reviewer.policy.review_policy(original, api)
    value = reviewer.review(original, events, shapes, api)
    assert (original, events, shapes) == before
    assert value["reviewed_admission"]["disposition"] == "valid"
    assert value["reviewed_admission"]["original_evaluation"] is None
    assert value["reviewed_admission"]["replacement_authorized"] is False
    assert len(value["record_field_proof"]) == 1
    assert len(value["provider_policy_proof"]) == 2
    assert "private-worker" not in json.dumps(value)
    assert value["record_field_proof"][0]["specialist_received_artifact_schema"] is None


@pytest.mark.parametrize("damage", ["field_only", "policy_only", "privacy", "operational",
    "evaluated", "completed", "timeout", "backend_error", "quota", "different_policy",
    "missing_response", "manager_refusal", "model", "later_call", "duplicate_call",
    "no_run_end", "extra_run_end", "terminal_mismatch", "unreturned_verification",
    "field_exists", "producer", "failed_selection"])
def test_unproven_compound_findings_never_enter_nominal_membership(
    field_case: tuple, tmp_path: Path, damage: str,
) -> None:
    original, events, shapes = field_case
    api = tmp_path / "api"
    policy_case(api, original, events)
    usage_path = api / "deadline-usage.json"
    usage = json.loads(usage_path.read_text())
    if damage == "field_only":
        original["problems"] = [reviewer.records.GATE_PROBLEM]
    elif damage == "policy_only":
        original["problems"] = [reviewer.policy.GATE]
    elif damage == "privacy":
        original["problems"].append("privacy")
    elif damage == "operational":
        original["operational_incidents"].append("provider_outage")
    elif damage == "evaluated":
        original["original_evaluation"] = {"benchmark_score": 0}
    elif damage == "completed":
        original["execution_completed"] = True
    elif damage == "timeout":
        usage.update(status=None, error_type="APITimeoutError")
    elif damage in {"backend_error", "quota"}:
        usage["status"] = 503 if damage == "backend_error" else 429
    elif damage == "different_policy":
        (api / "deadline-response.json").write_text('{"error":{"code":"something_else"}}')
    elif damage == "missing_response":
        (api / "deadline-response.json").unlink()
    elif damage == "manager_refusal":
        usage["recipient"] = "manager"
    elif damage == "model":
        usage["requested_model"] = "different"
    elif damage == "later_call":
        p = api / "success-usage.json"
        v = json.loads(p.read_text())
        v["finished_utc"] = "2026-10-06T08:05:00+00:00"
        p.write_text(json.dumps(v))
    elif damage == "duplicate_call":
        (api / "other-usage.json").write_text(json.dumps(usage))
    elif damage == "no_run_end":
        events.pop()
    elif damage == "extra_run_end":
        events.append(copy.deepcopy(events[-1]))
    elif damage == "terminal_mismatch":
        events[-1]["payload"]["failure"]["message"] = "budget"
    elif damage == "unreturned_verification":
        events.append({"event_type": "logical.verification", "payload": {}})
    elif damage == "field_exists":
        shapes["merged"]["actual_union_fields"].append("text")
    elif damage == "producer":
        events[3]["payload"]["action"]["operator"] = "unknown"
    else:
        events[7]["payload"]["failure"]["stage"] = "selection"
    usage_path.write_text(json.dumps(usage))
    with pytest.raises(RuntimeError):
        reviewer.review(original, events, shapes, api)


@pytest.mark.parametrize("damage", [None, "source", "evidence", "replica", "proof", "reviewer"])
def test_source_bound_policy_ledger_retains_unknown_quality_and_blocks_repeat(
    field_case: tuple, tmp_path: Path, damage: str | None,
) -> None:
    original, events, shapes = field_case
    directory = tmp_path / "evidence/cell/attempt1"
    run = directory / "runs/run"
    run.mkdir(parents=True)
    api = directory / "private/api"
    policy_case(api, original, events)
    shapes["merged"].update(size_bytes=100, media_type="application/json")
    (directory / "admission.json").write_text(json.dumps(original))
    trace = run / "trace.jsonl"
    trace.write_text("".join(json.dumps(e) + "\n" for e in events))
    metadata = {k: shapes["merged"][k] for k in (
        "artifact_id", "media_type", "size_bytes", "sha256_hex")}
    state = directory / "private/worker-state-after.json"
    state.write_text(json.dumps({"A28": {"artifacts": [metadata]}}))
    app = tmp_path / reviewer.methods.APPS[3]
    for relative in reviewer.previous.SOURCE_PATHS:
        p = app / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("immutable source")
    sources = {p: reviewer.sha256(app / p) for p in reviewer.previous.SOURCE_PATHS}
    freeze = {"source_sha256": sources}
    (tmp_path / "execution-freeze-004.json").write_text(json.dumps(freeze))
    execution = provenance_sha256(freeze)
    ledger = AttemptLedger(tmp_path / "phase1-attempts.jsonl", ("cell", "next"), "a" * 64)
    ledger.reserve("cell", "run", execution)
    ledger.settle("run", "confounder", reviewer.records.GATE_PROBLEM, provenance_sha256(original))
    attempt = ledger.attempts[0]
    value = {"run_id": "run", "original_admission_sha256": attempt.receipt_sha256,
             "original_execution_sha256": attempt.execution_sha256,
             "reviewer_source_sha256": reviewer.sha256(Path(reviewer.__file__)),
             "timeout_reviewer_source_sha256": reviewer.sha256(Path(reviewer.previous.__file__)),
             "method_reviewer_source_sha256": reviewer.sha256(Path(reviewer.methods.__file__)),
             "record_reviewer_source_sha256": reviewer.sha256(Path(reviewer.records.__file__)),
             "policy_reviewer_source_sha256": reviewer.sha256(Path(reviewer.policy.__file__)),
             "execution_sources_sha256": sources, "materialized_shapes": shapes,
             "original_evidence_file_sha256": reviewer.methods.evidence_files(directory),
             **reviewer.review(original, events, shapes, api)}
    value["reviewed_admission_sha256"] = provenance_sha256(value["reviewed_admission"])
    sidecar = tmp_path / reviewer.POLICY_DIRECTORY / "run.json"
    sidecar.parent.mkdir()
    sidecar.write_text(json.dumps(value))
    before = ledger.path.read_bytes()
    if damage == "source":
        (app / reviewer.previous.SOURCE_PATHS[0]).write_text("drift")
    elif damage == "evidence":
        trace.write_text("drift")
    elif damage == "replica":
        state.write_text('{"A28":{"artifacts":[]}}')
    elif damage == "proof":
        value["record_field_proof"] = []
        sidecar.write_text(json.dumps(value))
    elif damage == "reviewer":
        value["policy_reviewer_source_sha256"] = "b" * 64
        sidecar.write_text(json.dumps(value))
    view = reviewer.ProjectionAttemptLedger(ledger.path, ledger.cells, ledger.schedule_sha256)
    if damage:
        with pytest.raises(RuntimeError):
            _ = view.attempts
    else:
        assert view.completed_cells == ("cell",)
        assert view.original_attempts[0].disposition == "confounder"
        admission = reviewer.effective_admission(tmp_path, view.attempts[0])
        assert admission["original_evaluation"] is None
        with pytest.raises(RuntimeError, match="must not be repeated"):
            view.reserve("cell", "retry", execution)
    assert ledger.path.read_bytes() == before
    if damage is None:
        view.reserve("next", "later", execution)
        view.settle("later", "valid", "ordinary_outcome", "c" * 64)
        with pytest.raises(RuntimeError, match="unresolved system confounder"):
            reviewer.previous.ProjectionAttemptLedger(
                ledger.path, ledger.cells, ledger.schedule_sha256)
        assert reviewer.ProjectionAttemptLedger(
            ledger.path, ledger.cells, ledger.schedule_sha256).completed_cells == ("cell", "next")
