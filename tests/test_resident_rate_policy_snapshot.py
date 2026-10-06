"""Current collector preserves exact historical proofs and external exclusions."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
snapshot = importlib.import_module("large_scale_resident_rate_policy_snapshot_v1")


@pytest.fixture
def source(tmp_path, monkeypatch):
    journal = tmp_path / "phase1-attempts.jsonl"
    journal.write_text("immutable\n", encoding="utf-8")
    proof = tmp_path / snapshot.reviewer.RATE_DIRECTORY / "mixed.json"
    proof.parent.mkdir()
    proof.write_text("{}", encoding="utf-8")
    attempts = [{"run_id": "mixed", "disposition": "operational_excluded",
                 "reason": snapshot.reviewer.REASON},
                {"run_id": "nominal", "disposition": "valid", "reason": "semantic_failure"}]
    seen = []

    def original(root, predecessor):
        seen.append((root, predecessor, reviewer.ProjectionAttemptLedger,  # noqa: F821
                     reviewer.SEMANTIC_DIRECTORY, source_bindings()))  # noqa: F821
        return {"rows": [{"attempts": attempts}], "collector_source_sha256": source_bindings(),  # noqa: F821, E501
                "journal_sha256": snapshot.resident.sha256(journal),
                "execution_freezes": snapshot.EXECUTIONS, "admitted_cells": 1}

    monkeypatch.setattr(snapshot.previous, "collect", original)
    monkeypatch.setattr(snapshot, "source_bindings", lambda: {"actual.py": "a" * 64})
    return tmp_path, proof, attempts, seen, original


def test_verified_operational_membership_and_prior_nominal_samples_are_preserved(source):
    root, proof, attempts, seen, original = source
    before = dict(original.__globals__)
    value = snapshot.collect(root, root)
    assert seen == [(root, root, snapshot.reviewer.ProjectionAttemptLedger,
                     snapshot.reviewer.previous.SEMANTIC_DIRECTORY, {"actual.py": "a" * 64})]
    assert value["execution_freezes"] == snapshot.EXECUTIONS
    assert value["admitted_cells"] == 1
    assert attempts[0]["mixed_token_rate_policy_review_file_sha256"] == (
        snapshot.resident.sha256(proof))
    assert attempts[0]["benchmark_quality_unknown"] is True
    assert attempts[0]["policy_only_replacement_authorized"] is False
    assert attempts[1]["mixed_token_rate_policy_review_file_sha256"] is None
    assert original.__globals__ == before


@pytest.mark.parametrize("damage", ["nominal", "pending", "reason", "journal"])
def test_projection_rejects_different_membership_or_advanced_journal(source, monkeypatch, damage):
    root, _, attempts, *_ = source
    if damage == "nominal":
        attempts[0]["disposition"] = "valid"
    elif damage == "pending":
        attempts[0]["disposition"] = None
    elif damage == "reason":
        attempts[0]["reason"] = "unclassified_API_failure_requires_audit"
    else:
        original_sha = snapshot.resident.sha256
        count = 0

        def changed(path):
            nonlocal count
            if path.name == "phase1-attempts.jsonl":
                count += 1
                if count > 1:
                    return "f" * 64
            return original_sha(path)

        monkeypatch.setattr(snapshot.resident, "sha256", changed)
    with pytest.raises(RuntimeError):
        snapshot.collect(root, root)


def test_actual_source_closure_contains_both_collectors_and_new_reviewer():
    bindings = snapshot.source_bindings()
    assert bindings[Path(snapshot.__file__).name] == snapshot.resident.sha256(
        Path(snapshot.__file__))
    assert bindings[Path(snapshot.previous.__file__).name] == snapshot.resident.sha256(
        Path(snapshot.previous.__file__))
    assert bindings[Path(snapshot.reviewer.__file__).name] == snapshot.resident.sha256(
        Path(snapshot.reviewer.__file__))
    assert bindings[Path(snapshot.reviewer.previous.__file__).name] == snapshot.resident.sha256(
        Path(snapshot.reviewer.previous.__file__))
