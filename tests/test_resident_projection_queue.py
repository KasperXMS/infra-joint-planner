from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
queue = importlib.import_module("large_scale_resident_projection_queue_v1")


@pytest.mark.parametrize("damage", [None, "parent_hash", "parent_source", "missing", "unsettled"])
def test_new_control_requires_frozen_parent_and_reproducible_settled_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str | None,
) -> None:
    parent = {"execution_epochs_sha256": {"4": queue.previous.EXECUTION_SHA256},
              "source_bound_record_adjudications": {}, "controller_source_sha256": "a" * 64}
    path = tmp_path / "queue-control-freeze-011.json"
    path.write_text(json.dumps(parent))
    proof = tmp_path / queue.reviewer.DIRECTORY / "audited.json"
    proof.parent.mkdir()
    proof.write_text("{}")
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(queue, "PARENT_SHA256", queue.frozen.sha256(path))
    monkeypatch.setattr(queue.previous, "control_freeze", lambda: parent)
    monkeypatch.setattr(queue, "owned_ledger", lambda: SimpleNamespace(attempts=(
        SimpleNamespace(run_id="audited", reason=queue.reviewer.REASON),)))
    if damage == "parent_hash":
        path.write_text("{}")
    elif damage == "parent_source":
        monkeypatch.setattr(queue.previous, "control_freeze", lambda: {})
    elif damage == "missing":
        proof.unlink()
    elif damage == "unsettled":
        monkeypatch.setattr(queue, "owned_ledger", lambda: SimpleNamespace(attempts=()))
    if damage:
        with pytest.raises(RuntimeError):
            queue.control_freeze()
    else:
        value = queue.control_freeze()
        assert value["execution_epochs_sha256"] == parent["execution_epochs_sha256"]
        assert value["source_bound_record_adjudications"] == {}
        assert value["projected_record_adjudications"] == {proof.name: queue.frozen.sha256(proof)}
        assert value["measured_execution_changed"] is False
        assert value["semantic_retries"] is False


def test_drift_stops_before_any_new_reservation_or_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(queue.frozen, "require_remote", lambda: None)
    monkeypatch.setattr(queue, "control_freeze", lambda: {"actual": True})
    path = tmp_path / "queue-control-freeze-012.json"
    path.write_text('{"actual":false}')
    monkeypatch.setattr(queue, "owned_ledger", lambda: pytest.fail("must not open ledger"))
    with pytest.raises(RuntimeError, match="drift"):
        queue.run(path)
    assert not (tmp_path / "phase1-attempts.jsonl").exists()


def test_collector_and_post_block_audit_share_exact_projection_view() -> None:
    collector = importlib.import_module("large_scale_resident_projection_snapshot_v1")
    private = importlib.import_module("large_scale_resident_E_query_private_evidence_v1")
    assert private.sources is collector
    assert collector.reviewer is queue.reviewer
    assert len(collector.EXECUTIONS) == 4
