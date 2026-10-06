"""Exact expanded proof scope does not rewrite historical control or rerun outcomes."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from infra_joint.control.provenance import provenance_sha256

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
queue = importlib.import_module("large_scale_resident_record_continuation_queue_v1")


@pytest.mark.parametrize("damage", [None, "receipt", "source", "dependency", "proof",
                                    "authorization", "parent", "epoch", "execution"])
def test_pinned_history_and_new_proofs_have_distinct_scope(tmp_path, monkeypatch, damage):
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(queue.reviewer.methods, "APPS", ("immutable-app",))
    parent = {key: queue.source_sha256(name) for key, name in queue.SOURCE_KEYS.items()}
    parent["ledger_dependency_sources_sha256"] = {
        "large_scale_resident_record_review_v1": queue.source_sha256(
            "large_scale_resident_record_review_v1")}
    for key, folder in queue.PROOF_FOLDERS.items():
        path = tmp_path / folder / "original.json"
        path.parent.mkdir()
        path.write_text("{}")
        name = "original" if key == "E_query_contract_adjudications" else path.name
        parent[key] = {name: queue.frozen.sha256(path)}
    source = tmp_path / "immutable-app/source.py"
    source.parent.mkdir()
    source.write_text("immutable")
    freeze = {"source_sha256": {"source.py": queue.frozen.sha256(source)}}
    freeze_path = tmp_path / "execution-freeze-001.json"
    freeze_path.write_text(json.dumps(freeze))
    parent["execution_epochs_sha256"] = {"1": provenance_sha256(freeze)}
    for file, key in ((queue.previous.PARENT_FILE, "parent_control_file_sha256"),
                      (queue.e.AUTHORIZATION, "repair_authorization_file_sha256")):
        path = tmp_path / file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}")
        parent[key] = queue.frozen.sha256(path)
    historical = tmp_path / queue.PARENT_FILE
    historical.write_text(json.dumps(parent))
    monkeypatch.setattr(queue, "PARENT_SHA256", queue.frozen.sha256(historical))
    monkeypatch.setattr(queue.previous, "historical_control",
                        lambda: pytest.fail("expanded folders must not recompute old history"))
    new = tmp_path / queue.reviewer.methods.RECORD_DIRECTORY / "later.json"
    new.write_text('{"later":true}')
    if damage == "receipt":
        historical.write_text("drift")
    elif damage in {"source", "dependency"}:
        if damage == "source":
            parent["controller_source_sha256"] = "b" * 64
        else:
            parent["ledger_dependency_sources_sha256"] = {
                "large_scale_resident_record_review_v1": "b" * 64}
        historical.write_text(json.dumps(parent))
        monkeypatch.setattr(queue, "PARENT_SHA256", queue.frozen.sha256(historical))
    elif damage == "proof":
        (new.parent / "original.json").write_text("drift")
    elif damage == "authorization":
        (tmp_path / queue.e.AUTHORIZATION).write_text("drift")
    elif damage == "parent":
        (tmp_path / queue.previous.PARENT_FILE).write_text("drift")
    elif damage == "epoch":
        freeze_path.write_text("{}")
    elif damage == "execution":
        source.write_text("drift")
    if damage:
        with pytest.raises(RuntimeError):
            queue.historical_control()
    else:
        assert queue.historical_control() == parent
        assert new.name not in parent["source_bound_record_adjudications"]


@pytest.mark.parametrize("damage", [None, "no_new", "unsettled", "excluded", "wrong_reason"])
def test_only_reproduced_nominal_record_proof_enters_new_control(tmp_path, monkeypatch, damage):
    parent = {"source_bound_record_adjudications": {}, "semantic_retries": False}
    path = tmp_path / queue.reviewer.methods.RECORD_DIRECTORY / "recovered.json"
    path.parent.mkdir()
    path.write_text("{}")
    attempt = SimpleNamespace(run_id=path.stem, disposition="valid",
                              reason=queue.reviewer.records.REASON)
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(queue, "historical_control", lambda: parent)
    monkeypatch.setattr(queue, "owned_ledger", lambda: SimpleNamespace(attempts=(attempt,)))
    if damage == "no_new":
        parent["source_bound_record_adjudications"][path.name] = queue.frozen.sha256(path)
    elif damage == "unsettled":
        attempt.disposition = None
    elif damage == "excluded":
        attempt.disposition = "operational_excluded"
    elif damage == "wrong_reason":
        attempt.reason = "unknown"
    if damage:
        with pytest.raises(RuntimeError):
            queue.control_freeze()
    else:
        value = queue.control_freeze()
        assert value["source_bound_record_adjudications"] == {}
        assert value["current_source_bound_record_adjudications"] == {
            path.name: queue.frozen.sha256(path)}
        assert value["parent_proof_scope_preserved"]
        assert value["nominal_retries"] is False
        assert value["measured_execution_changed"] is False


def test_live_guard_precedes_control_reads_or_reservation(tmp_path, monkeypatch):
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(queue.frozen, "require_remote", lambda: None)

    def active(_):
        raise RuntimeError("live queue")

    monkeypatch.setattr(queue.e, "assert_inactive", active)
    monkeypatch.setattr(queue, "control_freeze", lambda: pytest.fail("control read"))
    with pytest.raises(RuntimeError, match="live queue"):
        queue.run(tmp_path / "queue-control-freeze-016.json")
    assert not (tmp_path / "phase1-attempts.jsonl").exists()


def test_recovered_cell_is_not_retried_and_child_has_only_frozen_imports(tmp_path, monkeypatch):
    saved = {"atomic_execution_entrypoint": "/immutable/atomic.py"}
    path = tmp_path / "queue-control-freeze-016.json"
    path.write_text(json.dumps(saved))
    (tmp_path / "cell-configs").mkdir()
    (tmp_path / queue.e.AUTHORIZATION).write_text('{"affected_original_runs":[]}')
    calls = []
    attempt = SimpleNamespace(cell_id="recovered", run_id="recovered-run", disposition="valid")
    ledger = SimpleNamespace(pending=(), attempts=(attempt,), completed_cells=("recovered",))

    def reserve(cell, run, execution):
        assert cell == "next" and execution == queue.e.EXECUTION_SHA256
        calls.append((cell, run))

    def settle(*args):
        assert args[1] == "valid"
        ledger.completed_cells = ("recovered", "next")

    ledger.reserve, ledger.settle = reserve, settle
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(queue.frozen, "APP", tmp_path / "immutable-app")
    monkeypatch.setattr(queue.frozen, "require_remote", lambda: None)
    monkeypatch.setattr(queue.e, "assert_inactive", lambda _: None)
    monkeypatch.setattr(queue, "control_freeze", lambda: saved)
    monkeypatch.setattr(queue, "owned_ledger", lambda: ledger)
    monkeypatch.setattr(queue.frozen, "schedule", lambda: (
        SimpleNamespace(cell_id="recovered", method="E"),
        SimpleNamespace(cell_id="next", method="A")))
    monkeypatch.setattr(queue.frozen, "schedule_sha256", lambda _: "a" * 64)
    monkeypatch.setattr(queue.frozen, "verified_prices", lambda *_: ({}, None))
    monkeypatch.setattr(queue.frozen, "reference", lambda: {})
    monkeypatch.setattr(queue.frozen, "cell_config", lambda _, run, *a, **k: {"run_id": run})
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
        write_new(Path(stdout.name).parent / "private/residency-validation.json", {"passed": True})
        return SimpleNamespace(pid=123, wait=lambda: 0)

    monkeypatch.setattr(queue.subprocess, "Popen", spawn)
    monkeypatch.setattr(queue.previous.previous.previous.quote, "admission", lambda *_: {
        "disposition": "valid", "reason": "ordinary_outcome", "problems": []})
    queue.run(path)
    assert len(calls) == 1
    assert not (tmp_path / "evidence/recovered").exists()
    assert (tmp_path / "phase1-queue-completed.json").exists()
