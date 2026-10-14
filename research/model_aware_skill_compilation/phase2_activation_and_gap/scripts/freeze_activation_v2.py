"""One prospective trigger refinement after the failed development-only v1 probe."""
import hashlib
import json
import time
from pathlib import Path

study=Path(__file__).resolve().parents[1]
old_path=study/'frozen-manifest.json'
new_path=study/'frozen-manifest-v2.json'
assert old_path.exists() and not new_path.exists()
old=json.loads(old_path.read_text())
dev=study/'trials/p2-development-financial-analysis-2-small-S3-r1/result.json'
result=json.loads(dev.read_text())
assert result['reward']==0
assert not any(result['original_skill_body_seen_in_model_request'].values())
assert not list((study/'trials').glob('p2-validation-*/result.json')), 'Cannot revise after validation starts'
text=(study/'read-trigger-v2.txt').read_text(encoding='utf-8').rstrip('\n')
digest=hashlib.sha256(text.encode()).hexdigest()
assert digest=='5e0da6c5ffd72e8b6132aa02d51d31e4fcfa38405072454af699f1f3f4a65803'
new=dict(old)
new.update({'frozen_epoch':time.time(),
 'supersedes_manifest_sha256':hashlib.sha256(old_path.read_bytes()).hexdigest(),
 'amendment':'One generic stronger first-tool-call read instruction after v1 development probe failed to read either Skill; no financial-analysis-4 model trial has begun',
 'v1_development_receipt':'trials/p2-development-financial-analysis-2-small-S3-r1/result.json',
 's3_trigger_text_file':'read-trigger-v2.txt','s3_trigger_sha256':digest,
 's3_trigger_tokens':68,
 'runner_sha256':hashlib.sha256((study/'scripts/run_phase2_cell.py').read_bytes()).hexdigest(),
 'trial_cells':[{'task_id':'financial-analysis-2','condition':'S3','model':'small',
                 'stage':'development','trial':2}]+old['trial_cells'][1:]})
new['trial_count']=len(new['trial_cells'])
blob=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
new_path.write_bytes(blob)
sha=hashlib.sha256(blob).hexdigest()
(study/'evidence/frozen-manifest-v2.sha256').write_text(sha+'  frozen-manifest-v2.json\n')
print(json.dumps({'sha256':sha,'cells':len(new['trial_cells']),'prior_sha256':new['supersedes_manifest_sha256']}))
