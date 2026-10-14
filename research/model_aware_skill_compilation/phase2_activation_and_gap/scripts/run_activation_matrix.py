"""Run all nine predeclared validation cells once, in the frozen balanced order."""
import json
import subprocess
import sys
import time
from pathlib import Path

study=Path(__file__).resolve().parents[1]
manifest=json.loads((study/'frozen-manifest-v2.json').read_text())
assert manifest['status']=='frozen'
dev=study/'trials/p2-development-financial-analysis-2-small-S3-r2/result.json'
assert dev.exists(), 'Run the prospective development probe before validation'
cells=[x for x in manifest['trial_cells'] if x['stage']=='validation']
assert len(cells)==9
for ordinal,cell in enumerate(cells,1):
    trial=f"p2-validation-{cell['task_id']}-{cell['model']}-{cell['condition']}-r{cell['trial']}"
    result_file=study/'trials'/trial/'result.json'
    if result_file.exists():
        prior=json.loads(result_file.read_text())
        if prior.get('error') or prior.get('reward') not in (0,1):
            raise SystemExit('Existing invalid cell needs diagnosis; no replacement: '+trial)
        print(json.dumps({'existing':trial,'reward':prior['reward']}),flush=True)
        continue
    print(json.dumps({'starting':trial,'ordinal':ordinal,'of':len(cells),'epoch':time.time()}),flush=True)
    p=subprocess.run([sys.executable,str(study/'scripts/run_phase2_cell.py'),
        cell['task_id'],cell['condition'],cell['model'],'--stage','validation',
        '--trial',str(cell['trial'])],capture_output=True,text=True,timeout=2100)
    print(p.stdout[-1000:],flush=True)
    if p.stderr:print(p.stderr[-1000:],file=sys.stderr,flush=True)
    if not result_file.exists():raise SystemExit('Missing cell result: '+trial)
    result=json.loads(result_file.read_text())
    (study/'evidence/validation-progress.json').write_text(json.dumps({
      'epoch':time.time(),'completed':ordinal,'of':len(cells),'latest':trial,
      'reward':result.get('reward'),'error':result.get('error')},indent=2)+'\n')
    if p.returncode or result.get('error') or result.get('reward') not in (0,1):
        raise SystemExit('Stopped on infrastructure-invalid cell; original trace retained: '+trial)
print(json.dumps({'completed_validation_cells':len(cells)}),flush=True)
