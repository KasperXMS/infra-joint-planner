"""Read-only service provenance; no request prompts or credentials are exported."""
import hashlib
import importlib.metadata
import json
import subprocess
import urllib.request
from pathlib import Path

root = Path('/root/autodl-tmp/real-benchmark-skills-v1')
service = json.loads((root / 'evidence/model-service.json').read_bytes())
materialization = json.loads((root / 'evidence/ranged-model-materialization.json').read_bytes())
with urllib.request.urlopen('http://127.0.0.1:18000/study/status', timeout=10) as response:
    status = json.load(response)
print(json.dumps({'service': service, 'idle_status': status,
    'versions': {name: importlib.metadata.version(name) for name in ('torch', 'transformers')},
    'verified_model_files': len(materialization['verified_files']),
    'verified_model_bytes': sum(item['bytes'] for item in materialization['verified_files']),
    'source_sha256': hashlib.sha256((root / 'guarded_transformers_server.py').read_bytes()).hexdigest(),
    'gpu': subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used', '--format=csv,noheader'], capture_output=True, text=True).stdout,
    'disk': subprocess.run(['df', '-B1', str(root)], capture_output=True, text=True).stdout}))
