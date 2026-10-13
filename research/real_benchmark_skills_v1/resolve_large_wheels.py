"""Resolve large Linux cp312 wheels from official PyPI for verified range fetches."""
import concurrent.futures
import hashlib
import json
import re
import urllib.request
from pathlib import Path

from packaging.tags import cpython_tags, compatible_tags
from packaging.utils import parse_wheel_filename

root = Path(".code-staging")
lock = (root / "inference.lock.txt").read_text()
packages = re.findall(r"^([A-Za-z0-9_.-]+)==([^\s;]+)", lock, re.M)
platforms = [f"manylinux_2_{minor}_x86_64" for minor in range(35, 16, -1)] + ["manylinux2014_x86_64", "manylinux2010_x86_64", "manylinux1_x86_64", "linux_x86_64"]
tags = set(cpython_tags((3, 12), platforms=platforms)) | set(compatible_tags((3, 12), interpreter="cp312", platforms=platforms))


def resolve(item):
    name, version = item
    with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/{version}/json", timeout=60) as response:
        meta = json.load(response)
    candidates = []
    for file in meta["urls"]:
        if file["filename"].endswith(".whl"):
            *_, wheel_tags = parse_wheel_filename(file["filename"])
            if tags & wheel_tags:
                candidates.append(file)
    if not candidates:
        return None
    file = max(candidates, key=lambda f: f["size"])
    if file["size"] < 5 * 1024 * 1024:
        return None
    digest = file["digests"]["sha256"]
    if digest not in lock:
        raise ValueError("Official wheel not allowed by hashed dependency lock: " + file["filename"])
    return {"filename": file["filename"], "sha256": digest, "bytes": file["size"], "download_url": file["url"]}


with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
    wheels = [f for f in pool.map(resolve, packages) if f]
(root / "large-wheels.lock.json").write_text(json.dumps(wheels, indent=2) + "\n")
print(json.dumps({"wheels": len(wheels), "total_bytes": sum(w["bytes"] for w in wheels), "lock_sha256": hashlib.sha256(lock.encode()).hexdigest()}))
