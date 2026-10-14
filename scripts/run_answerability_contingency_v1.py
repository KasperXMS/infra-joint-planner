"""Run the two preregistered replacement-task diagnostic calls, once."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from probe_answerability_protocol_v1 import GROUNDED_SYSTEM
from run_answerability_diagnostics_v1 import loaded_model, post_json
from run_hypothesis_cell_v1 import MODEL_ID, SYSTEM

TASK_ID = "multihop:667f4ac48afef820"
CONDITIONS = (("grounded-no-thinking", False, 128), ("grounded-thinking-512", True, 512))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-root", type=Path, required=True)
    parser.add_argument("--prior-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    prior = json.loads((args.prior_root / "diagnostic-scores-public.json").read_text())
    if len(prior) != 6 or any(
        row["evaluation"] and row["evaluation"]["task_success"] for row in prior
    ):
        raise RuntimeError("preregistered contingency condition not met")
    root = args.output_root
    root.mkdir(parents=True, exist_ok=True)
    private = root / "private"
    private.mkdir(exist_ok=True)
    manifest_path = root / "contingency-manifest-public.json"
    outcomes_path = root / "diagnostic-outcomes-public.jsonl"
    if manifest_path.exists() or outcomes_path.exists():
        raise FileExistsError("contingency namespace already used")
    prompt = json.loads(
        (args.audit_root / "private-prompts" / (TASK_ID.replace(":", "-") + "-g0.json")).read_text()
    )
    if prompt["system"] != SYSTEM:
        raise RuntimeError("original source-evidence prompt changed")
    manifest_path.write_text(
        json.dumps(
            {
                "task_id": TASK_ID,
                "workflow": "G0-replay",
                "model": MODEL_ID,
                "conditions": CONDITIONS,
                "system_sha256": hashlib.sha256(GROUNDED_SYSTEM.encode()).hexdigest(),
                "user_sha256": hashlib.sha256(prompt["user"].encode()).hexdigest(),
                "reason": "all six fixed original-task diagnostic calls lacked native success",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    for index, (condition, think, num_predict) in enumerate(CONDITIONS, start=7):
        loaded_model()
        count_response, _ = post_json(
            "http://127.0.0.1:37797/tokenize",
            {"content": GROUNDED_SYSTEM + "\n" + prompt["user"]},
            30,
        )
        tokens = count_response.get("tokens")
        if not isinstance(tokens, list) or len(tokens) + num_predict + 256 > 32768:
            raise RuntimeError("context_preflight_failed")
        payload = {
            "model": MODEL_ID,
            "messages": [
                {"role": "system", "content": GROUNDED_SYSTEM},
                {"role": "user", "content": prompt["user"]},
            ],
            "think": think,
            "stream": False,
            "options": {"num_predict": num_predict, "temperature": 0, "top_p": 1},
        }
        started = time.time()
        try:
            response, wall_ms = post_json("http://127.0.0.1:11436/api/chat", payload, 300)
            error = None
        except (OSError, ValueError) as exc:
            response, wall_ms = {}, (time.time() - started) * 1000
            error = {"type": type(exc).__name__, "message": str(exc)[:300]}
        run_id = f"diag-{index:02d}"
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
            "task_id": TASK_ID,
            "workflow": "G0-replay",
            "condition": condition,
            "system_sha256": hashlib.sha256(GROUNDED_SYSTEM.encode()).hexdigest(),
            "user_sha256": hashlib.sha256(prompt["user"].encode()).hexdigest(),
            "think": think,
            "num_predict": num_predict,
            "temperature": 0,
            "top_p": 1,
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
            "raw_ref": "experiment-machine:task-diagnostics-contingency/private/"
            + run_id
            + ".json",
        }
        with outcomes_path.open("a") as handle:
            handle.write(json.dumps(public, sort_keys=True) + "\n")
        print(json.dumps({"run_id": run_id, "condition": condition, "error": error}), flush=True)


if __name__ == "__main__":
    main()
