import json
import time
import urllib.request
from pathlib import Path

result = {}
for endpoint in ("https://pypi.org/pypi/torch/2.11.0/json", "https://pypi.tuna.tsinghua.edu.cn/pypi/torch/2.11.0/json"):
    try:
        with urllib.request.urlopen(endpoint, timeout=10) as response:
            meta = json.load(response)
        file = next(f for f in meta["urls"] if "cp312-cp312-manylinux" in f["filename"] and "x86_64" in f["filename"])
        started = time.time()
        request = urllib.request.Request(file["url"], headers={"Range": "bytes=0-4194303"})
        with urllib.request.urlopen(request, timeout=10) as response:
            chunk = response.read(4 * 1024 * 1024)
        result[endpoint] = {"seconds": time.time() - started, "bytes": len(chunk),
                            "filename": file["filename"], "sha256": file["digests"]["sha256"]}
    except Exception as exc:
        result[endpoint] = {"error": type(exc).__name__}
print(json.dumps(result))
