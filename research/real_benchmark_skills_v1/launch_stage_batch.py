"""Start one already frozen BenchFlow stage in a persistent local session."""
import argparse
import json
import os
import subprocess
import time
from pathlib import Path

root = Path('/root/skillsbench-local-20261013')
source = Path('/mnt/d/Codes/infra-aware-mas-new/infra-joint-planner/research/real_benchmark_skills_v1')
parser = argparse.ArgumentParser()
parser.add_argument('--stage', choices=['development', 'evaluation'], required=True)
parser.add_argument('--model', choices=['Qwen3.5-4B', 'Qwen3.5-9B'], required=True)
args = parser.parse_args()
name = f'{args.stage}-{args.model}'
receipt = root / 'evidence' / f'{name}-batch.json'
if receipt.exists():
    raise RuntimeError('Batch receipt already exists; inspect it instead of relaunching')
log_path = root / 'logs' / f'{name}-batch.log'
argv = [str(root / 'venv/bin/python'), str(source / 'run_stage.py'), '--stage', args.stage, '--model', args.model]
with log_path.open('w') as log:
    process = subprocess.Popen(argv, cwd=root, stdin=subprocess.DEVNULL, stdout=log,
                               stderr=subprocess.STDOUT, start_new_session=True)
record = {'pid': process.pid, 'argv': argv, 'started_epoch': time.time(), 'log': str(log_path),
          'classification': 'formal BenchFlow stage; outcomes only in individual cell records'}
receipt.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
