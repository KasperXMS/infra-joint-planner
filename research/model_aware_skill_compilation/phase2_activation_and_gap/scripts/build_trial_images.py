"""Layer pinned Codex CLI on oracle-checked, original task images."""
import json
import os
import subprocess
import time
from pathlib import Path

root=Path('/root/skillsbench-local-20261013')
study=Path('/mnt/d/Codes/infra-aware-mas-new/infra-joint-planner/research/model_aware_skill_compilation/phase2_activation_and_gap')
docker=str(root/'bin/docker')
env=os.environ.copy()
env['DOCKER_HOST']='unix://'+str(root/'run/docker.sock')
ids=['financial-analysis-2','financial-analysis-3','financial-analysis-4']
receipts=[]
for task_id in ids:
    base=(f'phase2-skilllearn-{task_id}:source-726e1f7' if task_id.endswith('-4')
          else f'model-aware-skilllearn-{task_id}:source-726e1f7')
    tag=f'phase2-trial-{task_id}:codex-0.162.1'
    print('building',task_id,flush=True)
    started=time.time()
    proc=subprocess.run([docker,'build','--build-arg','TASK_IMAGE='+base,
        '-t',tag,'-f',str(study/'scripts/CodexTaskOverlay.Dockerfile'),str(study/'scripts')],
        env=env,text=True,capture_output=True,timeout=600)
    inspect=subprocess.run([docker,'image','inspect',tag,'--format','{{.Id}}'],
                           env=env,text=True,capture_output=True,timeout=30) if proc.returncode==0 else None
    receipt={'task_id':task_id,'base_image':base,'trial_image':tag,
             'build_exit':proc.returncode,'seconds':time.time()-started,
             'image_id':inspect.stdout.strip() if inspect else None,
             'stdout_tail':proc.stdout[-2000:],'stderr_tail':proc.stderr[-1500:]}
    receipts.append(receipt)
    print(json.dumps({'task_id':task_id,'build_exit':proc.returncode,
                      'image_id':receipt['image_id'],'seconds':receipt['seconds']}),flush=True)
    if proc.returncode!=0: break
(study/'evidence/trial-image-builds.json').write_text(json.dumps(receipts,indent=2)+'\n')
if len(receipts)!=len(ids) or any(x['build_exit'] for x in receipts): raise SystemExit(1)
