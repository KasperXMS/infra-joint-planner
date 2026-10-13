"""Freeze checked infrastructure before the first formal development outcome."""
import hashlib
import json
import shutil
import tempfile
import time
from pathlib import Path

from benchflow.skill_policy import strip_task_bundled_skills

root = Path('/root/skillsbench-local-20261013')
source = Path('/mnt/d/Codes/infra-aware-mas-new/infra-joint-planner/research/real_benchmark_skills_v1')
evidence = root / 'evidence'
target = evidence / 'run-config.frozen.json'
if target.exists() or (root / 'jobs/development').exists():
    raise RuntimeError('Refuse to replace an existing freeze or freeze after development starts')
remote = json.loads(Path('/mnt/d/Codes/infra-aware-mas-new/.code-staging/remote-service-audit.json').read_bytes())
api = json.loads((evidence / 'final-api-contract.json').read_bytes())
native = json.loads((evidence / 'native-smoke-contract.json').read_bytes())
smoke = json.loads((root / 'jobs/agent-smoke-final-contract/summary.json').read_bytes())
reward = next((root / 'jobs/agent-smoke-final-contract').rglob('reward.txt')).read_text().strip()
assert api['status'] == 'pass' and smoke['total'] == 1 and smoke['errored'] == smoke['verifier_errored'] == 0
assert remote['idle_status']['pending_requests'] == remote['idle_status']['running_generations'] == 0
assert remote['source_sha256'] == hashlib.sha256((source / 'guarded_transformers_server.py').read_bytes()).hexdigest()
assert remote['verified_model_files'] == 26
observation = native['containers'][0]['observation']
assert observation['uid'] == 1000 and observation['readable_native_skills']
assert not observation['oracle_readable'] and not observation['oracle_solve_readable'] and not observation['docker_socket_exists']
assert native['rollout_max_retries'] == 0
with tempfile.TemporaryDirectory(prefix='s0-policy-', dir=root / 'private') as directory:
    copy = Path(directory) / 'dialogue-parser'
    shutil.copytree(root / 'skillsbench/tasks/dialogue-parser', copy)
    strip_task_bundled_skills(copy)
    assert not (copy / 'environment/skills').exists()
    s0 = {'native_copy_policy_checked': True, 'bundled_skill_directory_absent': True,
          'actual_container_observation': 'required on first formal S0 cell'}
names = ['run_stage.py', 'bench_with_frozen_openhands.py', 'model_bridge.py',
         'qwen3_coder_arguments.py', 'qwen3_coder_parameter_decoder.py',
         'guarded_transformers_server.py', 'switch_guarded_model.py',
         'task-selection.lock.json', 'models.lock.json']
frozen = {'frozen_epoch': time.time(), 'classification': 'before formal development outcomes',
    'real_agent_smoke_passed': True, 'smoke_gate_definition': 'operational tools/skills/artifacts/original verifier, not model task success',
    'smoke': {'official_summary': smoke, 'fractional_reward': reward, 'excluded_from_all_formal_denominators': True,
              'argument_typing_added_after_smoke': True},
    'api_contract': api, 'native_contract': native, 's0_contract': s0,
    'model_backend': 'official Transformers serve 5.19.0', 'remote_service_audit': remote,
    'precision': 'BF16', 'context': 32768, 'output_budget': 4096, 'temperature': 0,
    'thinking': False, 'seed': 42, 'attention': 'sdpa', 'continuous_batching': False,
    'concurrency': 1, 'trials_per_cell': 1, 'task_retries': 0, 'llm_retries': 0,
    'native_condenser': {'max_tokens': 20000, 'max_size': 240, 'keep_first': 2, 'hard_context_reset_max_retries': 1, 'same_model': True},
    'parameter_decoder': 'unchanged official vLLM v0.20.2 Qwen3Coder scalar conversion; all conversions logged',
    'guided_decoding': False, 'stops': 'original model EOS plus tokenizer chat EOS',
    'provider_namespace_note': 'BenchFlow model vllm/ prefix is an OpenAI-compatible provider adapter; actual engine is Transformers',
    'split_sizes': {'development': 8, 'evaluation': 16}, 'formal_runs': {'development': 32, 'evaluation_s0_s1': 64},
    'proposed_intervention': None, 'rental_cny_per_hour': 7.35,
    'runner_source_sha256': {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in names}}
target.write_text(json.dumps(frozen, indent=2) + '\n')
shutil.copy2(target, source / target.name)
for name in ('final-api-contract.json', 'native-smoke-contract.json', 'docker-storage.json', 'frozen-openhands-launch.json'):
    shutil.copy2(evidence / name, source / name)
public = json.loads((source / 'infrastructure-smoke.json').read_bytes())
public.pop('official_agent_runs', None)
public.update(formal_agent_runs_at_freeze=0, agent_smoke=frozen['smoke'], api_contract=api,
              excluded_infrastructure_attempts_retained=True)
(source / 'infrastructure-smoke.json').write_text(json.dumps(public, indent=2) + '\n')
print(json.dumps({'frozen': str(target), 'epoch': frozen['frozen_epoch'], 'source_files': len(names)}))
