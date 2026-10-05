"""Offline D adoption audit; no execution changes, payload exports or ranking.

The frozen collector's candidate-count >= 2 metric includes all-rejected sets.
Retain it as submitted-set evidence; independently count actual quoted cards,
feasible alternatives, Manager exposure and selected/authorized/executed choices.
"""

from __future__ import annotations

import json
from typing import Any


def comparison_adoption_audit(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Only exact created cards count; returned typed errors are not cost cards.

    Visibility means exact structured tool-result equality in recorded root SDK
    input, before first choice. It proves exposure, not causal use. No prompts,
    task content, arbitrary arguments/messages or cost body leave this function.
    """
    quotes: dict[str, tuple[int, dict[str, Any]]] = {}
    comparisons: dict[str, tuple[int, dict[str, Any]]] = {}
    selections: dict[str, list[tuple[int, str]]] = {}
    authorized: dict[str, list[int]] = {}
    observed: dict[str, tuple[int, bool]] = {}
    manager_inputs: list[tuple[int, list[Any]]] = []

    for index, event in enumerate(events):
        kind, payload = event["event_type"], event["payload"]
        if kind == "logical.cost_quote.created":
            card = payload["quote"]
            identifier = card["quote_id"]
            if not isinstance(identifier, str) or identifier in quotes:
                raise ValueError("unique created quote identity required")
            quotes[identifier] = (index, card)
        elif kind == "logical.cost_candidates.returned":
            identifier = payload["comparison_id"]
            if not isinstance(identifier, str) or identifier in comparisons:
                raise ValueError("unique comparison identity required")
            candidates = payload["candidates"]
            if not isinstance(candidates, list) or not 1 <= len(candidates) <= 3:
                raise ValueError("one to three returned candidate results required")
            if (payload.get("selected_by_system") is not None
                    or payload.get("quality_estimated") is not False):
                raise ValueError("system selection/quality estimation is outside frozen D")
            comparisons[identifier] = (index, payload)
        elif kind == "logical.cost_candidates.selected":
            identifier, quote_id = payload["comparison_id"], payload["quote_id"]
            if not isinstance(quote_id, str) or identifier not in comparisons:
                raise ValueError("comparison choice lacks prior returned candidates")
            selections.setdefault(identifier, []).append((index, quote_id))
        elif kind == "logical.cost_quote.commit_authorized":
            if payload["quote_id"] not in quotes:
                raise ValueError("quote authorization lacks prior creation")
            authorized.setdefault(payload["quote_id"], []).append(index)
        elif kind == "logical.cost_quote.observed":
            identifier, succeeded = payload["quote_id"], payload["succeeded"]
            if (identifier not in quotes or identifier in observed
                    or not isinstance(succeeded, bool)):
                raise ValueError("one unambiguous execution outcome per quote required")
            observed[identifier] = (index, succeeded)
        elif kind == "logical.reasoning.input" and payload.get("logical_agent_id") == "manager":
            outputs = []
            for item in payload.get("input_items", []):
                if item.get("type") != "function_call_output":
                    continue
                output = item.get("output")
                if not isinstance(output, str):
                    continue
                try:
                    outputs.append(json.loads(output))
                except json.JSONDecodeError:
                    continue  # Unstructured mentions are not comparison exposure.
            manager_inputs.append((index, outputs))

    rows = []
    for identifier, (creation, response) in comparisons.items():
        cards: list[str] = []
        feasible = typed_failures = consequences = 0
        for result in response["candidates"]:
            if not isinstance(result, dict):
                raise ValueError("structured returned candidate result required")
            quote_id = result.get("quote_id")
            if quote_id is None:
                typed_failures += result.get("succeeded") is False
                continue
            if (not isinstance(quote_id, str) or quote_id not in quotes
                    or quotes[quote_id][0] >= creation or quotes[quote_id][1] != result
                    or quote_id in cards):
                raise ValueError("returned cost card differs from unique prior created quote")
            cards.append(quote_id)
            consequence = result.get("consequence")
            consequences += isinstance(consequence, dict)
            feasible += (isinstance(consequence, dict)
                         and consequence.get("physical_selection_succeeded") is True)

        choices = selections.get(identifier, [])
        if len(choices) > 1 or any(quote_id not in cards for _, quote_id in choices):
            raise ValueError("at most one member quote may be selected per comparison")
        first_choice = choices[0][0] if choices else len(events)
        exposures = sum(creation < index < first_choice and response in outputs
                        for index, outputs in manager_inputs)
        choice_authorized = choice_executed = False
        choice_succeeded = None
        if choices:
            selected_at, quote_id = choices[0]
            choice_authorized = any(index > selected_at
                                    for index in authorized.get(quote_id, []))
            outcome = observed.get(quote_id)
            if outcome is not None:
                observed_at, choice_succeeded = outcome
                if (not choice_authorized or observed_at <= selected_at
                        or not any(selected_at < index < observed_at
                                   for index in authorized.get(quote_id, []))):
                    raise ValueError("comparison execution lacks ordered choice/authorization")
                choice_executed = True

        rows.append({
            "comparison_id": identifier,
            "returned_candidate_count": len(response["candidates"]),
            "exact_created_quote_card_count": len(cards),
            "consequence_card_count": consequences,
            "unknown_consequence_card_count": len(cards) - consequences,
            "physically_feasible_card_count": feasible,
            "returned_typed_failure_count": typed_failures,
            "submitted_multi_candidate_set": len(response["candidates"]) >= 2,
            "multi_quote_consequence_comparison": consequences >= 2,
            "multi_feasible_quote_comparison": feasible >= 2,
            "exact_manager_inputs_before_choice": exposures,
            "comparison_visible_before_choice": bool(exposures),
            "selected_member_quote": bool(choices),
            "selected_quote_authorized": choice_authorized,
            "selected_quote_executed": choice_executed,
            "selected_quote_succeeded": choice_succeeded,
            "visibility_or_choice_proves_causal_cost_use": False,
        })

    return {
        "version": "comparison-adoption-receipts-v1",
        "returned_sets": len(rows),
        "submitted_candidate_counts": [row["returned_candidate_count"] for row in rows],
        "submitted_multi_candidate_sets": sum(row["submitted_multi_candidate_set"]
                                              for row in rows),
        "multi_quote_consequence_comparisons": sum(row["multi_quote_consequence_comparison"]
                                                  for row in rows),
        "multi_feasible_quote_comparisons": sum(row["multi_feasible_quote_comparison"]
                                               for row in rows),
        "sets_visible_before_choice": sum(row["comparison_visible_before_choice"]
                                          for row in rows),
        "selected_member_quotes": sum(row["selected_member_quote"] for row in rows),
        "authorized_selected_quotes": sum(row["selected_quote_authorized"] for row in rows),
        "executed_selected_quotes": sum(row["selected_quote_executed"] for row in rows),
        "successful_selected_quotes": sum(row["selected_quote_succeeded"] is True
                                          for row in rows),
        "rows": rows,
        "actual_context_scope": "recorded root SDK function tool results, exact equality",
        "frozen_legacy_metrics_modified": False,
        "execution_or_admission_changed": False,
        "payload_exported": False,
        "causal_benefit_proven": False,
    }
