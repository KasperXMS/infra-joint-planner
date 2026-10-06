"""Exact offline proof; no measured semantic or physical execution changes."""

from __future__ import annotations

import copy
import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import AttemptLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
reviewer = importlib.import_module("large_scale_resident_projection_review_v1")


def case() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    original = {"disposition": "confounder", "reason": reviewer.records.GATE_PROBLEM,
                "problems": [reviewer.records.GATE_PROBLEM], "operational_incidents": [],
                "original_evaluation": {"benchmark_score": 1}}
    events = [{"event_type": "logical.reasoning.input", "payload": {
        "logical_agent_id": "manager", "input_items": [{"content": json.dumps({"task": {
            "artifacts": [{"artifact_id": "source", "content_schema": {"kind": "record_array",
                "text_field": "body", "fields": {"body": "string"}}}]}})}]}}]
    for aid, operator, inputs, output, args in [
        ("retrieve", "bm25_retrieve", ["source"], "retrieved", {"text_field": "body"}),
        ("project", "select_fields", ["retrieved"], "projected", {"fields": ["title", "body"]}),
        ("aggregate", "aggregate_artifacts", ["projected"], "merged", {}),
        ("bad", "bm25_retrieve", ["merged"], "missing", {"text_field": "text"}),
    ]:
        events.extend([
            {"event_type": "logical.action.prepared", "payload": {"action": {
                "action_id": aid, "owner_agent_id": "specialist", "action_type": "tool",
                "operator": operator, "inputs": inputs, "outputs": [{"artifact_id": output}],
                "arguments": args}}},
            {"event_type": "logical.observation", "payload": {"action_id": aid,
                "owner_agent_id": "specialist", "succeeded": aid != "bad",
                "failure_code": "validation_failed" if aid == "bad" else None,
                "failure_message": "document field must be text: text" if aid == "bad" else None}},
            {"event_type": "physical.execution", "payload": {"action_id": aid,
                "selection": {"selected_agent_id": "private-worker"}, "failure": {
                    "failure_code": "validation_failed", "operator": operator,
                    "failure_message": "document field must be text: text", "stage": "execution"}
                    if aid == "bad" else None}},
        ])
    shapes = {"merged": {"artifact_id": "merged", "sha256_hex": "a" * 64, "size_bytes": 100,
                         "media_type": "application/json", "record_count": 2,
                         "actual_union_fields": ["body", "title"],
                         "all_records_have_string_body": True}}
    return original, events, shapes


def test_projection_is_audited_without_mutation_or_retry() -> None:
    original, events, shapes = case()
    before = copy.deepcopy((original, events, shapes))
    with pytest.raises(RuntimeError, match="whole-record"):
        reviewer.records.review(original, events, shapes)
    value = reviewer.review(original, events, shapes)
    assert (original, events, shapes) == before
    assert value["reviewed_admission"]["original_evaluation"]["benchmark_score"] == 1
    assert not value["reviewed_admission"]["replacement_authorized"]
    path = value["projected_record_field_proof"][0]["successful_body_preserving_path"]
    assert [item["operator"] for item in path] == [
        "bm25_retrieve", "select_fields", "aggregate_artifacts"]
    assert "private-worker" not in json.dumps(value)
    assert value["projected_record_field_proof"][0]["specialist_received_artifact_schema"] is None


@pytest.mark.parametrize("damage", ["drop_body", "unknown_producer", "producer_failed",
                                    "producer_not_executed", "source_schema", "present_field",
                                    "private", "outage", "duplicate", "cycle", "wrong_stage",
                                    "wrong_message", "extra_failure", "wrong_owner", "shape_id"])
def test_unproven_projection_is_never_a_validation_waiver(damage: str) -> None:
    original, events, shapes = case()
    if damage == "drop_body":
        events[4]["payload"]["action"]["arguments"]["fields"] = ["title"]
    elif damage == "unknown_producer":
        events[4]["payload"]["action"]["operator"] = "invoke_model"
    elif damage == "producer_failed":
        events[5]["payload"]["succeeded"] = False
    elif damage == "producer_not_executed":
        events.pop(6)
    elif damage == "source_schema":
        events[0]["payload"]["input_items"][0]["content"] = '{"task":{"artifacts":[]}}'
    elif damage == "present_field":
        shapes["merged"]["actual_union_fields"].append("text")
    elif damage == "private":
        original["problems"].append("privacy")
    elif damage == "outage":
        original["operational_incidents"].append("provider_failure")
    elif damage == "duplicate":
        events.append(events[1])
    elif damage == "cycle":
        events[4]["payload"]["action"]["inputs"] = ["merged"]
    elif damage == "wrong_stage":
        events[-1]["payload"]["failure"]["stage"] = "transfer"
    elif damage == "wrong_message":
        events[-1]["payload"]["failure"]["failure_message"] = "unknown"
    elif damage == "extra_failure":
        extra = copy.deepcopy(events[-1])
        extra["payload"]["action_id"] = "unproved"
        events.append(extra)
    elif damage == "wrong_owner":
        events[-2]["payload"]["owner_agent_id"] = "other"
    else:
        shapes["merged"]["artifact_id"] = "other"
    with pytest.raises(RuntimeError):
        reviewer.review(original, events, shapes)


