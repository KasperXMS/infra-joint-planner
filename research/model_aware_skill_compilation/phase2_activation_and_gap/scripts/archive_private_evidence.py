"""Hash retained raw traffic and cell traces; publish only aggregate receipts."""
import hashlib
import json
from pathlib import Path

study = Path(__file__).resolve().parents[1]
private = Path('/root/skillsbench-local-20261013/private/model-aware-phase2')
manifest = json.loads((study / 'frozen-manifest-v2.json').read_text())
entries = []


def digest(path):
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


for path in sorted((private / 'requests').glob('*.bin')):
    entries.append({'scope': 'model-traffic', 'path': path.name,
                    'bytes': path.stat().st_size, 'sha256': digest(path)})
for path in sorted((study / 'trials').rglob('*')):
    if not path.is_file():
        continue
    # Codex's sqlite/session state duplicates sensitive prompt and tool data.
    if path.suffix in {'.sqlite', '.sqlite-shm', '.sqlite-wal', '.lock'}:
        continue
    relative = path.relative_to(study / 'trials').as_posix()
    entries.append({'scope': 'trial-trace', 'path': relative,
                    'bytes': path.stat().st_size, 'sha256': digest(path)})
bridge_log = private / 'requests.jsonl'
entries.append({'scope': 'bridge-index', 'path': bridge_log.name,
                'bytes': bridge_log.stat().st_size, 'sha256': digest(bridge_log)})
full = {'entries': entries, 'root': str(private),
        'note': 'Private hashes and relative names; never commit this manifest.'}
full_bytes = (json.dumps(full, sort_keys=True, separators=(',', ':')) + '\n').encode()
full_path = private / 'archive-hashes.private.json'
full_path.write_bytes(full_bytes)
public = {'private_manifest_sha256': hashlib.sha256(full_bytes).hexdigest(),
          'private_file_count': len(entries),
          'private_total_bytes': sum(x['bytes'] for x in entries),
          'model_traffic_files': sum(x['scope'] == 'model-traffic' for x in entries),
          'trial_trace_files': sum(x['scope'] == 'trial-trace' for x in entries),
          'planned_activation_cells': len(manifest['trial_cells']),
          'path': str(full_path)}
(study / 'evidence/private-archive-summary.json').write_text(json.dumps(public, indent=2) + '\n')
print(json.dumps(public))
