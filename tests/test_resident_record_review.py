import importlib
import json
import os
import sys
from pathlib import Path

import pytest

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import AttemptLedger
from infra_joint.worker.artifact_store import FileArtifactStore, StoredArtifact

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
reviewer = importlib.import_module("large_scale_resident_record_review_v1")


@pytest.fixture
def field_case() -> tuple:
    original = {"disposition": "confounder", "problems": [reviewer.GATE_PROBLEM],
                "operational_incidents": [], "original_evaluation": {"benchmark_score": 0}}
    schema = {"kind": "record_array", "text_field": "body", "fields": {"body": "string"}}
    events = [{"event_type": "logical.reasoning.input", "payload": {
        "logical_agent_id": "manager", "input_items": [{"content": json.dumps({"task": {
            "artifacts": [{"artifact_id": "source", "content_schema": schema}]}})}]}}]
    for aid, operator, inputs, output, args in [
        ("retrieve", "bm25_retrieve", ["source"], "retrieved", {"text_field": "body"}),
        ("aggregate", "aggregate_artifacts", ["retrieved"], "merged", {}),
        ("bad", "bm25_retrieve", ["merged"], "missing", {"text_field": "text"}),
    ]:
        events.append({"event_type": "logical.action.prepared", "payload": {"action": {
            "action_id": aid, "owner_agent_id": "specialist", "action_type": "tool",
            "operator": operator, "inputs": inputs, "arguments": args,
            "outputs": [{"artifact_id": output}]}}})
        events.append({"event_type": "logical.observation", "payload": {"action_id": aid,
            "owner_agent_id": "specialist", "succeeded": aid != "bad",
            "failure_code": "validation_failed" if aid == "bad" else None,
            "failure_message": "document field must be text: text" if aid == "bad" else None}})
    events.append({"event_type": "physical.execution", "payload": {"action_id": "bad",
        "selection": {"selected_agent_id": "private-worker"}, "failure": {
            "failure_code": "validation_failed",
            "failure_message": "document field must be text: text",
            "operator": "bm25_retrieve", "stage": "execution"}}})
    shape = {"merged": {"artifact_id": "merged", "sha256_hex": "a" * 64,
        "record_count": 2, "actual_union_fields": ["body", "title"],
        "all_records_have_string_body": True}}
    return original, events, shape


def test_exact_derived_field_failure_is_valid_wrong_sample_without_repair(field_case):
    original, events, shape = field_case
    before = json.dumps((original, events, shape))
    value = reviewer.review(original, events, shape)
    assert json.dumps((original, events, shape)) == before
    assert value["reviewed_admission"]["original_evaluation"]["benchmark_score"] == 0
    assert value["reviewed_admission"]["replacement_authorized"] is False
    assert value["record_field_proof"][0]["specialist_received_artifact_schema"] is None
    assert "private-worker" not in json.dumps(value)


@pytest.mark.parametrize("damage", ["privacy", "outage", "field_present", "schema", "producer",
                                    "duplicate", "wrong_stage", "wrong_message", "extra_failure"])
def test_record_review_rejects_every_unproven_validation_case(field_case, damage):
    original, events, shape = field_case
    if damage == "privacy":
        original["problems"].append("privacy_violation")
    elif damage == "outage":
        original["operational_incidents"].append("provider_failure")
    elif damage == "field_present":
        shape["merged"]["actual_union_fields"].append("text")
    elif damage == "schema":
        events[0]["payload"]["input_items"][0]["content"] = '{"task":{"artifacts":[]}}'
    elif damage == "producer":
        events[1]["payload"]["action"]["operator"] = "invoke_model"
    elif damage == "duplicate":
        events.append(events[1])
    elif damage == "wrong_stage":
        events[-1]["payload"]["failure"]["stage"] = "transfer"
    elif damage == "wrong_message":
        events[-1]["payload"]["failure"]["failure_message"] = "runtime failure"
    else:
        extra = json.loads(json.dumps(events[-1]))
        extra["payload"]["action_id"] = "unknown_failure"
        events.append(extra)
    with pytest.raises(RuntimeError):
        reviewer.review(original, events, shape)


def test_selected_absent_fields_have_exact_proof(field_case):
    original, events, shape = field_case
    action = events[-3]["payload"]["action"]
    action.update(operator="select_fields", arguments={"fields": ["title", "description", "body"]})
    message = "selected fields are missing: ['description']"
    events[-2]["payload"]["failure_message"] = message
    events[-1]["payload"]["failure"].update(operator="select_fields", failure_message=message)
    assert reviewer.review(original, events, shape)["record_field_proof"][0]["missing_fields"] == [
        "description"]


def test_shape_scan_exports_no_record_values_and_checks_hash(tmp_path):
    store = FileArtifactStore(tmp_path)
    store.put(StoredArtifact.create("records", "application/json",
                                   b'[{"title":"PRIVATE_TITLE","body":"PRIVATE_CORPUS"}]'))
    metadata = store.metadata()[0].model_dump()
    result = reviewer.inspect_store(tmp_path, "records", metadata)
    assert result["actual_union_fields"] == ["body", "title"]
    assert "PRIVATE" not in json.dumps(result)
    metadata["size_bytes"] += 1
    with pytest.raises(RuntimeError, match="metadata mismatch"):
        reviewer.inspect_store(tmp_path, "records", metadata)


