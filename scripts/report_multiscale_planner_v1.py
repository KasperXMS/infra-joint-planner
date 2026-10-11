"""Render four append-only reports from sanitized multiscale results; no inference."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROLES = ("manager", "specialist", "verifier")
CANDIDATES = ("qwen35-4b", "qwen35-9b", "ministral3-3b", "qwen35-27b")
ORIGINAL_SKILLS_CANDIDATES = ("qwen35-4b", "qwen35-27b")
TASKS = tuple(range(1, 7))
SCREENING_TASKS = (1, 3, 5)
FILES = (
    "multiscale-planner-screening-v1.md",
    "multiscale-planner-results-v1.md",
    "multiscale-planner-skills-ablation-v1.md",
    "multiscale-planner-research-conclusions-v1.md",
)


def fmt(value, digits=3):
    if value is None:
        return "unknown"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def seconds(value):
    return fmt(value / 1000 if value is not None else None)


def counts(value):
    return "; ".join(f"{fmt(key)}:{fmt(item)}" for key, item in sorted(value.items())) or "none"


def table(headers, rows):
    return [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
        *("| " + " | ".join(fmt(item) for item in row) + " |" for row in rows),
        "",
    ]


def key(row):
    cell = row["cell"]
    return cell["candidate"] + ("__skills" if cell["skills"] else "__no_skills")


def skills_candidates(data):
    conditions = data.get("execution_conditions", {})
    continuation = data.get("continuation_resources", {})
    for metadata in (conditions, continuation):
        selected = metadata.get("skills_candidates")
        if isinstance(selected, list) and selected:
            return tuple(dict.fromkeys(selected))
    observed = tuple(
        dict.fromkeys(
            row["cell"]["candidate"] for row in data.get("cells", []) if row["cell"]["skills"]
        )
    )
    return observed or ORIGINAL_SKILLS_CANDIDATES


def manager_node(row):
    value = row.get("execution_conditions", {}).get("manager_node", row.get("manager_node"))
    return value or ("cloud" if row["cell"]["candidate"] == "B0" else "unknown")


def contended(row):
    flags = row.get("external_gpu_contention", {})
    return bool(
        flags.get("process_set_changed_during_cell")
        or flags.get("resource_timing_comparison_caution")
        or row.get("reporting_recovery", {}).get("unplanned_external_contention_flagged")
    )


def continuation_applied(data):
    return bool(
        data.get("execution_conditions", {}).get("continuation_applied")
        or data.get("continuation_resources", {})
        .get("execution_conditions", {})
        .get("continuation_applied")
        or any(manager_node(row) == "A28" for row in data.get("cells", []))
    )


def display(condition, data):
    candidate = condition.split("__", 1)[0]
    names = {
        "B0": "B0 qwen3.8-max",
        "qwen35-4b": "Qwen3.5-4B",
        "qwen35-9b": "Qwen3.5-9B",
        "ministral3-3b": "Ministral 3 3B",
    }
    if candidate == "qwen35-27b":
        family = (
            data.get("models", {})
            .get("provenance", {})
            .get(candidate, {})
            .get("actual_checkpoint_family")
        )
        names[candidate] = (
            "Qwen3.8-27B [qwen35-27b]"
            if family == "Qwen3.8-27B"
            else "resident 27B [provenance unknown]"
        )
    return names.get(candidate, candidate) + (" +Skills" if condition.endswith("__skills") else "")


def rows_for(data, condition, tasks=TASKS):
    return [
        row
        for row in data.get("cells", [])
        if key(row) == condition and row["cell"]["task_index"] in tasks
    ]


def outcome_table(data, conditions, tasks=TASKS):
    rows = []
    for condition in conditions:
        cells = rows_for(data, condition, tasks)
        observed = len(cells)
        evaluated = [
            row["original_evaluation"]["score"]
            for row in cells
            if (row.get("original_evaluation") or {}).get("score") is not None
        ]
        attempts = sum(row.get("schema_attempts", 0) for row in cells)
        valid = sum(row.get("schema_valid", 0) for row in cells)
        failures = Counter(row["outcome_type"] for row in cells)
        rows.append(
            [
                display(condition, data),
                f"{observed}/{len(tasks)}",
                f"{sum(row['completed'] for row in cells)}/{observed}" if observed else "not run",
                f"{sum(row['successful'] for row in cells)}/{observed}" if observed else "not run",
                f"{sum(evaluated) / len(evaluated):.3f} ({len(evaluated)} evaluated)"
                if evaluated
                else "unknown",
                f"{valid}/{attempts}" if attempts else "not observed",
                sum(row.get("schema_failures", 0) for row in cells) if observed else "not run",
                counts(failures) if observed else "not run",
            ]
        )
    return table(
        [
            "Condition",
            "Observed/planned",
            "Completion",
            "TSR",
            "Mean original score",
            "Valid/schema attempts",
            "Schema failures",
            "Outcomes",
        ],
        rows,
    )


def all_conditions(data):
    ordered = ["B0__no_skills", *(c + "__no_skills" for c in CANDIDATES)]
    ordered += [c + "__skills" for c in skills_candidates(data)]
    return ordered + [c for c in sorted(data.get("conditions", {})) if c not in ordered]


def usage(metrics, field):
    value = metrics.get(field)
    if value is not None:
        return fmt(value)
    subtotal = metrics.get("known_" + field + "_subtotal")
    missing = metrics.get(
        "unknown_cached_usage_requests"
        if field == "cached_input_tokens"
        else "unknown_token_usage_requests"
    )
    return f"unknown (known subtotal {fmt(subtotal)}; {fmt(missing)} requests unknown)"


def role_table(data, conditions):
    rows = []
    for condition in conditions:
        summary = data.get("conditions", {}).get(condition)
        if not summary:
            continue
        for role in ROLES:
            metrics = summary.get("roles", {}).get(role, {})
            cost = metrics.get("cloud_api_cost", {})
            rows.append(
                [
                    display(condition, data),
                    role,
                    metrics.get("requests"),
                    metrics.get("turns"),
                    usage(metrics, "input_tokens"),
                    usage(metrics, "output_tokens"),
                    usage(metrics, "cached_input_tokens"),
                    seconds(metrics.get("provider_latency_ms")),
                    cost.get("known_usd_subtotal"),
                    cost.get("complete_usd_total"),
                    cost.get("unknown_usd_calls"),
                ]
            )
    return table(
        [
            "Condition",
            "Role",
            "Requests",
            "Turns",
            "Input tokens",
            "Output tokens",
            "Cached input",
            "Provider latency s",
            "Cloud USD known subtotal",
            "Complete cloud USD",
            "Unknown-cost calls",
        ],
        rows,
    )


def physical_table(data, conditions):
    rows = []
    for condition in conditions:
        summary = data.get("conditions", {}).get(condition)
        if not summary:
            continue
        physical = summary.get("physical", {})
        independent = summary.get("independent_planner_runner_work", {})
        rows.append(
            [
                display(condition, data),
                physical.get("admitted_requests"),
                physical.get("successful_inference_calls"),
                physical.get("failed_actions"),
                physical.get("input_tokens"),
                physical.get("output_tokens"),
                seconds(physical.get("known_model_service_ms")),
                fmt(summary.get("unmeasured_failed_model_service_work")),
                seconds(physical.get("operator_ms")),
                seconds(summary.get("task_e2e_ms")),
                seconds(summary.get("controller_execution_wall_ms")),
                physical.get("initial_transfer_bytes"),
                physical.get("action_transfer_bytes"),
                seconds(summary.get("runner_reported_total_time_ms")),
                summary.get("runner_task_starts"),
                seconds(independent.get("complete_reported_total_time_ms")),
                independent.get("known_runner_task_starts_subtotal"),
                independent.get("unobserved_cells"),
            ]
        )
    return table(
        [
            "Condition",
            "Physical admissions",
            "Inference successes",
            "Failed actions",
            "Physical input tokens",
            "Physical output tokens",
            "Known model-service s",
            "Failed service unmeasured",
            "Operator s",
            "Task E2E s",
            "Controller execution s",
            "Initial bytes",
            "Action bytes",
            "Resident runner s",
            "Resident starts",
            "Independent Planner runner s",
            "Independent starts known",
            "Independent work unobserved cells",
        ],
        rows,
    )


def workflow_table(data, conditions, tasks=TASKS):
    rows = []
    for task in tasks:
        for condition in conditions:
            cells = rows_for(data, condition, (task,))
            if not cells:
                rows.append(
                    [
                        task,
                        display(condition, data),
                        "not run",
                        "unknown",
                        "unknown",
                        "unknown",
                        "unknown",
                        "unknown",
                        "unknown",
                        "unknown",
                        "unknown",
                    ]
                )
                continue
            row = cells[0]
            detail = row.get("workflow_detail", {})
            recovery = row.get("schema_detail", {})
            rows.append(
                [
                    task,
                    display(condition, data),
                    row["outcome_type"],
                    (row.get("original_evaluation") or {}).get("score"),
                    detail.get("node_count"),
                    detail.get("edge_count"),
                    counts(detail.get("owners", {})),
                    counts(detail.get("operators", {})),
                    row.get("schema_failures"),
                    f"{fmt(recovery.get('owners_with_later_valid_call'))}/{fmt(recovery.get('owners_with_invalid_call'))}",
                    detail.get("repeated_identical_selected_calls"),
                ]
            )
    return table(
        [
            "Task index",
            "Condition",
            "Outcome",
            "Original score",
            "Nodes",
            "Artifact edges",
            "Owners",
            "Operators",
            "Schema failures",
            "Later-valid/invalid owners",
            "Identical repeated calls",
        ],
        rows,
    )


def intro(data, digest, title):
    return [
        "# " + title,
        "",
        f"Execution state: **{fmt(data.get('execution_state'))}**; "
        f"analyzed {fmt(data.get('analyzed_cells'))} cells. "
        "Missing cells below are not run, never zero-score observations.",
        "",
        f"Sanitized input SHA256: `{digest}`. Base commit `{fmt(data.get('base_commit'))}`. "
        "Raw prompts, answers, task payloads and credential evidence remain on the "
        "experiment machines.",
        "",
        "Six frozen, previously examined tasks; one attempt per model/task/Skills condition. "
        "Results are descriptive: no significance, noninferiority, held-out validation, "
        "or universal scale threshold. "
        "Schema failures and legitimate budget exhaustion remain evaluation outcomes; "
        "no selective score reruns.",
        "",
    ] + continuation_note(data)


def continuation_note(data):
    if not continuation_applied(data):
        return []
    return [
        "The original external-GPU-contention stop remains historical evidence. "
        f"Current export state is **{fmt(data.get('execution_state'))}**; "
        f"preserved stop receipts: {len(data.get('stop_receipts', []))}. "
        "A completed authorized continuation can be complete while retaining that stop.",
        "",
        "Placement amendment: the first three 4B cells (task indices 1/3/5) used GPU1; "
        "the remaining 4B cells use an independent A28 Planner service. The third "
        "4B cell's actual score is retained with its external-contention flag; its "
        "Planner service/runner work remains unknown. The 4B six-task cohort mixes "
        "placement and contention conditions, so its aggregate cost is not a pure "
        "matched hardware comparison. 9B and Ministral use A28; the resident 27B "
        "remains on GPU0. Foreign processes are outside experiment ownership.",
        "",
        "The continuation Skills allocation is 9B plus resident 27B, six matched "
        "tasks each. Timing verification that selection preceded the first 9B "
        "benchmark: "
        + fmt(data.get("execution_conditions", {}).get("skills_changed_before_first_9b_benchmark"))
        + ". The old 4B allocation is "
        "preserved in the original freeze but is not executed as an extra ablation. "
        "Weights, semantic prompts, frozen Skills, evaluator, Scheduler and Executor "
        "are unchanged; retained benchmark cells are not rerun.",
        "",
    ]


def placement_table(data):
    if not continuation_applied(data):
        return []
    cohorts = {}
    for row in data.get("cells", []):
        cohort = (key(row), manager_node(row), contended(row))
        cohorts.setdefault(cohort, []).append(row)
    rows = []
    for (condition, node, contention), cells in sorted(cohorts.items()):
        e2e = [row.get("task_e2e_ms") for row in cells]
        work = []
        for row in cells:
            service = row.get("independent_planner_service_work", {})
            runner = row.get("independent_planner_runner_work", {})
            unknown = contended(row) or service.get("observed") is False
            work.append(None if unknown else runner.get("reported_total_time_ms_sum"))
        rows.append(
            [
                display(condition, data),
                node,
                contention,
                ",".join(str(row["cell"]["task_index"]) for row in cells),
                f"{sum(row['completed'] for row in cells)}/{len(cells)}",
                f"{sum(row['successful'] for row in cells)}/{len(cells)}",
                sum(row.get("schema_failures", 0) for row in cells),
                seconds(sum(e2e) if all(value is not None for value in e2e) else None),
                seconds(sum(work) if all(value is not None for value in work) else None),
            ]
        )
    lines = ["## Placement and contention strata", ""] + table(
        [
            "Condition",
            "Manager placement",
            "External contention",
            "Task indices",
            "Completion",
            "TSR",
            "Schema failures",
            "Task E2E s",
            "Independent Planner runner s",
        ],
        rows,
    )
    summary = data.get("continuation_resources", {}).get("summary", {})
    lines += table(
        [
            "Placement cohort",
            "Cells",
            "Resource samples",
            "Controller GPU min free MiB",
            "A28 min available shared RAM KiB",
        ],
        [
            [
                cohort,
                values.get("cells"),
                values.get("sample_count"),
                counts(values.get("gpu_free_mib_min_by_index", {})),
                values.get("A28_available_ram_kib_min"),
            ]
            for cohort, values in sorted(summary.get("by_placement_cohort", {}).items())
        ],
    )
    lines += [
        "Sampled memory headroom is neither peak model memory nor continuous OOM "
        "surveillance. Missing Planner work for the contended third 4B cell remains "
        "unknown; its completion, score, API receipts and physical evidence are "
        "retained. Mixed-placement cohort resource sums are descriptive only.",
        "",
    ]
    return lines


def provenance_note(data):
    actual = display("qwen35-27b__no_skills", data)
    return [
        f"The frozen slot `qwen35-27b` is reported as **{actual}**. "
        "When the provenance correction receipt is present, its resident weight and "
        "projector match "
        "the official Qwen3.8-27B registry descriptors, rather than Qwen3.5-27B. "
        "The slot, weights and deployment were preserved. Only 4B and 9B provide a same-release "
        "Qwen3.5 size comparison; 27B also changes model generation, hardware and "
        "MTP/runtime configuration. "
        "None of these observational differences isolates a size-only causal effect.",
        "",
    ]


def screening_report(data, digest):
    conditions = [c + "__no_skills" for c in CANDIDATES]
    lines = intro(data, digest, "Multi-scale Planner screening v1")
    lines += [
        "Tasks 1/3/5 are the preregistered first task in MultiHop-RAG, LongBench and Video-MME. "
        "These cells are retained as the first half of the six-task matrix; any "
        "placement amendment and contention strata are recorded above. "
        "screening is not an independent validation set and its costs must not be counted twice.",
        "",
        "All four preselected candidates proceed unless context integrity, safety or "
        "budget protection fails. "
        "Observed model errors do not create another ability Gate or a score-based selection rule.",
        "",
    ]
    lines += provenance_note(data) + outcome_table(data, conditions, SCREENING_TASKS)
    lines += placement_table(data) + workflow_table(data, conditions, SCREENING_TASKS)
    return lines


def deployment_tables(data):
    models = data.get("models", {})
    lines = ["## Deployment and preparation work", ""]
    lines += table(
        ["Candidate", "Downloaded tag", "Download s", "Quantization", "Manifest SHA256"],
        [
            [
                display(candidate + "__no_skills", data),
                value.get("tag"),
                value.get("elapsed_seconds"),
                value.get("details", {}).get("quantization_level"),
                value.get("manifest_sha256"),
            ]
            for candidate, value in sorted(models.get("downloads", {}).items())
        ],
    )
    lines += table(
        [
            "Candidate",
            "Phase",
            "Load/attestation s",
            "Resident VRAM bytes",
            "GPU snapshots used/free MiB",
            "Executor runners unchanged",
        ],
        [
            [
                display(value["candidate"] + "__no_skills", data),
                value.get("phase"),
                seconds(value.get("elapsed_ms")),
                value.get("resident_size_vram_bytes"),
                "; ".join(
                    f"GPU{gpu.get('index')}:{fmt(gpu.get('used_mib'))}/{fmt(gpu.get('free_mib'))}"
                    for gpu in value.get("gpu_memory_snapshots", [])
                ),
                value.get("executor_runners_unchanged"),
            ]
            for value in models.get("deployment", [])
        ],
    )
    lines += [
        "Load/attestation elapsed time is preparation outside task E2E; a resident endpoint's "
        "attestation time is not a new weight-load measurement. VRAM values are "
        "snapshots, not peaks. "
        "Independent local Planner services share GPU resources with the protected physical pool; "
        "contention can affect timings. No resident Executor model was substituted for "
        "another model.",
        "",
        "Frozen Manager sampling: `"
        + json.dumps(models.get("sampling_from_frozen_plan", {}), sort_keys=True)
        + "`.",
        "",
    ]
    lines += table(
        [
            "Candidate",
            "Context/output",
            "Thinking",
            "Renderer",
            "Parser",
            "Model blob SHA256",
            "Template SHA256",
        ],
        [
            [
                display(candidate + "__no_skills", data),
                f"{fmt(value.get('context_window'))}/{fmt(value.get('reserved_output_tokens'))}",
                value.get("thinking"),
                value.get("renderer"),
                value.get("parser"),
                value.get("model_blob"),
                value.get("template_sha256"),
            ]
            for candidate, value in sorted(models.get("contexts", {}).items())
        ],
    )
    lines += [
        "A null thinking field means the sanitized metadata does not establish that switch; "
        "it does not assert that thinking was enabled. Backend versions and "
        "architecture details are "
        "retained in sanitized model metadata. Parser differences are deployment "
        "differences, not evidence "
        "that model scale alone caused an observed outcome.",
        "",
    ]
    return lines


def comparison_table(data, skills=False):
    rows = []
    for comparison in data.get("comparisons", []):
        condition = comparison["comparison"]
        if condition.endswith("__skills") != skills:
            continue
        delta = comparison.get("delta_comparison_minus_reference", {})
        manager = delta.get("roles", {}).get("manager", {})
        physical = delta.get("physical", {})
        rows.append(
            [
                display(comparison["reference"], data),
                display(condition, data),
                f"{comparison['paired_tasks']}/6",
                delta.get("completed"),
                delta.get("successful"),
                delta.get("schema_failures"),
                manager.get("turns"),
                manager.get("input_tokens"),
                delta.get("cloud_api_known_usd_subtotal"),
                physical.get("successful_inference_calls"),
                seconds(physical.get("known_model_service_ms")),
                seconds(delta.get("task_e2e_ms")),
                "unknown",
            ]
        )
    return table(
        [
            "Reference",
            "Comparison",
            "Pairs",
            "Completion delta",
            "TSR numerator delta",
            "Schema delta",
            "Manager turns delta",
            "Manager input delta",
            "Known cloud USD delta",
            "Physical successes delta",
            "Known model-service s delta",
            "Task E2E s delta",
            "Full cost delta",
        ],
        rows,
    )


def results_report(data, digest):
    conditions = all_conditions(data)
    lines = intro(data, digest, "Multi-scale Planner six-task results v1")
    lines += provenance_note(data)
    lines += [
        "B0 is the new matched qwen3.8-max Manager condition. Specialist, Verifier, physical pool, "
        "Scheduler, evaluator and semantic prompts stay fixed. Historical B0 4/6 is descriptive "
        "context only and is not pooled with the new baseline.",
        "",
    ]
    lines += outcome_table(data, conditions)
    lines += placement_table(data)
    lines += ["## Matched task comparison minus B0", ""] + comparison_table(data)
    lines += [
        "Deltas use only the shared task indices shown in the pair count. Fewer than "
        "six pairs is a partial comparison. Cloud deltas compare known subtotals; "
        "if costs are missing, a subtotal difference is not a bound on the true cost difference.",
        "",
    ]
    lines += ["## Control-plane resources", ""] + role_table(data, conditions)
    lines += [
        "Known token/cache subtotals are lower bounds when any request lacks usage. "
        "Unknown provider failures are not filled with zero tokens or zero cost. Cloud subtotals "
        "use the frozen price accounting; local GPU monetary cost and full resource "
        "monetary cost remain unknown.",
        "",
        "## Physical and wall-clock resources",
        "",
    ] + physical_table(data, conditions)
    lines += [
        f"Matrix journal wall: {seconds(data.get('matrix_wall_ms'))} s, "
        "including setup/cleanup and recorded pauses. "
        "Task E2E is summed separately. Operator/model service, API latency and runner "
        "durations can overlap; "
        "do not add them to infer E2E or GPU busy seconds. Resident work covers all "
        "five existing runners "
        "and includes Manager work only for a reused resident endpoint; independent "
        "Planner work is reported "
        "separately. Runner decode runs under MTP are not interchangeable with output "
        "tokens. An independent endpoint does not apply to B0 or the resident 27B; "
        "its unobserved independent-work counter does not imply missing resident work. "
        "Failed-action "
        "service work can be unmeasured. Persisted API JSON sizes are storage, not "
        "measured network transfer.",
        "",
        "Early failures may consume fewer resources because work was never completed. "
        "Lower observed cost "
        "on a failed task is not evidence of useful inference efficiency. GPU prices, "
        "energy, peak VRAM and "
        "complete GPU compute time are unknown.",
        "",
        "## Same-task workflows",
        "",
    ] + workflow_table(data, conditions)
    lines += [
        "Edges are artifact dependencies, including multiple edges between operator nodes. "
        "Owner labels are anonymized. A later valid call after a schema error "
        "establishes protocol recovery, "
        "not task completion or correctness. Counts describe topology and operator "
        "choices; they do not "
        "establish semantic decomposition quality or whether all necessary information "
        "reached synthesis.",
        "",
    ] + deployment_tables(data)
    lines += ["## Execution integrity", ""]
    lines += table(
        ["Check", "Observed"],
        [
            [
                field,
                counts(value)
                if isinstance(value, dict)
                else "; ".join(map(str, value))
                if isinstance(value, list)
                else value,
            ]
            for field, value in data.get("integrity", {}).items()
        ],
    )
    return lines


def paired(data, candidate):
    left = {row["cell"]["task_index"]: row for row in rows_for(data, candidate + "__no_skills")}
    right = {row["cell"]["task_index"]: row for row in rows_for(data, candidate + "__skills")}
    return left, right, sorted(set(left) & set(right))


def paired_token_delta(left, right, tasks, field):
    if not tasks:
        return None
    values = [
        (left[t]["roles"]["manager"].get(field), right[t]["roles"]["manager"].get(field))
        for t in tasks
    ]
    return (
        sum(b - a for a, b in values)
        if all(a is not None and b is not None for a, b in values)
        else None
    )


def skills_report(data, digest):
    selected = skills_candidates(data)
    lines = intro(data, digest, "Multi-scale Planner frozen Skills ablation v1")
    lines += [
        "The preregistered ablation uses the unchanged `configs/skills/planner-procedural-v1.md` "
        "for "
        + ", ".join(display(candidate + "__no_skills", data) for candidate in selected)
        + ". No-Skills matrix cells are reused as "
        "matched comparisons; "
        "they are not extra benchmark attempts. Model/task/runtime/budgets/strong roles "
        "remain matched.",
        "",
    ] + provenance_note(data)
    rows = []
    for candidate in selected:
        left, right, tasks = paired(data, candidate)
        state = (
            "complete six-task pairs" if tasks == list(TASKS) else "partial" if tasks else "not run"
        )
        rows.append(
            [
                display(candidate + "__no_skills", data),
                f"{len(tasks)}/6",
                state,
                sum(right[t]["completed"] - left[t]["completed"] for t in tasks) if tasks else None,
                sum(right[t]["successful"] - left[t]["successful"] for t in tasks)
                if tasks
                else None,
                paired_token_delta(left, right, tasks, "input_tokens"),
                paired_token_delta(left, right, tasks, "output_tokens"),
                paired_token_delta(left, right, tasks, "known_input_tokens_subtotal"),
            ]
        )
    lines += table(
        [
            "Model",
            "Paired tasks",
            "Coverage",
            "Completion delta",
            "TSR numerator delta",
            "Manager input delta",
            "Manager output delta",
            "Known input subtotal delta",
        ],
        rows,
    )
    lines += [
        "All deltas are with-Skills minus without-Skills on the same observed paired tasks. "
        "A partial pair count is not a six-task Skills effect. Total Manager input "
        "differences include "
        "Skills text repeated in requests, changed turn counts, tool results and recovery history; "
        "they are not a tokenizer-only estimate of the static Skills overhead. Cached usage and "
        "unknown provider requests must be considered separately.",
        "",
    ]
    lines += comparison_table(data, skills=True)
    for candidate in selected:
        conditions = [candidate + "__no_skills", candidate + "__skills"]
        lines += ["## " + display(conditions[0], data), ""]
        lines += (
            outcome_table(data, conditions)
            + role_table(data, conditions)
            + physical_table(data, conditions)
        )
        lines += workflow_table(data, conditions)
    lines += [
        "No statistical significance, general Skills efficacy claim, or size "
        "interaction is established "
        "by two models and six previously examined tasks. The resident 27B is Qwen3.8, "
        "so comparison "
        "against the smaller Skills model also changes model generation. "
        "If the ablation was not run, "
        "this report "
        "records the missing evidence rather than treating missing cells as failed trials.",
        "",
    ]
    return lines


def conclusions_report(data, digest, decision, reason):
    conditions = ["B0__no_skills", *(c + "__no_skills" for c in CANDIDATES)]
    lines = intro(data, digest, "Multi-scale Planner research conclusions v1")
    lines += [
        f"Infra-aware Workflow Adapter decision: **{decision.upper()}**. {reason.strip()}",
        "",
        "This decision is supplied by the researcher after reviewing evidence; the "
        "report generator "
        "does not invent an acceptance threshold. No Adapter, retrieval/sharing mechanism, "
        "join/leave logic, or additional experiment is started by this report.",
        "",
    ]
    lines += provenance_note(data) + outcome_table(data, conditions)
    lines += [
        "1. **RQ1 — hardware support.** Successful deployment receipts establish only the listed "
        "model/context/quantization configurations and point-in-time memory headroom on "
        "this setup. "
        "The independent Planner and protected Executor pool share GPU resources. "
        "Survey-only models, "
        "untried Orin placements and larger context windows remain unmeasured; peak "
        "memory is unknown.",
        "",
        "2. **RQ2 — scale and protocol reliability.** Raw valid/schema-attempt counts, "
        "failure types "
        "and Completion above are the observed operating points. Safety admission is "
        "not an ability "
        "pass. No preregistered numerical reliability threshold or minimum acceptable "
        "parameter scale "
        "can be inferred from six tasks. Only Qwen3.5-4B/9B form a same-release size comparison.",
        "",
        "3. **RQ3 — reliability versus TSR.** Compare schema validity, recovery and TSR jointly. "
        "A legal workflow can still produce an incorrect answer; later-valid recovery "
        "is not success. "
        "The matrix describes co-occurrence, not a causal effect or statistically "
        "established correlation.",
        "",
        "4. **RQ4 — local versus strong quality.** The matched B0 and local six-task "
        "numerators above "
        "are directly descriptive under their recorded conditions. Equality or a small "
        "observed gap "
        "does not establish noninferiority or general parity. Partial conditions cannot support a "
        "six-task comparison. Historical B0 is kept separate.",
        "",
        "5. **RQ5 — complete resources.** Manager savings must be assessed together "
        "with Specialist/Verifier "
        "recovery, physical service, runner work, transfer and E2E. API prices are only "
        "one component. "
        "GPU busy time, energy and GPU prices remain unknown, so complete monetary savings cannot "
        "be claimed. Early-failure resource reduction is not efficiency.",
        "",
        "6. **RQ6 — Skills effect.** The ablation report gives paired with-minus- "
        "without deltas and "
        "explicit six-task coverage. Input-token differences include both instruction overhead and "
        "behavior changes. Two model sizes cannot establish a general size-by-Skills interaction; "
        "the 27B slot also changes checkpoint generation.",
        "",
        "7. **RQ7 — workflows and information flow.** The same-task tables expose owner/operator "
        "choices, artifact edges, repetitions, schema failures and protocol recovery. Raw traces "
        "remain available privately for semantic assessment. Structural counts alone "
        "cannot establish "
        "whether decomposition or information aggregation was correct.",
        "",
        "8. **RQ8 — future Adapter base.** "
        f"The researcher's decision is {decision.upper()}: {reason.strip()} "
        "Any future base must be named by actual checkpoint and runtime, preserve a "
        "quality baseline "
        "and permit measurement of recovery/physical costs. This run does not implement "
        "an Adapter.",
        "",
        "9. **RQ9 — threshold/frontier.** These observations can identify candidate "
        "operating points "
        "for a later preregistered study, not a universal threshold or established "
        "quality-cost Pareto "
        "frontier. Missing full costs, six known tasks, one attempt, parser/runtime "
        "differences and "
        "the 27B generation correction limit such claims. No extra repeats or tasks were added.",
        "",
    ]
    return lines


def main(source, output_dir, decision, reason):
    if not reason.strip():
        raise ValueError("A concrete manual Adapter decision reason is required")
    raw = source.read_bytes()
    data = json.loads(raw)
    if data.get("version") != "multiscale-planner-results-v1":
        raise ValueError("Expected sanitized multiscale-planner-results-v1 input")
    destinations = [output_dir / name for name in FILES]
    if any(path.exists() for path in destinations):
        raise FileExistsError("Reports are append-only; use a new output namespace")
    digest = hashlib.sha256(raw).hexdigest()
    reports = [
        screening_report(data, digest),
        results_report(data, digest),
        skills_report(data, digest),
        conclusions_report(data, digest, decision, reason),
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    for path, lines in zip(destinations, reports, strict=True):
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(lines).rstrip() + "\n")
    print(
        json.dumps(
            {
                "reports": [path.name for path in destinations],
                "input_sha256": digest,
                "execution_state": data.get("execution_state"),
                "adapter_decision": decision,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", "--results", dest="source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--adapter-decision", choices=("go", "no-go"), required=True)
    parser.add_argument("--adapter-reason", required=True)
    args = parser.parse_args()
    main(args.source, args.output_dir, args.adapter_decision, args.adapter_reason)
