"""Fetch verified model files with bounded parallel HTTP ranges and resumable chunks."""
import concurrent.futures
import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path

ROOT = Path("/root/autodl-tmp/real-benchmark-skills-v1")
CHUNK = 32 * 1024 * 1024


def file_sha(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def materialize(model, name, info):
    target = ROOT / "models" / model / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size == info["bytes"] and file_sha(target) == info["sha256"]:
        return
    if "download_url" not in info:
        raise ValueError("Missing official config: " + str(target))
    temporary = target.with_suffix(target.suffix + ".ranged.partial")
    parts_path = target.with_suffix(target.suffix + ".parts.json")
    completed = set(json.loads(parts_path.read_text())) if parts_path.exists() else set()
    if not temporary.exists():
        with temporary.open("wb") as output:
            output.truncate(info["bytes"])
        completed = set()
    fd = os.open(temporary, os.O_RDWR)
    started = time.time()

    def fetch(index):
        start, stop = index * CHUNK, min((index + 1) * CHUNK, info["bytes"]) - 1
        for attempt in range(3):
            try:
                request = urllib.request.Request(info["download_url"], headers={"Range": f"bytes={start}-{stop}"})
                with urllib.request.urlopen(request, timeout=120) as response:
                    if response.status != 206 or not response.headers.get("Content-Range", "").startswith(f"bytes {start}-"):
                        raise ValueError("Source did not honor HTTP range")
                    offset = start
                    while data := response.read(4 * 1024 * 1024):
                        if offset + len(data) > stop + 1:
                            raise ValueError("HTTP range too long")
                        os.pwrite(fd, data, offset)
                        offset += len(data)
                    if offset != stop + 1:
                        raise ValueError("HTTP range truncated")
                return index
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)

    total = (info["bytes"] + CHUNK - 1) // CHUNK
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(fetch, index) for index in range(total) if index not in completed]
            for future in concurrent.futures.as_completed(futures):
                completed.add(future.result())
                parts_path.write_text(json.dumps(sorted(completed)))
                if len(completed) % 16 == 0 or len(completed) == total:
                    print(json.dumps({"model": model, "file": name, "chunks": len(completed), "total_chunks": total,
                                      "seconds": time.time() - started}), flush=True)
        os.fsync(fd)
    finally:
        os.close(fd)
    if file_sha(temporary) != info["sha256"]:
        raise ValueError("Official full-file SHA256 mismatch: " + name)
    temporary.replace(target)


def main():
    state = {"started_epoch": time.time(), "status": "running", "verified_files": []}
    receipt = ROOT / "evidence/ranged-model-materialization.json"
    def save():
        temp = receipt.with_suffix(".tmp")
        temp.write_text(json.dumps(state, indent=2) + "\n")
        temp.replace(receipt)
    save()
    try:
        for model, lock in json.loads((ROOT / "models.lock.json").read_bytes()).items():
            for name, info in lock["files"].items():
                materialize(model, name, info)
                state["verified_files"].append({"model": model, "file": name, "sha256": info["sha256"], "bytes": info["bytes"]})
                save()
        state["status"] = "pass"
    except Exception as exc:
        state.update(status="failed", error=type(exc).__name__, detail=str(exc))
        raise
    finally:
        state["finished_epoch"] = time.time()
        save()


if __name__ == "__main__":
    main()
