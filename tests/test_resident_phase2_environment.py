import importlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from infra_joint.experiments.attempt_ledger import Attempt, AttemptLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
env = importlib.import_module("large_scale_resident_phase2_environment_v1")
private = importlib.import_module("large_scale_resident_phase2_environment_private_v1")


@pytest.fixture
def environment_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(env, "CELL", "cell-0")
    monkeypatch.setattr(env, "RUN", "cell-0-old")
    cells = tuple(f"cell-{i}" for i in range(18))
    raw = AttemptLedger(tmp_path / "attempts.jsonl", cells, "a" * 64)
    raw.reserve(env.CELL, env.RUN, "b" * 64)
    raw.settle(env.RUN, "confounder", "admission_unverifiable", env.RAW_SHA)
    original = raw.attempts[0]
    effective = replace(original, disposition="operational_excluded", reason=env.REASON,
                        receipt_sha256="c" * 64)
    ledger = env.EnvironmentLedger(raw.path, cells, raw.schedule_sha256, (), (original, effective))
    return raw, ledger


def test_exact_exclusion_preserves_raw_and_authorizes_one_identical_replacement(environment_ledger):
    raw, ledger = environment_ledger
    before = raw.path.read_bytes()
    assert ledger.original_attempts[0].disposition == "confounder"
    assert ledger.attempts[0].disposition == "operational_excluded"
    assert ledger.completed_cells == ()
    assert before == raw.path.read_bytes()
    ledger.reserve(env.CELL, "replacement", "b" * 64)
    ledger.settle("replacement", "valid", "wrong_answer", "d" * 64)
    assert ledger.completed_cells == (env.CELL,)
    with pytest.raises(RuntimeError):
        ledger.reserve(env.CELL, "third", "b" * 64)
    reloaded = env.EnvironmentLedger(raw.path, raw.cells, raw.schedule_sha256, (), ledger.exclusion)
    assert reloaded.original_attempts[0] == raw.attempts[0]
    assert len(reloaded.attempts) == 2


def test_environment_replacement_cannot_change_execution(environment_ledger):
    _, ledger = environment_ledger
    before = ledger.path.read_bytes()
    with pytest.raises(RuntimeError, match="identical execution"):
        ledger.reserve(env.CELL, "replacement", "d" * 64)
    assert ledger.path.read_bytes() == before


def test_environment_cannot_skip_affected_cell(environment_ledger):
    _, ledger = environment_ledger
    with pytest.raises(RuntimeError, match="order"):
        ledger.reserve("cell-1", "skip", "b" * 64)


@pytest.mark.parametrize("damage", ["run", "cell", "raw_hash", "valid", "reason"])
def test_exclusion_cannot_waive_other_attempts(environment_ledger, damage):
    raw, ledger = environment_ledger
    original, effective = ledger.exclusion
    if damage == "run":
        original = replace(original, run_id="another")
    elif damage == "cell":
        original = replace(original, cell_id="another")
    elif damage == "raw_hash":
        original = replace(original, receipt_sha256="e" * 64)
    elif damage == "valid":
        original = replace(original, disposition="valid")
    else:
        effective = replace(effective, reason="provider_outage")
    with pytest.raises(RuntimeError):
        env.EnvironmentLedger(raw.path, raw.cells, raw.schedule_sha256, (), (original, effective))


def test_same_config_failed_replacement_stops_without_third_attempt(environment_ledger):
    _, ledger = environment_ledger
    ledger.reserve(env.CELL, "replacement", "b" * 64)
    ledger.settle("replacement", "operational_excluded", "provider_outage", "d" * 64)
    with pytest.raises(RuntimeError, match="finding"):
        env.dispatch_ready(ledger)
    with pytest.raises(RuntimeError, match="exhausted"):
        ledger.reserve(env.CELL, "third", "b" * 64)


def test_new_semantic_failure_valid_and_new_confounder_stop_immediately(environment_ledger):
    _, ledger = environment_ledger
    executions, audits = [], []

    def execute(cell):
        executions.append(cell.cell_id)
        run = cell.cell_id + "-new"
        ledger.reserve(cell.cell_id, run, "b" * 64)
        ledger.settle(run, "valid" if cell.cell_id == env.CELL else "confounder",
                      "wrong_answer" if cell.cell_id == env.CELL else "privacy", "d" * 64)

    with pytest.raises(RuntimeError, match="finding"):
        env.run_batches(tuple(SimpleNamespace(cell_id=c) for c in ledger.cells), ledger,
                        execute, lambda: None, lambda: audits.append(True))
    assert executions == [env.CELL, "cell-1"] and audits == []


def test_full_checkpoint_and_tail_keep_excluded_original(environment_ledger):
    _, ledger = environment_ledger
    audits = []

    def execute(cell):
        ledger.reserve(cell.cell_id, cell.cell_id + "-new", "b" * 64)
        ledger.settle(cell.cell_id + "-new", "valid", "wrong_answer", "d" * 64)

    env.run_batches(tuple(SimpleNamespace(cell_id=c) for c in ledger.cells), ledger,
                    execute, lambda: None, lambda: audits.append(len(ledger.completed_cells)))
    assert audits == [16, 18]
    assert len(ledger.attempts) == 19
    assert ledger.original_attempts[0].disposition == "confounder"


def test_outside_journal_write_stops(environment_ledger):
    _, ledger = environment_ledger
    with ledger.path.open("a") as stream:
        stream.write("\n")
    with pytest.raises(RuntimeError, match="single-writer"):
        ledger.check_disk()


def test_private_original_global_guard_precedes_any_input(monkeypatch):
    def reject(*_):
        raise RuntimeError("live controller")

    monkeypatch.setattr(private.previous.private, "assert_inactive", reject)
    with pytest.raises(RuntimeError, match="live controller"):
        private.audit_phase_two(Path("does-not-exist"), "a" * 64)


