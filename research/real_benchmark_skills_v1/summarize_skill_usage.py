"""Aggregate observed native Skill access in complete official stages.

ACP path/title matches are screening signals; they do not prove semantic use.
Manual trajectory review is required before assigning a failure mechanism.
"""
import argparse
import json
from pathlib import Path


source = Path(__file__).resolve().parent


def summarize(rows):
    rows = list(rows)
    return {
        's1_cells': len(rows),
        'official_resolutions': sum(row['resolved'] for row in rows),
        'harness_invocation_cells': sum(row['harness_invocation'] for row in rows),
        'skill_file_read_candidates': sum(row['skill_file_read'] for row in rows),
        'skill_reference_read_candidates': sum(row['skill_reference_read'] for row in rows),
        'skill_script_execution_candidates': sum(row['skill_script_execution'] for row in rows),
        'no_observed_read_or_invocation': sum(
            not row['skill_file_read'] and not row['skill_reference_read']
            and not row['harness_invocation'] for row in rows),
        'resolved_with_no_observed_read_or_invocation': sum(
            row['resolved'] and not row['skill_file_read']
            and not row['skill_reference_read'] and not row['harness_invocation']
            for row in rows),
    }


def main(stage):
    results = json.loads((source / f'{stage}-results.json').read_bytes())
    signals = json.loads((source / f'{stage}-trace-signals.json').read_bytes())
    if results['completed_cells'] != results['expected_cells'] or signals['completed_cells'] != results['expected_cells']:
        raise RuntimeError('Skill usage requires a complete official stage')
    by_id = {row['run_id']: row for row in results['cells']}
    if len(by_id) != results['expected_cells']:
        raise RuntimeError('Duplicate or missing official results')
    signal_ids = {row['run_id'] for row in signals['rows']}
    if signal_ids != set(by_id) or len(signals['rows']) != len(signal_ids):
        raise RuntimeError('Trace signal/result ID mismatch')

    rows = []
    for signal in signals['rows']:
        result = by_id[signal['run_id']]
        if result['condition'] != 's1':
            continue
        if not result['native_skill_available'] or not signal['native_skill_available']:
            raise RuntimeError('Native Skills missing in S1: ' + signal['run_id'])
        steps = signal['step_indices']
        rows.append({
            'run_id': signal['run_id'],
            'model': result['model'],
            'task_id': result['task_id'],
            'resolved': result['official_resolution'],
            'harness_invocation': result['skill_invocations'] > 0,
            'skill_file_read': bool(steps['skill_file_read']),
            'skill_reference_read': bool(steps['skill_reference_read']),
            'skill_script_execution': bool(steps['skill_script_execution']),
            'trajectory_sha256': signal['trajectory_sha256'],
        })
    expected_s1 = results['expected_cells'] // 2
    if len(rows) != expected_s1:
        raise RuntimeError(f'Expected {expected_s1} S1 cells; got {len(rows)}')
    report = {
        'stage': stage,
        'classification': 'observed native Skill access in official S1 cells',
        'method_limit': 'ACP path/name and tool-kind screen plus harness invocation counts. Candidates require manual review; no causal attribution.',
        'overall': summarize(rows),
        'by_model': {model: summarize(row for row in rows if row['model'] == model)
                     for model in ('Qwen3.5-4B', 'Qwen3.5-9B')},
        'cells': sorted(rows, key=lambda row: row['run_id']),
    }
    destination = source / f'{stage}-skill-usage.json'
    destination.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'saved': str(destination), 'overall': report['overall']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=('development', 'evaluation'), required=True)
    main(parser.parse_args().stage)
