import json
import urllib.request
from pathlib import Path

root = Path("/root/autodl-tmp/real-benchmark-skills-v1")
result = {"log": (root / "logs/transformers-api-probe.log").read_text(errors="replace")[-3500:]}
try:
    with urllib.request.urlopen("http://127.0.0.1:18001/health", timeout=3) as response:
        result["health"] = response.status
except Exception as exc:
    result["health_error"] = type(exc).__name__
print(json.dumps(result))
