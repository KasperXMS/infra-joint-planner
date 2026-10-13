"""Read-only check of actual first no-skill solver container."""
import json
import os
import subprocess
from pathlib import Path

root = Path('/root/skillsbench-local-20261013')
env = os.environ.copy()
env.update(PATH=str(root / 'bin') + ':' + env['PATH'],
           DOCKER_HOST='unix://' + str(root / 'run/docker.sock'),
           DOCKER_CONFIG=str(root / 'docker-config'))
containers = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], env=env,
                            capture_output=True, text=True, check=True).stdout.splitlines()
assert len(containers) == 1 and containers[0].startswith('dialogue-parser__'), containers
code = '''import json,os
paths=['/home/agent/.agents/skills','/workspace/.agents/skills','/skills','/app/skills']
print(json.dumps({p:{'exists':os.path.exists(p),'entries':os.listdir(p) if os.path.isdir(p) else []} for p in paths}))'''
result = subprocess.run(['docker', 'exec', '-u', '1000', containers[0], 'python3', '-c', code],
                        env=env, capture_output=True, text=True)
assert result.returncode == 0, result.stderr
observation = json.loads(result.stdout)
assert not any(x['entries'] for x in observation.values()), observation
receipt = {'container': containers[0], 'uid': 1000, 'paths': observation,
           'classification': 'first formal S0 sandbox access observation; no solver task output inspected'}
(root / 'evidence/s0-first-container.json').write_text(json.dumps(receipt, indent=2) + '\n')
destination = Path('/mnt/d/Codes/infra-aware-mas-new/infra-joint-planner/research/real_benchmark_skills_v1/s0-first-container.json')
destination.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
