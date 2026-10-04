"""Trace-only distillation contract; examples and rules contain no task answers/identities."""

import json
import re
from typing import Any

from pydantic import Field

from infra_joint.control.provenance import provenance_sha256
from infra_joint.core.base import ContractModel

DISTILLATION_INSTRUCTIONS = (
    "Distill at most six generic advisory COST heuristics from the supplied anonymized "
    "execution traces. Return JSON {rules:[{rule_id,principle,scope,support_examples,"
    "counterexamples,overfit_risk}]}. Each rule needs at least one supporting example and "
    "one counterexample or boundary example, identified ONLY by supplied example_id. "
    "Cost receipts do not establish semantic accuracy. Do not invent evidence or infer "
    "answer quality. Preserve unknowns. Do not name datasets/tasks/devices/deployments, "
    "give retrieval queries, or prescribe a task topology, fixed parameter, sampling "
    "schedule or answer. Describe generic limits and cases where the rule should NOT apply. "
    "These are advisory in-context heuristics, not trained weights or an optimal policy."
)


class CostRule(ContractModel):
    rule_id: str = Field(min_length=1, max_length=80)
    principle: str = Field(min_length=1, max_length=1200)
    scope: str = Field(min_length=1, max_length=800)
    support_examples: tuple[str, ...] = Field(min_length=1, max_length=12)
    counterexamples: tuple[str, ...] = Field(min_length=1, max_length=12)
    overfit_risk: str = Field(min_length=1, max_length=800)


class CostRuleSet(ContractModel):
    rules: tuple[CostRule, ...] = Field(min_length=1, max_length=6)


def validate_rule_set(value: CostRuleSet, examples: list[dict[str, Any]]) -> None:
    ids = {e["example_id"] for e in examples}
    if len({r.rule_id for r in value.rules}) != len(value.rules):
        raise ValueError("duplicate rule IDs")
    for rule in value.rules:
        if not set((*rule.support_examples, *rule.counterexamples)) <= ids:
            raise ValueError("rule refers to an unavailable trace")
        if set(rule.support_examples) & set(rule.counterexamples):
            raise ValueError("support and counterexample must be distinct")
    encoded = value.model_dump_json().lower()
    forbidden = ("multihop", "longbench", "video-mme", "848-1", "795-3", "barbara",
                 "barb-poly", "a28", "4090", "jetson", "deployment", "worker_id",
                 "source_ref", "gold", "evaluator", "supporting_evidence")
    if any(s in encoded for s in forbidden) or re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", encoded):
        raise ValueError("rule contains private, physical, or task-specific identifiers")


def anonymized_cost_trace(events: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    """Allowlist numeric/structural receipts only, never prompts, queries, answers or gold."""
    actions: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for event in events:
        payload = event["payload"]
        if event["event_type"] == "logical.action.prepared":
            action = payload["action"]
            actions[action["action_id"]] = action
        elif event["event_type"] == "physical.execution":
            action = actions[payload["action_id"]]
            execution = payload.get("execution")
            transfers: list[dict[str, Any]] = execution.get("transfers", []) if execution else []
            telemetry = execution.get("model_telemetry") if execution else None
            rows.append({
                "operator": action.get("operator", "invoke_model"),
                "input_count": len(action["inputs"]), "output_count": len(action["outputs"]),
                "transfer_bytes": sum(t["bytes_transferred"] for t in transfers)
                if execution else None,
                "transfer_work_ms": sum(t["duration_ms"] for t in transfers)
                if execution else None,
                "operator_wrapper_ms": execution.get("operator_latency_ms") if execution else None,
                "model_service_ms": telemetry.get("service_latency_ms") if telemetry else None,
                "model_input_tokens": telemetry.get("input_tokens") if telemetry else None,
                "model_output_tokens": telemetry.get("output_tokens") if telemetry else None,
            })
        elif event["event_type"] == "logical.observation" and not payload.get("succeeded", True):
            code = payload.get("failure_code")
            rows.append({"typed_failure": code if isinstance(code, str) else "unknown"})
    if not rows:
        raise ValueError("distillation trace has no real execution receipts")
    # No source task, run or artifact IDs reach the meta-agent; hashes are linkage only.
    return {"example_id": provenance_sha256(run_id), "events": rows,
            "quality_is_unknown": True, "source_trace_sha256": provenance_sha256(events)}


def parse_rules(text: str) -> CostRuleSet:
    raw = text.strip()
    if raw.startswith("```json") and raw.endswith("```"):
        raw = raw[7:-3].strip()
    return CostRuleSet.model_validate(json.loads(raw))
