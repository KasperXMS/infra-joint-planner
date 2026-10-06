"""Malformed raw native arguments are composition failure, not an outage waiver."""

from __future__ import annotations

import copy
import importlib
import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from infra_joint.control.provenance import provenance_sha256

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
review = importlib.import_module("large_scale_resident_sdk_argument_review_v1")
queue = importlib.import_module("large_scale_resident_sdk_argument_queue_v1")
snapshot = importlib.import_module("large_scale_resident_launch_snapshot_v2")


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def source(tmp_path):
    api = tmp_path / "private/api"
    args = '{"logical_agent_id": not_json}'
    try:
        review.SpecialistRequest.model_validate_json(args)
    except ValidationError as error:
        message = "Error running tool consult_specialist: " + str(error)
    terminal = {"code": "control_plane_failed", "exception_type": "UserError", "message": message}
    original = {"disposition": "confounder", "reason": review.GATE, "problems": [review.GATE],
                "operational_incidents": [], "execution_completed": False,
                "original_evaluation": None, "api_audit": {"problems": []},
                "terminal_failure": terminal}
    usage = {"call_id": "last", "recipient": "manager", "status": 200,
             "finished_utc": "2026-10-06T13:00:00+00:00"}
    request = {"tools": [{"function": {"name": "consult_specialist", "parameters":
        review.ensure_strict_json_schema(review.SpecialistRequest.model_json_schema())}}]}
    response = {"choices": [{"finish_reason": "tool_calls", "message": {"tool_calls": [
        {"id": "bad1", "function": {"name": "consult_specialist", "arguments": args}},
        {"id": "bad2", "function": {"name": "consult_specialist", "arguments": args}}]}}]}
    events = [{"event_type": "run.failed", "payload": {"failure": terminal}}]
    for name, value in (("usage", usage), ("request", request), ("response", response)):
        put(api / ("last-" + name + ".json"), value)
    return api, original, events, request, response


def test_raw_json_failure_retained_without_evaluation_imputation_or_replacement(source):
    api, original, events, *_ = source
    before = copy.deepcopy(original)
    value = review.review(original, api, events)
    assert original == before
    assert len(value["native_argument_proof"]) == 2
    admission = value["reviewed_admission"]
    assert admission["disposition"] == "valid" and not admission["problems"]
    assert admission["execution_completed"] is False and admission["original_evaluation"] is None
    assert admission["replacement_authorized"] is False
    assert admission["terminal_failure"] == original["terminal_failure"]


@pytest.mark.parametrize("damage", ["other_issue", "privacy", "outage", "evaluated",
    "different_exception", "message", "schema", "valid_json", "other_tool", "empty",
    "duplicate", "truncation", "later_call", "different_terminal", "missing_terminal"])
