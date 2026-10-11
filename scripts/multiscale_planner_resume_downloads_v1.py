"""One bounded network continuation; no inference or existing-service mutation."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import sys
import time
from contextlib import suppress
from pathlib import Path

ROOT = Path("/home/super/xiaoming/multiscale-planner-evaluation-v1/run-001")
sys.path.insert(0, str(ROOT / "app/scripts"))
from multiscale_planner_deploy_v1 import api, write  # noqa: E402


def main():
    assert not (ROOT / "network-continuation.json").exists()
    assert (ROOT / "qwen35-4b-download.json").exists()
    identities = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            argv = (proc / "cmdline").read_bytes().decode().split("\0")
            if Path(argv[0]).name.startswith("python") and argv[1:2] == [
                str(ROOT / "app/scripts/multiscale_planner_deploy_v1.py")
            ]:
                identities.append(int(proc.name))
        except OSError:
            pass
    assert len(identities) == 1, "download client ownership must be exact"
    parts = []
    for path in (ROOT / "models/blobs").glob("*partial-*"):
        with suppress(ValueError, OSError):
            parts.append(json.loads(path.read_text()))
    write(
        ROOT / "network-continuation.json",
        {
            "reason": "one incomplete network shard while other 15 shards completed",
            "original_client_pid": identities[0],
            "completed_bytes": sum(p.get("Completed", 0) for p in parts),
            "total_bytes": sum(p.get("Size", 0) for p in parts),
            "maximum_continuations": 1,
            "continuation_timeout_seconds": 600,
            "model_inference_calls": 0,
            "executor_services_modified": False,
            "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
    )
    os.kill(identities[0], signal.SIGTERM)
    time.sleep(2)
    for candidate, tag in [("qwen35-9b", "qwen3.5:9b"), ("ministral3-3b", "ministral-3:3b")]:
        if (ROOT / (candidate + "-download.json")).exists():
            continue
        begin = time.monotonic()
        try:
            status = api("pull", {"model": tag, "stream": False}, timeout=600)
            show = api("show", {"model": tag})
            manifest = (
                ROOT
                / "models/manifests/registry.ollama.ai/library"
                / tag.split(":")[0]
                / tag.split(":")[1]
            )
            layers = json.loads(manifest.read_text())["layers"]
            write(
                ROOT / (candidate + "-download.json"),
                {
                    "tag": tag,
                    "official_source": "https://ollama.com/library/" + tag,
                    "status": status,
                    "elapsed_seconds": time.monotonic() - begin,
                    "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                    "layers": layers,
                    "show": show,
                    "version": api("version"),
                    "bounded_network_continuation": True,
                },
            )
            print(
                json.dumps({"downloaded": candidate, "seconds": time.monotonic() - begin}),
                flush=True,
            )
        except Exception as exc:
            write(
                ROOT / (candidate + "-download-error.json"),
                {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "elapsed_seconds": time.monotonic() - begin,
                    "maximum_continuations_reached": True,
                },
            )
    write(ROOT / "downloads-finished.json", {"done": True, "bounded_network_continuation": True})


if __name__ == "__main__":
    main()
