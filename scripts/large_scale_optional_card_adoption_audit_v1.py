"""Offline B/E card exposure and exact execution linkage, not causal optimization.

Proposal and execution have different SDK action IDs. Join them only through the
explicit matched-card receipt and exact semantic fingerprint. No prompts, artifact
bodies, physical identities, consequence values or arbitrary messages are exported.
Raw HTTP query/interface counts remain the separate root_function_receipts scope.
"""

from __future__ import annotations

import json
from typing import Any

from infra_joint.control.provenance import provenance_sha256


def semantic_payload(action: dict[str, Any]) -> dict[str, Any]:
    """Use the frozen optional-card fingerprint encoding, not a new normalizer."""
    return {key: value for key, value in action.items() if key != "action_id"}


def optional_card_adoption_audit(events: list[dict[str, Any]]) -> dict[str, Any]:
    quotes: dict[str, tuple[int, dict[str, Any]]] = {}
    cards: dict[str, tuple[int, dict[str, Any]]] = {}
    matches: dict[str, tuple[int, dict[str, Any]]] = {}
    observed: dict[str, tuple[int, dict[str, Any]]] = {}
    prepared: dict[str, tuple[int, dict[str, Any]]] = {}
    physical: dict[str, tuple[int, dict[str, Any]]] = {}
    logical: dict[str, tuple[int, dict[str, Any]]] = {}
    inputs: list[tuple[int, list[Any]]] = []

    def insert(target: dict[str, tuple[int, dict[str, Any]]], key: Any,
               index: int, payload: dict[str, Any]) -> None:
        if not isinstance(key, str) or not key or key in target:
            raise ValueError("unique structured receipt identity required")
        target[key] = (index, payload)

    for index, event in enumerate(events):
        kind, payload = event["event_type"], event["payload"]
        if kind == "logical.cost_quote.created":
            insert(quotes, payload["quote"]["quote_id"], index, payload)
        elif kind == "logical.cost_card.returned":
            insert(cards, payload["card_id"], index, payload)
        elif kind == "logical.cost_card.matched":
            insert(matches, payload["card_id"], index, payload)
        elif kind == "logical.cost_quote.observed":
            insert(observed, payload["quote_id"], index, payload)
        elif kind == "logical.action.prepared":
            insert(prepared, payload["action"]["action_id"], index, payload["action"])
        elif kind == "physical.execution":
            insert(physical, payload["action_id"], index, payload)
        elif kind == "logical.observation":
            insert(logical, payload["action_id"], index, payload)
        elif kind == "logical.reasoning.input" and payload.get("logical_agent_id") == "manager":
            inputs.append((index, payload.get("input_items", [])))

    if set(matches) - cards.keys():
        raise ValueError("optional match lacks prior returned card")
    rows: list[dict[str, Any]] = []
    matched_actions: set[str] = set()
    for identifier, (returned_at, card) in cards.items():
        if identifier not in quotes:
            raise ValueError("returned card lacks exact created quote")
        created_at, proposal = quotes[identifier]
        action, quote = proposal["action"], proposal["quote"]
        proposal_id = action.get("action_id")
        if (created_at >= returned_at or action.get("owner_agent_id") != "manager"
                or not isinstance(proposal_id, str) or not proposal_id.startswith("manager:")
                or card.get("advisory_only") is not True
                or card.get("consequence") != quote.get("consequence")):
            raise ValueError("returned optional card differs from exact root proposal")

        matched = matches.get(identifier)
        prepared_at = len(events)
        execution_id: str | None = None
        succeeded: bool | None = None
        if matched is not None:
            matched_at, match = matched
            execution_id = match.get("action_id")
            if (not isinstance(execution_id, str) or execution_id not in prepared
                    or execution_id in matched_actions or execution_id not in physical
                    or execution_id not in logical or identifier not in observed):
                raise ValueError("optional match requires unique actual action/outcome receipts")
            prepared_at, executed = prepared[execution_id]
            fingerprint = provenance_sha256(semantic_payload(executed))
            observed_at, outcome = observed[identifier]
            observation_at, observation = logical[execution_id]
            physical_at, receipt = physical[execution_id]
            succeeded = observation.get("succeeded")
            if (not returned_at < prepared_at < matched_at < observed_at
                    or observation_at <= prepared_at or physical_at <= prepared_at
                    or semantic_payload(executed) != semantic_payload(action)
                    or match.get("exact_semantic_fingerprint") != fingerprint
                    or outcome.get("action_id") != proposal_id
                    or outcome.get("succeeded") != succeeded
                    or not isinstance(succeeded, bool)
                    or (succeeded and not isinstance(receipt.get("execution"), dict))
                    or (not succeeded and not isinstance(receipt.get("failure"), dict))):
                raise ValueError("optional proposal/match/actual execution proof is inconsistent")
            matched_actions.add(execution_id)
        elif identifier in observed:
            raise ValueError("optional quote outcome lacks explicit execution match")

        exposures = 0
        call_id = proposal_id.removeprefix("manager:")
        for index, items in inputs:
            if not returned_at < index < prepared_at:
                continue
            exact = False
            for item in items:
                if (item.get("type") != "function_call_output"
                        or item.get("call_id") != call_id):
                    continue
                try:
                    value = json.loads(item.get("output", ""))
                except (TypeError, ValueError):
                    continue
                exact = exact or value == card
            exposures += exact
        rows.append({
            "card_id": identifier,
            "proposal_action_id": proposal_id,
            "execution_action_id": execution_id,
            "exact_manager_inputs_before_execution": exposures,
            "card_visible_before_execution": bool(exposures),
            "exact_semantic_execution_match": matched is not None,
            "matched_execution_succeeded": succeeded,
            "exposure_and_match_prove_causal_cost_use": False,
        })
    return {
        "version": "optional-card-adoption-receipts-v1",
        "valid_returned_cards": len(rows),
        "cards_visible_before_execution": sum(row["card_visible_before_execution"]
                                               for row in rows),
        "exact_execution_matches": len(matched_actions),
        "successful_matched_executions": sum(row["matched_execution_succeeded"] is True
                                             for row in rows),
        "rows": rows,
        "unknown_profiles_imputed": False,
        "raw_query_attempts_counted_here": False,
        "causal_benefit_proven": False,
        "execution_or_admission_changed": False,
        "payload_exported": False,
        "visibility_window_note": "matched cards use the interval before actual action "
        "preparation; unexecuted cards use later inputs through trace end. Exposure "
        "alone does not imply execution",
        "physical_receipt_order_note": "completion metadata may be emitted after match; "
        "ordered receipt emission is not physical execution timing",
    }
