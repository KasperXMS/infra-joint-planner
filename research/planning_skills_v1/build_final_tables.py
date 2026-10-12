"""One final cross-study inventory from complete public outcomes and recorded work."""
import csv
import json
import statistics
from pathlib import Path


def write_csv(path, rows):
    with path.open("x", newline="", encoding="utf8") as stream:
        writer = csv.DictWriter(stream, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main(root):
    result_root = root / "results"
    resources = json.loads((root / "evidence/final-resource-work.json").read_text())
    inventory = []
    for row in resources["stages"]:
        inventory.append({"model_stage": row["stage"], "engineering_invalidated": row["engineering_invalidated"],
                          "physical_batches": row["physical_generate_batches"], "logical_requests": row["logical_model_requests"],
                          "batch_service_wall_seconds": row["model_service_batch_wall_seconds"],
                          "generation_span_seconds": row["last_request_epoch"] - row["first_request_epoch"],
                          "prompt_tokens": row["unpadding_prompt_tokens"], "cloud_api_usd": 0.0, "local_gpu_usd": None})
    groups = []
    for stage in ("diagnostic-v2", "role-placement-v1", "heldout-binding-v1", "structural-transfer-v1"):
        directory = result_root / stage
        summary = json.loads((directory / "summary.json").read_text())
        rows = json.loads((directory / "episode-results.json").read_text())
        for group in summary["groups"]:
            model, condition = group["group"]
            selected = [r for r in rows if (r["model"], r["condition"]) == (model, condition)]
            if len(selected) != group["n"]:
                raise RuntimeError("Group/cohort mismatch")
            groups.append({"stage": stage, "model": model, "condition": condition, "attempted": group["n"],
                           "completion": group["completion_count"], "numeric_success": group["success_count"],
                           "turns": group["turns"], "prompt_tokens": group["prompt_tokens"],
                           "completion_tokens": group["completion_tokens"],
                           "median_workflow_e2e_seconds": statistics.median(r["e2e_seconds"] for r in selected),
                           "verifier_tool_calls": group["tool_counts"].get("verify", 0),
                           "tool_calls": json.dumps(group["tool_counts"], sort_keys=True),
                           "finish_reasons": json.dumps(group["finish_reasons"], sort_keys=True),
                           "errors_as_recorded": json.dumps(group["errors"], sort_keys=True),
                           "error_definition": "includes expected update/transient events" if stage in ("diagnostic-v2", "role-placement-v1") else "unexpected errors only",
                           "cloud_api_usd": 0.0, "local_gpu_usd": None})
    if sum(r["attempted"] for r in groups) != 1000 or sum(r["logical_requests"] for r in inventory) != 30108:
        raise RuntimeError("Final inventory is not the completed original population")
    if sum(r["turns"] for r in groups) != 27388:
        raise RuntimeError("Workflow request totals differ")
    write_csv(result_root / "model-stage-work.csv", inventory)
    write_csv(result_root / "workflow-condition-results.csv", groups)
    lines = ["# Complete experimental inventory", "",
             "All selected inference is complete. 1,000 valid workflow episodes plus 2,316 one-step decision queries; no query is counted as workflow completion/TSR. Engineering-invalidated work remains included separately. Models are official BF16 Qwen3.5-4B/9B, Transformers/SDPA, greedy thinking-disabled. Frozen stage configs define context/turn/batch settings.", "",
             "| Model stage | Engineering-only | Logical requests | Physical batches | Batch service wall, s | Generation span, s | Prompt tokens |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for row in inventory:
        lines.append(f"| {row['model_stage']} | {row['engineering_invalidated']} | {row['logical_requests']:,} | {row['physical_batches']:,} | {row['batch_service_wall_seconds']:.3f} | {row['generation_span_seconds']:.3f} | {row['prompt_tokens']:,} |")
    lines += ["", "Each physical batch is counted once. Generation span covers first through last recorded request for that model, not model-loading/setup/E2E or GPU kernel time; stages on different GPUs overlap. Unrecorded in-flight engineering work is unknown. Cloud calls are absent; local GPU USD stays unknown, not zero. Whole-instance lease accounting is separate in final-resource-work.json and the shutdown receipt.", "",
              "| Workflow study | Model | Condition | Completion | Numeric success | Turns | Prompt tokens | Output tokens | Median E2E, s | Verify tool calls |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in groups:
        n = row["attempted"]
        lines.append(f"| {row['stage']} | {row['model']} | {row['condition']} | {row['completion']}/{n} | {row['numeric_success']}/{n} | {row['turns']:,} | {row['prompt_tokens']:,} | {row['completion_tokens']:,} | {row['median_workflow_e2e_seconds']:.2f} | {row['verifier_tool_calls']} |")
    lines += ["", "The verifier is an actual deterministic provenance/freshness tool, not an LLM; all measured model calls are planner calls. No Specialist/Physical Executor model is invoked in this synthetic study. This is not a resource-accounting substitution for historical InfraMAS. Tool/finish/error details are retained per group in workflow-condition-results.csv and each original summary; development errors include expected updates, while final-study errors explicitly exclude expected notices.", "",
              "One-step accuracy/tokens are in the two decision-probe summaries. The final diagnostic publishes individual provider latencies in decision-results.csv; development request latencies remain in indexed private raw evidence. Development decisions reuse source tasks; the final diagnostic samples observed primary states and is post-hoc, not independent held-out performance validation. Placement, primary and transfer tables include every failed attempt and all its work. No inverse cost-per-success claim is made from tiny success denominators or mixed-condition batch work.", ""]
    with (result_root / "experimental-inventory.md").open("x", encoding="utf8") as stream:
        stream.write("\n".join(lines))
    print(json.dumps({"model_stages": len(inventory), "workflow_groups": len(groups), "workflow_episodes": 1000,
                      "recorded_requests_including_engineering": 30108, "valid_workflow_requests": 27388}))


if __name__ == "__main__":
    main(Path(__file__).resolve().parent)
