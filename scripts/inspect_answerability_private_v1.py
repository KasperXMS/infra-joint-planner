"""Print only final answer text from machine-local diagnostic response files."""

import json
from pathlib import Path

root = Path("/home/super/xiaoming/infra-answerability-autonomous-v1")
for folder, run_id in (
    ("task-diagnostics", "diag-05"),
    ("task-diagnostics-contingency", "diag-08"),
):
    payload = json.loads((root / folder / "private" / (run_id + ".json")).read_text())
    print(json.dumps({"run_id": run_id, "answer": payload["response"]["message"].get("content")}))
