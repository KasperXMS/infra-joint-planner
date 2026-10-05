import importlib
import json
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from test_large_scale_compound_review import compound_fixture
from test_large_scale_provider_policy_review import api_fixture

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import AttemptLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
review = importlib.import_module("large_scale_field_policy_review_v1")
control = importlib.import_module("large_scale_field_policy_queue_v1")


def fixture(root: Path) -> tuple[dict, list, dict, Path]:
    directory = root / "evidence/cell4/attempt1"
    directory.mkdir(parents=True)
    api_fixture(directory / "private/api")
    schema = {"kind": "record_array", "text_field": "body", "record_count": 2,
              "fields": {"body": "string"}}
    body = root / "preparation/task-freeze-002/corpus.json"
    body.parent.mkdir(parents=True)
    body.write_text('[{"body":"PRIVATE evidence one"},{"body":"PRIVATE evidence two"}]')
    artifact = {"artifact_id": "corpus", "path": str(body), "bytes": body.stat().st_size,
                "sha256": review.sha256(body), "media_type": "application/json"}
    ref = {"artifact_id": "corpus", "content_schema": schema}
    (directory / "private/task-contract.json").write_text(json.dumps({"artifacts": [ref]}))
    (directory / "attempt-freeze.json").write_text(json.dumps({
        "task_receipt": {"artifacts": [artifact]}}))
    (directory / "private/worker-state-after.json").write_text(json.dumps({
        "A4": {"artifacts": [{"artifact_id": "corpus", "size_bytes": artifact["bytes"],
                               "sha256_hex": artifact["sha256"],
                               "media_type": "application/json"}]}}))
    original = {"disposition": "confounder", "reason": review.GATES[0],
                "problems": list(review.GATES), "operational_incidents": [],
                "execution_completed": False, "original_evaluation": None,
                "terminal_failure": {"code": "logical_loop_failed",
                                     "message": "HTTP400 data_inspection_failed"}}
    events = [
        {"event_type": "logical.reasoning.input", "payload": {
            "logical_agent_id": "manager", "input_items": [{"role": "user", "content":
                json.dumps({"task": {"artifacts": [ref]}})}]}},
        {"event_type": "logical.action.prepared", "payload": {"action": {
            "action_id": "action", "action_type": "tool", "operator": "bm25_retrieve",
            "inputs": ["corpus"], "arguments": {"query": "PRIVATE query", "text_field": "text"}}}},
        {"event_type": "logical.observation", "payload": {
            "action_id": "action", "succeeded": False, "failure_code": "validation_failed",
            "failure_message": "document field must be text: text"}},
        {"event_type": "physical.execution", "payload": {
            "action_id": "action", "selection": {"selected_agent_id": "private-worker"},
            "failure": {"stage": "execution", "operator": "bm25_retrieve",
                        "failure_code": "validation_failed",
                        "failure_message": "document field must be text: text"}}},
        {"event_type": "action.completed", "payload": {"action_id": "action", "succeeded": False}},
        {"event_type": "workflow.graph.snapshot", "payload": {
            "nodes": [{"action_id": "action", "status": "failed"}]}},
    ]
    return original, events, review.artifact_shapes(root, directory), directory


def test_exact_wrong_field_plus_policy_without_agent_repair_or_quality_fabrication(tmp_path: Path):
    original, events, shapes, directory = fixture(tmp_path)
    before = deepcopy((original, events))
    result = review.review(original, events, shapes, directory / "private/api")
    assert result["covered_original_findings"] == list(review.GATES)
    assert result["field_misuse_proof"][0]["root_received_correct_schema"]
    assert not result["field_misuse_proof"][0]["reached_model_inference"]
    assert result["reviewed_admission"]["original_evaluation"] is None
    assert not result["reviewed_admission"]["replacement_authorized"]
    assert len(result["provider_policy_proof"]) == 2
    assert "PRIVATE" not in json.dumps(result)
    assert (original, events) == before


