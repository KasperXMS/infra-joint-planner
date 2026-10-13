"""Prepare isolated project/inference environments; never launch model services."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def main(root: Path) -> None:
    root = root.resolve()
    if not root.is_relative_to(Path("/root/autodl-tmp")) or root == Path("/root/autodl-tmp"):
        raise ValueError("Use a dedicated directory under /root/autodl-tmp")
    source = root / "repo"
    for name in ("venvs", "cache/pip", "cache/huggingface", "cache/modelscope", "models", "artifacts", "logs", "evidence"):
        (root / name).mkdir(parents=True, exist_ok=True)
    receipt = root / "evidence/setup.json"
    if receipt.exists() and json.loads(receipt.read_text()).get("status") == "pass":
        raise RuntimeError("Setup already passed; inspect its receipt instead of reinstalling")
    state = {"status": "running", "started_epoch": time.time(), "stages": {}, "root": str(root),
             "model_downloads": 0, "model_services_started": 0}

    def save() -> None:
        temporary = receipt.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2) + "\n")
        temporary.replace(receipt)

    env = os.environ.copy()
    for name in ("PIP_EXTRA_INDEX_URL", "PIP_TRUSTED_HOST"):
        env.pop(name, None)
    env.update(PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple/", PIP_DISABLE_PIP_VERSION_CHECK="1",
               PIP_CACHE_DIR=str(root / "cache/pip"), PIP_REQUIRE_VIRTUALENV="true",
               OMP_NUM_THREADS="8", TOKENIZERS_PARALLELISM="false")

    def run(name: str, argv: list[str], timeout: int = 1200, offline: bool = False) -> None:
        call_env = env.copy()
        if offline:
            call_env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
        with (root / "logs" / (name + ".log")).open("w") as log:
            subprocess.run(argv, cwd=source, env=call_env, stdout=log, stderr=subprocess.STDOUT,
                           check=True, timeout=timeout)

    save()
    try:
        import torch
        import torchvision
        if torch.__version__ != "2.8.0+cu128" or torchvision.__version__ != "0.23.0+cu128":
            raise RuntimeError("Base PyTorch differs; do not silently replace the GPU stack")
        state["base"] = {"python": sys.version.split()[0], "torch": torch.__version__, "torchvision": torchvision.__version__}
        for kind, inherited in (("inference", True), ("project", False)):
            args = [sys.executable, "-m", "venv"]
            if inherited:
                args.append("--system-site-packages")
            args.append(str(root / "venvs" / kind))
            run("create-" + kind, args, timeout=120)
        save()

        def install(kind: str) -> None:
            python = str(root / "venvs" / kind / "bin/python")
            pip = [python, "-m", "pip", "install", "--timeout", "30", "--retries", "2", "--index-url", env["PIP_INDEX_URL"]]
            if kind == "inference":
                run("install-inference", pip + ["--constraint", str(source / "research/planning_skills_v1/constraints-observed.txt"),
                                                "--requirement", str(source / "research/planning_skills_v1/requirements-inference.txt")])
            else:
                run("install-project", pip + ["--require-hashes", "--requirement", str(root / "project-requirements.lock.txt")])
                run("install-editable", pip + ["--no-deps", "--editable", str(source)], timeout=300)
            run("pip-check-" + kind, [python, "-m", "pip", "check"], timeout=60)
            run("freeze-" + kind, [python, "-m", "pip", "freeze"], timeout=60)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = {pool.submit(install, kind): kind for kind in ("project", "inference")}
            failures = []
            for future in concurrent.futures.as_completed(futures):
                kind = futures[future]
                try:
                    future.result()
                    state["stages"][kind] = "dependencies_ready"
                except Exception as error:
                    state["stages"][kind] = {"status": "failed", "error_type": type(error).__name__}
                    failures.append(kind)
                save()
            if failures:
                raise RuntimeError("Dependency setup failed: " + ", ".join(failures))

        inference = str(root / "venvs/inference/bin/python")
        project = str(root / "venvs/project/bin/python")
        run("smoke-inference", [inference, str(source / "scripts/check_autodl_rtx6000.py"), "--output",
                                str(root / "evidence/inference-smoke.json")], timeout=120, offline=True)
        run("smoke-project", [str(root / "venvs/project/bin/infra-joint"), "--help"], timeout=60)
        run("test-microbench", [inference, "-m", "unittest", "discover", "-s", "research/planning_skills_v1",
                                "-p", "test_microbench.py", "-v"], timeout=120, offline=True)
        run("test-worker", [project, "-m", "pytest", "tests/test_worker_api.py", "tests/test_workflow_contracts.py"], timeout=120)
        state["stages"]["verification"] = "pass"
        for name in ("uv.lock", "pyproject.toml", "research/planning_skills_v1/requirements-inference.txt",
                     "research/planning_skills_v1/constraints-observed.txt"):
            state.setdefault("source_sha256", {})[name] = hashlib.sha256((source / name).read_bytes()).hexdigest()
        (root / "activate-inference.sh").write_text(
            f"source {root}/venvs/inference/bin/activate\nexport HF_HOME={root}/cache/huggingface\n"
            f"export MODELSCOPE_CACHE={root}/cache/modelscope\nexport OMP_NUM_THREADS=8 TOKENIZERS_PARALLELISM=false\n"
            "export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1\n")
        (root / "activate-project.sh").write_text(f"source {root}/venvs/project/bin/activate\ncd {source}\n")
        state.update(status="pass", finished_epoch=time.time())
        save()
    except Exception as error:
        state.update(status="failed", finished_epoch=time.time(), error_type=type(error).__name__, error=str(error))
        save()
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    main(parser.parse_args().root)
