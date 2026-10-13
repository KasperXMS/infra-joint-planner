"""Export aggregate official cell results, never raw prompts or trajectories."""
import argparse
import hashlib
import json
from pathlib import Path

root = Path('/root/skillsbench-local-20261013')
source = Path('/mnt/d/Codes/infra-aware-mas-new/infra-joint-planner/research/real_benchmark_skills_v1')
selection = json.loads((source / 'task-selection.lock.json').read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize_requests(run_id):
    directory = root / 'private/requests' / run_id
    output = {'chat_requests': 0, 'api_prompt_tokens': 0, 'api_completion_tokens': 0,
              'api_usage_responses': 0, 'non_200_responses': 0, 'native_response_sha256': [],
              'typed_response_sha256': []}
    if not directory.exists():
        return output
    for request in directory.glob('*.request.json'):
        output['chat_requests'] += 1
        response = request.with_name(request.stem.removesuffix('.request') + '.response.bin')
        native = request.with_name(request.stem.removesuffix('.request') + '.native-response.bin')
        if not response.exists():
            output['non_200_responses'] += 1
            continue
        try:
            data = json.loads(response.read_bytes())
        except (ValueError, UnicodeDecodeError):
            output['non_200_responses'] += 1
            continue
        usage = data.get('usage')
        if usage:
            output['api_usage_responses'] += 1
            output['api_prompt_tokens'] += usage.get('prompt_tokens', 0)
            output['api_completion_tokens'] += usage.get('completion_tokens', 0)
        else:
            output['non_200_responses'] += 1
        output['typed_response_sha256'].append(digest(response))
        if native.exists():
            output['native_response_sha256'].append(digest(native))
    output['native_response_sha256'].sort()
    output['typed_response_sha256'].sort()
    return output


def cell_row(path):
    cell = json.loads(path.read_bytes())
    if cell.get('status') != 'completed':
        return {'run_id': cell['run_id'], 'status': cell['status']}
    bench = path.parent / 'bench'
    summary_path = bench / 'summary.json'
    result_paths = list(bench.rglob('result.json'))
    if len(result_paths) != 1:
        raise RuntimeError(f'Expected one official result for {cell["run_id"]}; got {len(result_paths)}')
    result_path = result_paths[0]
    summary = json.loads(summary_path.read_bytes())
    result = json.loads(result_path.read_bytes())
    if summary['total'] != 1 or result['task_name'] != cell['task_id']:
        raise RuntimeError('Official summary/result task mismatch: ' + cell['run_id'])
    reward = result['rewards'].get('reward')
    passed = summary['passed'] == 1
    if passed != (reward == 1):
        raise RuntimeError('Reward/resolution mismatch: ' + cell['run_id'])
    trajectory = result_path.parent / 'agent/acp_trajectory.jsonl'
    request = summarize_requests(cell['run_id'])
    row = {k: cell[k] for k in ('run_id', 'stage', 'model', 'condition', 'task_id')}
    row.update(status='completed', official_resolution=passed, official_fractional_reward=reward,
               error_category=result['error_category'], verifier_error_category=result['verifier_error_category'],
               agent_timeout_info=result['agent_timeout_info'],
               native_skill_available=result['include_task_skills'], skill_source=result['skill_source'],
               skill_invocations=result['n_skill_invocations'], tool_calls=result['n_tool_calls'],
               trajectory_summary=result['trajectory_summary'],
               prompt_tokens=(result.get('agent_result') or {}).get('n_input_tokens'),
               completion_tokens=(result.get('agent_result') or {}).get('n_output_tokens'),
               execution_seconds=result['timing']['total'],
               environment_setup_seconds=result['timing']['environment_setup'],
               agent_setup_seconds=result['timing']['agent_setup'],
               agent_execution_seconds=result['timing']['agent_execution'],
               verifier_seconds=result['timing']['verifier'],
               started_epoch=cell['started_epoch'], finished_epoch=cell['finished_epoch'],
               quiescent_epoch=cell['quiescent_epoch'], generation_drain=cell['generation_drain'],
               official_task_digest=result['task_digest'], official_summary_sha256=digest(summary_path),
               original_result_sha256=digest(result_path),
               private_trajectory_sha256=digest(trajectory) if trajectory.exists() else None,
               request_metrics=request)
    if row['condition'] == 's0' and row['native_skill_available']:
        raise RuntimeError('S0 unexpectedly has native skills: ' + row['run_id'])
    if row['condition'] == 's1' and not row['native_skill_available']:
        raise RuntimeError('S1 has no native skills: ' + row['run_id'])
    return row


def main(stage, require_complete):
    task_ids = [t['id'] for t in selection['tasks'] if t['split'] == stage]
    expected_ids = {f'{stage}-{size}-{task}-{condition}-t1'
                    for size in ('4b', '9b') for task in task_ids for condition in ('s0', 's1')}
    rows = [cell_row(path) for path in (root / 'jobs' / stage).rglob('cell.json')]
    if len({r['run_id'] for r in rows}) != len(rows):
        raise RuntimeError('Duplicate cell records')
    if any(r['run_id'] not in expected_ids for r in rows):
        raise RuntimeError('Unexpected formal cell ID')
    complete = [r for r in rows if r['status'] == 'completed']
    if require_complete and {r['run_id'] for r in complete} != expected_ids:
        raise RuntimeError(f'Only {len(complete)}/{len(expected_ids)} completed')
    report = {'stage': stage, 'expected_cells': len(expected_ids), 'completed_cells': len(complete),
              'missing_cells': sorted(expected_ids - {r['run_id'] for r in rows}),
              'incomplete_cells': [r for r in rows if r['status'] != 'completed'],
              'cells': sorted(complete, key=lambda r: r['run_id']),
              'classification': 'official development' if stage == 'development' else 'official held-out evaluation'}
    if require_complete:
        destination = source / (stage + '-results.json')
        destination.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'saved': str(destination), 'completed': len(complete)}))
    else:
        print(json.dumps({'completed': len(complete), 'expected': len(expected_ids),
                          'incomplete': report['incomplete_cells'], 'missing_count': len(report['missing_cells'])}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['development', 'evaluation'], required=True)
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    main(args.stage, args.require_complete)
