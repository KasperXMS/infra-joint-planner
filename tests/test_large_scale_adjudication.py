import importlib
import json
import sys
from pathlib import Path

import pytest
import yaml

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import AttemptLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
reviewer = importlib.import_module("large_scale_adjudication_v1")


def original(score: int = 0) -> dict:
    return {"disposition": "confounder", "reason": reviewer.GATE_PROBLEM,
            "problems": [reviewer.GATE_PROBLEM], "operational_incidents": [],
            "original_evaluation": {"benchmark_score": score, "format_valid": True}}


def events() -> list[dict]:
    return [
        {"event_type": "logical.action.prepared", "payload": {"action": {
            "action_id": "action", "action_type": "model", "prompt": "PRIVATE-PROMPT",
            "outputs": [{"artifact_id": "PRIVATE-OUTPUT", "media_type": "application/json"}]}}},
        {"event_type": "logical.observation", "payload": {
            "action_id": "action", "succeeded": False, "failure_code": "validation_failed",
            "failure_message": "model output is not valid JSON"}},
        {"event_type": "physical.execution", "payload": {
            "action_id": "action", "selection": {"selected_deployment_id": "private-deployment"},
            "failure": {"stage": "execution", "failure_code": "validation_failed",
                        "failure_message": "model output is not valid JSON"}}},
    ]


@pytest.mark.parametrize("score", [0, 1])
def test_model_json_behavior_is_valid_independent_of_quality_without_repair(score: int) -> None:
    receipt = original(score)
    before = json.dumps(receipt)
    value = reviewer.review_model_json_failures(receipt, events())
    assert value["reviewed_admission"]["disposition"] == "valid"
    assert value["reviewed_admission"]["original_evaluation"]["benchmark_score"] == score
    assert value["proof"][0]["reached_model_inference"]
    assert value["proof"][0]["model_service_tokens_unknown"]
    assert json.dumps(receipt) == before
    assert "PRIVATE" not in json.dumps(value)


@pytest.mark.parametrize("damage", ["privacy", "outage", "tool", "message", "selection",
                                     "output", "missing"])
def test_review_is_not_a_blanket_validation_or_other_confounds_bypass(damage: str) -> None:
    receipt, trace = original(), events()
    if damage == "privacy":
        receipt["problems"].append("privacy_violation")
    elif damage == "outage":
        receipt["operational_incidents"] = ["provider_outage"]
    elif damage == "tool":
        trace[0]["payload"]["action"]["action_type"] = "tool"
    elif damage == "message":
        trace[1]["payload"]["failure_message"] = "artifact/schema mismatch"
    elif damage == "selection":
        trace[2]["payload"]["failure"]["stage"] = "selection"
    elif damage == "output":
        trace[0]["payload"]["action"]["outputs"][0]["media_type"] = "text/plain"
    else:
        trace = []
    with pytest.raises(RuntimeError):
        reviewer.review_model_json_failures(receipt, trace)


def fixture(tmp_path: Path) -> tuple[Path, AttemptLedger, Path]:
    ledger = AttemptLedger(tmp_path / "phase1-attempts.jsonl", ("cell1", "cell2"), "a" * 64)
    directory = tmp_path / "evidence/cell1/attempt1"
    run = directory / "runs/run1"
    run.mkdir(parents=True)
    receipt = original()
    (directory / "admission.json").write_text(json.dumps(receipt))
    (run / "trace.jsonl").write_text("\n".join(json.dumps(x) for x in events()))
    worker = tmp_path / "app/src/infra_joint/worker/server.py"
    worker.parent.mkdir(parents=True)
    worker.write_text('completion = await deployment.backend.invoke(model_request)\n'
                      'raise ValueError("model output is not valid JSON")\n')
    ledger.reserve("cell1", "run1", "b" * 64)
    ledger.settle("run1", "confounder", reviewer.GATE_PROBLEM, provenance_sha256(receipt))
    review = reviewer.review_model_json_failures(receipt, events())
    value = {"run_id": "run1", "original_admission_sha256": provenance_sha256(receipt),
             "original_execution_sha256": "b" * 64,
             "worker_source_sha256": reviewer.sha256(worker),
             "reviewer_source_sha256": reviewer.sha256(Path(reviewer.__file__)),
             "original_evidence_file_sha256": {str(p.relative_to(directory)): reviewer.sha256(p)
                                                for p in directory.rglob("*") if p.is_file()},
             **review, "reviewed_admission_sha256": provenance_sha256(review["reviewed_admission"])}
    sidecar = tmp_path / "adjudications/run1.json"
    sidecar.parent.mkdir()
    sidecar.write_text(json.dumps(value))
    return sidecar, ledger, directory


def test_effective_ledger_keeps_rejected_history_and_skips_rerun(tmp_path: Path) -> None:
    sidecar, ledger, directory = fixture(tmp_path)
    before = ledger.path.read_bytes()
    original_receipt = (directory / "admission.json").read_bytes()
    admitted = reviewer.AdjudicatedAttemptLedger(ledger.path, ledger.cells, ledger.schedule_sha256)
    assert admitted.original_attempts[0].disposition == "confounder"
    assert admitted.attempts[0].disposition == "valid"
    assert admitted.completed_cells == ("cell1",)
    assert ledger.path.read_bytes() == before
    assert (directory / "admission.json").read_bytes() == original_receipt
    with pytest.raises(RuntimeError, match="must not be repeated"):
        admitted.reserve("cell1", "replacement-forbidden", "b" * 64)
    admitted.reserve("cell2", "run2", "b" * 64)
    reloaded = reviewer.AdjudicatedAttemptLedger(ledger.path, ledger.cells, ledger.schedule_sha256)
    assert reloaded.pending[0].run_id == "run2"
    assert reviewer.effective_admission(tmp_path, reloaded.attempts[0])["disposition"] == "valid"
    assert sidecar.exists()


