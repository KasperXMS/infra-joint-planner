"""Parent scope remains immutable; a classified policy failure must be skipped."""

from __future__ import annotations

import copy
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
queue = importlib.import_module("large_scale_resident_field_policy_queue_v1")


@pytest.mark.parametrize("damage", [None, "parent_hash", "source", "proof", "old_scope"])
def test_parent_timeout_control_is_reproduced_without_obsolete_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str | None,
) -> None:
    parent = {"execution_epochs_sha256": {"4": queue.e.EXECUTION_SHA256},
              "projected_record_adjudications": {"old.json": "a" * 64}}
    proof = tmp_path / queue.previous.reviewer.TIMEOUT_DIRECTORY / "timeout.json"
    proof.parent.mkdir()
    proof.write_text("{}")
    old = {**parent, "version": "resident-exact-compound-cloud-timeout-control-v1",
           "parent_control_file_sha256": queue.previous.PARENT_SHA256,
           "parent_controller_source_sha256": queue.frozen.sha256(
               Path(queue.previous.previous.__file__)),
           "controller_source_sha256": queue.frozen.sha256(Path(queue.previous.__file__)),
           "timeout_reviewer_source_sha256": queue.frozen.sha256(
               Path(queue.previous.reviewer.__file__)),
           "compound_cloud_timeout_adjudications": {proof.name: queue.frozen.sha256(proof)},
           "operational_replacement_requires_identical_execution": True,
           "max_operational_replacements_per_cell": 1}
    path = tmp_path / queue.PARENT_FILE
    path.write_text(json.dumps(old))
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(queue, "PARENT_SHA256", queue.frozen.sha256(path))
    monkeypatch.setattr(queue.previous, "historical_control", lambda: parent)
    monkeypatch.setattr(queue.previous, "control_freeze",
                        lambda: pytest.fail("obsolete admission view must not replay journal"))
    if damage == "parent_hash":
        path.write_text("{}")
    elif damage == "source":
        old["controller_source_sha256"] = "b" * 64
        path.write_text(json.dumps(old))
        monkeypatch.setattr(queue, "PARENT_SHA256", queue.frozen.sha256(path))
    elif damage == "proof":
        proof.write_text("drift")
    elif damage == "old_scope":
        monkeypatch.setattr(queue.previous, "historical_control", lambda: {})
    if damage:
        with pytest.raises(RuntimeError):
            queue.historical_control()
    else:
        assert queue.historical_control() == old


@pytest.mark.parametrize("damage", [None, "missing", "operational", "unsettled", "wrong_reason"])
def test_control_requires_exact_classified_nominal_failure_without_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str | None,
) -> None:
    parent = {"measured_execution_changed": False, "semantic_retries": False}
    proof = tmp_path / queue.reviewer.POLICY_DIRECTORY / "classified.json"
    proof.parent.mkdir()
    proof.write_text("{}")
    attempt = SimpleNamespace(run_id="classified", disposition="valid",
                              reason=queue.reviewer.REASON)
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(queue, "historical_control", lambda: parent)
    monkeypatch.setattr(queue, "owned_ledger", lambda: SimpleNamespace(attempts=(attempt,)))
    if damage == "missing":
        proof.unlink()
    elif damage == "operational":
        attempt.disposition = "operational_excluded"
    elif damage == "unsettled":
        attempt.disposition = None
    elif damage == "wrong_reason":
        attempt.reason = "unknown"
    if damage:
        with pytest.raises(RuntimeError):
            queue.control_freeze()
    else:
        value = queue.control_freeze()
        assert value["compound_record_policy_adjudications"] == {
            proof.name: queue.frozen.sha256(proof)}
        assert value["provider_policy_retry"] is False
        assert value["input_censored"] is False
        assert value["measured_execution_changed"] is False


def test_control_drift_stops_before_reservation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(queue.frozen, "require_remote", lambda: None)
    monkeypatch.setattr(queue, "control_freeze", lambda: {"frozen": True})
    path = tmp_path / "queue-control-freeze-015.json"
    path.write_text('{"frozen":false}')
    monkeypatch.setattr(queue, "owned_ledger", lambda: pytest.fail("must not open ledger"))
    with pytest.raises(RuntimeError, match="drift"):
        queue.run(path)


