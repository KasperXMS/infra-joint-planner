"""When the complete 4B development batch finishes, run the frozen 9B batch.

This orchestration does not edit task files, scored cells, model settings, or
the frozen runner. An incomplete 4B batch stops the continuation for audit.
"""
import json
import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path

import paramiko

root = Path('/root/skillsbench-local-20261013')
source = Path('/mnt/d/Codes/infra-aware-mas-new/infra-joint-planner/research/real_benchmark_skills_v1')
receipt = root / 'evidence/development-continuation.json'
if receipt.exists():
    raise RuntimeError('Continuation already launched')


def save(state, **values):
    record = {'state': state, 'epoch': time.time(), **values}
    receipt.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record), flush=True)


def live_command(pid):
    path = Path(f'/proc/{pid}/cmdline')
    return path.read_bytes() if path.exists() else b''


def api(route):
    key = (root / 'private/bridge.key').read_text().strip()
    url = 'http://172.17.0.1:18080/runs/development-transition/v1/' + route
    request = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + key})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


try:
    prior = json.loads((root / 'evidence/development-Qwen3.5-4B-batch.json').read_bytes())
    while live_command(prior['pid']):
        if b'run_stage.py' not in live_command(prior['pid']):
            raise RuntimeError('Batch PID now belongs to an unexpected process')
        time.sleep(30)
    cells = [json.loads(p.read_bytes()) for p in (root / 'jobs/development/4b').rglob('cell.json')]
    if len(cells) != 16 or any(c.get('status') != 'completed' for c in cells):
        raise RuntimeError(f'4B batch is incomplete: {len(cells)}/16 records, '
                           f'{sum(c.get("status") == "completed" for c in cells)} complete')
    status = api('study_status')
    if status['pending_requests'] or status['running_generations']:
        raise RuntimeError('4B service was not idle after the batch')
    save('switching_to_9b', four_b_cells=16)
    private = Path('/mnt/d/Codes/infra-aware-mas-new/device_info.txt').read_text(encoding='utf-8-sig')
    target = re.search(r'ssh[^\r\n]*root@connect\.westd\.seetacloud\.com[^\r\n]*', private)
    if target is None:
        raise RuntimeError('Configured AutoDL host not found')
    password = re.search(r'(?:password|passwd|密码|口令)\s*[:：=]\s*[`\x27\x22]?([^\s`\x27\x22]+)', private[target.start():], re.I)
    if password is None:
        raise RuntimeError('Configured AutoDL credential not found')
    client = paramiko.SSHClient()
    client.load_host_keys('/mnt/c/Users/38058/.ssh/known_hosts')
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect('connect.westd.seetacloud.com', port=39059, username='root',
                   password=password.group(1), look_for_keys=False, allow_agent=False,
                   timeout=20, auth_timeout=20, banner_timeout=20)
    command = ('/root/miniconda3/bin/python '
               '/root/autodl-tmp/real-benchmark-skills-v1/switch_guarded_model.py '
               '--model Qwen3.5-9B')
    _, stdout, stderr = client.exec_command(command, timeout=30)
    output = stdout.read().decode()
    error = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    client.close()
    if code != 0:
        raise RuntimeError('Owned service switch failed: ' + error[-1000:])
    switch = json.loads(output)
    deadline = time.time() + 240
    while time.time() < deadline:
        try:
            models = api('models')
            status = api('study_status')
            if any('Qwen3.5-9B' in m.get('id', '') for m in models.get('data', [])) and not status['pending_requests']:
                break
        except Exception:
            pass
        time.sleep(5)
    else:
        raise RuntimeError('9B API did not become ready within 240 seconds')
    save('launching_9b', service_pid=switch['pid'], service_source_sha256=switch['service_source_sha256'])
    result = subprocess.run(['/usr/bin/python3', str(source / 'launch_stage_batch.py'),
                             '--stage', 'development', '--model', 'Qwen3.5-9B'],
                            cwd=root, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('9B launch failed: ' + result.stderr[-1000:])
    launched = json.loads(result.stdout)
    save('launched_9b', service_pid=switch['pid'], runner_pid=launched['pid'], four_b_cells=16)
except Exception as exc:
    save('stopped_for_audit', error_type=type(exc).__name__, error=str(exc)[-1500:])
    raise
