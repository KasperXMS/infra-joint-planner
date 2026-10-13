"""Periodically save only completed benchmark cells to the private local copy."""
import json
import os
import subprocess
import time
from pathlib import Path

root = Path('/root/skillsbench-local-20261013')
source = Path('/mnt/d/Codes/infra-aware-mas-new/infra-joint-planner/research/real_benchmark_skills_v1')
log = root / 'logs/private-backup-monitor.jsonl'
receipt = root / 'evidence/private-backup-monitor.json'
receipt.write_text(json.dumps({'pid': os.getpid(), 'started_epoch': time.time(),
                               'source': str(source / 'backup_completed_cells.py'),
                               'period_seconds': 180}, indent=2) + '\n')
while True:
    for stage in ('development', 'evaluation'):
        if not (root / 'jobs' / stage).exists():
            continue
        result = subprocess.run(['/usr/bin/python3', str(source / 'backup_completed_cells.py'), '--stage', stage],
                                cwd=root, capture_output=True, text=True, timeout=300)
        record = {'epoch': time.time(), 'stage': stage, 'returncode': result.returncode,
                  'output': result.stdout[-3000:], 'error': result.stderr[-1200:]}
        with log.open('a') as stream:
            stream.write(json.dumps(record) + '\n')
    time.sleep(180)
