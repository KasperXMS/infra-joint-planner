"""Offline verifier-state fingerprints. This module never changes live scheduling."""

from __future__ import annotations

from typing import Any, cast

from pydantic import Field

from infra_joint.control.workflow import canonical_sha256
from infra_joint.core.base import ContractModel


class OfflineVerifierSummary(ContractModel):
    schema_version: str = "offline-verifier-fingerprint-v1"
    verifier_calls: int = Field(ge=0)
    calls_with_input_context: int = Field(ge=0)
    repeated_schema_failure: int = Field(ge=0)
    no_new_semantic_evidence: int = Field(ge=0)
    same_candidate: int = Field(ge=0)
    same_preconditions: int = Field(ge=0)
    strict_duplicate_nonfinal_calls: int = Field(ge=0)
    hypothetical_input_tokens: int = Field(ge=0)
    hypothetical_output_tokens: int = Field(ge=0)
    actual_calls_skipped: int = 0


def analyze_verifier_trace(events: list[dict[str, Any]]) -> OfflineVerifierSummary:
    """Count fingerprints from recorded contexts; retain each run's last judgment."""
    contexts: dict[int, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    for event in events:
        raw_payload = event.get("payload", {})
        if not isinstance(raw_payload, dict):
            continue
        payload = cast(dict[str, Any], raw_payload)
        index = payload.get("verification_index")
        if not isinstance(index, int):
            continue
        if event.get("event_type") == "logical.verification.input":
            raw_context = payload.get("context")
            if isinstance(raw_context, dict):
                contexts[index] = cast(dict[str, Any], raw_context)
        elif event.get("event_type") == "logical.verification":
            results.append(payload)
    results.sort(key=lambda item: item["verification_index"])
    repeated_schema = no_new = same_candidate = same_pre = duplicate = 0
    hypothetical_input = hypothetical_output = 0
    previous: tuple[str, str, str, str | None] | None = None
    for position, result in enumerate(results):
        context = contexts.get(result["verification_index"])
        if context is None:
            previous = None
            continue
        raw_observations = context.get("observations", [])
        if not isinstance(raw_observations, list):
            previous = None
            continue
        observations = cast(list[Any], raw_observations)
        usable = [
            cast(dict[str, Any], item)
            for item in observations
            if isinstance(item, dict)
            and cast(dict[str, Any], item).get("failure_code") != "schema_validation_failed"
        ]
        model_action_ids = {
            cast(dict[str, Any], item).get("action_id")
            for item in cast(list[Any], context.get("actions", []))
            if isinstance(item, dict) and cast(dict[str, Any], item).get("action_type") == "model"
        }
        candidates = [
            {
                "action_id": item.get("action_id"),
                "text": cast(dict[str, Any], item.get("output", {})).get("text"),
            }
            for item in usable
            if item.get("succeeded")
            and item.get("owner_agent_id") == "manager"
            and item.get("action_id") in model_action_ids
            and isinstance(item.get("output"), dict)
            and isinstance(item["output"].get("text"), str)
        ]
        evidence = canonical_sha256(
            {
                "task": context.get("task"),
                "observations": usable,
                "produced_artifacts": context.get("produced_artifacts"),
            }
        )
        candidate = canonical_sha256(candidates)
        preconditions = canonical_sha256(
            {
                "phase": context.get("phase"),
                "remaining_budget": context.get("remaining_budget"),
                "output_contract": context.get("task", {}).get("output_contract"),
            }
        )
        last_failure: str | None = next(
            (
                cast(str | None, cast(dict[str, Any], item).get("failure_code"))
                for item in reversed(observations)
                if isinstance(item, dict)
            ),
            None,
        )
        if previous is not None:
            same_evidence = evidence == previous[0]
            same_answer = candidate == previous[1]
            same_conditions = preconditions == previous[2]
            if same_evidence:
                no_new += 1
            if same_answer:
                same_candidate += 1
            if same_conditions:
                same_pre += 1
            if last_failure == previous[3] == "schema_validation_failed":
                repeated_schema += 1
            if (
                same_evidence
                and same_answer
                and same_conditions
                and position < len(results) - 1
                and result.get("status") != "complete"
            ):
                duplicate += 1
                hypothetical_input += int(result.get("input_tokens") or 0)
                hypothetical_output += int(result.get("output_tokens") or 0)
        previous = (evidence, candidate, preconditions, last_failure)
    return OfflineVerifierSummary(
        verifier_calls=len(results),
        calls_with_input_context=sum(item["verification_index"] in contexts for item in results),
        repeated_schema_failure=repeated_schema,
        no_new_semantic_evidence=no_new,
        same_candidate=same_candidate,
        same_preconditions=same_pre,
        strict_duplicate_nonfinal_calls=duplicate,
        hypothetical_input_tokens=hypothetical_input,
        hypothetical_output_tokens=hypothetical_output,
    )
