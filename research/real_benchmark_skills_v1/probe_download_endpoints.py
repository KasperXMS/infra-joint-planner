import json
import time
import urllib.request

result = {}
for url in ("https://www.modelscope.cn/api/v1/models/Qwen/Qwen3.5-4B/repo/files?Revision=master&Recursive=true",
            "https://pypi.org/pypi/vllm/json",
            "https://pypi.tuna.tsinghua.edu.cn/simple/vllm/"):
    started = time.time()
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            content = response.read()
            result[url] = {"status": response.status, "bytes": len(content),
                           "has_vllm_0_31_0": b"0.31.0" in content, "seconds": time.time() - started}
    except Exception as exc:
        result[url] = {"error": type(exc).__name__, "seconds": time.time() - started}
print(json.dumps(result))
