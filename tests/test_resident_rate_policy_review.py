"""An operational429 is required; policy alone, billing and drift fail closed."""

from __future__ import annotations

import copy
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from infra_joint.control.provenance import provenance_sha256

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
review = importlib.import_module("large_scale_resident_rate_policy_review_v1")
queue = importlib.import_module("large_scale_resident_rate_policy_queue_v1")


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def source(tmp_path):
    api = tmp_path / "private/api"
    terminal = {"code": "logical_loop_failed", "exception_type": "AgentLoopError",
        "message": "Blind verifier failed: BadRequestError: Error code: 400 "
                   "data_inspection_failed: " + review.POLICY_MESSAGE}
    original = {"disposition": "confounder", "reason": review.GATE, "problems": [review.GATE],
        "operational_incidents": ["provider_outage"], "execution_completed": False,
        "original_evaluation": None, "terminal_failure": terminal,
        "api_audit": {"problems": [review.GATE], "operational_incidents": ["provider_outage"],
            "HTTP_calls": 4, "contexts": [{"call_id": c, "findings": []}
                                         for c in ("ok", "rate", "policy", "terminal")]}}
    for call, status, role, start in (("ok", 200, "manager", 0), ("rate", 429, "specialist", 1),
            ("policy", 400, "specialist", 2), ("terminal", 400, "verifier", 3)):
        model = "qwen3.8-max" if role == "verifier" else "deepseek-v4-pro"
        agent = "blind_evidence_verifier" if role == "verifier" else "bounded_specialist"
        usage = {"call_id": call, "scope_id": call, "status": status,
            "recipient": role, "agent_name": agent,
            "intended_model": model, "requested_model": model, "error_type": None, "usage": None,
            "started_utc": f"2026-10-06T15:00:0{start}+00:00",
            "finished_utc": f"2026-10-06T15:00:0{start + 1}+00:00", "latency_ms": 1000}
        request = {"model": model, "tools": [{"function": {"name": "submit_verification"}}]
                   if role == "verifier" else []}
        code = "insufficient_quota" if status == 429 else "data_inspection_failed"
        response = {"error": {"code": code, "type": code,
            "message": review.RATE_MESSAGE if status == 429 else review.POLICY_MESSAGE}}
        for suffix, value in (("usage", usage), ("request", request), ("response", response)):
            put(api / (call + "-" + suffix + ".json"), value)
        put(api / (call + "-model-attempt.json"), {"scope_id": call, "recipient": role,
            "agent_name": agent, "requested_model": model, "http_calls": 1,
            "error_type": "RateLimitError" if status == 429 else
                          "BadRequestError" if status == 400 else None})
    events = [{"event_type": "logical.subagent.end", "payload": {
        "logical_agent_id": "s1", "call_id": "tool1", "answer": "insufficient_quota"}},
        {"event_type": "logical.subagent.end", "payload": {
        "logical_agent_id": "s2", "call_id": "tool2", "answer": "data_inspection_failed"}},
        {"event_type": "logical.verification.input", "payload": {}},
        {"event_type": "logical.verification.failed", "payload": {}},
        {"event_type": "run.failed", "payload": {"failure": terminal}}]
    return api, original, events


def test_independent_rate_proof_excludes_comparison_without_hiding_policy(source):
    api, original, events = source
    before = copy.deepcopy(original)
    value = review.review(original, api, events)
    assert original == before
    admission = value["reviewed_admission"]
    assert admission["disposition"] == "operational_excluded"
    assert admission["immediate_terminal_failure"] == "provider_input_policy"
    assert admission["replacement_basis"] == "independently_proven_HTTP429_token_rate_limit"
    assert admission["max_operational_replacements"] == 1
    assert admission["identical_execution_required"] is True
    assert admission["policy_only_replacement_authorized"] is False
    assert admission["counterfactual_without_throttling"] is None
    assert admission["billing_failure_proven"] is False
    assert admission["original_evaluation"] is None
    assert admission["terminal_failure"] == before["terminal_failure"]
    assert sorted(p["http_status"] for p in value["mixed_provider_proof"]) == [400, 400, 429]
    assert len(value["specialist_failure_proof"]) == 2


