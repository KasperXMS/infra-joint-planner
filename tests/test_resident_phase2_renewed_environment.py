import importlib
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from infra_joint.experiments.attempt_ledger import AttemptLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
renewed = importlib.import_module("large_scale_resident_phase2_renewed_environment_v1")
environment = renewed.environment
original_collect = renewed.collect


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


class SyntheticHistory(AttemptLedger):
    """Build raw history previously admitted by successive source-bound views."""

    def _check_reservation(self, cell_id):
        pass


@pytest.fixture
def history(tmp_path, monkeypatch):
    monkeypatch.setattr(renewed.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(environment, "CELL", "cell-0")
    monkeypatch.setattr(environment, "RUN", "excluded-original")
    monkeypatch.setattr(renewed.frozen, "require_remote", lambda: None)
    monkeypatch.setattr(environment, "require_strata_stopped", lambda: None)
    monkeypatch.setattr(environment, "sources", lambda: {"original-env": "source"})
    monkeypatch.setattr(renewed.previous, "sources", lambda: {"derived-env": "source"})
    monkeypatch.setattr(renewed, "sources", lambda: {"renewed-env": "source"})
    monkeypatch.setattr(renewed.field, "sources", lambda: {"original-field": "source"})
    monkeypatch.setattr(renewed.frozen, "reference", lambda: {"fixed": True})
    monkeypatch.setattr(renewed.frozen, "verify_freeze", lambda: "b" * 64)
    calls = []
    monkeypatch.setattr(renewed.field.core.previous.gate.evidence.private, "assert_inactive",
                        lambda *_: calls.append("inactive"))
    monkeypatch.setattr(renewed.field.review.parent, "validate", lambda *_: None)
    cells = tuple(SimpleNamespace(cell_id=f"cell-{i}") for i in range(20))
    gate = save(tmp_path / "gate.json", {"schedule": [{"cell_id": c.cell_id} for c in cells]})
    prices = save(tmp_path / "prices.json", {})
    parent_path = tmp_path / "phase2-control-freeze-001.json"
    parent = {"execution_freeze_sha256": "b" * 64, "phase2_schedule_sha256": "a" * 64,
              "nominal_cells": len(cells), "gate_path": str(gate), "pricing_path": str(prices)}
    save(parent_path, parent)
    monkeypatch.setattr(renewed.field.core.previous, "checked_control", lambda *_: (parent, cells))
    raw = SyntheticHistory(tmp_path / "phase2-attempts.jsonl",
                           tuple(c.cell_id for c in cells), "a" * 64)
    raw.reserve("cell-0", environment.RUN, "b" * 64)
    raw.settle(environment.RUN, "confounder", "admission_unverifiable", environment.RAW_SHA)
    sidecar = save(tmp_path / environment.DIRECTORY / (environment.RUN + ".json"), {})
    exclusion = {"raw": asdict(raw.attempts[0]), "effective": asdict(replace(
        raw.attempts[0], disposition="operational_excluded", reason=environment.REASON,
        receipt_sha256=renewed.cadence.digest(sidecar)))}
    raw.reserve("cell-0", "replacement", "b" * 64)
    raw.settle("replacement", "valid", "wrong_answer", "c" * 64)
    reviewers = ((renewed.field.core.DIRECTORY, renewed.field.core,
                  renewed.field.core.legacy.REVIEW_REASON),
                 (renewed.field.review.DIRECTORY, renewed.field.review,
                  renewed.field.review.field.REASON),
                 (renewed.previous.derived.DIRECTORY, renewed.previous.derived,
                  renewed.previous.derived.REASON))

    def add(run, cell, group):
        raw.reserve(cell, run, "b" * 64)
        raw.settle(run, "confounder", "exact-gate", "d" * 64)
        path = save(tmp_path / reviewers[group][0] / (run + ".json"), {
            "run_id": run, "reviewed_admission_sha256": "e" * 64,
            "field_misuse_proof": [{"action": i} for i in range(3)],
            "derived_field_proof": [{"action": i} for i in range(2)],
            "reviewed_admission": {"disposition": "valid", "reason": reviewers[group][2]}})
        original = raw.attempts[-1]
        pair = {"raw": asdict(original), "effective": asdict(replace(
            original, disposition="valid", reason=reviewers[group][2],
            receipt_sha256="e" * 64))}
        return path, pair

    model, model_pair = add("model", "cell-1", 0)
    initial, initial_pair = add("initial", "cell-2", 1)
    baseline_original = raw.path.read_bytes()
    original_ids = [a.run_id for a in raw.attempts]
    old_inventory = {"model_json_sidecars": {model.name: renewed.cadence.digest(model)},
                     "initial_field_sidecars": {initial.name: renewed.cadence.digest(initial)},
                     "derived_field_sidecars": {}}
    model_control = tmp_path / "phase2-reviewed-control-freeze-001.json"
    model_receipt = save(tmp_path / "phase2-ledger-read-once-freeze-001.json", {})
    save(model_control, {
        "version": "resident-phase2-exact-model-json-continuation-v1",
        "parent_control_path": str(parent_path),
        "parent_control_file_sha256": renewed.cadence.digest(parent_path),
        "sidecars": old_inventory["model_json_sidecars"],
        "source_sha256": {Path(p).name: renewed.cadence.digest(Path(p)) for p in (
            renewed.field.core.__file__, renewed.field.core.legacy.__file__,
            renewed.field.core.bindings.__file__)},
        "execution_freeze_sha256": "b" * 64, "phase2_schedule_sha256": "a" * 64,
        "nominal_cells": len(cells), "no_retry": True, "semantic_tuning": False,
        "prior_results_modified": False})
    old_control = tmp_path / "phase2-field-reviewed-control-freeze-005.json"
    old_receipt = tmp_path / "phase2-field-ledger-freeze-005.json"
    save(old_control, renewed.field.control_bindings(parent_path, parent,
                                                    model_control, model_receipt))
    save(old_receipt, renewed.field.freeze_value(old_control))
    references = {parent_path, gate, prices, model_control, model_receipt,
                  old_control, old_receipt, sidecar, model, initial}
    original = {"version": renewed.BASE_VERSION, "interval": renewed.cadence.INTERVAL,
                "parent": parent, "control_path": str(old_control),
                "ledger_path": str(old_receipt), "sidecar_path": str(sidecar),
                "source_sha256": environment.sources(),
                "historical_reviews": [initial_pair, model_pair], "exclusion": exclusion,
                "baseline_journal_bytes": len(baseline_original),
                "baseline_journal_sha256": renewed.cadence.digest(raw.path),
                "baseline_run_ids": original_ids,
                "bound_metadata_files": {str(p): renewed.cadence.digest(p) for p in references},
                "reference_sha256": renewed.provenance_sha256(renewed.frozen.reference()),
                "model_json_sidecars": old_inventory["model_json_sidecars"],
                "initial_field_sidecars": old_inventory["initial_field_sidecars"],
                "maximum_cell71_replacements": 1, "atomic_execution_changed": False,
                "private_body_guard_changed": False, "semantic_tuning": False,
                "new_findings_stop_immediately": True}
    original_path = save(tmp_path / (environment.PREFIX + "002.json"), original)
    derived_path, derived_pair = add("derived81", "cell-3", 2)
    references |= {original_path, derived_path}
    derived = {**original, "extension_version": renewed.previous.VERSION,
               "source_sha256": renewed.previous.sources(),
               "derived_field_sidecars": {derived_path.name: renewed.cadence.digest(derived_path)},
               "historical_reviews": [*original["historical_reviews"], derived_pair],
               "parent_environment_manifest_path": str(original_path),
               "parent_environment_manifest_sha256": renewed.cadence.digest(original_path),
               "baseline_journal_bytes": len(raw.path.read_bytes()),
               "baseline_journal_sha256": renewed.cadence.digest(raw.path),
               "bound_metadata_files": {str(p): renewed.cadence.digest(p) for p in references}}
    derived_manifest = save(tmp_path / (renewed.previous.PREFIX + "001.json"), derived)
    added_path, added_pair = add("initial84", "cell-4", 1)

    for _directory, reviewer, _reason in reviewers:
        def verify(path, attempt):
            value = renewed.read(path)
            assert value["run_id"] == attempt.run_id and attempt.disposition == "confounder"
            calls.append(attempt.run_id)
            return value

        monkeypatch.setattr(reviewer, "verify_sidecar", verify)

    def verify_exclusion(path, attempt):
        assert path == sidecar and asdict(attempt) == exclusion["raw"]
        calls.append("exclusion")
        return {}

    monkeypatch.setattr(environment, "verify_exclusion", verify_exclusion)
    monkeypatch.setattr(renewed, "collect", lambda _value, ledger: {
        "preserved": len(ledger.original_attempts), "admitted": len(ledger.completed_cells)})
    monkeypatch.setattr(environment, "audit_wire", lambda projection, _sidecar: calls.append(
        ("all-wire", projection)))
    return SimpleNamespace(root=tmp_path, raw=raw, cells=cells, parent=parent, sidecar=sidecar,
                           original_path=original_path, original=original, old_control=old_control,
                           derived_manifest=derived_manifest, derived=derived,
                           added_path=added_path,
                           added_pair=added_pair, calls=calls, add=add)


def renew(history, suffix="001", control_suffix="006", parent=None):
    old = history.derived_manifest if parent is None else parent
    return renewed.freeze(old, renewed.cadence.digest(old),
                          history.root / ("phase2-field-reviewed-control-freeze-"
                                          + control_suffix + ".json"),
                          history.root / ("phase2-field-ledger-freeze-" + control_suffix + ".json"),
                          history.root / (renewed.PREFIX + suffix + ".json"))


def test_original_helpers_create_exact_control_receipt_and_preserve_ancestors(history):
    before = {p: p.read_bytes() for p in history.root.rglob("*") if p.is_file()}
    result = renew(history)
    output = history.root / (renewed.PREFIX + "001.json")
    renewed.fence(output, renewed.cadence.digest(output), result)
    assert renewed.read(output) == result
    assert result["historical_reviews"] == [*history.derived["historical_reviews"],
                                             history.added_pair]
    assert result["exclusion"] == history.derived["exclusion"]
    assert result["baseline_run_ids"] == history.original["baseline_run_ids"]
    assert result["derived_field_sidecars"] == history.derived["derived_field_sidecars"]
    assert result["new_review_sidecars"] == {
        "model_json_sidecars": {}, "initial_field_sidecars": {
            "initial84.json": renewed.cadence.digest(history.added_path)},
        "derived_field_sidecars": {}}
    control, receipt = Path(result["control_path"]), Path(result["ledger_path"])
    assert renewed.read(control)["initial_field_sidecars"] == result["initial_field_sidecars"]
    renewed.field.validate(control, receipt)
    assert renewed.read(receipt) == renewed.field.freeze_value(control)
    assert result["baseline_journal_bytes"] == len(before[history.raw.path])
    assert all(p.read_bytes() == data for p, data in before.items())
    assert ("all-wire", {"preserved": 6, "admitted": 5}) in history.calls
    assert all(name in history.calls for name in ("model", "initial", "derived81", "initial84"))


def test_old_control_remains_historically_valid_but_cannot_dispatch_current_inventory(history):
    old_sidecars_function = renewed.field.control_bindings.__globals__["sidecars"]
    assert renewed.historical_control(history.derived) == renewed.read(history.old_control)
    with pytest.raises(RuntimeError, match="combined continuation control"):
        renewed.full_control(history.old_control, history.sidecar,
                             history.derived["derived_field_sidecars"])
    with pytest.raises(RuntimeError, match="immutable source/evidence drift"):
        renewed.previous.fence(history.derived_manifest,
                               renewed.cadence.digest(history.derived_manifest), history.derived)
    assert renewed.field.control_bindings.__globals__["sidecars"] is old_sidecars_function


def test_same_adapter_supports_a_second_append_only_renewal(history):
    first = renew(history)
    first_path = history.root / (renewed.PREFIX + "001.json")
    preserved = {p: p.read_bytes() for p in history.root.rglob("*") if p.is_file()}
    new_path, new_pair = history.add("initial85", "cell-5", 1)
    second = renew(history, "002", "007", first_path)
    second_path = history.root / (renewed.PREFIX + "002.json")
    renewed.fence(second_path, renewed.cadence.digest(second_path), second)
    assert second["historical_reviews"] == [*first["historical_reviews"], new_pair]
    assert second["new_review_sidecars"]["initial_field_sidecars"] == {
        new_path.name: renewed.cadence.digest(new_path)}
    assert second["parent_environment_manifest_path"] == str(first_path)
    assert second["baseline_run_ids"] == first["baseline_run_ids"]
    assert all(p.read_bytes() == data for p, data in preserved.items() if p != history.raw.path)


@pytest.mark.parametrize("damage", ["unmatched_sidecar", "new_unproved_finding", "pending"])
def test_current_inventory_has_no_wildcard_admission_and_never_creates_control(history, damage):
    if damage == "unmatched_sidecar":
        save(history.added_path.with_name("unmatched.json"), {})
    else:
        history.raw.reserve("cell-5", "new-unproved", "b" * 64)
        if damage != "pending":
            history.raw.settle("new-unproved", "confounder", "new-gate", "f" * 64)
    with pytest.raises(RuntimeError, match="disjoint exact|pending/new finding"):
        renew(history)
    assert not (history.root / "phase2-field-reviewed-control-freeze-006.json").exists()
    assert not (history.root / (renewed.PREFIX + "001.json")).exists()


def test_matching_new_hash_does_not_replace_independent_source_proof(history, monkeypatch):
    original = renewed.field.review.verify_sidecar

    def reject(path, attempt):
        if attempt.run_id == "initial84":
            raise RuntimeError("actual evidence source proof failed")
        return original(path, attempt)

    monkeypatch.setattr(renewed.field.review, "verify_sidecar", reject)
    with pytest.raises(RuntimeError, match="source proof failed"):
        renew(history)
    assert not (history.root / "phase2-field-reviewed-control-freeze-006.json").exists()


@pytest.mark.parametrize("damage", ["source", "ancestor_source", "metadata", "old_sidecar",
                                     "prefix", "reference", "execution", "exclusion"])
def test_historical_chain_source_metadata_evidence_and_prefix_remain_exact(history, monkeypatch,
                                                                         damage):
    if damage == "source":
        monkeypatch.setattr(renewed.previous, "sources", lambda: {"changed": "source"})
    elif damage == "ancestor_source":
        monkeypatch.setattr(environment, "sources", lambda: {"changed": "source"})
    elif damage == "metadata":
        save(history.old_control, {"changed": True})
    elif damage == "old_sidecar":
        path = history.root / renewed.field.review.DIRECTORY / "initial.json"
        save(path, {"changed": True})
    elif damage == "prefix":
        history.raw.path.write_bytes(history.raw.path.read_bytes().replace(
            b"excluded-original", b"excluded-modified"))
    elif damage == "reference":
        monkeypatch.setattr(renewed.frozen, "reference", lambda: {"changed": True})
    elif damage == "execution":
        monkeypatch.setattr(renewed.frozen, "verify_freeze", lambda: "f" * 64)
    else:
        save(history.sidecar, {"changed": True})
    with pytest.raises(RuntimeError):
        renew(history)
    assert not (history.root / (renewed.PREFIX + "001.json")).exists()


def test_current_fence_rejects_inventory_growth_until_explicit_renewal(history):
    result = renew(history)
    path = history.root / (renewed.PREFIX + "001.json")
    history.add("initial85", "cell-5", 1)
    with pytest.raises(RuntimeError, match="current renewal manifest/inventory drift"):
        renewed.fence(path, renewed.cadence.digest(path), result)


def test_creator_never_overwrites_and_requires_nonempty_additions(history):
    result = renew(history)
    path = history.root / (renewed.PREFIX + "001.json")
    with pytest.raises(FileExistsError):
        renew(history)
    with pytest.raises(RuntimeError, match="new review sidecars required"):
        renew(history, "002", "007", path)
    assert renewed.read(path) == result


def test_precreated_control_receipt_are_verified_and_reused(history):
    control = history.root / "phase2-field-reviewed-control-freeze-006.json"
    receipt = history.root / "phase2-field-ledger-freeze-006.json"
    old = renewed.read(history.old_control)
    save(control, renewed.field.control_bindings(Path(old["parent_control_path"]), history.parent,
                                                Path(old["preserved_model_control_path"]),
                                                Path(old["preserved_model_ledger_path"])))
    save(receipt, renewed.field.freeze_value(control))
    before = (control.read_bytes(), receipt.read_bytes())
    result = renew(history)
    assert (control.read_bytes(), receipt.read_bytes()) == before
    assert result["control_path"] == str(control)


def test_renewed_ledger_keeps_original_cap_cadence_and_new_finding_stop(history):
    result = renew(history)
    ledger = renewed.membership({**renewed.read(Path(result["control_path"])),
                                 "derived_field_sidecars": result["derived_field_sidecars"]},
                                history.cells, history.sidecar, require_dispatch_ready=True)
    with pytest.raises(RuntimeError, match="exhausted"):
        ledger.reserve(environment.CELL, "third", "b" * 64)
    checkpoints = []

    def execute(cell):
        ledger.reserve(cell.cell_id, cell.cell_id + "-new", "b" * 64)
        ledger.settle(cell.cell_id + "-new", "valid", "wrong_answer", "f" * 64)

    environment.run_batches(history.cells, ledger, execute, lambda: None,
                            lambda: checkpoints.append(len(ledger.completed_cells)))
    assert checkpoints == [16, 20]
    assert ledger.original_attempts[0].disposition == "confounder"


def test_initial_proof_telemetry_comes_from_hash_pinned_sidecar(history, monkeypatch):
    result = renew(history)
    ledger = renewed.membership({**renewed.read(Path(result["control_path"])),
                                 "derived_field_sidecars": result["derived_field_sidecars"]},
                                history.cells, history.sidecar, require_dispatch_ready=True)
    monkeypatch.setattr(renewed, "collect", original_collect)
    monkeypatch.setattr(renewed.previous, "collect", lambda *_: {"rows": [{"attempts": [{
        "run_id": "initial84", "reason": renewed.field.review.field.REASON,
        "receipt_sha256": "e" * 64, "original_disposition": "confounder"}]}]})
    projection = renewed.collect(result, ledger)
    assert projection["confirmed_initial_absent_record_field_failures"] == 3
    record = projection["rows"][0]["attempts"][0]
    assert record["confirmed_absent_record_field_failures"] == 3
    assert record["original_disposition"] == "confounder"
    save(history.added_path, {"reviewed_admission_sha256": "e" * 64,
                              "field_misuse_proof": []})
    with pytest.raises(RuntimeError, match="initial-field proof/receipt drift"):
        renewed.collect(result, ledger)


def test_inactive_guard_and_registered_startup_precede_input(tmp_path, monkeypatch):
    monkeypatch.setattr(renewed.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(renewed.frozen, "require_remote", lambda: None)

    def reject(*_):
        raise RuntimeError("original global live-process guard")

    monkeypatch.setattr(renewed.field.core.previous.gate.evidence.private,
                        "assert_inactive", reject)
    with pytest.raises(RuntimeError, match="global live-process"):
        renewed.freeze(tmp_path / "absent", "a" * 64, tmp_path / "control",
                       tmp_path / "receipt", tmp_path / "manifest")
    original_module = environment.run.__globals__["MODULE"]
    original_startup_module = renewed.cadence.assert_startup_safe.__globals__["MODULE"]
    with pytest.raises(RuntimeError, match="owned launch-pinned"):
        renewed.run(tmp_path / "absent-invalid.json", "a" * 64)
    assert environment.run.__globals__["MODULE"] == original_module
    assert renewed.cadence.assert_startup_safe.__globals__["MODULE"] == original_startup_module
