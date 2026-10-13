import importlib.util
import json
from pathlib import Path

package = Path(importlib.util.find_spec("transformers").origin).parent
print(json.dumps({"serve_options": (package / "cli/serve.py").read_text()[:19000],
                  "model_manager": (package / "cli/serving/model_manager.py").read_text()[:14000]}))
