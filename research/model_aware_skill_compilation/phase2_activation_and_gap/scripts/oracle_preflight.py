"""Run an isolated, unmodified SkillLearnBench reference solution and verifier.

Run as root in the existing study WSL distro. This is a scoring-chain preflight,
not an Agent trial; the solution is copied only into this disposable container.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path('/root/skillsbench-local-20261013')
SOURCE = Path('/mnt/d/Codes/infra-aware-mas-new/.code-staging/benchmarks/skilllearn')
OUT = Path('/mnt/d/Codes/infra-aware-mas-new/infra-joint-planner/research/model_aware_skill_compilation/phase2_activation_and_gap/evidence')
TASK_ID = sys.argv[1] if len(sys.argv) > 1 else 'earthquake-plate-calculation-3'
FAMILY = TASK_ID.rsplit('-', 1)[0]
TASK = SOURCE / 'tasks' / FAMILY / TASK_ID
IMAGE = 'phase2-skilllearn-' + TASK_ID + ':source-726e1f7'
CONTAINER = 'phase2-oracle-' + TASK_ID


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(relative: str) -> bytes:
    p = subprocess.run(['git', '-c', f'safe.directory={SOURCE}', '-C', str(SOURCE),
                        'show', 'HEAD:' + relative], capture_output=True, check=True)
    return p.stdout


def run(argv: list[str], *, timeout: int, **kwargs) -> subprocess.CompletedProcess:
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, **kwargs)
    return result


def main() -> None:
    assert os.geteuid() == 0
    assert TASK.is_dir()
    OUT.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(PATH=str(ROOT / 'bin') + ':' + env['PATH'],
               DOCKER_HOST='unix://' + str(ROOT / 'run/docker.sock'),
               DOCKER_CONFIG=str(ROOT / 'docker-config'))
    docker = str(ROOT / 'bin/docker')
    info = run([docker, 'info', '--format', '{{.DockerRootDir}}'], timeout=10, env=env)
    assert info.returncode == 0 and info.stdout.strip() == str(ROOT / 'docker-volume/data')
    receipt = {'task_id': TASK_ID, 'source_commit': '726e1f79b96b0cb3d729d0e55a1c847e0b5353ae',
               'dockerfile_sha256': digest(TASK / 'environment/Dockerfile'),
               'solution_sha256': digest(TASK / 'solution/solve.sh'),
               'verifier_sha256': digest(TASK / 'tests/test_outputs.py'),
               'test_sh_sha256': digest(TASK / 'tests/test.sh'),
               'started_epoch': time.time(), 'stages': {}}
    with tempfile.TemporaryDirectory(prefix='phase2-oracle-', dir=ROOT) as tmp:
        context = Path(tmp) / 'context'
        shutil.copytree(TASK / 'environment', context)
        (context / 'skills').mkdir(exist_ok=True)
        solution = Path(tmp) / 'solve.sh'
        tests = Path(tmp) / 'tests'
        shutil.copytree(TASK / 'tests', tests)
        solution_bytes = git_blob(f'tasks/{FAMILY}/{TASK_ID}/solution/solve.sh')
        verifier_shell_bytes = git_blob(f'tasks/{FAMILY}/{TASK_ID}/tests/test.sh')
        solution.write_bytes(solution_bytes)
        (tests / 'test.sh').write_bytes(verifier_shell_bytes)
        receipt['transport'] = {'solution_copied_sha256': hashlib.sha256(solution_bytes).hexdigest(),
                                'test_sh_copied_sha256': hashlib.sha256(verifier_shell_bytes).hexdigest()}
        try:
            for name, argv, timeout in [
                ('build', [docker, 'build', '-t', IMAGE, str(context)], 900),
                ('create', [docker, 'run', '-d', '--name', CONTAINER, IMAGE, 'sleep', 'infinity'], 30),
                ('copy-solution', [docker, 'cp', str(solution), CONTAINER + ':/tmp/solve.sh'], 30),
                ('copy-tests', [docker, 'cp', str(tests), CONTAINER + ':/tests'], 30),
                ('make-logs', [docker, 'exec', CONTAINER, 'mkdir', '-p', '/logs/verifier'], 30),
                ('solve', [docker, 'exec', CONTAINER, 'bash', '/tmp/solve.sh'], 120),
                ('verify', [docker, 'exec', CONTAINER, 'bash', '/tests/test.sh'], 600),
                ('reward', [docker, 'exec', CONTAINER, 'cat', '/logs/verifier/reward.txt'], 30),
            ]:
                print(name, flush=True)
                result = run(argv, timeout=timeout, env=env)
                receipt['stages'][name] = {'exit': result.returncode,
                                           'stdout_tail': result.stdout[-3000:],
                                           'stderr_tail': result.stderr[-3000:]}
                (OUT / f'skilllearn-oracle-{TASK_ID}.json').write_text(
                    json.dumps(receipt, indent=2) + '\n')
                if result.returncode != 0:
                    raise RuntimeError(name + ' failed')
        finally:
            run([docker, 'rm', '-f', CONTAINER], timeout=30, env=env)
    receipt['finished_epoch'] = time.time()
    (OUT / f'skilllearn-oracle-{TASK_ID}.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'task_id': TASK_ID, 'reward': receipt['stages']['reward']['stdout_tail'].strip(),
                      'receipt': str(OUT / f'skilllearn-oracle-{TASK_ID}.json')}))


if __name__ == '__main__':
    main()
