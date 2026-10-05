import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from test_large_scale_adjudication import events as json_events
from test_large_scale_adjudication import fixture as json_fixture
from test_large_scale_provider_policy_review import api_fixture
from test_large_scale_provider_policy_review import original as policy_original

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import AttemptLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
review = importlib.import_module("large_scale_compound_review_v1")
control = importlib.import_module("large_scale_compound_queue_v1")


def original() -> dict:
    return {"disposition": "confounder", "reason": review.GATES[0],
            "problems": list(review.GATES), "operational_incidents": [],
            "execution_completed": False, "original_evaluation": None,
            "terminal_failure": {"code": "logical_loop_failed",
                                 "message": "HTTP400 data_inspection_failed"}}


def test_both_exact_proofs_required_without_changing_original_or_old_reviewers(
    tmp_path: Path,
) -> None:
    api_fixture(tmp_path / "api")
    receipt, trace = original(), json_events()
    before = json.dumps((receipt, trace))
    value = review.review_compound(receipt, trace, tmp_path / "api")
    assert value["covered_original_findings"] == list(review.GATES)
    assert len(value["model_json_proof"]) == 1
    assert len(value["provider_policy_proof"]) == 2
    assert value["reviewed_admission"]["original_evaluation"] is None
    assert not value["reviewed_admission"]["replacement_authorized"]
    assert "PRIVATE" not in json.dumps(value)
    assert json.dumps((receipt, trace)) == before
    with pytest.raises(RuntimeError):
        review.model_review.review_model_json_failures(receipt, trace)
    with pytest.raises(RuntimeError):
        review.policy_review.review_policy(receipt, tmp_path / "api")


@pytest.mark.parametrize("damage", ["extra", "single", "duplicates", "outage", "evaluated",
                                     "completed", "terminal", "no-json", "not-model", "stage",
                                     "message", "output", "policy-status", "quota", "missing"])
def test_no_partial_gate_waiver_or_unrelated_failure_admission(
    tmp_path: Path, damage: str,
) -> None:
    api_fixture(tmp_path / "api")
    receipt, trace = original(), json_events()
    if damage == "extra":
        receipt["problems"].append("privacy_violation")
    elif damage == "single":
        receipt["problems"].pop()
    elif damage == "duplicates":
        receipt["problems"].append(receipt["problems"][0])
    elif damage == "outage":
        receipt["operational_incidents"] = ["provider_outage"]
    elif damage == "evaluated":
        receipt["original_evaluation"] = {"benchmark_score": 0}
    elif damage == "completed":
        receipt["execution_completed"] = True
    elif damage == "terminal":
        receipt["terminal_failure"]["message"] = "SDK/context fault"
    elif damage == "no-json":
        trace = []
    elif damage == "not-model":
        trace[0]["payload"]["action"]["action_type"] = "tool"
    elif damage == "stage":
        trace[2]["payload"]["failure"]["stage"] = "selection"
    elif damage == "message":
        trace[1]["payload"]["failure_message"] = "wrong-schema"
    elif damage == "output":
        trace[0]["payload"]["action"]["outputs"][0]["media_type"] = "text/plain"
    elif damage == "policy-status":
        path = tmp_path / "api/blocked1-usage.json"
        data = json.loads(path.read_text())
        data["status"] = 503
        path.write_text(json.dumps(data))
    elif damage == "quota":
        path = tmp_path / "api/blocked1-response.json"
        data = json.loads(path.read_text())
        data["error"]["code"] = "insufficient_quota"
        path.write_text(json.dumps(data))
    else:
        (tmp_path / "api/blocked1-response.json").unlink()
    with pytest.raises(RuntimeError):
        review.review_compound(receipt, trace, tmp_path / "api")


