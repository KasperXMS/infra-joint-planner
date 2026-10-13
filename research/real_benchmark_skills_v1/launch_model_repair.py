"""Resume model provisioning after a rejected incomplete config transfer."""
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

root = Path("/root/autodl-tmp/real-benchmark-skills-v1")
lock_source = root.parent / "real-benchmark-models-repair.lock.json"
locks = json.loads(lock_source.read_bytes())
config_source = root.parent / "real-benchmark-model-configs-repair.tar.gz"
with tarfile.open(config_source) as archive:
    for member in archive.getmembers():
        if member.isfile():
            model, name = member.name.split("/", 1)
            data = archive.extractfile(member).read()
            assert hashlib.sha256(data).hexdigest() == locks[model]["files"][name]["sha256"]
shutil.copy2(lock_source, root / "models.lock.json")
shutil.copy2(config_source, root / "model-configs.tar.gz")
script = root.parent / "prepare_real_benchmark_inference_repair.py"
with (root / "logs/models-repair.log").open("w") as log:
    process = subprocess.Popen([sys.executable, str(script), "--models-only"],
                               stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
(root / "model-repair.pid").write_text(str(process.pid))
print(json.dumps({"pid": process.pid, "root": str(root), "reason": "Initial config archive was copied before SFTP completed; no model runs were affected."}))
