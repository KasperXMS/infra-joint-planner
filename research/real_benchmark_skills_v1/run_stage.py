"""Run frozen paired cells through official BenchFlow; never retry a scored cell.

Run explicitly after the real agent smoke and configuration freeze. Each cell
gets a private request-capture namespace and an immutable output directory.
"""
import argparse
import hashlib
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path("/root/skillsbench-local-20261013")
SOURCE = Path("/mnt/d/Codes/infra-aware-mas-new/infra-joint-planner/research/real_benchmark_skills_v1")


def wait_for_idle(run_id, token):
    """Drain cancelled native generation before another task can use the GPU."""
    started = time.time()
    observations = []
    while True:
        request = urllib.request.Request(
            f"http://172.17.0.1:18080/runs/{run_id}/v1/study_status",
            headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(request, timeout=30) as response:
            status = json.load(response)
        observations.append({"epoch": time.time(), **status})
        if status["pending_requests"] == status["running_generations"] == 0:
            return {"seconds": time.time() - started, "observations": observations}
        if time.time() - started > 600:
            raise RuntimeError("Native generation did not drain; preserve batch for audit")
        time.sleep(5)


def main(stage, model):
    config_path = ROOT / "evidence/run-config.frozen.json"
    if not config_path.exists():
        raise RuntimeError("Freeze configuration after smoke before launching batches")
    frozen = json.loads(config_path.read_bytes())
    if frozen.get("real_agent_smoke_passed") is not True:
        raise RuntimeError("Real agent smoke has not passed")
    selection = json.loads((SOURCE / "task-selection.lock.json").read_bytes())
    tasks = [t for t in selection["tasks"] if t["split"] == stage]
    expected = 8 if stage == "development" else 16
    if len(tasks) != expected:
        raise RuntimeError("Unexpected split size")
    if stage == "evaluation" and not (ROOT / "evidence/development-analysis.frozen.json").exists():
        raise RuntimeError("Development analysis/method freeze must precede held-out runs")
    for name, digest in frozen["runner_source_sha256"].items():
        if hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError("Runner changed after freeze: " + name)
    token = (ROOT / "private/bridge.key").read_text().strip()
    env = os.environ.copy()
    env.update(PATH=f"{ROOT}/bin:{ROOT}/venv/bin:" + env["PATH"],
               DOCKER_HOST=f"unix://{ROOT}/run/docker.sock", DOCKER_CONFIG=str(ROOT / "docker-config"),
               OPENAI_API_KEY=token, LLM_API_KEY=token, NO_COLOR="1", TERM="dumb")
    size = "4b" if model.endswith("4B") else "9b"
    batch_root = ROOT / "jobs" / stage / size
    batch_root.mkdir(parents=True, exist_ok=True)
    wait_for_idle(f"{stage}-{size}-preflight", token)
    # Conservative initial policy: one sandbox at a time; the model remains
    # loaded for the whole stage. Freeze any batching change before outcomes.
    for index, task in enumerate(tasks):
        task_root = ROOT / "skillsbench/tasks" / task["id"]
        for relative, digest in task["files_sha256"].items():
            if hashlib.sha256((task_root / relative).read_bytes()).hexdigest() != digest:
                raise RuntimeError("Official source changed: " + task["id"] + "/" + relative)
        conditions = ["s0", "s1"] if index % 2 == 0 else ["s1", "s0"]
        for condition in conditions:
            run_id = f"{stage}-{size}-{task['id']}-{condition}-t1"
            cell_root = batch_root / run_id
            if cell_root.exists():
                if (cell_root / "cell.json").exists():
                    prior = json.loads((cell_root / "cell.json").read_bytes())
                    if prior.get("status") == "completed":
                        continue
                raise RuntimeError("Existing incomplete cell requires explicit infrastructure audit: " + run_id)
            cell_root.mkdir()
            mode = "no-skill" if condition == "s0" else "with-skill"
            job_config = {"tasks_dir": str(task_root), "jobs_dir": str(cell_root / "bench"),
                          "agent": "openhands", "model": "vllm/" + model, "environment": "docker",
                          "concurrency": 1, "max_retries": 0, "skill_mode": mode,
                          "loop_strategy": "single-shot", "agent_idle_timeout": 0,
                          "agent_env": {"BENCHFLOW_PROVIDER_BASE_URL": f"http://172.17.0.1:18080/runs/{run_id}/v1"}}
            if condition == "s1":
                job_config["skills_dir"] = str(task_root / "environment/skills")
            config_path = cell_root / "job.yaml"
            config_path.write_text(json.dumps(job_config, indent=2) + "\n")
            argv = [str(ROOT / "venv/bin/python"), str(SOURCE / "bench_with_frozen_openhands.py"),
                    "eval", "run", "--config", str(config_path)]
            record = {"run_id": run_id, "stage": stage, "model": model, "condition": condition,
                      "task_id": task["id"], "started_epoch": time.time(), "argv": argv, "status": "running"}
            path = cell_root / "cell.json"
            path.write_text(json.dumps(record, indent=2) + "\n")
            with (cell_root / "runner.log").open("w") as log:
                result = subprocess.run(argv, env=env, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            summaries = list((cell_root / "bench").glob("summary.json"))
            record.update(returncode=result.returncode, finished_epoch=time.time())
            if not summaries:
                record["status"] = "infrastructure_fault"
                path.write_text(json.dumps(record, indent=2) + "\n")
                raise RuntimeError("Missing official summary; stopping affected batch: " + run_id)
            summary = json.loads(summaries[0].read_bytes())
            record.update(status="scored", official_summary=summary)
            path.write_text(json.dumps(record, indent=2) + "\n")
            record["generation_drain"] = wait_for_idle(run_id, token)
            record.update(status="completed", quiescent_epoch=time.time())
            path.write_text(json.dumps(record, indent=2) + "\n")
            print(json.dumps({"run_id": run_id, "passed": summary["passed"], "errored": summary["errored"]}), flush=True)
            # Ordinary model failures continue; evaluator/environment faults stop.
            if summary.get("verifier_errored", 0) or summary.get("errored", 0):
                raise RuntimeError("Audit error category before continuing: " + run_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["development", "evaluation"], required=True)
    parser.add_argument("--model", choices=["Qwen3.5-4B", "Qwen3.5-9B"], required=True)
    args = parser.parse_args()
    main(args.stage, args.model)
