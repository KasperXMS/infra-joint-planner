"""Generic environment/accounting repair provenance; no Agent behavior changes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import prepare_sdk_native_infra_worker_v1_3 as original_workers
import yaml
from run_predecision_matrix_v1 import HOSTS, remote_python, write_new

from infra_joint.control.provenance import provenance_sha256

PARENT_PRICE_SHA256 = "279d993cca0fd6b3206cbdb8eb5c1aab5008c3b35ed0424bec5d7587552122b6"
PARENT_EXECUTION_SHA256 = "38c9b72f641e22ddef770828221d4e4d41b7fa25a506f3e8b99bc7e337953133"
DECODER_RECEIPT_SHA256 = "79f793c856eadea8d0ebadfae51ceda2250f98870f5b64605b873ab6fca2aab2"
ARM_FFMPEG_SHA256 = "d45da9277fbb9931ac5e0ddc324b5371a742db28c245b49023e9e31b56661f0c"
ARM_FFMPEG = Path("/mnt/ssd/large-scale-cost-guidance-v1/environment-repair-001"
                  "/ffmpeg-av1-h264-sw-v8.0.1/bin/ffmpeg")


def sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def repaired_prices(root: Path, app: Path) -> dict[str, Any]:
    parent = root / "preparation/pricing-001/price-freeze.json"
    if sha256(parent) != PARENT_PRICE_SHA256:
        raise RuntimeError("original price/FX freeze drift")
    original = json.loads(parent.read_text())
    return {**original, "version": "large-scale-api-list-price-repair-v1",
            "parent_price_freeze_sha256": PARENT_PRICE_SHA256,
            "calculator_source_sha256": sha256(app / "src/infra_joint/experiments/api_cost.py"),
            "implementation_repair": "exact order-independent per-call receipt aggregation",
            "preserved_excluded_attempts": 1}


def verified_prices(root: Path, app: Path) -> tuple[Path, str]:
    path = root / "preparation/pricing-002/price-freeze.json"
    if json.loads(path.read_text()) != repaired_prices(root, app):
        raise RuntimeError("repaired pricing/calculator provenance drift")
    return path, sha256(path)


def prepare_prices(root: Path, app: Path) -> None:
    # Original rates, FX date, source receipts and per-call calculation are unchanged.
    write_new(root / "preparation/pricing-002/price-freeze.json", repaired_prices(root, app))


def prepare(cell_path: Path, agent_id: str, output: Path) -> None:
    """Derive the same Worker surface, changing only Jetson's decoder executable."""
    if output.exists():
        raise FileExistsError(f"refusing to overwrite Worker config: {output}")
    cell = original_workers._yaml(cell_path)
    if agent_id not in HOSTS or agent_id not in cell["fresh_worker_stores"]:
        raise ValueError("unknown Worker or missing fresh store")
    base_name = "strong-4090" if agent_id == "strong-4090" else agent_id.lower()
    worker = original_workers._yaml(original_workers.REPO /
                                   "configs/experiments/workers/blind-3family-video-v1.3" /
                                   f"worker-{base_name}.yaml")
    url = urlparse(cell["worker_urls"][agent_id])
    if url.scheme != "http" or url.port is None:
        raise ValueError("Worker URL must declare an HTTP port")
    worker["port"] = url.port
    worker["artifact_root"] = cell["fresh_worker_stores"][agent_id]
    if "model_service_timeout_seconds" in cell:
        for deployment in worker.get("deployments", {}).values():
            backend = deployment["model"]
            if backend["backend"] == "openai_compatible":
                backend["request_timeout_seconds"] = cell["model_service_timeout_seconds"]
    if agent_id != "strong-4090":
        worker["ffmpeg_executable"] = str(ARM_FFMPEG)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        yaml.safe_dump(worker, stream, sort_keys=False, allow_unicode=True)


def environment_fingerprint(root: Path) -> dict[str, Any]:
    """Validate pinned actual binaries on all nodes without starting Workers/models/tc."""
    receipt_path = root / "readiness/decoder-repair-validation-001.json"
    if sha256(receipt_path) != DECODER_RECEIPT_SHA256:
        raise RuntimeError("decoder repair receipt drift")
    receipt = json.loads(receipt_path.read_text())
    if set(receipt) != {"A4", "A5", "A28"}:
        raise RuntimeError("incomplete decoder repair receipt")
    binaries = {}
    for agent, host in HOSTS.items():
        if host is None:
            binaries[agent] = sha256(Path("/usr/bin/ffmpeg"))
            continue
        row = receipt[agent]
        if (row["binary_sha256"] != ARM_FFMPEG_SHA256
                or not row["historical_binary_unchanged"]
                or any(row["decoder_probes"][codec]["returncode"] != 0
                       or row["decoder_probes"][codec]["frames"] < 1
                       or row["decoder_probes"][codec]["jpeg_bytes"] < 1
                       for codec in ("h264", "av1"))):
            raise RuntimeError("decoder probes did not establish required codec execution")
        digest = remote_python(host, "import hashlib; from pathlib import Path; "
                               f"print(hashlib.sha256(Path({str(ARM_FFMPEG)!r})"
                               ".read_bytes()).hexdigest())").strip()
        if digest != ARM_FFMPEG_SHA256:
            raise RuntimeError("actual Worker decoder binary drift")
        binaries[agent] = digest
    return {"decoder_receipt_sha256": DECODER_RECEIPT_SHA256,
            "arm_ffmpeg_executable": str(ARM_FFMPEG), "binary_sha256": binaries}


def parent_execution(root: Path) -> dict[str, Any]:
    path = root / "execution-freeze.json"
    if sha256(path) != PARENT_EXECUTION_SHA256:
        raise RuntimeError("original execution freeze drift")
    return json.loads(path.read_text())


def original_attempt(root: Path) -> dict[str, Any]:
    events = [json.loads(line) for line in
              (root / "phase1-attempts.jsonl").read_text().splitlines()]
    reserved = next(e for e in events if e["event"] == "reserved")
    settled = next(e for e in events if e["event"] == "settled")
    if reserved["run_id"] != settled["run_id"] or settled["disposition"] != "confounder":
        raise RuntimeError("generic repair must refer to original excluded attempt")
    return {"run_id": reserved["run_id"], "cell_id": reserved["cell_id"],
            "original_admission_sha256": settled["receipt_sha256"],
            "parent_execution_sha256": provenance_sha256(parent_execution(root))}