@pytest.mark.parametrize("damage", [None, "source", "evidence", "replica", "sidecar_shape"])
def test_record_ledger_proof_is_reproducible_and_preserves_original(
    field_case, tmp_path, damage,
):
    original, events, shapes = field_case
    root = tmp_path
    directory = root / "evidence/cell/attempt1"
    run = directory / "runs/run"
    run.mkdir(parents=True)
    (directory / "admission.json").write_text(json.dumps(original))
    (run / "trace.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    shapes["merged"].update(media_type="application/json", size_bytes=100)
    metadata = {k: shapes["merged"][k] for k in (
        "artifact_id", "media_type", "size_bytes", "sha256_hex")}
    private = directory / "private"
    private.mkdir()
    state = private / "worker-state-after.json"
    state.write_text(json.dumps({"A28": {"artifacts": [metadata]}}))
    for source in reviewer.SOURCE_PATHS:
        path = root / "app" / source
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("frozen source\n")
    ledger = AttemptLedger(root / "phase1-attempts.jsonl", ("cell",), "a" * 64)
    ledger.reserve("cell", "run", "b" * 64)
    ledger.settle("run", "confounder", reviewer.GATE_PROBLEM, provenance_sha256(original))
    attempt = ledger.attempts[0]
    review = reviewer.review(original, events, shapes)
    value = {"run_id": "run", "original_admission_sha256": attempt.receipt_sha256,
        "original_execution_sha256": attempt.execution_sha256,
        "reviewer_source_sha256": reviewer.sha256(Path(reviewer.__file__)),
        "execution_sources_sha256": {p: reviewer.sha256(root / "app" / p)
                                     for p in reviewer.SOURCE_PATHS},
        "materialized_shapes": shapes, "original_evidence_file_sha256": {
            str(p.relative_to(directory)): reviewer.sha256(p)
            for p in directory.rglob("*") if p.is_file()}, **review,
        "reviewed_admission_sha256": provenance_sha256(review["reviewed_admission"])}
    sidecar = root / reviewer.DIRECTORY / "run.json"
    sidecar.parent.mkdir()
    sidecar.write_text(json.dumps(value))
    journal = ledger.path.read_bytes()
    if damage == "source":
        (root / "app" / reviewer.SOURCE_PATHS[0]).write_text("drift")
    elif damage == "evidence":
        (run / "trace.jsonl").write_text("drift")
    elif damage == "replica":
        state.write_text('{"A28":{"artifacts":[]}}')
    elif damage == "sidecar_shape":
        value["materialized_shapes"]["merged"]["actual_union_fields"].append("text")
        sidecar.write_text(json.dumps(value))
    view = reviewer.RecordAttemptLedger(ledger.path, ledger.cells, ledger.schedule_sha256)
    if damage:
        with pytest.raises(RuntimeError):
            _ = view.attempts
    else:
        assert view.completed_cells == ("cell",)
        assert view.original_attempts[0].disposition == "confounder"
        assert reviewer.effective_admission(root, view.attempts[0])["disposition"] == "valid"
        with pytest.raises(RuntimeError, match="must not be repeated"):
            view.reserve("cell", "retry", "b" * 64)
    assert journal == ledger.path.read_bytes()


def test_auditor_lease_does_not_waive_actual_queue_or_atomic_process(tmp_path):
    root = tmp_path / "resident-block"
    root.mkdir()
    proc = tmp_path / "proc"
    live = proc / str(os.getpid())
    live.mkdir(parents=True)
    (live / "cmdline").write_bytes(b"python resident-block audit.py")
    lease = root / "queue-lease.json"
    lease.write_text(json.dumps({"pid": os.getpid()}))
    with pytest.raises(RuntimeError, match="inactive"):
        reviewer.assert_inactive(root, proc_root=proc)
    reviewer.assert_inactive(root, proc_root=proc, allow_current_audit_lease=True)
    handle = root / "queue-process-001.json"
    handle.write_text(json.dumps({"pid": os.getpid()}))
    with pytest.raises(RuntimeError, match="inactive"):
        reviewer.assert_inactive(root, proc_root=proc, allow_current_audit_lease=True)
    handle.unlink()
    other = proc / str(os.getpid() + 1)
    other.mkdir()
    (other / "cmdline").write_bytes(b"python resident-block queue.py")
    lease.write_text(json.dumps({"pid": os.getpid() + 1}))
    with pytest.raises(RuntimeError, match="inactive"):
        reviewer.assert_inactive(root, proc_root=proc, allow_current_audit_lease=True)


def test_snapshot_records_record_sidecar_without_claiming_a_model_parse_failure(tmp_path):
    from types import SimpleNamespace

    base = importlib.import_module("large_scale_snapshot_v1")
    directory = tmp_path / "evidence/cell/attempt1"
    run = directory / "runs/run"
    run.mkdir(parents=True)
    (directory / "private/api").mkdir(parents=True)
    result = {"execution_completed": True, "final_answer": "No", "loop": {"usage": {}},
              "evaluation": {"benchmark_score": 0, "format_valid": True}, "telemetry": {}}
    (run / "result.json").write_text(json.dumps(result))
    (run / "trace.jsonl").write_text("")
    admission = {"disposition": "valid", "problems": [],
                 "result_sha256": provenance_sha256(result)}
    sidecar = tmp_path / reviewer.DIRECTORY / "run.json"
    sidecar.parent.mkdir()
    value = {"record_field_proof": [{"action_id": "bad1"}, {"action_id": "bad2"}]}
    sidecar.write_text(json.dumps(value))
    attempt = SimpleNamespace(run_id="run", attempt_index=1, disposition="valid",
        receipt_sha256=provenance_sha256(admission), reason=reviewer.REASON,
        execution_sha256="a" * 64)
    actual = base.settled_attempt(tmp_path, "cell", attempt,
                                  admission_reader=lambda root, item: admission)
    assert actual["original_rejection_preserved"]
    assert actual["record_field_adjudication_sha256"] == provenance_sha256(value)
    assert actual["confirmed_absent_record_field_failures"] == 2
    assert actual["confirmed_post_inference_json_failures"] == 0
    assert actual["benchmark_score"] == 0