@pytest.mark.parametrize("damage", ["proof", "hash", "missing-file", "worker", "evidence"])
def test_sidecar_or_original_evidence_drift_fails_closed(tmp_path: Path, damage: str) -> None:
    sidecar, ledger, directory = fixture(tmp_path)
    value = json.loads(sidecar.read_text())
    if damage == "proof":
        value["proof"][0]["reached_model_inference"] = False
    elif damage == "hash":
        value["original_admission_sha256"] = "c" * 64
    elif damage == "missing-file":
        value["original_evidence_file_sha256"] = {}
    elif damage == "worker":
        (tmp_path / "app/src/infra_joint/worker/server.py").write_text("changed")
    else:
        (directory / "admission.json").write_text("{}")
    sidecar.write_text(json.dumps(value))
    admitted = reviewer.AdjudicatedAttemptLedger(ledger.path, ledger.cells, ledger.schedule_sha256)
    with pytest.raises(RuntimeError):
        _ = admitted.completed_cells


def test_frozen_queue_adapter_launches_only_the_next_never_started_cell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    queue = importlib.import_module("large_scale_queue_v1")
    controller = importlib.import_module("large_scale_adjudicated_queue_v1")
    _, ledger, _ = fixture(tmp_path)
    monkeypatch.setattr(controller, "ROOT", tmp_path)
    monkeypatch.setattr(queue, "ROOT", tmp_path)
    monkeypatch.setattr(queue, "require_remote", lambda root: None)
    monkeypatch.setattr(queue.frozen, "validate_runtime_import_root", lambda: None)
    monkeypatch.setattr(queue, "schedule", lambda: tuple(
        SimpleNamespace(cell_id=identifier) for identifier in ledger.cells))
    monkeypatch.setattr(queue, "schedule_sha256", lambda cells: ledger.schedule_sha256)
    monkeypatch.setattr(queue, "verify_execution_freeze", lambda path=None: "b" * 64)
    monkeypatch.setattr(queue, "verified_prices", lambda *args: (tmp_path / "prices", "c" * 64))
    monkeypatch.setattr(queue.frozen, "protocol", lambda: {})
    monkeypatch.setattr(queue, "cell_config", lambda cell, run_id, reference: {
        "cell_id": cell.cell_id, "run_id": run_id})
    # Restore the frozen module's global after testing the narrowly scoped adapter.
    monkeypatch.setattr(queue, "AttemptLedger", AttemptLedger)
    launches = []

    class Process:
        def __init__(self, command: list[str], **kwargs: object) -> None:
            config = yaml.safe_load(Path(command[command.index("--config") + 1]).read_text())
            launches.append(config["cell_id"])
            self.pid = 999

        def wait(self) -> int:
            return 0

    monkeypatch.setattr(queue.subprocess, "Popen", Process)
    monkeypatch.setattr(queue, "admit", lambda *args: {
        "disposition": "valid", "reason": "completed_or_valid_semantic_failure"})
    manifest = {"adjudication_receipts": {"run1.json": "digest"}}
    monkeypatch.setattr(controller, "control_freeze", lambda: manifest)
    path = tmp_path / "queue-control-freeze-001.json"
    path.write_text(json.dumps(manifest))
    controller.run(path)
    assert launches == ["cell2"]
    updated = reviewer.AdjudicatedAttemptLedger(ledger.path, ledger.cells, ledger.schedule_sha256)
    assert updated.completed_cells == ("cell1", "cell2")
    assert len(updated.original_attempts) == 2


def test_control_freeze_drift_stops_before_any_cell_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = importlib.import_module("large_scale_adjudicated_queue_v1")
    monkeypatch.setattr(controller, "ROOT", tmp_path)
    monkeypatch.setattr(controller, "control_freeze", lambda: {
        "adjudication_receipts": {"x": "new"}})
    path = tmp_path / "queue-control-freeze-001.json"
    path.write_text('{"adjudication_receipts":{"x":"old"}}')
    with pytest.raises(RuntimeError, match="provenance drift"):
        controller.run(path)


def test_duplicate_failed_observations_do_not_inflate_inference_count() -> None:
    trace = events()
    trace.append(trace[1])
    with pytest.raises(RuntimeError, match="duplicate"):
        reviewer.review_model_json_failures(original(), trace)


def test_queue_completion_view_avoids_rehash_per_cell_but_sidecar_drift_invalidates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = importlib.import_module("large_scale_adjudicated_queue_v1")
    path, ledger, _ = fixture(tmp_path)
    calls = []
    delegate = reviewer.verify_sidecar

    def verify(path: Path, attempt: object) -> dict:
        calls.append(path)
        return delegate(path, attempt)

    monkeypatch.setattr(reviewer, "verify_sidecar", verify)
    view = controller.QueueAdmissionView(ledger.path, ledger.cells, ledger.schedule_sha256)
    for _ in range(200):
        assert view.completed_cells == ("cell1",)
    assert len(calls) == 1
    value = json.loads(path.read_text())
    value["proof"][0]["reached_model_inference"] = False
    path.write_text(json.dumps(value))
    with pytest.raises(RuntimeError):
        _ = view.completed_cells
