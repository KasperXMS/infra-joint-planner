import copy
import importlib
import json
import sys
from pathlib import Path

import pytest

from infra_joint.experiments.large_scale_protocol import (
    FAMILIES,
    METHODS,
    SelectedTask,
    phase_one_schedule,
    schedule_sha256,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
gate = importlib.import_module("large_scale_resident_phase2_gate_v1")


def bundle() -> dict:
    tasks = tuple(SelectedTask(f, f"synthetic-{f}-{i}", i)
                  for f in FAMILIES for i in range(1, 7))
    cells = phase_one_schedule(tasks, e_history_tasks=())
    freezes = {"1": gate.evidence.sources.resident.EXECUTION_FREEZE_SHA256,
               "2": gate.evidence.sources.REPAIR_SHA256, "3": "f" * 64}
    boundaries = list(gate.evidence.BOUNDARIES)
    rows = []
    reviews = []
    coverage = []
    bindings = {}
    for i, c in enumerate(cells):
        run = "synthetic-run-" + str(i)
        epoch = freezes[str(i % 3 + 1)]
        rows.append({
            "condition": {"cell_id": c.cell_id}, "pending_run_ids": [],
            "attempts": [{
                "run_id": run, "execution_sha256": epoch, "disposition": "valid",
                "comparative_sample_eligible": True, "admission_problems": [],
                "execution_source_boundary": boundaries[i % 3],
                "actual_recipient_contexts_audited": 5, "trace_file_sha256": "a" * 64,
                "execution_completed": True, "format_valid": True, "benchmark_score": 1,
            }],
        })
        bindings[c.cell_id] = {"trace": "a" * 64, "result": "b" * 64,
                               "admission": "c" * 64, "worker_shutdown": "d" * 64}
        reviews.append({
            "cell_id": c.cell_id, "run_id": run, "execution_sha256": epoch,
            **dict.fromkeys(gate.CHECKS, True), "semantic_summary": "Synthetic reviewed path",
            "evidence_file_sha256": bindings[c.cell_id], "recipient_contexts_audited": 5,
            "primary_cause": "not_applicable", "contributing_factors": [],
        })
        coverage.append({"cell_id": c.cell_id, "run_id": run, "execution_sha256": epoch,
                         "execution_source_boundary": boundaries[i % 3], "benchmark_score": 1})
    hashes = {"snapshot": "1" * 64, "private": "2" * 64,
              "audit": "3" * 64, "pruning": "4" * 64}
    reports = dict.fromkeys(gate.REPORTS, "5" * 64)
    return {
        "snapshot": {
            "scheduled_cells": 168, "admitted_cells": 168, "pending_count": 0,
            "phase1_complete": True, "rows": rows, "execution_freezes": freezes,
            "journal_sha256": "6" * 64,
        },
        "private": {
            "version": "resident-cardinality-private-evidence-paths-v1", "records": coverage,
            "journal_sha256": "6" * 64, "execution_freezes": freezes,
            "planner_or_model_calls": 0, "artifact_bodies_exported": False,
            "measured_execution_modified": False,
        },
        "audit": {
            "version": "resident-comprehensive-phase1-audit-v1", "complete": True,
            "unresolved_confounders": [], "journal_sha256": "6" * 64,
            "execution_freezes": freezes, "source_projection_sha256": hashes["snapshot"],
            "private_evidence_sha256": hashes["private"], "records": reviews,
            "report_file_sha256": reports,
        },
        "pruning": {
            "version": "resident-phase1-method-pruning-v1", "frozen": True,
            "comprehensive_audit_sha256": hashes["audit"], "journal_sha256": "6" * 64,
            "prior_substantive_cells": 42,
            "methods": [{"method": m, "status": "retain" if m in METHODS[:3] else "drop",
                         "rationale": "Synthetic evidence, not an actual pruning decision",
                         "supporting_run_ids": ["synthetic-run-0"],
                         "bases": ["interface_unused"]} for m in METHODS],
        },
        "selection": {
            "tasks": [{"family": t.family, "source_task_id": t.source_task_id,
                       "position": t.position} for t in tasks],
            "e_history_task_identities": [], "schedule_seed": 20261005,
            "phase1_schedule_sha256": schedule_sha256(cells),
        },
        "hashes": hashes, "bindings": bindings, "reports": reports,
    }


def test_verified_audit_freezes_exact_remaining_task_schedule_without_launch() -> None:
    inputs = bundle()
    before = copy.deepcopy(inputs)
    value = gate.validate_bundle(**inputs)
    assert inputs == before
    assert value["methods"] == ["B0", "B1", "A"]
    assert value["phase2_cells"] == 144
    assert value["planned_cumulative_substantive_cells"] == 354
    assert len({c["cell_id"] for c in value["schedule"]}) == 144
    assert all(c["phase"] == 2 and c["task"]["position"] >= 3 for c in value["schedule"])
    assert value["queue_launched"] is False
    assert value["planner_or_model_calls"] == 0


@pytest.mark.parametrize("defect", [
    "partial", "pending", "semantic_incomplete", "failure_incomplete", "recipient_incomplete",
    "adoption_incomplete", "manual_summary_missing", "wrong_run", "wrong_source",
    "trace_drift", "result_drift", "recipient_scan_count", "private_record_missing",
    "private_wrong_run", "private_calls", "private_export", "unresolved", "audit_not_complete",
    "audit_hash", "private_hash", "journal", "report_missing", "report_hash",
    "duplicate_review", "pruning_before_audit", "pruning_not_frozen", "prior_cap_ignored",
    "missing_method", "method_not_screened", "E2E_only", "unknown_pruning_evidence",
    "quality_zero_unclassified", "missing_evaluation_unclassified", "unknown_cause",
    "unknown_factor", "task_drift",
])
def test_no_placeholder_digest_or_incomplete_review_can_open_phase_two(defect: str) -> None:
    v = bundle()
    a = v["audit"]
    record = a["records"][0]
    attempt = v["snapshot"]["rows"][0]["attempts"][0]
    if defect == "partial":
        v["snapshot"]["admitted_cells"] = 167
    elif defect == "pending":
        v["snapshot"]["pending_count"] = 1
    elif defect.endswith("_incomplete"):
        record[defect.removesuffix("_incomplete") + "_review_complete"] = False
    elif defect == "manual_summary_missing":
        record["semantic_summary"] = " "
    elif defect == "wrong_run":
        record["run_id"] = "other"
    elif defect == "wrong_source":
        record["execution_sha256"] = "0" * 64
    elif defect in {"trace_drift", "result_drift"}:
        record["evidence_file_sha256"] = dict(record["evidence_file_sha256"])
        record["evidence_file_sha256"][defect.removesuffix("_drift")] = "0" * 64
    elif defect == "recipient_scan_count":
        record["recipient_contexts_audited"] = 4
    elif defect == "private_record_missing":
        v["private"]["records"].pop()
    elif defect == "private_wrong_run":
        v["private"]["records"][0]["run_id"] = "other"
    elif defect == "private_calls":
        v["private"]["planner_or_model_calls"] = 1
    elif defect == "private_export":
        v["private"]["artifact_bodies_exported"] = True
    elif defect == "unresolved":
        a["unresolved_confounders"] = ["privacy"]
    elif defect == "audit_not_complete":
        a["complete"] = False
    elif defect == "audit_hash":
        a["source_projection_sha256"] = "0" * 64
    elif defect == "private_hash":
        a["private_evidence_sha256"] = "0" * 64
    elif defect == "journal":
        a["journal_sha256"] = "0" * 64
    elif defect == "report_missing":
        v["reports"] = dict(v["reports"])
        v["reports"].pop("phase1_semantic_audit")
    elif defect == "report_hash":
        a["report_file_sha256"] = dict(v["reports"], phase1_failure_audit="0" * 64)
    elif defect == "duplicate_review":
        a["records"][1] = dict(a["records"][0])
    elif defect == "pruning_before_audit":
        v["pruning"]["comprehensive_audit_sha256"] = "0" * 64
    elif defect == "pruning_not_frozen":
        v["pruning"]["frozen"] = False
    elif defect == "prior_cap_ignored":
        v["pruning"]["prior_substantive_cells"] = 0
    elif defect == "missing_method":
        v["pruning"]["methods"].pop()
    elif defect == "method_not_screened":
        v["pruning"]["methods"][0]["status"] = "pending"
    elif defect == "E2E_only":
        v["pruning"]["methods"][-1]["bases"] = ["mean_E2E"]
    elif defect == "unknown_pruning_evidence":
        v["pruning"]["methods"][-1]["supporting_run_ids"] = ["not-a-real-run"]
    elif defect in {"quality_zero_unclassified", "missing_evaluation_unclassified"}:
        attempt["benchmark_score"] = 0 if defect.startswith("quality_zero") else None
    elif defect == "unknown_cause":
        record["primary_cause"] = "unknown"
    elif defect == "unknown_factor":
        record["contributing_factors"] = ["new_method"]
    elif defect == "task_drift":
        v["selection"]["tasks"][0]["source_task_id"] = "replacement"
    else:
        raise AssertionError(defect)
    with pytest.raises(RuntimeError):
        gate.validate_bundle(**v)


def test_quality_failure_is_preserved_when_manually_audited_not_replaced() -> None:
    v = bundle()
    v["snapshot"]["rows"][0]["attempts"][0]["benchmark_score"] = 0
    v["private"]["records"][0]["benchmark_score"] = 0
    v["audit"]["records"][0]["primary_cause"] = "retrieval_failure"
    assert gate.validate_bundle(**v)["phase2_cells"] == 144


def test_five_survivors_exceed_actual_cumulative_cap_but_four_fit() -> None:
    v = bundle()
    v["pruning"]["methods"][3]["status"] = "retain"
    assert gate.validate_bundle(**v)["planned_cumulative_substantive_cells"] == 402
    v["pruning"]["methods"][4]["status"] = "retain"
    with pytest.raises(ValueError, match="420"):
        gate.validate_bundle(**v)


def test_live_queue_blocks_gate_before_reading_any_inputs(monkeypatch, tmp_path: Path) -> None:
    def active(root):
        raise RuntimeError("queue live")

    monkeypatch.setattr(gate.evidence.private, "assert_inactive", active)
    monkeypatch.setattr(gate, "digest", lambda _: pytest.fail("must not read while queue live"))
    with pytest.raises(RuntimeError, match="queue live"):
        gate.freeze_gate({}, tmp_path / "gate.json")
    assert not (tmp_path / "gate.json").exists()


def file_bundle(monkeypatch, tmp_path: Path) -> tuple[dict[str, Path], Path]:
    """Synthetic local files exercise the offline I/O guard, never real evidence."""
    v = bundle()
    root = tmp_path / "resident"
    analysis = root / "analysis"
    analysis.mkdir(parents=True)
    predecessor = tmp_path / "predecessor"
    selection = predecessor / "preparation/task-freeze-002"
    selection.mkdir(parents=True)
    manifest = selection / "manifest.json"
    manifest.write_text(json.dumps(v["selection"]))
    monkeypatch.setattr(gate.sys, "platform", "linux")
    monkeypatch.setattr(gate.evidence.private, "ROOT", root)
    monkeypatch.setattr(gate.evidence.private, "PREDECESSOR", predecessor)
    monkeypatch.setattr(gate.evidence.private, "assert_inactive", lambda _: None)
    monkeypatch.setattr(gate.evidence.sources.resident, "TASK_FREEZE_SHA256", gate.digest(manifest))
    for i, row in enumerate(v["snapshot"]["rows"]):
        attempt = row["attempts"][0]
        attempt["attempt_index"] = 1
        directory = root / "evidence" / row["condition"]["cell_id"] / "attempt1"
        run = directory / "runs" / attempt["run_id"]
        run.mkdir(parents=True)
        files = {"trace": run / "trace.jsonl", "result": run / "result.json",
                 "admission": directory / "admission.json",
                 "worker_shutdown": directory / "worker-shutdown.json"}
        for name, path in files.items():
            path.write_text('{"verified_exited":true}' if name == "worker_shutdown" else '{}')
        v["audit"]["records"][i]["evidence_file_sha256"] = {
            n: gate.digest(p) for n, p in files.items()}
        attempt["trace_file_sha256"] = gate.digest(files["trace"])
    v["private"]["excluded_historical_run_ids"] = []
    v["private"]["audit_source_sha256"] = {Path(p).name: gate.digest(Path(p)) for p in (
        gate.evidence.__file__, gate.evidence.private.__file__,
        sys.modules[gate.evidence.resolved_membership.__module__].__file__,
        sys.modules[gate.evidence.private.scan_store.__module__].__file__,
    )}
    report_refs = {}
    for name in gate.REPORTS:
        path = analysis / (name + ".md")
        path.write_text("Synthetic report; NOT an actual result or screening decision.")
        report_refs[name] = {"filename": path.name, "sha256": gate.digest(path)}
    v["audit"]["report_files"] = report_refs
    v["audit"]["report_file_sha256"] = {n: ref["sha256"] for n, ref in report_refs.items()}
    paths = {name: analysis / (name + ".json") for name in ("snapshot", "private", "audit",
                                                          "pruning")}
    for name in ("snapshot", "private"):
        paths[name].write_text(json.dumps(v[name]))
    v["audit"]["source_projection_sha256"] = gate.digest(paths["snapshot"])
    v["audit"]["private_evidence_sha256"] = gate.digest(paths["private"])
    paths["audit"].write_text(json.dumps(v["audit"]))
    v["pruning"]["comprehensive_audit_sha256"] = gate.digest(paths["audit"])
    paths["pruning"].write_text(json.dumps(v["pruning"]))
    (root / "phase1-attempts.jsonl").write_text("synthetic journal\n")
    journal = gate.digest(root / "phase1-attempts.jsonl")
    for name in ("snapshot", "private", "audit", "pruning"):
        v[name]["journal_sha256"] = journal
    # Resolve digest dependencies in order after binding the real journal bytes.
    for name in ("snapshot", "private"):
        paths[name].write_text(json.dumps(v[name]))
    v["audit"]["source_projection_sha256"] = gate.digest(paths["snapshot"])
    v["audit"]["private_evidence_sha256"] = gate.digest(paths["private"])
    paths["audit"].write_text(json.dumps(v["audit"]))
    v["pruning"]["comprehensive_audit_sha256"] = gate.digest(paths["audit"])
    paths["pruning"].write_text(json.dumps(v["pruning"]))
    monkeypatch.setattr(gate.evidence.sources, "collect", lambda: copy.deepcopy(v["snapshot"]))
    return paths, analysis / "gate.json"


def test_actual_files_are_bound_and_output_cannot_be_overwritten(monkeypatch,
                                                               tmp_path: Path) -> None:
    paths, output = file_bundle(monkeypatch, tmp_path)
    result = gate.freeze_gate(paths, output)
    assert json.loads(output.read_text()) == result
    assert result["input_file_sha256"] == {n: gate.digest(p) for n, p in paths.items()}
    with pytest.raises(RuntimeError, match="append-only"):
        gate.freeze_gate(paths, output)


@pytest.mark.parametrize("defect", ["report", "source", "snapshot", "worker", "input_mutation",
                                     "journal_mutation", "queue_restart"])
def test_file_gate_rejects_real_drift_without_emitting_receipt(monkeypatch, tmp_path: Path,
                                                             defect: str) -> None:
    paths, output = file_bundle(monkeypatch, tmp_path)
    if defect == "report":
        (output.parent / "phase1_failure_audit.md").write_text("Changed report")
    elif defect == "source":
        private = json.loads(paths["private"].read_text())
        private["audit_source_sha256"] = {}
        paths["private"].write_text(json.dumps(private))
    elif defect == "snapshot":
        snapshot = json.loads(paths["snapshot"].read_text())
        snapshot["pending_count"] = 1
        paths["snapshot"].write_text(json.dumps(snapshot))
    elif defect == "worker":
        worker = next((output.parent.parent / "evidence").glob("*/attempt1/worker-shutdown.json"))
        worker.write_text('{"verified_exited":false}')
    elif defect in {"input_mutation", "journal_mutation"}:
        validate = gate.validate_bundle

        def after_validation(*args):
            value = validate(*args)
            target = paths["audit"] if defect == "input_mutation" else (
                output.parent.parent / "phase1-attempts.jsonl")
            target.write_text(target.read_text() + "\n")
            return value

        monkeypatch.setattr(gate, "validate_bundle", after_validation)
    elif defect == "queue_restart":
        checks = []

        def inactive(root):
            checks.append(root)
            if len(checks) == 2:
                raise RuntimeError("queue restarted")

        monkeypatch.setattr(gate.evidence.private, "assert_inactive", inactive)
    with pytest.raises(RuntimeError):
        gate.freeze_gate(paths, output)
    assert not output.exists()
