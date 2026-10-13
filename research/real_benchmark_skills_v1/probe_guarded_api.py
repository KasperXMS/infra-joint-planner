import json
import time
import urllib.error
import urllib.request
from pathlib import Path

root = Path("/root/autodl-tmp/real-benchmark-skills-v1")
model = str(root / "models/Qwen3.5-4B")
checks = {}
for name, body in (
    ("greedy", {"model": model, "messages": [{"role": "user", "content": "Reply with only OK."}],
                "temperature": 0, "max_tokens": 8, "stream": False}),
    ("context_rejection", {"model": model, "messages": [{"role": "user", "content": "a " * 33000}],
                           "temperature": 0, "max_tokens": 1, "stream": False}),
):
    started = time.time()
    request = urllib.request.Request("http://127.0.0.1:18000/v1/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            checks[name] = {"status": response.status, "body": json.load(response), "seconds": time.time()-started}
    except urllib.error.HTTPError as exc:
        checks[name] = {"status": exc.code, "body": json.loads(exc.read()), "seconds": time.time()-started}
    except Exception as exc:
        checks[name] = {"error": type(exc).__name__, "seconds": time.time()-started}
checks["pass"] = checks["greedy"].get("status") == 200 and checks["context_rejection"].get("status") == 400
(root / "evidence/guarded-api-smoke.json").write_text(json.dumps(checks, indent=2) + "\n")
print(json.dumps(checks))
