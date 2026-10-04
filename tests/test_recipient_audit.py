import json

import pytest

from infra_joint.control.bde_native import RULE_PREFIX
from infra_joint.control.ledger import LEDGER_MESSAGE_PREFIX
from infra_joint.control.provenance import PROFILE_MESSAGE_PREFIX, provenance_sha256
from infra_joint.experiments.recipient_audit import (
    audit_effective_inputs,
    scan_recipient_context,
)


def categories(value: object, recipient: str = "manager", method: str = "B0") -> set[str]:
    return {item.category for item in scan_recipient_context(
        value, recipient=recipient, method=method)}


@pytest.mark.parametrize("recipient", ["manager", "specialist", "verifier"])
def test_all_recipients_scan_nested_accumulated_tool_result(recipient: str) -> None:
    previous_tool_output = json.dumps({"observation": {"physical_profile": {
        "network_class": "constrained", "queue_pressure_range": [0, 1]}}})
    messages = [{"role": "tool", "content": previous_tool_output}]
    assert "dynamic_profile_leakage" in categories(messages, recipient)
    assert not categories([{"role": "tool", "content": json.dumps({
        "physical_profile": None, "succeeded": True})}], recipient)


@pytest.mark.parametrize("method", ["B0", "B1", "A", "B", "C", "D", "E"])
def test_only_B1_root_may_receive_anonymous_dynamic_profile(method: str) -> None:
    profile = [{"role": "user", "content": PROFILE_MESSAGE_PREFIX + json.dumps({
        "network_class": "fast", "queue_pressure_range": [0, 1]})}]
    assert bool(categories(profile, method=method)) == (method != "B1")
    for recipient in ("specialist", "verifier"):
        assert "dynamic_profile_leakage" in categories(profile, recipient, method)


@pytest.mark.parametrize("private_key", [
    "source_ref", "evaluator_id", "gold_answer", "supporting_evidence",
    "worker_id", "deployment_id", "selected_agent_id", "initial_placement",
])
def test_private_and_physical_fields_are_forbidden_even_inside_allowed_B1_feedback(
    private_key: str,
) -> None:
    profile = [{"role": "user", "content": PROFILE_MESSAGE_PREFIX + json.dumps({
        "network_class": "fast", private_key: "synthetic-private"})}]
    assert "private_or_physical_field" in categories(profile, method="B1")


def test_known_endpoint_scan_reports_path_not_identity_or_artifact_body() -> None:
    findings = scan_recipient_context(
        [{"role": "tool", "content": '{"message":"http://192.168.0.104:65004 leaked"}'}],
        recipient="specialist", method="B1", physical_identifiers=("192.168.0.104",))
    assert findings and "192.168" not in repr(findings)
    assert not scan_recipient_context(
        [{"role": "tool", "content": "Corpus discusses a public 203.0.113.7 example."}],
        recipient="specialist", method="B0", physical_identifiers=("192.168.0.104",))


def test_feedback_permissions_are_method_and_recipient_specific() -> None:
    ledger = [{"role": "user", "content": LEDGER_MESSAGE_PREFIX + "{}"}]
    quote = [{"role": "tool", "content": json.dumps({
        "quote_id": "q", "action_sha256": "a", "consequence": {}})}]
    rules = [{"role": "user", "content": RULE_PREFIX + '{"rules":[]}'}]
    card = [{"role": "tool", "content": json.dumps({"card_id": "c", "consequence": {}})}]
    for method in ("B0", "B1", "A", "B", "C", "D", "E"):
        assert bool(categories(ledger, method=method)) == (method in {"B0", "B1"})
        assert bool(categories(quote, method=method)) == (method not in {"C", "D"})
        assert bool(categories(card, method=method)) == (method not in {"B", "D", "E"})
        assert bool(categories(rules, method=method)) == (method != "E")
        for recipient in ("specialist", "verifier"):
            for feedback in (ledger, quote, rules, card):
                assert categories(feedback, recipient, method)


def reasoning(items: list[dict], *, profile: dict | None = None) -> dict:
    return {"event_type": "logical.reasoning.input", "payload": {
        "logical_agent_id": "manager", "decision_id": "d1", "input_items": items,
        "input_sha256": provenance_sha256(items), "current_anonymous_profile": profile}}


def test_B1_profile_must_precede_reasoning_and_match_exactly() -> None:
    profile = {"network_class": "fast"}
    message = {"role": "user", "content": PROFILE_MESSAGE_PREFIX + json.dumps(profile)}
    before = {"event_type": "logical.profile.predecision", "payload": {
        "decision_id": "d1", "profile": profile}}
    call = reasoning([message], profile=profile)
    assert not audit_effective_inputs([before, call], "B1")["problems"]
    assert audit_effective_inputs([call, before], "B1")["problems"]
    assert audit_effective_inputs([call], "B1")["problems"]
    before["payload"]["profile"] = {"network_class": "slow"}
    assert audit_effective_inputs([before, call], "B1")["problems"]


def test_provenance_and_exact_fresh_feedback_counts_fail_closed() -> None:
    ledger = {"role": "user", "content": LEDGER_MESSAGE_PREFIX + "{}"}
    assert not audit_effective_inputs([reasoning([ledger])], "A")["problems"]
    assert audit_effective_inputs([reasoning([])], "A")["problems"]
    assert audit_effective_inputs([reasoning([ledger, ledger])], "A")["problems"]
    assert audit_effective_inputs([reasoning([ledger])], "B0")["problems"]
    event = reasoning([])
    event["payload"]["input_sha256"] = "tampered"
    assert "effective_input_hash_mismatch" in audit_effective_inputs([event], "B0")["problems"]


def test_verifier_context_hash_and_historical_tool_feedback_are_both_checked() -> None:
    context = {"observations": [{"output": json.dumps({
        "card_id": "historical-card", "consequence": {}})}]}
    event = {"event_type": "logical.verification.input", "payload": {
        "context": context, "context_sha256": provenance_sha256(context)}}
    report = audit_effective_inputs([reasoning([]), event], "B0")
    assert report["recipient_inputs"] == {"manager": 1, "specialist": 0, "verifier": 1}
    assert any("card_or_rules_leakage" in issue for issue in report["problems"])


def test_rule_is_exactly_once_for_E_and_never_visible_for_other_methods() -> None:
    ledger = {"role": "user", "content": LEDGER_MESSAGE_PREFIX + "{}"}
    rule = {"role": "user", "content": RULE_PREFIX + '{"rules":[]}'}
    assert not audit_effective_inputs([reasoning([ledger, rule])], "E")["problems"]
    assert audit_effective_inputs([reasoning([ledger])], "E")["problems"]
    assert audit_effective_inputs([reasoning([ledger, rule, rule])], "E")["problems"]
    assert audit_effective_inputs([reasoning([ledger, rule])], "B")["problems"]