@pytest.mark.parametrize("damage", ["policy_only", "billing", "type", "message", "privacy",
    "other_gate", "other_incident", "missing_request", "missing_response", "extra_file",
    "duplicate_id", "response500", "manager429", "wrong_model", "request_model", "usage",
    "error_type", "tool", "timing", "naive_time", "later_call", "missing_subagent_rate",
    "missing_subagent_policy", "duplicate_subagent", "missing_verifier_failed", "verified",
    "different_terminal", "missing_terminal", "evaluated", "completed", "missing_context",
    "count", "no_operational", "context_missing_findings", "scope", "sdk_retry",
    "sdk_exception", "sdk_model", "sdk_missing", "sdk_role", "sdk_identity"])
def test_all_other_findings_and_provider_failures_remain_blocked(source, damage):
    api, original, events = source
    if damage in {"policy_only", "billing", "type", "message"}:
        response = json.loads((api / "rate-response.json").read_text())
        if damage == "policy_only":
            usage = json.loads((api / "rate-usage.json").read_text())
            usage["status"] = 400
            put(api / "rate-usage.json", usage)
            response["error"] = {"code": "data_inspection_failed", "type": "data_inspection_failed",
                                  "message": review.POLICY_MESSAGE}
        elif damage == "billing":
            response["error"]["message"] = "Your credits are depleted. Please top up."
        elif damage == "type":
            response["error"]["type"] = "different_quota"
        else:
            response["error"]["message"] += " extra"
        put(api / "rate-response.json", response)
    elif damage in {"privacy", "other_gate", "other_incident", "evaluated", "completed",
                    "count", "no_operational", "missing_context", "context_missing_findings"}:
        if damage == "privacy":
            original["api_audit"]["contexts"][0]["findings"] = ["private_leak"]
        elif damage == "other_gate":
            original["problems"].append("artifact_missing")
        elif damage == "other_incident":
            original["operational_incidents"].append("tc_cleanup_failed")
        elif damage == "evaluated":
            original["original_evaluation"] = {"score": 0}
        elif damage == "completed":
            original["execution_completed"] = True
        elif damage == "count":
            original["api_audit"]["HTTP_calls"] = 5
        elif damage == "no_operational":
            original["operational_incidents"] = []
        elif damage == "missing_context":
            original["api_audit"]["contexts"].pop()
        else:
            del original["api_audit"]["contexts"][0]["findings"]
    elif damage == "scope":
        usage = json.loads((api / "rate-usage.json").read_text())
        usage["scope_id"] = "ok"
        put(api / "rate-usage.json", usage)
    elif damage.startswith("sdk_"):
        path = api / "rate-model-attempt.json"
        invocation = json.loads(path.read_text())
        if damage == "sdk_missing":
            path.unlink()
        else:
            key, value = {"sdk_retry": ("http_calls", 2), "sdk_exception": ("error_type", None),
                "sdk_model": ("requested_model", "other-model"),
                "sdk_role": ("recipient", "manager"), "sdk_identity": ("scope_id", "other")}[damage]
            invocation[key] = value
            put(path, invocation)
    elif damage in {"missing_request", "missing_response"}:
        (api / ("rate-" + damage.removeprefix("missing_") + ".json")).unlink()
    elif damage == "extra_file":
        put(api / "hidden-response.json", {})
    elif damage in {"duplicate_id", "response500", "manager429", "wrong_model", "usage",
                    "error_type", "timing", "naive_time", "later_call"}:
        usage = json.loads((api / "rate-usage.json").read_text())
        if damage == "duplicate_id":
            usage["call_id"] = "ok"
        elif damage == "response500":
            usage["status"] = 500
        elif damage == "manager429":
            usage["recipient"] = "manager"
        elif damage == "wrong_model":
            usage["intended_model"] = "other-model"
        elif damage == "usage":
            usage["usage"] = {"input_tokens": 0}
        elif damage == "error_type":
            usage["error_type"] = "APITimeoutError"
        elif damage == "timing":
            usage["latency_ms"] = 60000
        elif damage == "naive_time":
            usage["started_utc"] = "2026-10-06T15:00:01"
        else:
            usage["started_utc"] = "2026-10-06T15:00:10+00:00"
            usage["finished_utc"] = "2026-10-06T15:00:11+00:00"
        put(api / "rate-usage.json", usage)
    elif damage in {"request_model", "tool"}:
        request = json.loads((api / "terminal-request.json").read_text())
        if damage == "request_model":
            request["model"] = "other-model"
        else:
            request["tools"] = []
        put(api / "terminal-request.json", request)
    elif damage == "missing_subagent_rate":
        events.pop(0)
    elif damage == "missing_subagent_policy":
        events.pop(1)
    elif damage == "duplicate_subagent":
        events.insert(0, copy.deepcopy(events[0]))
    elif damage == "missing_verifier_failed":
        events.pop(-2)
    elif damage == "verified":
        events.insert(-1, {"event_type": "logical.verification", "payload": {}})
    elif damage == "different_terminal":
        events[-1]["payload"]["failure"] = {"code": "runtime_failure"}
    else:
        events.pop()
    with pytest.raises(RuntimeError):
        review.review(original, api, events)