def compound_fixture(
    tmp_path: Path, cells: tuple[str, ...] = ("cell1", "cell2", "cell3", "cell4"),
) -> tuple[Path, AttemptLedger, Path, Path, Path]:
    first, ledger, _ = json_fixture(tmp_path, cells)
    view = control.CompoundQueueView(ledger.path, ledger.cells, ledger.schedule_sha256)
    view.reserve("cell2", "run2", "b" * 64)
    directory = tmp_path / "evidence/cell2/attempt1"
    api_fixture(directory / "private/api")
    receipt = policy_original()
    (directory / "admission.json").write_text(json.dumps(receipt))
    view.settle("run2", "confounder", review.policy_review.GATE, provenance_sha256(receipt))
    proof = review.policy_review.review_policy(receipt, directory / "private/api")
    value = {"run_id": "run2", "original_admission_sha256": provenance_sha256(receipt),
             "original_execution_sha256": "b" * 64,
             "reviewer_source_sha256": review.sha256(Path(review.policy_review.__file__)),
             "original_evidence_file_sha256": {str(p.relative_to(directory)): review.sha256(p)
                for p in directory.rglob("*") if p.is_file()}, **proof,
             "reviewed_admission_sha256": provenance_sha256(proof["reviewed_admission"])}
    policy = tmp_path / review.policy_review.POLICY_DIRECTORY / "run2.json"
    policy.parent.mkdir()
    policy.write_text(json.dumps(value))
    view.reserve("cell3", "run3", "b" * 64)
    directory = tmp_path / "evidence/cell3/attempt1"
    api_fixture(directory / "private/api")
    run = directory / "runs/run3"
    run.mkdir(parents=True)
    receipt = original()
    (directory / "admission.json").write_text(json.dumps(receipt))
    (run / "trace.jsonl").write_text("\n".join(json.dumps(e) for e in json_events()))
    view.settle("run3", "confounder", review.GATES[0], provenance_sha256(receipt))
    proof = review.review_compound(receipt, json_events(), directory / "private/api")
    worker = tmp_path / "app/src/infra_joint/worker/server.py"
    value = {"run_id": "run3", "original_admission_sha256": provenance_sha256(receipt),
             "original_execution_sha256": "b" * 64,
             "reviewer_sources_sha256": review.reviewer_sources(),
             "worker_source_sha256": review.sha256(worker),
             "original_evidence_file_sha256": {str(p.relative_to(directory)): review.sha256(p)
                for p in directory.rglob("*") if p.is_file()}, **proof,
             "reviewed_admission_sha256": provenance_sha256(proof["reviewed_admission"])}
    sidecar = tmp_path / review.DIRECTORY / "run3.json"
    sidecar.parent.mkdir()
    sidecar.write_text(json.dumps(value))
    return sidecar, ledger, directory, first, policy


def test_three_review_types_coexist_no_journal_rewrite_no_failure_replacement(
    tmp_path: Path,
) -> None:
    _, ledger, directory, first, policy = compound_fixture(tmp_path)
    preserved = [p.read_bytes() for p in (ledger.path, first, policy,
                                         directory / "admission.json")]
    view = control.CompoundQueueView(ledger.path, ledger.cells, ledger.schedule_sha256)
    assert view.completed_cells == ledger.cells[:3]
    assert all(a.disposition == "confounder" for a in view.original_attempts)
    assert view.attempts[-1].reason == review.REASON
    assert review.effective_admission(tmp_path, view.attempts[-1])["original_evaluation"] is None
    assert preserved == [p.read_bytes() for p in (ledger.path, first, policy,
                                                directory / "admission.json")]
    with pytest.raises(RuntimeError, match="must not be repeated"):
        view.reserve("cell3", "forbidden-replacement", "b" * 64)


def test_review_entry_membership_verifies_all_attempts_once_not_per_scheduled_cell(
    tmp_path: Path,
) -> None:
    _, ledger, _, _, _ = compound_fixture(tmp_path)

    class CountingLedger(review.CompoundAttemptLedger):
        proof_passes = 0

        @property
        def attempts(self):
            self.proof_passes += 1
            return super().attempts

    view = CountingLedger(ledger.path, ledger.cells, ledger.schedule_sha256)
    view.proof_passes = 0
    assert view.completed_cells == ledger.cells[:3]
    assert view.proof_passes == 1


@pytest.mark.parametrize("damage", ["proof-json", "proof-policy", "source", "original",
                                     "evidence", "extra-file", "worker", "coverage"])
def test_compound_sidecar_and_cache_fail_closed_on_tamper(tmp_path: Path, damage: str) -> None:
    sidecar, ledger, directory, _, _ = compound_fixture(tmp_path)
    view = control.CompoundQueueView(ledger.path, ledger.cells, ledger.schedule_sha256)
    assert view.completed_cells == ledger.cells[:3]
    value = json.loads(sidecar.read_text())
    if damage == "proof-json":
        value["model_json_proof"][0]["reached_model_inference"] = False
    elif damage == "proof-policy":
        value["provider_policy_proof"][0]["http_status"] = 200
    elif damage == "source":
        value["reviewer_sources_sha256"]["compound"] = "c" * 64
    elif damage == "original":
        value["original_admission_sha256"] = "c" * 64
    elif damage == "evidence":
        (directory / "private/api/blocked1-request.json").write_text("changed")
    elif damage == "extra-file":
        (directory / "extra.json").write_text("{}")
    elif damage == "worker":
        (tmp_path / "app/src/infra_joint/worker/server.py").write_text("changed")
    else:
        value["covered_original_findings"] = [review.policy_review.GATE]
    sidecar.write_text(json.dumps(value))
    with pytest.raises(RuntimeError):
        _ = view.completed_cells


