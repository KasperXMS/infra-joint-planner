"""Run the unchanged official development oracle in the dedicated Docker sandbox."""
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path("/root/skillsbench-local-20261013")
env = os.environ.copy()
env.update(PATH=f"{ROOT}/bin:{ROOT}/venv/bin:" + env["PATH"],
           DOCKER_HOST=f"unix://{ROOT}/run/docker.sock", DOCKER_CONFIG=str(ROOT / "docker-config"),
           NO_COLOR="1", TERM="dumb")
task = ROOT / "skillsbench/tasks/dialogue-parser"
receipt = {"started_epoch": time.time(), "task": "dialogue-parser", "stage": "infrastructure-smoke"}
for name, argv in (
    ("structural", [str(ROOT / "venv/bin/bench"), "tasks", "check", str(task)]),
    ("oracle", [str(ROOT / "venv/bin/bench"), "eval", "run", "--tasks-dir", str(task),
                "--agent", "oracle", "--sandbox", "docker", "--concurrency", "1",
                "--jobs-dir", str(ROOT / "jobs/oracle-smoke"), "--loop-strategy", "single-shot"]),
):
    with (ROOT / "logs" / f"{name}-smoke.log").open("w") as log:
        result = subprocess.run(argv, env=env, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
    receipt[name] = {"returncode": result.returncode, "argv": argv}
    if result.returncode:
        break
receipt["finished_epoch"] = time.time()
(ROOT / "evidence/oracle-smoke-launch.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
