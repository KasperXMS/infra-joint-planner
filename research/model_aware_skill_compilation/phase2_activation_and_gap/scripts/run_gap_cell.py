"""Run one source-valid loaded-original-Skill gap cell; tests enter only afterward.

Run inside WSL2 as root after writing pilot-manifest.json. The original task
image, task instruction, Skills and verifier are byte-for-byte source blobs.
The only orchestration adaptation closes the source runner's pre-Agent /tests
mount exposure and configures its registered Codex CLI for the local model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

ROOT=Path('/root/skillsbench-local-20261013')
PRIVATE=ROOT/'private/model-aware-phase2'
MATERIAL=ROOT/'private/model-aware-phase2-gap/material'
STUDY=Path('/mnt/d/Codes/infra-aware-mas-new/infra-joint-planner/research/model_aware_skill_compilation/phase2_activation_and_gap')
MANIFEST=STUDY/'gap-manifest.json'
DOCKER=str(ROOT/'bin/docker')


def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def run(argv: list[str], env: dict[str,str], *, timeout: int=90) -> subprocess.CompletedProcess:
    return subprocess.run(argv,env=env,capture_output=True,text=True,timeout=timeout)


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument('task_id')
    ap.add_argument('condition',choices=['S2'])
    ap.add_argument('model',choices=['small','strong'])
    ap.add_argument('--stage',choices=['gap'],required=True)
    ap.add_argument('--trial',type=int,default=1)
    args=ap.parse_args()
    manifest=json.loads(MANIFEST.read_text())
    assert manifest['status']=='frozen', 'Manifest must be frozen before Agent trials'
    assert {'task_id':args.task_id,'condition':args.condition,'model':args.model,
            'stage':args.stage,'trial':args.trial} in manifest['trial_cells']
    family=args.task_id.rsplit('-',1)[0]
    model=manifest['models'][args.model]
    label=model['served_model_name']
    trial_id=f"p2-{args.stage}-{args.task_id}-{args.model}-{args.condition}-r{args.trial}"
    trial=STUDY/'trials'/trial_id
    if trial.exists():
        raise SystemExit('Refusing to overwrite a planned/previous trial: '+str(trial))
    (trial/'agent').mkdir(parents=True)
    (trial/'verifier').mkdir()
    (trial/'artifacts').mkdir()
    token=(PRIVATE/'bridge.key').read_text().strip()
    skill_root=MATERIAL/'skills/human_authored'/family
    skill_files=sorted(skill_root.glob('*/SKILL.md'))
    assert skill_files
    content='\n\n'.join(p.read_text(encoding='utf-8') for p in skill_files) if args.condition=='S2' else None
    if content is not None:
        assert hashlib.sha256(content.encode()).hexdigest()==manifest['s2_skill_sha256'][family]
    trigger=(STUDY/manifest['s3_trigger_text_file']).read_text(encoding='utf-8').rstrip('\n') if args.condition=='S3' else None
    if trigger is not None:
        assert hashlib.sha256(trigger.encode()).hexdigest()==manifest['s3_trigger_sha256']
    config=(f'model = {json.dumps(label)}\n'
            'model_provider = "model_aware_local"\n'
            'model_reasoning_effort = "none"\n'
            'model_context_window = 16384\n'
            'model_auto_compact_token_limit = 14000\n'
            'approval_policy = "never"\n'
            'sandbox_mode = "danger-full-access"\n')
    if content is not None:
        config+='developer_instructions = '+json.dumps(content,ensure_ascii=False)+'\n'
    if trigger is not None:
        config+='developer_instructions = '+json.dumps(trigger,ensure_ascii=False)+'\n'
    config+=('\n[model_providers.model_aware_local]\n'
             'name = "Study Qwen over SSH"\n'
             f'base_url = "http://172.17.0.1:{model["bridge_port"]}/v1"\n'
             'env_key = "OPENAI_API_KEY"\n'
             'wire_api = "responses"\n'
             'request_max_retries = 0\n'
             'stream_max_retries = 0\n'
             f'http_headers = {{ "X-Study-Run-ID" = "{trial_id}" }}\n')
    (trial/'agent/config.toml').write_text(config,encoding='utf-8')
    instruction=MATERIAL/'tasks'/family/args.task_id/'instruction.md'
    tests=MATERIAL/'tasks'/family/args.task_id/'tests'
    assert instruction.exists() and tests.is_dir()
    source_manifest=json.loads((STUDY/'evidence/gap-source-files.sha256.json').read_text())
    source_hashes={x['path']:x['sha256'] for x in source_manifest['files']}
    for path in [instruction,*skill_files,*tests.rglob('*')]:
        if not path.is_file():continue
        rel=path.relative_to(MATERIAL).as_posix()
        assert sha(path)==source_hashes[rel],rel
    env=os.environ.copy()
    env['DOCKER_HOST']='unix://'+str(ROOT/'run/docker.sock')
    env['PATH']=str(ROOT/'bin')+':'+env['PATH']
    image=f'phase2-gap-trial-{args.task_id}:codex-0.162.1'
    inspect=run([DOCKER,'image','inspect',image,'--format','{{.Id}}'],env)
    assert inspect.returncode==0,image
    assert inspect.stdout.strip()==manifest['trial_image_ids'][args.task_id],image
    container='ma-'+trial_id
    receipt={'trial_id':trial_id,'task_id':args.task_id,'condition':args.condition,
             'model':args.model,'served_model_name':label,'source_commit':manifest['benchmark_commit'],
             'image_id':inspect.stdout.strip(),'instruction_sha256':sha(instruction),
             'skill_files':[{'name':p.parent.name,'sha256':sha(p)} for p in skill_files] if args.condition!='S0' else [],
             's2_developer_instructions_sha256':hashlib.sha256(content.encode()).hexdigest() if content is not None else None,
             's2_developer_instructions_tokens':manifest['s2_skill_tokens'].get(family) if content is not None else None,
             's3_trigger_sha256':manifest['s3_trigger_sha256'] if trigger is not None else None,
             's3_trigger_tokens':manifest['s3_trigger_tokens'] if trigger is not None else None,
             'stage':args.stage,'trial':args.trial,
             'agent_budget_seconds':manifest['agent_budget_seconds'],
             'tests_visible_during_agent':False,'started_epoch':time.time(),'stages':{}}
    (trial/'setup.json').write_text(json.dumps(receipt,indent=2)+'\n')
    created=False
    try:
        proc=run([DOCKER,'run','-d','--name',container,'--network','bridge',
                  '-v',str(trial)+':/logs','-e','OPENAI_API_KEY='+token,
                  image,'sleep','3600'],env,timeout=45)
        receipt['stages']['create']={'exit':proc.returncode,'stderr':proc.stderr[-1500:]}
        assert proc.returncode==0,proc.stderr
        created=True
        for target in ('/root/.agents/skills','/root/.codex/skills'):
            proc=run([DOCKER,'exec',container,'mkdir','-p',target],env)
            assert proc.returncode==0,proc.stderr
            proc=run([DOCKER,'cp',str(skill_root)+'/.',container+':'+target],env)
            assert proc.returncode==0,proc.stderr
        proc=run([DOCKER,'cp',str(instruction),container+':/tmp/instruction.txt'],env)
        assert proc.returncode==0,proc.stderr
        skill_inventory=run([DOCKER,'exec',container,'find','/root/.agents/skills','-type','f'],env)
        receipt['skill_inventory']=skill_inventory.stdout.splitlines()
        assert receipt['skill_inventory']
        command=('timeout --signal=TERM '+str(manifest['agent_budget_seconds'])+'s '
                 'codex exec --dangerously-bypass-approvals-and-sandbox '
                 '--skip-git-repo-check --json --model '+label+' -- "$(cat /tmp/instruction.txt)"')
        agent_started=time.time()
        with (trial/'agent/codex.jsonl').open('wb') as stdout, (trial/'agent/codex.stderr.log').open('wb') as stderr:
            try:
                agent=subprocess.run([DOCKER,'exec','-e','CODEX_HOME=/logs/agent',container,
                                      'sh','-c',command],env=env,stdout=stdout,stderr=stderr,
                                     timeout=manifest['agent_budget_seconds']+90)
                agent_exit=agent.returncode
                outer_timeout=False
            except subprocess.TimeoutExpired:
                agent_exit=None
                outer_timeout=True
                run([DOCKER,'exec',container,'pkill','-f','codex'],env,timeout=15)
        receipt['stages']['agent']={'exit':agent_exit,'seconds':time.time()-agent_started,
                                    'timed_out':agent_exit==124 or outer_timeout,
                                    'outer_timeout':outer_timeout}
        events=[]
        for line in (trial/'agent/codex.jsonl').read_text(errors='replace').splitlines():
            if not line.startswith('{'):continue
            try:events.append(json.loads(line))
            except json.JSONDecodeError:pass
        completed=[x for x in events if x.get('type')=='turn.completed']
        receipt['token_usage']=completed[-1].get('usage') if completed else None
        receipt['agent_event_counts']={kind:sum(x.get('type')==kind for x in events)
                                       for kind in ('item.started','item.completed','turn.completed','turn.failed')}
        bridge_records=[json.loads(line) for line in (PRIVATE/'requests.jsonl').read_text().splitlines()
                        if line.strip()]
        model_requests=[x for x in bridge_records if x.get('run_id')==trial_id]
        receipt['model_requests']=model_requests
        def contains(value,needle):
            if isinstance(value,str):return needle in value
            if isinstance(value,list):return any(contains(x,needle) for x in value)
            if isinstance(value,dict):return any(contains(x,needle) for x in value.values())
            return False
        request_json=[json.loads((PRIVATE/'requests'/(x['id']+'.request.bin')).read_bytes())
                      for x in model_requests if x['route']=='/v1/responses']
        receipt['original_skill_body_seen_in_model_request']={
            p.parent.name:any(contains(data,p.read_text(encoding='utf-8')) for data in request_json)
            for p in skill_files}
        if content is not None:
            receipt['s2_body_seen_in_model_request']=any(contains(data,content) for data in request_json)
        if trigger is not None:
            receipt['s3_trigger_seen_in_model_request']=any(contains(data,trigger) for data in request_json)
        # Official tests enter the container only after the Agent has exited.
        proc=run([DOCKER,'cp',str(tests),container+':/tests'],env,timeout=45)
        assert proc.returncode==0,proc.stderr
        verifier_started=time.time()
        try:
            verifier=run([DOCKER,'exec',container,'bash','/tests/test.sh'],env,timeout=manifest['verifier_budget_seconds'])
            verifier_exit=verifier.returncode
            verifier_stdout,verifier_stderr=verifier.stdout,verifier.stderr
            verifier_timeout=False
        except subprocess.TimeoutExpired as exc:
            verifier_exit=None
            verifier_stdout=exc.stdout.decode(errors='replace') if isinstance(exc.stdout,bytes) else (exc.stdout or '')
            verifier_stderr=exc.stderr.decode(errors='replace') if isinstance(exc.stderr,bytes) else (exc.stderr or '')
            verifier_timeout=True
        (trial/'verifier/stdout.log').write_text(verifier_stdout,encoding='utf-8')
        (trial/'verifier/stderr.log').write_text(verifier_stderr,encoding='utf-8')
        receipt['stages']['verifier']={'exit':verifier_exit,'seconds':time.time()-verifier_started,
                                       'timed_out':verifier_timeout}
        reward_file=trial/'verifier/reward.txt'
        receipt['reward']=int(reward_file.read_text().strip()) if reward_file.exists() else None
        receipt['official_pass']=receipt['reward']==1
        artifact=manifest['artifact_paths'][args.task_id]
        copied=run([DOCKER,'cp',container+':'+artifact,str(trial/'artifacts')],env,timeout=60)
        receipt['artifact_copy_exit']=copied.returncode
        artifact_path=trial/'artifacts'/Path(artifact).name
        receipt['artifact_sha256']=sha(artifact_path) if artifact_path.exists() else None
        diff=run([DOCKER,'diff',container],env,timeout=30)
        (trial/'container-diff.txt').write_text(diff.stdout,encoding='utf-8')
        receipt['finished_epoch']=time.time()
    except Exception as exc:
        receipt['error']=repr(exc)
        receipt['finished_epoch']=time.time()
        raise
    finally:
        (trial/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
        if created:run([DOCKER,'rm','-f',container],env,timeout=45)
    print(json.dumps({'trial_id':trial_id,'reward':receipt.get('reward'),
                      'agent_exit':receipt['stages'].get('agent',{}).get('exit'),
                      'verifier_exit':receipt['stages'].get('verifier',{}).get('exit'),
                      'seconds':receipt['finished_epoch']-receipt['started_epoch']}))


if __name__=='__main__':main()
