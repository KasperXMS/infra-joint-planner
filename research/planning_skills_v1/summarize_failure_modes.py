"""Descriptive failure partitions from completed replay-validated rows; no inference."""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


LABELS = {
    "success_clean_policy_history": "Numeric success; all executed policies correct",
    "success_after_discarded_policy_error": "Numeric success; compliant submitted ancestry after an earlier policy error",
    "success_with_retained_policy_error": "Numeric success; retained policy violation",
    "wrong_answer_without_unexpected_tool_error": "Wrong answer; no unexpected tool error",
    "wrong_answer_with_unexpected_tool_error": "Wrong answer; unexpected tool error also observed",
    "budget_before_valid_compute": "Turn exhaustion; no valid computation executed",
    "budget_with_observed_policy_error": "Turn exhaustion; a valid computation chose a wrong policy",
    "budget_with_valid_compute_no_observed_policy_error": "Turn exhaustion; valid partial computation, no observed policy error",
}


def classify(row):
    if row["completion"]:
        if row["success"]:
            if row["numeric_success_with_policy_violation"]:
                return "success_with_retained_policy_error"
            if row["recovered_policy_provenance"]:
                return "success_after_discarded_policy_error"
            return "success_clean_policy_history"
        if row["finish_reason"] != "wrong_answer":
            raise RuntimeError("Unrecognized completed failure")
        return "wrong_answer_with_unexpected_tool_error" if row["unexpected_errors"] else "wrong_answer_without_unexpected_tool_error"
    if row["finish_reason"] != "turn_budget_exhausted":
        raise RuntimeError("Unexpected finish category; report it explicitly before partitioning")
    if not row["policy_decisions"]:
        return "budget_before_valid_compute"
    if row["first_policy_error_turn"] is not None:
        return "budget_with_observed_policy_error"
    return "budget_with_valid_compute_no_observed_policy_error"


def summarize(directory, output):
    if output.exists():
        raise RuntimeError("Never overwrite an earlier analysis")
    raw = (directory / "episode-results.json").read_bytes()
    rows = json.loads(raw)
    receipt = json.loads((directory / "postprocess-complete.json").read_text())
    if receipt.get("status") != "pass" or receipt.get("revision") != "policy-provenance-v2":
        raise RuntimeError("Completed versioned replay is required")
    if len(rows) != receipt["invariant"]["episodes"]:
        raise RuntimeError("Episode completeness differs from validated cohort")
    identities = {(r["model"], r["episode_id"]) for r in rows}
    if len(identities) != len(rows):
        raise RuntimeError("Duplicate episode identity")
    groups, strata = defaultdict(Counter), defaultdict(Counter)
    total, details = Counter(), []
    for row in rows:
        category = classify(row)
        total[category] += 1
        groups[(row["model"], row["condition"])][category] += 1
        strata[(row["model"], row["depth"])][category] += 1
        details.append({"model": row["model"], "episode_id": row["episode_id"],
                        "category": category, "policy_decisions": row["policy_decisions"],
                        "trace_sha256": row["trace_sha256"]})
    if sum(total.values()) != len(rows):
        raise RuntimeError("Failure partition is incomplete")
    zero = [r for r in rows if not r["completion"] and r["policy_decisions"] == 0]
    zero_errors = sum((Counter(r["unexpected_errors"]) for r in zero), Counter())
    result = {"episodes": len(rows), "counts": dict(total), "labels": LABELS,
              "groups": [{"model": m, "condition": c, "counts": dict(v)} for (m, c), v in sorted(groups.items())],
              "depth_strata": [{"model": m, "depth": d, "counts": dict(v)} for (m, d), v in sorted(strata.items())],
              "zero_valid_compute_tool_errors": dict(zero_errors),
              "episode_categories": sorted(details, key=lambda r: (r["model"], r["episode_id"])),
              "input_episode_results_sha256": hashlib.sha256(raw).hexdigest(),
              "executing_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "note": "Descriptive partitions, not causal first-failure attribution. Wrong-answer branches concern submitted numeric results; rejected calls can coexist with policy errors. Zero valid compute is not evidence of correct operation choice. Original numeric evaluator and every outcome are unchanged."}
    output.mkdir(parents=True)
    (output / "failure-decomposition.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    lines = ["# Failure decomposition", "", result["note"], "",
             "| Observed outcome/history | Episodes |", "| --- | --- |"]
    lines += [f"| {label} | {total[key]} |" for key, label in LABELS.items()]
    lines += ["", f"Total: {len(rows)} frozen episodes. Zero-valid-compute failures contain these rejected tool calls: `{json.dumps(dict(zero_errors), sort_keys=True)}`.", "",
              "A valid computation means the tool accepted the declared ordered dependencies and produced an artifact; an invalid compute request is not counted as an executed policy decision. The all-executed-policies-correct field is vacuously true when this count is zero. Such failures belong to dependency execution, not demonstrated branch competence.", "",
              "Policy-compliant submitted ancestry after an earlier wrong computation does not prove intentional recognition or repair; an update can invalidate and discard an old path. Unexpected errors exclude the task's expected source-update/transient notifications. No output is selectively rerun.", "",
              "Per-model/condition, depth and per-episode identities are retained in the accompanying JSON; decisions, input values and raw generations are absent.", ""]
    (output / "failure-decomposition.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"episodes": len(rows), "counts": dict(total)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    summarize(args.directory, args.output)
