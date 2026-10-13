"""Keep the checked 4B-to-9B transition alive across terminal sessions."""
import json
import subprocess
import time
from pathlib import Path

root = Path('/root/skillsbench-local-20261013')
source = Path('/mnt/d/Codes/infra-aware-mas-new/infra-joint-planner/research/real_benchmark_skills_v1')
if (root / 'evidence/development-continuation.json').exists():
    raise RuntimeError('Continuation already started')
log_path = root / 'logs/development-continuation.log'
with log_path.open('w') as log:
    process = subprocess.Popen([str(root / 'venv/bin/python'), str(source / 'continue_development.py')],
                               cwd=root, stdin=subprocess.DEVNULL, stdout=log,
                               stderr=subprocess.STDOUT, start_new_session=True)
receipt = {'pid': process.pid, 'epoch': time.time(), 'log': str(log_path)}
(root / 'evidence/development-continuation-launch.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
