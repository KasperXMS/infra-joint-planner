"""Three fixed non-benchmark probes of the unchanged resident Ollama model."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path

from run_hypothesis_cell_v1 import MODEL_ID, SYSTEM

GROUNDED_SYSTEM = (
    "Answer the original question using only the supplied source evidence. "
    "Identify the relevant facts and give the best-supported short answer. "
    "Return UNKNOWN only when the supplied evidence genuinely lacks the facts needed to answer. "
    "Do not include an explanation."
)
SYNTHETIC_USER = (
    "Original question: Did Cedarville's bus fleet increase from 2020 to 2021?\n"
    'Evidence: [{"document_id":"A","text":"Cedarville operated 12 buses in 2020."},'
    '{"document_id":"B","text":"Cedarville operated 14 buses in 2021."}]\nShort answer:'
)
CONDITIONS = (
    ("original-no-thinking", SYSTEM, False),
    ("grounded-no-thinking", GROUNDED_SYSTEM, False),
    ("original-thinking", SYSTEM, True),
)


def post_json(url: str, payload: dict[str, object]) -> tuple[dict[str, object], float]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read()), (time.perf_counter() - started) * 1000


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.output_root
    root.mkdir(parents=True, exist_ok=True)
    public = root / "protocol-probes-public.json"
    if public.exists():
        raise FileExistsError(public)
    with urllib.request.urlopen("http://127.0.0.1:11436/api/ps", timeout=5) as response:
        loaded = json.loads(response.read())["models"]
    if not any(row["name"] == MODEL_ID and row["context_length"] == 32768 for row in loaded):
        raise RuntimeError("resident model identity/context changed")
    summary = []
    for name, system, think in CONDITIONS:
        payload: dict[str, object] = {
            "model": MODEL_ID,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": SYNTHETIC_USER},
            ],
            "think": think,
            "stream": False,
            "options": {"num_predict": 128, "temperature": 0, "top_p": 1},
        }
        response, wall_ms = post_json("http://127.0.0.1:11436/api/chat", payload)
        private = root / (name + "-private.json")
        private.write_text(json.dumps({"request": payload, "response": response}, indent=2) + "\n")
        message = response["message"]
        summary.append(
            {
                "name": name,
                "system_sha256": hashlib.sha256(system.encode()).hexdigest(),
                "request_sha256": hashlib.sha256(
                    json.dumps(payload, sort_keys=True).encode()
                ).hexdigest(),
                "model": response.get("model"),
                "answer": message.get("content"),
                "thinking_characters": len(message.get("thinking", "")),
                "done_reason": response.get("done_reason"),
                "prompt_tokens": response.get("prompt_eval_count"),
                "completion_tokens": response.get("eval_count"),
                "wall_ms": round(wall_ms, 3),
            }
        )
    public.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"probes": len(summary), "public": str(public)}))


if __name__ == "__main__":
    main()
