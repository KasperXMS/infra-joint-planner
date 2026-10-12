"""Same replay/bootstrap/prompt audit with the explicitly declared task presentation."""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import analyze
import analyze_heldout
import audit_frozen_prompts
from transfer_microbench import Task

analyze.Task = Task
analyze_heldout.Task = Task
audit_frozen_prompts.Task = Task
analyze_heldout.CONTRASTS = [("unbound_system", "binding_system"),
                            ("static_system", "binding_system"),
                            ("static_system", "unbound_system"), ("none", "static_system")]


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    analyze_heldout.analyze(args.root, args.output)
    summary_path = args.output / "summary.json"
    summary = json.loads(summary_path.read_text())
    cluster_count = len({r["cluster_id"] for r in json.loads((args.output / "episode-results.json").read_text())})
    summary["statistical_note"] = f"Exploratory paired graph-cluster bootstrap; {cluster_count} graphs, synthetic structural transfer, no universal significance claim."
    summary["presentation"] = "Opaque node/source identifiers and shuffled public node order; evaluator private topological order unchanged."
    support_work = defaultdict(lambda: {"render_attempts": 0, "support_wall_seconds": 0.0})
    for work_path in sorted(args.root.glob("*/support-work.jsonl")):
        for line in work_path.read_text().splitlines():
            record = json.loads(line)
            group = support_work[(work_path.parent.name, record["condition"])]
            group["render_attempts"] += 1
            group["support_wall_seconds"] += record["support_wall_seconds"]
    summary["support_runtime_work"] = [{"model": key[0], "condition": key[1], **value} for key, value in sorted(support_work.items())]
    summary["support_runtime_work_note"] = "Measured renderer wall time includes projection/join and its matching tokenization. Excludes shared chat-template/full-prompt tokenization and telemetry append; not CPU monetary cost. Primary stage had no separate renderer timer and is not backfilled."
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
    audit_frozen_prompts.audit(args.root, args.output / "exact-prompt-audit.json")
    with (args.output / "executing-analysis-source.json").open("x") as stream:
        json.dump({name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                   for name in ("analyze.py", "analyze_heldout.py", "audit_frozen_prompts.py", "analyze_transfer.py", "transfer_microbench.py")}, stream, indent=2)
