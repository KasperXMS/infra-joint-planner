"""Create a complete-line private copy of remote generation counters for SFTP."""
import hashlib
import json
import time
from pathlib import Path

root = Path('/root/autodl-tmp/real-benchmark-skills-v1/private')
source = root / 'generation-metadata.jsonl'
raw = source.read_bytes()
complete = raw[:raw.rfind(b'\n') + 1]
for line in complete.splitlines():
    json.loads(line)
target = root / f'generation-metadata-snapshot-{int(time.time())}.jsonl'
target.write_bytes(complete)
print(json.dumps({'snapshot': str(target), 'bytes': len(complete),
                  'sha256': hashlib.sha256(complete).hexdigest(),
                  'complete_records': len(complete.splitlines())}))
