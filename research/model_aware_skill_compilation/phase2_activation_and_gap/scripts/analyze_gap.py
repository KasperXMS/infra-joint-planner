"""Summarize loaded-original-Skill gap cells without publishing task artifacts."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

study = Path(__file__).resolve().parents[1]
private = Path('/root/skillsbench-local-20261013/private/model-aware-phase2')
material = Path('/root/skillsbench-local-20261013/private/model-aware-phase2-gap/material')
manifest_path = study / 'gap-manifest.json'
manifest = json.loads(manifest_path.read_text())


def contains(obj, needle):
    if isinstance(obj, str):
        return needle in obj
    if isinstance(obj, list):
        return any(contains(x, needle) for x in obj)
    if isinstance(obj, dict):
        return any(contains(x, needle) for x in obj.values())
    return False


rows = []
for cell in manifest['trial_cells']:
    task_id = cell['task_id']
    family = task_id.rsplit('-', 1)[0]
    name = f"p2-gap-{task_id}-{cell['model']}-S2-r1"
    folder = study / 'trials' / name
    result_path = folder / 'result.json'
    if not result_path.exists():
        rows.append({'trial_id': name, 'task_id': task_id, 'model': cell['model'],
                     'status': 'not-run', 'reward': None})
        continue
    result = json.loads(result_path.read_text())
    skill_files = sorted((material / 'skills/human_authored' / family).glob('*/SKILL.md'))
    skills = {path.parent.name: path.read_text(encoding='utf-8') for path in skill_files}
    forms_path = material / 'skills/human_authored/court-form-filling/pdf/forms.md'
    forms_body = forms_path.read_text(encoding='utf-8') if task_id == 'court-form-filling-2' else None
    events = []
    for line in (folder / 'agent/codex.jsonl').read_text(errors='replace').splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    commands = [item['item'] for item in events if item.get('type') == 'item.completed'
                and item.get('item', {}).get('type') == 'command_execution']
    counts = Counter(item.get('command', '') for item in commands)
    stderr = (folder / 'agent/codex.stderr.log').read_text(errors='replace')
    errors = [item.get('item', {}).get('message', '') for item in events
              if item.get('type') == 'item.completed' and item.get('item', {}).get('type') == 'error']
    requests = [x for x in result.get('model_requests', []) if x.get('route') == '/v1/responses']
    docs, usages = [], []
    for request in requests:
        raw = private / 'requests' / (request['id'] + '.request.bin')
        if raw.exists():
            docs.append(json.loads(raw.read_bytes()))
        response = private / 'requests' / (request['id'] + '.response.bin')
        if not response.exists():
            continue
        for line in response.read_text(errors='replace').splitlines():
            if not line.startswith('data: '):
                continue
            try:
                event = json.loads(line[6:])
            except json.JSONDecodeError:
                continue
            if event.get('type') in ('response.completed', 'response.incomplete', 'response.failed'):
                usage = (event.get('response') or {}).get('usage')
                if usage:
                    usages.append(usage)
    rejected = [x for x in requests if isinstance(x.get('status'), int)
                and 400 <= x['status'] < 500]
    context = sum('maximum context length' in
                  (private / 'requests' / (x['id'] + '.response.bin')).read_text(errors='replace')
                  for x in rejected)
    verifier = (folder / 'verifier/stdout.log').read_text(errors='replace')
    tests = sorted(set(re.sub(r'\[[^]]*\]', '', line.split(' - ')[0])
                       for line in verifier.splitlines()
                       if line.startswith(('PASSED ', 'FAILED ', 'ERROR '))))
    agent = result.get('stages', {}).get('agent', {})
    rows.append({
        'trial_id': name, 'task_id': task_id, 'model': cell['model'],
        'status': ('invalid' if result.get('error') or result.get('reward') not in (0, 1)
                   else 'scored-context-rejection' if context
                   else 'scored-timeout' if agent.get('timed_out') else 'valid-score'),
        'reward': result.get('reward'), 'agent_exit': agent.get('exit'),
        'agent_timed_out': bool(agent.get('timed_out')),
        'agent_seconds': agent.get('seconds'),
        'total_seconds': result.get('finished_epoch', 0) - result.get('started_epoch', 0),
        'model_requests': len(requests),
        'main_skill_body_request_count': {k: sum(contains(doc, v) for doc in docs)
                                          for k, v in skills.items()},
        's2_body_in_all_requests': bool(docs) and all(contains(doc, '\n\n'.join(skills.values()))
                                                    for doc in docs),
        'main_skill_tool_read': {k: any('SKILL.md' in item.get('command', '')
                                       and item.get('exit_code') == 0
                                       and v in item.get('aggregated_output', '')
                                       for item in commands) for k, v in skills.items()},
        'referenced_forms_resource_tool_access': any('forms.md' in item.get('command', '')
                                                      for item in commands),
        'referenced_forms_read_successfully': (any('forms.md' in item.get('command', '')
                                                   and item.get('exit_code') == 0
                                                   and forms_body in item.get('aggregated_output', '')
                                                   for item in commands)
                                               if forms_body is not None else None),
        'referenced_forms_body_request_count': (sum(contains(doc, forms_body) for doc in docs)
                                                if forms_body is not None else None),
        'tool_calls': len(commands),
        'failed_tool_calls': sum(item.get('exit_code') not in (0, None) for item in commands),
        'repeated_command_occurrences': sum(value - 1 for value in counts.values() if value > 1),
        'tool_router_errors': stderr.count('ERROR codex_core::tools::router'),
        'compaction_warnings': sum('multiple compactions' in message for message in errors),
        'api_rejections': len(rejected), 'context_rejections': context,
        'transport_failures': sum(x.get('status') is None or x.get('status', 0) >= 500
                                  or x.get('error') is not None for x in requests),
        'input_tokens': sum(x.get('input_tokens', 0) or 0 for x in usages),
        'output_tokens': sum(x.get('output_tokens', 0) or 0 for x in usages),
        'cached_input_tokens': sum((x.get('input_tokens_details') or {}).get('cached_tokens', 0)
                                   or 0 for x in usages),
        'first_byte_seconds_sum': round(sum(x.get('first_byte_seconds') or 0 for x in requests), 3),
        'response_seconds_sum': round(sum(x.get('seconds') or 0 for x in requests), 3),
        'artifact_present': bool(result.get('artifact_sha256')),
        'artifact_sha256': result.get('artifact_sha256'),
        'verifier_test_statuses': tests,
    })
out = {'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
       'planned_maximum': len(manifest['trial_cells']), 'rows': rows}
(study / 'evidence/gap-summary.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps({'scored': sum(r['reward'] in (0, 1) for r in rows),
                  'planned_maximum': len(rows)}))
