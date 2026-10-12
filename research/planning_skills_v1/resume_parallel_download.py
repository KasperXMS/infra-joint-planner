"""One-time SDK range-download resume, preserving already downloaded prefixes.

This changes transport only, before inference. Model repositories/revisions and
experiment conditions are unchanged. Does not restart any evaluation episode.
"""
import os
os.environ["MODELSCOPE_DOWNLOAD_PARALLEL_WORKERS"] = "8"

import json
import signal
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from modelscope.hub.api import HubApi
from modelscope_hub.constants import DOWNLOAD_PART_SIZE, DOWNLOAD_PARALLELS
from prepare_models import prepare
from runtime_guard import append, identity, register

root = Path("/root/autodl-tmp/xiaoming/planning-skills-research-v1/run-001")
with (root / "parallel-resume-receipt.json").open("x") as stream:
    json.dump({"epoch": time.time(), "pid": os.getpid(), "range_workers_per_file": DOWNLOAD_PARALLELS}, stream)
register(root, "parallel_model_download")
assert not list((root / "results").rglob("frozen-manifest.json")), "Transport change requires pre-inference state"
old = json.loads((root / "preparation-launch.json").read_text())["preparation"]
assert identity(old["pid"]) == old, "Original downloader identity changed"
os.kill(old["pid"], signal.SIGTERM)
for _ in range(100):
    proc = Path(f"/proc/{old['pid']}/stat")
    if not proc.exists() or proc.read_text().rsplit(")", 1)[1].split()[0] == "Z":
        break
    time.sleep(0.1)
else:
    raise RuntimeError("Original downloader did not exit; refusing concurrent writes")

metadata = {}
api = HubApi()
for model in ("Qwen3.5-4B", "Qwen3.5-9B"):
    files = api.get_model_files(f"Qwen/{model}", revision="master", recursive=True)
    metadata[model] = {f["Path"]: {"bytes": f["Size"]} for f in files}
(root / "repository-file-sizes.json").write_text(json.dumps(metadata, indent=2))

copied = 0
for partial in (root / "models").rglob("*.safetensors.incomplete"):
    target = partial.with_name(partial.name.removesuffix(".incomplete"))
    model = partial.parent.parent.parent.name.removeprefix("Qwen--")
    total = metadata[model][target.name]["bytes"]
    prefix_length = partial.stat().st_size
    assert prefix_length <= total
    with partial.open("rb") as source:
        for start in range(0, prefix_length, DOWNLOAD_PART_SIZE):
            end = min(start + DOWNLOAD_PART_SIZE, total) - 1
            part = Path(f"{target}_{start}_{end}")
            remaining = min(DOWNLOAD_PART_SIZE, prefix_length - start)
            with part.open("xb") as stream:
                while remaining:
                    chunk = source.read(min(8 * 1024 * 1024, remaining))
                    if not chunk:
                        raise RuntimeError("Unexpected prefix EOF")
                    stream.write(chunk)
                    remaining -= len(chunk)
                    copied += len(chunk)
append(root / "administration.jsonl", {"event": "download_transport_resumed", "epoch": time.time(),
       "preserved_prefix_bytes": copied, "sdk_range_workers": DOWNLOAD_PARALLELS,
       "same_official_repositories": True, "evaluation_episodes_restarted": 0})
with ThreadPoolExecutor(max_workers=2) as pool:
    list(pool.map(lambda model: prepare(root, model), ("Qwen/Qwen3.5-4B", "Qwen/Qwen3.5-9B")))
