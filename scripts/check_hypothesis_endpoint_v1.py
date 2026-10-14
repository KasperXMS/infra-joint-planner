"""Check the unchanged resident Ollama model and its GGUF tokenizer."""

import json
import urllib.request

base = "http://127.0.0.1:11436"
with urllib.request.urlopen(base + "/api/ps", timeout=5) as response:
    active = json.loads(response.read())
assert any(
    model["name"] == "qwen35-27b-resident-32k-v1:latest"
    and model["context_length"] == 32768
    for model in active["models"]
)
body = json.dumps({"content": "hello"}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:37797/tokenize",
    data=body,
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=30) as response:
    data = json.loads(response.read())
assert isinstance(data.get("tokens"), list) and data["tokens"]
print(json.dumps({"model": active["models"][0]["name"], "token_count": len(data["tokens"])}))
