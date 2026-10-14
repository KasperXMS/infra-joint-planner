"""Extract byte-exact pinned Git blobs to study-private WSL paths and hash them."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

study=Path('/mnt/d/Codes/infra-aware-mas-new/infra-joint-planner/research/model_aware_skill_compilation/phase2_activation_and_gap')
source=Path('/mnt/d/Codes/infra-aware-mas-new/.code-staging/benchmarks/skilllearn')
private=Path('/root/skillsbench-local-20261013/private/model-aware-phase2-gap/material')
private.mkdir(parents=True,exist_ok=True)
os.chmod(private,0o700)
git=['git','-c',f'safe.directory={source}','-C',str(source)]
commit=subprocess.check_output(git+['rev-parse','HEAD'],text=True).strip()
assert commit=='726e1f79b96b0cb3d729d0e55a1c847e0b5353ae',commit
ids=['offer-letter-generator-2','court-form-filling-2']
families=sorted({x.rsplit('-',1)[0] for x in ids})
paths=[f'tasks/{tid.rsplit("-",1)[0]}/{tid}' for tid in ids]
paths += [f'skills/human_authored/{f}' for f in families]
tracked=subprocess.check_output(git+['ls-files','-z','--']+paths).decode().split('\0')
entries=[]
for rel in sorted(p for p in tracked if p):
    blob=subprocess.check_output(git+['show','HEAD:'+rel])
    entry={'path':rel,'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest()}
    entries.append(entry)
    if rel.startswith('skills/human_authored/'):
        dest=private/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(blob)
    elif '/tests/' in rel or rel.endswith('/instruction.md'):
        dest=private/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(blob)
receipt={'source':'SkillLearnBench','commit':commit,'task_ids':ids,'files':entries,
         'material_root':str(private),'source_git_object_bytes':True}
(study/'evidence/gap-source-files.sha256.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'files':len(entries),'bytes':sum(x['bytes'] for x in entries),
                  'skill_files':sum(x['path'].startswith('skills/') for x in entries),
                  'source_commit':commit,'material_root':str(private)}))
