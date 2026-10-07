"""Persisted actual recipient wire audit; never an Agent input or online policy."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import large_scale_resident_phase2_field_queue_v1 as field
import yaml

from infra_joint.control.bde_native import RULE_PREFIX
from infra_joint.control.ledger import LEDGER_MESSAGE_PREFIX
from infra_joint.control.provenance import PROFILE_MESSAGE_PREFIX, provenance_sha256


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise RuntimeError(reason)


def texts(request: dict[str, Any]) -> list[str]:
    result = []
    for message in request["messages"]:
        content = message.get("content")
        if isinstance(content, str):
            result.append(content)
        elif isinstance(content, list):
            result.extend(b["text"] for b in content
                          if isinstance(b, dict) and isinstance(b.get("text"), str))
    return result


def audit_feedback(projection: dict[str, Any]) -> dict[str, Any]:
    root = field.frozen.ROOT
    rules = json.loads(field.frozen.RULES.read_text(encoding="utf-8"))["rules"]
    parent = json.loads((root / "phase2-control-freeze-001.json").read_text(encoding="utf-8"))
    records = []
    for row in projection["rows"]:
        for attempt in row["attempts"]:  # Never silently drop failed/additional attempts.
            cell, method = row["condition"]["cell_id"], row["condition"]["method"]
            directory = root / "evidence" / cell / ("attempt" + str(attempt["attempt_index"]))
            trace = directory / "runs" / attempt["run_id"] / "trace.jsonl"
            _require(field.core.legacy.sha256(trace) == attempt["trace_file_sha256"],
                     "trace/source snapshot drift")
            config = yaml.safe_load((root / "cell-configs" / (attempt["run_id"] + ".yaml"))
                                    .read_text(encoding="utf-8"))
            admission = json.loads((directory / "admission.json").read_text(encoding="utf-8"))
            reproduced = field.core.previous.previous.admission(
                directory, config, Path(parent["pricing_path"]))
            _require(admission == reproduced, "actual original recipient/admission drift")
            _require(admission["api_audit"]["problems"] == []
                     and admission["method_audit"]["problems"] == [], "recipient scan failed")
            with trace.open(encoding="utf-8") as stream:
                events = [json.loads(line) for line in stream]
            starts = sorted((datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")),
                             e["payload"]["decision_id"]) for e in events
                            if e["event_type"] == "logical.reasoning.started"
                            and e["payload"]["logical_agent_id"] == "manager")
            profiles = {e["payload"]["decision_id"]: e["payload"]["profile"] for e in events
                        if e["event_type"] == "logical.profile.predecision"}
            ledgers = {e["payload"]["decision_id"]: e["payload"]["ledger"] for e in events
                       if e["event_type"] == "logical.cost_ledger.predecision"}
            rule_events = [e["payload"]["rules"] for e in events
                           if e["event_type"] == "logical.cost_rules.predecision"]
            _require(len(profiles) == (len(starts) if method == "B1" else 0)
                     and len(ledgers) == (len(starts) if method in {"A", "E"} else 0)
                     and len(rule_events) == (len(starts) if method == "E" else 0)
                     and all(x == rules for x in rule_events), "feedback event contract mismatch")
            freeze = json.loads((directory / "attempt-freeze.json").read_text(encoding="utf-8"))
            _require(freeze["rules_sha256"] == provenance_sha256(rules), "rules freeze drift")
            counts = {"manager": 0, "verifier": 0, "specialist": 0}
            hashes, roots = {}, []
            for usage_path in (directory / "private/api").glob("*-usage.json"):
                usage = json.loads(usage_path.read_text(encoding="utf-8"))
                role, call = usage["recipient"], usage["call_id"]
                _require(role in counts and Path(call).name == call
                         and usage_path.name == call + "-usage.json", "invalid recipient identity")
                counts[role] += 1
                request_path = usage_path.parent / (call + "-request.json")
                _require(not request_path.is_symlink() and not usage_path.is_symlink(),
                         "API files must be owned regular files")
                request = json.loads(request_path.read_text(encoding="utf-8"))
                hashes[request_path.name] = field.core.legacy.sha256(request_path)
                model = freeze["verifier_model"] if role == "verifier" else freeze["manager_model"]
                _require(request["model"] == model, "fixed model recipient binding drift")
                if role != "manager":
                    _require(all(prefix not in json.dumps(request, ensure_ascii=False)
                                 for prefix in (PROFILE_MESSAGE_PREFIX, LEDGER_MESSAGE_PREFIX,
                                                RULE_PREFIX)), "non-Manager feedback leakage")
                    continue
                stamp = datetime.fromisoformat(usage["started_utc"].replace("Z", "+00:00"))
                candidates = [identifier for t, identifier in starts if t <= stamp]
                _require(bool(candidates), "actual request lacks root decision")
                identifier, matched = candidates[-1], {}
                messages = texts(request)
                for name, prefix, expected in (
                    ("profile", PROFILE_MESSAGE_PREFIX, profiles.get(identifier)),
                    ("ledger", LEDGER_MESSAGE_PREFIX, ledgers.get(identifier)),
                    ("rules", RULE_PREFIX, rules if method == "E" else None),
                ):
                    actual = [t for t in messages if t.startswith(prefix)]
                    if expected is None:
                        _require(not actual, "unexpected root feedback")
                    else:
                        _require(len(actual) == 1
                                 and json.loads(actual[0][len(prefix):]) == expected,
                                 "actual feedback differs from decision receipt")
                        matched[name] = provenance_sha256(expected)
                roots.append({"call_id": call, "decision_id": identifier,
                              "provider_status": usage["status"], "exact_feedback_hashes": matched})
            _require(len(roots) == len(starts)
                     and len({r["decision_id"] for r in roots}) == len(starts)
                     and counts == admission["method_audit"]["recipient_inputs"],
                     "actual recipient population mismatch")
            records.append({"cell_id": cell, "run_id": attempt["run_id"],
                            "attempt_index": attempt["attempt_index"], "method": method,
                            "planner": row["condition"]["planner"],
                            "trace_sha256": attempt["trace_file_sha256"],
                            "actual_recipient_counts": counts, "request_file_sha256": hashes,
                            "root_decisions": roots, "original_recipient_scan_findings": [],
                            "all_Verifier_requests_match_fixed_frozen_model": True,
                            "non_manager_requests_without_profile_ledger_or_rules_prefix": True})
    return {"records": records, "review_scope": "persisted SDK requests and original admissions",
            "new_model_calls": 0, "private_semantic_audit_complete": False,
            "raw_payload_exported": False, "visibility_proves_adoption_or_cost_effect": False}
