"""Offline content-free aggregation for the bounded multiscale Planner evaluation."""

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

from analyze_lightweight_planner_pilot_v1 import aggregate, enrich, read, total, write

SAFE_LABEL = re.compile(r"[A-Za-z0-9_.:+-]{1,120}\Z")
SHA256 = re.compile(r"(?:sha256[:-])?[a-f0-9]{64}\Z")
DROP_KEYS = {
    "message",
    "messages",
    "prompt",
    "prompts",
    "content",
    "text",
    "arguments",
    "response",
    "request",
    "modelfile",
    "system",
    "environment",
    "command",
    "argv",
    "url",
    "ollama_url",
    "runner_url",
    "path",
    "root",
    "remote_root",
    "headers",
    "api_key",
    "key",
    "authorization",
    "show",
}


def label(value, default="unknown"):
    return value if isinstance(value, str) and SAFE_LABEL.fullmatch(value) else default


def numeric_tree(value):
    """Keep metrics and their safe field names, never arbitrary string values."""
    if value is None or type(value) in (bool, int, float):
        return value
    if isinstance(value, dict):
        return {
            key: numeric_tree(item)
            for key, item in value.items()
            if isinstance(key, str)
            and SAFE_LABEL.fullmatch(key)
            and key.lower() not in DROP_KEYS
            and not isinstance(item, str)
        }
    if isinstance(value, list):
        return [numeric_tree(item) for item in value if not isinstance(item, str)]
    return None


def safe_metadata(value):
    """Explicit identity/protocol fields only; endpoint addresses remain private."""
    fields = (
        "candidate",
        "model",
        "tag",
        "digest",
        "manifest_sha256",
        "model_blob",
        "template_sha256",
        "renderer",
        "parser",
        "context_window",
        "reserved_output_tokens",
        "context_length",
        "num_ctx",
        "max_tokens",
        "temperature",
        "top_p",
        "reasoning_effort",
        "thinking",
        "disable_thinking",
        "phase",
        "version",
        "quantization",
        "quantization_level",
        "parameter_size",
        "family",
        "status",
        "type",
        "code",
        "exception_type",
        "admitted",
        "safe",
        "ready",
        "manager_node",
    )
    result = {}
    for key in fields:
        item = value.get(key)
        if item is None or type(item) in (bool, int, float):
            if key in value:
                result[key] = item
        elif isinstance(item, str) and (SAFE_LABEL.fullmatch(item) or SHA256.fullmatch(item)):
            result[key] = item
    return result