def test_controller_launches_only_original_unstarted_cell_with_unchanged_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, ledger, _, _, _ = compound_fixture(tmp_path)
    # Real queue loop skips all three reviewed failures and launches only cell4.
    queue = importlib.import_module("large_scale_queue_v1")
    monkeypatch.setattr(control, "ROOT", tmp_path)
    monkeypatch.setattr(queue, "ROOT", tmp_path)
    monkeypatch.setattr(queue, "require_remote", lambda root: None)
    monkeypatch.setattr(review, "require_stopped", lambda *args, **kwargs: None)
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
        def __init__(self, command: list[str], **kwargs: object) -> None:
            config = yaml.safe_load(Path(command[command.index("--config") + 1]).read_text())
            launches.append(config["cell_id"])
            self.pid = 999

        def wait(self) -> int:
            return 0

    monkeypatch.setattr(queue.subprocess, "Popen", Process)
    monkeypatch.setattr(queue, "admit", lambda *args: {
        "disposition": "valid", "reason": "completed_or_valid_semantic_failure"})
    freeze = {"compound_review_receipts": {"run3.json": "bound"}}
    monkeypatch.setattr(control, "control_value", lambda: freeze)
    path = tmp_path / "queue-control-freeze-006.json"
    path.write_text(json.dumps(freeze))
    control.run(path)
    assert launches == ["cell4"]
    assert json.loads((tmp_path / "phase1-queue-completed.json").read_text())["completed_cells"]
    assert queue.AttemptLedger is control.CompoundQueueView


def test_controller_drift_prevents_any_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = importlib.import_module("large_scale_queue_v1")
    monkeypatch.setattr(control, "ROOT", tmp_path)
    monkeypatch.setattr(queue, "require_remote", lambda root: None)
    monkeypatch.setattr(control, "control_value", lambda: {
        "compound_review_receipts": {"run3.json": "new"}})
    path = tmp_path / "queue-control-freeze-006.json"
    path.write_text('{"compound_review_receipts":{"run3.json":"old"}}')
    with pytest.raises(RuntimeError, match="provenance drift"):
        control.run(path)


def test_compound_snapshot_preserves_unknown_quality_and_failed_inference_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    sidecar, _, _, _, _ = compound_fixture(tmp_path)
    collector = importlib.import_module("large_scale_compound_snapshot_v1")
    ledger_before = collector.base.SnapshotAttemptLedger
    admission_before = collector.base.effective_admission
    raw = {"rows": [{"attempts": [{"run_id": "run3", "admission_reason": review.REASON,
                                   "benchmark_score": None, "telemetry": None,
                                   "post_inference_failed_service_tokens": 0}]}]}
    monkeypatch.setattr(collector.base, "snapshot", lambda root: raw)
    result = collector.snapshot(tmp_path)
    attempt = result["rows"][0]["attempts"][0]
    assert result["compound_adjudicated_attempts"] == 1
    assert attempt["benchmark_score"] is None
    assert attempt["telemetry"] is None
    assert attempt["confirmed_post_inference_json_failures"] == 1
    assert attempt["post_inference_failed_service_tokens"] is None
    assert attempt["provider_policy_failure"]
    assert attempt["compound_adjudication_sha256"] == provenance_sha256(
        json.loads(sidecar.read_text()))
    assert collector.base.SnapshotAttemptLedger is ledger_before
    assert collector.base.effective_admission is admission_before


def test_compound_projection_restores_base_even_if_audit_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    collector = importlib.import_module("large_scale_compound_snapshot_v1")
    ledger_before = collector.base.SnapshotAttemptLedger
    admission_before = collector.base.effective_admission

    def fail(root: Path) -> None:
        raise RuntimeError("original evidence drift")

    monkeypatch.setattr(collector.base, "snapshot", fail)
    with pytest.raises(RuntimeError, match="evidence drift"):
        collector.snapshot(tmp_path)
    assert collector.base.SnapshotAttemptLedger is ledger_before
    assert collector.base.effective_admission is admission_before


@pytest.mark.parametrize("state", ["live", "absent", "own-audit"])
def test_actual_owned_process_not_observation_timeout_controls_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str,
) -> None:
    (tmp_path / "queue-process-006.json").write_text('{"pid": 12345}')
    cmdline = tmp_path / "proc-cmdline"
    if state != "absent":
        cmdline.write_bytes(tmp_path.name.encode() + b" --queue")
    monkeypatch.setattr(review, "Path", lambda value: cmdline)
    if state == "live":
        with pytest.raises(RuntimeError, match="still live"):
            review.require_stopped(tmp_path)
    else:
        review.require_stopped(tmp_path, ignore_pid=12345 if state == "own-audit" else None)


def test_new_control_freeze_preserves_parent_and_exact_component_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = importlib.import_module("large_scale_transport_control_v1")
    saved = {"execution_sha256": "b" * 64, "unchanged_parent": True}
    path = tmp_path / "queue-control-freeze-005.json"
    path.write_text(json.dumps(saved))
    monkeypatch.setattr(control, "ROOT", tmp_path)
    monkeypatch.setattr(control, "PARENT_CONTROL", provenance_sha256(saved))
    monkeypatch.setattr(parent, "control_value", lambda: saved)
    before = path.read_bytes()
    value = control.control_value()
    assert value["parent_control_sha256"] == provenance_sha256(saved)
    assert value["execution_sha256"] == saved["execution_sha256"]
    assert value["reviewer_sources_sha256"] == review.reviewer_sources()
    assert not value["formal_execution_changed"]
    assert not value["replacement_authorized"]
    assert path.read_bytes() == before
    monkeypatch.setattr(parent, "control_value", lambda: {**saved, "changed": True})
    with pytest.raises(RuntimeError, match="parent transport control drift"):
        control.control_value()
