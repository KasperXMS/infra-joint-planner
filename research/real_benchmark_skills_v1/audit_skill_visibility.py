"""Check whether official native Skill names reached the first model request.

This reads private request trajectories but emits only task IDs, Skill names,
presence flags and the trajectory digest. It never exports prompt content.
Use with ACP read/action analysis to distinguish availability from consumption.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path('/root/skillsbench-local-20261013')
SOURCE = Path(__file__).resolve().parent


def first_system_message(path):
    with path.open() as stream:
        first = json.loads(next(stream))
    request = first.get('request', {})
    body = request.get('body', {})
    if isinstance(body, str):
        body = json.loads(body)
    if not isinstance(body, dict):
        raise RuntimeError('Unexpected first model request body: ' + str(path))
    messages = body.get('messages', [])
    systems = [message.get('content', '') for message in messages if message.get('role') == 'system']
    if not systems:
        raise RuntimeError('No system message in first model request: ' + str(path))
    return '\n'.join(content if isinstance(content, str) else json.dumps(content)
                     for content in systems).lower()


def main(stage, require_complete):
    lock = json.loads((SOURCE / 'task-selection.lock.json').read_bytes())
    tasks = {task['id']: task for task in lock['tasks'] if task['split'] == stage}
    expected = len(tasks) * 2 * 2
    rows = []
    for size in ('4b', '9b'):
        for cell_path in sorted((ROOT / 'jobs' / stage / size).glob('*/cell.json')):
            cell = json.loads(cell_path.read_bytes())
            if cell.get('status') != 'completed':
                continue
            task = tasks.get(cell['task_id'])
            if task is None:
                raise RuntimeError('Unselected task in completed cell: ' + cell['task_id'])
            matches = list(cell_path.parent.rglob('llm_trajectory.jsonl'))
            if len(matches) != 1:
                raise RuntimeError('Expected one private model trajectory: ' + cell['run_id'])
            path = matches[0]
            system = first_system_message(path)
            offered = {
                name: bool(re.search(r'<name>\s*' + re.escape(name.lower()) + r'\s*</name>', system))
                for name in task['skill_directories']
            }
            rows.append({
                'run_id': cell['run_id'],
                'model': cell['model'],
                'condition': cell['condition'],
                'task_id': cell['task_id'],
                'official_native_skill_names': sorted(offered),
                'names_in_first_system_message': offered,
                'all_names_offered': all(offered.values()),
                'any_name_offered': any(offered.values()),
                'llm_trajectory_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            })
    ids = [row['run_id'] for row in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError('Duplicate completed run IDs')
    report = {
        'stage': stage,
        'classification': 'first-request native Skill metadata visibility; not a file read or invocation',
        'method': 'Exact official Skill directory names within <name> tags in the initial model system message.',
        'completed_cells': len(rows),
        'expected_cells': expected,
        's1_all_names_offered': sum(row['condition'] == 's1' and row['all_names_offered'] for row in rows),
        's1_cells': sum(row['condition'] == 's1' for row in rows),
        's0_any_name_offered': sum(row['condition'] == 's0' and row['any_name_offered'] for row in rows),
        'rows': rows,
    }
    if require_complete and len(rows) != expected:
        raise RuntimeError(f'Incomplete {stage} stage: {len(rows)}/{expected} cells')
    if len(rows) == expected:
        destination = SOURCE / f'{stage}-skill-visibility.json'
        destination.write_text(json.dumps(report, indent=2) + '\n')
        report['saved'] = str(destination)
    print(json.dumps({key: value for key, value in report.items() if key != 'rows'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=('development', 'evaluation'), required=True)
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    main(args.stage, args.require_complete)
