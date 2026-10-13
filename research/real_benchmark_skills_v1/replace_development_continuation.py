"""Replace only the idle transition watcher after a failed /models preflight."""
import json
import os
import signal
import subprocess
import time
from pathlib import Path

root = Path('/root/skillsbench-local-20261013')
source = Path('/mnt/d/Codes/infra-aware-mas-new/infra-joint-planner/research/real_benchmark_skills_v1')
receipt = root / 'evidence/development-continuation-launch.json'
old = json.loads(receipt.read_bytes())
pid = old['pid']
cmdline = Path(f'/proc/{pid}/cmdline')
if not cmdline.exists() or b'continue_development.py' not in cmdline.read_bytes():
    raise RuntimeError('Original continuation PID is not the expected watcher')
if (root / 'evidence/development-continuation.json').exists():
    raise RuntimeError('Continuation already advanced; do not replace')
if not any((root / 'jobs/development/4b').rglob('cell.json')):
    raise RuntimeError('4B batch has not started')
os.kill(pid, signal.SIGTERM)
for _ in range(50):
    if not cmdline.exists() or not cmdline.read_bytes():
        break
    time.sleep(0.1)
else:
    raise RuntimeError('Original watcher did not stop')
old_path = receipt.with_name('development-continuation-launch.before-api-fix.json')
receipt.rename(old_path)
launched = subprocess.run(['/usr/bin/python3', str(source / 'launch_development_continuation.py')],
                          cwd=root, capture_output=True, text=True)
if launched.returncode:
    raise RuntimeError('Replacement watcher did not start: ' + launched.stderr[-1000:])
new = json.loads(launched.stdout)
record = {'old_pid': pid, 'new_pid': new['pid'], 'epoch': time.time(),
          'reason': 'Transformers serve GET /v1/models returned HTTP 500; transition now verifies /study/status and a real 9B response identity.',
          'effect_on_formal_cells': 'none; 4B BenchFlow runner was neither stopped nor changed'}
(root / 'evidence/transition-check-amendment.json').write_text(json.dumps(record, indent=2) + '\n')
(source / 'transition-check-amendment.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
