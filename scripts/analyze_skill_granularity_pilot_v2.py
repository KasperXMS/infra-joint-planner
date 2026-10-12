"""Final offline, content-free analysis of the frozen 30-cell Skill granularity pilot.

Run on the experiment machine after final inspection. Raw task text, responses,
artifact identities and private paths never enter the export. This script does
not perform inference, inspect source/history again, or change an experiment.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import analyze_lightweight_planner_pilot_v1 as legacy_analysis
from analyze_lightweight_planner_pilot_v1 import aggregate, read, total, write
from analyze_multiscale_planner_v1 import (
    SHA256,
    evidence_manifest,
    independent_planner_work,
    label,
    numeric_tree,
    safe_metadata,
    safe_row,
)

VERSION = "skill-granularity-pilot-results-v2"
CANDIDATES = ("qwen35-4b", "qwen35-9b", "qwen35-27b")
SKILLS = ("S0", "S1", "S2", "S3")
ROLES = ("manager", "specialist", "verifier")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ratio(numerator, denominator):
    return numerator / denominator if numerator is not None and denominator else None


def difference(before, after):
    if before is None or after is None:
        return None
    if isinstance(before, dict) and isinstance(after, dict):
        return {
            key: difference(before[key], after[key])
            for key in sorted(before.keys() & after.keys())
            if isinstance(before[key], dict) or type(before[key]) in (int, float)
        }
    if type(before) in (int, float) and type(after) in (int, float):
        return after - before
    return None


def key(cell):
    return cell["candidate"] + "__" + cell["skill_condition"]


def validate_plan(freeze):
    cells = freeze.get("ordered_cells", [])
    if len(cells) != 30:
        raise RuntimeError("Final analysis requires the frozen 30-cell plan")
    seen = set()
    conditions = defaultdict(set)
    for cell in cells:
        identity = (cell.get("candidate"), cell.get("skill_condition"), cell.get("task_index"))
        if (
            identity[0] not in CANDIDATES
            or identity[1] not in SKILLS
            or identity[2] not in (1, 2, 3)
            or identity in seen
            or label(cell.get("cell_id")) == "unknown"
        ):
            raise RuntimeError("Invalid or duplicate frozen cell identity")
        seen.add(identity)
        conditions[identity[:2]].add(identity[2])
    if len({cell["cell_id"] for cell in cells}) != 30 or len(conditions) != 10:
        raise RuntimeError("Expected 30 unique IDs and 10 conditions")
    if any(tasks != {1, 2, 3} for tasks in conditions.values()):
        raise RuntimeError("Every frozen condition must contain exactly the same three tasks")
    for candidate in CANDIDATES[:2]:
        if {condition for model, condition in conditions if model == candidate} != set(SKILLS):
            raise RuntimeError("4B and 9B each require S0/S1/S2/S3")
    if sum(model == CANDIDATES[2] for model, _ in conditions) != 2:
        raise RuntimeError("27B requires exactly its two frozen conditions")
    # The selected pair for 27B is read from the freeze, never inferred from scores.
    return cells


def events_for(cell):
    return [
        json.loads(line)
        for path in sorted((cell / "runs").glob("*/trace.jsonl"))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def service_text(cell):
    paths = list((cell / "private/residency-log-intervals").glob("*.json"))
    paths += list((cell / "private").glob("*planner*log*interval*.json"))
    texts = []
    for path in paths:
        value = read(path)
        if isinstance(value.get("text"), str):
            texts.append(value["text"])
        texts.extend(
            interval["text"]
            for interval in value.get("intervals", {}).values()
            if isinstance(interval, dict) and isinstance(interval.get("text"), str)
        )
    return "\n".join(texts)


def provider_category(message, exception_type=""):
    """Classify fixed diagnostic patterns without exporting a provider message."""
    text = str(message).lower()
    exception_type = str(exception_type).lower()
    if "xml syntax error" in text and ("element" in text or "unexpected" in text):
        return "provider_xml_tool_call_parse_error"
    if (
        "invalid character" in text
        or "unexpected end of json" in text
        or "invalid json" in text
        or "json" in text
        and any(s in text for s in ("parse", "unmarshal", "decode"))
    ):
        return "provider_json_syntax_error"
    if re.search(r"out of memory|oom.kill|cuda.*memory allocation", text):
        return "provider_oom_error"
    if any(s in text + " " + exception_type for s in ("timeout", "timed out", "deadline")):
        return "provider_timeout_error"
    if "connection" in exception_type or "connection attempts failed" in text:
        return "provider_connection_error"
    if "tool" in text and any(s in text for s in ("parse", "parsing", "renderer", "render")):
        return "provider_tool_protocol_error_other"
    return "provider_error_other"


def provider_findings(root, cell):
    text = service_text(cell)
    findings = []
    response_shapes = Counter()
    for path in sorted((cell / "private/api").rglob("*-usage.json")):
        usage = read(path)
        response = path.with_name(path.name.replace("-usage.json", "-response.json"))
        body = read(response) if response.exists() else {}
        body_shape = (
            "missing"
            if not response.is_file()
            else "null"
            if body is None
            else "object"
            if isinstance(body, dict)
            else "array"
            if isinstance(body, list)
            else "boolean"
            if type(body) is bool
            else "number"
            if type(body) in (int, float)
            else "string"
            if isinstance(body, str)
            else "unknown"
        )
        response_shapes[body_shape] += 1
        error = body.get("error") if isinstance(body, dict) else None
        status = usage.get("status")
        if (
            not error
            and not usage.get("error_type")
            and not (type(status) is int and status >= 400)
        ):
            continue
        message = str(error.get("message") or "") if isinstance(error, dict) else str(error or "")
        category = provider_category(message, usage.get("error_type", ""))
        source_locations = []
        if category == "provider_xml_tool_call_parse_error":
            source_locations = [
                source for source in ("qwen3coder.go:71", "qwen35.go:108") if source in text
            ]
        xml = re.search(
            r"XML syntax error on line (\d+): element <([^>]+)> closed by <([^>]+)>", message
        )
        allowed_tags = {
            "function",
            "parameter",
            "tool_call",
            "/function",
            "/parameter",
            "/tool_call",
        }
        finding = {
            "category": category,
            "response_body_shape": body_shape,
            "persisted_null_response": body_shape == "null",
            "role": label(usage.get("recipient")),
            "http_status": status if type(status) is int else None,
            "exception_type": label(usage.get("error_type")) if usage.get("error_type") else None,
            "provider_latency_ms": usage.get("latency_ms"),
            "component_confirmed": bool(source_locations),
            "source_locations": source_locations,
            "specific_parser_or_renderer_unknown": not bool(source_locations),
            "xml_line": int(xml.group(1)) if xml else None,
            "xml_open_tag": xml.group(2) if xml and xml.group(2) in allowed_tags else None,
            "xml_close_tag": xml.group(3) if xml and xml.group(3) in allowed_tags else None,
            "json_error_after_object_key": "after object key" in message,
            "json_error_in_string_literal": "in string literal" in message,
            "usage_missing": any(
                type((usage.get("usage") or {}).get(field)) is not int
                for field in ("prompt_tokens", "completion_tokens")
            ),
            "private_usage_sha256": sha(path),
            "private_response_sha256": sha(response) if response.exists() else None,
            "message_sha256": hashlib.sha256(message.encode()).hexdigest(),
        }
        findings.append(finding)
    log_paths = list((cell / "private/residency-log-intervals").glob("*.json"))
    log_paths += list((cell / "private").glob("*planner*log*interval*.json"))
    return {
        "errors": findings,
        "categories": dict(Counter(finding["category"] for finding in findings)),
        "response_body_shapes": dict(response_shapes),
        "service_log_evidence": evidence_manifest(root, log_paths),
        "observed_log_signals": {
            "logs_available": bool(log_paths),
            "oom": bool(re.search(r"out of memory|oom.kill|cuda.*memory allocation", text, re.I)),
            "timeout": bool(re.search(r"timed out|timeout|deadline exceeded", text, re.I)),
            "nonzero_truncation": bool(re.search(r"truncated\s*=\s*[1-9]\d*", text)),
        },
    }


def schema_details(events):
    calls = [
        event["payload"]
        for event in events
        if event["event_type"] == "logical.tool.schema_validation"
    ]
    by_role = {}
    for role in ("manager", "specialist"):
        selected = [
            call for call in calls if (call["owner_agent_id"] == "manager") == (role == "manager")
        ]
        valid = sum(bool(call["valid"]) for call in selected)
        by_role[role] = {
            "attempts": len(selected),
            "valid": valid,
            "invalid": len(selected) - valid,
            "validity": ratio(valid, len(selected)),
        }
    invalid = [call for call in calls if not call["valid"]]
    categories = Counter()
    for call in invalid:
        error_text = "\n".join(str(error) for error in call.get("errors", []))
        for category, pattern in {
            "missing_arguments": r"'arguments' is a required property",
            "missing_inputs": r"'inputs' is a required property",
            "missing_required_property": r"is a required property",
            "undeclared_property": r"Additional properties are not allowed",
            "wrong_json_type": r"is not of type",
            "invalid_enum": r"is not one of",
            "size_or_numeric_bound": r"too short|too long|less than|greater than",
            "invalid_json": r"invalid JSON",
        }.items():
            categories[category] += bool(re.search(pattern, error_text))
    recovered = 0
    for index, call in enumerate(calls):
        if call["valid"]:
            continue
        recovered += any(
            later["valid"]
            and later["owner_agent_id"] == call["owner_agent_id"]
            and later.get("tool") == call.get("tool")
            for later in calls[index + 1 :]
        )
    return {
        "by_role": by_role,
        "invalid_by_tool": dict(Counter(label(call.get("tool")) for call in invalid)),
        "invalid_call_categories_nonexclusive": dict(categories),
        "invalid_calls_with_later_valid_same_owner_and_tool": recovered,
        "invalid_calls_without_later_valid_same_owner_and_tool": len(invalid) - recovered,
        "later_valid_call_rate": ratio(recovered, len(invalid)),
    }


def workflow_shape(row, events):
    nodes, edges = row["workflow"]["nodes"], row["workflow"]["edges"]
    owners = {node["index"]: node["owner"] for node in nodes}
    children = defaultdict(list)
    indegree = Counter()
    for edge in edges:
        children[edge["producer"]].append(edge["consumer"])
        indegree[edge["consumer"]] += 1
    ready = [node["index"] for node in nodes if not indegree[node["index"]]]
    depth = dict.fromkeys(ready, 1)
    visited = 0
    while ready:
        source = ready.pop()
        visited += 1
        for child in children[source]:
            depth[child] = max(depth.get(child, 1), depth[source] + 1)
            indegree[child] -= 1
            if not indegree[child]:
                ready.append(child)
    handoffs = [
        event["payload"] for event in events if event["event_type"] == "logical.information.handoff"
    ]
    return {
        **row["workflow_detail"],
        "dependency_depth": max(depth.values(), default=0) if visited == len(nodes) else None,
        "acyclic": visited == len(nodes),
        "maximum_artifact_fanout": max(map(len, children.values()), default=0),
        "cross_owner_dependency_edges": sum(
            owners.get(edge["producer"]) != owners.get(edge["consumer"]) for edge in edges
        ),
        "artifact_handoffs": len(handoffs),
        "handed_off_artifact_count": sum(
            len(handoff.get("artifact_ids", [])) for handoff in handoffs
        ),
        "model_actions_without_artifact_inputs": sum(
            node["operator"] == "invoke_model" and node["input_count"] == 0 for node in nodes
        ),
    }


def concurrency_metadata(root):
    paths = sorted(root.glob("protocol-amendment-*.json"))
    serial, concurrent = set(), set()
    for path in paths:
        value = read(path)
        serial.update(label(cell) for cell in value.get("serial_completed_cell_ids", []))
        concurrent.update(label(cell) for cell in value.get("concurrent_cell_ids", []))
    return {
        "shared_resource_concurrency": 3 if paths else 1,
        "protocol_amendments": [receipt_metadata(path) for path in paths],
        "serial_completed_cell_ids": sorted(serial),
        "concurrent_cell_ids": sorted(concurrent),
        "resource_policy_amended": bool(paths),
        "tsr_is_primary": bool(paths),
        "e2e_is_diagnostic_not_exclusive_cost": bool(paths),
        "runner_log_sums_may_double_count_shared_work": bool(paths),
        "exclusive_gpu_cost": None,
    }


def slot_metrics(value):
    count, processing, invalid = 0, 0, 0
    if isinstance(value, dict):
        if "is_processing" in value:
            count += 1
            if type(value["is_processing"]) is not bool:
                invalid += 1
            else:
                processing += value["is_processing"]
        children = value.values()
    elif isinstance(value, list):
        children = value
    else:
        children = ()
    for child in children:
        metrics = slot_metrics(child)
        count += metrics["observed_slots"]
        processing += metrics["processing_slots"]
        invalid += metrics["invalid_slot_flags"]
    return {"observed_slots": count, "processing_slots": processing, "invalid_slot_flags": invalid}


def concurrency_audit(root, planned, concurrency):
    """Final metadata-only audit; never query a service or rescan historical code."""
    if not concurrency["resource_policy_amended"]:
        return {"applicable": False, "passed": True, "waves": [], "new_inference_calls": 0}
    amendment_path = root / "protocol-amendment-001.json"
    amendment = read(amendment_path) if amendment_path.exists() else {}
    source = root / "administration/run_skill_granularity_batch_v2.py"
    actual_source = sha(source) if source.is_file() else None
    expected_source = amendment.get("administration_source_sha256")
    expected_source = (
        expected_source
        if isinstance(expected_source, str) and SHA256.fullmatch(expected_source)
        else None
    )
    serial = concurrency["serial_completed_cell_ids"]
    expected = concurrency["concurrent_cell_ids"]
    frozen_ids = [cell["cell_id"] for cell in planned]
    frozen_models = {cell["cell_id"]: cell["candidate"] for cell in planned}
    waves, dispatched = [], []
    for path in sorted((root / "concurrency-waves").glob("wave-*.json")):
        if not re.fullmatch(r"wave-\d+", path.stem):
            continue
        wave = read(path)
        ids = [
            label(cell.get("cell_id") if isinstance(cell, dict) else cell)
            for cell in wave.get("cells", [])
        ]
        dispatched.extend(ids)
        drain_path = path.with_name(path.stem + "-model-drain.json")
        drain = read(drain_path) if drain_path.exists() else {}
        resident, planner = (
            slot_metrics(drain.get("resident_slots")),
            slot_metrics(drain.get("planner_slots")),
        )
        checks = {
            "declared_size_matches_cells": type(wave.get("actual_wave_size")) is int
            and wave["actual_wave_size"] == len(ids),
            "wave_size_within_dispatch_limit": 1 <= len(ids) <= 3,
            "maximum_concurrency_unchanged": wave.get("maximum_concurrency") == 3,
            "serving_request_parallelism_unchanged": wave.get("serving_request_parallelism") == 1,
            "no_recorded_system_errors": wave.get("system_errors") == [],
            "all_child_processes_exited": wave.get("all_child_processes_exited") is True,
            "drain_receipt_present": drain_path.is_file(),
            "real_drain_observation": drain.get("real_observation") is True,
            "all_shared_models_idle": drain.get("all_shared_models_idle") is True,
            "observed_resident_slots_idle": resident["observed_slots"] > 0
            and resident["processing_slots"] == 0
            and resident["invalid_slot_flags"] == 0,
            "observed_planner_slots_idle": planner["observed_slots"] > 0
            and planner["processing_slots"] == 0
            and planner["invalid_slot_flags"] == 0,
            "one_candidate_per_wave": len({frozen_models.get(cell) for cell in ids}) == 1
            and all(cell in frozen_models for cell in ids),
        }
        receipts, slots = [], []
        receipt_matches = True
        for cell_id in ids:
            receipt_path = root / "cells" / cell_id / "concurrency-receipt.json"
            receipt = read(receipt_path) if receipt_path.is_file() else {}
            receipt_matches &= (
                receipt.get("concurrency_wave") == path.stem
                and receipt.get("actual_wave_size") == len(ids)
                and receipt.get("shared_resource_concurrency") == 3
                and receipt.get("serving_request_parallelism") == 1
                and receipt.get("shared_executor_pool") is True
                and receipt.get("runner_log_intervals_may_overlap") is True
            )
            slots.append(receipt.get("slot"))
            receipts.append(
                {
                    "cell_id": cell_id,
                    "sha256": sha(receipt_path) if receipt_path.is_file() else None,
                }
            )
        checks["cell_receipts_match_wave"] = bool(receipt_matches)
        checks["cell_slots_unique_and_complete"] = all(type(slot) is int for slot in slots) and set(
            slots
        ) == set(range(len(ids)))
        waves.append(
            {
                "wave_id": path.stem,
                "cell_ids": ids,
                "actual_wave_size": wave.get("actual_wave_size"),
                "maximum_concurrency": wave.get("maximum_concurrency"),
                "serving_request_parallelism": wave.get("serving_request_parallelism"),
                "system_error_count": len(wave.get("system_errors", [])),
                "all_child_processes_exited": wave.get("all_child_processes_exited") is True,
                "all_shared_models_idle": drain.get("all_shared_models_idle") is True,
                "resident_slot_metrics": resident,
                "planner_slot_metrics": planner,
                "checks": checks,
                "passed": all(checks.values()),
                "wave_receipt_sha256": sha(path),
                "drain_receipt_sha256": sha(drain_path) if drain_path.is_file() else None,
                "cell_receipt_hashes": receipts,
            }
        )
    counts = Counter(dispatched)
    checks = {
        "administration_source_matches_amendment": actual_source is not None
        and actual_source == expected_source,
        "original_pre_registration_preserved": amendment.get("original_pre_registration_unchanged")
        is True,
        "original_freeze_hash_matches_amendment": amendment.get("original_execution_freeze_sha256")
        == sha(root / "execution-freeze.json")
        if (root / "execution-freeze.json").is_file()
        else False,
        "serial_and_concurrent_sets_disjoint": not set(serial) & set(expected),
        "serial_and_concurrent_cover_frozen_plan": set(serial) | set(expected) == set(frozen_ids),
        "every_concurrent_cell_dispatched_exactly_once": set(counts) == set(expected)
        and all(count == 1 for count in counts.values()),
        "no_duplicate_cell_dispatch": all(count == 1 for count in counts.values()),
        "serial_cells_excluded_from_waves": not set(serial) & set(dispatched),
        "fixed_remaining_dispatch_order_preserved": dispatched
        == [cell for cell in frozen_ids if cell not in set(serial)],
        "all_wave_checks_passed": bool(waves) and all(wave["passed"] for wave in waves),
        "all_model_drain_receipts_have_wave_records": {
            path.stem.removesuffix("-model-drain")
            for path in (root / "concurrency-waves").glob("wave-*-model-drain.json")
        }
        == {wave["wave_id"] for wave in waves},
    }
    return {
        "applicable": True,
        "passed": all(checks.values()),
        "checks": checks,
        "administration_source_expected_sha256": expected_source,
        "administration_source_observed_sha256": actual_source,
        "protocol_amendment_sha256": sha(amendment_path) if amendment_path.is_file() else None,
        "serial_cell_ids": serial,
        "expected_concurrent_cell_ids": expected,
        "dispatched_cell_count": len(dispatched),
        "unique_dispatched_cell_count": len(counts),
        "wave_count": len(waves),
        "waves": waves,
        "audit_scope": (
            "Final dispatch, exit and real-drain metadata only; "
            "no service query or historical source scan."
        ),
        "new_inference_calls": 0,
    }


def cell_concurrency(root, planned, concurrency):
    path = root / "cells" / planned["cell_id"] / "concurrency-receipt.json"
    receipt = read(path) if path.exists() else {}
    setting = receipt.get("shared_resource_concurrency")
    serial = planned["cell_id"] in concurrency["serial_completed_cell_ids"]
    if setting not in (1, 2, 3):
        setting = 1 if serial or not concurrency["resource_policy_amended"] else None
    overlaps = (
        receipt.get("runner_log_intervals_may_overlap") is True
        or planned["cell_id"] in concurrency["concurrent_cell_ids"]
    )
    return {
        "authorized_shared_resource_concurrency": concurrency["shared_resource_concurrency"],
        "shared_resource_concurrency": setting,
        "concurrency_wave": label(receipt.get("concurrency_wave")) if receipt else None,
        "actual_wave_size": receipt.get("actual_wave_size")
        if type(receipt.get("actual_wave_size")) is int
        else None,
        "slot": receipt.get("slot") if type(receipt.get("slot")) is int else None,
        "serving_request_parallelism": receipt.get("serving_request_parallelism")
        if type(receipt.get("serving_request_parallelism")) is int
        else None,
        "shared_executor_pool": receipt.get("shared_executor_pool") if receipt else None,
        "runner_log_intervals_may_overlap": overlaps or setting in (2, 3),
        "execution_cohort": "serial_before_amendment"
        if serial
        else "shared_resource_wave"
        if receipt
        else "serial_frozen_initial_protocol"
        if not concurrency["resource_policy_amended"]
        else "unrecorded_concurrency",
        "concurrency_receipt_sha256": sha(path) if path.exists() else None,
        "e2e_is_diagnostic_not_exclusive_cost": concurrency["e2e_is_diagnostic_not_exclusive_cost"],
        "exclusive_gpu_cost": None,
    }


def legacy_response_error_view(path):
    """Adapt a legacy .get(error) read without modifying a persisted null response.

    A null error-response capture has no error field. Its real shape, transport
    exception, missing usage and original SHA are separately exported. This view
    never constructs a response, Function Call, success flag or token usage.
    """
    value = read(path)
    return {} if path.name.endswith("-response.json") and value is None else value


def safe_cell(root, planned, concurrency):
    cell = root / "cells" / planned["cell_id"]
    original = read(cell / "sanitized-result.json")
    for field in ("cell_id", "candidate", "skill_condition", "task_index"):
        if original["cell"].get(field) != planned.get(field):
            raise RuntimeError("Sanitized result differs from its frozen cell identity")
    # Old enrichment assumes every saved error response is an object. Patch only
    # its in-memory reader for this offline call, then restore it even on failure.
    original_reader = legacy_analysis.read
    legacy_analysis.read = legacy_response_error_view
    try:
        row = safe_row(root, original)
    finally:
        legacy_analysis.read = original_reader
    row["cell"]["skill_condition"] = planned["skill_condition"]
    row["cell"]["execution_index"] = planned["execution_index"]
    row["execution_conditions"] = {
        "manager_node": "A28" if planned["candidate"] != "qwen35-27b" else "strong-4090-gpu0",
        "independent_manager_endpoint": planned["candidate"] != "qwen35-27b",
        "gpu_price_known": False,
        **cell_concurrency(root, planned, concurrency),
    }
    events = events_for(cell)
    row["schema_detail"].update(schema_details(events))
    row["workflow_detail"] = workflow_shape(row, events)
    row["provider_diagnostics"] = provider_findings(root, cell)
    if row["outcome_type"] == "context_budget_exceeded":
        # The SDK may wrap a local preflight rejection in APIConnectionError.
        # The recorded preflight outcome takes precedence over that outer type.
        for finding in row["provider_diagnostics"]["errors"]:
            if finding["category"] == "provider_connection_error":
                finding["category"] = "context_preflight_rejection"
                finding["transport_failure_confirmed"] = False
                finding["inference_forwarded"] = False
        row["provider_diagnostics"]["categories"] = dict(
            Counter(finding["category"] for finding in row["provider_diagnostics"]["errors"])
        )
    row["provider_error_types"] = row["provider_diagnostics"]["categories"]
    if not row["completed"] and row["outcome_type"] != "context_budget_exceeded":
        for category in (
            "provider_xml_tool_call_parse_error",
            "provider_json_syntax_error",
            "provider_timeout_error",
            "provider_oom_error",
            "provider_connection_error",
        ):
            if row["provider_error_types"].get(category):
                row["outcome_type"] = category
                break
    applicable = planned["candidate"] != "qwen35-27b"
    work = (
        independent_planner_work(cell)
        if applicable
        else {
            "observed": False,
            "runner_task_starts": None,
            "reported_total_time_ms_sum": None,
            "reported_evaluation_units": {},
        }
    )
    work["applicable"] = applicable
    row["independent_planner_runner_work"] = work
    row["resident_runner_work"]["log_intervals_may_overlap"] = row["execution_conditions"][
        "runner_log_intervals_may_overlap"
    ]
    row["independent_planner_runner_work"]["log_intervals_may_overlap"] = row[
        "execution_conditions"
    ]["runner_log_intervals_may_overlap"]
    row["resident_runner_work"]["observed"] = bool(
        list((cell / "private/residency-log-intervals").glob("*.json"))
    )
    if not row["resident_runner_work"]["observed"]:
        row["resident_runner_work"]["observed_task_starts"] = None
        row["resident_runner_work"]["reported_total_time_ms_sum"] = None
    for role, metrics in row["roles"].items():
        metrics["known_cached_input_tokens_subtotal"] = sum(
            usage.get("prompt_tokens_details", {}).get("cached_tokens", 0) or 0
            for receipt in (cell / "private/api").rglob("*-usage.json")
            if (value := read(receipt)).get("recipient") == role
            for usage in [value.get("usage") or {}]
        )
    return row


def verifier_amplification(summary):
    manager, verifier = summary["roles"]["manager"], summary["roles"]["verifier"]
    success = summary["successful"]
    verifier_usd = verifier["cloud_api_cost"]
    complete_usd = verifier_usd["complete_usd_total"]
    return {
        "verifier_to_manager_turn_ratio": ratio(verifier["turns"], manager["turns"]),
        "verifier_to_manager_request_ratio": ratio(verifier["requests"], manager["requests"]),
        "verifier_to_manager_input_token_ratio": ratio(
            verifier["input_tokens"], manager["input_tokens"]
        ),
        "verifier_to_manager_output_token_ratio": ratio(
            verifier["output_tokens"], manager["output_tokens"]
        ),
        "verifier_turns_per_success": ratio(verifier["turns"], success),
        "verifier_requests_per_success": ratio(verifier["requests"], success),
        "verifier_input_tokens_per_success": ratio(verifier["input_tokens"], success),
        "verifier_output_tokens_per_success": ratio(verifier["output_tokens"], success),
        "verifier_complete_usd_per_success": str(Decimal(complete_usd) / success)
        if complete_usd is not None and success
        else None,
        "verifier_known_usd_subtotal_per_success": str(
            Decimal(verifier_usd["known_usd_subtotal"]) / success
        )
        if success
        else None,
        "successful_tasks_denominator": success,
    }


def summarize(rows):
    # aggregate requires numeric resident log counters; preserve its known
    # subtotal then explicitly restore complete totals to unknown if unobserved.
    aggregate_rows = copy.deepcopy(rows)
    for row in aggregate_rows:
        for field in ("observed_task_starts", "reported_total_time_ms_sum"):
            if row["resident_runner_work"][field] is None:
                row["resident_runner_work"][field] = 0
    result = aggregate(aggregate_rows)
    result["runner_known_task_starts_subtotal"] = result["runner_task_starts"]
    result["runner_known_reported_total_time_ms_subtotal"] = result["runner_reported_total_time_ms"]
    result["runner_task_starts"] = total(
        row["resident_runner_work"]["observed_task_starts"] for row in rows
    )
    result["runner_reported_total_time_ms"] = total(
        row["resident_runner_work"]["reported_total_time_ms_sum"] for row in rows
    )
    result["resident_runner_unobserved_cells"] = sum(
        not row["resident_runner_work"]["observed"] for row in rows
    )
    result["schema_attempts"] = sum(row["schema_attempts"] for row in rows)
    result["schema_valid"] = sum(row["schema_valid"] for row in rows)
    result["raw_schema_validity"] = ratio(result["schema_valid"], result["schema_attempts"])
    result["schema_by_role"] = {
        role: {
            **{
                field: sum(row["schema_detail"]["by_role"][role][field] for row in rows)
                for field in ("attempts", "valid", "invalid")
            },
            "validity": ratio(
                sum(row["schema_detail"]["by_role"][role]["valid"] for row in rows),
                sum(row["schema_detail"]["by_role"][role]["attempts"] for row in rows),
            ),
        }
        for role in ("manager", "specialist")
    }
    result["schema_recovery"] = {
        field: sum(row["schema_detail"][field] for row in rows)
        for field in (
            "owners_with_invalid_call",
            "owners_with_later_valid_call",
            "invalid_calls_with_later_valid_same_owner_and_tool",
            "invalid_calls_without_later_valid_same_owner_and_tool",
        )
    }
    result["schema_invalid_categories_nonexclusive"] = dict(
        sum(
            (Counter(row["schema_detail"]["invalid_call_categories_nonexclusive"]) for row in rows),
            Counter(),
        )
    )
    result["provider_error_types"] = dict(
        sum((Counter(row["provider_error_types"]) for row in rows), Counter())
    )
    result["provider_response_body_shapes"] = dict(
        sum(
            (Counter(row["provider_diagnostics"]["response_body_shapes"]) for row in rows),
            Counter(),
        )
    )
    result["workflow"] = {
        field: sum(row["workflow_detail"][field] for row in rows)
        for field in (
            "node_count",
            "edge_count",
            "repeated_identical_selected_calls",
            "specialist_invocations",
            "artifact_handoffs",
            "handed_off_artifact_count",
            "cross_owner_dependency_edges",
            "model_actions_without_artifact_inputs",
        )
    }
    result["workflow"]["operators"] = dict(
        sum((Counter(row["workflow_detail"]["operators"]) for row in rows), Counter())
    )
    applicable = [
        row["independent_planner_runner_work"]
        for row in rows
        if row["independent_planner_runner_work"]["applicable"]
    ]
    result["independent_planner_runner_work"] = {
        "applicable_cells": len(applicable),
        "not_applicable_cells": len(rows) - len(applicable),
        "observed_cells": sum(work["observed"] for work in applicable),
        "unobserved_cells": sum(not work["observed"] for work in applicable),
        "known_runner_task_starts_subtotal": sum(
            work["runner_task_starts"] or 0 for work in applicable
        ),
        "known_reported_total_time_ms_subtotal": sum(
            work["reported_total_time_ms_sum"] or 0 for work in applicable
        ),
        "complete_reported_total_time_ms": total(
            work["reported_total_time_ms_sum"] for work in applicable
        )
        if applicable
        else None,
        "applicable": bool(applicable),
    }
    overlapping = any(
        row["execution_conditions"]["runner_log_intervals_may_overlap"] for row in rows
    )
    result["execution_cohorts"] = dict(
        Counter(row["execution_conditions"]["execution_cohort"] for row in rows)
    )
    result["runner_log_work_attribution"] = {
        "reported_proxy": "overlapping_reported_proxy"
        if overlapping
        else "captured_interval_proxy",
        "log_intervals_may_overlap": overlapping,
        "sums_are_exclusive_cell_service_cost": False,
        "resident_interval_reported_ms_sum": result["runner_reported_total_time_ms"],
        "independent_interval_reported_ms_sum": result["independent_planner_runner_work"][
            "complete_reported_total_time_ms"
        ],
        "exclusive_cell_service_work_ms": None,
        "exclusive_gpu_cost": None,
    }
    result["unmeasured_failed_model_service_work"] = any(
        row["physical"].get("unmeasured_failed_model_service_work", False) for row in rows
    )
    result["original_scores"] = [
        (row.get("original_evaluation") or {}).get("score") for row in rows
    ]
    result["evaluated_tasks"] = sum(score is not None for score in result["original_scores"])
    result["verifier_amplification"] = verifier_amplification(result)
    result["cost_per_success"] = {
        "known_cloud_usd_subtotal": str(
            Decimal(result["cloud_api_cost"]["known_usd_subtotal"]) / result["successful"]
        )
        if result["successful"]
        else None,
        "complete_cloud_usd": str(
            Decimal(result["cloud_api_cost"]["complete_usd_total"]) / result["successful"]
        )
        if result["successful"] and result["cloud_api_cost"]["complete_usd_total"] is not None
        else None,
        "task_e2e_ms": ratio(result["task_e2e_ms"], result["successful"]),
        "physical_successful_inference_calls": ratio(
            result["physical"]["successful_inference_calls"], result["successful"]
        ),
        "full_resource_monetary_cost": None,
    }
    for role in ROLES:
        result["roles"][role]["unknown_cached_usage_requests"] = sum(
            row["roles"][role]["unknown_cached_usage_requests"] for row in rows
        )
    return result


def paired_comparisons(rows):
    indexed = {
        (row["cell"]["candidate"], row["cell"]["skill_condition"], row["cell"]["task_index"]): row
        for row in rows
    }
    comparisons = []
    trajectories = []
    for candidate in CANDIDATES:
        conditions = [condition for condition in SKILLS if (candidate, condition, 1) in indexed]
        for task in (1, 2, 3):
            trajectories.append(
                {
                    "candidate": candidate,
                    "task_index": task,
                    "conditions": {
                        condition: {
                            "cell_id": indexed[candidate, condition, task]["cell"]["cell_id"],
                            "completed": indexed[candidate, condition, task]["completed"],
                            "successful": indexed[candidate, condition, task]["successful"],
                            "score": (
                                indexed[candidate, condition, task].get("original_evaluation") or {}
                            ).get("score"),
                            "outcome_type": indexed[candidate, condition, task]["outcome_type"],
                            "workflow": indexed[candidate, condition, task]["workflow"],
                            "workflow_detail": indexed[candidate, condition, task][
                                "workflow_detail"
                            ],
                        }
                        for condition in conditions
                    },
                    "not_run_conditions": [
                        condition for condition in SKILLS if condition not in conditions
                    ],
                }
            )
        for left_index, left in enumerate(conditions):
            for right in conditions[left_index + 1 :]:
                before = summarize([indexed[candidate, left, task] for task in (1, 2, 3)])
                after = summarize([indexed[candidate, right, task] for task in (1, 2, 3)])
                comparisons.append(
                    {
                        "candidate": candidate,
                        "reference": left,
                        "comparison": right,
                        "paired_tasks": 3,
                        "task_indices": [1, 2, 3],
                        "delta_comparison_minus_reference": difference(before, after),
                        "cloud_known_usd_delta": str(
                            Decimal(after["cloud_api_cost"]["known_usd_subtotal"])
                            - Decimal(before["cloud_api_cost"]["known_usd_subtotal"])
                        ),
                        "complete_cloud_usd_delta": str(
                            Decimal(after["cloud_api_cost"]["complete_usd_total"])
                            - Decimal(before["cloud_api_cost"]["complete_usd_total"])
                        )
                        if after["cloud_api_cost"]["complete_usd_total"] is not None
                        and before["cloud_api_cost"]["complete_usd_total"] is not None
                        else None,
                        "paired_task_deltas": [
                            {
                                "task_index": task,
                                "delta": difference(
                                    summarize([indexed[candidate, left, task]]),
                                    summarize([indexed[candidate, right, task]]),
                                ),
                            }
                            for task in (1, 2, 3)
                        ],
                        "descriptive_only": True,
                        "full_resource_monetary_cost_delta": None,
                    }
                )
    return comparisons, trajectories


def receipt_metadata(path):
    value = read(path)
    return {
        "sha256": sha(path),
        "identity": safe_metadata(value),
        "numeric_evidence": numeric_tree(value),
        "system_problems": [label(problem) for problem in value.get("system_problems", [])],
        "analysis_errors": [
            {field: label(error.get(field)) for field in ("cell_id", "exception_type")}
            for error in value.get("analysis_errors", [])
            if isinstance(error, dict)
        ],
    }


def resume_metadata(root):
    """Preserve administrative interruptions without exporting exception messages."""
    batches = []
    for directory in sorted(root.glob("resume-network-*")):
        if not directory.is_dir():
            continue
        stopped = directory / "batch-stopped.json"
        tc_path = directory / "tc-attestation.json"
        tc = read(tc_path) if tc_path.is_file() else {}
        message = str(read(stopped).get("message", "")).lower() if stopped.is_file() else ""
        batches.append(
            {
                "network_batch_id": label(directory.name),
                "interruption_recorded": stopped.is_file(),
                "interruption_class": (
                    "port_bind_conflict"
                    if "address already in use" in message or "errno 98" in message
                    else "administrative_interruption_other"
                    if stopped.is_file()
                    else None
                ),
                "interruption_receipt": receipt_metadata(stopped) if stopped.is_file() else None,
                "network_attestation": receipt_metadata(tc_path) if tc_path.is_file() else None,
                "network_restoration_confirmed": (
                    not tc.get("cleanup_error")
                    and tc.get("original_qdisc") == tc.get("restored_qdisc")
                    if tc_path.is_file() and "original_qdisc" in tc and "restored_qdisc" in tc
                    else None
                ),
                "partial_integrity": receipt_metadata(directory / "partial-integrity.json")
                if (directory / "partial-integrity.json").is_file()
                else None,
                "service_cleanup_error": receipt_metadata(directory / "service-cleanup-error.json")
                if (directory / "service-cleanup-error.json").is_file()
                else None,
            }
        )
    paths = [path for path in root.glob("concurrent-resume-*") if path.is_file()]
    root_receipts = []
    for path in sorted(paths):
        if path.suffix != ".json":
            continue
        value = read(path)
        reason = str(value.get("reason", "")).lower()
        root_receipts.append(
            {
                "event_id": label(path.stem),
                **receipt_metadata(path),
                "model_group_transition": "model-group boundary" in reason,
                "interruption_class": "port_bind_conflict"
                if "port bind conflict" in reason or "address already in use" in reason
                else "administrative_resume_other",
                "completed_cells_preserved": value.get("completed_cells_preserved")
                if type(value.get("completed_cells_preserved")) is int
                else None,
                "unfinished_claims": value.get("unfinished_claims")
                if type(value.get("unfinished_claims")) is int
                else None,
                "runtime_changed": value.get("runtime_changed")
                if type(value.get("runtime_changed")) is bool
                else None,
                "semantic_retries": value.get("semantic_retries")
                if type(value.get("semantic_retries")) is int
                else None,
            }
        )
    return {
        "network_batches": batches,
        "network_batch_count": len(batches),
        "recorded_interruptions": sum(batch["interruption_recorded"] for batch in batches),
        "completed_after_recorded_interruption": any(
            batch["interruption_recorded"] for batch in batches
        ),
        "root_resume_receipts": root_receipts,
        "root_resume_artifact_hashes": evidence_manifest(root, paths),
        "exception_messages_exported": False,
        "new_inference_calls": 0,
    }


def token_lengths(root):
    result = {}
    for path in sorted(root.glob("skill-token-lengths-*.json")):
        candidate = path.stem.removeprefix("skill-token-lengths-")
        if candidate not in CANDIDATES:
            raise RuntimeError("Unknown model tokenizer receipt identity")
        value = read(path)
        result[candidate] = receipt_metadata(path)
        blob = value.get("tokenizer_model_blob")
        result[candidate]["tokenizer_model_blob"] = (
            blob if isinstance(blob, str) and SHA256.fullmatch(blob) else None
        )
    return result


def safe_hash_map(value):
    if not isinstance(value, dict):
        return {}
    return {
        hashlib.sha256(str(name).encode()).hexdigest(): digest
        for name, digest in value.items()
        if isinstance(digest, str) and SHA256.fullmatch(digest)
    }


def configuration_metadata(value):
    """Only explicit deployment identity strings; other strings remain private."""
    fields = {
        "candidate",
        "model",
        "tag",
        "model_tag",
        "model_blob",
        "model_digest",
        "digest",
        "sha256",
        "quantization",
        "quantization_level",
        "family",
        "num_ctx",
        "temperature",
        "top_p",
        "max_tokens",
        "thinking",
        "think",
        "reasoning_effort",
        "backend",
        "serving_backend",
        "placement",
        "display_name",
        "version",
        "renderer",
        "parser",
        "manager_node",
        "actual_family",
        "actual_model",
        "tokenizer_model_blob",
    }
    if isinstance(value, dict):
        result = {}
        for field, item in value.items():
            if label(field) == "unknown":
                continue
            if isinstance(item, (dict, list)):
                nested = configuration_metadata(item)
                if nested:
                    result[field] = nested
            elif field in fields and (
                item is None
                or type(item) in (int, float, bool)
                or isinstance(item, str)
                and (
                    label(item) != "unknown"
                    or SHA256.fullmatch(item)
                    or field == "serving_backend"
                    and re.fullmatch(r"[A-Za-z][A-Za-z0-9._-]* [0-9][A-Za-z0-9._-]*", item)
                )
            ):
                result[field] = item
        return result
    if isinstance(value, list):
        return [item for child in value if (item := configuration_metadata(child))]
    return None


def fmt(value):
    if value is None:
        return "unknown"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def markdown_cell(value):
    return fmt(value).replace("|", "/").replace("\n", " ").replace("<", "&lt;").replace(">", "&gt;")


def seconds(value):
    return fmt(value / 1000 if value is not None else None)


def table(headers, values):
    return [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(markdown_cell(value) for value in row) + " |" for row in values),
        "",
    ]


def report(data):
    conditions = data["conditions"]
    lines = [
        "# Skill Granularity Pilot v2 — final results",
        "",
        "All 30 frozen cells are included: three tasks per condition; 4B and 9B have "
        "S0/S1/S2/S3 and 27B has its two preregistered conditions. S0=no Skills; "
        "S1=unchanged abstract guidance; S2=procedure with real schemas; S3=conditional "
        "atomic SOP. These are different content/length treatments, not an isolated "
        "causal test of presentation granularity.",
        "",
        "The frozen `qwen35-27b` slot uses the existing Qwen3.8-27B deployment; "
        "it is not a Qwen3.5-27B checkpoint. The 4B/9B Managers use the independent "
        "A28 replicas (one runner slot each); 27B shares the existing resident endpoint. Specialist, Verifier, "
        "Executor and Physical Scheduler are fixed. Cross-scale latency comparisons "
        "therefore also reflect deployment differences.",
        "",
        "## Completion, quality and protocol reliability",
        "",
    ]
    models = data["execution_freeze"]["frozen_configuration"].get("plan", {}).get("models", {})
    lines += table(
        [
            "Frozen candidate",
            "Actual model",
            "Model blob",
            "Quantization",
            "Context/output",
            "Temperature/top-p",
            "Thinking/effort",
            "Backend",
            "Manager placement",
        ],
        [
            [
                candidate,
                model.get("display_name"),
                model.get("model_blob"),
                model.get("quantization"),
                f"{model.get('num_ctx')}/{model.get('max_tokens')}",
                f"{model.get('temperature')}/{model.get('top_p')}",
                f"{model.get('thinking')}/{model.get('reasoning_effort')}",
                model.get("serving_backend"),
                model.get("placement"),
            ]
            for candidate, model in models.items()
        ],
    )
    concurrency = data["execution_conditions"]
    if concurrency["resource_policy_amended"]:
        lines += [
            "The v2 serving protocol uses three concurrent workflow cells and two "
            "independent A28 Ollama one-slot replicas. Every one of the 30 frozen "
            "cells was rerun once in this separate namespace. Manager requests wait "
            "for a free endpoint slot on the client. The 27B resident endpoint remains "
            "one slot. TSR is primary; E2E and shared log service work are diagnostic.",
            "",
        ]
        lines += table(
            [
                "Cell",
                "Cohort",
                "Dispatch ceiling",
                "Wave",
                "Actual wave size",
                "Serving request parallelism",
                "Log intervals may overlap",
            ],
            [
                [
                    row["cell"]["cell_id"],
                    row["execution_conditions"]["execution_cohort"],
                    row["execution_conditions"]["shared_resource_concurrency"],
                    row["execution_conditions"]["concurrency_wave"],
                    row["execution_conditions"]["actual_wave_size"],
                    row["execution_conditions"]["serving_request_parallelism"],
                    row["execution_conditions"]["runner_log_intervals_may_overlap"],
                ]
                for row in data["cells"]
            ],
        )
        lines += [
            "Cells in the same wave can capture overlapping intervals from the "
            "same resident or independent Planner service log. Summed log times "
            "are therefore an overlapping reported proxy: they can double-count "
            "shared work and must not be interpreted as exclusive per-cell "
            "service work, GPU cost, or a causal cost effect of Skills. API usage "
            "and trace-recorded physical calls remain attributed to their own "
            "cells. The serial/shared cohort difference is preserved, including "
            "possible queue and timeout effects; latency deltas do not determine "
            "the TSR assessment.",
            "",
        ]
    lines += table(
        [
            "Condition",
            "Completion",
            "TSR",
            "Raw valid/calls",
            "Schema failures",
            "Provider errors",
            "Outcomes",
        ],
        [
            [
                name,
                f"{s['completed']}/3",
                f"{s['successful']}/3",
                f"{s['schema_valid']}/{s['schema_attempts']}",
                s["schema_failures"],
                json.dumps(s["provider_error_types"], sort_keys=True),
                json.dumps(s["outcome_types"], sort_keys=True),
            ]
            for name, s in conditions.items()
        ],
    )
    lines += [
        "Schema validity divides valid original parsed operator/delegation Function Calls "
        "by all such calls reaching the strict application validator, across Manager and "
        "Specialists. It excludes Verifier structured-output validation and provider "
        "responses that never yielded a parsed Function Call. One call with several "
        "schema defects counts once. HTTP 500 XML/JSON parser failures remain a separate "
        "protocol layer; they cannot establish pure task-reasoning failure.",
        "",
        "## Recovery and workflow structure",
        "",
    ]
    lines += table(
        [
            "Condition",
            "Manager valid/calls",
            "Specialist valid/calls",
            "Later-valid/invalid calls",
            "Verifier invalid",
            "Nodes/edges",
            "Repeated calls",
            "Specialists",
        ],
        [
            [
                name,
                f"{s['schema_by_role']['manager']['valid']}/{s['schema_by_role']['manager']['attempts']}",
                f"{s['schema_by_role']['specialist']['valid']}/{s['schema_by_role']['specialist']['attempts']}",
                f"{s['schema_recovery']['invalid_calls_with_later_valid_same_owner_and_tool']}/{s['schema_failures']}",
                s["verifier_schema_failures"],
                f"{s['workflow']['node_count']}/{s['workflow']['edge_count']}",
                s["workflow"]["repeated_identical_selected_calls"],
                s["workflow"]["specialist_invocations"],
            ]
            for name, s in conditions.items()
        ],
    )
    lines += [
        "Recovery here means an invalid call is followed by a valid call to the same "
        "tool by the same owner. Several invalid calls can precede one valid call; "
        "this is a descriptive recovery signal, not proof of matching semantic intent "
        "or successful task completion. Repeated calls share identical selected "
        "arguments; this count does not by itself prove redundancy.",
        "",
        "## Role turns, usage and API cost",
        "",
    ]
    lines += table(
        [
            "Condition/role",
            "Requests/turns",
            "Input tokens",
            "Output tokens",
            "Cached tokens",
            "Unknown usage requests",
            "Known input/output subtotal",
            "API USD known",
            "API USD complete",
        ],
        [
            [
                name + "/" + role,
                f"{m['requests']}/{m['turns']}",
                m["input_tokens"],
                m["output_tokens"],
                m["cached_input_tokens"],
                m["unknown_token_usage_requests"],
                f"{m['known_input_tokens_subtotal']}/{m['known_output_tokens_subtotal']}",
                m["cloud_api_cost"]["known_usd_subtotal"],
                m["cloud_api_cost"]["complete_usd_total"],
            ]
            for name, s in conditions.items()
            for role, m in s["roles"].items()
        ],
    )
    lines += [
        "Missing usage remains unknown; known subtotals are lower bounds and do not "
        "replace complete totals. Zero requests legitimately yields zero usage. "
        "Cloud prices use the frozen accounting card and are estimates, not invoices. "
        "A local Manager's zero cloud charge excludes its unknown hardware/energy cost.",
        "",
        "## Verifier amplification and cost per successful task",
        "",
    ]
    lines += table(
        [
            "Condition",
            "V/M turns",
            "V/M input tokens",
            "V turns/success",
            "V API USD/success complete",
            "All cloud USD/success complete",
            "E2E diagnostic s/success",
        ],
        [
            [
                name,
                s["verifier_amplification"]["verifier_to_manager_turn_ratio"],
                s["verifier_amplification"]["verifier_to_manager_input_token_ratio"],
                s["verifier_amplification"]["verifier_turns_per_success"],
                s["verifier_amplification"]["verifier_complete_usd_per_success"],
                s["cost_per_success"]["complete_cloud_usd"],
                seconds(s["cost_per_success"]["task_e2e_ms"]),
            ]
            for name, s in conditions.items()
        ],
    )
    lines += [
        "Per-success numerators include all three attempts, including failures; "
        "the denominator is successful tasks. No successes gives unknown, not zero. "
        "V/M uses aggregate role totals, not the mean of cell ratios. More Verifier "
        "work can accompany repeated evidence batches and recovery; these traces "
        "do not isolate a causal Verifier effect.",
        "",
        "## Physical work, service proxies and data transfer",
        "",
    ]
    lines += table(
        [
            "Condition",
            "Physical successes/admissions",
            "Known physical service s",
            "Resident log interval proxy s",
            "Independent Planner log interval proxy s",
            "E2E diagnostic s",
            "Initial/action artifact bytes",
            "Cloud USD known/unknown calls",
            "Full cost",
        ],
        [
            [
                name,
                f"{s['physical']['successful_inference_calls']}/{s['physical']['admitted_requests']}",
                seconds(s["physical"]["known_model_service_ms"]),
                seconds(s["runner_reported_total_time_ms"]),
                seconds(s["independent_planner_runner_work"]["complete_reported_total_time_ms"])
                if s["independent_planner_runner_work"]["applicable"]
                else "not applicable (resident)",
                seconds(s["task_e2e_ms"]),
                f"{s['physical']['initial_transfer_bytes']}/{s['physical']['action_transfer_bytes']}",
                f"{s['cloud_api_cost']['known_usd_subtotal']}/{s['cloud_api_cost']['unknown_usd_calls']}",
                "unknown",
            ]
            for name, s in conditions.items()
        ],
    )
    lines += [
        "Admissions are not all completed inference calls. Failed/cancelled work can "
        "lack telemetry. Resident runner logs include the 27B Manager when it shares "
        "that endpoint; independent Planner logs are separate for 4B/9B and are not "
        "applicable to 27B. Missing logs remain unknown. Runner timings are partial "
        "service-work proxies, not GPU busy time; caches/speculative decode units "
        "differ from billed token usage. Service sums can overlap and must not be "
        "added to E2E. Artifact bytes are application transfers, not wire traffic. "
        "Persisted API JSON sizes are storage proxies, not network counters. GPU "
        "prices and complete GPU/energy costs are unknown. Under shared-resource "
        "concurrency, log interval sums can overlap and duplicate work; they "
        "cannot identify exclusive costs. Per-call physical telemetry remains "
        "attributable, while its latency can include shared-resource waiting.",
        "",
        "## Paired Skill comparisons",
        "",
    ]
    lines += table(
        [
            "Model",
            "Comparison",
            "Completion delta",
            "TSR count delta",
            "Schema-failure delta",
            "Manager-turn delta",
            "Verifier-turn delta",
            "Physical-call delta",
            "E2E diagnostic s delta",
            "Known cloud USD delta",
        ],
        [
            [
                c["candidate"],
                c["reference"] + " → " + c["comparison"],
                c["delta_comparison_minus_reference"].get("completed"),
                c["delta_comparison_minus_reference"].get("successful"),
                c["delta_comparison_minus_reference"].get("schema_failures"),
                c["delta_comparison_minus_reference"]["roles"]["manager"].get("turns"),
                c["delta_comparison_minus_reference"]["roles"]["verifier"].get("turns"),
                c["delta_comparison_minus_reference"]["physical"].get("successful_inference_calls"),
                seconds(c["delta_comparison_minus_reference"].get("task_e2e_ms")),
                c["cloud_known_usd_delta"],
            ]
            for c in data["paired_comparisons"]
        ],
    )
    lines += [
        "Differences are comparison minus reference on identical task indices. "
        "Lower cost caused by an early failure is not evidence of efficiency. "
        "Inspect completion, TSR and failure layers together with each resource "
        "vector; the machine-readable artifact retains every paired task delta.",
        "",
        "## Same-task S0 → S1 → S2 → S3 behavior",
        "",
    ]
    lines += table(
        [
            "Model/task",
            "Condition",
            "Outcome",
            "Score",
            "Workflow operators",
            "Nodes/edges/depth",
            "Handoffs",
            "Repeated calls",
        ],
        [
            [
                trajectory["candidate"] + "/t" + str(trajectory["task_index"]),
                condition,
                item["outcome_type"],
                item["score"],
                " → ".join(node["operator"] for node in item["workflow"]["nodes"]) or "none",
                f"{item['workflow_detail']['node_count']}/{item['workflow_detail']['edge_count']}/{fmt(item['workflow_detail']['dependency_depth'])}",
                item["workflow_detail"]["artifact_handoffs"],
                item["workflow_detail"]["repeated_identical_selected_calls"],
            ]
            for trajectory in data["task_trajectories"]
            for condition, item in trajectory["conditions"].items()
        ],
    )
    lines += [
        "Unscheduled 27B Skill conditions are not run, not failed. Workflow edges "
        "describe artifact dependencies; the operator sequence is executed graph "
        "order rather than a claim that all calls were sequential. Missing artifact "
        "inputs are a structural metric, not proof that reasoning lacked evidence.",
        "",
        "## Skill context overhead",
        "",
        "The following numeric receipts come from each deployed model's independent "
        "tokenizer, with no generation. Token lengths and instruction increments "
        "are model-specific; bytes and words are not substituted for tokens. Actual "
        "Manager usage above includes Skills within each request and the evolving "
        "history. Usage deltas also reflect different call counts and workflows.",
        "",
    ]
    token_rows = []
    for candidate in CANDIDATES:
        receipt = data["skill_token_lengths"].get(candidate) or {}
        metrics = receipt.get("numeric_evidence", {})
        for condition in SKILLS:
            item = metrics.get("skills", {}).get(condition, {})
            token_rows.append(
                [
                    candidate,
                    condition,
                    item.get("utf8_bytes"),
                    item.get("standalone_tokens"),
                    item.get("manager_instruction_tokens"),
                    item.get("manager_instruction_increment_tokens"),
                    metrics.get("base_instruction_tokens"),
                    metrics.get("inference_calls"),
                ]
            )
    lines += table(
        [
            "Tokenizer model",
            "Condition",
            "UTF-8 bytes",
            "Standalone tokens",
            "Manager instruction tokens",
            "Instruction increment",
            "Base instruction",
            "Tokenizer generation calls",
        ],
        token_rows,
    )
    lines += ["## Provider parsing failure evidence", ""]
    findings = [
        (row, item) for row in data["cells"] for item in row["provider_diagnostics"]["errors"]
    ]
    lines += table(
        [
            "Cell",
            "Role",
            "HTTP",
            "Response body shape",
            "Class",
            "Component confirmed",
            "XML line/open/close",
            "JSON after-key/in-string",
        ],
        [
            [
                row["cell"]["cell_id"],
                finding["role"],
                finding["http_status"],
                finding["response_body_shape"],
                finding["category"],
                finding["component_confirmed"],
                f"{fmt(finding['xml_line'])}/{fmt(finding['xml_open_tag'])}/{fmt(finding['xml_close_tag'])}",
                f"{finding['json_error_after_object_key']}/{finding['json_error_in_string_literal']}",
            ]
            for row, finding in findings
        ],
    )
    lines += [
        "Only matching static log source markers establish a specific Qwen XML "
        "parser attribution. JSON syntax messages alone leave the particular "
        "parser/renderer component unknown. Absence of OOM/timeout/truncation "
        "markers is limited to the captured cell service logs. These are this "
        "pilot's observed errors; historical seven-error findings are not imported "
        "as new results.",
        "Persisted JSON null on an APITimeoutError means no object response was "
        "captured, not that the model produced malformed JSON. The original null "
        "file is preserved and hashed, HTTP status and usage remain unknown, and "
        "the timeout is classified at the transport/provider layer. Shared-service "
        "queuing can contribute to these failures; they do not isolate intrinsic "
        "Planner competence.",
        "",
        "## Interpretation and next stage",
        "",
        "This is a descriptive three-task pilot, one execution per condition/task, "
        "not a significant TSR comparison, non-inferiority result or competence "
        "threshold estimate. Balanced frozen order reduces some order imbalance "
        "but does not eliminate caching, residency, external workload or temporal "
        "confounding. More detailed Skills also supply additional procedural "
        "content and tokens, so improvements cannot be assigned solely to granularity.",
        "",
        "A useful next-stage candidate must retain task success while improving "
        "protocol reliability/recovery at an acceptable full resource vector. "
        "No complete monetary frontier is identified with GPU cost unknown. "
        "Resolve persistent protocol/terminal failures before attributing a gain "
        "to semantic planning; a larger held-out evaluation would be needed for "
        "generalization or an Infra-aware Workflow Adapter decision.",
        "",
        "## Integrity and evidence",
        "",
        "The runner's final integrity receipt is referenced by hash and exported "
        "as sanitized numeric evidence; this analyzer does not repeat source, "
        "history, evaluator or system scans. No new inference or selective task "
        "reruns were performed by analysis. Raw traces, prompts, responses, task "
        "bodies, artifact identities and private evidence paths stay on the "
        "experiment machine. Anonymous file IDs and SHA256 hashes link evidence; "
        "the private mapping remains there. Export generation is refused until "
        "the completion marker and all 30 sanitized cell results exist.",
        "",
    ]
    lines += table(
        ["Final receipt", "SHA256", "Sanitized integrity evidence"],
        [
            [
                "final-integrity",
                data["final_integrity"]["sha256"],
                json.dumps(data["final_integrity"]["numeric_evidence"], sort_keys=True),
            ]
        ],
    )
    audit = data["concurrency_audit"]
    if audit["applicable"]:
        lines += [
            "Final concurrency metadata audit: "
            + ("passed" if audit["passed"] else "failed")
            + ". The administration source matches the protocol amendment; every "
            "concurrent cell appears exactly once in fixed remaining dispatch order, "
            "and no serial cells precede this v2 run. Each wave requires "
            "exited child processes and a real observed idle-model drain receipt. "
            "Only slot counts/checks and receipt hashes are exported; original slot "
            "payloads and concurrent launch configurations remain private. This "
            "final metadata audit does not query models or repeat historical source scans.",
            "",
        ]
        lines += table(
            ["Wave", "Cells", "Actual size", "Exited", "Real model drain", "Checks passed"],
            [
                [
                    wave["wave_id"],
                    ",".join(wave["cell_ids"]),
                    wave["actual_wave_size"],
                    wave["all_child_processes_exited"],
                    wave["checks"]["real_drain_observation"],
                    wave["passed"],
                ]
                for wave in audit["waves"]
            ],
        )
    if data["recorded_system_problems"]:
        lines += [
            "Recorded cell system problems: "
            + ", ".join(data["recorded_system_problems"])
            + ". Matrix completion alone does not resolve these validity concerns.",
            "",
        ]
    resumes = data["resume_metadata"]
    if resumes["network_batches"]:
        lines += [
            "Administrative resume/interruption records are preserved below. "
            "Resuming an unchanged queue is distinct from rerunning a claimed "
            "task; the concurrency audit separately checks each concurrent cell "
            "appears exactly once. Port-bind interruptions are administrative "
            "events, not new benchmark attempts or model capability outcomes. "
            "Raw exception messages and resume logs remain private.",
            "",
        ]
        lines += table(
            ["Network batch", "Interruption", "Class", "Exception type", "Network restored"],
            [
                [
                    batch["network_batch_id"],
                    batch["interruption_recorded"],
                    batch["interruption_class"],
                    (batch["interruption_receipt"] or {}).get("identity", {}).get("exception_type"),
                    batch["network_restoration_confirmed"],
                ]
                for batch in resumes["network_batches"]
            ],
        )
    if resumes["root_resume_receipts"]:
        lines += table(
            [
                "Resume event",
                "Model-group transition",
                "Class",
                "Completed cells preserved",
                "Unfinished claims",
                "Runtime changed",
                "Semantic retries",
                "Receipt SHA256",
            ],
            [
                [
                    event["event_id"],
                    event["model_group_transition"],
                    event["interruption_class"],
                    event["completed_cells_preserved"],
                    event["unfinished_claims"],
                    event["runtime_changed"],
                    event["semantic_retries"],
                    event["sha256"],
                ]
                for event in resumes["root_resume_receipts"]
            ],
        )
        for event in resumes["root_resume_receipts"]:
            if (
                event["model_group_transition"]
                and event["interruption_class"] == "port_bind_conflict"
                and event["runtime_changed"] is False
                and event["unfinished_claims"] == 0
                and event["semantic_retries"] == 0
                and type(event["completed_cells_preserved"]) is int
            ):
                lines += [
                    "The model-group transition encountered an administrative tokenizer "
                    "port-bind interruption. The unchanged-runtime resume receipt "
                    f"preserves {event['completed_cells_preserved']} completed cells, "
                    "with zero unfinished claims and zero semantic retries. This event "
                    "is not counted as a model capability failure or an additional "
                    "benchmark attempt.",
                    "",
                ]
    return "\n".join(lines)


def main(root, output):
    if output.exists():
        raise FileExistsError("Final export namespace must be new")
    marker = root / "matrix-complete.json"
    integrity = root / "final-integrity.json"
    if not marker.is_file() or not integrity.is_file():
        raise RuntimeError("Final matrix-complete and integrity receipts are required")
    final_integrity = read(integrity)
    if (
        final_integrity.get("matrix_complete") is not True
        or final_integrity.get("executed_cell_records") != 30
        or final_integrity.get("planned_cells") != 30
    ):
        raise RuntimeError("Final integrity does not attest the completed 30-cell matrix")
    freeze = read(root / "execution-freeze.json")
    planned = validate_plan(freeze)
    concurrency = concurrency_metadata(root)
    concurrency_integrity = concurrency_audit(root, planned, concurrency)
    if not concurrency_integrity["passed"]:
        failed = [check for check, passed in concurrency_integrity["checks"].items() if not passed]
        raise RuntimeError("Final concurrency metadata audit failed: " + ",".join(failed))
    paths = list((root / "cells").glob("*/sanitized-result.json"))
    if len(paths) != 30 or {path.parent.name for path in paths} != {
        cell["cell_id"] for cell in planned
    }:
        raise RuntimeError("All and only the 30 frozen sanitized cells are required")
    rows = [
        safe_cell(root, {**cell, "execution_index": index}, concurrency)
        for index, cell in enumerate(planned, 1)
    ]
    grouped = defaultdict(list)
    for row in rows:
        grouped[key(row["cell"])].append(row)
    comparisons, trajectories = paired_comparisons(rows)
    journal_path = root / "journal.jsonl"
    journal = (
        [json.loads(line) for line in journal_path.read_text().splitlines() if line.strip()]
        if journal_path.exists()
        else []
    )
    wall = (
        (
            datetime.fromisoformat(journal[-1]["utc"]) - datetime.fromisoformat(journal[0]["utc"])
        ).total_seconds()
        * 1000
        if len(journal) > 1 and all("utc" in item for item in (journal[0], journal[-1]))
        else None
    )
    data = {
        "version": VERSION,
        "analyzer_source_sha256": sha(Path(__file__)),
        "execution_state": "complete",
        "analyzed_cells": len(rows),
        "execution_conditions": concurrency,
        "shared_resource_concurrency": concurrency["shared_resource_concurrency"],
        "concurrency_audit": concurrency_integrity,
        "resume_metadata": resume_metadata(root),
        "conditions": {name: summarize(grouped[name]) for name in sorted(grouped)},
        "cells": rows,
        "paired_comparisons": comparisons,
        "task_trajectories": trajectories,
        "skill_token_lengths": token_lengths(root),
        "matrix_wall_ms": wall,
        "matrix_marker": receipt_metadata(marker),
        "final_integrity": receipt_metadata(integrity),
        "tc_attestation": receipt_metadata(root / "tc-attestation.json")
        if (root / "tc-attestation.json").exists()
        else None,
        "execution_freeze": {
            "sha256": sha(root / "execution-freeze.json"),
            "base_commit": label(freeze.get("base_commit")),
            "ordered_cells": [
                {
                    field: cell[field]
                    for field in ("cell_id", "candidate", "skill_condition", "task_index")
                    if field in cell
                }
                for cell in planned
            ],
            "source_sha256_anonymous": safe_hash_map(freeze.get("source_sha256")),
            "protected_sha256_anonymous": safe_hash_map(freeze.get("protected_sha256")),
            "skills": {
                condition: {
                    "sha256": item.get("sha256")
                    if isinstance(item.get("sha256"), str) and SHA256.fullmatch(item["sha256"])
                    else None,
                    "utf8_bytes": item.get("utf8_bytes")
                    if type(item.get("utf8_bytes")) is int
                    else None,
                }
                for condition, item in freeze.get("plan", {}).get("skills", {}).items()
                if condition in SKILLS and isinstance(item, dict)
            },
            "numeric_evidence": numeric_tree(freeze),
            "frozen_configuration": configuration_metadata(freeze),
        },
        "recorded_system_problems": sorted(
            {problem for row in rows for problem in row["system_problems"]}
            | {label(problem) for problem in final_integrity.get("system_problems", [])}
        ),
        "schema_denominator": (
            "Original parsed operator/delegation Function Calls reaching strict application "
            "validation; provider parsing failures and Verifier structured-output checks "
            "are separate."
        ),
        "limits": {
            "descriptive_only": True,
            "tasks_per_condition": 3,
            "full_resource_monetary_cost": None,
            "gpu_price": None,
            "missing_usage_is_unknown": True,
            "service_work_is_partial_proxy": True,
            "service_sums_can_overlap_e2e": True,
            "early_failure_saving_is_not_efficiency": True,
            "e2e_is_diagnostic_not_tsr_admission_criterion": concurrency["tsr_is_primary"],
            "overlapping_runner_log_sums_are_not_exclusive_work": True,
            "source_or_history_rescanned_by_analyzer": False,
            "raw_sensitive_evidence_exported": False,
            "new_inference_calls": 0,
        },
    }
    metadata = list(root.glob("*.json")) + list(root.glob("*.jsonl")) + list(root.glob("*.py"))
    metadata += list((root / "private/deployment").rglob("*"))
    metadata += list((root / "administration").glob("*.py"))
    metadata += list((root / "concurrency-waves").glob("*.json"))
    metadata += list((root / "concurrency-configs").glob("*.json"))
    metadata += list((root / "reporting").glob("*.py"))
    metadata += [path for path in root.glob("concurrent-resume-*") if path.is_file()]
    metadata += [
        path
        for directory in root.glob("resume-network-*")
        if directory.is_dir()
        for path in directory.rglob("*")
    ]
    rendered_report = report(data)
    json.dumps(data, allow_nan=False)
    output.mkdir(parents=True, exist_ok=False)
    write(output / "skill-granularity-results.json", data)
    write(
        output / "raw-evidence-hashes.json",
        {
            "root_metadata": evidence_manifest(root, metadata),
            "cells": {row["cell"]["cell_id"]: row["raw_evidence_manifest"] for row in rows},
        },
    )
    write(output / "final-integrity.json", data["final_integrity"])
    write(output / "concurrency-audit.json", concurrency_integrity)
    write(output / "resume-metadata.json", data["resume_metadata"])
    (output / "skill-granularity-report.md").write_text(
        rendered_report, encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {
                "execution_state": "complete",
                "analyzed_cells": len(rows),
                "conditions": len(grouped),
                "new_inference_calls": 0,
            }
        )
    )


def self_test():
    """Three focused offline checks; no experiment outcomes are simulated."""
    import tempfile

    planned = [
        {
            "cell_id": f"{candidate}-{condition}-t{task}",
            "candidate": candidate,
            "skill_condition": condition,
            "task_index": task,
        }
        for candidate in CANDIDATES
        for condition in (SKILLS if candidate != "qwen35-27b" else ("S0", "S3"))
        for task in (1, 2, 3)
    ]
    assert len(validate_plan({"ordered_cells": planned})) == 30
    duplicate = copy.deepcopy(planned)
    duplicate[-1] = copy.deepcopy(duplicate[-2])
    try:
        validate_plan({"ordered_cells": duplicate})
    except RuntimeError:
        pass
    else:
        raise AssertionError("Duplicate plan accepted")
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        tokenizer_fixture = {
            "candidate": "qwen35-4b",
            "tokenizer_model_blob": "sha256-" + "a" * 64,
            "base_instruction_tokens": 10,
            "skills": {
                condition: {
                    "utf8_bytes": index,
                    "standalone_tokens": index,
                    "manager_instruction_tokens": 10 + index,
                    "manager_instruction_increment_tokens": index,
                }
                for index, condition in enumerate(SKILLS)
            },
            "inference_calls": 0,
        }
        write(root / "skill-token-lengths-qwen35-4b.json", tokenizer_fixture)
        exported_tokens = token_lengths(root)["qwen35-4b"]
        assert set(exported_tokens["numeric_evidence"]["skills"]) == set(SKILLS)
        assert exported_tokens["numeric_evidence"]["skills"]["S2"]["standalone_tokens"] == 2
        assert (
            exported_tokens["numeric_evidence"]["skills"]["S3"][
                "manager_instruction_increment_tokens"
            ]
            == 3
        )
        assert exported_tokens["tokenizer_model_blob"] == tokenizer_fixture["tokenizer_model_blob"]
        administration = root / "administration/run_skill_granularity_concurrent_v1.py"
        administration.parent.mkdir(parents=True)
        administration.write_text("pass\n", encoding="utf-8")
        audit_plan = [
            {"cell_id": cell, "candidate": "qwen35-4b"}
            for cell in ("serial-cell", "wave-cell", "wave-cell-2")
        ]
        write(root / "execution-freeze.json", {"ordered_cells": audit_plan})
        write(
            root / "protocol-amendment-001.json",
            {
                "shared_resource_concurrency": 3,
                "serial_completed_cell_ids": ["serial-cell"],
                "concurrent_cell_ids": ["wave-cell", "wave-cell-2"],
                "original_pre_registration_unchanged": True,
                "administration_source_sha256": sha(administration),
                "original_execution_freeze_sha256": sha(root / "execution-freeze.json"),
            },
        )
        receipt = root / "cells/wave-cell/concurrency-receipt.json"
        write(
            receipt,
            {
                "shared_resource_concurrency": 3,
                "concurrency_wave": "wave-001",
                "actual_wave_size": 2,
                "slot": 0,
                "serving_request_parallelism": 1,
                "shared_executor_pool": True,
                "runner_log_intervals_may_overlap": True,
            },
        )
        concurrency = concurrency_metadata(root)
        assert concurrency["shared_resource_concurrency"] == 3
        serial = cell_concurrency(root, {"cell_id": "serial-cell"}, concurrency)
        concurrent = cell_concurrency(root, {"cell_id": "wave-cell"}, concurrency)
        assert serial["shared_resource_concurrency"] == 1
        assert not serial["runner_log_intervals_may_overlap"]
        assert concurrent["shared_resource_concurrency"] == 3
        assert concurrent["actual_wave_size"] == 2
        assert concurrent["serving_request_parallelism"] == 1
        assert concurrent["runner_log_intervals_may_overlap"]
        second_receipt = {**read(receipt), "slot": 1}
        write(root / "cells/wave-cell-2/concurrency-receipt.json", second_receipt)
        write(
            root / "concurrency-waves/wave-001.json",
            {
                "cells": ["wave-cell", "wave-cell-2"],
                "actual_wave_size": 2,
                "maximum_concurrency": 3,
                "system_errors": [],
                "all_child_processes_exited": True,
                "serving_request_parallelism": 1,
            },
        )
        drain = root / "concurrency-waves/wave-001-model-drain.json"
        write(
            drain,
            {
                "all_shared_models_idle": True,
                "real_observation": True,
                "resident_slots": {"node": {"port": [{"is_processing": False}]}},
                "planner_slots": [{"is_processing": False}],
            },
        )
        assert concurrency_audit(root, audit_plan, concurrency)["passed"]
        drain.unlink()
        missing_drain_audit = concurrency_audit(root, audit_plan, concurrency)
        assert not missing_drain_audit["passed"]
        assert not missing_drain_audit["waves"][0]["checks"]["drain_receipt_present"]
        write(
            root / "resume-network-001/batch-stopped.json",
            {
                "exception_type": "OSError",
                "message": "Address already in use PRIVATE_MARKER",
                "semantic_retries": 0,
            },
        )
        for sequence in (1, 2):
            write(
                root / f"resume-network-{sequence:03d}/tc-attestation.json",
                {
                    "original_qdisc": "private qdisc",
                    "restored_qdisc": "private qdisc",
                    "cleanup_error": None,
                },
            )
        write(
            root / "concurrent-resume-002.json",
            {
                "reason": (
                    "transient tokenizer port bind conflict at model-group boundary; "
                    "port now bindable"
                ),
                "completed_cells_preserved": 12,
                "unfinished_claims": 0,
                "runtime_changed": False,
                "semantic_retries": 0,
            },
        )
        resumes = resume_metadata(root)
        assert resumes["network_batch_count"] == 2
        assert resumes["recorded_interruptions"] == 1
        assert resumes["network_batches"][0]["interruption_class"] == "port_bind_conflict"
        assert all(batch["network_restoration_confirmed"] for batch in resumes["network_batches"])
        assert resumes["root_resume_receipts"][0]["numeric_evidence"]["unfinished_claims"] == 0
        assert resumes["root_resume_receipts"][0]["model_group_transition"]
        assert resumes["root_resume_receipts"][0]["completed_cells_preserved"] == 12
        assert resumes["root_resume_receipts"][0]["runtime_changed"] is False
        assert "PRIVATE_MARKER" not in json.dumps(resumes)
        assert "private qdisc" not in json.dumps(resumes)
        null_cell = root / "cells/null-response-check"
        null_response = null_cell / "private/api/check-response.json"
        write(null_response, None)
        write(
            null_cell / "private/api/check-usage.json",
            {
                "recipient": "manager",
                "status": None,
                "error_type": "APITimeoutError",
                "usage": None,
                "latency_ms": 1,
            },
        )
        before_sha = sha(null_response)
        assert legacy_response_error_view(null_response) == {}
        assert read(null_response) is None and sha(null_response) == before_sha
        diagnosed = provider_findings(root, null_cell)
        assert diagnosed["errors"][0]["response_body_shape"] == "null"
        assert diagnosed["errors"][0]["category"] == "provider_timeout_error"
        assert diagnosed["errors"][0]["usage_missing"]
        try:
            main(root, root / "export")
        except RuntimeError:
            assert not (root / "export").exists()
        else:
            raise AssertionError("Incomplete matrix published")

    assert (
        provider_category("XML syntax error on line 8: element <function> closed by </parameter>")
        == "provider_xml_tool_call_parse_error"
    )
    for message in (
        "invalid character '}' after object key",
        "invalid character '\\n' in string literal",
    ):
        assert provider_category(message) == "provider_json_syntax_error"
    assert provider_category("out of memory") == "provider_oom_error"
    assert provider_category("request timed out") == "provider_timeout_error"
    assert provider_category("internal server error") == "provider_error_other"

    amplification = verifier_amplification(
        {
            "successful": 0,
            "roles": {
                "manager": {"turns": 2, "requests": 2, "input_tokens": None, "output_tokens": None},
                "verifier": {
                    "turns": 3,
                    "requests": 3,
                    "input_tokens": 6,
                    "output_tokens": 2,
                    "cloud_api_cost": {"complete_usd_total": None, "known_usd_subtotal": "0.1"},
                },
            },
        }
    )
    assert amplification["verifier_to_manager_turn_ratio"] == 1.5
    assert amplification["verifier_to_manager_input_token_ratio"] is None
    assert amplification["verifier_turns_per_success"] is None
    assert amplification["verifier_complete_usd_per_success"] is None
    assert difference({"unknown": None, "known": 2}, {"unknown": 4, "known": 3}) == {"known": 1}
    print(json.dumps({"focused_checks": 3, "status": "passed", "new_inference_calls": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    arguments = parser.parse_args()
    if arguments.self_test:
        self_test()
    elif arguments.root is None or arguments.output is None:
        parser.error("--root and --output are required for final analysis")
    else:
        main(arguments.root, arguments.output)
