import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from test_large_scale_adjudication import fixture as json_fixture

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import AttemptLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
reviewer = importlib.import_module("large_scale_provider_policy_review_v1")
controller = importlib.import_module("large_scale_classified_queue_v1")


def original() -> dict:
    return {"disposition": "confounder", "reason": reviewer.GATE,
            "problems": [reviewer.GATE], "operational_incidents": [],
            "execution_completed": False, "original_evaluation": None,
            "terminal_failure": {"code": "logical_loop_failed",
                                 "message": "HTTP400 data_inspection_failed"}}


def api_fixture(path: Path) -> None:
    path.mkdir(parents=True)
    for call, role, status in (("ok", "manager", 200), ("blocked1", "specialist", 400),
                               ("blocked2", "verifier", 400)):
        request = {"model": "qwen3.8-max", "messages": [{"content": "PRIVATE-TASK-BODY"}]}
        response = {"usage": {"input_tokens": 10}} if status == 200 else {
            "error": {"code": "data_inspection_failed", "type": "data_inspection_failed",
                      "message": "Input text data may contain inappropriate content."}}
        usage = {"call_id": call, "recipient": role, "requested_model": "qwen3.8-max",
                 "status": status, "usage": response.get("usage")}
        for suffix, value in (("request", request), ("response", response), ("usage", usage)):
            (path / f"{call}-{suffix}.json").write_text(json.dumps(value))


def test_exact_policy_is_unknown_quality_not_semantic_zero_or_retry(tmp_path: Path) -> None:
    api_fixture(tmp_path / "api")
    receipt = original()
    before = json.dumps(receipt)
    value = reviewer.review_policy(receipt, tmp_path / "api")
    assert len(value["proof"]) == 2
    assert value["reviewed_admission"]["failure_class"] == "provider_input_policy"
    assert value["reviewed_admission"]["original_evaluation"] is None
    assert not value["reviewed_admission"]["replacement_authorized"]
    assert all(x["failed_call_usage"] is None for x in value["proof"])
    assert "PRIVATE" not in json.dumps(value)
    assert json.dumps(receipt) == before


@pytest.mark.parametrize("damage", ["privacy", "outage", "evaluated", "complete", "terminal",
                                     "schema", "quota", "status", "missing", "no-refusal"])
def test_policy_is_not_generic_400_outage_or_leakage_waiver(tmp_path: Path, damage: str) -> None:
    api = tmp_path / "api"
    api_fixture(api)
    receipt = original()
    if damage == "privacy":
        receipt["problems"].append("actual_recipient_privacy_or_method_leakage")
    elif damage == "outage":
        receipt["operational_incidents"] = ["provider_outage"]
    elif damage == "evaluated":
        receipt["original_evaluation"] = {"benchmark_score": 0}
    elif damage == "complete":
        receipt["execution_completed"] = True
    elif damage == "terminal":
        receipt["terminal_failure"]["message"] = "different SDK fault"
    elif damage in {"schema", "quota"}:
        value = json.loads((api / "blocked1-response.json").read_text())
        value["error"]["code"] = "invalid_parameter" if damage == "schema" else "insufficient_quota"
        (api / "blocked1-response.json").write_text(json.dumps(value))
    elif damage == "status":
        value = json.loads((api / "blocked1-usage.json").read_text())
        value["status"] = 503
        (api / "blocked1-usage.json").write_text(json.dumps(value))
    elif damage == "missing":
        (api / "blocked1-response.json").unlink()
    else:
        for path in api.glob("*-usage.json"):
            value = json.loads(path.read_text())
            value["status"] = 200
            path.write_text(json.dumps(value))
    with pytest.raises(RuntimeError):
        reviewer.review_policy(receipt, api)


