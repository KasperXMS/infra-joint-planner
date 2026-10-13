"""Copy completed private run evidence outside Git with digest receipts."""
import argparse
import hashlib
import io
import json
import os
import tarfile
import time
from pathlib import Path

root = Path('/root/skillsbench-local-20261013')
backup = Path('/mnt/d/Codes/infra-aware-mas-new/.code-staging/skillsbench-private-backup')
os.umask(0o077)
backup.mkdir(mode=0o700, parents=True, exist_ok=True)


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def save_cell(cell_path):
    cell = json.loads(cell_path.read_bytes())
    if cell.get('status') != 'completed':
        return None
    run_id = cell['run_id']
    archive = backup / (run_id + '.tar.gz')
    receipt = backup / (run_id + '.backup.json')
    if archive.exists() or receipt.exists():
        if not archive.exists() or not receipt.exists():
            raise RuntimeError('Partial existing backup: ' + run_id)
        previous = json.loads(receipt.read_bytes())
        if previous['archive_sha256'] != sha256(archive):
            raise RuntimeError('Existing backup hash mismatch: ' + run_id)
        return {'run_id': run_id, 'status': 'verified_existing'}
    if not (cell_path.parent / 'bench/summary.json').exists():
        raise RuntimeError('Official summary missing from completed cell: ' + run_id)
    requests = root / 'private/requests' / run_id
    if not requests.exists():
        raise RuntimeError('Private request directory missing: ' + run_id)
    matching = [line for line in (root / 'private/requests.jsonl').read_bytes().splitlines()
                if json.loads(line).get('run_id') == run_id]
    temp = archive.with_name(archive.name + '.partial')
    with tarfile.open(temp, 'w:gz', compresslevel=3) as output:
        output.add(cell_path.parent, arcname='jobs/' + cell_path.parent.name, recursive=True)
        output.add(requests, arcname='private/requests/' + run_id, recursive=True)
        payload = b'\n'.join(matching) + b'\n'
        info = tarfile.TarInfo('private/request-metadata.jsonl')
        info.size = len(payload)
        info.mtime = int(time.time())
        info.mode = 0o600
        output.addfile(info, io.BytesIO(payload))
    with tarfile.open(temp, 'r:gz') as verify:
        names = verify.getnames()
        if 'private/request-metadata.jsonl' not in names or not any(name.endswith('/bench/summary.json') for name in names):
            raise RuntimeError('Backup lacks critical records: ' + run_id)
    archive_hash = sha256(temp)
    temp.rename(archive)
    record = {'run_id': run_id, 'archive_name': archive.name, 'archive_bytes': archive.stat().st_size,
              'archive_sha256': archive_hash, 'backed_up_epoch': time.time(),
              'formal_cell_sha256': sha256(cell_path), 'private_request_records': len(matching)}
    receipt.write_text(json.dumps(record, indent=2) + '\n')
    return {'run_id': run_id, 'status': 'saved', 'bytes': record['archive_bytes']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=('development', 'evaluation'), required=True)
    args = parser.parse_args()
    print(json.dumps([result for path in (root / 'jobs' / args.stage).rglob('cell.json')
                      if (result := save_cell(path)) is not None]))
