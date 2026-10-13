import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

root = Path("/root/autodl-tmp/real-benchmark-skills-v1")
(root / "logs").mkdir(parents=True, exist_ok=True)
with tarfile.open(root.parent / "real-benchmark-model-configs.tar.gz") as archive:
    for member in archive.getmembers():
        if member.isfile():
            archive.extractfile(member).read()
for source, target in (("real-benchmark-model-configs.tar.gz", "model-configs.tar.gz"),
                       ("real-benchmark-models.lock.json", "models.lock.json"),
                       ("prepare_real_benchmark_inference.py", "prepare_autodl_inference.py")):
    shutil.copy2(root.parent / source, root / target)
with (root / "logs/preparation.log").open("w") as log:
    process = subprocess.Popen([sys.executable, str(root / "prepare_autodl_inference.py")],
                               stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
(root / "preparation.pid").write_text(str(process.pid))
print(json.dumps({"pid": process.pid, "root": str(root)}))