@pytest.mark.parametrize("damage", ["extra", "duplicate", "operator", "model", "message",
                                    "stage", "selected", "source-input", "schema-hidden",
                                    "field-declared", "field-present", "not-completed",
                                    "graph-open", "quota", "policy-missing"])
def test_no_blanket_validation_or_missing_capability_waiver(tmp_path: Path, damage: str):
    original, events, shapes, directory = fixture(tmp_path)
    if damage == "extra":
        original["problems"].append("privacy_violation")
    elif damage == "duplicate":
        events.append(deepcopy(events[2]))
    elif damage == "operator":
        events[1]["payload"]["action"]["operator"] = "filter_records"
    elif damage == "model":
        events[1]["payload"]["action"]["action_type"] = "model"
    elif damage == "message":
        events[2]["payload"]["failure_message"] = "artifact missing"
    elif damage == "stage":
        events[3]["payload"]["failure"]["stage"] = "selection"
    elif damage == "selected":
        events[3]["payload"]["selection"] = {}
    elif damage == "source-input":
        events[1]["payload"]["action"]["inputs"] = ["generated-artifact"]
    elif damage == "schema-hidden":
        events[0]["payload"]["input_items"][0]["content"] = '{"task":{"artifacts":[]}}'
    elif damage == "field-declared":
        shapes["corpus"]["all_declared_fields"].append("text")
    elif damage == "field-present":
        shapes["corpus"]["actual_union_fields"].append("text")
    elif damage == "not-completed":
        events.pop(4)
    elif damage == "graph-open":
        events[5]["payload"]["nodes"][0]["status"] = "running"
    elif damage == "quota":
        p = directory / "private/api/blocked1-response.json"
        p.write_text('{"error":{"code":"quota"}}')
    else:
        (directory / "private/api/blocked1-response.json").unlink()
    with pytest.raises((RuntimeError, KeyError)):
        review.review(original, events, shapes, directory / "private/api")


@pytest.mark.parametrize("damage", ["hash", "shape", "metadata", "symlink", "outside"])
def test_prepared_payload_not_assumed_equivalent_to_declared_schema(
    tmp_path: Path, damage: str, monkeypatch: pytest.MonkeyPatch,
):
    _, _, _, directory = fixture(tmp_path)
    if damage in ("hash", "shape", "symlink", "outside"):
        p = directory / "attempt-freeze.json"
        value = json.loads(p.read_text())
        row = value["task_receipt"]["artifacts"][0]
        source = Path(row["path"])
        if damage == "hash":
            source.write_text('[]')
        elif damage == "shape":
            source.write_text('[{"body":1},{"body":2}]')
            row["sha256"], row["bytes"] = review.sha256(source), source.stat().st_size
        elif damage == "symlink":
            original = Path.is_symlink
            monkeypatch.setattr(Path, "is_symlink", lambda p: p == source or original(p))
        else:
            outside = tmp_path / "outside.json"
            outside.write_bytes(source.read_bytes())
            row["path"] = str(outside)
        p.write_text(json.dumps(value))
    else:
        p = directory / "private/worker-state-after.json"
        value = json.loads(p.read_text())
        value["A4"]["artifacts"][0]["sha256_hex"] = "0" * 64
        p.write_text(json.dumps(value))
    with pytest.raises(RuntimeError):
        review.artifact_shapes(tmp_path, directory)


