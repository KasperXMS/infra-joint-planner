"""Executed on the pinned AutoDL host through the local SSH wrapper."""
import hashlib
import json
import subprocess

text = ("Required first step: Before inspecting task data or planning a solution, use the shell tool to read each relevant SKILL.md listed under Available skills. Resolve listed aliases using their root paths, then read the complete file. Treat metadata only as a pointer; do not proceed until the tool returns the full instructions. Read referenced scripts when needed.")
script = '''import json,sys
from transformers import AutoTokenizer
t=AutoTokenizer.from_pretrained('/root/autodl-tmp/models/Qwen3.5-9B')
s=sys.stdin.read()
print(json.dumps({'tokens':len(t.encode(s,add_special_tokens=False))}))'''
p = subprocess.run(['/root/autodl-tmp/envs/inference/bin/python', '-c', script],
                   input=text, text=True, capture_output=True, timeout=90, check=True)
print(json.dumps({'sha256': hashlib.sha256(text.encode()).hexdigest(),
                  'tokens': json.loads(p.stdout)['tokens']}))
