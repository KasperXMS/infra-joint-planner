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
    if not paths:
        return {
            "observed": False,
            "runner_task_starts": None,
            "reported_total_time_ms_sum": None,
            "reported_evaluation_units": {},
        }
    return {"observed": True, **parse_runner_work("\n".join(texts))}


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
    downloads = {}
    for path in sorted(root.glob("*-download.json")):
        value = read(path)
        show = value.get("show", {})
        downloads[label(path.name.removesuffix("-download.json"))] = {
            **safe_metadata(value),
            "elapsed_seconds": value.get("elapsed_seconds"),
            "backend": safe_metadata(value.get("version", {})),
            "details": safe_metadata(show.get("details", {})),
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
    return {"contexts": result, "downloads": downloads, "download_errors": errors}


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
    data = {
        "version": "multiscale-planner-results-v1",
        "base_commit": label(freeze.get("base_commit"), "70a75ae"),
        "execution_state": state,
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
    metadata_paths = [
        path for path in root.glob("*.json") if path.name != "multiscale-results.json"
    ]
    metadata_paths += list((root / "candidate-contexts").glob("*.json"))
    metadata_paths += list((root / "compatibility").rglob("*.json"))
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