def ledger_fixture(tmp_path: Path, cells=("cell1", "cell2", "cell3", "cell4")):
    _, ledger, _, _, _ = compound_fixture(tmp_path, cells)
    ledger = review.previous.CompoundAttemptLedger(
        ledger.path, ledger.cells, ledger.schedule_sha256)
    original, events, shapes, directory = fixture(tmp_path)
    ledger.reserve("cell4", "run4", "b" * 64)
    (directory / "admission.json").write_text(json.dumps(original))
    run = directory / "runs/run4"
    run.mkdir(parents=True)
    (run / "trace.jsonl").write_text("\n".join(json.dumps(e) for e in events))
    ledger.settle("run4", "confounder", review.GATES[0], provenance_sha256(original))
    for source in review.SOURCE_PATHS:
        p = tmp_path / "app" / source
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("frozen source")
    proof = review.review(original, events, shapes, directory / "private/api")
    sidecar = tmp_path / review.DIRECTORY / "run4.json"
    sidecar.parent.mkdir()
    value = {"run_id": "run4", "original_admission_sha256": provenance_sha256(original),
             "original_execution_sha256": "b" * 64, "reviewer_sources_sha256": review.sources(),
             "execution_sources_sha256": {p: review.sha256(tmp_path / "app" / p)
                                           for p in review.SOURCE_PATHS},
             "initial_artifact_shapes": shapes, "original_evidence_file_sha256": {
                 str(p.relative_to(directory)): review.sha256(p)
                 for p in directory.rglob("*") if p.is_file()}, **proof,
             "reviewed_admission_sha256": provenance_sha256(proof["reviewed_admission"])}
    sidecar.write_text(json.dumps(value))
    return sidecar, ledger, directory


def test_all_four_review_types_coexist_without_journal_rewrite_or_replacement(tmp_path: Path):
    _, ledger, directory = ledger_fixture(tmp_path)
    before = ledger.path.read_bytes(), (directory / "admission.json").read_bytes()
    view = control.FieldQueueView(ledger.path, ledger.cells, ledger.schedule_sha256)
    assert view.completed_cells == ledger.cells
    assert all(a.disposition == "confounder" for a in view.original_attempts)
    assert review.effective_admission(tmp_path, view.attempts[-1])["original_evaluation"] is None
    assert before == (ledger.path.read_bytes(), (directory / "admission.json").read_bytes())
    with pytest.raises(RuntimeError, match="must not be repeated"):
        view.reserve("cell4", "replacement", "b" * 64)


@pytest.mark.parametrize("damage", ["body", "source", "evidence", "proof", "reviewer"])
def test_cache_and_direct_proof_reject_mutation(tmp_path: Path, damage: str):
    sidecar, ledger, directory = ledger_fixture(tmp_path)
    view = control.FieldQueueView(ledger.path, ledger.cells, ledger.schedule_sha256)
    assert view.completed_cells == ledger.cells
    value = json.loads(sidecar.read_text())
    if damage == "body":
        Path(value["initial_artifact_shapes"]["corpus"]["path"]).write_text('[]')
    elif damage == "source":
        (tmp_path / "app" / review.SOURCE_PATHS[0]).write_text("changed")
    elif damage == "evidence":
        (directory / "extra.json").write_text("{}")
    elif damage == "proof":
        value["field_misuse_proof"][0]["reached_model_inference"] = True
        sidecar.write_text(json.dumps(value))
    else:
        value["reviewer_sources_sha256"]["field"] = "c" * 64
        sidecar.write_text(json.dumps(value))
    with pytest.raises(RuntimeError):
        _ = view.completed_cells


def test_parent_control_is_immutable_and_new_receipts_do_not_modify_it(tmp_path, monkeypatch):
    saved = {"execution_sha256": "b" * 64}
    p = tmp_path / "queue-control-freeze-006.json"
    p.write_text(json.dumps(saved))
    monkeypatch.setattr(control, "ROOT", tmp_path)
    monkeypatch.setattr(control, "PARENT_CONTROL", provenance_sha256(saved))
    monkeypatch.setattr(control.parent, "control_value", lambda: saved)
    before = p.read_bytes()
    value = control.control_value()
    assert not value["formal_execution_changed"]
    assert not value["replacement_authorized"]
    assert p.read_bytes() == before
    monkeypatch.setattr(control.parent, "control_value", lambda: {**saved, "changed": True})
    with pytest.raises(RuntimeError, match="parent control drift"):
        control.control_value()


