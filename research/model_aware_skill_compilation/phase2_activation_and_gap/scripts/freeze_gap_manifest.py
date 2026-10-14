"""Freeze at most four oracle-valid loaded-original-Skill diagnostics."""
import hashlib
import json
import time
from pathlib import Path

study = Path(__file__).resolve().parents[1]
target = study / 'gap-manifest.json'
assert not target.exists(), 'Refusing to replace a frozen gap manifest'
activation = json.loads((study / 'frozen-manifest-v2.json').read_text())
source = json.loads((study / 'evidence/gap-source-files.sha256.json').read_text())
builds = json.loads((study / 'evidence/gap-image-builds.json').read_text())
tokens = json.loads((study / 'evidence/gap-skill-token-counts.json').read_text())
oracles = json.loads((study / 'evidence/oracle-preflight-summary.json').read_text())
oracle_by_id = {row['task_id']: row for row in oracles['reference_oracles']}
ids = ['offer-letter-generator-2', 'court-form-filling-2']
assert all(oracle_by_id[task_id]['reference_reward'] == 1 for task_id in ids)
assert {row['task_id'] for row in builds} == set(ids)
assert all(row['build_exit'] == 0 and row['image_id'] for row in builds)
assert source['commit'] == activation['benchmark_commit']
material = Path('/root/skillsbench-local-20261013/private/model-aware-phase2-gap/material')
skill_digest = {}
for family in sorted({task_id.rsplit('-', 1)[0] for task_id in ids}):
    files = sorted((material / 'skills/human_authored' / family).glob('*/SKILL.md'))
    assert files
    text = '\n\n'.join(path.read_text(encoding='utf-8') for path in files)
    skill_digest[family] = hashlib.sha256(text.encode()).hexdigest()
assert set(skill_digest) == set(tokens['original_body_tokens'])

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

cells = []
for model in ('small', 'strong'):
    for task_id in ids:
        cells.append({'task_id': task_id, 'condition': 'S2', 'model': model,
                      'stage': 'gap', 'trial': 1})
manifest = {
    'status': 'frozen', 'frozen_epoch': time.time(),
    'phase': 'loaded-original-skill-gap-diagnostics',
    'benchmark': 'SkillLearnBench', 'benchmark_commit': activation['benchmark_commit'],
    'task_split': {task_id: 'procedural-gap development; never future G2/G3' for task_id in ids},
    'task_ids': ids, 'source_file_hash_receipt': 'evidence/gap-source-files.sha256.json',
    'oracle_summary': 'evidence/oracle-preflight-summary.json',
    'oracle_raw_receipts_private': {task_id: f'evidence/skilllearn-oracle-{task_id}.json' for task_id in ids},
    'trial_image_ids': {row['task_id']: row['image_id'] for row in builds},
    'models': activation['models'], 'decoding': activation['decoding'],
    'agent': activation['agent'],
    'conditions': {'S2': 'Original Skill tree unchanged; exact concatenated original SKILL.md bodies in developer_instructions'},
    's2_skill_tokens': tokens['original_body_tokens'], 's2_skill_sha256': skill_digest,
    'original_skill_main_file_hashes': {
        row['path']: row['sha256'] for row in source['files'] if row['path'].endswith('/SKILL.md')},
    'artifact_paths': {'offer-letter-generator-2': '/root/offer_letter_filled.docx',
                       'court-form-filling-2': '/root/sc100-filled.pdf'},
    'agent_budget_seconds': 900, 'verifier_budget_seconds': 900,
    'model_request_budget': 'No separate request cap; fixed 900-second Agent wall-time per cell',
    'evaluator': 'source tests/test.sh after Agent exit; binary /logs/verifier/reward.txt',
    'source_tests_visible_to_agent': False,
    'trial_count_max': 4, 'planned_small_runs': 2,
    'conditional_strong_policy': 'Run a 27B S2 reference only if the corresponding 9B outcome is a plausible loaded-Skill procedural failure and the same source-valid task can isolate model capability from tooling/perception; no selective replacement of 9B scores.',
    'trial_cells': cells,
    'runner_sha256': sha(study / 'scripts/run_gap_cell.py'),
    'bridge_sha256': sha(study / 'scripts/model_bridge.py'),
    'environment_note': '9B and 27B services use the same GPUs and run serially; no AutoDL instance restart',
}
target.write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'manifest_sha256': sha(target), 'cells_max': len(cells),
                  'small_runs': 2, 'source_valid': ids}))
