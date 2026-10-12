"""Download official Qwen weights from ModelScope and retain file identities."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from modelscope import snapshot_download

from runtime_guard import append, register


def prepare(root: Path, model_id: str) -> dict:
    begun = time.time()
    append(root / "provisioning.jsonl", {"event": "download_started", "model_id": model_id, "epoch": begun})
    kwargs = {"model_id": model_id, "cache_dir": str(root / "models"), "revision": "master"}
    if "max_workers" in inspect.signature(snapshot_download).parameters:
        kwargs["max_workers"] = 8
    path = Path(snapshot_download(**kwargs))
    files = []
    for file in sorted(path.rglob("*")):
        if file.is_file() and file.suffix in {".json", ".safetensors", ".jinja", ".txt"}:
            digest = hashlib.sha256()
            with file.open("rb") as stream:
                for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                    digest.update(chunk)
            files.append({"path": str(file.relative_to(path)), "bytes": file.stat().st_size, "sha256": digest.hexdigest()})
    record = {"model_id": model_id, "requested_revision": "master", "local_path": str(path),
              "identity_policy": "all actual safetensors/config/tokenizer bytes hashed; mutable master is not a commit pin",
              "begun_epoch": begun, "finished_epoch": time.time(), "files": files}
    target = root / (model_id.split("/")[-1] + "-identity.json")
    with target.open("x") as stream:
        json.dump(record, stream, indent=2)
    append(root / "provisioning.jsonl", {"event": "download_finished", "model_id": model_id, "epoch": time.time()})
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    register(args.root, "model_provisioning")
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda model: prepare(args.root, model), ("Qwen/Qwen3.5-4B", "Qwen/Qwen3.5-9B")))
