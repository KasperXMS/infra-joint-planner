"""Copy the existing AutoDL 5-second GPU sample log; no new sampler is launched."""
import subprocess
import sys
from pathlib import Path

study=Path(__file__).resolve().parents[1]
staging=study.parents[3]/'.code-staging'
target=study/'evidence/gpu-samples.jsonl'
with target.open('wb') as output:
    subprocess.run([sys.executable,str(staging/'run-new-autodl.py'),
                    str(staging/'read-model-aware-gpu-samples.py')],
                   stdout=output,check=True)
print(target)
