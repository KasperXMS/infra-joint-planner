import importlib
import json
import sys
from itertools import product
from pathlib import Path

import pytest

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import AttemptLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
repair = importlib.import_module("large_scale_quote_repair_ledger_v1")


def fixture(root: Path) -> tuple[object, dict, list[dict], Path]:
    source = root / "app/src/infra_joint/control/quote.py"
    source.parent.mkdir(parents=True)
    source.write_text("synthetic frozen quote source", encoding="utf-8")
    freeze = {"source_sha256": {"src/infra_joint/control/quote.py": repair.sha256(source)}}
    (root / "execution-freeze-001.json").write_text(json.dumps(freeze), encoding="utf-8")
    ledger = repair.QuoteRepairAttemptLedger(root / "phase1-attempts.jsonl",
                                            ("cell-1", "cell-2", "cell-3"), "a" * 64)
    ledger.reserve("cell-1", "first", provenance_sha256(freeze))
    original = {"disposition": "valid", "reason": "completed_or_valid_semantic_failure",
                "problems": [], "original_evaluation": {"benchmark_score": 0}}
    ledger.settle("first", "valid", original["reason"], provenance_sha256(original))
    ledger.reserve("cell-2", "unaffected", provenance_sha256(freeze))
    ledger.settle("unaffected", "valid", "wrong_answer", "b" * 64)
    directory = root / "evidence/cell-1/attempt1"
    api = directory / "private/api"
    api.mkdir(parents=True)
    call = {"id": "commit", "function": {"name": "commit_quote",
                                           "arguments": json.dumps({"quote_id": "quote"})}}
    (api / "response-response.json").write_text(json.dumps({"choices": [
        {"message": {"tool_calls": [call]}}]}), encoding="utf-8")
    action = {"action_type": "model", "action_id": "manager:propose",
              "prompt": "PRIVATE-PROMPT 中文", "requirements": {"modalities": ["image", "text"],
                                                          "required_capabilities": ["model"]}}
    events = [
        {"event_type": "logical.cost_quote.created", "payload": {"action": action, "quote": {
            "quote_id": "quote", "action_sha256": repair.original_action_sha256(action)}}},
        {"event_type": "logical.cost_quote.control_timing", "payload": {
            "operation": "authorize", "identifier": "quote", "succeeded": False}},
        {"event_type": "logical.cost_quote.rejected", "payload": {
            "failure_code": "quoted_action_mutated", "action_id": "manager:commit"}},
    ]
    run = directory / "runs/first"
    run.mkdir(parents=True)
    (run / "trace.jsonl").write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
    (directory / "admission.json").write_text(json.dumps(original), encoding="utf-8")
    return ledger, original, events, api


def sidecar(root: Path, ledger: object, original: dict, events: list[dict], api: Path) -> Path:
    attempt = ledger.attempts[0]
    directory = root / "evidence/cell-1/attempt1"
    value = repair.review(original, events, api)
    value.update({
        "run_id": "first", "original_admission_sha256": attempt.receipt_sha256,
        "original_execution_sha256": attempt.execution_sha256,
        "frozen_quote_source_sha256": repair.sha256(root / "app/src/infra_joint/control/quote.py"),
        "reviewer_source_sha256": repair.sha256(Path(repair.__file__)),
        "original_evidence_file_sha256": {str(p.relative_to(directory)): repair.sha256(p)
                                         for p in directory.rglob("*") if p.is_file()},
        "reviewed_admission_sha256": provenance_sha256(value["reviewed_admission"]),
    })
    path = root / repair.DIRECTORY / "first.json"
    path.parent.mkdir()
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_retrospective_confounder_is_append_only_and_allows_only_frozen_repair(
    tmp_path: Path,
) -> None:
    ledger, original, events, api = fixture(tmp_path)
    review_file = sidecar(tmp_path, ledger, original, events, api)
    journal = tmp_path / "phase1-attempts.jsonl"
    before = journal.read_bytes()
    evidence = (api / "response-response.json").read_bytes()
    ledger.invalidate_quote_integrity("first")
    assert journal.read_bytes().startswith(before)
    assert ledger.completed_cells == ("cell-2",)
    assert ledger.attempts[0].disposition == "confounder"
    for cell in ("cell-1", "cell-3"):
        with pytest.raises(RuntimeError, match="confounder"):
            ledger.reserve(cell, "illegal-retry", "c" * 64)
    corrected_hash = provenance_sha256(json.loads(review_file.read_text())["reviewed_admission"])
    ledger.authorize_generic_repair("first", original_admission_sha256=corrected_hash,
                                    repair_audit_sha256="d" * 64, new_execution_sha256="e" * 64)
    with pytest.raises(RuntimeError, match="audited new freeze"):
        ledger.reserve("cell-1", "old-freeze", "c" * 64)
    ledger.reserve("cell-1", "repaired", "e" * 64)
    ledger.settle("repaired", "valid", "wrong_answer", "f" * 64)
    reload = repair.QuoteRepairAttemptLedger(journal, ledger.cells, "a" * 64)
    assert reload.completed_cells == ("cell-1", "cell-2")
    with pytest.raises(RuntimeError, match="must not be repeated"):
        reload.reserve("cell-2", "repeat-unaffected", "e" * 64)
    reload.reserve("cell-3", "next", "e" * 64)
    assert (api / "response-response.json").read_bytes() == evidence
    assert json.loads((api.parent.parent / "admission.json").read_text()) == original


@pytest.mark.parametrize("damage", ["no-rejection", "commit-action", "hash", "single-set",
                                     "other-confounder", "other-operation", "receipt-encoding"])
