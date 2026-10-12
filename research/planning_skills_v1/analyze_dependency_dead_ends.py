"""Localize every zero-valid-compute failure in a completed cohort; no inference."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def analyze(stage, output):
    rows = json.loads((stage / "analysis-v2/episode-results.json").read_text())
    receipt = json.loads((stage / "analysis-v2/postprocess-complete.json").read_text())
    if receipt.get("status") != "pass" or len(rows) != receipt["invariant"]["episodes"]:
        raise RuntimeError("Completed versioned analysis required")
    eligible = [r for r in rows if not r["completion"] and r["policy_decisions"] == 0]
    records, totals = [], Counter()
    for row in sorted(eligible, key=lambda r: (r["model"], r["episode_id"])):
        directory = stage / row["model"] / "episodes" / row["episode_id"]
        task = json.loads((directory / "started.json").read_text())["task"]
        nodes = {n["node"]: n for n in task["nodes"]}
        raw = (directory / "trace.jsonl").read_bytes()
        if hashlib.sha256(raw).hexdigest() != row["trace_sha256"]:
            raise RuntimeError("Changed input trace")
        counts, handles, previous = Counter(), {}, None
        actions = set()
        for line in raw.splitlines():
            event = json.loads(line)
            if event["event"] != "inference":
                continue
            observation = event["observation"]
            if observation.get("status") in ("fetched", "computed"):
                handles[observation["artifact"]] = observation["node"]
            if event["category"] != "dependency_mismatch":
                previous = None
                continue
            args = event["action"]["arguments"]
            selected = tuple(handles[h] for h in args["inputs"])
            expected = tuple(nodes[args["node"]]["parents"])
            if selected == expected:
                raise RuntimeError("Dependency-error category conflicts with ordered observed inputs")
            counts["dependency_mismatches"] += 1
            counts["requested_root"] += args["node"] == task["root"]
            counts["all_supplied_inputs_are_sources"] += all(n in task["sources"] for n in selected)
            counts["requires_unbuilt_derived_parent"] += any(p in nodes for p in expected)
            counts["same_parent_set_wrong_order_only"] += sorted(selected) == sorted(expected)
            signature = json.dumps(args, sort_keys=True)
            actions.add(signature)
            if previous is not None:
                counts["adjacent_dependency_rejections"] += 1
                counts["identical_arguments_after_rejection"] += previous == args
                same_dependencies = all(previous[k] == args[k] for k in ("node", "inputs"))
                counts["only_operation_changed_after_rejection"] += same_dependencies and previous["operation"] != args["operation"]
            previous = args
        if counts["dependency_mismatches"] != row["unexpected_errors"].get("dependency_mismatch", 0):
            raise RuntimeError("Row/trace mismatch")
        totals.update(counts)
        records.append({"model": row["model"], "episode_id": row["episode_id"], "condition": row["condition"],
                        "turns": row["turns"], "trace_sha256": row["trace_sha256"],
                        "counts": dict(counts), "distinct_rejected_argument_objects": len(actions)})
    result = {"episodes": len(records), "counts": dict(totals), "episode_results": records,
              "executing_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "note": "All completed-cohort failures with zero accepted computations, including every condition/model. Descriptive post-hoc localization, not causal attribution or an intervention. Adjacent repetition compares canonical arguments, not raw formatting. No values, policies/gold labels or raw actions exported; scores and traces are unchanged."}
    with output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
    print(json.dumps({"episodes": len(records), "counts": dict(totals)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    analyze(args.stage, args.output)
