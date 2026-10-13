"""One official development task through the supported native-skill ACP harness."""
import json
import os
import subprocess
import time
from pathlib import Path

root = Path("/root/skillsbench-local-20261013")
attempt = "agent-smoke-final-contract"
source = Path("/mnt/d/Codes/infra-aware-mas-new/infra-joint-planner/research/real_benchmark_skills_v1")
task = root / "skillsbench/tasks/dialogue-parser"
token = (root / "private/bridge.key").read_text().strip()
env = os.environ.copy()
env.update(PATH=f"{root}/bin:{root}/venv/bin:" + env["PATH"],
           DOCKER_HOST=f"unix://{root}/run/docker.sock", DOCKER_CONFIG=str(root / "docker-config"),
           OPENAI_API_KEY=token, LLM_API_KEY=token, NO_COLOR="1", TERM="dumb")
job = {"tasks_dir": str(task), "jobs_dir": str(root / "jobs" / attempt), "agent": "openhands",
       "model": "vllm/Qwen3.5-4B", "environment": "docker", "concurrency": 1, "max_retries": 0,
       "skill_mode": "with-skill", "skills_dir": str(task / "environment/skills"),
       "loop_strategy": "single-shot", "agent_idle_timeout": 0,
       "agent_env": {"BENCHFLOW_PROVIDER_BASE_URL": f"http://172.17.0.1:18080/runs/{attempt}/v1"}}
job_path = root / "evidence" / (attempt + ".yaml")
job_path.write_text(json.dumps(job, indent=2) + "\n")
argv = [str(root / "venv/bin/python"), str(source / "bench_with_frozen_openhands.py"),
        "eval", "run", "--config", str(job_path)]
state = {"started_epoch": time.time(), "classification": "infrastructure-smoke, excluded from formal cells",
         "argv": argv, "status": "running"}
receipt = root / "evidence" / (attempt + ".json")
receipt.write_text(json.dumps(state, indent=2) + "\n")
with (root / "logs" / (attempt + ".log")).open("w") as log:
    result = subprocess.run(argv, env=env, cwd=root, stdout=log, stderr=subprocess.STDOUT, timeout=3000)
state.update(returncode=result.returncode, finished_epoch=time.time(), status="finished")
summary = root / "jobs" / attempt / "summary.json"
if summary.exists():
    state["summary"] = json.loads(summary.read_bytes())
receipt.write_text(json.dumps(state, indent=2) + "\n")
print(json.dumps({k: v for k, v in state.items() if k not in ("argv", "summary")}))
