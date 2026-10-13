import concurrent.futures
import json
import time
import urllib.request
from pathlib import Path

root = Path("/root/autodl-tmp/real-benchmark-skills-v1")
wheel = json.loads((root / "large-wheels.lock.json").read_bytes())[0]
original = wheel["download_url"]
urls = [original, original.replace("https://files.pythonhosted.org", "https://pypi.tuna.tsinghua.edu.cn"),
        original.replace("https://files.pythonhosted.org", "https://mirrors.aliyun.com/pypi")]


def probe(url):
    started = time.time()
    try:
        request = urllib.request.Request(url, headers={"Range": "bytes=0-65535"})
        with urllib.request.urlopen(request, timeout=8) as response:
            data = response.read(65536)
            return {"url": url, "bytes": len(data), "seconds": time.time() - started,
                    "status": response.status, "content_range": response.headers.get("Content-Range")}
    except Exception as exc:
        return {"url": url, "error": type(exc).__name__, "seconds": time.time() - started}


with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    print(json.dumps({"probes": list(pool.map(probe, urls))}))
