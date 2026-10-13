"""Freeze complete development evidence before any held-out outcome is observed.

This analysis-only gate does not alter the frozen task runner or model service.
It refuses partial or stale reports and verifies private completed-cell backups.
"""
import hashlib
import json
import time
from pathlib import Path

from collect_formal_results import cell_row


SOURCE = Path(__file__).resolve().parent
ROOT = Path('/root/skillsbench-local-20261013')
BACKUP = Path('/mnt/d/Codes/infra-aware-mas-new/.code-staging/skillsbench-private-backup')
REQUIRED_REPORTS = (
    'development-results.json',
    'development-trace-signals.json',
    'development-skill-visibility.json',
    'development-exact-repetition.json',
    'development-paired-analysis.json',
    'development-skill-usage.json',
    'development-tool-errors.json',
    'development-backend-reconciliation.json',
    'development-costs.json',
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load(name):
    path = SOURCE / name
    require(path.is_file(), 'Required frozen analysis report missing: ' + name)
    return json.loads(path.read_bytes())


def run_ids(rows):
    ids = [row['run_id'] for row in rows]
    require(len(ids) == len(set(ids)), 'Duplicate run ID in analysis report')
    return set(ids)


def main():
    destination = ROOT / 'evidence/development-analysis.frozen.json'
    require(not destination.exists(), 'Development gate already frozen; never overwrite it')
    require(not any((ROOT / 'jobs/evaluation').rglob('cell.json')),
            'Held-out jobs already exist before development freeze')
    require(not (SOURCE / 'evaluation-results.json').exists(),
            'Held-out results already exist before development freeze')

    selection = load('task-selection.lock.json')
    dev_tasks = [task['id'] for task in selection['tasks'] if task['split'] == 'development']
    heldout_tasks = [task['id'] for task in selection['tasks'] if task['split'] == 'evaluation']
    require(len(dev_tasks) == 8 and len(heldout_tasks) == 16,
            'Frozen split does not contain 8 development and 16 held-out tasks')
    require(not set(dev_tasks) & set(heldout_tasks), 'Split task IDs overlap')
    expected = {f'development-{size}-{task}-{condition}-t1'
                for size in ('4b', '9b') for task in dev_tasks for condition in ('s0', 's1')}
    require(len(expected) == 32, 'Expected-cell IDs are not unique')

    reports = {name: load(name) for name in REQUIRED_REPORTS}
    results = reports['development-results.json']
    require(results['stage'] == 'development' and results['completed_cells'] == 32
            and results['expected_cells'] == 32 and not results['missing_cells']
            and not results['incomplete_cells'], 'Official development results are incomplete')
    require(run_ids(results['cells']) == expected, 'Official development IDs differ from frozen selection')
    current_rows = [cell_row(path) for path in (ROOT / 'jobs/development').rglob('cell.json')]
    require(run_ids(current_rows) == expected
            and all(row['status'] == 'completed' for row in current_rows)
            and {row['run_id']: row for row in current_rows}
            == {row['run_id']: row for row in results['cells']},
            'Official result report differs from current original cell evidence')
    require(all(row['original_result_sha256'] and row['official_summary_sha256']
                and (row['original_verifier_stdout_sha256'] or row['original_ctrf_sha256'])
                and row['private_trajectory_sha256']
                for row in results['cells']), 'A completed cell lacks original scoring or trajectory evidence')

    for name in ('development-trace-signals.json', 'development-skill-visibility.json',
                 'development-exact-repetition.json', 'development-tool-errors.json',
                 'development-backend-reconciliation.json'):
        report = reports[name]
        rows = report['rows'] if 'rows' in report else report['cells']
        require(report['stage'] == 'development' and run_ids(rows) == expected,
                'Incomplete or mismatched analysis report: ' + name)
    visibility = reports['development-skill-visibility.json']
    require(visibility['s0_any_name_offered'] == 0
            and visibility['s1_all_names_offered'] == visibility['s1_cells'] == 16,
            'Native Skill visibility audit is incomplete or contaminated')
    usage = reports['development-skill-usage.json']
    require(usage['stage'] == 'development' and usage['overall']['s1_cells'] == 16
            and run_ids(usage['cells']) == {run_id for run_id in expected if '-s1-' in run_id},
            'Native Skill use report does not cover all S1 cells')
    paired = reports['development-paired-analysis.json']
    require(paired['stage'] == 'development' and paired['trial_count_per_cell'] == 1
            and all(paired['paired'][model]['all']['n_paired_tasks'] == 8
                    for model in ('Qwen3.5-4B', 'Qwen3.5-9B')),
            'Paired analysis is incomplete')
    backend = reports['development-backend-reconciliation.json']
    require(backend['completed_cells'] == 32 and all(
        row['prompt_token_difference_backend_minus_api'] == 0
        and row['completion_token_difference_backend_minus_api'] == 0
        for row in backend['rows']), 'Backend/API token reconciliation failed')
    costs = reports['development-costs.json']
    require(costs['included_stages'] == ['development'] and costs['cells'] == 32
            and costs['backend_counter_snapshot_sha256_by_stage']['development']
            == backend['snapshot_sha256'], 'Development cost report is incomplete or mismatched')

    for run_id in expected:
        receipt = BACKUP / (run_id + '.backup.json')
        require(receipt.is_file(), 'Missing private backup receipt: ' + run_id)
        metadata = json.loads(receipt.read_bytes())
        archive = BACKUP / (run_id + '.tar.gz')
        require(metadata['run_id'] == run_id and archive.is_file()
                and metadata['archive_name'] == archive.name
                and metadata['archive_bytes'] == archive.stat().st_size
                and metadata['archive_sha256'] == digest(archive),
                'Private backup archive mismatch: ' + run_id)

    analysis_path = SOURCE / 'development-analysis.md'
    decision_path = SOURCE / 'development-method-decision.json'
    require(analysis_path.is_file() and len(analysis_path.read_bytes()) > 200,
            'Human development analysis is missing')
    require(decision_path.is_file(), 'Explicit S2 method decision is missing')
    decision = json.loads(decision_path.read_bytes())
    require(decision.get('decision') in ('omit_s2', 'freeze_s2')
            and isinstance(decision.get('rationale'), str)
            and len(decision['rationale'].strip()) >= 50,
            'S2 decision or evidence rationale is missing')
    if decision['decision'] == 'freeze_s2':
        method = SOURCE / decision.get('method_manifest', '')
        require(method.is_file() and decision.get('development_validation_evidence'),
                'S2 needs a frozen manifest and development validation evidence')

    files = ('task-selection.lock.json', 'run-config.frozen.json',
             'development-analysis.md', 'development-method-decision.json') + REQUIRED_REPORTS
    run_config = ROOT / 'evidence/run-config.frozen.json'
    require(run_config.is_file(), 'Frozen runner configuration missing')
    require(digest(SOURCE / 'run-config.frozen.json') == digest(run_config),
            'Public and WSL frozen runner configuration differ')
    for name, expected_sha256 in json.loads(run_config.read_bytes())['runner_source_sha256'].items():
        require(digest(SOURCE / name) == expected_sha256,
                'Frozen runner source changed: ' + name)
    record = {
        'classification': 'development analysis and S2 decision frozen before held-out outcomes',
        'created_epoch': time.time(), 'development_cells': 32,
        'heldout_cells_started': 0, 'decision': decision['decision'],
        'backend_snapshot_sha256': backend['snapshot_sha256'],
        'private_backups_verified': 32,
        'source_file_sha256': {name: digest(SOURCE / name) for name in files if (SOURCE / name).is_file()},
        'wsl_run_config_sha256': digest(run_config),
    }
    if decision['decision'] == 'freeze_s2':
        record['method_manifest_sha256'] = digest(SOURCE / decision['method_manifest'])
    temp = destination.with_suffix('.json.tmp')
    temp.write_text(json.dumps(record, indent=2) + '\n')
    temp.replace(destination)
    print(json.dumps({'saved': str(destination), 'decision': decision['decision'],
                      'development_cells': 32, 'backups_verified': 32}))


if __name__ == '__main__':
    main()
