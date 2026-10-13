"""Summarize observed terminal exits and ACP failures after a complete stage."""
import argparse
import json
from pathlib import Path


source = Path(__file__).resolve().parent


def aggregate(rows):
    rows = list(rows)
    reported = sum(row['terminal_exit_observation']['reported_count'] for row in rows)
    nonzero = sum(row['terminal_exit_observation']['nonzero_count'] for row in rows)
    return {
        'cells': len(rows),
        'terminal_exits_reported': reported,
        'terminal_nonzero_exits': nonzero,
        'terminal_nonzero_exit_rate_among_reported': nonzero / reported if reported else None,
        'terminal_exits_unreported': sum(row['terminal_exit_observation']['unreported_count'] for row in rows),
        'acp_failed_executable_actions': sum(len(row['step_indices']['failed_executable_actions']) for row in rows),
        'acp_failed_think_calls': sum(len(row['step_indices']['failed_think_calls']) for row in rows),
        'acp_failed_other_kind_calls': sum(len(row['step_indices']['failed_other_kind_calls']) for row in rows),
        'cells_with_incomplete_terminal_trajectory': sum(not row['trace_terminal_complete'] for row in rows),
        'pending_tool_calls_at_timeout': sum(row['pending_tool_call_count'] for row in rows),
    }


def main(stage):
    report = json.loads((source / f'{stage}-trace-signals.json').read_bytes())
    expected = 32 if stage == 'development' else 64
    rows = report['rows']
    if report['completed_cells'] != expected or len(rows) != expected:
        raise RuntimeError('Trace error analysis requires a complete official stage')
    if len({row['run_id'] for row in rows}) != expected:
        raise RuntimeError('Duplicate trace row')
    output = {
        'stage': stage,
        'classification': 'observed tool exit and ACP status signals on official cells',
        'method_limit': 'Last Exit code in ACP terminal output; shell pipelines/compound commands may mask failures. Nonzero exploratory probes need manual review. ACP failed status and shell nonzero are distinct signals.',
        'overall': aggregate(rows),
        'by_model_condition': {
            model: {condition: aggregate(row for row in rows
                                         if row['model'] == model and row['condition'] == condition)
                    for condition in ('s0', 's1')}
            for model in ('Qwen3.5-4B', 'Qwen3.5-9B')},
        'cells': sorted(({
            'run_id': row['run_id'], 'model': row['model'], 'condition': row['condition'],
            'task_id': row['task_id'], 'trace_terminal_complete': row['trace_terminal_complete'],
            'terminal_exit_observation': row['terminal_exit_observation'],
            'acp_failed_executable_actions': len(row['step_indices']['failed_executable_actions']),
            'acp_failed_think_calls': len(row['step_indices']['failed_think_calls']),
            'acp_failed_other_kind_calls': len(row['step_indices']['failed_other_kind_calls']),
        } for row in rows), key=lambda row: row['run_id']),
    }
    destination = source / f'{stage}-tool-errors.json'
    destination.write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({'saved': str(destination), 'overall': output['overall']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=('development', 'evaluation'), required=True)
    main(parser.parse_args().stage)
