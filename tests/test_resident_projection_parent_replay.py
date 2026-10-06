"""Regression for continuation after a reviewed confounder and a later cell."""

import copy
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
queue = importlib.import_module("large_scale_resident_projection_queue_v2")


def test_expanded_journal_never_replays_the_incompatible_parent_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = {"execution_epochs_sha256": {"4": queue.previous.EXECUTION_SHA256}}
    path = tmp_path / "queue-control-freeze-011.json"
    path.write_text(json.dumps(parent))
    proof = tmp_path / queue.reviewer.DIRECTORY / "reviewed.json"
    proof.parent.mkdir()
    proof.write_text("{}")
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(queue, "PARENT_SHA256", queue.frozen.sha256(path))
    monkeypatch.setattr(queue.previous, "control_freeze",
                        lambda: pytest.fail("historical ledger cannot replay new proof"))
    monkeypatch.setattr(queue, "historical_control", lambda: parent)
    monkeypatch.setattr(queue, "owned_ledger", lambda: SimpleNamespace(attempts=(
        SimpleNamespace(run_id="reviewed", reason=queue.reviewer.REASON),
        SimpleNamespace(run_id="later-valid-cell", reason="completed_or_valid_semantic_failure"),
    )))
    value = queue.control_freeze()
    assert value["execution_epochs_sha256"] == parent["execution_epochs_sha256"]
    assert value["measured_execution_changed"] is False
    assert value["semantic_retries"] is False
    assert value["projected_record_adjudications"] == {proof.name: queue.frozen.sha256(proof)}


@pytest.mark.parametrize("damage", [None, "source", "old_review", "authorization",
                                    "quote", "repair", "exclusion", "epoch"])
def test_parent_freeze_retains_sources_proofs_and_exact_repair_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str | None,
) -> None:
    root = tmp_path
    monkeypatch.setattr(queue.frozen, "ROOT", root)
    keys = ("reviewer_source_sha256", "record_reviewer_source_sha256",
            "private_guard_source_sha256", "ledger_view_source_sha256",
            "ledger_dependency_sources_sha256", "adjudications", "record_field_adjudications",
            "resident_provider_policy_adjudications", "provider_policy_adjudications")
    current = {k: {"source": "a" * 64} for k in keys}
    old = copy.deepcopy(current)
    old["quote_integrity_adjudications"] = {}
    (root / "queue-control-freeze-010.json").write_text(json.dumps(old))
    saved = {"affected_original_runs": ["old-E"]}
    (root / queue.previous.AUTHORIZATION).write_text(json.dumps(saved))
    review = root / queue.previous.reviewer.DIRECTORY / "old-E.json"
    review.parent.mkdir()
    review.write_text("{}")
    monkeypatch.setattr(queue.previous.previous, "control_freeze", lambda: current)
    monkeypatch.setattr(queue.previous, "authorization_value", lambda _: saved)
    monkeypatch.setattr(queue.previous, "historical_repairs", lambda _: {"old-quote": "2" * 64})
    journal = [
        {"event": "generic_repair", "run_id": "old-quote", "new_execution_sha256": "2" * 64},
        {"event": "generic_repair", "run_id": "old-E",
         "new_execution_sha256": queue.previous.EXECUTION_SHA256},
        {"event": "E_query_contract_confounded", "run_id": "old-E"},
        {"event": "settled", "run_id": "reviewed-record-field-misuse"},
        {"event": "reserved", "run_id": "later-valid-cell"},
        {"event": "settled", "run_id": "later-valid-cell"},
    ]
    for index, app in enumerate(queue.previous.reviewer.APPS, 1):
        folder = root / app
        folder.mkdir()
        (folder / "source.py").write_text("frozen")
        (root / f"execution-freeze-{index:03d}.json").write_text(json.dumps({
            "source_sha256": {"source.py": queue.frozen.sha256(folder / "source.py")}}))
    if damage == "source":
        current["reviewer_source_sha256"] = {}
    elif damage == "old_review":
        current["record_field_adjudications"] = {}
    elif damage == "authorization":
        monkeypatch.setattr(queue.previous, "authorization_value", lambda _: {})
    elif damage == "quote":
        folder = root / queue.quote.reviewer.DIRECTORY
        folder.mkdir()
        (folder / "extra.json").write_text("{}")
    elif damage == "repair":
        journal[0]["new_execution_sha256"] = "4" * 64
    elif damage == "exclusion":
        journal[2]["run_id"] = "unexpected-E"
    elif damage == "epoch":
        (root / queue.previous.reviewer.APPS[3] / "source.py").write_text("drift")
    p = root / "phase1-attempts.jsonl"
    p.write_text("".join(json.dumps(row) + "\n" for row in journal))
    before = p.read_bytes()
    if damage:
        with pytest.raises(RuntimeError):
            queue.historical_control()
    else:
        actual = queue.historical_control()
        assert actual["generic_affected_reruns"] == ["old-E"]
        assert actual["ordinary_semantic_retries"] is False
        assert actual["source_bound_record_adjudications"] == {}
    assert p.read_bytes() == before
