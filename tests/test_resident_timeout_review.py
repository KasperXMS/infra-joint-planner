"""Compound proof is not a semantic retry or a generic timeout allowlist."""

from __future__ import annotations

import copy
import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from test_resident_record_review import field_case as field_case

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import AttemptLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
reviewer = importlib.import_module("large_scale_resident_timeout_review_v1")


def api_case(api: Path, original: dict[str, Any], events: list[dict[str, Any]]) -> None:
    api.mkdir(parents=True)
    original.update(reason=reviewer.previous.records.GATE_PROBLEM,
                    problems=[reviewer.previous.records.GATE_PROBLEM, reviewer.API_GATE],
                    execution_completed=False, original_evaluation=None,
                    terminal_failure={"code": "logical_loop_failed",
                        "exception_type": "AgentLoopError", "message":
                        "Blind verifier failed: APITimeoutError: Request timed out."})
    for event in ("logical.verification.input", "logical.verification",
                  "logical.verification.input"):
        events.append({"event_type": event, "payload": {}})
    for call, status in (("success", 200), ("deadline", None)):
        usage = {"call_id": call, "recipient": "verifier", "agent_name": "blind_evidence_verifier",
                 "intended_model": "qwen3.8-max", "requested_model": "qwen3.8-max",
                 "status": status, "error_type": None if status else "APITimeoutError",
                 "response_model": "qwen3.8-max" if status else None,
                 "request_id": "served" if status else None, "usage": {} if status else None,
                 "latency_ms": 180_400 if status is None else 1000,
                 "started_utc": "2026-10-06T08:00:00+00:00",
                 "finished_utc": "2026-10-06T08:03:00.400000+00:00" if status is None
                 else "2026-10-06T08:00:01+00:00"}
        (api / (call + "-usage.json")).write_text(json.dumps(usage))
        (api / (call + "-request.json")).write_text(json.dumps({"model": "qwen3.8-max",
            "tools": [{"function": {"name": "submit_verification"}}]}))
        (api / (call + "-response.json")).write_text(json.dumps({} if status else None))


def test_both_proofs_preserve_raw_and_only_allow_identical_operational_replacement(
    field_case: tuple, tmp_path: Path,
) -> None:
    original, events, shapes = field_case
    api = tmp_path / "api"
    api_case(api, original, events)
    before = copy.deepcopy((original, events, shapes))
    with pytest.raises(RuntimeError):
        reviewer.previous.records.review(original, events, shapes)
    value = reviewer.review(original, events, shapes, api)
    assert (original, events, shapes) == before
    admission = value["reviewed_admission"]
    assert admission["disposition"] == "operational_excluded"
    assert admission["original_evaluation"] is None
    assert admission["identical_execution_required"] is True
    assert admission["max_operational_replacements"] == 1
    assert value["timeout_proof"]["provider_wide_outage_proven"] is False
    assert value["timeout_proof"]["timeout_origin"] is None
    assert "private-worker" not in json.dumps(value)
    assert value["record_field_proof"][0]["specialist_received_artifact_schema"] is None


@pytest.mark.parametrize("damage", ["field_only", "timeout_only", "privacy", "evaluated",
    "completed", "budget", "modelerror", "HTTP400", "HTTP503", "connection", "readtimeout",
    "fast_exception", "usage", "response", "missing_response", "model", "recipient", "tool",
    "duplicate_failure", "unreturned_trace", "unmatched_trace", "interval", "later_success",
    "unknown_field", "wrong_stage", "schema"])
def test_unproven_findings_do_not_authorize_any_replacement(
    field_case: tuple, tmp_path: Path, damage: str,
) -> None:
    original, events, shapes = field_case
    api = tmp_path / "api"
    api_case(api, original, events)
    path = api / "deadline-usage.json"
    usage = json.loads(path.read_text())
    if damage == "field_only":
        original["problems"] = [reviewer.previous.records.GATE_PROBLEM]
    elif damage == "timeout_only":
        original["problems"] = [reviewer.API_GATE]
    elif damage == "privacy":
        original["problems"].append("privacy")
    elif damage == "evaluated":
        original["original_evaluation"] = {"benchmark_score": 0}
    elif damage == "completed":
        original["execution_completed"] = True
    elif damage == "budget":
        original["terminal_failure"]["message"] = "budget exhausted"
    elif damage == "modelerror":
        original["terminal_failure"]["exception_type"] = "ModelBehaviorError"
    elif damage in {"HTTP400", "HTTP503"}:
        usage["status"] = int(damage[4:])
    elif damage in {"connection", "readtimeout"}:
        usage["error_type"] = "APIConnectionError" if damage == "connection" else "ReadTimeout"
    elif damage == "fast_exception":
        usage["latency_ms"] = 100
    elif damage == "usage":
        usage["usage"] = {"input_tokens": 123}
    elif damage == "response":
        (api / "deadline-response.json").write_text('{"error":"actual HTTP response"}')
    elif damage == "missing_response":
        (api / "deadline-response.json").unlink()
    elif damage == "model":
        usage["requested_model"] = "different"
    elif damage == "recipient":
        usage["recipient"] = "specialist"
    elif damage == "tool":
        (api / "deadline-request.json").write_text('{"model":"qwen3.8-max","tools":[]}')
    elif damage == "duplicate_failure":
        (api / "other-usage.json").write_text(json.dumps(usage))
    elif damage == "unreturned_trace":
        events.pop()
    elif damage == "unmatched_trace":
        events.append({"event_type": "logical.verification", "payload": {}})
    elif damage == "interval":
        usage["finished_utc"] = "2026-10-06T08:01:00+00:00"
    elif damage == "later_success":
        p = api / "success-usage.json"
        v = json.loads(p.read_text())
        v["finished_utc"] = "2026-10-06T08:04:00+00:00"
        p.write_text(json.dumps(v))
    elif damage == "unknown_field":
        shapes["merged"]["actual_union_fields"].append("text")
    elif damage == "wrong_stage":
        events[-4]["payload"]["failure"]["stage"] = "transfer"
    else:
        events[0]["payload"]["input_items"][0]["content"] = '{"task":{"artifacts":[]}}'
    path.write_text(json.dumps(usage))
    with pytest.raises(RuntimeError):
        reviewer.review(original, events, shapes, api)


