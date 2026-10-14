"""Fixed, bounded task replay diagnostics against the unchanged Ollama service.

No private evaluator data is read. Prompts were reconstructed from legitimate
source artifacts before this runner; raw requests and responses stay remote.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from probe_answerability_protocol_v1 import GROUNDED_SYSTEM
from run_hypothesis_cell_v1 import MODEL_ID, SYSTEM

TASKS = (
    "multihop:a647807d9a1d0efd",
    "mmqa:0ed625390ca7f919b46fd99fe85d80b5",
)
CONDITIONS = (
    ("grounded-no-thinking", GROUNDED_SYSTEM, False, 128),
    ("original-thinking-512", SYSTEM, True, 512),
    ("grounded-thinking-512", GROUNDED_SYSTEM, True, 512),
)


def post_json(url: str, payload: dict[str, Any], timeout: int) -> tuple[dict[str, Any], float]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read()), (time.perf_counter() - started) * 1000


def loaded_model() -> dict[str, Any]:
    with urllib.request.urlopen("http://127.0.0.1:11436/api/ps", timeout=5) as response:
        rows = json.loads(response.read())["models"]
    row = next((item for item in rows if item["name"] == MODEL_ID), None)
    if row is None or row["context_length"] != 32768:
        raise RuntimeError("resident model identity or context changed")
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_root
    output.mkdir(parents=True, exist_ok=True)
    private = output / "private"
    private.mkdir(exist_ok=True)
    manifest_path = output / "diagnostic-manifest-public.json"
    outcomes_path = output / "diagnostic-outcomes-public.jsonl"
    if manifest_path.exists() or outcomes_path.exists():
        raise FileExistsError("diagnostic namespace already used")
    model = loaded_model()
    schedule = []
    for condition, system, think, num_predict in CONDITIONS:
        for task_id in TASKS:
            prompt_path = (
                args.audit_root / "private-prompts" / (task_id.replace(":", "-") + "-g0.json")
            )
            prompt = json.loads(prompt_path.read_text())
            if prompt["system"] != SYSTEM:
                raise RuntimeError("reconstructed frozen system prompt mismatch")
            schedule.append(
                {
                    "task_id": task_id,
                    "workflow": "G0-replay",
                    "condition": condition,
                    "system_sha256": hashlib.sha256(system.encode()).hexdigest(),
                    "user_sha256": hashlib.sha256(prompt["user"].encode()).hexdigest(),
                    "think": think,
                    "num_predict": num_predict,
                    "temperature": 0,
                    "top_p": 1,
                }
            )
    manifest = {
        "schema_version": "infra-answerability-task-diagnostics-v1",
        "model": MODEL_ID,
        "backend": "unchanged resident Ollama 0.34.0",
        "context_length": 32768,
        "loaded_model_digest": model["digest"],
        "schedule": schedule,
        "historical_baseline": "infra-hypothesis-feasibility-v1 original G0 cells; not rerun here",
        "followup_rule": (
            "After independent scoring: if neither original task succeeds in any of these "
            "six conditions, run two preregistered replacement-MultiHop G0 conditions "
            "(grounded/no-thinking/128, grounded/thinking/512), then stop diagnostics. "
            "No correctness-driven prompt edits or reruns."
        ),
        "selection_priority_if_answerable": (
            "grounded-no-thinking, then grounded-thinking-512, then "
            "original-thinking-512; freeze a separately labeled H1 condition"
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    for index, item in enumerate(schedule, start=1):
        loaded_model()
        task_id = item["task_id"]
        prompt = json.loads(
            (
                args.audit_root / "private-prompts" / (task_id.replace(":", "-") + "-g0.json")
            ).read_text()
        )
        system = next(row[1] for row in CONDITIONS if row[0] == item["condition"])
        (
            count_response,
            _,
        ) = post_json(
            "http://127.0.0.1:37797/tokenize",
            {"content": system + "\n" + prompt["user"]},
            30,
        )
        tokens = count_response.get("tokens")
        if not isinstance(tokens, list) or len(tokens) + item["num_predict"] + 256 > 32768:
            raise RuntimeError("context_preflight_failed")
        payload = {
            "model": MODEL_ID,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt["user"]},
            ],
            "think": item["think"],
            "stream": False,
            "options": {
                "num_predict": item["num_predict"],
                "temperature": 0,
                "top_p": 1,
            },
        }
        run_id = f"diag-{index:02d}"
        started = time.time()
        try:
            response, wall_ms = post_json("http://127.0.0.1:11436/api/chat", payload, 300)
            error = None
        except (OSError, ValueError, urllib.error.HTTPError) as exc:
            response, wall_ms = {}, (time.time() - started) * 1000
            error = {"type": type(exc).__name__, "message": str(exc)[:300]}
        (private / (run_id + ".json")).write_text(
            json.dumps(
                {"request": payload, "response": response, "error": error},
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
        message = response.get("message", {})
        answer = message.get("content", "").strip()
        public = {
            "run_id": run_id,
            **item,
            "request_sha256": hashlib.sha256(
                json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest(),
            "preflight_tokens": len(tokens),
            "model_returned": response.get("model"),
            "answer_sha256": hashlib.sha256(answer.encode()).hexdigest() if answer else None,
            "answer_characters": len(answer),
            "returned_unknown": answer.upper() == "UNKNOWN",
            "thinking_characters": len(message.get("thinking", "")),
            "done_reason": response.get("done_reason"),
            "prompt_tokens": response.get("prompt_eval_count"),
            "completion_tokens": response.get("eval_count"),
            "wall_ms": round(wall_ms, 3),
            "error": error,
            "raw_ref": "experiment-machine:task-diagnostics/private/" + run_id + ".json",
        }
        with outcomes_path.open("a") as handle:
            handle.write(json.dumps(public, sort_keys=True) + "\n")
        print(
            json.dumps({"run_id": run_id, "condition": item["condition"], "error": error}),
            flush=True,
        )


if __name__ == "__main__":
    main()
