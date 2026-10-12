"""One final replay after all models finish; system-failure STOP without reruns."""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

from runtime_guard import append, register


def main(root, experiment):
    register(root, f"postprocess_{experiment}")
    config_path = root / "configs" / f"{experiment}.json"
    config = json.loads(config_path.read_text())
    stage = root / "results" / experiment
    output = stage / "analysis"
    output.mkdir(parents=True, exist_ok=True)
    receipt = output / "postprocess-started.json"
    with receipt.open("x") as stream:
        json.dump({"launched_epoch": time.time(), "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
                   "source_sha256": {name: hashlib.sha256((root / "code" / name).read_bytes()).hexdigest()
                                     for name in ("analyze.py", "analyze_heldout.py", "audit_frozen_prompts.py", "postprocess_when_complete.py")}}, stream, indent=2)
    while not all((stage / model / "complete.json").exists() for model in config["models"]):
        if (root / "SYSTEM_ISSUE").exists():
            (root / "STOP").touch(exist_ok=True)
            append(root / "administration.jsonl", {"epoch": time.time(), "event": "system_failure_batch_stop", "experiment": experiment})
            raise SystemExit("System issue: no further workflows or automatic reruns")
        if (root / "STOP").exists():
            raise SystemExit("STOP requested")
        time.sleep(20)
    for script, extra in (("analyze_heldout.py", ["--output", str(output)]),
                          ("audit_frozen_prompts.py", ["--output", str(output / "exact-prompt-audit.json")])):
        subprocess.run([sys.executable, str(root / "code" / script), "--root", str(stage), *extra], check=True)
    with (output / "postprocess-complete.json").open("x") as stream:
        json.dump({"finished_epoch": time.time(), "status": "pass"}, stream, indent=2)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--experiment", required=True)
    args = p.parse_args()
    main(args.root, args.experiment)