def test_review_does_not_enable_semantic_retries_or_waive_other_faults(
    tmp_path: Path, damage: str,
) -> None:
    _, original, events, api = fixture(tmp_path)
    if damage == "no-rejection":
        events[-1]["payload"]["failure_code"] = "context_limit_exceeded"
    elif damage == "commit-action":
        path = api / "response-response.json"
        value = json.loads(path.read_text())
        value["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = json.dumps({
            "quote_id": "quote", "prompt": "change"})
        path.write_text(json.dumps(value))
    elif damage == "hash":
        events[0]["payload"]["quote"]["action_sha256"] = "0" * 64
    elif damage == "single-set":
        action = events[0]["payload"]["action"]
        action["requirements"]["modalities"] = ["text"]
        events[0]["payload"]["quote"]["action_sha256"] = repair.original_action_sha256(action)
    elif damage == "other-confounder":
        original["problems"] = ["privacy_violation"]
    elif damage == "receipt-encoding":
        events[0]["payload"]["quote"]["action_sha256"] = provenance_sha256(
            events[0]["payload"]["action"])
    else:
        events[1]["payload"]["operation"] = "discard"
    with pytest.raises(RuntimeError):
        repair.review(original, events, api)


@pytest.mark.parametrize("damage", ["evidence", "review", "source"])
def test_retrospective_proof_is_revalidated_after_reload(tmp_path: Path, damage: str) -> None:
    ledger, original, events, api = fixture(tmp_path)
    path = sidecar(tmp_path, ledger, original, events, api)
    ledger.invalidate_quote_integrity("first")
    if damage == "evidence":
        (api / "response-response.json").write_text("{}")
    elif damage == "review":
        value = json.loads(path.read_text())
        value["proof"] = []
        path.write_text(json.dumps(value))
    else:
        (tmp_path / "app/src/infra_joint/control/quote.py").write_text("changed")
    with pytest.raises(RuntimeError):
        repair.QuoteRepairAttemptLedger(tmp_path / "phase1-attempts.jsonl", ledger.cells, "a" * 64)


def test_pending_attempt_prevents_retrospective_state_changes(tmp_path: Path) -> None:
    ledger, original, events, api = fixture(tmp_path)
    sidecar(tmp_path, ledger, original, events, api)
    ledger.reserve("cell-3", "live", "c" * 64)
    before = (tmp_path / "phase1-attempts.jsonl").read_bytes()
    with pytest.raises(RuntimeError, match="still be live"):
        ledger.invalidate_quote_integrity("first")
    assert (tmp_path / "phase1-attempts.jsonl").read_bytes() == before


def test_completed_membership_validates_once_per_call_without_cross_call_cache(
    tmp_path: Path,
) -> None:
    class CountingLedger(repair.QuoteRepairAttemptLedger):
        validations = 0

        @property
        def attempts(self) -> tuple:
            self.validations += 1
            return super().attempts

    ledger = CountingLedger(tmp_path / "journal.jsonl", ("c", "a", "b"), "a" * 64)
    ledger._attempts = {
        "a": repair.Attempt("a", "a", 1, "b" * 64, "valid", "wrong_answer", "c" * 64),
        "c": repair.Attempt("c", "c", 1, "b" * 64, "valid", "correct", "c" * 64),
        "b": repair.Attempt("b", "b", 1, "b" * 64, "confounder", "fault", "c" * 64),
    }
    before = ledger.validations
    assert ledger.completed_cells == ("c", "a")
    assert ledger.validations == before + 1
    ledger._attempts["a"] = repair.Attempt("a", "a", 1, "b" * 64, "confounder")
    assert ledger.completed_cells == ("c",)
    assert ledger.validations == before + 2


def test_single_view_reservation_has_exact_base_gate_equivalence() -> None:
    class View(repair.QuoteRepairAttemptLedger):
        @property
        def attempts(self) -> tuple:
            return tuple(self._attempts.values())

    def outcome(method: object, view: View, cell: str) -> tuple | None:
        try:
            method(view, cell)
        except (ValueError, RuntimeError) as error:
            return type(error), str(error)
        return None

    cells = ("c", "a", "b")
    for states in product(("absent", "pending", "valid", "excluded", "confounder", "twice"),
                          repeat=3):
        for repairs in product((False, True), repeat=3):
            view = object.__new__(View)
            view.cells, view._attempts, view._repairs = cells, {}, {}
            for cell, state, repaired in zip(cells, states, repairs, strict=True):
                if state == "absent":
                    continue
                disposition = {"pending": None, "valid": "valid", "excluded":
                               "operational_excluded", "confounder": "confounder",
                               "twice": "operational_excluded"}[state]
                for index in range(2 if state == "twice" else 1):
                    run = cell + str(index)
                    view._attempts[run] = repair.Attempt(cell, run, index + 1, "a" * 64,
                                                         disposition)
                    if repaired:
                        view._repairs[run] = "b" * 64
            for cell in (*cells, "unknown"):
                assert outcome(View._check_reservation, view, cell) == outcome(
                    AttemptLedger._check_reservation, view, cell)


def test_reservation_view_revalidated_each_call_not_each_scheduled_cell(tmp_path: Path) -> None:
    class CountingView(repair.QuoteRepairAttemptLedger):
        validations = 0

        @property
        def attempts(self) -> tuple:
            self.validations += 1
            return super().attempts

    cells = tuple(f"cell-{index}" for index in range(168))
    view = CountingView(tmp_path / "journal.jsonl", cells, "a" * 64)
    before = view.validations
    view._check_reservation(cells[0])
    assert view.validations == before + 1
    view._check_reservation(cells[0])
    assert view.validations == before + 2
