"""Match private backend counters to serial official cells by frozen time windows."""
import argparse
import hashlib
import json
from pathlib import Path

from collect_formal_results import root, summarize_requests


def main(snapshot, stage, require_complete):
    payload = snapshot.read_bytes()
    records = [json.loads(line) for line in payload.splitlines()]
    cells = [json.loads(path.read_bytes()) for path in (root / 'jobs' / stage).rglob('cell.json')]
    complete = [cell for cell in cells if cell.get('status') == 'completed']
    if require_complete and len(complete) != (32 if stage == 'development' else 64):
        raise RuntimeError('Official stage is not complete')
    rows = []
    for cell in complete:
        start, end = cell['started_epoch'], cell['quiescent_epoch']
        generated = [record for record in records if start <= record['started_epoch'] <= end]
        api = summarize_requests(cell['run_id'])
        row = {'run_id': cell['run_id'], 'backend_generation_count': len(generated),
               'backend_prompt_tokens': sum(x['prompt_tokens'] for x in generated),
               'backend_generated_tokens': sum(x.get('generated_tokens', 0) for x in generated),
               'backend_generation_seconds': sum(x.get('generation_seconds', 0) for x in generated),
               'api_usage_responses': api['api_usage_responses'],
               'api_prompt_tokens': api['api_prompt_tokens'],
               'api_completion_tokens': api['api_completion_tokens'],
               'api_transport_errors': api['api_transport_errors']}
        row['prompt_token_difference_backend_minus_api'] = row['backend_prompt_tokens'] - row['api_prompt_tokens']
        row['completion_token_difference_backend_minus_api'] = row['backend_generated_tokens'] - row['api_completion_tokens']
        rows.append(row)
    report = {'stage': stage, 'snapshot_sha256': hashlib.sha256(payload).hexdigest(),
              'snapshot_record_count': len(records), 'completed_cells': len(rows),
              'method': 'Serial, non-overlapping [cell start, post-generation drain] windows.',
              'rows': sorted(rows, key=lambda row: row['run_id'])}
    if require_complete:
        source = Path(__file__).resolve().parent
        output = source / (stage + '-backend-reconciliation.json')
        output.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'saved': str(output), 'completed_cells': len(rows)}))
    else:
        print(json.dumps({'completed_cells': len(rows),
                          'snapshot_sha256': report['snapshot_sha256'],
                          'backend_generation_count': sum(row['backend_generation_count'] for row in rows),
                          'api_transport_errors': sum(row['api_transport_errors'] for row in rows),
                          'cells_with_token_mismatch': [row['run_id'] for row in rows
                                                        if row['prompt_token_difference_backend_minus_api']
                                                        or row['completion_token_difference_backend_minus_api']]}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--stage', choices=('development', 'evaluation'), required=True)
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    main(args.snapshot, args.stage, args.require_complete)
