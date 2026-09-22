import asyncio
import json
import shlex
from collections.abc import Sequence
from time import perf_counter
from typing import Any, cast

from pydantic import Field

from infra_joint.core.base import ContractModel
from infra_joint.heterogeneous.calibration import summarize
from infra_joint.heterogeneous.contracts import ComputeProfilePoint


class ModelProfileSample(ContractModel):
    wall_service_ms: float = Field(ge=0)
    ttft_ms: float = Field(ge=0)
    prompt_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    prompt_eval_ms: float = Field(ge=0)
    decode_ms: float = Field(ge=0)
    output_tokens_per_second: float = Field(ge=0)
    load_ms: float = Field(ge=0)
    total_runtime_ms: float = Field(ge=0)
    done_reason: str = Field(min_length=1)


class SshOllamaProfiler:
    def __init__(self, ssh_target: str, *, base_url: str = "http://127.0.0.1:11435") -> None:
        self._ssh_target = ssh_target
        self._base_url = base_url.rstrip("/")

    async def invoke(
        self,
        model: str,
        prompt: str,
        *,
        output_tokens: int,
        context_window: int,
    ) -> ModelProfileSample:
        request = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "think": False,
            "keep_alive": "30m",
            "options": {
                "num_ctx": context_window,
                "num_predict": output_tokens,
                "temperature": 0,
                "seed": 42,
                "top_k": 1,
                "top_p": 1.0,
            },
        }
        remote = shlex.join(
            (
                "curl",
                "-fsS",
                "-N",
                "-H",
                "content-type: application/json",
                "--data-binary",
                "@-",
                f"{self._base_url}/api/generate",
            )
        )
        process = await asyncio.create_subprocess_exec(
            "ssh",
            "-o",
            "BatchMode=yes",
            self._ssh_target,
            remote,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        if process.stdin is None or process.stdout is None:
            process.kill()
            raise RuntimeError("profiling subprocess lacks required pipes")
        started = perf_counter()
        process.stdin.write(json.dumps(request).encode("utf-8"))
        await process.stdin.drain()
        process.stdin.close()
        first_token_at: float | None = None
        final: dict[str, Any] | None = None
        while line := await process.stdout.readline():
            raw_payload: Any = json.loads(line)
            if not isinstance(raw_payload, dict):
                raise RuntimeError("Ollama streaming chunk is not an object")
            payload = cast(dict[str, Any], raw_payload)
            if first_token_at is None and (payload.get("response") or payload.get("thinking")):
                first_token_at = perf_counter()
            if payload.get("done") is True:
                final = payload
        stderr = b""
        if process.stderr is not None:
            stderr = await process.stderr.read()
        return_code = await process.wait()
        finished = perf_counter()
        if return_code != 0:
            raise RuntimeError(
                f"Ollama profiling request failed ({return_code}): "
                f"{stderr.decode('utf-8', errors='replace').strip()}"
            )
        if final is None or first_token_at is None:
            raise RuntimeError("Ollama profiling response lacks token/final telemetry")
        return _sample_from_final(
            final, (finished - started) * 1000, (first_token_at - started) * 1000
        )

    async def profile_point(
        self,
        model: str,
        prompt: str,
        *,
        requested_input_tokens: int,
        requested_output_tokens: int,
        context_window: int,
        warmup_runs: int = 10,
        measured_runs: int = 30,
    ) -> tuple[ComputeProfilePoint, tuple[ModelProfileSample, ...]]:
        if warmup_runs < 10 or measured_runs < 30:
            raise ValueError("formal compute profiles require >=10 warmups and >=30 samples")
        for _ in range(warmup_runs):
            await self.invoke(
                model,
                prompt,
                output_tokens=requested_output_tokens,
                context_window=context_window,
            )
        samples = tuple(
            [
                await self.invoke(
                    model,
                    prompt,
                    output_tokens=requested_output_tokens,
                    context_window=context_window,
                )
                for _ in range(measured_runs)
            ]
        )
        return (
            profile_point_from_samples(
                requested_input_tokens,
                requested_output_tokens,
                warmup_runs,
                samples,
            ),
            samples,
        )


def profile_point_from_samples(
    requested_input_tokens: int,
    requested_output_tokens: int,
    warmup_runs: int,
    samples: Sequence[ModelProfileSample],
) -> ComputeProfilePoint:
    if len(samples) < 1:
        raise ValueError("profile point requires samples")
    return ComputeProfilePoint(
        input_tokens=requested_input_tokens,
        requested_output_tokens=requested_output_tokens,
        warmup_runs=warmup_runs,
        measured_runs=len(samples),
        ttft_ms=summarize(tuple(item.ttft_ms for item in samples)),
        prefill_ms=summarize(tuple(item.prompt_eval_ms for item in samples)),
        decode_ms=summarize(tuple(item.decode_ms for item in samples)),
        total_service_ms=summarize(tuple(item.wall_service_ms for item in samples)),
        output_tokens_per_second=summarize(
            tuple(item.output_tokens_per_second for item in samples)
        ),
        actual_input_tokens=summarize(tuple(float(item.prompt_tokens) for item in samples)),
        actual_output_tokens=summarize(tuple(float(item.output_tokens) for item in samples)),
    )


def _sample_from_final(
    final: dict[str, Any], wall_service_ms: float, ttft_ms: float
) -> ModelProfileSample:
    def number(name: str) -> float:
        value = final.get(name)
        if not isinstance(value, (int, float)) or value < 0:
            raise RuntimeError(f"Ollama final telemetry missing {name}")
        return float(value)

    prompt_tokens = int(number("prompt_eval_count"))
    output_tokens = int(number("eval_count"))
    prompt_eval_ms = number("prompt_eval_duration") / 1_000_000
    decode_ms = number("eval_duration") / 1_000_000
    output_rate = output_tokens / (decode_ms / 1000) if decode_ms > 0 else 0
    reason = final.get("done_reason")
    if not isinstance(reason, str) or not reason:
        raise RuntimeError("Ollama final telemetry missing done_reason")
    return ModelProfileSample(
        wall_service_ms=wall_service_ms,
        ttft_ms=ttft_ms,
        prompt_tokens=prompt_tokens,
        output_tokens=output_tokens,
        prompt_eval_ms=prompt_eval_ms,
        decode_ms=decode_ms,
        output_tokens_per_second=output_rate,
        load_ms=number("load_duration") / 1_000_000,
        total_runtime_ms=number("total_duration") / 1_000_000,
        done_reason=reason,
    )
