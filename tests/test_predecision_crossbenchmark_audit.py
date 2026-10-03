import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from predecision_crossbenchmark_audit_v1 import (  # noqa: E402
    audit_external_hard_stop,
    audited_validation,
    effective_attempt,
    provenance_checks,
)
from predecision_crossbenchmark_audit_v1 import (
    main as audit_main,
)
from predecision_crossbenchmark_continue_v1 import (  # noqa: E402
    remaining_cells,
    require_clean_attempt,
)
from test_predecision_crossbenchmark import protocol  # noqa: E402

from infra_joint.control.native_agents import _deterministic_terminal_answer
from infra_joint.control.provenance import provenance_sha256
from infra_joint.core.task import OutputContract, OutputFormat


def test_external_hard_stop_is_preserved_and_hash_validated(tmp_path: Path) -> None:
    from hashlib import sha256

    directory = tmp_path / "primary"
    trace = directory / "runs/run-1/trace.jsonl"
    trace.parent.mkdir(parents=True)
    trace.write_bytes(b"{}\n")
    cleanup = directory / "private/hard-stop-artifact-and-cleanup-audit.json"
    cleanup.parent.mkdir()
    cleanup.write_bytes(b"{}")
    result = {
        "result_type": "external_hard_stop_record_not_a_normal_benchmark_result",
        "run_id": "run-1", "failure_class": "system/harness confounder",
        "execution_completed": False, "evaluation": None,
        "trace_sha256": sha256(trace.read_bytes()).hexdigest(),
        "cleanup_audit_sha256": sha256(cleanup.read_bytes()).hexdigest(),
    }
    (directory / "hard-stop-result.json").write_text(json.dumps(result))
    assert audit_external_hard_stop(directory)["result"] == result
    trace.write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        audit_external_hard_stop(directory)


def test_complete_matrix_accepts_preserved_aborted_primary_not_a_fake_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    cell = "longbench-multidoc-financial-fast-blind"
    primary = root / "evidence" / cell / "primary"
    patch = root / "evidence" / cell / "isolation-patch-1"
    primary.mkdir(parents=True)
    patch.mkdir()
    (primary / "hard-stop-result.json").write_text("{}")
    (patch / "lightweight-validation.json").write_text("{}")
    one_cell_protocol = {"tasks": [{"label": "longbench-multidoc-financial"}]}
    output = tmp_path / "merged.json"
    monkeypatch.setattr("predecision_crossbenchmark_audit_v1.CONDITIONS", ("fast-blind",))
    monkeypatch.setattr("predecision_crossbenchmark_audit_v1._yaml", lambda _: one_cell_protocol)
    monkeypatch.setattr("predecision_crossbenchmark_audit_v1.audit_cell",
                        lambda _: {**clean_record(), "attempt": "isolation-patch-1"})
    monkeypatch.setattr("predecision_crossbenchmark_audit_v1.audit_external_hard_stop",
                        lambda _: {"attempt": "primary", "result": {"evaluation": None}})
    monkeypatch.setattr(sys, "argv", [
        "audit", "--root", str(root), "--output", str(output), "--require-complete",
    ])
    audit_main()
    merged = json.loads(output.read_text())
    assert merged["records"] == []  # No fabricated normal primary result.
    assert len(merged["effective_records"]) == len(merged["aborted_attempt_records"]) == 1
    assert merged["missing_primary_cells"] == merged["unresolved_cells"] == []


def test_external_backend_retry_evidence_excludes_without_rewriting_result(tmp_path: Path) -> None:
    original = {"problems": []}
    validation = tmp_path / "lightweight-validation.json"
    validation.write_text(json.dumps(original))
    assert audited_validation(tmp_path, "run-1") == original
    (tmp_path / "private").mkdir()
    (tmp_path / "private/execution-incidents.json").write_text(json.dumps({
        "run_id": "run-1", "incidents": [{"code": "hidden_backend_retry"}],
    }))
    record = clean_record()
    record["validation"] = audited_validation(tmp_path, "run-1")
    assert effective_attempt([record]) is None
    assert json.loads(validation.read_text()) == original


