"""Start the owned private backup monitor once."""
import json
import subprocess
from pathlib import Path

root = Path('/root/skillsbench-local-20261013')
source = Path('/mnt/d/Codes/infra-aware-mas-new/infra-joint-planner/research/real_benchmark_skills_v1')
receipt = root / 'evidence/private-backup-monitor.json'
if receipt.exists():
    pid = json.loads(receipt.read_bytes())['pid']
    command = Path(f'/proc/{pid}/cmdline')
    if command.exists() and b'private_backup_monitor.py' in command.read_bytes():
        raise RuntimeError('Backup monitor already running')
with (root / 'logs/private-backup-monitor.stderr').open('a') as stderr:
    process = subprocess.Popen(['/usr/bin/python3', str(source / 'private_backup_monitor.py')],
                               cwd=root, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=stderr, start_new_session=True)
print(json.dumps({'pid': process.pid, 'receipt': str(receipt)}))