@pytest.mark.parametrize("damage", [None, "source", "evidence", "replica", "shape", "reviewer"])
def test_exact_source_bound_ledger_preserves_raw_and_blocks_semantic_retry(
    tmp_path: Path, damage: str | None,
) -> None:
    original, events, shapes = case()
    directory = tmp_path / "evidence/cell/attempt1"
    run = directory / "runs/run"
    run.mkdir(parents=True)
    (directory / "admission.json").write_text(json.dumps(original))
    (run / "trace.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    state = directory / "private/worker-state-after.json"
    state.parent.mkdir()
    metadata = {k: shapes["merged"][k] for k in (
        "artifact_id", "media_type", "size_bytes", "sha256_hex")}
    state.write_text(json.dumps({"A28": {"artifacts": [metadata]}}))
    app = tmp_path / reviewer.previous.APPS[3]
    for relative in reviewer.records.SOURCE_PATHS:
        path = app / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("frozen execution source\n")
    sources = {p: reviewer.sha256(app / p) for p in reviewer.records.SOURCE_PATHS}
    freeze = {"source_sha256": sources}
    (tmp_path / "execution-freeze-004.json").write_text(json.dumps(freeze))
    ledger = AttemptLedger(tmp_path / "phase1-attempts.jsonl", ("cell", "next"), "a" * 64)
    ledger.reserve("cell", "run", provenance_sha256(freeze))
    ledger.settle("run", "confounder", reviewer.records.GATE_PROBLEM, provenance_sha256(original))
    attempt = ledger.attempts[0]
    value = {"run_id": "run", "original_admission_sha256": attempt.receipt_sha256,
        "original_execution_sha256": attempt.execution_sha256,
        "reviewer_source_sha256": reviewer.sha256(Path(reviewer.__file__)),
        "previous_reviewer_source_sha256": reviewer.sha256(Path(reviewer.previous.__file__)),
        "record_reviewer_source_sha256": reviewer.sha256(Path(reviewer.records.__file__)),
        "execution_sources_sha256": sources, "materialized_shapes": shapes,
        "original_evidence_file_sha256": reviewer.previous.evidence_files(directory),
        **reviewer.review(original, events, shapes)}
    value["reviewed_admission_sha256"] = provenance_sha256(value["reviewed_admission"])
    sidecar = tmp_path / reviewer.DIRECTORY / "run.json"
    sidecar.parent.mkdir()
    sidecar.write_text(json.dumps(value))
    before = ledger.path.read_bytes()
    if damage == "source":
        (app / reviewer.records.SOURCE_PATHS[0]).write_text("drift")
    elif damage == "evidence":
        (run / "trace.jsonl").write_text("drift")
    elif damage == "replica":
        state.write_text('{"A28":{"artifacts":[]}}')
    elif damage == "shape":
        value["materialized_shapes"]["merged"]["actual_union_fields"].append("text")
        sidecar.write_text(json.dumps(value))
    elif damage == "reviewer":
        value["record_reviewer_source_sha256"] = "b" * 64
        sidecar.write_text(json.dumps(value))
    view = reviewer.ProjectionAttemptLedger(ledger.path, ledger.cells, ledger.schedule_sha256)
    if damage:
        with pytest.raises(RuntimeError):
            _ = view.attempts
    else:
        assert view.completed_cells == ("cell",)
        assert view.original_attempts[0].disposition == "confounder"
        assert reviewer.effective_admission(tmp_path, view.attempts[0])["disposition"] == "valid"
        with pytest.raises(RuntimeError, match="must not be repeated"):
            view.reserve("cell", "retry", attempt.execution_sha256)
    assert ledger.path.read_bytes() == before
    if damage is None:
        # Reproduce the actual next-cell boundary: only the new view can replay
        # a reservation after the now-reviewed raw confounder. Historical
        # control code must remain immutable and must not replay this journal.
        view.reserve("next", "later", attempt.execution_sha256)
        view.settle("later", "valid", "completed_or_valid_semantic_failure", "c" * 64)
        with pytest.raises(RuntimeError, match="unresolved system confounder"):
            reviewer.previous.MethodContractAttemptLedger(
                ledger.path, ledger.cells, ledger.schedule_sha256)
        replay = reviewer.ProjectionAttemptLedger(ledger.path, ledger.cells, ledger.schedule_sha256)
        assert replay.completed_cells == ("cell", "next")
        assert replay.original_attempts[0].disposition == "confounder"
