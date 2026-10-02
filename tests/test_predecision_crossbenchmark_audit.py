import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from predecision_crossbenchmark_audit_v1 import provenance_checks  # noqa: E402

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