def test_strata_off_boundary_not_inferred_from_process_name_only(monkeypatch):
    def run(argv, **_):
        return SimpleNamespace(stdout=("ActiveState=active\nSubState=running\nMainPID=123\n"
                                      if argv[0] == "systemctl" else "llama-server\n"))

    monkeypatch.setattr(env.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="boundary changed"):
        env.require_strata_stopped()


def test_exclusion_wire_resolver_is_exact_and_never_rewrites_original(tmp_path, monkeypatch):
    monkeypatch.setattr(env.frozen, "ROOT", tmp_path)
    proof = {"raw": {"cell_id": env.CELL, "run_id": env.RUN, "attempt_index": 1,
                     "execution_sha256": "b" * 64, "disposition": "confounder",
                     "reason": "admission_unverifiable", "receipt_sha256": env.RAW_SHA},
             "reproduced_base_admission": {"disposition": "valid"}}
    path = tmp_path / "sidecar.json"
    path.write_text(json.dumps(proof))
    monkeypatch.setattr(env, "verify_exclusion", lambda *_: proof)
    original = {"disposition": "confounder"}
    monkeypatch.setattr(env, "RAW_SHA", env.provenance_sha256(original))

    def audit(_, resolve):
        directory = tmp_path / "evidence" / env.CELL / "attempt1"
        assert resolve(directory, original, {"disposition": "valid"}) == {"disposition": "valid"}
        assert resolve(directory / "other", original, {}) is original
        with pytest.raises(RuntimeError):
            resolve(directory, original, {"disposition": "confounder"})
        return {"checked": True}

    monkeypatch.setattr(env.wire, "audit_feedback", audit)
    assert env.audit_wire({}, path) == {"checked": True}
    assert original == {"disposition": "confounder"}


@pytest.mark.parametrize("damage", ["none", "tc", "worker", "error", "receipt", "model", "api"])
def test_actual_exclusion_proof_is_environment_only(tmp_path, monkeypatch, damage):
    monkeypatch.setattr(env.frozen, "ROOT", tmp_path)
    directory = tmp_path / "evidence" / env.CELL / "attempt1"
    directory.mkdir(parents=True)

    def save(name, value):
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))

    save("admission.json", {"disposition": "confounder", "reason": "admission_unverifiable",
                            "problems": ["FileNotFoundError"]})
    save("attempt-error.json", {"exception_type": "RuntimeError", "message": env.MESSAGE,
                                "before_runner": damage == "error"})
    save("process-exit.json", {"returncode": 1})
    save("worker-shutdown.json", {"verified_exited": damage != "worker"})
    save("tc-attestation.json", {"cleanup_error": None, "original_qdisc": {},
                                 "restored_qdisc": {"drift": True} if damage == "tc" else {}})
    if damage == "receipt":
        save("private/residency-validation.json", {"passed": True})
    before = {node: {"node": node, "instances": [{"target": {"instance": node},
              "server": {}, "runner": {}}], "gpu_compute_processes": None}
              for node in ("A4", "A5", "A28", "strong-4090")}
    before["strong-4090"]["gpu_compute_processes"] = [{"gpu_uuid": "gpu1", "pid": 10}]
    after = json.loads(json.dumps(before))
    after["strong-4090"]["gpu_compute_processes"] = [{"gpu_uuid": "gpu1", "pid": 20}]
    if damage == "model":
        after["A4"]["instances"][0]["runner"] = {"changed": True}
    save("private/residency-before.json", before)
    save("private/residency-after.json", after)
    authorization = tmp_path / "authorization.json"
    authorization.write_text(json.dumps({
        "version": "cell71-environment-replacement-user-authorization-v1", "run_id": env.RUN,
        "cell_id": env.CELL, "original_admission_sha256": env.RAW_SHA,
        "maximum_replacements": 1, "identical_execution_required": True,
        "original_attempt_preserved_as_invalid": True, "strata_coordinated_stopped": True,
        "semantic_retries": False}))
    (tmp_path / "phase2-control-freeze-001.json").write_text(json.dumps({
        "execution_freeze_sha256": "b" * 64, "pricing_path": "prices"}))
    monkeypatch.setattr(env, "sources", lambda: {"actual": "sha"})
    monkeypatch.setattr(env.frozen.frozen, "_yaml", lambda *_: {})
    base = {"disposition": "confounder" if damage == "api" else "valid", "problems": []}
    field = SimpleNamespace(core=SimpleNamespace(
        bindings=SimpleNamespace(frozen_sources=lambda *_: {
            "scripts/resident_model_pool_attestation_v1.py": env.cadence.digest(
                Path(env.resident.__file__))}, evidence_files=lambda *_: {}),
        previous=SimpleNamespace(execute_cell=SimpleNamespace(__globals__={
            "admission": lambda *_: base, "method_contract": SimpleNamespace(
                assert_E_tool_isolation=lambda *_: None)}))),
        base=SimpleNamespace(JsonlTraceWriter=lambda *_: SimpleNamespace(read_all=lambda: [])))
    monkeypatch.setattr(env, "field", field)
    attempt = Attempt(env.CELL, env.RUN, 1, "b" * 64, "confounder",
                      "admission_unverifiable", env.RAW_SHA)
    before_files = {str(p): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    if damage == "none":
        proof = env.prove_exclusion(attempt, authorization)
        assert proof["original_result_is_not_valid_baseline_sample"] is True
        assert proof["reproduced_base_admission"] == base
        assert proof["new_model_calls"] == 0
    else:
        with pytest.raises(RuntimeError):
            env.prove_exclusion(attempt, authorization)
    assert before_files == {str(p): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
