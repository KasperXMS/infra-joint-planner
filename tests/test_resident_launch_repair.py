"""A tested zero-execution launch repair never becomes a semantic retry waiver."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from infra_joint.control.provenance import provenance_sha256

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
review = importlib.import_module("large_scale_resident_launch_review_v1")
queue = importlib.import_module("large_scale_resident_launch_queue_v1")
snapshot = importlib.import_module("large_scale_resident_launch_snapshot_v1")


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    root = tmp_path
    code = root / "audit-tools/correction/scripts"
    code.mkdir(parents=True)
    for name in ("review.py", "environment.py", "queue.py"):
        (code / name).write_text("# immutable correction\n", encoding="utf-8")
    monkeypatch.setattr(review, "__file__", str(code / "review.py"))
    monkeypatch.setattr(review.environment, "__file__", str(code / "environment.py"))
    app = root / "app-E-query-contract-repair-004"
    source = app / "scripts/atomic.py"
    source.parent.mkdir(parents=True)
    source.write_text("# unchanged measured archive\n", encoding="utf-8")
    execution = {"commit_sha": "a" * 40,
                 "source_sha256": {"scripts/atomic.py": review.sha256(source)}}
    freeze = root / "execution-freeze-004.json"
    put(freeze, execution)
    execution_sha = provenance_sha256(execution)
    sources = {str(p.relative_to(root)): review.sha256(p) for p in code.iterdir()}
    local = {"pytest_passed": 1561, "pytest_returncode": 0, "ruff_returncode": 0,
             "strict_pyright_returncode": 0, "diff_returncode": 0,
             "repair_sources_sha256": sources}
    linux = {"pytest_passed": 31, "pytest_returncode": 0, "preflight_returncode": 0,
             "preflight_execution_sha256": execution_sha, "repair_sources_sha256": sources}
    put(root / "validation/local.json", local)
    put(root / "validation/linux.json", linux)
    correction = {
        "version": "exact-preexecution-provenance-launch-repair-v1",
        "max_affected_reexecutions": 1, "measured_execution_changed": False,
        "semantic_tuning": False, "repair_sources_sha256": sources,
        "archive_app": app.name, "execution_freeze_file": freeze.name,
        "execution_freeze_file_sha256": review.sha256(freeze),
        "execution_sha256": execution_sha, "code_revision": "a" * 40,
        "validation_receipts": {key: {"filename": "validation/" + key + ".json",
                                     "sha256": review.sha256(root / "validation" / (key + ".json"))}
                                for key in ("local", "linux")}}
    correction["validation_receipts"]["full_local"] = correction["validation_receipts"].pop(
        "local")
    patch = root / "launch-repair-freeze-001.json"
    put(patch, correction)
    ledger = review.ProjectionAttemptLedger(root / "phase1-attempts.jsonl", ("first", "second"),
                                           "b" * 64)
    run = root.name + "-first-attempt1"
    ledger.reserve("first", run, execution_sha)
    directory = root / "evidence/first/attempt1"
    raw = {"disposition": "confounder", "reason": "admission_unverifiable",
           "problems": ["FileNotFoundError"]}
    put(directory / "admission.json", raw)
    put(directory / "process.json", {"pid": 123, "run_id": run})
    put(directory / "process-exit.json", {"pid": 123, "returncode": 1})
    put(directory / "attempt-error.json", {"exception_type": "RuntimeError",
                                          "message": review.FAILURE["message"],
                                          "before_runner": True})
    (directory / "console.log").write_text("preserved setup failure", encoding="utf-8")
    put(directory / "runs" / run / "result.json", {"execution_completed": False,
                                                  "evaluation": None, "failure": review.FAILURE})
    events = [{"event_type": "run.start", "payload": {"attempt_before_runner": True}},
              {"event_type": "run.failed", "payload": {"failure": review.FAILURE}}]
    trace = directory / "runs" / run / "trace.jsonl"
    trace.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    ledger.settle(run, "confounder", raw["reason"], provenance_sha256(raw))
    sidecar = root / review.AUTH_DIRECTORY / (run + ".json")
    value = {"run_id": run, "original_admission_sha256": provenance_sha256(raw),
             "original_execution_sha256": execution_sha,
             "reviewer_source_sha256": review.sha256(code / "review.py"),
             "repair_freeze_file": patch.name, "repair_freeze_file_sha256": review.sha256(patch),
             "original_evidence_file_sha256": review.methods.evidence_files(directory)}
    put(sidecar, value)
    return SimpleNamespace(root=root, app=app, source=source, ledger=ledger, run=run,
                           directory=directory, sidecar=sidecar, value=value, patch=patch,
                           correction=correction, events=events, trace=trace,
                           execution=execution_sha)


def test_repair_keeps_original_confounder_and_authorizes_only_one_identical_execution(prepared):
    p = prepared
    original = p.ledger.attempts[0]
    settlement = p.ledger._records[-1].copy()
    p.ledger.authorize_launch_repair(p.run)
    assert p.ledger.attempts[0] == original
    assert original.disposition == "confounder" and not p.ledger.completed_cells
    assert p.ledger._records[-2] == settlement
    assert p.ledger._repairs == {}  # No invented measured execution epoch.
    reloaded = review.ProjectionAttemptLedger(p.ledger.path, ("first", "second"), "b" * 64)
    assert reloaded.launch_repairs == p.ledger.launch_repairs
    reloaded.reserve("first", "recovered-attempt2", p.execution)
    reloaded.settle("recovered-attempt2", "valid", "ordinary_semantic_failure", "c" * 64)
    assert reloaded.completed_cells == ("first",)
    reloaded.reserve("second", "next-original-cell", p.execution)


def test_changed_execution_and_third_attempt_cannot_use_the_launch_repair(prepared):
    p = prepared
    p.ledger.authorize_launch_repair(p.run)
    with pytest.raises(RuntimeError, match="identical execution"):
        p.ledger.reserve("first", "wrong-freeze", "f" * 64)
    # Native append validation failed before disk write; reload authoritative state.
    ledger = review.ProjectionAttemptLedger(p.ledger.path, ("first", "second"), "b" * 64)
    ledger.reserve("first", "second-attempt", p.execution)
    ledger.settle("second-attempt", "confounder", "another_system_failure", "d" * 64)
    with pytest.raises(RuntimeError, match="repair exhausted"):
        ledger.reserve("first", "forbidden-third", p.execution)


@pytest.mark.parametrize("damage", ["reasoning", "inference", "worker", "tc", "evaluated",
                                    "different_failure", "error_stage", "zero_exit", "identity",
                                    "source", "validation", "freeze", "extra_file"])
def test_exact_no_execution_review_cannot_waive_other_failures(prepared, damage):
    p = prepared
    if damage in {"reasoning", "inference"}:
        p.events.insert(1, {"event_type": "logical.reasoning.started" if damage == "reasoning"
                           else "logical.model.outcome", "payload": {}})
        p.trace.write_text("".join(json.dumps(e) + "\n" for e in p.events), encoding="utf-8")
    elif damage in {"worker", "tc", "extra_file"}:
        name = {"worker": "worker-starts/A4.json", "tc": "tc-attestation.json",
                "extra_file": "unreviewed.json"}[damage]
        put(p.directory / name, {})
    elif damage in {"evaluated", "different_failure"}:
        path = p.directory / "runs" / p.run / "result.json"
        result = json.loads(path.read_text())
        if damage == "evaluated":
            result["evaluation"] = {"benchmark_score": 0}
        else:
            result["failure"] = {"code": "budget_exhausted"}
        put(path, result)
    elif damage == "error_stage":
        path = p.directory / "attempt-error.json"
        value = json.loads(path.read_text())
        value["before_runner"] = False
        put(path, value)
    elif damage == "zero_exit":
        put(p.directory / "process-exit.json", {"pid": 123, "returncode": 0})
    elif damage == "identity":
        p.value["run_id"] = "other"
    elif damage == "source":
        p.source.write_text("drift")
    elif damage == "validation":
        path = p.root / "validation/linux.json"
        value = json.loads(path.read_text())
        value["preflight_execution_sha256"] = "f" * 64
        put(path, value)
        p.correction["validation_receipts"]["linux"]["sha256"] = review.sha256(path)
        put(p.patch, p.correction)
        p.value["repair_freeze_file_sha256"] = review.sha256(p.patch)
    else:
        p.patch.write_text("{}")
    p.value["original_evidence_file_sha256"] = review.methods.evidence_files(p.directory)
    put(p.sidecar, p.value)
    with pytest.raises(RuntimeError):
        p.ledger.authorize_launch_repair(p.run)
    assert not p.ledger.launch_repairs


def test_proof_drift_after_authorization_prevents_another_reservation(prepared):
    p = prepared
    p.ledger.authorize_launch_repair(p.run)
    (p.directory / "console.log").write_text("changed")
    before = p.ledger.path.read_bytes()
    with pytest.raises(RuntimeError, match="seven original"):
        p.ledger.reserve("first", "repair-attempt2", p.execution)
    assert p.ledger.path.read_bytes() == before


def test_duplicate_authorization_is_rejected_before_journal_mutation(prepared):
    p = prepared
    p.ledger.authorize_launch_repair(p.run)
    before = p.ledger.path.read_bytes()
    with pytest.raises(RuntimeError, match="unique settled"):
        p.ledger.authorize_launch_repair(p.run)
    assert p.ledger.path.read_bytes() == before


def test_controller_preflight_failure_cannot_reserve_or_start_a_worker(prepared, monkeypatch):
    p = prepared
    monkeypatch.setattr(queue.frozen, "ROOT", p.root)
    monkeypatch.setattr(queue.frozen, "require_remote", lambda: None)
    monkeypatch.setattr(queue, "control_freeze", lambda: {"immutable": True})
    monkeypatch.setattr(queue, "owned_ledger", lambda: p.ledger)
    monkeypatch.setattr(queue, "child_environment", lambda _: {"checked": "before-reserve"})

    def preflight(_):
        raise RuntimeError("preflight stop")

    monkeypatch.setattr(queue, "preflight", preflight)
    control = p.root / "queue-control-freeze-test.json"
    put(control, {"immutable": True})
    before = p.ledger.path.read_bytes()
    with pytest.raises(RuntimeError, match="preflight stop"):
        queue.run(control)
    assert p.ledger.path.read_bytes() == before
    assert not (p.root / "worker-configs").exists()


def test_only_proved_journaled_setup_failure_may_have_no_residency_receipt(prepared):
    p = prepared
    original = p.ledger.attempts[0]
    with pytest.raises(FileNotFoundError):
        snapshot.residency_receipt(p.root, p.directory, original, p.ledger)
    p.ledger.authorize_launch_repair(p.run)
    value = snapshot.residency_receipt(p.root, p.directory, original, p.ledger)
    assert value["residency_validation"] is None
    assert not value["comparative_sample_eligible"]
    assert not value["operational_replacement"]
    assert original.disposition == "confounder"
    (p.directory / "console.log").write_text("drift")
    with pytest.raises(RuntimeError):
        snapshot.residency_receipt(p.root, p.directory, original, p.ledger)


def test_child_environment_pins_archive_revision_without_audit_imports(prepared, monkeypatch):
    p = prepared
    p.ledger.authorize_launch_repair(p.run)
    monkeypatch.setattr(queue.frozen, "ROOT", p.root)
    monkeypatch.setattr(queue.frozen, "APP", p.app)
    monkeypatch.setattr(queue.e, "EXECUTION_SHA256", p.execution)
    monkeypatch.delenv(review.environment.REVISION_VARIABLE, raising=False)
    env = queue.child_environment(p.ledger)
    assert env[review.environment.REVISION_VARIABLE] == "a" * 40
    assert env["PYTHONPATH"].split(queue.os.pathsep) == [
        str(p.app / "src"), str(p.app / "scripts")]
    assert "audit-tools" not in env["PYTHONPATH"]


def test_boolean_repair_limit_cannot_claim_a_numeric_one(prepared):
    p = prepared
    p.correction["max_affected_reexecutions"] = True
    put(p.patch, p.correction)
    p.value["repair_freeze_file_sha256"] = review.sha256(p.patch)
    put(p.sidecar, p.value)
    with pytest.raises(RuntimeError, match="preserve the measured"):
        p.ledger.authorize_launch_repair(p.run)
