"""One compatibility probe of the already prepared official Transformers server.

No benchmark task is executed and no formal backend choice is changed here.
"""
import json
import os
import subprocess
import time
from pathlib import Path

root = Path("/root/autodl-tmp/real-benchmark-skills-v1")
python = "/root/autodl-tmp/infra-joint-planner-rtx6000/setup-20261013/venvs/inference/bin/python"
program = (
    "from transformers.cli.serve import Serve; "
    f"Serve(force_model={str(root / 'models/Qwen3.5-4B')!r}, device='cuda:0', dtype='bfloat16', "
    "attn_implementation='sdpa', reasoning='off', host='127.0.0.1', port=18001, "
    "default_seed=42, continuous_batching=False, compile=False)"
)
env = os.environ.copy()
env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", OMP_NUM_THREADS="8", TOKENIZERS_PARALLELISM="false")
env["PYTHONPATH"] = "/root/autodl-tmp/infra-joint-planner-rtx6000/setup-20261013/venvs/project/lib/python3.12/site-packages"
with (root / "logs/transformers-api-probe.log").open("w") as log:
    process = subprocess.Popen([python, "-c", program], env=env, stdin=subprocess.DEVNULL,
                               stdout=log, stderr=log, start_new_session=True)
(root / "transformers-api-probe.pid").write_text(str(process.pid))
print(json.dumps({"pid": process.pid, "epoch": time.time(), "port": 18001, "classification": "compatibility_only"}))
