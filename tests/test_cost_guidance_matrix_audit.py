import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from audit_cost_guidance_matrix_v1 import (  # noqa: E402
    admission,
    audit_matrix,
    digest,
    freeze_findings,
    trace_findings,
)


def test_adjudication_requires_exact_retained_hashes_without_erasing_original_gate(
    tmp_path: Path,
) -> None:
    result, trace = tmp_path / "result.json", tmp_path / "trace.jsonl"
    result.write_text('{"execution_completed":true}', encoding="utf-8")
    trace.write_text("retained trace", encoding="utf-8")
    gate = tmp_path / "lightweight-validation.json"
    gate.write_text(json.dumps({"problems": ["validation_failed requires audit"]}),
                    encoding="utf-8")
    original = gate.read_bytes()
    assert admission(tmp_path, result, trace)[0] == "audit_required"
    audit = {"effective_cell_retained": True, "rerun": False,
             "remaining_operational_gates_pass": True,
             "runtime_or_semantic_behavior_changed": False,
             "result_sha256": digest(result), "trace_sha256": digest(trace)}
    path = tmp_path / "postrun-eligibility-audit-001.json"
    path.write_text(json.dumps(audit), encoding="utf-8")
    assert admission(tmp_path, result, trace) == ("independently_adjudicated_retained", [])
    assert gate.read_bytes() == original
    audit["trace_sha256"] = "unproven"
    path.write_text(json.dumps(audit), encoding="utf-8")
    assert admission(tmp_path, result, trace)[0] == "audit_required"


def test_freeze_parity_checks_feedback_exposure_network_and_frozen_history(tmp_path: Path) -> None:
    history, history_manifest = tmp_path / "history.json", tmp_path / "history-manifest.json"
    history.write_text("original clean numeric history", encoding="utf-8")
    history_manifest.write_text("original lineage", encoding="utf-8")
    protocol = {"code_revision": "rev", "harness_sha256": "harness",
                "protocol_sha256": "protocol", "component_sha256": {"f": "sha"},
                "history_file": str(history), "history_manifest_file": str(history_manifest)}
    task = {"task_bundle_sha256": "task", "static_capability_sha256": "cap",
            "initial_placement": {"source": "edge"}, "source_manifest": {"corpus": "sha"}}
    manifest = {"code_revision": "rev", "task_bundle_sha256": "task",
                "static_capability_contract_sha256": "cap", "initial_placement": {"source": "edge"},
                "source_manifest": {"corpus": "sha"}, "harness_manifest_sha256": "harness",
                "profile_visibility": "blind", "repetitions": 1, "retry": False,
                "replacement": False, "scheduler": "auto_physical_locality_aware",
                "model_service_timeout_seconds": 1200.0, "network_regime": "slow",
                "bandwidth_mbps": 3, "added_rtt_ms": 50}
    method = {"method": "ledger-quote-v0", "protocol_sha256": "protocol",
              "component_sha256": {"f": "sha"}, "history_sha256": digest(history),
              "history_manifest_sha256": digest(history_manifest),
              "raw_dynamic_profile_injected": False, "specialists_and_verifier_blind": True}
    assert freeze_findings(manifest, method, task, protocol, "slow-quote") == []
    manifest["retry"] = True
    method["raw_dynamic_profile_injected"] = True
    history.write_text("changed after outcomes", encoding="utf-8")
    findings = freeze_findings(manifest, method, task, protocol, "slow-quote")
    assert "cell freeze mismatch: retry" in findings
    assert "method exposure contract mismatch" in findings
    assert "historical estimator freeze mismatch: history_sha256" in findings


def test_existing_incomplete_cell_is_not_replaced_or_admitted(tmp_path: Path) -> None:
    (tmp_path / "protocol-freeze.json").write_text(json.dumps({
        "component_sha256": {}, "tasks": [{"label": "task"}],
        "protocol": {"harness_manifest": "harness.json"}, "harness_sha256": "sha"}),
        encoding="utf-8")
    native = tmp_path / "app/src/infra_joint/control/native_agents.py"
    native.parent.mkdir(parents=True)
    native.write_text("synthetic source", encoding="utf-8")
    (tmp_path / "app/harness.json").write_text("synthetic harness", encoding="utf-8")
    with pytest.raises(RuntimeError, match="incomplete/ambiguous cell; never restart"):
        audit_matrix(tmp_path)
    assert not (tmp_path / "evidence").exists()


def test_operational_admission_does_not_select_on_benchmark_quality(tmp_path: Path) -> None:
    result, trace = tmp_path / "result.json", tmp_path / "trace.jsonl"
    result.write_text('{"execution_completed":true,"evaluation":{"benchmark_score":0}}',
                      encoding="utf-8")
    trace.write_text("retained failure trajectory", encoding="utf-8")
    (tmp_path / "lightweight-validation.json").write_text('{"problems":[]}', encoding="utf-8")
    assert admission(tmp_path, result, trace) == ("original_operational_checks_pass", [])


def test_trace_chain_audit_rejects_gaps_and_missing_terminal_without_reading_payloads() -> None:
    events = [
        {"run_id": "r", "step_id": "start", "parent_id": None,
         "timestamp": "t", "event_type": "task.start", "payload": {"private": "not exported"}},
        {"run_id": "r", "step_id": "end", "parent_id": "start",
         "timestamp": "t", "event_type": "run.end", "payload": {}},
    ]
    assert trace_findings(events, "r") == []
    events[1]["parent_id"] = "missing event"
    assert "trace parent chain broken" in trace_findings(events, "r")
    assert "trace terminal run end missing" in trace_findings(events[:1], "r")
    events[1]["step_id"] = "start"
    assert "missing/duplicate trace event identifier" in trace_findings(events, "r")
