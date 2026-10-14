"""Freeze the activation study before its first model trial."""
import hashlib
import json
import time
from pathlib import Path

study = Path(__file__).resolve().parents[1]
baseline = study.parent / 'pilot-manifest.json'
out = study / 'frozen-manifest.json'
assert not out.exists(), 'Never overwrite the frozen protocol'
old = json.loads(baseline.read_text())
source = json.loads((study / 'evidence/source-files.sha256.json').read_text())
images = json.loads((study / 'evidence/trial-image-builds.json').read_text())
oracle = json.loads((study / 'evidence/skilllearn-oracle-financial-analysis-4.json').read_text())
negative = json.loads((study / 'evidence/verifier-negative-control.json').read_text())
assert source['commit'] == old['benchmark_commit']
assert source['task_ids'] == ['financial-analysis-2', 'financial-analysis-3', 'financial-analysis-4']
assert len(images) == 3 and all(x['build_exit'] == 0 for x in images)
assert oracle['stages']['reward']['stdout_tail'].strip() == '1'
assert negative['reward'] == 0
trigger = (study / 'read-trigger.txt').read_text(encoding='utf-8').rstrip('\n')
trigger_hash = hashlib.sha256(trigger.encode()).hexdigest()
assert trigger_hash == 'e10bbf2a7cf79bb18de25c7252f54a1ba9fcbaa0a8f2915aa3216621e939e6b5'
skill_files = [x for x in source['files'] if x['path'].startswith('skills/human_authored/financial-analysis/') and x['path'].endswith('/SKILL.md')]
assert len(skill_files) == 2
cells = [{'task_id':'financial-analysis-2','condition':'S3','model':'small','stage':'development','trial':1}]
for trial, order in [(1, ('S1','S2','S3')), (2, ('S2','S3','S1')), (3, ('S3','S1','S2'))]:
    cells += [{'task_id':'financial-analysis-4','condition':condition,'model':'small',
               'stage':'validation','trial':trial} for condition in order]
manifest = {
 'status':'frozen','frozen_epoch':time.time(),'phase':'activation-and-gap',
 'benchmark':'SkillLearnBench','benchmark_commit':source['commit'],
 'task_ids':source['task_ids'],
 'task_split':{'financial-analysis-2':'previous-development; S3 activation probe only',
               'financial-analysis-3':'previous-development; no activation trial planned',
               'financial-analysis-4':'within-family validation; frozen before any S1/S2/S3 model run'},
 'source_file_hash_receipt':'evidence/source-files.sha256.json',
 'trial_image_ids':{x['task_id']:x['image_id'] for x in images},
 'oracle_receipt':'evidence/skilllearn-oracle-financial-analysis-4.json',
 'negative_control_receipt':'evidence/verifier-negative-control.json',
 'models':old['models'],'decoding':{**old['decoding'],'explicit_model_seed':None,
    'seed_note':'temperature zero; no reliable seed control exposed by this Codex/vLLM Responses path'},
 'agent':old['agent'],
 'conditions':{
   'S1':'Original Skill tree and native metadata; autonomous file read; no developer body or trigger',
   'S2':'Same tree plus exact concatenated original SKILL.md bodies in developer_instructions',
   'S3':'Same tree plus generic read-trigger text in developer_instructions; Agent must read files via actual tools'},
 's2_skill_tokens':{'financial-analysis':old['s2_skill_tokens']['financial-analysis']},
 's2_skill_sha256':{'financial-analysis':old['s2_skill_sha256']['financial-analysis']},
 's3_trigger_text_file':'read-trigger.txt','s3_trigger_sha256':trigger_hash,
 's3_trigger_tokens':64,'s3_trigger_placement':'Codex config developer_instructions',
 's3_scope':'generic across Skill families; contains no finance names, domain facts or task answers',
 'original_skill_main_file_hashes':{x['path']:x['sha256'] for x in skill_files},
 'agent_budget_seconds':900,'verifier_budget_seconds':900,
 'model_request_budget':'No separate request cap; fixed 900-second Agent wall-time per cell',
 'evaluator':old['evaluator'],'source_tests_visible_to_agent':False,
 'trial_count':len(cells),'trial_cells':cells,
 'runner_sha256':hashlib.sha256((study/'scripts/run_phase2_cell.py').read_bytes()).hexdigest(),
 'bridge_sha256':hashlib.sha256((study.parent/'scripts/model_bridge.py').read_bytes()).hexdigest(),
 'no_replacement_after_outcome':True,
 'infrastructure_retry_policy':'Retain original trace; any retry gets a new labeled cell, never substitutes its score',
 'analysis_warning':'One public within-family validation instance and three potentially deterministic repeats; no significance claim'
}
blob = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
out.write_bytes(blob)
digest = hashlib.sha256(blob).hexdigest()
(study / 'evidence/frozen-manifest.sha256').write_text(digest+'  frozen-manifest.json\n')
print(json.dumps({'manifest_sha256':digest,'cells':len(cells),'trigger_sha256':trigger_hash}))
