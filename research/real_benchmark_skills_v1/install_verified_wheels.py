"""Finish the same hashed inference lock using already verified local wheels."""
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path("/root/autodl-tmp/real-benchmark-skills-v1")
UV = "/root/autodl-tmp/infra-joint-planner-rtx6000/setup-20261013/venvs/project/bin/uv"
state = {"started_epoch": time.time(), "status": "running"}
receipt = ROOT / "evidence/inference-environment-repair.json"
receipt.write_text(json.dumps(state, indent=2) + "\n")
try:
    downloads = json.loads((ROOT / "evidence/large-wheel-materialization.json").read_bytes())
    if downloads["status"] != "pass":
        raise RuntimeError("Wheel materialization is incomplete")
    env = os.environ.copy()
    env.update(UV_CACHE_DIR=str(ROOT / "cache/uv"), UV_HTTP_TIMEOUT="120")
    python = str(ROOT / "venv/bin/python")
    commands = [
        [UV, "pip", "install", "--python", python, "--require-hashes", "--find-links", str(ROOT / "wheelhouse"),
         "--index-url", "https://pypi.tuna.tsinghua.edu.cn/simple/", "--requirement", str(ROOT / "inference.lock.txt")],
        [UV, "pip", "check", "--python", python],
        [python, "-c", "import json,torch,vllm,transformers; assert torch.cuda.is_available(); x=torch.eye(64,device='cuda',dtype=torch.bfloat16); assert torch.equal(x@x,x); print(json.dumps({'torch':torch.__version__,'vllm':vllm.__version__,'transformers':transformers.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name()}))"],
    ]
    for index, argv in enumerate(commands):
        with (ROOT / "logs" / f"wheel-install-{index}.log").open("w") as log:
            subprocess.run(argv, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1200)
    state.update(status="pass", versions=json.loads((ROOT / "logs/wheel-install-2.log").read_text().splitlines()[-1]))
except Exception as exc:
    state.update(status="failed", error=type(exc).__name__, detail=str(exc))
    raise
finally:
    state["finished_epoch"] = time.time()
    receipt.write_text(json.dumps(state, indent=2) + "\n")
