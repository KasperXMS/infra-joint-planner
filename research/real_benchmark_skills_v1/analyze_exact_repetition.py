"""Index adjacent identical ACP tool actions and outputs without exporting text.

This is a conservative screen for repeated work, not proof that the operation
was unnecessary. Human review must distinguish expected rechecks from loops.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path('/root/skillsbench-local-20261013')
SOURCE = Path(__file__).resolve().parent


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def action(event):
    if (event.get('type') != 'tool_call' or event.get('status') != 'completed'
            or event.get('kind') not in ('execute', 'read', 'edit')):
        return None
    title = str(event.get('title', ''))
    output = '\n'.join(str(item['content'].get('text', ''))
                       for item in event.get('content', [])
                       if isinstance(item, dict) and isinstance(item.get('content'), dict))
    if not title or not output:
        return None
    exits = re.findall(r'Exit code:\s*(-?\d+)', output)
    return {'kind': event['kind'], 'title_sha256': digest(title),
            'output_sha256': digest(output),
            'last_reported_exit': int(exits[-1]) if exits else None}


def sequences(events):
    found = []
    current = []
    previous = None
    for index, event in enumerate(events):
        candidate = action(event)
        key = (candidate['kind'], candidate['title_sha256'], candidate['output_sha256']) if candidate else None
        if key is not None and key == previous and current and index == current[-1]:
            current.append(index + 1)
        else:
            if len(current) >= 2:
                found.append({'step_indices': [step - 1 for step in current], **last_candidate})
            current = [index + 1] if key is not None else []
        previous = key
        last_candidate = candidate
    if len(current) >= 2:
        found.append({'step_indices': [step - 1 for step in current], **last_candidate})
    return found


def main(stage, require_complete):
    expected = 32 if stage == 'development' else 64
    rows = []
    for cell_path in sorted((ROOT / 'jobs' / stage).rglob('cell.json')):
        cell = json.loads(cell_path.read_bytes())
        if cell.get('status') != 'completed':
            continue
        matches = list(cell_path.parent.rglob('agent/acp_trajectory.jsonl'))
        if len(matches) != 1:
            raise RuntimeError('Expected one ACP trajectory: ' + cell['run_id'])
        path = matches[0]
        events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        repeats = sequences(events)
        rows.append({'run_id': cell['run_id'], 'model': cell['model'],
                     'condition': cell['condition'], 'task_id': cell['task_id'],
                     'trajectory_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'exact_adjacent_repeat_sequences': repeats,
                     'repeat_actions_beyond_first': sum(len(item['step_indices']) - 1 for item in repeats)})
    ids = [row['run_id'] for row in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError('Duplicate completed run IDs')
    if require_complete and len(rows) != expected:
        raise RuntimeError(f'Incomplete {stage} stage: {len(rows)}/{expected} cells')
    report = {
        'stage': stage,
        'classification': 'exact adjacent ACP title/output repetition, not task success or tool failure',
        'method_limit': 'Only consecutive completed execute/read/edit calls with byte-identical titles and text outputs. Manual review is required to identify useless repetition and recovery.',
        'completed_cells': len(rows), 'expected_cells': expected,
        'cells_with_repeats': sum(bool(row['exact_adjacent_repeat_sequences']) for row in rows),
        'repeat_cell_ids': [row['run_id'] for row in rows if row['exact_adjacent_repeat_sequences']],
        'repeat_actions_beyond_first': sum(row['repeat_actions_beyond_first'] for row in rows),
        'rows': rows,
    }
    if len(rows) == expected:
        destination = SOURCE / f'{stage}-exact-repetition.json'
        destination.write_text(json.dumps(report, indent=2) + '\n')
        report['saved'] = str(destination)
    print(json.dumps({key: value for key, value in report.items() if key != 'rows'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=('development', 'evaluation'), required=True)
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    main(args.stage, args.require_complete)