def policy_fixture(tmp_path: Path) -> tuple[Path, AttemptLedger, Path, Path]:
    first, ledger, _ = json_fixture(tmp_path, ("cell1", "cell2", "cell3"))
    view = controller.ClassifiedQueueView(ledger.path, ledger.cells, ledger.schedule_sha256)
    view.reserve("cell2", "run2", "b" * 64)
    directory = tmp_path / "evidence/cell2/attempt1"
    api_fixture(directory / "private/api")
    receipt = original()
    (directory / "admission.json").write_text(json.dumps(receipt))
    view.settle("run2", "confounder", reviewer.GATE, provenance_sha256(receipt))
    review = reviewer.review_policy(receipt, directory / "private/api")
    value = {"run_id": "run2", "original_admission_sha256": provenance_sha256(receipt),
             "original_execution_sha256": "b" * 64,
             "reviewer_source_sha256": reviewer.sha256(Path(reviewer.__file__)),
             "original_evidence_file_sha256": {str(p.relative_to(directory)): reviewer.sha256(p)
                                                for p in directory.rglob("*") if p.is_file()},
             **review, "reviewed_admission_sha256": provenance_sha256(review["reviewed_admission"])}
    sidecar = tmp_path / reviewer.POLICY_DIRECTORY / "run2.json"
    sidecar.parent.mkdir()
    sidecar.write_text(json.dumps(value))
    return sidecar, ledger, directory, first


def test_mixed_exact_reviews_preserve_original_history_and_disallow_replacement(
    tmp_path: Path,
) -> None:
    _, ledger, directory, first = policy_fixture(tmp_path)
    preserved = (ledger.path.read_bytes(), first.read_bytes(),
                 (directory / "admission.json").read_bytes())
    view = controller.ClassifiedQueueView(ledger.path, ledger.cells, ledger.schedule_sha256)
    assert view.completed_cells == ("cell1", "cell2")
    assert all(x.disposition == "confounder" for x in view.original_attempts)
    assert reviewer.effective_admission(tmp_path, view.attempts[1])["original_evaluation"] is None
    assert reviewer.effective_admission(tmp_path, view.attempts[0])["original_evaluation"]
    assert preserved == (ledger.path.read_bytes(), first.read_bytes(),
                         (directory / "admission.json").read_bytes())
    with pytest.raises(RuntimeError, match="must not be repeated"):
        view.reserve("cell2", "policy-retry-forbidden", "b" * 64)
    view.reserve("cell3", "run3", "b" * 64)
    reloaded = controller.ClassifiedQueueView(ledger.path, ledger.cells, ledger.schedule_sha256)
    assert reloaded.pending[0].run_id == "run3"
    assert first.read_bytes() == preserved[1]


@pytest.mark.parametrize("damage", ["proof", "source", "original", "evidence", "extra-file"])
def test_policy_proof_tamper_invalidates_even_cached_completion(
    tmp_path: Path, damage: str,
) -> None:
    sidecar, ledger, directory, _ = policy_fixture(tmp_path)
    view = controller.ClassifiedQueueView(ledger.path, ledger.cells, ledger.schedule_sha256)
    assert view.completed_cells == ("cell1", "cell2")
    value = json.loads(sidecar.read_text())
    if damage == "proof":
        value["proof"][0]["http_status"] = 200
    elif damage == "source":
        value["reviewer_source_sha256"] = "c" * 64
    elif damage == "original":
        value["original_admission_sha256"] = "c" * 64
    elif damage == "evidence":
        (directory / "private/api/blocked1-request.json").write_text("changed")
    else:
        (directory / "extra.json").write_text("{}")
    sidecar.write_text(json.dumps(value))
    with pytest.raises(RuntimeError):
        _ = view.completed_cells


def test_classified_queue_launches_only_next_unstarted_cell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, ledger, _, _ = policy_fixture(tmp_path)
    queue = importlib.import_module("large_scale_queue_v1")
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
    freeze = {"provider_policy_receipts": {"run2.json": "digest"}}
    monkeypatch.setattr(controller, "control_freeze", lambda: freeze)
    path = tmp_path / "queue-control-freeze-004.json"
    path.write_text(json.dumps(freeze))
    controller.run(path)
    assert launches == ["cell3"]
    updated = controller.ClassifiedQueueView(ledger.path, ledger.cells, ledger.schedule_sha256)
    assert updated.completed_cells == ("cell1", "cell2", "cell3")
    assert updated.attempts[1].reason == reviewer.REASON


def test_classified_control_freeze_drift_prevents_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(controller, "ROOT", tmp_path)
    monkeypatch.setattr(controller, "control_freeze", lambda: {
        "provider_policy_receipts": {"run2.json": "new"}})
    path = tmp_path / "queue-control-freeze-004.json"
    path.write_text('{"provider_policy_receipts":{"run2.json":"old"}}')
    with pytest.raises(RuntimeError, match="provenance drift"):
        controller.run(path)
