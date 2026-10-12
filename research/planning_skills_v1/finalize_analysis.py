"""Versioned diagnostic correction after completed, audited inference; no LLM calls.

Retains the first analysis and exact-prompt audit. Proves that every shared
per-episode field except explicitly corrected policy diagnostics is unchanged.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import analyze
import analyze_heldout


CORRECTED_FIELDS = {"policy_decisions", "policy_correct", "all_executed_policy_choices_correct"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(original, revised):
    def index(rows):
        result = {(r["model"], r["episode_id"]): r for r in rows}
        if len(result) != len(rows):
            raise RuntimeError("Duplicate episode identity in analysis")
        return result
    before, after = index(original), index(revised)
    if before.keys() != after.keys():
        raise RuntimeError("Diagnostic revision changed the episode set")
    changed = {name: 0 for name in sorted(CORRECTED_FIELDS)}
    for identity, old in before.items():
        new = after[identity]
        for key, value in old.items():
            if key in CORRECTED_FIELDS:
                changed[key] += value != new[key]
            elif key == "conditional_counts":
                if any(new[key].get(k) != v for k, v in value.items()):
                    raise RuntimeError(f"Changed existing conditional diagnostic: {identity}")
            elif new.get(key) != value:
                raise RuntimeError(f"Changed frozen outcome/accounting field: {identity}, {key}")
    return {"status": "pass", "episodes": len(before), "corrected_field_changes": changed,
            "note": "All other original per-episode fields and existing conditional counts are identical, including completion, numeric success, traces, turns, tokens and timing."}


def finalize(stage, output):
    original = stage / "analysis"
    for name in ("postprocess-complete.json", "exact-prompt-audit.json"):
        if json.loads((original / name).read_text())["status"] != "pass":
            raise RuntimeError("Initial unified audit has not passed")
    if output.exists():
        raise RuntimeError("Existing final analysis; never overwrite")
    output.mkdir(parents=True)
    if stage.name == "structural-transfer-v1":
        from transfer_microbench import Task
        analyze.Task = Task
        analyze_heldout.Task = Task
        analyze_heldout.CONTRASTS = [("unbound_system", "binding_system"),
                                   ("static_system", "binding_system"),
                                   ("static_system", "unbound_system"), ("none", "static_system")]
    elif stage.name != "heldout-binding-v1":
        raise RuntimeError("This revision is limited to the declared final studies")
    analyze_heldout.analyze(stage, output)
    previous_rows = json.loads((original / "episode-results.json").read_text())
    current_rows = json.loads((output / "episode-results.json").read_text())
    invariant = compare(previous_rows, current_rows)
    previous_summary = json.loads((original / "summary.json").read_text())
    summary_path = output / "summary.json"
    summary = json.loads(summary_path.read_text())
    for key in ("statistical_note", "presentation", "support_runtime_work", "support_runtime_work_note"):
        if key in previous_summary:
            summary[key] = previous_summary[key]
    receipt = {"epoch": time.time(), "status": "pass", "revision": "policy-provenance-v2",
               "invariant": invariant,
               "original_analysis_sha256": {name: digest(original / name) for name in
                                            ("summary.json", "episode-results.json", "exact-prompt-audit.json", "postprocess-complete.json")},
               "executing_source_sha256": {p.name: digest(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
               "exact_prompt_audit": "Original once-per-study audit retained unchanged; no repeated tokenizer audit or model execution.",
               "numeric_evaluator": "Unchanged. Policy provenance is an additional diagnostic, never a replacement for frozen TSR."}
    summary["analysis_revision"] = receipt["revision"]
    summary["unchanged_outcome_verification"] = invariant
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
    with (output / "postprocess-complete.json").open("x") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
    print(json.dumps(invariant, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    finalize(arguments.root, arguments.output)
