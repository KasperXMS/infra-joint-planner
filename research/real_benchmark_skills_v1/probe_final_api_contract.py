"""Minimal final API contract check, not a benchmark or an intervention trial."""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

root = Path("/root/skillsbench-local-20261013")
token = (root / "private/bridge.key").read_text().strip()
base = "http://172.17.0.1:18080/runs/final-api-contract/v1/"
headers = {"Content-Type": "application/json", "Authorization": "Bearer " + token}
body = {"model": "Qwen3.5-4B", "messages": [
    {"role": "user", "content": "Call arithmetic with a=2 and items=[1,10]."}],
    "tools": [{"type": "function", "function": {"name": "arithmetic", "description": "Process integers.",
               "parameters": {"type": "object", "properties": {"a": {"type": "integer"},
                    "items": {"anyOf": [{"type": "array", "items": {"type": "integer"}}, {"type": "null"}]}},
                    "required": ["a", "items"]}}}], "temperature": 0, "stream": False}
started = time.time()
with urllib.request.urlopen(urllib.request.Request(base + "chat/completions", data=json.dumps(body).encode(), headers=headers), timeout=45) as response:
    data = json.load(response)
call = data["choices"][0]["message"]["tool_calls"][0]
arguments = json.loads(call["function"]["arguments"])
assert arguments == {"a": 2, "items": [1, 10]}, arguments
with urllib.request.urlopen(urllib.request.Request(base + "study_status", headers=headers), timeout=10) as response:
    status = json.load(response)
assert status["pending_requests"] == status["running_generations"] == 0
result = {"status": "pass", "typed_arguments": arguments, "usage": data["usage"],
          "seconds": time.time() - started, "service_status": status,
          "classification": "API compatibility, excluded from all benchmark denominators"}
(root / "evidence/final-api-contract.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
