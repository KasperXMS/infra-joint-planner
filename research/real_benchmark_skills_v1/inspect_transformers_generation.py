import importlib.util
import json
from pathlib import Path

package = Path(importlib.util.find_spec("transformers").origin).parent
result = {}
for relative in ("cli/serving/chat_completion.py", "cli/serving/utils.py"):
    lines = (package / relative).read_text().splitlines()
    selected = set()
    for index, line in enumerate(lines):
        if any(key in line for key in ("model.generate", "except ", "max_new_tokens", "do_sample", "prepare_inputs")):
            selected.update(range(max(0, index - 3), min(len(lines), index + 7)))
    result[relative] = "\n".join(f"{i+1}: {lines[i]}" for i in sorted(selected))
print(json.dumps(result))