@pytest.mark.parametrize("damage", [None, "source", "evidence", "replica", "proof", "reviewer"])
def test_timeout_ledger_replays_exact_sources_and_caps_replacement(
    field_case: tuple, tmp_path: Path, damage: str | None,
) -> None:
    original, events, shapes = field_case
    directory = tmp_path / "evidence/cell/attempt1"
    run = directory / "runs/run"
    run.mkdir(parents=True)
    api = directory / "private/api"
    api_case(api, original, events)
    shapes["merged"].update(size_bytes=100, media_type="application/json")
    (directory / "admission.json").write_text(json.dumps(original))
    (run / "trace.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    metadata = {k: shapes["merged"][k] for k in (
        "artifact_id", "media_type", "size_bytes", "sha256_hex")}
    state = directory / "private/worker-state-after.json"
    state.write_text(json.dumps({"A28": {"artifacts": [metadata]}}))
    app = tmp_path / reviewer.previous.previous.APPS[3]
    for relative in reviewer.SOURCE_PATHS:
        p = app / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("immutable source")
    sources = {p: reviewer.previous.sha256(app / p) for p in reviewer.SOURCE_PATHS}
    freeze = {"source_sha256": sources}
    (tmp_path / "execution-freeze-004.json").write_text(json.dumps(freeze))
    execution = provenance_sha256(freeze)
    ledger = AttemptLedger(tmp_path / "phase1-attempts.jsonl", ("cell", "next"), "a" * 64)
    ledger.reserve("cell", "run", execution)
    ledger.settle("run", "confounder", reviewer.previous.records.GATE_PROBLEM,
                  provenance_sha256(original))
    attempt = ledger.attempts[0]
    value = {"run_id": "run", "original_admission_sha256": attempt.receipt_sha256,
             "original_execution_sha256": attempt.execution_sha256,
             "reviewer_source_sha256": reviewer.previous.sha256(Path(reviewer.__file__)),
             "projection_reviewer_source_sha256": reviewer.previous.sha256(
                 Path(reviewer.previous.__file__)),
             "method_reviewer_source_sha256": reviewer.previous.sha256(
                 Path(reviewer.previous.previous.__file__)),
             "record_reviewer_source_sha256": reviewer.previous.sha256(
                 Path(reviewer.previous.records.__file__)),
             "execution_sources_sha256": sources, "materialized_shapes": shapes,
             "original_evidence_file_sha256": reviewer.previous.previous.evidence_files(directory),
             **reviewer.review(original, events, shapes, api)}
    value["reviewed_admission_sha256"] = provenance_sha256(value["reviewed_admission"])
    sidecar = tmp_path / reviewer.TIMEOUT_DIRECTORY / "run.json"
    sidecar.parent.mkdir()
    sidecar.write_text(json.dumps(value))
    before = ledger.path.read_bytes()
    if damage == "source":
        (app / reviewer.SOURCE_PATHS[0]).write_text("drift")
    elif damage == "evidence":
        (run / "trace.jsonl").write_text("drift")
    elif damage == "replica":
        state.write_text('{"A28":{"artifacts":[]}}')
    elif damage == "proof":
        value["timeout_proof"]["latency_ms"] = 1
        sidecar.write_text(json.dumps(value))
    elif damage == "reviewer":
        value["record_reviewer_source_sha256"] = "b" * 64
        sidecar.write_text(json.dumps(value))
    if damage:
        with pytest.raises(RuntimeError):
            _ = reviewer.ProjectionAttemptLedger(
                ledger.path, ledger.cells, ledger.schedule_sha256).attempts
        assert ledger.path.read_bytes() == before
        return
    view = reviewer.ProjectionAttemptLedger(ledger.path, ledger.cells, ledger.schedule_sha256)
    assert view.completed_cells == ()
    assert view.original_attempts[0].disposition == "confounder"
    assert view.attempts[0].disposition == "operational_excluded"
    assert reviewer.effective_admission(tmp_path, view.attempts[0])["original_evaluation"] is None
    assert ledger.path.read_bytes() == before
    with pytest.raises(RuntimeError, match="identical execution"):
        view.reserve("cell", "wrong-build", "d" * 64)
    assert ledger.path.read_bytes() == before
    view.reserve("cell", "replacement", execution)
    view.settle("replacement", "operational_excluded", reviewer.REASON, "c" * 64)
    replay = reviewer.ProjectionAttemptLedger(ledger.path, ledger.cells, ledger.schedule_sha256)
    with pytest.raises(RuntimeError, match="one operational replacement exhausted"):
        replay.reserve("cell", "third", execution)