def test_external_incident_wrong_run_identity_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "lightweight-validation.json").write_text(json.dumps({"problems": []}))
    (tmp_path / "private").mkdir()
    (tmp_path / "private/execution-incidents.json").write_text(json.dumps({
        "run_id": "wrong-run", "incidents": [{"code": "hidden_backend_retry"}],
    }))
    with pytest.raises(ValueError, match="identity mismatch"):
        audited_validation(tmp_path, "run-1")


def test_crossbenchmark_audit_verifies_actual_profile_timing_and_semantic_hashes() -> None:
    profile = {"network_class": "constrained"}
    items = [{"role": "user", "content": "alpha\u2028beta"}]
    context = {"task": {"objective": "question"}, "physical_profile": None}
    events = [
        {"event_type": "logical.profile.predecision", "payload": {
            "decision_id": "manager:1", "profile": profile,
        }},
        {"event_type": "logical.reasoning.input", "payload": {
            "logical_agent_id": "manager", "decision_id": "manager:1",
            "input_items": items, "input_sha256": provenance_sha256(items),
            "current_anonymous_profile": profile,
        }},
        {"event_type": "logical.verification.input", "payload": {
            "context": context, "context_sha256": provenance_sha256(context),
        }},
    ]
    assert provenance_checks(events, "aware")["pass"]
    assert not provenance_checks(list(reversed(events)), "aware")["pass"]
    assert not provenance_checks(events, "blind")["pass"]
    events[1]["payload"]["input_sha256"] = "bad"
    assert "reasoning input hash mismatch" in provenance_checks(events, "aware")["failures"]
    # Fixture records represent structured metadata, not provider reasoning.
    assert json.loads(json.dumps(items)) == items


def test_frozen_choice_contract_field_name_roundtrip_is_not_schema_alias_failure() -> None:
    original = OutputContract(format=OutputFormat.CHOICE, choices=("A", "B", "C", "D"))
    frozen_task_view = original.model_dump(mode="json")
    restored = OutputContract.model_validate(frozen_task_view, by_name=True)
    assert _deterministic_terminal_answer(restored, "A") == "A"


@pytest.mark.parametrize("owner,visibility", [
    ("specialist", "aware"), ("specialist", "blind"), ("manager", "blind"),
])
@pytest.mark.parametrize("profile", [None, {"network_class": "constrained"}])
def test_audit_checks_tool_result_context_not_only_direct_profile(
    owner: str, visibility: str, profile: dict[str, str] | None,
) -> None:
    items = [{"type": "function_call_output", "call_id": "call-1", "output": json.dumps({
        "succeeded": True, "physical_profile": profile,
    })}]
    events = [{"event_type": "logical.reasoning.input", "payload": {
        "logical_agent_id": "manager", "decision_id": "manager:1", "input_items": [],
        "input_sha256": provenance_sha256([]), "current_anonymous_profile": None,
    }}, {"event_type": "logical.reasoning.input", "payload": {
        "logical_agent_id": owner, "decision_id": "owner:1", "input_items": items,
        "input_sha256": provenance_sha256(items), "current_anonymous_profile": None,
    }}]
    # Manager timing is a separate gate; focus on recipient isolation finding here.
    failures = provenance_checks(events, visibility)["failures"]
    assert ("Blind recipient tool-result/profile leakage" in failures) == (profile is not None)


def clean_record() -> dict[str, Any]:
    return {"attempt": "primary", "validation": {"problems": []}, "probe_errors": [],
            "persistence": {"pass": True}, "provenance": {"pass": True},
            "summary": {"logical_privacy_pass": True},
            "terminal_answer_provenance_pass": True, "evaluation": {"benchmark_score": 0}}


def test_wrong_semantic_answer_is_not_replaced_or_discarded() -> None:
    record = clean_record()
    assert effective_attempt([record]) is record


