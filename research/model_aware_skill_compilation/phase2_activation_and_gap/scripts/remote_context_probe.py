"""Non-task 32K serving probe on the existing GPU; restore the frozen 16K service."""
import json
import os
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

root = Path('/root/autodl-tmp')
study = root / 'model-aware-skill-compilation'
launch_path = study / 'vllm_qwen35_9b_launch.json'
out_path = study / 'phase2_32k_runtime_probe.json'
original = json.loads(launch_path.read_text())
argv = original['argv']
assert argv[argv.index('--max-model-len') + 1] == '16384'
assert argv[argv.index('--port') + 1] == '18081'
original_pid = original['pid']
cmdline = Path(f'/proc/{original_pid}/cmdline')
assert cmdline.exists() and b'Qwen3.5-9B' in cmdline.read_bytes()
assert os.getpgid(original_pid) == original_pid

envdir = root / 'envs/inference'
site = envdir / 'lib/python3.12/site-packages'
env = os.environ.copy()
env.update(CUDA_VISIBLE_DEVICES='0',
           LD_LIBRARY_PATH=':'.join((str(site / 'nvidia/cu13/lib'),
                                      str(site / 'torch/lib'), env.get('LD_LIBRARY_PATH', ''))),
           HF_HOME=str(root / 'cache/huggingface'),
           XDG_CACHE_HOME=str(root / 'cache/xdg'),
           VLLM_CONFIG_ROOT=str(study / 'vllm-config'))
result = {'condition': 'non-task-serving-stability',
          'original_max_model_len': 16384, 'probe_max_model_len': 32768,
          'model': 'Qwen3.5-9B BF16', 'backend': 'vLLM 0.31.0',
          'gpu': 0, 'started_epoch': time.time(), 'original_pid': original_pid}


def health(port):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=2) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def stop_group(pid):
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    for _ in range(30):
        status = Path(f'/proc/{pid}/status')
        if not status.exists() or 'State:\tZ' in status.read_text():
            return
        time.sleep(1)
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def start_service(command, logfile):
    with logfile.open('ab') as log:
        return subprocess.Popen(command, env=env, cwd=str(study),
                                stdin=subprocess.DEVNULL, stdout=log,
                                stderr=subprocess.STDOUT, start_new_session=True)


assert health(18081), 'The frozen 16K service must be healthy before the probe'
probe = None
restored = None
try:
    stop_group(original_pid)
    for _ in range(30):
        if not health(18081):
            break
        time.sleep(1)
    time.sleep(8)
    probe_argv = list(argv)
    probe_argv[probe_argv.index('--max-model-len') + 1] = '32768'
    probe_argv[probe_argv.index('--port') + 1] = '18083'
    probe = start_service(probe_argv, study / 'phase2_32k_runtime_probe.log')
    result['probe_pid'] = probe.pid
    for tick in range(240):
        if health(18083):
            break
        if probe.poll() is not None:
            result['startup_exit'] = probe.returncode
            break
        if tick % 20 == 0:
            print(json.dumps({'stage': '32k_starting', 'seconds': tick}), flush=True)
        time.sleep(1)
    result['probe_healthy'] = health(18083)
    if result['probe_healthy']:
        # Repeated common text crosses the old 16K limit; report server token usage.
        body = json.dumps({'model': 'Qwen3.5-9B',
                           'input': [{'role': 'user',
                                      'content': 'Context test only. ' + (' hello' * 18000)
                                      + '\nReply with OK.'}],
                           'max_output_tokens': 16, 'temperature': 0}).encode()
        request = urllib.request.Request('http://127.0.0.1:18083/v1/responses',
                                         data=body, headers={'Content-Type': 'application/json'})
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                parsed = json.load(response)
                result['request_status'] = response.status
                result['usage'] = parsed.get('usage')
        except urllib.error.HTTPError as exc:
            result['request_status'] = exc.code
            result['request_error_tail'] = exc.read(1500).decode(errors='replace')
        except Exception as exc:
            result['request_error'] = repr(exc)
        result['request_seconds'] = time.time() - started
finally:
    if probe is not None:
        stop_group(probe.pid)
    time.sleep(8)
    restored = start_service(argv, study / 'vllm_qwen35_9b.log')
    launch_path.write_text(json.dumps({**original, 'pid': restored.pid}, indent=2) + '\n')
    result['restored_pid'] = restored.pid
    for tick in range(240):
        if health(18081):
            break
        if restored.poll() is not None:
            result['restore_exit'] = restored.returncode
            break
        if tick % 20 == 0:
            print(json.dumps({'stage': '16k_restoring', 'seconds': tick}), flush=True)
        time.sleep(1)
    result['restored_healthy'] = health(18081)
    result['finished_epoch'] = time.time()
    out_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)
