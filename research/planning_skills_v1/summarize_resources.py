"""Whole-goal work/rental accounting; never fabricate a per-GPU USD price."""
import argparse
import json
from collections import defaultdict
from pathlib import Path


def records(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def summarize(root, output):
    stages = []
    for p in sorted((root / "results").glob("*/*/service-batches.jsonl")):
        batches = records(p)
        if not batches:
            continue
        stages.append({"stage": str(p.parent.relative_to(root / "results")),
                       "engineering_invalidated": (p.parent.parent / "engineering-invalidated.json").exists(),
                       "physical_generate_batches": len(batches),
                       "logical_model_requests": sum(b["requests"] for b in batches),
                       "model_service_batch_wall_seconds": sum(b["provider_seconds"] for b in batches),
                       "first_request_epoch": min(b["started_epoch"] for b in batches),
                       "last_request_epoch": max(b["finished_epoch"] for b in batches),
                       "padded_input_token_positions": sum(b["padded_input_width"] * b["requests"] for b in batches) if all("padded_input_width" in b for b in batches) else None,
                       "unpadding_prompt_tokens": sum(sum(b["input_lengths"]) for b in batches) if all("input_lengths" in b for b in batches) else None})
    telemetry = records(root / "resources.jsonl")
    budget = json.loads((root / "resource-budget.json").read_text())
    energy = defaultdict(float)
    for a, b in zip(telemetry, telemetry[1:]):
        def watts(sample):
            result = {}
            for line in sample.get("gpu_csv", "").splitlines():
                cells = [cell.strip() for cell in line.split(",")]
                if len(cells) == 4:
                    try:
                        result[cells[0]] = float(cells[3])
                    except ValueError:
                        pass
            return result
        left, right = watts(a), watts(b)
        dt = b["epoch"] - a["epoch"]
        if 0 < dt <= 180:
            for gpu in left.keys() & right.keys():
                energy[gpu] += (left[gpu] + right[gpu]) / 2 * dt / 3600
    elapsed = telemetry[-1]["epoch"] - budget["start_epoch"]
    result = {"stages": stages, "telemetry_samples": len(telemetry),
              "elapsed_seconds_through_last_sample": elapsed,
              "whole_instance_rental_cny_estimate": elapsed / 3600 * budget["lease_cny_per_hour"],
              "rate_cny_per_hour": budget["lease_cny_per_hour"],
              "baseline_epoch": budget["start_epoch"], "last_sample_epoch": telemetry[-1]["epoch"],
              "sampled_gpu_energy_wh_estimate": dict(energy),
              "gpu_energy_note": "Trapezoidal NVML board-power estimate over observed gaps <=180s, not metered energy or currency.",
              "local_gpu_usd": None, "cloud_api_usd": 0.0,
              "accounting_note": "Includes setup and invalidated engineering work. Unrecorded in-flight work is not inferred. Batch wall is not GPU kernel time. No allocation of mixed-condition batch costs to individual treatments."}
    with output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
    print(json.dumps({"stages": len(stages), "elapsed_hours": elapsed / 3600,
                      "rental_cny_estimate": result["whole_instance_rental_cny_estimate"]}))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    summarize(args.root, args.output)
