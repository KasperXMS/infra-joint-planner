"""Publish audited synthetic outcome metadata; raw actions/inputs stay private."""
import argparse
import csv
import json
import shutil
from pathlib import Path


PRIVATE_DETAILS = {"decisions", "executed_policy_decisions", "submitted_provenance_error_decisions", "submitted_value"}
ORDER = ["none", "static_system", "static", "local", "ledger_system", "binding_system", "unbound_system"]


def publish(analysis, output):
    receipt = json.loads((analysis / "postprocess-complete.json").read_text())
    if receipt["status"] != "pass" or receipt.get("revision") != "policy-provenance-v2":
        raise RuntimeError("Final versioned analysis has not passed")
    if output.exists():
        raise RuntimeError("Existing published results; never overwrite")
    rows = json.loads((analysis / "episode-results.json").read_text())
    summary = json.loads((analysis / "summary.json").read_text())
    assert len(rows) == receipt["invariant"]["episodes"] == summary["episodes"]
    output.mkdir(parents=True)
    for name in ("summary.json", "trace-index.json", "postprocess-complete.json", "exact-prompt-audit.json"):
        if (analysis / name).exists():
            shutil.copyfile(analysis / name, output / name)
    public = [{k: v for k, v in r.items() if k not in PRIVATE_DETAILS} for r in rows]
    (output / "episode-results.json").write_text(json.dumps(public, indent=2, sort_keys=True), encoding="utf-8")
    fields = ["model", "condition", "task_id", "cluster_id", "depth", "template", "update_mode",
              "completion", "success", "submitted_provenance_policy_compliant", "numeric_success_with_policy_violation",
              "finish_reason", "turns", "prompt_tokens", "completion_tokens", "support_tokens", "max_prompt_tokens",
              "e2e_seconds", "tool_seconds", "policy_correct", "policy_decisions", "recovered_policy_provenance",
              "conditional_counts", "tool_counts", "unexpected_errors", "trace_sha256", "local_gpu_usd", "cloud_api_usd"]
    with (output / "results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        for row in public:
            writer.writerow({k: json.dumps(row[k], sort_keys=True) if isinstance(row[k], dict) else row[k] for k in fields})
    groups = sorted(summary["groups"], key=lambda g: (g["group"][0], ORDER.index(g["group"][1])))
    lines = ["# Audited synthetic workflow results", "",
             "All frozen episodes are included. Completion, numeric task success and submitted-policy compliance are separate metrics. Raw generations, per-decision values and submitted values remain in the private evidence archive.", "",
             "| Model | Condition | Completion | Numeric success | Policy-compliant submission | Turns | Prompt tokens | Output tokens | Median E2E, s |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for g in groups:
        model, condition = g["group"]
        lines.append(f"| {model} | {condition} | {g['completion_count']}/{g['n']} | {g['success_count']}/{g['n']} | {g['policy_compliant_completion_count']}/{g['n']} | {g['turns']:,} | {g['prompt_tokens']:,} | {g['completion_tokens']:,} | {g['e2e_median_seconds']:.2f} |")
    lines += ["", "Prompt/output counts include failed workflows. E2E reflects the frozen mixed-condition tensor batches. Batch service wall is counted once in summary.json; summed overlapping request latency is not GPU kernel time. Local GPU USD is unknown (JSON null / empty CSV cell), and cloud API calls are absent.", "",
              "## Failures and verification", "",
              "| Model | Condition | Schema-valid / raw actions | JSON / schema failures | Dependency mismatch | Stale/invalid | Non-root verify | Phase / terminal errors | Turn exhaustion | Verify calls, all workflows |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for g in groups:
        e, c = g["errors"], g["counts"]
        lines.append(f"| {g['group'][0]} | {g['group'][1]} | {c.get('schema_valid_actions',0)}/{c.get('raw_actions',0)} | {e.get('json_parse_failed',0)} / {e.get('schema_validation_failed',0)} | {e.get('dependency_mismatch',0)} | {e.get('invalid_or_stale_artifact',0)} | {e.get('not_root',0)} | {e.get('phase_violation',0)} / {e.get('terminal_contract_failed',0)} | {g['finish_reasons'].get('turn_budget_exhausted',0)} | {g['tool_counts'].get('verify',0)} |")
    lines += ["", "All other typed errors, context rejections, legal deadlines and finish reasons remain in summary.json and per-episode tables. Expected source updates/transient notices are excluded from unexpected-error counts. Correct submitted provenance after earlier wrong computations is a behavioral diagnostic; it does not prove that the model recognized its semantic error.", "",
              "## Paired success contrasts", "",
              "Intervals resample graph clusters and retain paired update variants. They are exploratory uncertainty summaries on a selected synthetic stress distribution, not universal significance claims.", "",
              "| Model | Treatment minus baseline | Mean TSR difference, pp | Cluster bootstrap 95%, pp | Rescues / regressions |",
              "| --- | --- | --- | --- | --- |"]
    for model, contrasts in sorted(summary["paired"].items()):
        for contrast in contrasts:
            if contrast["update_mode"] != "all":
                continue
            effect = contrast["effects"]["success"]
            lo, hi = effect["cluster_bootstrap_percentile95"]
            lines.append(f"| {model} | {contrast['treatment']} - {contrast['baseline']} | {100*effect['mean']:+.2f} | [{100*lo:.2f}, {100*hi:.2f}] | {contrast['rescues']} / {contrast['regressions']} |")
    lines += ["", "Runtime condition names ending in `_system` put the generic static bank in the system message; their observation-only dynamic block is the latest user message. Joined/unjoined blocks match facts and tokenizer length at the same state, not total tokens along divergent trajectories.", ""]
    (output / "result-tables.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"episodes": len(public), "groups": len(groups), "output": str(output)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    publish(args.analysis, args.output)
