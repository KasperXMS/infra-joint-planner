"""Observe native settings, skills and isolation without sending hints to the solver."""
import json
import os
import subprocess
from pathlib import Path

from benchflow.evaluation import Evaluation

root = Path("/root/skillsbench-local-20261013")
job = root / "evidence/agent-smoke-final-contract.yaml"
evaluation = Evaluation.from_yaml(job)
assert evaluation._config.retry.max_retries == 0
env = os.environ.copy()
env.update(DOCKER_HOST=f"unix://{root}/run/docker.sock", DOCKER_CONFIG=str(root / "docker-config"))
docker = str(root / "bin/docker")
ids = subprocess.check_output([docker, "ps", "-q", "--filter", "label=benchflow.owned=true"], env=env, text=True).split()
result = {"rollout_max_retries": evaluation._config.retry.max_retries, "containers": []}
program = """
import hashlib,json,os
from pathlib import Path
p=Path('/home/agent/.openhands/agent_settings.json')
d=json.loads(p.read_text())
skills={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/home/agent/.agents/skills').glob('*/SKILL.md')}
print(json.dumps({'uid':os.getuid(),'llm':{k:d['llm'].get(k) for k in ['temperature','max_input_tokens','max_output_tokens','num_retries']},
'condenser':{k:d.get('condenser',{}).get(k) for k in ['kind','max_tokens','hard_context_reset_max_retries']},
'readable_native_skills':skills,'oracle_exists':Path('/oracle').exists(),
'oracle_readable':os.access('/oracle',os.R_OK|os.X_OK),
'oracle_solve_readable':os.access('/oracle/solve.sh',os.R_OK),
'docker_socket_exists':Path('/var/run/docker.sock').exists()}))
"""
for container in ids:
    details = json.loads(subprocess.check_output([docker, "inspect", container], env=env, text=True))[0]
    project = details["Config"]["Labels"].get("com.docker.compose.project", "")
    if project.startswith("dialogue-parser__"):
        output = subprocess.run([docker, "exec", "--user", "agent", container, "python3", "-c", program],
                                env=env, capture_output=True, text=True, timeout=20)
        result["containers"].append({"project": project, "returncode": output.returncode,
                                     "observation": json.loads(output.stdout) if output.returncode == 0 else output.stderr[-500:],
                                     "mount_targets": [m["Destination"] for m in details.get("Mounts", [])]})
(root / "evidence/native-smoke-contract.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
