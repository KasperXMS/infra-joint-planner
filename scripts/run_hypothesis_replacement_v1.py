"""Run the preregistered technical-invalidity replacement H1 pair once."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import time
from pathlib import Path

from run_hypothesis_feasibility_v1 import gpu_sample, probe_model, public_trial, rows, score, sha

REPLACEMENT = "multihop:667f4ac48afef820"
ORIGINAL = "multihop:a647807d9a1d0efd"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    public = root / "public"
    study = root / "controller" / "study"
    out = root / "controller" / "out"
    manifest = json.loads((public / "frozen-experiment-manifest.json").read_text())
    if manifest["task_ids"][0] != ORIGINAL:
        raise RuntimeError("original frozen task mismatch")
    initial = [
        json.loads(line) for line in (public / "trial-outcomes.jsonl").read_text().splitlines()
    ]
    failed = next(row for row in initial if row["run_id"] == "h03-0-g1-hfast")
    if (
        failed["error"]["type"] != "RuntimeError"
        or "artifact_too_large" not in failed["error"]["message"]
    ):
        raise RuntimeError("replacement reason mismatch")
    if (public / "replacement-manifest.json").exists():
        raise FileExistsError("replacement already frozen")
    task = rows(study / "task-candidates.jsonl")[REPLACEMENT]
    private = rows(
        Path("/home/super/xiaoming/infra-evaluation-workload-v0.1/private/evaluator-private.jsonl")
    )[REPLACEMENT]
    probes = probe_model()
    if any(row["model"] != manifest["model"]["served_name"] for row in probes):
        raise RuntimeError("resident model changed")
    replacement_manifest = {
        "created_unix": time.time(),
        "replaces": ORIGINAL,
        "task_id": REPLACEMENT,
        "reason": "G1 source-selected artifact exceeded the study Worker's 65536-byte read cap",
        "rule": "first remaining D2 MultiHop Development row in the parent manifest",
        "worker_read_cap_before": 65536,
        "worker_read_cap_after": 262144,
        "workflow_order": ["G0", "G1"],
        "profile": "Hfast",
        "script_sha256": sha(study / "run_hypothesis_cell_v1.py"),
        "model_probes": probes,
    }
    (public / "replacement-manifest.json").write_text(
        json.dumps(replacement_manifest, indent=2, sort_keys=True) + "\n"
    )
    outcomes = []
    for index, workflow in enumerate(("G0", "G1"), start=5):
        run_id = f"h{index:02d}-replacement-{workflow.lower()}-hfast"
        if (out / (run_id + ".json")).exists():
            raise FileExistsError(run_id)
        before = gpu_sample()
        done = subprocess.run(
            [
                "bash",
                str(root / "run_isolated_hypothesis_controller_v1.sh"),
                str(root / "controller"),
                run_id,
                "run_hypothesis_cell_v1.py",
                "--task-id",
                REPLACEMENT,
                "--workflow",
                workflow,
                "--profile",
                "Hfast",
            ],
            capture_output=True,
            text=True,
            timeout=3600,
            check=False,
        )
        after = gpu_sample()
        raw_path = out / (run_id + ".json")
        raw = (
            json.loads(raw_path.read_text())
            if raw_path.exists()
            else {
                "run_id": run_id,
                "task_id": REPLACEMENT,
                "workflow": workflow,
                "profile": "Hfast",
                "answer": None,
                "error": {"type": "controller_exit", "message": done.stderr[-300:]},
                "e2e_ms": None,
                "metrics": {},
                "evidence_ids": [],
            }
        )
        evaluation = (
            asyncio.run(score(task, private, raw["answer"]))
            if raw.get("answer") is not None
            else None
        )
        result = public_trial(raw, evaluation)
        result["gpu_before"] = before
        result["gpu_after"] = after
        with (public / "trial-outcomes.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, sort_keys=True) + "\n")
        outcomes.append(result)
        print(
            json.dumps(
                {
                    "run_id": run_id,
                    "success": bool(evaluation and evaluation["task_success"]),
                    "error": result["error"],
                }
            ),
            flush=True,
        )
    eligible = all(row["evaluation"] and row["evaluation"]["task_success"] for row in outcomes)
    (public / "replacement-decision.json").write_text(
        json.dumps(
            {"replacement_task_id": REPLACEMENT, "h1_eligible": eligible, "h2_started": False},
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