def test_queue_skips_classified_policy_failure_and_starts_only_original_next_cell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    saved = {"atomic_execution_entrypoint": "/immutable/atomic.py"}
    path = tmp_path / "queue-control-freeze-015.json"
    path.write_text(json.dumps(saved))
    (tmp_path / "cell-configs").mkdir()
    (tmp_path / queue.e.AUTHORIZATION).write_text('{"affected_original_runs":[]}')
    calls = []
    attempt = SimpleNamespace(cell_id="classified", run_id="classified-run",
                              disposition="valid", reason=queue.reviewer.REASON)
    ledger = SimpleNamespace(pending=(), attempts=(attempt,), completed_cells=("classified",))

    def reserve(cell, run, execution):
        assert cell == "next"
        assert execution == queue.e.EXECUTION_SHA256
        calls.append((cell, run))

    def settle(*args):
        assert args[1] == "valid"
        ledger.completed_cells = ("classified", "next")

    ledger.reserve, ledger.settle = reserve, settle
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(queue.frozen, "require_remote", lambda: None)
    monkeypatch.setattr(queue.frozen, "APP", tmp_path / "immutable-app")
    monkeypatch.setattr(queue, "control_freeze", lambda: saved)
    monkeypatch.setattr(queue, "owned_ledger", lambda: ledger)
    monkeypatch.setattr(queue.frozen, "schedule", lambda: (
        SimpleNamespace(cell_id="classified", method="E"),
        SimpleNamespace(cell_id="next", method="A")))
    monkeypatch.setattr(queue.frozen, "schedule_sha256", lambda _: "a" * 64)
    monkeypatch.setattr(queue.frozen, "verified_prices", lambda *_: ({}, None))
    monkeypatch.setattr(queue.frozen, "reference", lambda: {})
    monkeypatch.setattr(queue.frozen, "cell_config",
                        lambda _, run, *args, **kwargs: {"run_id": run})
    monkeypatch.setattr(queue.e, "historical_repairs", lambda _: {})

    def write_new(destination, value):
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x") as stream:
            json.dump(value, stream)

    monkeypatch.setattr(queue.frozen, "write_new", write_new)

    def spawn(command, *, stdout, stderr, env):
        assert command[1] == saved["atomic_execution_entrypoint"]
        assert env["PYTHONPATH"].split(queue.os.pathsep) == [
            str(queue.frozen.APP / "src"), str(queue.frozen.APP / "scripts")]
        directory = Path(stdout.name).parent
        write_new(directory / "private/residency-validation.json", {"passed": True})
        return SimpleNamespace(pid=123, wait=lambda: 0)

    monkeypatch.setattr(queue.subprocess, "Popen", spawn)
    monkeypatch.setattr(queue.previous.previous.quote, "admission", lambda *_: {
        "disposition": "valid", "reason": "ordinary_outcome", "problems": []})
    queue.run(path)
    assert len(calls) == 1
    assert not (tmp_path / "evidence/classified").exists()
    assert (tmp_path / "phase1-queue-completed.json").exists()


@pytest.mark.parametrize("journal_advanced", [False, True])
def test_projection_retains_both_operational_and_nominal_unknown_quality(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, journal_advanced: bool,
) -> None:
    collector = importlib.import_module("large_scale_resident_field_policy_snapshot_v1")
    for name, folder in (("timeout", collector.reviewer.previous.TIMEOUT_DIRECTORY),
                         ("policy", collector.reviewer.POLICY_DIRECTORY)):
        path = tmp_path / folder / (name + ".json")
        path.parent.mkdir()
        path.write_text(json.dumps({"record_field_proof": ["bounded-proof"],
                                    "provider_policy_proof": ["specialist", "verifier"]}))
    journal = tmp_path / "phase1-attempts.jsonl"
    journal.write_text("initial")
    value = {"rows": [{"attempts": [{"run_id": n, "benchmark_score": None}
                                   for n in ("timeout", "policy")]}],
             "collector_source_sha256": {}, "journal_sha256": collector.resident.sha256(journal)}

    def collect(*args, **kwargs):
        assert kwargs["audit_view"] is collector.reviewer
        if journal_advanced:
            journal.write_text("advanced")
        return copy.deepcopy(value)

    monkeypatch.setattr(collector.previous.previous.core, "collect", collect)
    if journal_advanced:
        with pytest.raises(RuntimeError, match="journal advanced"):
            collector.collect(tmp_path, tmp_path)
    else:
        result = collector.collect(tmp_path, tmp_path)
        attempts = result["rows"][0]["attempts"]
        assert all(a["benchmark_score"] is None for a in attempts)
        assert all(a["benchmark_quality_unknown"] for a in attempts)
        assert attempts[1]["confirmed_provider_policy_refusals"] == 2
