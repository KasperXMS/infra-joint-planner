import json
from pathlib import Path

import pytest

from infra_joint.experiments.attempt_ledger import AttemptLedger, QueueLease


def ledger(path: Path) -> AttemptLedger:
    return AttemptLedger(path, ("cell-1", "cell-2"), "a" * 64)


def test_semantic_failure_is_retained_as_valid_and_never_repeated(tmp_path: Path) -> None:
    path = tmp_path / "attempts.jsonl"
    value = ledger(path)
    value.reserve("cell-1", "run-1", "b" * 64)
    value.settle("run-1", "valid", "budget_exhaustion", "c" * 64)
    reloaded = ledger(path)
    assert reloaded.completed_cells == ("cell-1",)
    with pytest.raises(RuntimeError, match="must not be repeated"):
        reloaded.reserve("cell-1", "rerun", "b" * 64)
    reloaded.reserve("cell-2", "run-2", "b" * 64)
    reloaded.settle("run-2", "valid", "wrong_answer", "c" * 64)
    assert ledger(path).completed_cells == ("cell-1", "cell-2")


def test_outstanding_reservation_blocks_restart_after_observation_timeout(tmp_path: Path) -> None:
    path = tmp_path / "attempts.jsonl"
    ledger(path).reserve("cell-1", "still-possibly-live", "b" * 64)
    reloaded = ledger(path)
    assert reloaded.pending[0].run_id == "still-possibly-live"
    for cell in ("cell-1", "cell-2"):
        with pytest.raises(RuntimeError, match="outstanding"):
            reloaded.reserve(cell, "restart", "b" * 64)


def test_only_one_identical_operational_replacement_allowed(tmp_path: Path) -> None:
    path = tmp_path / "attempts.jsonl"
    value = ledger(path)
    value.reserve("cell-1", "first", "b" * 64)
    with pytest.raises(ValueError, match="ordinary Agent failure"):
        value.settle("first", "operational_excluded", "context_limit_exceeded", "c" * 64)
    value.settle("first", "operational_excluded", "provider_outage", "c" * 64)
    with pytest.raises(RuntimeError, match="identical"):
        value.reserve("cell-1", "changed", "d" * 64)
    value.reserve("cell-1", "replacement", "b" * 64)
    value.settle("replacement", "operational_excluded", "provider_outage", "e" * 64)
    reloaded = ledger(path)
    with pytest.raises(RuntimeError, match="exhausted"):
        reloaded.reserve("cell-1", "third", "b" * 64)
    assert len(reloaded.attempts) == 2 and not reloaded.completed_cells


def test_confounder_stops_every_following_cell(tmp_path: Path) -> None:
    value = ledger(tmp_path / "attempts.jsonl")
    value.reserve("cell-1", "first", "b" * 64)
    value.settle("first", "confounder", "privacy_violation", "c" * 64)
    for cell in ("cell-1", "cell-2"):
        with pytest.raises(RuntimeError, match="confounder"):
            value.reserve(cell, "next", "b" * 64)


@pytest.mark.parametrize("damage", ["tail", "content", "schedule"])
def test_torn_tampered_or_drifted_journal_is_not_silently_repaired(
    tmp_path: Path, damage: str,
) -> None:
    path = tmp_path / "attempts.jsonl"
    value = ledger(path)
    value.reserve("cell-1", "first", "b" * 64)
    if damage == "tail":
        path.write_text(path.read_text().rstrip("\n"))
    elif damage == "content":
        path.write_text(path.read_text().replace('"first"', '"other"'))
    with pytest.raises(RuntimeError):
        if damage == "schedule":
            AttemptLedger(path, ("cell-2", "cell-1"), "a" * 64)
        else:
            ledger(path)


def test_schedule_cap_order_duplicates_and_receipts_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        AttemptLedger(tmp_path / "too-many", tuple(str(i) for i in range(421)), "a" * 64)
    value = ledger(tmp_path / "attempts.jsonl")
    with pytest.raises(ValueError, match="outside"):
        value.reserve("new-task", "first", "b" * 64)
    with pytest.raises(RuntimeError, match="order"):
        value.reserve("cell-2", "first", "b" * 64)
    with pytest.raises(ValueError, match="SHA-256"):
        value.reserve("cell-1", "first", "unknown")
    value.reserve("cell-1", "first", "b" * 64)
    value.settle("first", "valid", "completed", "c" * 64)
    with pytest.raises(RuntimeError, match="duplicate attempt"):
        value.reserve("cell-2", "first", "b" * 64)
    with pytest.raises(RuntimeError, match="already settled"):
        value.settle("first", "valid", "completed", "c" * 64)


def test_exclusive_lease_is_not_removed_by_failed_second_acquisition(tmp_path: Path) -> None:
    path = tmp_path / "lease.json"
    with QueueLease(path):
        original = json.loads(path.read_text())
        with pytest.raises(FileExistsError), QueueLease(path):
            pass
        assert json.loads(path.read_text()) == original
    assert not path.exists()


def test_lease_ownership_drift_requires_explicit_reconciliation(tmp_path: Path) -> None:
    path = tmp_path / "lease.json"
    with pytest.raises(RuntimeError, match="ownership changed"), QueueLease(path):
        path.write_text('{"pid": "changed"}')
    assert path.exists()


def test_generic_repair_is_append_only_affected_only_and_bound_to_new_freeze(
    tmp_path: Path,
) -> None:
    path = tmp_path / "attempts.jsonl"
    value = ledger(path)
    value.reserve("cell-1", "broken", "b" * 64)
    value.settle("broken", "confounder", "decoder_missing", "c" * 64)
    original = path.read_bytes()
    value.authorize_generic_repair("broken", original_admission_sha256="c" * 64,
                                   repair_audit_sha256="d" * 64,
                                   new_execution_sha256="e" * 64)
    assert path.read_bytes().startswith(original)
    assert value.attempts[0].disposition == "confounder"
    assert not value.completed_cells
    resumed = ledger(path)
    with pytest.raises(RuntimeError, match="order"):
        resumed.reserve("cell-2", "skip-broken", "e" * 64)
    with pytest.raises(RuntimeError, match="audited new freeze"):
        resumed.reserve("cell-1", "wrong-revision", "b" * 64)
    resumed.reserve("cell-1", "fixed", "e" * 64)
    resumed.settle("fixed", "valid", "wrong_answer", "f" * 64)
    assert ledger(path).completed_cells == ("cell-1",)
    assert len(ledger(path).attempts) == 2


@pytest.mark.parametrize("invalid", ["ordinary_failure", "wrong_receipt", "unchanged_freeze"])
def test_repair_cannot_be_used_to_rescue_semantic_failure_or_bypass_audit(
    tmp_path: Path, invalid: str,
) -> None:
    value = ledger(tmp_path / "attempts.jsonl")
    value.reserve("cell-1", "first", "b" * 64)
    value.settle("first", "valid" if invalid == "ordinary_failure" else "confounder",
                 "failure", "c" * 64)
    with pytest.raises(RuntimeError, match="repair requires"):
        value.authorize_generic_repair(
            "first", original_admission_sha256="a" * 64 if invalid == "wrong_receipt" else "c" * 64,
            repair_audit_sha256="d" * 64,
            new_execution_sha256="b" * 64 if invalid == "unchanged_freeze" else "e" * 64)
