"""New operational view must never replay through the immutable old ledger."""

from __future__ import annotations

import copy
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
queue = importlib.import_module("large_scale_resident_timeout_queue_v1")


@pytest.mark.parametrize("damage", [None, "parent_hash", "source", "proof", "E_scope"])
def test_timeout_parent_reproduces_exact_history_without_legacy_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str | None,
) -> None:
    parent = {"execution_epochs_sha256": {"4": queue.e.EXECUTION_SHA256}}
    (tmp_path / "queue-control-freeze-011.json").write_text(json.dumps(parent))
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(queue.previous, "PARENT_SHA256", queue.frozen.sha256(
        tmp_path / "queue-control-freeze-011.json"))
    proof = tmp_path / queue.previous.reviewer.DIRECTORY / "old-projection.json"
    proof.parent.mkdir()
    proof.write_text("{}")
    old = {**parent, "version": "resident-body-preserving-projection-control-v2",
           "parent_control_file_sha256": queue.previous.PARENT_SHA256,
           "parent_controller_source_sha256": queue.frozen.sha256(Path(queue.e.__file__)),
           "controller_source_sha256": queue.frozen.sha256(Path(queue.previous.__file__)),
           "projection_reviewer_source_sha256": queue.frozen.sha256(
               Path(queue.previous.reviewer.__file__)),
           "projected_record_adjudications": {proof.name: queue.frozen.sha256(proof)},
           "measured_execution_changed": False, "semantic_retries": False}
    path = tmp_path / queue.PARENT_FILE
    path.write_text(json.dumps(old))
    monkeypatch.setattr(queue, "PARENT_SHA256", queue.frozen.sha256(path))
    monkeypatch.setattr(queue.previous, "control_freeze",
                        lambda: pytest.fail("obsolete ledger must not replay expanded journal"))
    monkeypatch.setattr(queue.previous, "historical_control", lambda: parent)
    if damage == "parent_hash":
        path.write_text("{}")
    elif damage == "source":
        old["controller_source_sha256"] = "b" * 64
        path.write_text(json.dumps(old))
        monkeypatch.setattr(queue, "PARENT_SHA256", queue.frozen.sha256(path))
    elif damage == "proof":
        proof.write_text("drift")
    elif damage == "E_scope":
        monkeypatch.setattr(queue.previous, "historical_control", lambda: {})
    if damage:
        with pytest.raises(RuntimeError):
            queue.historical_control()
    else:
        assert queue.historical_control() == old


@pytest.mark.parametrize("damage", [None, "no_proof", "unsettled",
                                    "valid_semantic", "wrong_reason"])
def test_new_control_accepts_only_independently_proven_operational_membership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str | None,
) -> None:
    parent = {"measured_execution_changed": False, "semantic_retries": False}
    path = tmp_path / queue.reviewer.TIMEOUT_DIRECTORY / "timeout.json"
    path.parent.mkdir()
    path.write_text("{}")
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(queue, "historical_control", lambda: parent)
    attempt = SimpleNamespace(run_id="timeout", disposition="operational_excluded",
                              reason=queue.reviewer.REASON)
    monkeypatch.setattr(queue, "owned_ledger", lambda: SimpleNamespace(attempts=(attempt,)))
    if damage == "no_proof":
        path.unlink()
    elif damage == "unsettled":
        attempt.disposition = None
    elif damage == "valid_semantic":
        attempt.disposition = "valid"
    elif damage == "wrong_reason":
        attempt.reason = "poor_stopping"
    if damage:
        with pytest.raises(RuntimeError):
            queue.control_freeze()
    else:
        value = queue.control_freeze()
        assert value["compound_cloud_timeout_adjudications"] == {
            path.name: queue.frozen.sha256(path)}
        assert value["measured_execution_changed"] is False
        assert value["semantic_retries"] is False
        assert value["max_operational_replacements_per_cell"] == 1


def test_control_drift_stops_before_new_cell_or_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(queue.frozen, "require_remote", lambda: None)
    monkeypatch.setattr(queue, "control_freeze", lambda: {"frozen": True})
    path = tmp_path / "queue-control-freeze-014.json"
    path.write_text('{"frozen":false}')
    monkeypatch.setattr(queue, "owned_ledger", lambda: pytest.fail("must not open ledger"))
    with pytest.raises(RuntimeError, match="drift"):
        queue.run(path)
    assert not (tmp_path / "phase1-attempts.jsonl").exists()


@pytest.mark.parametrize("journal_advanced", [False, True])
def test_timeout_projection_keeps_unknown_quality_and_checks_final_journal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, journal_advanced: bool,
) -> None:
    collector = importlib.import_module("large_scale_resident_timeout_snapshot_v1")
    path = tmp_path / collector.reviewer.TIMEOUT_DIRECTORY / "timeout.json"
    path.parent.mkdir()
    proof = {"record_field_proof": [{"action_id": "bad"}],
             "timeout_proof": {"http_status": None, "timeout_origin": None}}
    path.write_text(json.dumps(proof))
    journal = tmp_path / "phase1-attempts.jsonl"
    journal.write_text("initial")
    initial = {"rows": [{"attempts": [{"run_id": "timeout", "benchmark_score": None,
                                         "disposition": "operational_excluded"}]}],
               "collector_source_sha256": {}, "journal_sha256": collector.resident.sha256(journal)}

    def collect(*args, **kwargs):
        assert kwargs["audit_view"] is collector.reviewer
        if journal_advanced:
            journal.write_text("advanced")
        return copy.deepcopy(initial)

    monkeypatch.setattr(collector.previous.core, "collect", collect)
    if journal_advanced:
        with pytest.raises(RuntimeError, match="journal advanced"):
            collector.collect(tmp_path, tmp_path)
    else:
        value = collector.collect(tmp_path, tmp_path)
        attempt = value["rows"][0]["attempts"][0]
        assert attempt["benchmark_score"] is None
        assert attempt["benchmark_quality_unknown"] is True
        assert attempt["confirmed_absent_field_failures"] == 1
        assert attempt["original_rejection_preserved"] is True
        assert value["version"] == "resident-four-epoch-exact-compound-cloud-timeout-v1"
