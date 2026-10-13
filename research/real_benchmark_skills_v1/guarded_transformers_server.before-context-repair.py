"""Official Transformers serve with explicit context/output and greedy guards.

Valid requests use the unmodified official generation and Qwen3.5 response
parser. Guards reject invalid budgets rather than truncating or repairing them.
"""
import argparse
import hashlib
import json
import time
import threading
import uuid
from pathlib import Path

from starlette.responses import JSONResponse
from transformers.cli.serve import Serve

ROOT = Path("/root/autodl-tmp/real-benchmark-skills-v1")


class ContextLimitError(ValueError):
    pass


class FrozenServe(Serve):
    def start_server(self):
        self._study_pending = 0
        self._study_running = 0
        self._study_lock = threading.Lock()
        private = ROOT / "private"
        private.mkdir(exist_ok=True, mode=0o700)
        for timed in self._model_manager.loaded_models.values():
            model = timed.model
            original_generate = model.generate
            tokenizer = getattr(timed.processor, "tokenizer", timed.processor)
            chat_eos = tokenizer.eos_token_id
            def guarded_generate(*args, _original=original_generate, _model=model, _chat_eos=chat_eos, **kwargs):
                input_ids = kwargs.get("input_ids")
                if input_ids is None:
                    input_ids = kwargs.get("inputs")
                if input_ids is None and args:
                    input_ids = args[0]
                if input_ids is None:
                    raise RuntimeError("Cannot verify context length")
                length = input_ids.shape[-1]
                config = kwargs["generation_config"]
                original_eos = config.eos_token_id
                stops = original_eos if isinstance(original_eos, list) else [original_eos]
                config.eos_token_id = sorted({v for v in stops + [_chat_eos] if v is not None})
                output_limit = int(config.max_new_tokens)
                if output_limit > 4096 or output_limit < 1 or length + output_limit > 32768:
                    raise ContextLimitError(
                        f"Maximum context length is 32768 tokens and output cap is 4096 tokens; "
                        f"requested {length} input tokens plus {output_limit} output tokens.")
                if config.do_sample or config.temperature != 0:
                    raise RuntimeError("Frozen greedy decoding settings were not delivered")
                record = {"id": uuid.uuid4().hex, "started_epoch": time.time(), "prompt_tokens": length,
                          "max_new_tokens": output_limit, "temperature": config.temperature,
                          "do_sample": config.do_sample, "dtype": str(_model.dtype),
                          "eos_token_id": config.eos_token_id, "chat_eos_token_id": _chat_eos,
                          "input_ids_sha256": hashlib.sha256(input_ids.cpu().numpy().tobytes()).hexdigest()}
                with self._study_lock:
                    self._study_running += 1
                try:
                    output = _original(*args, **kwargs)
                    generated = output[0, length:]
                    record["generated_tokens"] = len(generated)
                    record["chat_eos_positions"] = (generated == _chat_eos).nonzero().flatten().tolist()
                    return output
                finally:
                    with self._study_lock:
                        self._study_running -= 1
                    record["generation_seconds"] = time.time() - record["started_epoch"]
                    with (private / "generation-metadata.jsonl").open("a") as log:
                        log.write(json.dumps(record) + "\n")
            model.generate = guarded_generate

        async def context_error(_request, exc):
            return JSONResponse(status_code=400, content={"error": {"message": str(exc),
                "type": "invalid_request_error", "code": "context_length_exceeded"}})
        self.server.config.app.add_exception_handler(ContextLimitError, context_error)
        @self.server.config.app.middleware("http")
        async def count_requests(request, call_next):
            counted = request.url.path == "/v1/chat/completions"
            if counted:
                with self._study_lock:
                    self._study_pending += 1
            try:
                return await call_next(request)
            finally:
                if counted:
                    with self._study_lock:
                        self._study_pending -= 1
        @self.server.config.app.get("/study/status")
        async def study_status():
            with self._study_lock:
                return {"pending_requests": self._study_pending, "running_generations": self._study_running,
                        "queued_requests": max(0, self._study_pending-self._study_running),
                        "context_limit": 32768, "output_cap": 4096}
        super().start_server()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["Qwen3.5-4B", "Qwen3.5-9B"], required=True)
    args = parser.parse_args()
    server = FrozenServe(force_model=str(ROOT / "models" / args.model), device="cuda:0", dtype="bfloat16",
                         attn_implementation="sdpa", reasoning="off", host="127.0.0.1", port=18000,
                         default_seed=42, continuous_batching=False, compile=False, non_blocking=True)
    server._thread.join()
