"""Prepare a separate pinned vLLM environment and verified official model bytes.

No task code is executed on AutoDL. No instance lifecycle operations occur.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

ROOT = Path("/root/autodl-tmp/real-benchmark-skills-v1")
UV = "/root/autodl-tmp/infra-joint-planner-rtx6000/setup-20261013/venvs/project/bin/uv"


def main(only_models=False):
    for name in ("logs", "evidence", "models", "cache/uv"):
        (ROOT / name).mkdir(parents=True, exist_ok=True)
    state = {"started_epoch": time.time(), "status": "running", "stages": {}}

    def save():
        receipt = ROOT / "evidence" / ("model-materialization-repair.json" if only_models else "preparation.json")
        temporary = receipt.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2) + "\n")
        temporary.replace(receipt)

    save()

    def install():
        env = os.environ.copy()
        env.update(UV_CACHE_DIR=str(ROOT / "cache/uv"), UV_HTTP_TIMEOUT="120")
        requirements = ROOT / "inference.in"
        requirements.write_text("vllm==0.20.2\ntransformers==5.17.0\n")
        commands = [
            [UV, "venv", "--python", sys.executable, str(ROOT / "venv")],
            [UV, "pip", "compile", "--python", str(ROOT / "venv/bin/python"), "--generate-hashes",
             "--index-url", "https://pypi.tuna.tsinghua.edu.cn/simple/", str(requirements),
             "--output-file", str(ROOT / "inference.lock.txt")],
            [UV, "pip", "install", "--python", str(ROOT / "venv/bin/python"), "--require-hashes",
             "--index-url", "https://pypi.tuna.tsinghua.edu.cn/simple/",
             "--requirement", str(ROOT / "inference.lock.txt")],
            [str(ROOT / "venv/bin/python"), "-c",
             "import torch,vllm,transformers; print(torch.__version__,vllm.__version__,transformers.__version__); assert torch.cuda.is_available(); print(torch.cuda.get_device_name())"],
        ]
        for index, argv in enumerate(commands):
            with (ROOT / "logs" / f"install-{index}.log").open("w") as log:
                subprocess.run(argv, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=2400, check=True)
        return "installed"

    def download_models():
        with tarfile.open(ROOT / "model-configs.tar.gz") as archive:
            archive.extractall(ROOT / "models", filter="data")
        locks = json.loads((ROOT / "models.lock.json").read_bytes())
        def download(item):
            model, name, info = item
            target = ROOT / "models" / model / name
            if target.exists():
                with target.open("rb") as source:
                    valid = hashlib.file_digest(source, "sha256").hexdigest() == info["sha256"]
                if not valid:
                    target.replace(target.with_suffix(target.suffix + ".invalid-initial-transfer"))
            if not target.exists():
                temporary = target.with_suffix(target.suffix + ".partial")
                digest = hashlib.sha256()
                with urllib.request.urlopen(info["download_url"], timeout=120) as response, temporary.open("wb") as output:
                    while chunk := response.read(8 * 1024 * 1024):
                        output.write(chunk)
                        digest.update(chunk)
                if digest.hexdigest() != info["sha256"] or temporary.stat().st_size != info["bytes"]:
                    raise ValueError("Official weight digest differs: " + name)
                temporary.replace(target)
            else:
                with target.open("rb") as source:
                    if hashlib.file_digest(source, "sha256").hexdigest() != info["sha256"]:
                        raise ValueError("Existing weight digest differs: " + name)
            return {"model": model, "file": name, "sha256": info["sha256"], "bytes": info["bytes"]}
        items = [(model, name, info) for model, lock in locks.items() for name, info in lock["files"].items()
                 if "download_url" in info]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            weights = list(pool.map(download, items))
        for model, lock in locks.items():
            for name, info in lock["files"].items():
                if "download_url" not in info:
                    target = ROOT / "models" / model / name
                    if hashlib.sha256(target.read_bytes()).hexdigest() != info["sha256"]:
                        raise ValueError("Config digest differs: " + name)
        (ROOT / "evidence/model-weights.json").write_text(json.dumps(weights, indent=2) + "\n")
        return "all_official_bytes_verified"

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        jobs = {pool.submit(download_models): "models"}
        if not only_models:
            jobs[pool.submit(install)] = "environment"
        for future in concurrent.futures.as_completed(jobs):
            name = jobs[future]
            try:
                state["stages"][name] = {"status": "pass", "result": future.result()}
            except Exception as exc:
                state["stages"][name] = {"status": "failed", "error": type(exc).__name__, "detail": str(exc)}
            save()
    state.update(status="pass" if all(s["status"] == "pass" for s in state["stages"].values()) else "failed",
                 finished_epoch=time.time())
    save()
    print(json.dumps(state))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--models-only", action="store_true")
    main(parser.parse_args().models_only)