def test_sidecar_rehashes_original_sources_and_actual_requests(source, monkeypatch, tmp_path):
    api, original, events = source
    root = tmp_path / "owned"
    cell, run = "cell", "run"
    directory = root / "evidence" / cell / "attempt1"
    destination = directory / "private/api"
    destination.mkdir(parents=True)
    for file in api.glob("*.json"):
        (destination / file.name).write_bytes(file.read_bytes())
    put(directory / "admission.json", original)
    trace = directory / "runs" / run / "trace.jsonl"
    trace.parent.mkdir(parents=True)
    trace.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    attempt = SimpleNamespace(cell_id=cell, attempt_index=1, run_id=run,
        disposition="confounder", reason=review.GATE, receipt_sha256=provenance_sha256(original),
        execution_sha256="a" * 64)
    monkeypatch.setattr(review.methods, "frozen_sources", lambda *_: {"immutable.py": "b" * 64})
    value = {"run_id": run, "original_admission_sha256": attempt.receipt_sha256,
        "original_execution_sha256": attempt.execution_sha256,
        "reviewer_source_sha256": review.sha256(Path(review.__file__)),
        "previous_reviewer_source_sha256": review.sha256(Path(review.previous.__file__)),
        "execution_sources_sha256": {"immutable.py": "b" * 64},
        "original_evidence_file_sha256": review.methods.evidence_files(directory),
        **review.review(original, destination, events)}
    value["reviewed_admission_sha256"] = provenance_sha256(value["reviewed_admission"])
    path = root / review.RATE_DIRECTORY / (run + ".json")
    put(path, value)
    assert review.verify_sidecar(path, attempt) == value
    (destination / "rate-response.json").write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="drift"):
        review.verify_sidecar(path, attempt)


def test_copied_external_control_preserves_launch_and_global_namespace(monkeypatch, tmp_path):
    seen = []

    def original(path):
        seen.append((owned_ledger(), control_freeze(), path))  # noqa: F821

    monkeypatch.setattr(queue.previous.previous.previous, "run", original)
    monkeypatch.setattr(queue, "owned_ledger", lambda: "mixed operational ledger")
    monkeypatch.setattr(queue, "control_freeze", lambda: "new external scope")
    before = dict(original.__globals__)
    path = tmp_path / "queue-control-freeze-023.json"
    queue.run(path)
    assert seen == [("mixed operational ledger", "new external scope", path)]
    assert original.__globals__ == before


@pytest.fixture
def scope(tmp_path, monkeypatch):
    parent = {"compound_record_policy_adjudications": {"historical.json": "a" * 64},
        "native_argument_adjudications": {"sdk.json": "b" * 64},
        "execution_sha256": "c" * 64, "atomic_execution_entrypoint": "/immutable/atomic.py"}
    control = tmp_path / queue.PARENT_FILE
    put(control, parent)
    stopped = tmp_path / queue.STOPPED_FILE
    put(stopped, {"original_scope": "preserved"})
    path = tmp_path / review.RATE_DIRECTORY / "mixed.json"
    put(path, {})
    raw = SimpleNamespace(run_id="mixed", disposition="confounder", reason=review.GATE)
    effective = SimpleNamespace(run_id="mixed", disposition="operational_excluded",
                                reason=review.REASON)
    ledger = SimpleNamespace(original_attempts=(raw,), attempts=(effective,))
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(queue, "PARENT_SHA256", queue.frozen.sha256(control))
    monkeypatch.setattr(queue, "STOPPED_SHA256", queue.frozen.sha256(stopped))
    monkeypatch.setattr(queue.previous, "control_freeze", lambda: parent)
    monkeypatch.setattr(queue, "owned_ledger", lambda: ledger)
    calls = []
    monkeypatch.setattr(review, "verify_sidecar", lambda p, a: calls.append((p.name, a.run_id)))
    return SimpleNamespace(parent=parent, path=path, control=control, ledger=ledger, calls=calls)