def evidence_manifest(root, paths):
    rows = []
    for path in sorted(set(paths)):
        if not path.is_file():
            continue
        relative = str(path.relative_to(root)).replace("\\", "/")
        rows.append(
            {
                "file_id": hashlib.sha256(relative.encode()).hexdigest(),
                "kind": (
                    "trace"
                    if path.name == "trace.jsonl"
                    else "usage"
                    if path.name.endswith("-usage.json")
                    else "raw_response"
                    if path.name.endswith("-response.json")
                    else "raw_request"
                    if path.name.endswith("-request.json")
                    else "metadata"
                ),
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return rows


def parse_runner_work(text):
    units = Counter()
    for kind, count, unit in re.findall(
        r"(prompt eval|eval) time\s*=\s*[\d.]+\s*ms\s*/\s*(\d+)\s*(tokens|runs)", text
    ):
        units[("prompt_eval_" if kind == "prompt eval" else "decode_eval_") + unit] += int(count)
    return {
        "runner_task_starts": len(re.findall(r"processing task, is_child = 0", text)),
        "reported_total_time_ms_sum": sum(
            float(value) for value in re.findall(r"total time\s*=\s*([\d.]+)\s*ms", text)
        ),
        "reported_evaluation_units": dict(units),
    }


def independent_planner_work(cell):
    unobserved = cell / "private/planner-service-unobserved.json"
    explicitly_unknown = unobserved.exists() and read(unobserved).get("observed") is False
    paths = sorted((cell / "private").glob("*planner*log*interval*.json"))
    texts = []
    for path in paths:
        value = read(path)
        if isinstance(value.get("text"), str):
            texts.append(value["text"])
        elif isinstance(value.get("intervals"), dict):
            texts.extend(
                interval["text"]
                for interval in value["intervals"].values()
                if isinstance(interval, dict) and isinstance(interval.get("text"), str)
            )
    if explicitly_unknown or not texts:
        return {
            "observed": False,
            "runner_task_starts": None,
            "reported_total_time_ms_sum": None,
            "reported_evaluation_units": {},
        }
    return {"observed": True, **parse_runner_work("\n".join(texts))}


def resource_summary(samples):
    """Summarize sampled headroom; absent samples never imply zero usage."""
    gpu = defaultdict(list)
    available, totals = [], []
    for sample in samples:
        for value in sample.get("gpu", []):
            if type(value.get("index")) is int and type(value.get("free_mib")) in (int, float):
                gpu[str(value["index"])].append(value["free_mib"])
        memory = sample.get("a28_memory_kib", {})
        if type(memory.get("MemAvailable")) in (int, float):
            available.append(memory["MemAvailable"])
        if type(memory.get("MemTotal")) in (int, float):
            totals.append(memory["MemTotal"])
    return {
        "sample_count": len(samples),
        "gpu_free_mib_min_by_index": {key: min(values) for key, values in sorted(gpu.items())},
        "gpu_free_mib_max_by_index": {key: max(values) for key, values in sorted(gpu.items())},
        "A28_available_ram_kib_min": min(available) if available else None,
        "A28_available_ram_kib_max": max(available) if available else None,
        "A28_total_ram_kib_min": min(totals) if totals else None,
        "A28_total_ram_kib_max": max(totals) if totals else None,
        "sampled_headroom_is_continuous_peak_measurement": False,
    }


def cell_execution_conditions(cell, original):
    path = cell / "private/continuation-resources.json"
    resource = read(path) if path.exists() else {}
    candidate, _ = infer_identity(original)
    if candidate == "B0":
        manager_node, cohort = "cloud", "cloud-manager"
    elif candidate == "qwen35-27b":
        manager_node, cohort = "strong-4090-gpu0", "existing-resident-gpu0"
    elif resource.get("manager_node") == "A28":
        manager_node, cohort = "A28", "continued-a28"
    elif candidate == "qwen35-4b" and cell.name in {
        "qwen35-4b-t1-plain",
        "qwen35-4b-t3-plain",
        "qwen35-4b-t5-plain",
    }:
        manager_node, cohort = "strong-4090-gpu1", "original-gpu1"
    else:
        manager_node, cohort = "unknown", "unverified-placement"
    samples = resource.get("samples", [])
    result = {
        "manager_node": manager_node,
        "placement_cohort": cohort,
        "continuation_resource_receipt_present": path.exists(),
        "external_gpu_contention_authorized": resource.get(
            "external_gpu_contention_authorized", False
        ),
        "resource_failure": label(resource["resource_failure"])
        if resource.get("resource_failure") is not None
        else None,
        "resources": resource_summary(samples),
    }
    # Export numeric samples, not private addresses or arbitrary metadata strings.
    result["resource_samples"] = [
        {
            "sample_index": index,
            "gpu": numeric_tree(sample.get("gpu", [])),
            "a28_memory_kib": numeric_tree(sample.get("a28_memory_kib", {})),
        }
        for index, sample in enumerate(samples)
    ]
    return result


def continuation_evidence(root, rows, freeze, journal):
    amendments = sorted(root.glob("continuation-freeze-*.json"))
    latest = read(amendments[-1]) if amendments else {}
    skills_path = root / "skills-selection.json"
    skills = read(skills_path).get("candidates") if skills_path.exists() else None
    if not isinstance(skills, list):
        skills = next(
            (
                value["skills_candidates"]
                for path in reversed(amendments)
                if isinstance((value := read(path)).get("skills_candidates"), list)
            ),
            freeze.get("plan", {}).get("skills_candidates", []),
        )
    skills = [label(value) for value in skills]
    # Resource-only continuation amendments may follow real benchmark outcomes.
    # Selection timing belongs to the first declaration of the current list,
    # while resource limits belong to the latest amendment.
    skills_freeze_path = next(
        (path for path in amendments if read(path).get("skills_candidates") == skills), None
    )
    skills_freeze = read(skills_freeze_path) if skills_freeze_path is not None else {}

    def freeze_utc(value):
        timestamp = value.get("frozen_at")
        return datetime.fromisoformat(timestamp).isoformat() if timestamp else None

    first_9b = next(
        (
            item.get("utc")
            for item in journal
            if item.get("event") == "cell_started"
            and isinstance(item.get("cell"), dict)
            and item["cell"].get("candidate") == "qwen35-9b"
        ),
        None,
    )
    changed_before = None
    if skills_freeze.get("frozen_at") and first_9b:
        changed_before = datetime.fromisoformat(
            skills_freeze["frozen_at"]
        ) <= datetime.fromisoformat(first_9b)
    cohorts = {
        row["execution_conditions"]["manager_node"]
        for row in rows
        if row["cell"]["candidate"] == "qwen35-4b"
    }
    conditions = {
        "continuation_applied": bool(amendments),
        "effective_continuation_freeze": label(amendments[-1].stem) if amendments else None,
        "effective_continuation_freeze_sha256": (
            hashlib.sha256(amendments[-1].read_bytes()).hexdigest() if amendments else None
        ),
        "latest_resource_freeze": label(amendments[-1].stem) if amendments else None,
        "latest_resource_freeze_sha256": (
            hashlib.sha256(amendments[-1].read_bytes()).hexdigest() if amendments else None
        ),
        "latest_resource_freeze_utc": freeze_utc(latest),
        "initial_skills_freeze": label(skills_freeze_path.stem)
        if skills_freeze_path is not None
        else None,
        "initial_skills_freeze_sha256": hashlib.sha256(skills_freeze_path.read_bytes()).hexdigest()
        if skills_freeze_path is not None
        else None,
        "initial_skills_freeze_utc": freeze_utc(skills_freeze),
        "skills_timing_uses_initial_declaration_not_latest_resource_amendment": True,
        "effective_resource_boundaries": {
            "controller_gpu_free_minimum_mib": latest.get("gpu_free_minimum_mib"),
            "A28_available_ram_minimum_gib": latest.get("A28_available_ram_minimum_gib"),
            "resource_sample_interval_seconds": latest.get("resource_sample_interval_seconds"),
        },
        "preserved_continuation_stop_receipts": len(list(root.glob("continuation-stopped-*.json"))),
        "skills_candidates": skills,
        "skills_changed_before_first_9b_benchmark": changed_before,
        "historical_stop_preserved": (root / "matrix-stopped.json").exists(),
        "matrix_completed_after_recorded_stop": (root / "matrix-stopped.json").exists()
        and (root / "matrix-complete.json").exists(),
        "mixed_4b_manager_placement": len(cohorts - {"unknown"}) > 1,
        "cohort_stratification_required": len(cohorts - {"unknown"}) > 1,
    }
    metadata_paths = [
        *amendments,
        root / "reporting-amendment.json",
        root / "a28-service.json",
        root / "a28-service-preparation.json",
        root / "skills-selection.json",
        root / "matrix-stopped.json",
        root / "matrix-complete.json",
        root / "placement-clarification.json",
        *sorted(root.glob("continuation-stopped-*.json")),
    ]
    metadata = []
    for path in metadata_paths:
        if not path.is_file():
            continue
        value = read(path)
        item = {
            "kind": label(path.stem),
            "receipt_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "numeric_evidence": numeric_tree(value),
        }
        for key in (
            "source_sha256",
            "helper_source_sha256",
            "controller_source_sha256",
            "original_execution_freeze_sha256",
            "original_stop_sha256",
            "original_raw_result_sha256",
            "sanitized_result_sha256",
        ):
            digest = value.get(key)
            if isinstance(digest, str) and SHA256.fullmatch(digest):
                item[key] = digest
        metadata.append(item)
    cells = [
        {
            "cell_id": row["cell"]["cell_id"],
            **row["execution_conditions"],
            "external_gpu_contention": row["external_gpu_contention"],
            "reporting_recovery": row["reporting_recovery"],
            "independent_planner_runner_work": row["independent_planner_runner_work"],
        }
        for row in rows
    ]
    all_samples = [sample for cell in cells for sample in cell["resource_samples"]]
    by_cohort = defaultdict(list)
    for cell in cells:
        by_cohort[cell["placement_cohort"]].append(cell)
    return {
        "schema_version": 1,
        "execution_conditions": conditions,
        "cells": cells,
        "summary": {
            **resource_summary(all_samples),
            "placement_cells": dict(Counter(cell["manager_node"] for cell in cells)),
            "cells_with_resource_samples": sum(
                cell["resources"]["sample_count"] > 0 for cell in cells
            ),
            "cells_without_resource_samples": sum(
                cell["resources"]["sample_count"] == 0 for cell in cells
            ),
            "independent_planner_work_unobserved_cells": sum(
                not cell["independent_planner_runner_work"]["observed"] for cell in cells
            ),
            "external_process_set_changed_cells": sum(
                cell["external_gpu_contention"].get("process_set_changed_during_cell") is True
                for cell in cells
            ),
            "reporting_recovered_cells": sum(bool(cell["reporting_recovery"]) for cell in cells),
            "by_placement_cohort": {
                key: {
                    "cells": len(values),
                    **resource_summary(
                        [sample for value in values for sample in value["resource_samples"]]
                    ),
                }
                for key, values in sorted(by_cohort.items())
            },
        },
        "amendments": metadata,
        "evidence_manifest": evidence_manifest(
            root,
            [
                *metadata_paths,
                *root.glob("reporting/*.py"),
                *(root / "cells").glob("*/private/continuation-resources.json"),
                *(root / "cells").glob("*/private/planner-service-unobserved.json"),
            ],
        ),
        "limits": {
            "timestamps_are_not_continuous_resource_telemetry": True,
            "missing_resource_samples_are_unknown": True,
            "foreign_processes_not_modified": latest.get("external_processes_modified") is False
            if amendments
            else None,
            "mixed_hardware_quality_results_are_descriptive": True,
        },
    }


def infer_identity(row):
    cell = row["cell"]
    group = cell.get("group")
    candidate = cell.get("candidate")
    if not candidate:
        candidate = "B0" if group == "B0" else "historical-qwen3vl-8b"
    return label(candidate), bool(cell.get("skills", group == "B2"))


def condition_key(row):
    candidate, skills = infer_identity(row)
    return candidate + ("__skills" if skills else "__no_skills")


def safe_row(root, original):
    row = enrich(root, copy.deepcopy(original))
    cell = root / "cells" / row["cell"]["cell_id"]
    candidate, skills = infer_identity(row)
    row["cell"]["candidate"] = candidate
    row["cell"]["skills"] = skills
    row["cell"].setdefault("stage", "historical")
    row["independent_planner_runner_work"] = independent_planner_work(cell)
    row["resident_runner_work"]["scope"] = (
        "existing five resident Executor runners; includes Planner only when that "
        "Planner reuses a resident endpoint; partial service proxy, not GPU compute"
    )
    # Unknown cached usage must remain unknown; the known subtotal is a lower bound.
    receipts = [read(path) for path in (cell / "private/api").rglob("*-usage.json")]
    for role, metrics in row["roles"].items():
        selected = [
            (receipt.get("usage") or {}) for receipt in receipts if receipt.get("recipient") == role
        ]
        metrics["unknown_cached_usage_requests"] = sum(
            type(usage.get("prompt_tokens_details", {}).get("cached_tokens")) is not int
            for usage in selected
        )
    result = {
        "cell": {
            field: row["cell"][field]
            for field in (
                "cell_id",
                "candidate",
                "stage",
                "skills",
                "group",
                "task_index",
                "family",
                "position",
            )
            if field in row["cell"]
        },
        "completed": bool(row["completed"]),
        "successful": bool(row["successful"]),
        "original_evaluation": numeric_tree(row.get("original_evaluation")),
        "failure": safe_metadata(row.get("failure") or {}) or None,
        "outcome_type": label(row["outcome_type"]),
        "failure_counts": numeric_tree(row["failure_counts"]),
        "provider_error_types": numeric_tree(row["provider_error_types"]),
        "schema_attempts": row["schema_attempts"],
        "schema_valid": row["schema_valid"],
        "schema_failures": row["schema_failures"],
        "schema_detail": numeric_tree(row["schema_detail"]),
        "roles": numeric_tree(row["roles"]),
        "cost_accounting": {
            scope: {
                "roles": {
                    role: {
                        field: value
                        for field, value in metrics.items()
                        if field
                        in (
                            "calls",
                            "known_usd_calls",
                            "unknown_usd_calls",
                            "known_usd_subtotal",
                            "complete_usd_total",
                        )
                    }
                    for role, metrics in meter.get("roles", {}).items()
                    if role in ("all", "manager", "specialist", "verifier")
                }
            }
            for scope, meter in row["cost_accounting"].items()
            if scope in ("cloud", "local")
        },
        "physical": numeric_tree(row["physical"]),
        "timing": numeric_tree(row["timing"]),
        "telemetry": numeric_tree(row.get("telemetry")),
        "task_e2e_ms": row["task_e2e_ms"],
        "workflow": row["workflow"],
        "workflow_detail": row["workflow_detail"],
        "created_specialists": row["created_specialists"],
        "budget": numeric_tree(row["budget"]),
        "context_rejections": row["context_rejections"],
        "context_detail": numeric_tree(row["context_detail"]),
        "cleanup": numeric_tree(row["cleanup"]),
        "system_problems": [label(value) for value in row["system_problems"]],
        "resident_runner_work": row["resident_runner_work"],
        "independent_planner_runner_work": row["independent_planner_runner_work"],
        "api_payload_storage_bytes": numeric_tree(row["api_payload_storage_bytes"]),
        "full_resource_monetary_cost": None,
    }
    result["execution_conditions"] = cell_execution_conditions(cell, original)
    result["external_gpu_contention"] = numeric_tree(original.get("external_gpu_contention", {}))
    result["reporting_recovery"] = numeric_tree(original.get("reporting_recovery", {}))
    audits = [read(path) for path in (cell / "private/residency-log-intervals").glob("*.json")]
    if any("external_gpu_process_set_changed" in value for value in audits):
        result["external_gpu_contention"]["process_set_changed_during_cell"] = any(
            value.get("external_gpu_process_set_changed") is True for value in audits
        )
        result["external_gpu_contention"]["user_authorized_contended_continuation"] = all(
            value.get("external_contention_authorized_for_continuation") is True for value in audits
        )
    result["raw_evidence_manifest"] = evidence_manifest(root, cell.rglob("*"))
    return result


def summarize(rows):
    result = aggregate(rows)
    result["original_scores"] = [
        (row.get("original_evaluation") or {}).get("score") for row in rows
    ]
    evaluated = [score for score in result["original_scores"] if score is not None]
    result["evaluated_tasks"] = len(evaluated)
    result["mean_original_score_among_evaluated"] = (
        sum(evaluated) / len(evaluated) if evaluated else None
    )
    result["evaluation_missing_tasks"] = len(rows) - len(evaluated)
    result["provider_error_types"] = dict(
        sum((Counter(row["provider_error_types"]) for row in rows), Counter())
    )
    result["schema_attempts"] = sum(row["schema_attempts"] for row in rows)
    result["schema_valid"] = sum(row["schema_valid"] for row in rows)
    result["raw_schema_validity"] = (
        result["schema_valid"] / result["schema_attempts"] if result["schema_attempts"] else None
    )
    result["schema_recovery"] = {
        field: sum(row["schema_detail"][field] for row in rows)
        for field in ("owners_with_invalid_call", "owners_with_later_valid_call")
    }
    result["independent_planner_runner_work"] = {
        "observed_cells": sum(row["independent_planner_runner_work"]["observed"] for row in rows),
        "unobserved_cells": sum(
            not row["independent_planner_runner_work"]["observed"] for row in rows
        ),
        "known_runner_task_starts_subtotal": sum(
            row["independent_planner_runner_work"]["runner_task_starts"] or 0 for row in rows
        ),
        "known_reported_total_time_ms_subtotal": sum(
            row["independent_planner_runner_work"]["reported_total_time_ms_sum"] or 0
            for row in rows
        ),
        "complete_reported_total_time_ms": total(
            row["independent_planner_runner_work"]["reported_total_time_ms_sum"] for row in rows
        ),
    }
    result["workflow"] = {
        field: sum(row["workflow_detail"][field] for row in rows)
        for field in (
            "node_count",
            "edge_count",
            "repeated_identical_selected_calls",
            "specialist_invocations",
        )
    }
    result["workflow"]["operators"] = dict(
        sum((Counter(row["workflow_detail"]["operators"]) for row in rows), Counter())
    )
    for role, metrics in result["roles"].items():
        metrics["unknown_cached_usage_requests"] = sum(
            row["roles"][role]["unknown_cached_usage_requests"] for row in rows
        )
    result["unmeasured_failed_model_service_work"] = any(
        row["physical"].get("unmeasured_failed_model_service_work") for row in rows
    )
    result["manager_placement_cells"] = dict(
        Counter(row["execution_conditions"]["manager_node"] for row in rows)
    )
    result["mixed_manager_placement"] = len(result["manager_placement_cells"]) > 1
    result["external_contention_authorized_cells"] = sum(
        row["execution_conditions"].get("external_gpu_contention_authorized") is True
        or row["external_gpu_contention"].get("user_authorized_contended_continuation") is True
        for row in rows
    )
    result["reporting_recovered_cells"] = sum(bool(row["reporting_recovery"]) for row in rows)
    return result


def delta(left, right):
    """Return right minus left; incomplete paired resource totals stay unknown."""
    result = {
        key: right[key] - left[key]
        if left.get(key) is not None and right.get(key) is not None
        else None
        for key in (
            "completed",
            "successful",
            "schema_failures",
            "task_e2e_ms",
            "controller_execution_wall_ms",
            "runner_task_starts",
            "runner_reported_total_time_ms",
        )
    }
    result["roles"] = {
        role: {
            key: right["roles"][role][key] - left["roles"][role][key]
            if left["roles"][role].get(key) is not None
            and right["roles"][role].get(key) is not None
            else None
            for key in (
                "requests",
                "turns",
                "input_tokens",
                "output_tokens",
                "cached_input_tokens",
                "provider_latency_ms",
                "known_input_tokens_subtotal",
                "known_output_tokens_subtotal",
                "unknown_token_usage_requests",
            )
        }
        for role in ("manager", "specialist", "verifier")
    }
    result["physical"] = {
        key: right["physical"][key] - left["physical"][key]
        if left["physical"].get(key) is not None and right["physical"].get(key) is not None
        else None
        for key in left["physical"]
    }
    result["cloud_api_known_usd_subtotal"] = str(
        Decimal(right["cloud_api_cost"]["known_usd_subtotal"])
        - Decimal(left["cloud_api_cost"]["known_usd_subtotal"])
    )
    result["full_resource_monetary_cost"] = None
    return result


def comparisons(rows):
    conditions = defaultdict(dict)
    for row in rows:
        condition = condition_key(row)
        task = row["cell"]["task_index"]
        if task in conditions[condition]:
            raise RuntimeError("Duplicate task attempt in a candidate/Skills condition")
        conditions[condition][task] = row
    result = []
    baseline = "B0__no_skills"
    for condition in sorted(conditions):
        candidate = condition.rsplit("__", 1)[0]
        reference = candidate + "__no_skills" if condition.endswith("__skills") else baseline
        if reference == condition or reference not in conditions:
            continue
        tasks = sorted(set(conditions[condition]) & set(conditions[reference]))
        if not tasks:
            continue
        left_rows = [conditions[reference][task] for task in tasks]
        right_rows = [conditions[condition][task] for task in tasks]
        result.append(
            {
                "reference": reference,
                "comparison": condition,
                "paired_task_indices": tasks,
                "paired_tasks": len(tasks),
                "descriptive_only": True,
                "delta_comparison_minus_reference": delta(
                    summarize(left_rows), summarize(right_rows)
                ),
                "task_workflows": [
                    {
                        "task_index": task,
                        "reference_cell": conditions[reference][task]["cell"]["cell_id"],
                        "comparison_cell": conditions[condition][task]["cell"]["cell_id"],
                        "reference_outcome": conditions[reference][task]["outcome_type"],
                        "comparison_outcome": conditions[condition][task]["outcome_type"],
                        "reference_workflow": conditions[reference][task]["workflow"],
                        "comparison_workflow": conditions[condition][task]["workflow"],
                    }
                    for task in tasks
                ],
            }
        )
    return result


def safe_receipt(path):
    value = read(path)
    return {
        "identity": safe_metadata(value),
        "numeric_evidence": numeric_tree(value),
        "scenario_statuses": {
            label(key): label(item)
            for key, item in value.items()
            if key not in DROP_KEYS
            and isinstance(item, str)
            and SAFE_LABEL.fullmatch(key)
            and SAFE_LABEL.fullmatch(item)
        },
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def model_metadata(root):
    result = {}
    for path in sorted((root / "candidate-contexts").glob("*.json")):
        result[label(path.stem)] = safe_metadata(read(path))
    for path in sorted((root / "compatibility").glob("*/receipt.json")):
        result.setdefault(label(path.parent.name), safe_metadata(read(path).get("context", {})))

    freeze_path = root / "execution-freeze.json"
    freeze = read(freeze_path) if freeze_path.exists() else {}
    plan = freeze.get("plan", {})
    sampling = {
        key: plan[key]
        for key in (
            "manager_max_tokens",
            "manager_temperature",
            "manager_top_p",
            "qwen_reasoning_effort",
            "context_window",
        )
        if key in plan
        and (
            type(plan[key]) in (bool, int, float)
            or isinstance(plan[key], str)
            and SAFE_LABEL.fullmatch(plan[key])
        )
    }
    for context in result.values():
        context["sampling"] = dict(sampling)
        context["thinking"] = False if context.get("disable_thinking") is True else None

    def architecture(show):
        strings = {
            "general.architecture",
            "general.name",
            "general.basename",
            "general.version",
            "general.size_label",
            "general.type",
            "general.license",
            "general.base_model.0.name",
            "general.base_model.0.organization",
        }
        return {
            key: value
            for key, value in show.get("model_info", {}).items()
            if SAFE_LABEL.fullmatch(key)
            and (
                value is None
                or type(value) in (bool, int, float)
                or key in strings
                and isinstance(value, str)
                and re.fullmatch(r"[A-Za-z0-9_. +()-]{1,120}", value)
            )
        }

    deployment = []
    for path in sorted((root / "private/deployment").glob("*.json")):
        value = read(path)
        context = safe_metadata(value.get("context", {}))
        context["thinking"] = False if context.get("disable_thinking") is True else None
        context["sampling"] = dict(sampling)
        candidate = label(value.get("candidate"))
        deployment.append(
            {
                "candidate": candidate,
                "phase": label(value.get("phase")),
                "manager_node": (
                    "A28"
                    if value.get("manager_node") == "A28"
                    else "strong-4090-gpu0"
                    if candidate == "qwen35-27b"
                    else "strong-4090-gpu1"
                ),
                "a28_memory_kib": numeric_tree(value.get("a28_memory_kib")),
                "same_manager_weights_after_relocation": value.get(
                    "same_manager_weights_after_relocation"
                ),
                "elapsed_ms": value.get("elapsed_ms"),
                "gpu_memory_snapshots": [
                    {key: gpu.get(key) for key in ("index", "used_mib", "free_mib")}
                    for gpu in value.get("gpu", [])
                ],
                "resident_size_vram_bytes": value.get("resident_size_vram"),
                "context": context,
                "details": safe_metadata(value.get("show", {}).get("details", {})),
                "architecture_metadata": architecture(value.get("show", {})),
                "executor_runners_unchanged": value.get("executor_runners_unchanged"),
                "receipt_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "gpu_busy_seconds": None,
                "peak_gpu_memory_mib": None,
            }
        )
        result.setdefault(candidate, context)
    downloads = {}
    for path in sorted(root.glob("*-download.json")):
        value = read(path)
        show = value.get("show", {})
        downloads[label(path.name.removesuffix("-download.json"))] = {
            **safe_metadata(value),
            "elapsed_seconds": value.get("elapsed_seconds"),
            "backend": safe_metadata(value.get("version", {})),
            "details": safe_metadata(show.get("details", {})),
            "architecture_metadata": architecture(show),
            "layers": [
                {key: layer[key] for key in ("digest", "size", "mediaType") if key in layer}
                for layer in value.get("layers", [])
            ],
            "template_sha256": hashlib.sha256(show.get("template", "").encode()).hexdigest(),
            "renderer_parser": [
                line
                for line in show.get("modelfile", "").splitlines()
                if re.fullmatch(r"(RENDERER|PARSER) [A-Za-z0-9_.:+-]+", line)
            ],
            "receipt_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    errors = {}
    for path in sorted(root.glob("*-download-error.json")):
        value = read(path)
        errors[label(path.name.removesuffix("-download-error.json"))] = {
            **safe_metadata(value),
            "elapsed_seconds": value.get("elapsed_seconds"),
            "receipt_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    correction_path = root / "model-provenance-correction.json"
    correction = read(correction_path) if correction_path.exists() else None

    def correction_metadata(value, key=""):
        if isinstance(value, dict):
            return {
                field: correction_metadata(item, field)
                for field, item in value.items()
                if isinstance(field, str)
                and SAFE_LABEL.fullmatch(field)
                and field.lower() not in DROP_KEYS
            }
        if isinstance(value, list):
            return [correction_metadata(item, key) for item in value]
        if value is None or type(value) in (bool, int, float):
            return value
        if isinstance(value, str):
            if SAFE_LABEL.fullmatch(value) or SHA256.fullmatch(value):
                return value
            if value.startswith(
                (
                    "https://ollama.com/library/",
                    "https://registry.ollama.ai/v2/library/",
                )
            ) and not any(character in value for character in ("\n", "\r", " ", "@", "?")):
                return value
            if key in {"actual_family", "actual_model", "model_name", "display_label"} and (
                re.fullmatch(r"[A-Za-z0-9_. +()-]{1,120}", value)
            ):
                return value
        return None

    resolved_27b = bool(
        correction
        and correction.get("actual_checkpoint_family") == "Qwen3.8-27B"
        and correction.get("official_registry_match", {}).get(
            "model_matches_resident_manifest_descriptor"
        )
        is True
        and correction.get("official_registry_match", {}).get(
            "projector_matches_resident_manifest_descriptor"
        )
        is True
    )
    safe_correction = correction_metadata(correction)
    if isinstance(safe_correction, dict):
        safe_correction["execution_candidate_id"] = label(
            str(correction.get("nominal_candidate_key_unchanged", "")).replace("_", "-")
        )
    provenance = {}
    for candidate in result:
        historical_27b = candidate == "qwen35-27b"
        provenance[candidate] = {
            "nominal_candidate_id": candidate,
            "provenance_unknown": not resolved_27b
            if historical_27b
            else candidate not in downloads,
            "official_registry_download_receipt_present": candidate in downloads,
            "correction_receipt_present": historical_27b and correction is not None,
            "actual_checkpoint_family": (
                correction.get("actual_checkpoint_family")
                if historical_27b and resolved_27b
                else None
            ),
        }
    return {
        "contexts": result,
        "downloads": downloads,
        "download_errors": errors,
        "deployment": deployment,
        "deployment_memory_is_snapshot_not_peak": True,
        "sampling_from_frozen_plan": sampling,
        "provenance": provenance,
        "provenance_corrections": safe_correction,
        "provenance_correction_sha256": (
            hashlib.sha256(correction_path.read_bytes()).hexdigest()
            if correction_path.exists()
            else None
        ),
    }


def integrity(root, rows):
    freeze_path = root / "execution-freeze.json"
    freeze = read(freeze_path) if freeze_path.exists() else {}
    source_map = freeze.get("source_sha256", {})
    protected_map = freeze.get("protected_sha256", {})

    def matches(path, expected):
        return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected

    return {
        "source_unchanged": all(
            matches(root / "app" / path, value) for path, value in source_map.items()
        )
        if source_map
        else None,
        "protected_history_and_skills_unchanged": all(
            matches(Path(path), value) for path, value in protected_map.items()
        )
        if protected_map
        else None,
        "all_executed_workers_drained_and_exited": all(
            row["cleanup"].get("drained") and row["cleanup"].get("verified_exited") for row in rows
        )
        if rows
        else None,
        "system_problems": sorted({value for row in rows for value in row["system_problems"]}),
        "semantic_retries": 0,
        "private_raw_evidence_exported": False,
        "source_files_checked": len(source_map),
        "protected_files_checked": len(protected_map),
    }


def main(root, output):
    if output.exists():
        raise FileExistsError("Output namespace must be new; previous exports are immutable")
    if not root.is_dir():
        raise FileNotFoundError("Experiment namespace does not exist")
    freeze_path = root / "execution-freeze.json"
    freeze = read(freeze_path) if freeze_path.exists() else {}
    order = {cell["cell_id"]: index for index, cell in enumerate(freeze.get("ordered_cells", []))}
    paths = sorted(
        (root / "cells").glob("*/sanitized-result.json"),
        key=lambda path: (order.get(path.parent.name, 10**9), path.parent.name),
    )
    rows, errors = [], []
    for path in paths:
        try:
            rows.append(safe_row(root, read(path)))
        except Exception as exc:
            errors.append(
                {"cell_id": label(path.parent.name), "exception_type": type(exc).__name__}
            )
    conditions = defaultdict(list)
    stages = defaultdict(list)
    for row in rows:
        conditions[condition_key(row)].append(row)
        stages[label(row["cell"]["stage"])].append(row)
    journal_path = root / "journal.jsonl"
    journal = (
        [json.loads(line) for line in journal_path.read_text().splitlines()]
        if journal_path.exists()
        else []
    )
    wall_ms = None
    if len(journal) > 1 and all("utc" in entry for entry in (journal[0], journal[-1])):
        wall_ms = (
            datetime.fromisoformat(journal[-1]["utc"]) - datetime.fromisoformat(journal[0]["utc"])
        ).total_seconds() * 1000
    marker = root / "matrix-complete.json"
    stopped_markers = sorted(root.glob("*stopp*.json"))
    compatibility = {
        label(path.parent.name): safe_receipt(path)
        for path in sorted((root / "compatibility").glob("*/receipt.json"))
    }
    state = "complete" if marker.exists() and not errors else "partial_or_stopped"
    continuation = continuation_evidence(root, rows, freeze, journal)
    data = {
        "version": "multiscale-planner-results-v1",
        "base_commit": label(freeze.get("base_commit"), "70a75ae"),
        "execution_state": state,
        "execution_conditions": continuation["execution_conditions"],
        "continuation_resources": continuation,
        "matrix_complete_marker_present": marker.exists(),
        "matrix_marker": safe_receipt(marker) if marker.exists() else None,
        "stop_receipts": [safe_receipt(path) for path in stopped_markers],
        "executed_cell_files": len(paths),
        "analyzed_cells": len(rows),
        "analysis_errors": errors,
        "matrix_wall_ms": wall_ms,
        "conditions": {key: summarize(value) for key, value in sorted(conditions.items())},
        "stages": {
            stage: {
                key: summarize([row for row in stage_rows if condition_key(row) == key])
                for key in sorted({condition_key(row) for row in stage_rows})
            }
            for stage, stage_rows in sorted(stages.items())
        },
        "compatibility": compatibility,
        "models": model_metadata(root),
        "comparisons": comparisons(rows),
        "cells": rows,
        "integrity": integrity(root, rows),
        "limits": {
            "descriptive_only": True,
            "previously_examined_tasks": True,
            "no_selective_score_reruns": True,
            "full_resource_monetary_cost": None,
            "gpu_price": None,
            "runner_service_is_partial_proxy_not_gpu_busy_time": True,
            "resource_sums_can_overlap_e2e": True,
            "failed_provider_usage_is_unknown": True,
            "early_failure_lower_cost_is_not_efficiency": True,
            "raw_evidence_locator": (
                "file_id is SHA256 of experiment-relative filename; "
                "mapping remains on experiment host"
            ),
        },
    }
    output.mkdir(parents=True, exist_ok=False)
    write(output / "multiscale-results.json", data)
    write(output / "final-integrity.json", data["integrity"])
    write(output / "continuation-resources.json", continuation)
    metadata_paths = [
        path for path in root.glob("*.json") if path.name != "multiscale-results.json"
    ]
    metadata_paths += list((root / "candidate-contexts").glob("*.json"))
    metadata_paths += list((root / "compatibility").rglob("*.json"))
    metadata_paths += list((root / "private/deployment").rglob("*"))
    metadata_paths += list(root.glob("*.log"))
    metadata_paths += list(root.glob("*.py"))
    metadata_paths += list((root / "reporting").glob("*.py"))
    metadata_paths += list((root / "private").glob("*network*"))
    write(
        output / "raw-evidence-hashes.json",
        {
            "root_metadata": evidence_manifest(root, metadata_paths),
            "cells": {row["cell"]["cell_id"]: row["raw_evidence_manifest"] for row in rows},
        },
    )
    print(
        json.dumps(
            {
                "execution_state": state,
                "analyzed_cells": len(rows),
                "analysis_errors": errors,
                "conditions": {
                    key: {
                        field: value[field]
                        for field in ("executed", "completed", "successful", "schema_failures")
                    }
                    for key, value in data["conditions"].items()
                },
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    main(arguments.root, arguments.output)
