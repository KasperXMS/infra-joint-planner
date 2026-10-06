import copy
import importlib
import json
import sys
from pathlib import Path

import pytest
from test_resident_cardinality_private_evidence import prepare_completed_stores
from test_resident_E_query_private_evidence import complete_snapshot

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
audit = importlib.import_module("large_scale_resident_current_private_evidence_v1")


def compound_membership() -> dict:
    snapshot = complete_snapshot()
    row = snapshot["rows"][3]
    final = row["attempts"][0]
    row["condition"]["task"]["family"] = "multihop_rag"
    row["attempts"] = [
        dict(final, run_id="old-runtime-confounder", disposition="confounder",
             comparative_sample_eligible=False, execution_source_epoch=3,
             execution_sha256=audit.sources.EXECUTIONS[3]),
        dict(final, run_id="verifier-timeout", disposition="operational_excluded",
             comparative_sample_eligible=False, attempt_index=2),
        dict(final, run_id="replacement-policy-failure", attempt_index=3,
             benchmark_score=None, execution_completed=False),
    ]
    return snapshot


def test_current_audit_uses_current_collector_not_historical_projection() -> None:
    current = importlib.import_module("large_scale_resident_field_policy_snapshot_v1")
    historical = importlib.import_module("large_scale_resident_E_query_private_evidence_v1")
    assert audit.sources is current
    assert historical.sources is not current
    assert audit.sources.EXECUTIONS == historical.sources.EXECUTIONS


def test_exact_nominal_failure_retained_and_exclusions_not_repeated_or_imputed() -> None:
    snapshot = compound_membership()
    before = copy.deepcopy(snapshot)
    selected = audit.source_bound_membership(snapshot)
    assert len(selected) == 168
    assert selected[3][1]["run_id"] == "replacement-policy-failure"
    assert selected[3][1]["benchmark_score"] is None
    assert snapshot == before


@pytest.mark.parametrize("defect", ["partial", "pending", "multiple_valid",
                                     "missing_epoch", "historical_source_drift"])
def test_current_membership_remains_fail_closed(defect: str) -> None:
    snapshot = compound_membership()
    row = snapshot["rows"][3]
    if defect == "partial":
        snapshot["admitted_cells"] = 124
    elif defect == "pending":
        snapshot["pending_count"] = 1
    elif defect == "multiple_valid":
        row["attempts"].append(dict(row["attempts"][-1], run_id="another-valid"))
    elif defect == "missing_epoch":
        del snapshot["execution_freezes"]["4"]
    else:
        row["attempts"][1]["execution_sha256"] = "f" * 64
    with pytest.raises(RuntimeError):
        audit.source_bound_membership(snapshot)


def test_live_queue_blocks_before_even_metadata_collection(monkeypatch, tmp_path) -> None:
    def live(_):
        raise RuntimeError("queue live")

    monkeypatch.setattr(audit.private, "assert_inactive", live)
    monkeypatch.setattr(audit.sources, "collect", lambda *_: pytest.fail("live read"))
    with pytest.raises(RuntimeError, match="queue live"):
        audit.audit_phase_one(tmp_path, tmp_path, tmp_path / "unused")


def test_partial_block_blocks_every_private_body_read(monkeypatch, tmp_path) -> None:
    snapshot = compound_membership()
    snapshot["admitted_cells"] = 124
    monkeypatch.setattr(audit.sources, "collect", lambda *_: snapshot)
    monkeypatch.setattr(audit.private, "audit_multihop", lambda *_: pytest.fail("body read"))
    with pytest.raises(RuntimeError, match="completed resolved168"):
        audit.audit_phase_one(tmp_path, tmp_path, tmp_path / "unused")


def test_last_worker_must_exit_before_first_body_read(monkeypatch, tmp_path) -> None:
    snapshot = compound_membership()
    prepare_completed_stores(tmp_path, snapshot)
    (tmp_path / "evidence/cell-167/attempt1/worker-shutdown.json").write_text(
        '{"verified_exited":false}')
    monkeypatch.setattr(audit.sources, "collect", lambda *_: snapshot)
    monkeypatch.setattr(audit.private, "audit_multihop", lambda *_: pytest.fail("body read"))
    with pytest.raises(RuntimeError, match="every effective Worker exited"):
        audit.audit_phase_one(tmp_path, tmp_path, tmp_path / "unused")


def test_only_nominal_current_attempt_scanned_and_no_quality_fabricated(monkeypatch, tmp_path):
    snapshot = compound_membership()
    prepare_completed_stores(tmp_path, snapshot)
    calls = []
    monkeypatch.setattr(audit.sources, "collect", lambda *_: snapshot)
    monkeypatch.setattr(audit.private, "audit_multihop",
                        lambda *args: calls.append(args) or {"semantic_evidence_retention": None})
    value = audit.audit_phase_one(tmp_path, tmp_path, tmp_path / "corpus")
    assert len(calls) == 1 and calls[0][0] == tmp_path / "evidence/cell-3/attempt3"
    assert value["records"][3]["benchmark_score"] is None
    assert value["excluded_historical_run_ids"] == ["old-runtime-confounder", "verifier-timeout"]
    assert value["version"] == audit.VERSION
    assert not value["phase2_authorized"] and not value["semantic_audit_complete"]
    assert value["planner_or_model_calls"] == 0 and not value["artifact_bodies_exported"]
    assert not value["measured_execution_modified"]


@pytest.mark.parametrize("defect", ["restarted", "journal_changed"])
def test_current_audit_rechecks_membership_and_inactivity(monkeypatch, tmp_path, defect):
    snapshot = compound_membership()
    prepare_completed_stores(tmp_path, snapshot)
    calls = []

    def inactive(*args):
        calls.append(args)
        if len(calls) == 2:
            if defect == "restarted":
                raise RuntimeError("queue restarted")
            (tmp_path / "phase1-attempts.jsonl").write_text(json.dumps({"changed": True}))

    monkeypatch.setattr(audit.sources, "collect", lambda *_: snapshot)
    monkeypatch.setattr(audit.private, "assert_inactive", inactive)
    monkeypatch.setattr(audit.private, "audit_multihop", lambda *_: {})
    with pytest.raises(RuntimeError, match="queue restarted|membership changed"):
        audit.audit_phase_one(tmp_path, tmp_path, tmp_path / "unused")
