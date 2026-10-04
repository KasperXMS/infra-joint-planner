"""Offline audit of actual recipient contexts, including accumulated tool results.

No audit result or private evaluation information is fed back into an Agent.
Request payloads stay in the remote private namespace. Receipts contain paths and
counts, not messages, artifact bodies, gold answers or physical identities.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from infra_joint.control.bde_native import RULE_PREFIX, contains_bde_feedback
from infra_joint.control.ledger import LEDGER_MESSAGE_PREFIX, is_ledger_message
from infra_joint.control.provenance import PROFILE_MESSAGE_PREFIX, provenance_sha256
from infra_joint.experiments.large_scale_protocol import METHODS

PRIVATE_IDENTITY_KEYS = frozenset({
    "worker_id", "deployment_id", "selected_agent_id", "selected_deployment_id",
    "source_ref", "evaluator_id", "gold", "gold_answer", "supporting_evidence",
    "supporting_context", "initial_placement", "physical_location", "physical_route",
})
DYNAMIC_KEYS = frozenset({
    "physical_profile", "current_anonymous_profile", "network_class", "bandwidth_mbps",
    "rtt_ms", "queue_pressure_range", "worker_load", "deployment_availability",
})


@dataclass(frozen=True)
class ContextFinding:
    category: str
    path: str


def _quote(value: object) -> bool:
    if isinstance(value, Mapping):
        mapping = cast(Mapping[str, object], value)
        return ({"quote_id", "action_sha256", "consequence"} <= mapping.keys()
                or any(_quote(item) for item in mapping.values()))
    if isinstance(value, list):
        return any(_quote(item) for item in cast(list[object], value))
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (ValueError, RecursionError):
            return False
        return _quote(parsed) if not isinstance(parsed, str) else False
    return False


def scan_recipient_context(
    value: object, *, recipient: str, method: str,
    physical_identifiers: tuple[str, ...] = (),
) -> tuple[ContextFinding, ...]:
    """Scan messages, instructions and nested JSON-string tool outputs, not just H0.

    Root B1 may receive an anonymous profile; cost methods may receive their
    prescribed root-only feedback. Specialists/Verifier never receive either.
    Concrete identities/private fields are forbidden for every recipient. Known
    endpoint/deployment strings are supplied from private Worker state, rather
    than mistaking ordinary corpus numbers or arbitrary IPv4 prose for leakage.
    """
    if method not in METHODS or recipient not in {"manager", "specialist", "verifier"}:
        raise ValueError("unknown frozen method or recipient")
    findings: list[ContextFinding] = []
    root = recipient == "manager"
    dynamic_allowed = root and method == "B1"
    ledger_allowed = root and method in {"A", "B", "C", "D", "E"}
    quote_allowed = root and method in {"C", "D"}
    bde_allowed = root and method in {"B", "D", "E"}

    def walk(item: object, path: str, depth: int) -> None:
        if depth > 96:
            findings.append(ContextFinding("context_nesting_unverifiable", path))
            return
        if isinstance(item, Mapping):
            mapping = cast(Mapping[str, object], item)
            for key, nested in mapping.items():
                lowered = key.lower()
                child = f"{path}.{key}"
                if lowered in PRIVATE_IDENTITY_KEYS:
                    findings.append(ContextFinding("private_or_physical_field", child))
                if lowered in DYNAMIC_KEYS and nested is not None and not dynamic_allowed:
                    findings.append(ContextFinding("dynamic_profile_leakage", child))
                walk(nested, child, depth + 1)
        elif isinstance(item, Sequence) and not isinstance(item, str | bytes | bytearray):
            for index, nested in enumerate(cast(Sequence[object], item)):
                walk(nested, f"{path}[{index}]", depth + 1)
        elif isinstance(item, str):
            if "private://" in item or any(identity and identity in item
                                            for identity in physical_identifiers):
                findings.append(ContextFinding("private_or_physical_identity", path))
            for prefix, allowed, category in (
                (PROFILE_MESSAGE_PREFIX, dynamic_allowed, "dynamic_profile_leakage"),
                (LEDGER_MESSAGE_PREFIX, ledger_allowed, "ledger_leakage"),
                (RULE_PREFIX, root and method == "E", "rule_leakage"),
            ):
                if prefix in item and not allowed:
                    findings.append(ContextFinding(category, path))
                # Allowing a feedback category never permits a hidden identity.
                if item.startswith(prefix):
                    walk(item[len(prefix):], path + ".feedback", depth + 1)
                    return
            try:
                decoded = json.loads(item)
            except (ValueError, RecursionError):
                return
            if not isinstance(decoded, str):
                walk(decoded, path + ".json", depth + 1)

    walk(value, "$", 0)
    if not quote_allowed and _quote(value):
        findings.append(ContextFinding("quote_leakage", "$"))
    if not bde_allowed and contains_bde_feedback(value):
        findings.append(ContextFinding("card_or_rules_leakage", "$"))
    return tuple(sorted(set(findings), key=lambda item: (item.category, item.path)))


def audit_effective_inputs(events: list[dict[str, Any]], method: str) -> dict[str, object]:
    """Validate method-specific input provenance and pre-decision ordering."""
    issues: list[str] = []
    counts = {"manager": 0, "specialist": 0, "verifier": 0}
    profiles: dict[str, tuple[int, object]] = {}
    for index, event in enumerate(events):
        payload = event["payload"]
        kind = event["event_type"]
        if kind == "logical.profile.predecision":
            decision = payload["decision_id"]
            if decision in profiles:
                issues.append("duplicate_predecision_profile")
            profiles[decision] = (index, payload["profile"])
        elif kind == "logical.reasoning.input":
            owner = "manager" if payload["logical_agent_id"] == "manager" else "specialist"
            counts[owner] += 1
            items = payload.get("input_items", [])
            if provenance_sha256(items) != payload.get("input_sha256"):
                issues.append("effective_input_hash_mismatch")
            issues.extend(f"{owner}:{item.category}:{item.path}" for item in
                          scan_recipient_context(items, recipient=owner, method=method))
            ledgers = sum(is_ledger_message(item) for item in items)
            if owner == "manager":
                expected = int(method in {"A", "B", "C", "D", "E"})
                if ledgers != expected:
                    issues.append("incorrect_fresh_ledger_count")
                profile = profiles.get(payload["decision_id"])
                actual = payload.get("current_anonymous_profile")
                if method == "B1":
                    if profile is None or profile[0] >= index or profile[1] != actual:
                        issues.append("missing_late_or_mismatched_B1_profile")
                elif actual is not None or profile is not None:
                    issues.append("unexpected_predecision_profile")
                rules = sum(isinstance(item.get("content"), str)
                            and item["content"].startswith(RULE_PREFIX) for item in items)
                if rules != int(method == "E"):
                    issues.append("incorrect_frozen_rule_count")
        elif kind == "logical.verification.input":
            counts["verifier"] += 1
            context = payload["context"]
            if provenance_sha256(context) != payload.get("context_sha256"):
                issues.append("verifier_context_hash_mismatch")
            issues.extend(f"verifier:{item.category}:{item.path}" for item in
                          scan_recipient_context(context, recipient="verifier", method=method))
    if method != "B1" and profiles:
        issues.append("unexpected_profile_events")
    return {"problems": sorted(set(issues)), "recipient_inputs": counts}
