"""Summarize immutable phase-2 receipts; keep full request bodies private in WSL."""
import hashlib
import json
from collections import Counter
from pathlib import Path

study = Path(__file__).resolve().parents[1]
private = Path('/root/skillsbench-local-20261013/private/model-aware-phase2')
requests_dir = private / 'requests'
manifest = json.loads((study / 'frozen-manifest-v2.json').read_text())
skill_dir = private / 'material/skills/human_authored/financial-analysis'
skills = {p.parent.name:p.read_text(encoding='utf-8') for p in sorted(skill_dir.glob('*/SKILL.md'))}

def contains(x, needle):
    if isinstance(x,str):return needle in x
    if isinstance(x,list):return any(contains(y,needle) for y in x)
    if isinstance(x,dict):return any(contains(y,needle) for y in x.values())
    return False

rows=[]
for cell in manifest['trial_cells']:
    trial=f"p2-{cell['stage']}-{cell['task_id']}-{cell['model']}-{cell['condition']}-r{cell['trial']}"
    folder=study/'trials'/trial
    p=folder/'result.json'
    if not p.exists():
        rows.append({'trial_id':trial,'status':'missing','reward':None})
        continue
    result=json.loads(p.read_text())
    events=[]
    for line in (folder/'agent/codex.jsonl').read_text(errors='replace').splitlines():
        try:events.append(json.loads(line))
        except json.JSONDecodeError:pass
    commands=[e['item'] for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='command_execution']
    cmd_count=Counter(x.get('command','') for x in commands)
    stderr=(folder/'agent/codex.stderr.log').read_text(errors='replace').splitlines()
    router=[s for s in stderr if 'ERROR codex_core::tools::router' in s]
    errors=[e.get('item',{}).get('message','') for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='error']
    requests=[x for x in result.get('model_requests',[]) if x.get('route')=='/v1/responses']
    model_docs=[]
    usage=[]
    for req in requests:
        rp=requests_dir/(req['id']+'.request.bin')
        if rp.exists():model_docs.append(json.loads(rp.read_bytes()))
        sp=requests_dir/(req['id']+'.response.bin')
        if not sp.exists():continue
        final=None
        for line in sp.read_text(errors='replace').splitlines():
            if not line.startswith('data: '):continue
            try:event=json.loads(line[6:])
            except json.JSONDecodeError:continue
            if event.get('type') in ('response.completed','response.incomplete','response.failed'):
                final=(event.get('response') or {}).get('usage')
        if final:usage.append(final)
    read={name:any(x.get('exit_code')==0 and body in x.get('aggregated_output','')
                       and 'SKILL.md' in x.get('command','') for x in commands)
          for name,body in skills.items()}
    discovery={name:any(name in x.get('command','') and 'SKILL.md' in x.get('command','') for x in commands)
               for name in skills}
    referenced={name:any(x.get('exit_code')==0 and name in x.get('command','')
                             and '/scripts/' in x.get('command','') for x in commands)
                for name in skills}
    body_requests={name:sum(contains(doc,body) for doc in model_docs) for name,body in skills.items()}
    first=model_docs[0] if model_docs else {}
    metadata={name:contains(first,'/'+name+'/SKILL.md') for name in skills}
    api_errors=[x for x in requests if isinstance(x.get('status'),int) and 400<=x['status']<500]
    context=sum('maximum context length' in (requests_dir/(x['id']+'.response.bin')).read_text(errors='replace')
                for x in api_errors if (requests_dir/(x['id']+'.response.bin')).exists())
    agent_stage=result.get('stages',{}).get('agent',{})
    status=('invalid' if result.get('error') or result.get('reward') not in (0,1) else
            'scored-context-rejection' if context else
            'scored-timeout' if agent_stage.get('timed_out') else 'valid-score')
    row={'trial_id':trial,'stage':cell['stage'],'task_id':cell['task_id'],
         'condition':cell['condition'],'model':cell['model'],'repetition':cell['trial'],
         'status':status,'reward':result.get('reward'),
         'agent_exit':agent_stage.get('exit'),
         'agent_timed_out':bool(agent_stage.get('timed_out')),
         'agent_seconds':agent_stage.get('seconds'),
         'total_seconds':result.get('finished_epoch',0)-result.get('started_epoch',0),
         'skill_available':bool(result.get('skill_inventory')),
         'metadata_visible_first_request':metadata,
         'skill_discovery_attempt':discovery,
         'main_skill_read_successfully_via_tool':read,
         'referenced_script_accessed_via_tool':referenced,
         'skill_body_model_request_count':body_requests,
         'model_requests':len(requests),
         'nominal_injected_tokens_per_request':manifest['s2_skill_tokens']['financial-analysis'] if cell['condition']=='S2' else (manifest['s3_trigger_tokens'] if cell['condition']=='S3' else 0),
         'nominal_repeated_injected_tokens':len(requests)*(manifest['s2_skill_tokens']['financial-analysis'] if cell['condition']=='S2' else (manifest['s3_trigger_tokens'] if cell['condition']=='S3' else 0)),
         'input_tokens':sum(x.get('input_tokens',0) or 0 for x in usage),
         'output_tokens':sum(x.get('output_tokens',0) or 0 for x in usage),
         'cached_input_tokens':sum((x.get('input_tokens_details') or {}).get('cached_tokens',0) or 0 for x in usage),
         'tool_calls':len(commands),
         'failed_tool_calls':sum(x.get('exit_code') not in (0,None) for x in commands),
         'repeated_command_occurrences':sum(v-1 for v in cmd_count.values() if v>1),
         'tool_router_errors':len(router),
         'compaction_warnings':sum('multiple compactions' in s for s in errors),
         'api_rejections':len(api_errors),'context_rejections':context,
         'transport_failures':sum(x.get('status') is None or x.get('status',0)>=500 or x.get('error') is not None for x in requests),
         'first_byte_seconds_sum':round(sum(x.get('first_byte_seconds') or 0 for x in requests),3),
         'response_seconds_sum':round(sum(x.get('seconds') or 0 for x in requests),3),
         'artifact_sha256':result.get('artifact_sha256'),
         'artifact_present':bool(result.get('artifact_sha256')),
         'trigger_in_first_request':contains(first,(study/manifest['s3_trigger_text_file']).read_text().rstrip('\n')),
         's2_body_in_all_requests':bool(model_docs) and all(contains(doc,'\n\n'.join(skills.values())) for doc in model_docs) if cell['condition']=='S2' else None}
    rows.append(row)
out={'manifest_sha256':hashlib.sha256((study/'frozen-manifest-v2.json').read_bytes()).hexdigest(),
     'planned':len(manifest['trial_cells']),
     'officially_scored':sum(x.get('reward') in (0,1) for x in rows),
     'valid_scored':sum(x['status']=='valid-score' for x in rows),
     'rows':rows}
(study/'evidence/activation-summary.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'planned':out['planned'],'officially_scored':out['officially_scored'],
                  'valid_scored':out['valid_scored']}))
