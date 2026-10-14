"""Save safe public receipts for the two pre-validation trigger probes."""
import hashlib
import json
from pathlib import Path

study = Path(__file__).resolve().parents[1]
rows = []
for repeat, version in [(1, 'v1'), (2, 'v2')]:
    name = f'p2-development-financial-analysis-2-small-S3-r{repeat}'
    path = study / 'trials' / name / 'result.json'
    source = json.loads(path.read_text(encoding='utf-8'))
    rows.append({'trial_id': name, 'trigger_version': version,
                 'task_id': source['task_id'], 'official_reward': source['reward'],
                 'agent_exit': source['stages']['agent']['exit'],
                 'agent_seconds': source['stages']['agent']['seconds'],
                 'model_requests': len(source['model_requests']),
                 'trigger_seen_in_model_request': source['s3_trigger_seen_in_model_request'],
                 'original_skill_body_seen_in_model_request':
                     source['original_skill_body_seen_in_model_request'],
                 'private_result_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
out = {'task_split': 'previous-development; excluded from new-instance validation',
       'probes': rows}
(study / 'evidence/development-probe-summary.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps({'probes': len(rows)}))
