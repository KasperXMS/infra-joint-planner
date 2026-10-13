import json
import time
import urllib.request
from pathlib import Path

root = Path("/root/skillsbench-local-20261013")
token = (root / "private/bridge.key").read_text().strip()
body = {"model": "Qwen3.5-4B", "messages": [{"role": "user", "content": "Reply with only OK."}],
        "temperature": 0, "max_tokens": 8, "stream": False}
request = urllib.request.Request("http://172.17.0.1:18080/runs/relay-smoke/v1/chat/completions",
    data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + token})
started = time.time()
try:
    with urllib.request.urlopen(request, timeout=45) as response:
        result = {"status": response.status, "response": json.load(response), "seconds": time.time() - started}
except Exception as exc:
    result = {"error": type(exc).__name__, "seconds": time.time() - started}
(root / "evidence/relay-smoke.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
