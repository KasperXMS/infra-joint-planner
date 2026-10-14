"""Publish only source hashes and outcomes; keep raw oracle logs local."""
import hashlib
import json
from pathlib import Path

study = Path(__file__).resolve().parents[1]
evidence = study / 'evidence'
rows = []
for path in sorted(evidence.glob('skilllearn-oracle-*.json')):
    source = json.loads(path.read_text(encoding='utf-8'))
    stages = source['stages']
    rows.append({
        'task_id': source['task_id'],
        'source_commit': source['source_commit'],
        'dockerfile_sha256': source['dockerfile_sha256'],
        'solution_sha256': source['solution_sha256'],
        'verifier_sha256': source['verifier_sha256'],
        'test_sh_sha256': source['test_sh_sha256'],
        'stage_exit_codes': {name: data['exit'] for name, data in stages.items()},
        'reference_reward': int(stages['reward']['stdout_tail'].strip()),
        'private_raw_receipt_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    })
negative = evidence / 'verifier-negative-control.json'
negative_summary = None
if negative.exists():
    source = json.loads(negative.read_text(encoding='utf-8'))
    negative_summary = {
        'private_raw_receipt_sha256': hashlib.sha256(negative.read_bytes()).hexdigest(),
        'task_id': source.get('task_id'),
        'reward': source.get('reward'),
        'keys': sorted(source),
    }
out = {'reference_oracles': rows, 'incomplete_artifact_control': negative_summary}
(evidence / 'oracle-preflight-summary.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps({'oracles': len(rows), 'negative_control': negative_summary is not None}))