def test_proof_does_not_waive_other_model_system_or_provider_failures(source, damage):
    api, original, events, request, response = source
    if damage == "other_issue":
        original["problems"].append("artifact_missing")
    elif damage == "privacy":
        original["api_audit"]["problems"].append("private_leak")
    elif damage == "outage":
        usage = json.loads((api / "last-usage.json").read_text())
        usage["status"] = 503
        put(api / "last-usage.json", usage)
    elif damage == "evaluated":
        original["original_evaluation"] = {"benchmark_score": 0}
    elif damage == "different_exception":
        original["terminal_failure"]["exception_type"] = "RuntimeError"
    elif damage == "message":
        original["terminal_failure"]["message"] = "a runtime problem"
    elif damage == "schema":
        request["tools"][0]["function"]["parameters"] = {}
    elif damage == "valid_json":
        response["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = '{}'
    elif damage == "other_tool":
        response["choices"][0]["message"]["tool_calls"][0]["function"]["name"] = 'new_tool'
    elif damage == "empty":
        response["choices"][0]["message"]["tool_calls"] = []
    elif damage == "duplicate":
        response["choices"][0]["message"]["tool_calls"][1]["id"] = "bad1"
    elif damage == "truncation":
        response["choices"][0]["finish_reason"] = "length"
    elif damage == "later_call":
        put(api / "later-usage.json", {"call_id": "later", "recipient": "verifier",
             "status": 200, "finished_utc": "2026-10-06T13:00:01+00:00"})
    elif damage == "different_terminal":
        events[0]["payload"]["failure"] = {"code": "another_failure"}
    else:
        events.clear()
    put(api / "last-request.json", request)
    put(api / "last-response.json", response)
    with pytest.raises(RuntimeError):
        review.review(original, api, events)


def test_ledger_projection_preserves_raw_settlement_and_prohibits_repeat(source, monkeypatch):
    api, original, events, _, _ = source
    root = api.parents[1]
    ledger = review.ProjectionAttemptLedger(root / "journal.jsonl", ("one", "two"), "a" * 64)
    run = "ordinary-bad-model-json"
    ledger.reserve("one", run, "b" * 64)
    ledger.settle(run, "confounder", review.GATE, provenance_sha256(original))
    raw = ledger.original_attempts
    put(root / review.SEMANTIC_DIRECTORY / (run + ".json"), {})
    reviewed = review.review(original, api, events)
    proof = {**reviewed, "reviewed_admission_sha256": provenance_sha256(
        reviewed["reviewed_admission"])}
    monkeypatch.setattr(review, "verify_sidecar", lambda *_: proof)
    assert ledger.original_attempts == raw and raw[0].disposition == "confounder"
    assert ledger.completed_cells == ("one",)
    with pytest.raises(RuntimeError, match="valid nominal"):
        ledger.reserve("one", "forbidden-retry", "b" * 64)
    ledger.reserve("two", "next-original-cell", "b" * 64)


def test_control_dependency_injection_never_mutates_historical_globals(monkeypatch, tmp_path):
    def original(path):
        return owned_ledger(), control_freeze(), path  # noqa: F821

    monkeypatch.setattr(queue.previous, "run", original)
    monkeypatch.setattr(queue, "owned_ledger", lambda: "verified-current-view")
    monkeypatch.setattr(queue, "control_freeze", lambda: "verified-current-control")
    before = dict(original.__globals__)
    queue.run(tmp_path / "control.json")
    assert original.__globals__ == before


def test_projection_source_identity_does_not_depend_on_unrelated_imports(monkeypatch):
    from types import ModuleType

    before = snapshot.source_bindings()
    unrelated = ModuleType("large_scale_unused_gate")
    unrelated.__file__ = "must-not-be-opened.py"
    monkeypatch.setitem(sys.modules, unrelated.__name__, unrelated)
    assert snapshot.source_bindings() == before
    assert "large_scale_resident_sdk_argument_review_v1.py" in before
    assert "large_scale_resident_launch_review_v1.py" in before
    assert "large_scale_resident_current_phase2_queue_v1.py" not in before


def test_current_projection_uses_new_view_without_mutating_old_collector(monkeypatch, tmp_path):
    journal = tmp_path / "phase1-attempts.jsonl"
    journal.write_text("unchanged\n")
    sha = snapshot.resident.sha256(journal)
    calls = []

    def historical_collect(root, predecessor):
        calls.append((reviewer.ProjectionAttemptLedger, root, predecessor))  # noqa: F821
        return {"rows": [], "journal_sha256": sha, "collector_source_sha256": {}}

    monkeypatch.setattr(snapshot.previous, "collect", historical_collect)
    before = dict(historical_collect.__globals__)
    value = snapshot.collect(tmp_path, tmp_path / "predecessor")
    assert calls == [(review.ProjectionAttemptLedger, tmp_path, tmp_path / "predecessor")]
    assert historical_collect.__globals__ == before
    assert value["collector_source_sha256"] == snapshot.source_bindings()
    assert journal.read_text() == "unchanged\n"
