"""An exact nominal failure extends control scope, never measured execution."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
queue = importlib.import_module("large_scale_resident_compound_scope_queue_v1")


@pytest.fixture
def scope(tmp_path, monkeypatch):
    folder = tmp_path / queue.compound.POLICY_DIRECTORY
    folder.mkdir()
    paths = [folder / (name + ".json") for name in ("old", "new")]
    for path in paths:
        path.write_text(json.dumps({"run_id": path.stem}), encoding="utf-8")
    parent = {"compound_record_policy_adjudications": {
        paths[0].name: queue.frozen.sha256(paths[0])},
        "native_argument_adjudications": {"sdk.json": "a" * 64},
        "atomic_execution_entrypoint": "/immutable/atomic.py",
        "execution_sha256": "b" * 64}
    control = tmp_path / queue.PARENT_FILE
    control.write_text(json.dumps(parent), encoding="utf-8")
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(queue, "PARENT_SHA256", queue.frozen.sha256(control))
    monkeypatch.setattr(queue.previous, "control_freeze", lambda: parent)
    raw = tuple(SimpleNamespace(run_id=p.stem, disposition="confounder") for p in paths)
    effective = tuple(SimpleNamespace(run_id=p.stem, disposition="valid",
                      reason=queue.compound.REASON) for p in paths)
    ledger = SimpleNamespace(original_attempts=raw, attempts=effective)
    monkeypatch.setattr(queue, "owned_ledger", lambda: ledger)
    verified = []
    monkeypatch.setattr(queue.compound, "verify_sidecar",
                        lambda p, a: verified.append((p.name, a.run_id)))
    return SimpleNamespace(paths=paths, control=control, parent=parent, ledger=ledger,
                           verified=verified)


def test_exact_current_proofs_extend_scope_without_replacing_old_control(scope):
    before = scope.control.read_bytes()
    raw = scope.ledger.original_attempts
    value = queue.control_freeze()
    assert value["compound_record_policy_adjudications"] == {
        p.name: queue.frozen.sha256(p) for p in scope.paths}
    assert value["native_argument_adjudications"] == scope.parent["native_argument_adjudications"]
    assert value["atomic_execution_entrypoint"] == scope.parent["atomic_execution_entrypoint"]
    assert value["execution_sha256"] == scope.parent["execution_sha256"]
    assert value["parent_proof_scope_preserved"] is True
    assert value["measured_execution_changed"] is False
    assert value["semantic_retries"] is False
    assert value["provider_policy_retry"] is False
    assert value["input_censored"] is False
    assert sorted(scope.verified) == [("new.json", "new"), ("old.json", "old")]
    assert scope.control.read_bytes() == before
    assert scope.ledger.original_attempts == raw


@pytest.mark.parametrize("damage", ["parent", "parent_scope", "old_proof", "old_missing",
    "no_new", "unknown_proof", "operational", "pending", "wrong_reason", "raw_missing",
    "invalid_proof"])
def test_other_findings_and_proof_drift_remain_fail_closed(scope, monkeypatch, damage):
    if damage == "parent":
        scope.control.write_text("{}", encoding="utf-8")
    elif damage == "parent_scope":
        monkeypatch.setattr(queue.previous, "control_freeze", lambda: {})
    elif damage == "old_proof":
        scope.paths[0].write_text("changed", encoding="utf-8")
    elif damage == "old_missing":
        scope.paths[0].unlink()
    elif damage == "no_new":
        scope.paths[1].unlink()
    elif damage == "unknown_proof":
        (scope.paths[0].parent / "unknown.json").write_text("{}", encoding="utf-8")
    elif damage == "operational":
        scope.ledger.attempts[1].disposition = "operational_excluded"
    elif damage == "pending":
        scope.ledger.attempts[1].disposition = None
    elif damage == "wrong_reason":
        scope.ledger.attempts[1].reason = "unclassified"
    elif damage == "raw_missing":
        scope.ledger.original_attempts = scope.ledger.original_attempts[:1]
    else:
        def reject(*_):
            raise RuntimeError("unreproduced source/API proof")

        monkeypatch.setattr(queue.compound, "verify_sidecar", reject)
    with pytest.raises(RuntimeError):
        queue.control_freeze()


def test_copied_control_keeps_launch_helpers_and_historical_globals(monkeypatch, tmp_path):
    calls = []

    def original(path):
        calls.append((owned_ledger(), control_freeze(), path))  # noqa: F821

    monkeypatch.setattr(queue.previous.previous, "run", original)
    monkeypatch.setattr(queue, "owned_ledger", lambda: "same-effective-ledger")
    monkeypatch.setattr(queue, "control_freeze", lambda: "new-proof-scope")
    before = dict(original.__globals__)
    path = tmp_path / "queue-control-freeze-022.json"
    queue.run(path)
    assert calls == [("same-effective-ledger", "new-proof-scope", path)]
    assert original.__globals__ == before


def test_control_drift_stops_before_reservation_or_physical_execution(monkeypatch, tmp_path):
    path = tmp_path / "queue-control-freeze-022.json"
    path.write_text('{"bad":true}', encoding="utf-8")
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(queue.frozen, "require_remote", lambda: None)
    monkeypatch.setattr(queue, "control_freeze", lambda: {"frozen": True})
    monkeypatch.setattr(queue, "owned_ledger", lambda: pytest.fail("must not open ledger"))
    with pytest.raises(RuntimeError, match="drift"):
        queue.run(path)
