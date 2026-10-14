"""Read-only status for the existing study-owned AutoDL GPU sampler."""
import json
import time
from pathlib import Path

p=Path('/root/autodl-tmp/model-aware-skill-compilation/gpu_samples.jsonl')
pid=7450
print(json.dumps({'sampler_pid_alive':Path(f'/proc/{pid}').exists(),
                  'log_exists':p.exists(),
                  'log_bytes':p.stat().st_size if p.exists() else 0,
                  'log_age_seconds':round(time.time()-p.stat().st_mtime,1) if p.exists() else None}))
