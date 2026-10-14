"""Count exact original Skill-body tokens with the served model tokenizer."""
import base64
import json
import subprocess
import sys
import tempfile
from pathlib import Path

study = Path(__file__).resolve().parents[1]
workspace = study.parents[3]
source = workspace / '.code-staging/benchmarks/skilllearn/skills/human_authored'
payload = {}
for family in ('offer-letter-generator', 'court-form-filling'):
    files = sorted((source / family).glob('*/SKILL.md'))
    assert files, family
    payload[family] = '\n\n'.join(p.read_text(encoding='utf-8') for p in files)
encoded = base64.b64encode(json.dumps(payload).encode()).decode()
inner = ("import base64,json; from transformers import AutoTokenizer; "
         "t=AutoTokenizer.from_pretrained('/root/autodl-tmp/models/Qwen3.5-9B'); "
         f"x=json.loads(base64.b64decode('{encoded}')); "
         "print(json.dumps({k:len(t.encode(v,add_special_tokens=False)) for k,v in x.items()}))")
remote = ("import subprocess; r=subprocess.run("
          "['/root/autodl-tmp/envs/inference/bin/python','-c',"
          + repr(inner) + "],capture_output=True,text=True); "
          "print(r.stdout,end=''); print(r.stderr,end='',file=__import__('sys').stderr); "
          "raise SystemExit(r.returncode)\n")
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'remote_token_count.py'
    path.write_text(remote, encoding='utf-8')
    run = subprocess.run([sys.executable, str(workspace / '.code-staging/run-new-autodl.py'),
                          str(path)], text=True, capture_output=True, check=True)
    counts = json.loads(run.stdout)
result = {'model': 'Qwen3.5-9B tokenizer', 'add_special_tokens': False,
          'original_body_tokens': counts}
(study / 'evidence/gap-skill-token-counts.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
