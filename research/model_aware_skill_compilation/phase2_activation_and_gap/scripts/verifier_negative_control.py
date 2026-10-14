"""Check that the unchanged verifier rejects an intentionally incomplete artifact."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

root = Path('/root/skillsbench-local-20261013')
study = Path(__file__).resolve().parents[1]
task = 'financial-analysis-4'
tests = root / 'private/model-aware-phase2/material/tasks/financial-analysis' / task / 'tests'
docker = str(root / 'bin/docker')
env = os.environ.copy()
env['DOCKER_HOST'] = 'unix://' + str(root / 'run/docker.sock')
env['PATH'] = str(root / 'bin') + ':' + env['PATH']
container = 'phase2-negative-control-financial-analysis-4'

def call(*args):
    return subprocess.run([docker, *args], env=env, capture_output=True, text=True, timeout=900)

try:
    p = call('run', '-d', '--name', container, 'phase2-trial-financial-analysis-4:codex-0.162.1', 'sleep', '3600')
    assert p.returncode == 0, p.stderr
    p = call('exec', container, 'sh', '-c', "printf '{}' > /root/answers.json")
    assert p.returncode == 0, p.stderr
    p = call('cp', str(tests), container + ':/tests')
    assert p.returncode == 0, p.stderr
    p = call('exec', container, 'bash', '/tests/test.sh')
    reward = call('exec', container, 'cat', '/logs/verifier/reward.txt')
    assert reward.returncode == 0, reward.stderr
    receipt = {'task_id': task, 'control_artifact_sha256': hashlib.sha256(b'{}').hexdigest(),
               'verifier_exit': p.returncode, 'reward': int(reward.stdout.strip()),
               'expected_control_reward': 0,
               'tests_sha256': {x.name: hashlib.sha256(x.read_bytes()).hexdigest() for x in tests.iterdir() if x.is_file()}}
    (study / 'evidence/verifier-negative-control.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'reward': receipt['reward'], 'expected': 0, 'verifier_exit': p.returncode}))
    assert receipt['reward'] == 0
finally:
    call('rm', '-f', container)
