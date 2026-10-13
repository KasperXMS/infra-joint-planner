"""One real official API tool-call compatibility check, separate from benchmark runs."""
import json
import time
import urllib.request
from pathlib import Path

root = Path("/root/autodl-tmp/real-benchmark-skills-v1")
body = {"model": str(root / "models/Qwen3.5-4B"), "messages": [
    {"role": "system", "content": "Use the provided function to perform arithmetic."},
    {"role": "user", "content": "Call add with a=2 and b=3."}],
    "tools": [{"type": "function", "function": {"name": "add", "description": "Add two integers.",
               "parameters": {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                              "required": ["a", "b"]}}}],
    "temperature": 0, "max_tokens": 128, "stream": False,
    "chat_template_kwargs": {"enable_thinking": False}}
request = urllib.request.Request("http://127.0.0.1:18001/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
started = time.time()
try:
    with urllib.request.urlopen(request, timeout=45) as response:
        result = {"http_status": response.status, "response": json.load(response), "seconds": time.time() - started,
                  "classification": "API compatibility, not a benchmark outcome"}
except Exception as exc:
    result = {"error": type(exc).__name__, "seconds": time.time() - started}
    if hasattr(exc, "read"):
        result["body"] = exc.read().decode(errors="replace")[-2000:]
(root / "evidence/transformers-tool-api-smoke.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
