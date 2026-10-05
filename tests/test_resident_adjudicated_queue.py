import importlib
import json
import os
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import AttemptLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
control = importlib.import_module("large_scale_resident_adjudicated_queue_v1")
reviewer = control.reviewer
frozen = control.frozen


@pytest.fixture
def rejected_model_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple:
    receipt = {"disposition": "confounder", "reason": reviewer.GATE_PROBLEM,
               "problems": [reviewer.GATE_PROBLEM], "operational_incidents": [],
               "result_sha256": "result_hash",
               "original_evaluation": {"benchmark_score": 1, "format_valid": True}}
    events = [
        {"event_type": "logical.action.prepared", "payload": {"action": {
            "action_id": "model", "action_type": "model", "prompt": "PRIVATE_PROMPT",
            "outputs": [{"artifact_id": "note", "media_type": "application/json"}]}}},
        {"event_type": "logical.observation", "payload": {"action_id": "model",
            "succeeded": False, "failure_code": "validation_failed",
            "failure_message": "model output is not valid JSON"}},
        {"event_type": "physical.execution", "payload": {"action_id": "model",
            "selection": {"selected_deployment_id": "private-deployment"},
            "failure": {"stage": "execution", "failure_code": "validation_failed",
                        "failure_message": "model output is not valid JSON"}}},
    ]
    cells = (SimpleNamespace(cell_id="cell1"), SimpleNamespace(cell_id="cell2"))
    ledger = AttemptLedger(tmp_path / "phase1-attempts.jsonl", ("cell1", "cell2"), "a" * 64)
    directory = tmp_path / "evidence/cell1/attempt1"
    run = directory / "runs/run1"
    run.mkdir(parents=True)
    (directory / "admission.json").write_text(json.dumps(receipt))
    (run / "trace.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    (directory / "process.json").write_text('{"pid":9999999,"run_id":"run1"}')
    (directory / "worker-shutdown.json").write_text('{"verified_exited":true}')
    private = directory / "private"
    private.mkdir()
    (private / "residency-validation.json").write_text('{"passed":true}')
    worker = tmp_path / "app/src/infra_joint/worker/server.py"
    worker.parent.mkdir(parents=True)
    worker.write_text('completion = await deployment.backend.invoke(model_request)\n'
                      'raise ValueError("model output is not valid JSON")\n')
    freeze_path = tmp_path / "execution-freeze-001.json"
    freeze_path.write_text(json.dumps({"source_sha256": {
        "src/infra_joint/worker/server.py": reviewer.sha256(worker)}}))
    ledger.reserve("cell1", "run1", "b" * 64)
    ledger.settle("run1", "confounder", reviewer.GATE_PROBLEM, provenance_sha256(receipt))
    monkeypatch.setattr(frozen, "ROOT", tmp_path)
    monkeypatch.setattr(frozen, "APP", tmp_path / "app")
    monkeypatch.setattr(frozen, "FREEZE", freeze_path)
    monkeypatch.setattr(frozen, "require_remote", lambda: None)
    monkeypatch.setattr(frozen, "verify_freeze", lambda: "b" * 64)
    monkeypatch.setattr(frozen, "schedule", lambda: cells)
    monkeypatch.setattr(frozen, "schedule_sha256", lambda cells: "a" * 64)
    monkeypatch.setattr(frozen, "verified_prices", lambda *args: (tmp_path / "prices", "p" * 64))
    monkeypatch.setattr(frozen.frozen, "_yaml", lambda path: {"run_id": "run1"})
    monkeypatch.setattr(frozen, "admit", lambda *args: receipt)
    return tmp_path, directory, ledger, receipt


def test_resident_review_preserves_all_rejected_bytes_and_never_repeats(rejected_model_json):
    root, directory, ledger, _ = rejected_model_json
    before = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    journal = ledger.path.read_bytes()
    value = control.create_review("run1")
    assert value["confirmed_parse_failures"] == 1 and not value["rerun"]
    assert not value["execution_changed"]
    assert journal == ledger.path.read_bytes()
    assert all(path.read_bytes() == content for path, content in before.items())
    view = control.SnapshotAttemptLedger(ledger.path, ledger.cells, ledger.schedule_sha256)
    assert view.original_attempts[0].disposition == "confounder"
    assert view.attempts[0].disposition == "valid" and view.completed_cells == ("cell1",)
    with pytest.raises(RuntimeError, match="must not be repeated"):
        view.reserve("cell1", "forbidden_retry", "b" * 64)
    assert "PRIVATE_PROMPT" not in json.dumps(value)
    assert (root / "adjudications/run1.json").is_file()


@pytest.mark.parametrize("damage", ["privacy", "residency", "worker_exit", "source", "message"])
def test_resident_review_is_not_a_generic_validation_bypass(
    rejected_model_json, damage: str,
) -> None:
    root, directory, _, receipt = rejected_model_json
    if damage == "privacy":
        receipt["problems"].append("privacy_violation")
    elif damage == "residency":
        (directory / "private/residency-validation.json").write_text('{"passed":false}')
    elif damage == "worker_exit":
        (directory / "worker-shutdown.json").write_text('{"verified_exited":false}')
    elif damage == "source":
        (root / "app/src/infra_joint/worker/server.py").write_text("changed")
    else:
        trace = directory / "runs/run1/trace.jsonl"
        trace.write_text(trace.read_text().replace(
            "model output is not valid JSON", "schema mismatch"))
    with pytest.raises(RuntimeError):
        control.create_review("run1")
    assert not (root / "adjudications/run1.json").exists()


def test_resident_continuation_launches_only_never_started_frozen_atomic_child(
    rejected_model_json, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _, ledger, _ = rejected_model_json
    control.create_review("run1")
    saved = control.control_freeze()
    path = root / "queue-control-freeze-001.json"
    path.write_text(json.dumps(saved))
    monkeypatch.setattr(frozen, "reference", lambda: {})
    monkeypatch.setattr(frozen, "cell_config", lambda cell, run, reference, *, root: {
        "cell_id": cell.cell_id, "run_id": run})
    monkeypatch.setattr(frozen, "admit", lambda *args: {
        "disposition": "valid", "reason": "completed_or_valid_semantic_failure"})
    launches = []
    historical_ledger_class = frozen.AttemptLedger

    class Process:
        pid = 9999999

        def __init__(self, command: list[str], **kwargs: object) -> None:
            assert command[1] == str(Path(frozen.__file__).resolve())
            assert "--attempt" in command
            config = yaml.safe_load(Path(command[command.index("--config") + 1]).read_text())
            launches.append(config["cell_id"])
            assert kwargs["env"]["PYTHONPATH"] == os.pathsep.join(
                str(frozen.APP / folder) for folder in ("src", "scripts"))
            directory = Path(command[command.index("--output") + 1])
            private = directory / "private"
            private.mkdir()
            (private / "residency-validation.json").write_text('{"passed":true}')

        def wait(self) -> int:
            return 0

    monkeypatch.setattr(control.subprocess, "Popen", Process)
    control.run(path)
    assert launches == ["cell2"]
    assert frozen.AttemptLedger is historical_ledger_class  # No runtime-global monkeypatch.
    view = control.SnapshotAttemptLedger(ledger.path, ledger.cells, ledger.schedule_sha256)
    assert view.completed_cells == ("cell1", "cell2") and len(view.original_attempts) == 2
    assert (root / "phase1-queue-completed.json").is_file()


def test_resident_control_drift_and_unreviewed_findings_stop_before_launch(
    rejected_model_json, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _, _, _ = rejected_model_json
    monkeypatch.setattr(control.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("launch"))
    path = root / "queue-control-freeze-001.json"
    path.write_text(json.dumps(control.control_freeze()))
    with pytest.raises(RuntimeError, match="control/adjudication drift"):
        control.run(path)  # No exact sidecar, so no continuation.
    control.create_review("run1")
    saved = control.control_freeze()
    path.write_text(json.dumps(saved))
    review = root / "adjudications/run1.json"
    review.write_text(review.read_text() + "\n")
    with pytest.raises(RuntimeError, match="control/adjudication drift"):
        control.run(path)


def test_second_exact_review_replays_previously_adjudicated_original_journal(rejected_model_json):
    root, directory, ledger, receipt = rejected_model_json
    control.create_review("run1")
    view = control.SnapshotAttemptLedger(ledger.path, ledger.cells, ledger.schedule_sha256)
    view.reserve("cell2", "run2", "b" * 64)
    second = root / "evidence/cell2/attempt1"
    shutil.copytree(directory, second)
    (second / "runs/run1").rename(second / "runs/run2")
    (second / "process.json").write_text('{"pid":9999999,"run_id":"run2"}')
    view.settle("run2", "confounder", reviewer.GATE_PROBLEM, provenance_sha256(receipt))
    before = ledger.path.read_bytes()
    value = control.create_review("run2")
    assert value["confirmed_parse_failures"] == 1 and not value["rerun"]
    assert ledger.path.read_bytes() == before
    assert view.completed_cells == ("cell1", "cell2")
