"""Frozen bounded H1/H2 orchestrator; Planner runs only in isolated Controller."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any

from infra_joint.benchmarks.multihop_rag import MultiHopOfficialTokenOverlapEvaluator
from infra_joint.benchmarks.multimodalqa import MultiModalQAOfficialEvaluator
from infra_joint.core.task import OutputContract, OutputFormat, TaskContract

MODEL = "qwen35-27b-resident-32k-v1:latest"
TASKS = ("multihop:a647807d9a1d0efd", "mmqa:0ed625390ca7f919b46fd99fe85d80b5")
H1_ORDER = ((0, "G0", "Hfast"), (1, "G1", "Hfast"), (0, "G1", "Hfast"), (1, "G0", "Hfast"))
H2_ORDER = (
    (0, "G1", "Hslow"),
    (1, "G0", "Hslow"),
    (0, "G0", "Hslow"),
    (1, "G1", "Hslow"),
    (0, "G1", "Hfast"),
    (1, "G0", "Hfast"),
    (0, "G0", "Hfast"),
    (1, "G1", "Hfast"),
    (0, "G0", "Hslow"),
    (1, "G1", "Hslow"),
    (0, "G1", "Hslow"),
    (1, "G0", "Hslow"),
)


def rows(path: Path) -> dict[str, dict[str, Any]]:
    return {
        row["task_id"]: row for row in (json.loads(line) for line in path.read_text().splitlines())
    }


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gpu_sample() -> list[dict[str, int]] | None:
    done = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,utilization.gpu,memory.used",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if done.returncode:
        return None
    try:
        return [
            {
                "index": int(parts[0]),
                "utilization_pct": int(parts[1]),
                "memory_used_mib": int(parts[2]),
            }
            for parts in (line.split(",") for line in done.stdout.splitlines())
        ]
    except (ValueError, IndexError):
        return None


def probe_model() -> list[dict[str, Any]]:
    observations = []
    for _ in range(2):
        body = json.dumps(
            {
                "model": MODEL,
                "messages": [{"role": "user", "content": "Return READY."}],
                "temperature": 0,
                "think": False,
                "stream": False,
                "options": {"num_predict": 8, "temperature": 0},
            }
        ).encode()
        request = urllib.request.Request(
            "http://127.0.0.1:11436/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        started = time.perf_counter()
        with urllib.request.urlopen(request, timeout=300) as response:
            data = json.loads(response.read())
        observations.append(
            {
                "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                "model": data.get("model"),
                "usage": {
                    "prompt_tokens": data.get("prompt_eval_count"),
                    "completion_tokens": data.get("eval_count"),
                },
                "queue_ms": None,
                "cache_state": "unknown",
            }
        )
    return observations


async def score(task: dict[str, Any], private: dict[str, Any], answer: str) -> dict[str, Any]:
    case = TaskContract(
        task_id=task["task_id"],
        benchmark_id=task["benchmark"],
        objective=task["question"],
        artifacts=(),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
        evaluator_id=private["evaluator_ref"],
    )
    if task["benchmark"] == "MultiHop-RAG":
        evaluator = MultiHopOfficialTokenOverlapEvaluator(private["answer"])
    else:
        evaluator = MultiModalQAOfficialEvaluator(
            tuple(str(item["answer"]) for item in private["answers"])
        )
    result = await evaluator.evaluate(case, answer)
    return {
        "format_valid": result.format_valid,
        "benchmark_score": result.benchmark_score,
        "task_success": bool(result.format_valid and result.benchmark_score == 1.0),
    }


def public_trial(raw: dict[str, Any], evaluation: dict[str, Any] | None) -> dict[str, Any]:
    metrics = raw.get("metrics", {})
    actions = metrics.get("source_actions", [])
    transfers = metrics.get("transfers", [])
    service = metrics.get("model") or {}
    return {
        "run_id": raw["run_id"],
        "task_id": raw["task_id"],
        "workflow": raw["workflow"],
        "profile": raw["profile"],
        "completion": raw.get("answer") is not None,
        "evaluation": evaluation,
        "error": raw.get("error"),
        "e2e_ms": raw.get("e2e_ms"),
        "source_action_count": len(actions),
        "source_local_rpc_ms": round(sum(item["ms"] for item in actions), 3),
        "transfer_count": len(transfers),
        "a4_to_a5_bytes": sum(item["bytes"] for item in transfers),
        "a4_to_a5_ms": round(sum(item["ms"] for item in transfers), 3),
        "a5_to_controller_response_bytes": sum(
            item["response_bytes"] for item in actions if item["node"] == "source-b"
        ),
        "acquired_original_count": metrics.get("acquired_original_count"),
        "final_evidence_count": len(raw.get("evidence_ids", [])),
        "context_tokens": metrics.get("context_tokens"),
        "model_usage": service.get("usage"),
        "model_latency_ms": service.get("provider_latency_ms"),
        "model_queue_ms": service.get("queue_ms"),
        "cache_state": service.get("cache_state", "unknown"),
        "cleanup_count": len(metrics.get("cleanup", [])),
        "cleanup_ok": all(item["status"] in (200, 204) for item in metrics.get("cleanup", [])),
        "api_usd": None,
        "gpu_usd": None,
        "study_max_model_concurrency": 2,
        "raw_evidence_ref": "machine-local:controller/out/" + raw["run_id"] + ".json",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--model-blob", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    study = root / "controller" / "study"
    out = root / "controller" / "out"
    public = root / "public"
    public.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = public / "frozen-experiment-manifest.json"
    trials_path = public / "trial-outcomes.jsonl"
    if manifest_path.exists() or trials_path.exists():
        raise FileExistsError("Experiment namespace already has frozen results")
    task_rows = rows(study / "task-candidates.jsonl")
    private_rows = rows(
        Path("/home/super/xiaoming/infra-evaluation-workload-v0.1/private/evaluator-private.jsonl")
    )
    for task_id in TASKS:
        if task_id not in task_rows or task_id not in private_rows:
            raise RuntimeError("Frozen task/evaluator unavailable")
    observations = probe_model()
    if any(row["model"] != MODEL for row in observations):
        raise RuntimeError("Ollama model identity mismatch")
    blob = args.model_blob.resolve()
    if not blob.is_file() or not blob.name.startswith("sha256-"):
        raise RuntimeError("Frozen GGUF blob unavailable")
    frozen = {
        "schema_version": "infra-hypothesis-feasibility-v1",
        "parent_commit": "8c5bcce",
        "created_unix": time.time(),
        "task_ids": TASKS,
        "h1_order": H1_ORDER,
        "h2_conditional_order": H2_ORDER,
        "model": {
            "served_name": MODEL,
            "gguf_blob": blob.name,
            "backend": "ollama 0.34.0 / llama-server",
            "quantization": "Q4_K_M",
            "max_model_len": 32768,
            "gpu": "workstation GPU0 RTX 4090",
        },
        "network": {
            "Hslow": {"bandwidth_mbps": 3, "extra_rtt_ms": 50, "proxy_port": 63205},
            "Hfast": {"bandwidth_mbps": 100, "extra_rtt_ms": 5, "proxy_port": 63206},
        },
        "sha256": {
            name: sha(study / name)
            for name in (
                "task-candidates.jsonl",
                "source-residency.jsonl",
                "run_hypothesis_cell_v1.py",
            )
        },
        "service_probes": observations,
        "quality_success_rule": "format_valid and native_score == 1.0",
    }
    manifest_path.write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n")

    def run_cell(index: int, task_index: int, workflow: str, profile: str) -> dict[str, Any]:
        task_id = TASKS[task_index]
        run_id = f"h{index:02d}-{task_index}-{workflow.lower()}-{profile.lower()}"
        command = [
            "bash",
            str(root / "run_isolated_hypothesis_controller_v1.sh"),
            str(root / "controller"),
            run_id,
            "run_hypothesis_cell_v1.py",
            "--task-id",
            task_id,
            "--workflow",
            workflow,
            "--profile",
            profile,
        ]
        before_gpu = gpu_sample()
        done = subprocess.run(command, capture_output=True, text=True, timeout=3600, check=False)
        after_gpu = gpu_sample()
        raw_path = out / (run_id + ".json")
        if raw_path.exists():
            raw = json.loads(raw_path.read_text())
        else:
            raw = {
                "run_id": run_id,
                "task_id": task_id,
                "workflow": workflow,
                "profile": profile,
                "answer": None,
                "error": {"type": "controller_exit", "message": done.stderr[-300:]},
                "e2e_ms": None,
                "metrics": {},
                "evidence_ids": [],
            }
        evaluation = None
        if raw.get("answer") is not None:
            evaluation = asyncio.run(
                score(task_rows[task_id], private_rows[task_id], raw["answer"])
            )
        result = public_trial(raw, evaluation)
        result["gpu_before"] = before_gpu
        result["gpu_after"] = after_gpu
        with trials_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, sort_keys=True) + "\n")
        print(
            json.dumps(
                {
                    "run_id": run_id,
                    "success": bool(evaluation and evaluation["task_success"]),
                    "e2e_ms": result["e2e_ms"],
                }
            ),
            flush=True,
        )
        return result

    h1 = [run_cell(index, *condition) for index, condition in enumerate(H1_ORDER, start=1)]
    eligible = {
        task_id
        for task_id in TASKS
        if all(
            any(
                row["task_id"] == task_id
                and row["workflow"] == workflow
                and row["evaluation"]
                and row["evaluation"]["task_success"]
                for row in h1
            )
            for workflow in ("G0", "G1")
        )
    }
    decision = {
        "p1": "Go",
        "h1_eligible_tasks": sorted(eligible),
        "h2_started": bool(eligible),
        "completed_unix": None,
    }
    if eligible:
        for index, (task_index, workflow, profile) in enumerate(H2_ORDER, start=5):
            if TASKS[task_index] in eligible:
                run_cell(index, task_index, workflow, profile)
    decision["completed_unix"] = time.time()
    (public / "execution-decision.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n"
    )


if __name__ == "__main__":
    main()
