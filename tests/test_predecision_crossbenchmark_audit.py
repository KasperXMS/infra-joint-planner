import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from predecision_crossbenchmark_audit_v1 import (  # noqa: E402
    effective_attempt,
    provenance_checks,
)
from predecision_crossbenchmark_continue_v1 import (  # noqa: E402
    remaining_cells,
    require_clean_attempt,
)
from test_predecision_crossbenchmark import protocol  # noqa: E402

from infra_joint.control.native_agents import _deterministic_terminal_answer
from infra_joint.control.provenance import provenance_sha256
from infra_joint.core.task import OutputContract, OutputFormat


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