def test_snapshot_restores_base_and_keeps_field_failure_non_inference(tmp_path, monkeypatch):
    sidecar, _, _ = ledger_fixture(tmp_path)
    projection = importlib.import_module("large_scale_field_policy_snapshot_v1")
    prior = projection.base.SnapshotAttemptLedger, projection.base.effective_admission
    value = {"rows": [{"attempts": [{"run_id": "run4", "admission_reason": review.REASON,
                                     "benchmark_score": None}]}]}
    monkeypatch.setattr(projection.base, "snapshot", lambda root: value)
    result = projection.snapshot(tmp_path)
    row = result["rows"][0]["attempts"][0]
    assert row["benchmark_score"] is None
    assert row["confirmed_initial_corpus_field_failures"] == 1
    assert "confirmed_post_inference_json_failures" not in row
    assert row["compound_adjudication_sha256"] == provenance_sha256(json.loads(sidecar.read_text()))
    assert prior == (projection.base.SnapshotAttemptLedger, projection.base.effective_admission)


def test_controller_drift_cannot_launch_any_cell(tmp_path, monkeypatch):
    queue = importlib.import_module("large_scale_queue_v1")
    monkeypatch.setattr(control, "ROOT", tmp_path)
    monkeypatch.setattr(queue, "require_remote", lambda root: None)
    monkeypatch.setattr(control, "control_value", lambda: {
        "field_review_receipts": {"run4": "new"}})
    path = tmp_path / "queue-control-freeze-007.json"
    path.write_text('{"field_review_receipts":{"run4":"old"}}')
    with pytest.raises(RuntimeError, match="provenance drift"):
        control.run(path)


def test_actual_queue_skips_reviewed_failures_and_launches_only_original_next_cell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    _, ledger, _ = ledger_fixture(tmp_path, ("cell1", "cell2", "cell3", "cell4", "cell5"))
    queue = importlib.import_module("large_scale_queue_v1")
    monkeypatch.setattr(control, "ROOT", tmp_path)
    monkeypatch.setattr(queue, "ROOT", tmp_path)
    monkeypatch.setattr(queue, "require_remote", lambda root: None)
    monkeypatch.setattr(review.previous, "require_stopped", lambda *args, **kwargs: None)
    monkeypatch.setattr(queue.frozen, "validate_runtime_import_root", lambda: None)
    monkeypatch.setattr(queue, "schedule", lambda: tuple(
        SimpleNamespace(cell_id=c) for c in ledger.cells))
    monkeypatch.setattr(queue, "schedule_sha256", lambda cells: ledger.schedule_sha256)
    monkeypatch.setattr(queue, "verify_execution_freeze", lambda path=None: "b" * 64)
    monkeypatch.setattr(queue, "verified_prices", lambda *args: (tmp_path / "prices", "c" * 64))
    monkeypatch.setattr(queue.frozen, "protocol", lambda: {})
    monkeypatch.setattr(queue, "AttemptLedger", AttemptLedger)
    monkeypatch.setattr(queue, "cell_config", lambda cell, run_id, reference: {
        "cell_id": cell.cell_id, "run_id": run_id})
    launches = []

    class Process:
        def __init__(self, command, **kwargs):
            config = yaml.safe_load(Path(command[command.index("--config") + 1]).read_text())
            launches.append(config["cell_id"])
            self.pid = 999

        def wait(self):
            return 0

    monkeypatch.setattr(queue.subprocess, "Popen", Process)
    monkeypatch.setattr(queue, "admit", lambda *args: {
        "disposition": "valid", "reason": "completed_or_valid_semantic_failure"})
    freeze = {"field_review_receipts": {"run4.json": "bound"}}
    monkeypatch.setattr(control, "control_value", lambda: freeze)
    p = tmp_path / "queue-control-freeze-007.json"
    p.write_text(json.dumps(freeze))
    control.run(p)
    assert launches == ["cell5"]
    assert queue.AttemptLedger is control.FieldQueueView
    assert len(json.loads((tmp_path / "phase1-queue-completed.json").read_text())[
        "completed_cells"]) == 5
