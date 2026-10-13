import importlib.util
import json
import subprocess
from pathlib import Path

root = Path("/root/autodl-tmp/infra-joint-planner-rtx6000/setup-20261013/venvs/inference")
package = Path(importlib.util.find_spec("transformers").origin).parent
files = list(package.rglob("*serv*"))
relevant = {}
for p in [package / "cli/serve.py"] + list((package / "cli/serving").rglob("*.py")):
    relevant[str(p.relative_to(package))] = [line for line in p.read_text().splitlines() if any(k in line.lower() for k in ("tool", "parse_response", "qwen", "context_length"))][:40]
source = (package / "utils/import_utils.py").read_text()
position = source.index("def is_serve_available")
print(json.dumps({"source": relevant, "serve_dependencies": source[position:position+1100]}))