def test_operational_replacement_excludes_but_preserves_confounded_primary() -> None:
    primary = clean_record()
    primary["probe_errors"] = [{"probe_error_type": "RemoteProtocolError"}]
    primary["validation"]["problems"] = ["observer probe incident"]
    replacement = clean_record()
    replacement["attempt"] = "operational-replacement-1"
    attempts = [primary, replacement]
    assert effective_attempt(attempts) is replacement
    assert len(attempts) == 2 and attempts[0] is primary


def test_no_clean_attempt_remains_unresolved_and_two_clean_attempts_rejected() -> None:
    record = clean_record()
    record["persistence"]["pass"] = False
    assert effective_attempt([record]) is None
    with pytest.raises(ValueError, match="multiple clean attempts"):
        effective_attempt([clean_record(), clean_record()])


@pytest.mark.parametrize("patch_attempt", [
    "transport-patch-1", "backend-client-patch-1", "isolation-patch-1",
])
def test_cross_revision_audit_preserves_old_attempts_and_selects_authorized_patch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, patch_attempt: str,
) -> None:
    old_root, new_root = tmp_path / "old", tmp_path / "patch"
    cell = "longbench-multidoc-financial-slow-aware"
    for root, attempt in ((old_root, "primary"), (old_root, "operational-replacement-1"),
                          (new_root, patch_attempt)):
        directory = root / "evidence" / cell / attempt
        directory.mkdir(parents=True)
        (directory / "lightweight-validation.json").write_text("{}")

    def audit(directory: Path) -> dict[str, Any]:
        record = clean_record()
        record["attempt"] = directory.name
        if directory.name != patch_attempt:
            record["probe_errors"] = [{"probe_error_type": "RemoteProtocolError"}]
        return record

    output = tmp_path / "merged.json"
    monkeypatch.setattr("predecision_crossbenchmark_audit_v1.audit_cell", audit)
    monkeypatch.setattr("predecision_crossbenchmark_audit_v1._yaml", lambda _: protocol())
    monkeypatch.setattr(sys, "argv", [
        "audit", "--root", str(new_root), "--previous-root", str(old_root),
        "--protocol", "new-protocol.yaml", "--output", str(output),
    ])
    audit_main()
    merged = json.loads(output.read_text())
    assert len(merged["attempt_records"]) == 3
    assert len(merged["records"]) == len(merged["effective_records"]) == 1
    assert merged["records"][0]["attempt"] == "primary"
    assert merged["effective_records"][0]["attempt"] == patch_attempt
    assert merged["scope_roots"] == [str(old_root), str(new_root)]
    assert len(merged["unresolved_cells"]) == 23


def test_continuation_is_exact_unexecuted_suffix_not_a_matrix_rerun() -> None:
    cells = remaining_cells(protocol(), "longbench-multidoc-financial-slow-aware")
    assert len(cells) == 20
    assert cells[0] == "longbench-multidoc-academic-fast-blind"
    assert cells[-1] == "video-mme-795-2-slow-aware"
    assert all("financial" not in cell for cell in cells)
    with pytest.raises(ValueError, match="boundary"):
        remaining_cells(protocol(), "unknown")


def test_continuation_boundary_requires_audited_clean_shutdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = clean_record()
    monkeypatch.setattr("predecision_crossbenchmark_continue_v1.audit_cell", lambda _: record)
    shutdown = tmp_path / "worker-shutdown.json"
    shutdown.write_text(json.dumps({"errors": []}))
    require_clean_attempt(tmp_path)
    changed = deepcopy(record)
    changed["probe_errors"] = [{"probe_error_type": "RemoteProtocolError"}]
    monkeypatch.setattr("predecision_crossbenchmark_continue_v1.audit_cell", lambda _: changed)
    with pytest.raises(RuntimeError, match="requires audit"):
        require_clean_attempt(tmp_path)
    monkeypatch.setattr("predecision_crossbenchmark_continue_v1.audit_cell", lambda _: record)
    shutdown.write_text(json.dumps({"errors": ["still running"]}))
    with pytest.raises(RuntimeError, match="shutdown"):
        require_clean_attempt(tmp_path)
