"""Descriptive paired official outcomes; no significance or repeatability claims."""
import argparse
import json
from collections import defaultdict
from pathlib import Path

source = Path(__file__).resolve().parent
selection = json.loads((source / 'task-selection.lock.json').read_bytes())


def metrics(pairs):
    records = list(pairs)
    n = len(records)
    if not n:
        return None
    s0 = sum(int(a['official_resolution']) for a, _ in records)
    s1 = sum(int(b['official_resolution']) for _, b in records)
    rescue = sum(not a['official_resolution'] and b['official_resolution'] for a, b in records)
    regression = sum(a['official_resolution'] and not b['official_resolution'] for a, b in records)
    request_prompt = {condition: sum(x['request_metrics']['api_prompt_tokens'] for x in (pair[condition] for pair in records))
                      for condition in (0, 1)}
    request_completion = {condition: sum(x['request_metrics']['api_completion_tokens'] for x in (pair[condition] for pair in records))
                          for condition in (0, 1)}
    return {'n_paired_tasks': n, 's0_passes': s0, 's1_passes': s1,
            's0_resolution_rate': s0 / n, 's1_resolution_rate': s1 / n,
            'paired_lift': (s1 - s0) / n, 'rescue': rescue, 'regression': regression,
            'both_pass': sum(a['official_resolution'] and b['official_resolution'] for a, b in records),
            'both_fail': sum(not a['official_resolution'] and not b['official_resolution'] for a, b in records),
            's0_fractional_reward_mean': sum(a['official_fractional_reward'] for a, _ in records) / n,
            's1_fractional_reward_mean': sum(b['official_fractional_reward'] for _, b in records) / n,
            's0_prompt_tokens': request_prompt[0], 's1_prompt_tokens': request_prompt[1],
            's0_completion_tokens': request_completion[0], 's1_completion_tokens': request_completion[1],
            's0_tool_calls': sum(a['tool_calls'] for a, _ in records),
            's1_tool_calls': sum(b['tool_calls'] for _, b in records),
            's0_wall_seconds': sum(a['execution_seconds'] for a, _ in records),
            's1_wall_seconds': sum(b['execution_seconds'] for _, b in records),
            's1_skill_invocations_reported_by_harness': sum(b['skill_invocations'] for _, b in records)}


def main(stage):
    results = json.loads((source / (stage + '-results.json')).read_bytes())
    assert results['completed_cells'] == results['expected_cells']
    lookup = {(cell['model'], cell['task_id'], cell['condition']): cell for cell in results['cells']}
    group = defaultdict(list)
    for model in ('Qwen3.5-4B', 'Qwen3.5-9B'):
        tasks = [t for t in selection['tasks'] if t['split'] == stage]
        for task in tasks:
            a = lookup[(model, task['id'], 's0')]
            b = lookup[(model, task['id'], 's1')]
            pair = (a, b)
            group[(model, 'all')].append(pair)
            group[(model, 'domain:' + task['category'])].append(pair)
            group[(model, 'difficulty:' + task['difficulty'])].append(pair)
    report = {'stage': stage, 'trial_count_per_cell': 1,
              'units_of_comparison': 'frozen official task pairs',
              'paired': {model: {name: metrics(group[(model, name)]) for grouped_model, name in group
                                 if grouped_model == model}
                         for model in ('Qwen3.5-4B', 'Qwen3.5-9B')},
              'inference_limit': 'Descriptive single-trial task outcomes; no statistical significance, repeatability or general scaling claim.'}
    report['model_size_comparison'] = {
        'same_tasks_in_both_models': True,
        'native_skill_lift_9b_minus_4b': (
            report['paired']['Qwen3.5-9B']['all']['paired_lift']
            - report['paired']['Qwen3.5-4B']['all']['paired_lift']),
        'interpretation_limit': 'Descriptive difference of paired lifts on this frozen task sample only.'}
    output = source / (stage + '-paired-analysis.json')
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'saved': str(output),
                      'overall': {model: report['paired'][model]['all'] for model in report['paired']}}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=('development', 'evaluation'), required=True)
    main(parser.parse_args().stage)