def test_frozen_parent_scope_and_execution_survive_operational_projection(scope):
    before = scope.control.read_bytes()
    value = queue.control_freeze()
    assert value["execution_sha256"] == scope.parent["execution_sha256"]
    assert value["compound_record_policy_adjudications"] == (
        scope.parent["compound_record_policy_adjudications"])
    assert value["native_argument_adjudications"] == scope.parent["native_argument_adjudications"]
    assert value["mixed_token_rate_policy_adjudications"] == {
        "mixed.json": queue.frozen.sha256(scope.path)}
    assert value["policy_only_replacement_authorized"] is False
    assert value["max_operational_replacements_per_cell"] == 1
    assert value["API_concurrency_changed"] is False
    assert value["quota_or_billing_configuration_changed"] is False
    assert value["measured_execution_changed"] is False
    assert scope.calls == [("mixed.json", "mixed")]
    assert scope.control.read_bytes() == before


@pytest.mark.parametrize("damage", ["parent", "stopped", "scope", "unknown", "missing_raw",
                                   "pending", "nominal", "reason", "no_proof", "invalid_proof"])
def test_external_scope_cannot_admit_unproved_or_nominal_failures(scope, monkeypatch, damage):
    if damage == "parent":
        scope.control.write_text("{}", encoding="utf-8")
    elif damage == "stopped":
        (scope.control.parent / queue.STOPPED_FILE).write_text("{}", encoding="utf-8")
    elif damage == "scope":
        monkeypatch.setattr(queue.previous, "control_freeze", lambda: {})
    elif damage == "unknown":
        put(scope.path.parent / "unknown.json", {})
    elif damage == "missing_raw":
        scope.ledger.original_attempts = ()
    elif damage == "pending":
        scope.ledger.attempts[0].disposition = None
    elif damage == "nominal":
        scope.ledger.attempts[0].disposition = "valid"
    elif damage == "reason":
        scope.ledger.attempts[0].reason = "provider_input_policy"
    elif damage == "no_proof":
        scope.path.unlink()
    else:
        def reject(*_):
            raise RuntimeError("unproved actual API failure")

        monkeypatch.setattr(review, "verify_sidecar", reject)
    with pytest.raises(RuntimeError):
        queue.control_freeze()


def test_parent_replay_uses_current_ledger_without_mutating_historical_checks(monkeypatch):
    seen = []
    ledger = SimpleNamespace(attempts=("nominal", "operational429", "identical replacement"))

    def native():
        seen.append(("native", owned_ledger()))  # noqa: F821
        return {"original_native_scope": True}

    def compound():
        seen.append(("compound", owned_ledger()))  # noqa: F821
        return {**previous.control_freeze(), "original_compound_scope": True}  # noqa: F821

    monkeypatch.setattr(queue.previous.previous, "control_freeze", native)
    monkeypatch.setattr(queue.previous, "control_freeze", compound)
    monkeypatch.setattr(queue.previous.previous, "owned_ledger",
                        lambda: pytest.fail("old view cannot replay new429replacement"))
    monkeypatch.setattr(queue.previous, "owned_ledger",
                        lambda: pytest.fail("old view cannot replay new429replacement"))
    before_native, before_compound = dict(native.__globals__), dict(compound.__globals__)
    assert queue.historical_parent(ledger) == {
        "original_native_scope": True, "original_compound_scope": True}
    assert seen == [("compound", ledger), ("native", ledger)]
    assert native.__globals__ == before_native and compound.__globals__ == before_compound
