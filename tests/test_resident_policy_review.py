import importlib
import json
import sys
from pathlib import Path

import pytest

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import AttemptLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
reviewer = importlib.import_module("large_scale_resident_policy_review_v1")


@pytest.fixture
def policy_case(tmp_path):
    api = tmp_path / "api"
    api.mkdir()
    error = {"code": "data_inspection_failed", "type": "data_inspection_failed",
             "message": "Input text data may contain inappropriate content."}
    row = {"call_id": "call1", "status": 400, "recipient": "manager",
           "requested_model": "deepseek-v4-pro", "usage": None,
           "finished_utc": "2026-10-05T19:01:19Z"}
    (api / "call1-usage.json").write_text(json.dumps(row))
    (api / "call1-response.json").write_text(json.dumps({"error": error}))
    (api / "call1-request.json").write_text('{"content":"PRIVATE_INPUT"}')
    terminal = {"code": "control_plane_failed", "exception_type": "BadRequestError",
                "message": "HTTP400 data_inspection_failed"}
    original = {"disposition": "confounder", "reason": reviewer.TERMINAL_GATE,
                "problems": [reviewer.TERMINAL_GATE, reviewer.legacy.GATE],
                "api_audit": {"problems": [reviewer.legacy.GATE]},
                "operational_incidents": [], "execution_completed": False,
                "original_evaluation": None, "terminal_failure": terminal}
    events = [{"event_type": "run.failed", "payload": {"failure": terminal}}]
    return original, api, events


def test_exact_resident_policy_failure_preserves_missing_quality_and_usage(policy_case):
    original, api, events = policy_case
    before = json.dumps(original, sort_keys=True)
    actual = reviewer.review(original, api, events)
    assert json.dumps(original, sort_keys=True) == before
    assert actual["reviewed_admission"]["disposition"] == "valid"
    assert actual["reviewed_admission"]["original_evaluation"] is None
    assert not actual["reviewed_admission"]["execution_completed"]
    assert not actual["reviewed_admission"]["replacement_authorized"]
    assert actual["proof"][0]["failed_call_usage"] is None
    assert "PRIVATE_INPUT" not in json.dumps(actual)


@pytest.mark.parametrize("damage", ["privacy", "outage", "status", "error_code", "message",
    "request_missing", "terminal", "trace", "evaluated", "api_gate", "duplicate", "recipient",
    "later_call", "second_failure"])
def test_resident_policy_review_never_waives_unproven_findings(policy_case, damage):
    original, api, events = policy_case
    usage = api / "call1-usage.json"
    row = json.loads(usage.read_text())
    response = api / "call1-response.json"
    value = json.loads(response.read_text())
    if damage == "privacy":
        original["problems"].append("privacy_violation")
    elif damage == "outage":
        original["operational_incidents"].append("provider_outage")
    elif damage == "status":
        row["status"] = 503
    elif damage == "error_code":
        value["error"]["code"] = "backend_error"
    elif damage == "message":
        value["error"]["message"] = "unrelated"
    elif damage == "request_missing":
        (api / "call1-request.json").unlink()
    elif damage == "terminal":
        original["terminal_failure"]["exception_type"] = "RuntimeError"
    elif damage == "trace":
        events.clear()
    elif damage == "evaluated":
        original["original_evaluation"] = {"benchmark_score": 0}
    elif damage == "api_gate":
        original["api_audit"]["problems"].append("privacy_violation")
    elif damage == "duplicate":
        (api / "duplicate-usage.json").write_text(json.dumps(row))
    elif damage == "recipient":
        row["recipient"] = "verifier"
    elif damage == "later_call":
        (api / "later-usage.json").write_text(json.dumps({**row, "call_id": "later",
            "status": 200, "finished_utc": "2026-10-05T19:02:19Z"}))
    else:
        for suffix in ["usage", "request", "response"]:
            p = api / f"call1-{suffix}.json"
            v = json.loads(p.read_text())
            if suffix == "usage":
                v["call_id"] = "call2"
            (api / f"call2-{suffix}.json").write_text(json.dumps(v))
    usage.write_text(json.dumps(row))
    response.write_text(json.dumps(value))
    with pytest.raises(RuntimeError):
        reviewer.review(original, api, events)


@pytest.mark.parametrize("damage", [None, "evidence", "source", "review", "files"])
def test_resident_policy_ledger_preserves_history_and_verifies_exact_proof(
    policy_case, tmp_path, damage,
):
    original, api, events = policy_case
    directory = tmp_path / "evidence/cell/attempt1"
    run = directory / "runs/run"
    run.mkdir(parents=True)
    private = directory / "private"
    private.mkdir()
    api.rename(private / "api")
    api = private / "api"
    (directory / "admission.json").write_text(json.dumps(original))
    (run / "trace.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    ledger = AttemptLedger(tmp_path / "phase1-attempts.jsonl", ("cell",), "a" * 64)
    ledger.reserve("cell", "run", "b" * 64)
    ledger.settle("run", "confounder", reviewer.TERMINAL_GATE, provenance_sha256(original))
    attempt = ledger.attempts[0]
    review = reviewer.review(original, api, events)
    value = {"run_id": "run", "original_admission_sha256": attempt.receipt_sha256,
        "original_execution_sha256": attempt.execution_sha256,
        "reviewer_source_sha256": reviewer.legacy.sha256(Path(reviewer.__file__)),
        "legacy_reviewer_source_sha256": reviewer.legacy.sha256(Path(reviewer.legacy.__file__)),
        "original_evidence_file_sha256": {str(p.relative_to(directory)): reviewer.legacy.sha256(p)
                                         for p in directory.rglob("*") if p.is_file()},
        **review, "reviewed_admission_sha256": provenance_sha256(review["reviewed_admission"])}
    sidecar = tmp_path / reviewer.DIRECTORY / "run.json"
    sidecar.parent.mkdir()
    sidecar.write_text(json.dumps(value))
    before = ledger.path.read_bytes()
    if damage == "evidence":
        (api / "call1-request.json").write_text("changed")
    elif damage == "source":
        value["legacy_reviewer_source_sha256"] = "0" * 64
    elif damage == "review":
        value["reviewed_admission"]["original_evaluation"] = {"benchmark_score": 0}
    elif damage == "files":
        value["original_evidence_file_sha256"].pop("admission.json")
    sidecar.write_text(json.dumps(value))
    view = reviewer.ResidentPolicyAttemptLedger(ledger.path, ledger.cells, ledger.schedule_sha256)
    if damage:
        with pytest.raises(RuntimeError):
            _ = view.attempts
    else:
        assert view.completed_cells == ("cell",)
        assert view.original_attempts[0].disposition == "confounder"
        effective = reviewer.effective_admission(tmp_path, view.attempts[0])
        assert effective["original_evaluation"] is None
        with pytest.raises(RuntimeError, match="must not be repeated"):
            view.reserve("cell", "forbidden_retry", "b" * 64)
    assert before == ledger.path.read_bytes()
