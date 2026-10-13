"""Index private ACP trajectories without exporting their contents.

The path screen is a conservative candidate for manual review. A file mention
does not prove correct skill application, and absent path hits do not prove
the model never internalized skill content from a different route.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

root = Path('/root/skillsbench-local-20261013')
source = Path(__file__).resolve().parent
selection = json.loads((source / 'task-selection.lock.json').read_bytes())
tasks = {task['id']: task for task in selection['tasks']}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_skill_path(text):
    # Directory names such as "pdf" or "pymatgen" also occur in ordinary task
    # files and libraries. Require the native Skill directory or SKILL.md.
    pattern = r'(?:SKILL\.md\b|/skills(?:/|(?=[\s"\x27`]|$))|(?<![\w./-])skills/)'
    return bool(re.search(pattern, text, re.I))


def direct_skill_script_execution(title):
    """Screen for actually launching a bundled script, rather than inspecting it.

    A `grep`, `cat`, `find`, or file listing over a .py path is a read/probe,
    not execution. This intentionally misses indirect imports or `python -c`.
    """
    if not selected_skill_path(title):
        return False
    command = title.split('$', 1)[-1].strip()
    boundary = r'(?:^|[;&|]\s*)'
    assignments = r'(?:[A-Za-z_]\w*=\S+\s+)*'
    interpreter = r'(?:python(?:3(?:\.\d+)?)?|bash|sh|node|tsx|deno)\s+(?:-[A-Za-z0-9]+\s+)*'
    script = r'["\x27]?(?:/|\./|skills/)[^\s"\x27;&|]*\.(?:py|sh|js|ts)(?=\s|["\x27;&|]|$)'
    return bool(re.search(boundary + assignments + interpreter + script, command, re.I)
                or re.search(boundary + assignments + script, command, re.I))


def signal_row(path):
    cell = json.loads(path.read_bytes())
    if cell.get('status') != 'completed':
        return None
    if cell['task_id'] not in tasks:
        raise RuntimeError('Unrecognized frozen task: ' + cell['task_id'])
    result_path = next((path.parent / 'bench').rglob('result.json'))
    result = json.loads(result_path.read_bytes())
    trajectory = result_path.parent / 'agent/acp_trajectory.jsonl'
    if not trajectory.exists():
        raise RuntimeError('Missing native ACP trajectory: ' + cell['run_id'])
    events = [json.loads(line) for line in trajectory.read_text().splitlines()]
    actions = {'skill_discovery': [], 'skill_file_read': [], 'skill_reference_read': [],
               'skill_script_execution': [], 'skill_mentioned_in_thought': [],
               'failed_tool_calls': [], 'failed_executable_actions': [],
               'failed_think_calls': [], 'failed_other_kind_calls': [],
               'terminal_zero_exit_steps': [], 'terminal_nonzero_exit_steps': [],
               'terminal_exit_unreported_steps': [],
               'completed_tool_calls': []}
    for step, event in enumerate(events):
        kind = event.get('kind')
        title = event.get('title', '')
        if event.get('type') == 'agent_thought' and selected_skill_path(event.get('text', '')):
            actions['skill_mentioned_in_thought'].append(step)
        if event.get('type') != 'tool_call':
            continue
        if event.get('status') == 'failed':
            actions['failed_tool_calls'].append(step)
            if kind in ('execute', 'read', 'edit'):
                actions['failed_executable_actions'].append(step)
            elif kind == 'think':
                actions['failed_think_calls'].append(step)
            else:
                actions['failed_other_kind_calls'].append(step)
        elif event.get('status') == 'completed':
            actions['completed_tool_calls'].append(step)
        if kind == 'execute':
            output = '\n'.join(str(item['content'].get('text', ''))
                               for item in event.get('content', [])
                               if isinstance(item, dict) and isinstance(item.get('content'), dict))
            exit_codes = re.findall(r'Exit code:\s*(-?\d+)', output)
            if not exit_codes:
                actions['terminal_exit_unreported_steps'].append(step)
            elif int(exit_codes[-1]) == 0:
                actions['terminal_zero_exit_steps'].append(step)
            else:
                actions['terminal_nonzero_exit_steps'].append(step)
        if not selected_skill_path(title):
            continue
        if kind in ('read', 'execute'):
            actions['skill_discovery'].append(step)
        if kind == 'read':
            key = 'skill_file_read' if re.search(r'SKILL\.md', title, re.I) else 'skill_reference_read'
            actions[key].append(step)
        if kind == 'execute' and direct_skill_script_execution(title):
            actions['skill_script_execution'].append(step)
    verifier = result_path.parent / 'verifier/ctrf.json'
    verifier_stdout = result_path.parent / 'verifier/test-stdout.txt'
    timeout = result.get('agent_timeout_info') or {}
    tests = None
    if verifier.exists():
        report = json.loads(verifier.read_bytes())['results']
        tests = {'summary': {k: report['summary'].get(k) for k in ('tests', 'passed', 'failed', 'skipped')},
                 'failed_test_names': [t['name'] for t in report.get('tests', []) if t.get('status') in ('failed', 'error')],
                 'report_sha256': sha(verifier)}
    return {'run_id': cell['run_id'], 'model': cell['model'], 'task_id': cell['task_id'],
            'condition': cell['condition'], 'native_skill_available': result['include_task_skills'],
            'official_reward': result['rewards'], 'harness_skill_invocations': result['n_skill_invocations'],
            'trajectory_sha256': sha(trajectory), 'trajectory_steps': len(events),
            'step_indices': actions, 'verifier_tests': tests,
            'terminal_exit_observation': {
                'reported_count': len(actions['terminal_zero_exit_steps']) + len(actions['terminal_nonzero_exit_steps']),
                'nonzero_count': len(actions['terminal_nonzero_exit_steps']),
                'unreported_count': len(actions['terminal_exit_unreported_steps']),
                'limit': 'Last terminal Exit code in ACP output; compound shell commands may hide an earlier failure.'},
            'verifier_stdout_sha256': sha(verifier_stdout) if verifier_stdout.exists() else None,
            'agent_timeout_reason': timeout.get('reason'),
            'pending_tool_call_count': len(timeout.get('pending_tool_call_ids') or []),
            'trace_terminal_complete': (timeout.get('terminal_trajectory_complete')
                                        if timeout else not result.get('partial_trajectory', False)),
            'method_limit': 'Native Skill path and direct interpreter/script-launch screens; indirect imports may be missed. Human trace review required for actual use or causality.'}


def main(stage, require_complete):
    paths = list((root / 'jobs' / stage).rglob('cell.json'))
    rows = [row for p in paths if (row := signal_row(p)) is not None]
    output = {'stage': stage, 'completed_cells': len(rows), 'rows': sorted(rows, key=lambda row: row['run_id']),
              'classification': 'development trace index' if stage == 'development' else 'held-out trace index'}
    expected = 32 if stage == 'development' else 64
    if require_complete and len(rows) != expected:
        raise RuntimeError(f'Only {len(rows)}/{expected} official cells completed')
    if require_complete:
        destination = source / (stage + '-trace-signals.json')
        destination.write_text(json.dumps(output, indent=2) + '\n')
        print(json.dumps({'saved': str(destination), 'completed_cells': len(rows)}))
    else:
        print(json.dumps({'completed_cells': len(rows), 'expected': expected,
                          'skill_read_cells': [r['run_id'] for r in rows if r['step_indices']['skill_file_read']],
                          'direct_skill_script_execution_candidates': [
                              r['run_id'] for r in rows if r['step_indices']['skill_script_execution']],
                          'verifier_failure_names': {r['run_id']: r['verifier_tests']['failed_test_names']
                                                     for r in rows if r['verifier_tests']}}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=('development', 'evaluation'), required=True)
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    main(args.stage, args.require_complete)
