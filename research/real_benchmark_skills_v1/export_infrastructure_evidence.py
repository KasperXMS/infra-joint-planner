"""Publish only non-sensitive infrastructure facts, never raw trajectories."""
import hashlib
import json
import shutil
from pathlib import Path

root = Path("/root/skillsbench-local-20261013")
destination = Path("/mnt/d/Codes/infra-aware-mas-new/infra-joint-planner/research/real_benchmark_skills_v1")
docker = json.loads((root / "evidence/docker-bootstrap.json").read_bytes())
oracle = json.loads((root / "jobs/oracle-smoke/summary.json").read_bytes())
tooling = json.loads((root / "evidence/tooling.json").read_bytes())
public = {"classification": "infrastructure_smoke_only", "official_agent_runs": 0,
    "autodl_local_docker": {"available": False, "namespace_checks": "EPERM", "sys_admin_capability": False},
    "sandbox_location": "local Ubuntu-22.04 WSL2", "inference_location": "existing AutoDL instance",
    "docker": {"status": docker["status"], "server_version": docker["info"]["ServerVersion"],
               "engine_archive": docker["docker"], "compose_binary": docker["compose"],
               "cgroup_version": docker["info"].get("CgroupVersion"),
               "security_options": docker["info"].get("SecurityOptions"),
               "hello_world_returncode": docker["hello_world"]["returncode"]},
    "tooling": tooling,
    "oracle": {"task": "dialogue-parser", "agent": "oracle", "passed": oracle["passed"],
               "total": oracle["total"], "errored": oracle["errored"], "elapsed_sec": oracle["elapsed_sec"],
               "reward": 1.0, "original_summary_sha256": hashlib.sha256((root / "jobs/oracle-smoke/summary.json").read_bytes()).hexdigest()},
    "rental_cny_per_hour": 7.35,
    "warning": "Oracle pass is not a model outcome. Runtime feasibility of the other selected tasks remains pending."}
(destination / "infrastructure-smoke.json").write_text(json.dumps(public, indent=2) + "\n")
shutil.copy2(root / "requirements.lock.txt", destination / "requirements-benchflow.lock.txt")
print(json.dumps({"exported": ["infrastructure-smoke.json", "requirements-benchflow.lock.txt"]}))
