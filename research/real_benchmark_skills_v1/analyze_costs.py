"""Calculate measurable task and rental costs after official cells complete."""
import argparse
import datetime as dt
import json
from collections import defaultdict
from pathlib import Path

source = Path(__file__).resolve().parent
RATE_CNY_PER_HOUR = 7.35
HKT = dt.timezone(dt.timedelta(hours=8))
APPROX_STUDY_START = dt.datetime(2026, 10, 13, 11, 48, tzinfo=HKT).timestamp()


def rental(seconds):
    return RATE_CNY_PER_HOUR * seconds / 3600


def main(stages, ending_epoch):
    cells = []
    backend_by_id = {}
    snapshot_sha256 = {}
    for stage in stages:
        report = json.loads((source / (stage + '-results.json')).read_bytes())
        if report['completed_cells'] != report['expected_cells']:
            raise RuntimeError('Only complete official stages can enter aggregate costs')
        cells.extend(report['cells'])
        backend = json.loads((source / (stage + '-backend-reconciliation.json')).read_bytes())
        stage_ids = {cell['run_id'] for cell in report['cells']}
        rows = backend['rows']
        if (backend['stage'] != stage or len(rows) != len(stage_ids)
                or {row['run_id'] for row in rows} != stage_ids):
            raise RuntimeError('Backend generation reconciliation does not cover official cells')
        if any(row['prompt_token_difference_backend_minus_api']
               or row['completion_token_difference_backend_minus_api'] for row in rows):
            raise RuntimeError('Backend/API token mismatch requires cost audit')
        backend_by_id.update((row['run_id'], row) for row in rows)
        snapshot_sha256[stage] = backend['snapshot_sha256']
    if not cells:
        raise RuntimeError('No official cells')
    first = min(cell['started_epoch'] for cell in cells)
    last = max(cell['quiescent_epoch'] for cell in cells)
    end = last if ending_epoch is None else ending_epoch
    if end < last:
        raise ValueError('Ending observation precedes last completed cell')
    groups = defaultdict(list)
    for cell in cells:
        groups[(cell['stage'], cell['model'], cell['condition'])].append(cell)
    aggregate = []
    for (stage, model, condition), rows in sorted(groups.items()):
        elapsed = sum(row['quiescent_epoch'] - row['started_epoch'] for row in rows)
        pass_count = sum(row['official_resolution'] for row in rows)
        prompt = sum(row['request_metrics']['api_prompt_tokens'] for row in rows)
        completion = sum(row['request_metrics']['api_completion_tokens'] for row in rows)
        value = {'stage': stage, 'model': model, 'condition': condition, 'n_cells': len(rows),
                 'official_passes': pass_count, 'cell_elapsed_seconds': elapsed,
                 'incremental_rental_equivalent_cny': rental(elapsed),
                 'api_prompt_tokens': prompt, 'api_completion_tokens': completion,
                 'backend_generation_count': sum(backend_by_id[row['run_id']]['backend_generation_count']
                                                 for row in rows),
                 'backend_generation_seconds': sum(backend_by_id[row['run_id']]['backend_generation_seconds']
                                                   for row in rows),
                 'api_roundtrip_seconds': sum(row['request_metrics']['api_roundtrip_seconds'] for row in rows),
                 'api_transport_errors': sum(row['request_metrics']['api_transport_errors'] for row in rows),
                 'tool_calls': sum(row['tool_calls'] for row in rows),
                 'harness_prompt_tokens': sum(row['prompt_tokens'] or 0 for row in rows),
                 'harness_completion_tokens': sum(row['completion_tokens'] or 0 for row in rows)}
        value['incremental_rental_equivalent_per_pass_cny'] = (
            value['incremental_rental_equivalent_cny'] / pass_count if pass_count else None)
        aggregate.append(value)
    report = {'classification': 'measurable cost accounting on complete official task cells',
              'included_stages': stages, 'rental_cny_per_hour_user_supplied': RATE_CNY_PER_HOUR,
              'cells': len(cells), 'first_formal_cell_epoch': first, 'last_formal_quiescence_epoch': last,
              'ending_observation_epoch': end,
              'sum_cell_elapsed_seconds': sum(row['quiescent_epoch'] - row['started_epoch'] for row in cells),
              'sum_cell_incremental_rental_equivalent_cny': sum(
                  rental(row['quiescent_epoch'] - row['started_epoch']) for row in cells),
              'backend_counter_snapshot_sha256_by_stage': snapshot_sha256,
              'backend_generation_count': sum(row['backend_generation_count'] for row in backend_by_id.values()),
              'backend_generation_seconds': sum(row['backend_generation_seconds'] for row in backend_by_id.values()),
              'formal_period_rental_estimate_cny': rental(last - first),
              'estimated_all_in_rental_since_approx_study_start_cny': rental(end - APPROX_STUDY_START),
              'approx_study_start_hkt': '2026-10-13 11:48 (approximately)',
              'rental_continues_after_observation': True,
              'local_wsl_electricity_hardware_and_transfer_costs': 'unpriced',
              'api_per_token_bill': 0,
              'usage_limit': 'Bridge response usage can omit a failed call without usage; backend generation counters are reconciled to completed cell windows and must match API totals here. GPU generation seconds exclude idle/load/setup time.',
              'groups': aggregate}
    output = source / ('-'.join(stages) + '-costs.json')
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'saved': str(output), 'cells': len(cells),
                      'estimated_all_in_rental_cny': report['estimated_all_in_rental_since_approx_study_start_cny']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=('development', 'evaluation'), action='append', required=True)
    parser.add_argument('--ending-epoch', type=float)
    args = parser.parse_args()
    main(args.stage, args.ending_epoch)
