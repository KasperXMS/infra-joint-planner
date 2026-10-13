"""Apply a declared tokenizer chat-EOS compatibility correction before formal runs."""
import json
import os
import signal
import subprocess
import time
from pathlib import Path

root = Path("/root/autodl-tmp/real-benchmark-skills-v1")
receipt_path = root / "evidence/model-service.json"
previous = json.loads(receipt_path.read_bytes())
pid = previous["pid"]
command_path = Path(f"/proc/{pid}/cmdline")
if command_path.exists() and command_path.read_bytes():
    assert str(root / "guarded_transformers_server.py").encode() in command_path.read_bytes()
    os.kill(pid, signal.SIGTERM)
    for _ in range(100):
        if not command_path.exists() or not command_path.read_bytes():
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("Study service did not exit")
env = os.environ.copy()
env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", OMP_NUM_THREADS="8", TOKENIZERS_PARALLELISM="false",
           PYTHONPATH="/root/autodl-tmp/infra-joint-planner-rtx6000/setup-20261013/venvs/project/lib/python3.12/site-packages")
with (root / "logs/Qwen3.5-4B-transformers-eos-corrected.log").open("w") as log:
    process = subprocess.Popen(previous["argv"], env=env, stdin=subprocess.DEVNULL,
                               stdout=log, stderr=log, start_new_session=True)
previous.update(pid=process.pid, epoch=time.time(), status="starting", chat_eos_correction="Include official tokenizer EOS as a stop token, alongside model EOS; no schema decoding or argument repair.")
receipt_path.write_text(json.dumps(previous, indent=2) + "\n")
print(json.dumps(previous))
