"""Fail-closed, text-only Ollama Manager preflight at the final HTTP wire boundary.

The server renders the complete conversation with truncation disabled. Its own
resident llama-server tokenizes that rendered prompt. Accepted inference request
bytes are untouched. This adapter never summarizes, repairs, selects actions, or
wraps Specialist/Verifier models. It requires a pinned, already resident runner.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

import httpx


class ManagerContextError(RuntimeError):
    code = "context_preflight_unavailable"


class ManagerContextLimitExceeded(ManagerContextError):
    code = "context_limit_exceeded"


class ManagerContextIntegrityError(ManagerContextError):
    code = "context_integrity_failed"


def truncation_events(log: str) -> list[str]:
    """Distinguish real truncation from normal llama-server 'truncated = 0'."""
    return [
        line
        for line in log.splitlines()
        if any(
            marker in line.lower()
            for marker in (
                "truncating input prompt",
                "truncating input messages",
                "truncating native chat",
                "context shift,",
            )
        )
        or re.search(r"\btruncated\s*=\s*[1-9]\d*\b", line, re.IGNORECASE)
    ]


@dataclass(frozen=True)
class ManagerContextConfig:
    model: str
    digest: str
    model_blob: str
    template_sha256: str
    ollama_url: str
    runner_url: str
    context_window: int = 32768
    reserved_output_tokens: int = 2048


def native_text_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Port the text subset of Ollama FromChatRequest; reject other modalities.

    A list of text blocks becomes multiple messages, as in the provider adapter.
    Tool names are resolved from call IDs; JSON arguments become native objects.
    This conversion is only for render/count, never for the inference request.
    """
    names = {
        call["id"]: call["function"]["name"]
        for message in messages
        for call in message.get("tool_calls", [])
    }
    result: list[dict[str, Any]] = []
    for message in messages:
        if set(message) - {"role", "content", "tool_calls", "tool_call_id", "name", "reasoning"}:
            raise ManagerContextError("unsupported Manager message fields")
        role = message["role"]
        if role not in {"system", "developer", "user", "assistant", "tool"}:
            raise ManagerContextError("unsupported Manager message role")
        calls: list[dict[str, Any]] = []
        for call in message.get("tool_calls", []):
            if call.get("type") != "function":
                raise ManagerContextError("unsupported Manager tool-call type")
            args = json.loads(call["function"]["arguments"])
            if not isinstance(args, dict):
                raise ManagerContextError("tool-call arguments must be a JSON object")
            calls.append(
                {
                    "id": call["id"],
                    "function": {
                        "name": call["function"]["name"],
                        "arguments": args,
                    },
                }
            )
        tool_id = message.get("tool_call_id", "")
        name = message.get("name", "") or names.get(tool_id, "") if role == "tool" else ""
        metadata = {"thinking": message.get("reasoning", ""), "tool_call_id": tool_id}
        content = message.get("content")
        if isinstance(content, str):
            result.append(
                {
                    "role": role,
                    "content": content,
                    "tool_calls": calls,
                    "tool_name": name,
                    **metadata,
                }
            )
        elif isinstance(content, list):
            if not content:
                raise ManagerContextError("empty Manager content block list")
            for block in cast(list[Any], content):
                if set(block) != {"type", "text"} or block["type"] != "text":
                    raise ManagerContextError("Manager preflight only supports text content")
                if not isinstance(block["text"], str):
                    raise ManagerContextError("invalid Manager text content")
                result.append({"role": role, "content": block["text"]})
            if calls:
                result[-1].update(tool_calls=calls, tool_name=name, **metadata)
        elif content is None and calls:
            result.append({"role": role, "tool_calls": calls, **metadata})
        else:
            raise ManagerContextError("unsupported Manager content")
    return result


class OllamaManagerContextPreflight:
    def __init__(
        self,
        config: ManagerContextConfig,
        helper: httpx.AsyncClient,
        *,
        sink: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        if not 0 < config.reserved_output_tokens < config.context_window:
            raise ValueError("invalid Manager context/output budget")
        self.config, self.helper, self.sink = config, helper, sink
        self.receipts: list[dict[str, Any]] = []
        self.helper_requests = 0

    async def _json(self, method: str, url: str, body: Any = None) -> dict[str, Any]:
        self.helper_requests += 1
        response = await self.helper.request(method, url, json=body, timeout=20)
        response.raise_for_status()
        value = response.json()
        if not isinstance(value, dict):
            raise ManagerContextError("invalid context helper response")
        return cast(dict[str, Any], value)

    async def attest(self) -> None:
        c = self.config
        ps = await self._json("GET", c.ollama_url + "/api/ps")
        models = [
            m for m in ps.get("models", []) if m.get("name") in {c.model, c.model + ":latest"}
        ]
        if (
            len(models) != 1
            or models[0].get("digest") != c.digest
            or models[0].get("context_length") != c.context_window
        ):
            raise ManagerContextError("Manager residency/digest/context attestation failed")
        props = await self._json("GET", c.runner_url + "/props")
        if props.get("default_generation_settings", {}).get("n_ctx") != c.context_window:
            raise ManagerContextError("Manager runner context changed")
        if props.get("model_path", "").rsplit("/", 1)[-1] != c.model_blob:
            raise ManagerContextError("Manager tokenizer weights changed")
        show = await self._json("POST", c.ollama_url + "/api/show", {"model": c.model})
        if hashlib.sha256(show.get("template", "").encode()).hexdigest() != c.template_sha256:
            raise ManagerContextError("Manager template changed")
        # Pin the custom renderer/parser as well as the TEMPLATE blob.
        modelfile = show.get("modelfile", "")
        if "RENDERER qwen3-vl-instruct\n" not in modelfile or (
            "PARSER qwen3-vl-instruct\n" not in modelfile
        ):
            raise ManagerContextError("unsupported Manager renderer/parser")

    async def inspect(self, wire: dict[str, Any]) -> dict[str, Any]:
        c = self.config
        if wire.get("model") != c.model or wire.get("stream", False):
            raise ManagerContextError("unexpected Manager model or streaming request")
        if set(wire) - {
            "model",
            "messages",
            "tools",
            "max_tokens",
            "temperature",
            "top_p",
            "parallel_tool_calls",
            "stream",
            "store",
            "tool_choice",
            "frequency_penalty",
            "presence_penalty",
            "stop",
        }:
            raise ManagerContextError("unsupported Manager wire fields")
        cap = wire.get("max_tokens")
        if type(cap) is not int or not 0 < cap <= c.reserved_output_tokens:
            raise ManagerContextError("Manager requires an explicit bounded max_tokens")
        messages = native_text_messages(wire["messages"])
        await self.attest()
        render = await self._json(
            "POST",
            c.ollama_url + "/api/chat",
            {
                "model": c.model,
                "messages": messages,
                "tools": wire.get("tools", []),
                "stream": False,
                "truncate": False,
                "_debug_render_only": True,
                "options": {"num_ctx": c.context_window, "num_predict": c.reserved_output_tokens},
            },
        )
        info = render.get("_debug_info", {})
        prompt = info.get("rendered_template")
        if (
            not isinstance(prompt, str)
            or render.get("done") is not False
            or render.get("eval_count", 0) != 0
            or info.get("image_count", 0) != 0
        ):
            raise ManagerContextError("non-generating full-text rendering not confirmed")
        tokens = await self._json(
            "POST",
            c.runner_url + "/tokenize",
            {
                "content": prompt,
                "add_special": True,
            },
        )
        ids = tokens.get("tokens")
        if not isinstance(ids, list) or not ids:
            raise ManagerContextError("resident tokenizer returned invalid token IDs")
        ids = cast(list[object], ids)
        if any(type(i) is not int for i in ids):
            raise ManagerContextError("resident tokenizer returned invalid token IDs")
        count = len(ids)
        receipt = {
            "prompt_tokens": count,
            "context_window": c.context_window,
            "reserved_output_tokens": c.reserved_output_tokens,
            "effective_input_budget": c.context_window - c.reserved_output_tokens,
            "rendered_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "decision": "allow"
            if count + c.reserved_output_tokens <= c.context_window
            else "context_limit_exceeded",
            "count_source": "truncate=false native renderer + resident /tokenize",
        }
        if self.sink:
            self.sink("rendered", {"prompt": prompt, "receipt": receipt})
        return receipt

    async def request_hook(self, request: httpx.Request) -> None:
        receipt: dict[str, Any] = {
            "request_sha256": hashlib.sha256(await request.aread()).hexdigest(),
            "inference_forwarded": False,
        }
        self.receipts.append(receipt)
        try:
            receipt.update(await self.inspect(json.loads(request.content)))
            if receipt["decision"] != "allow":
                raise ManagerContextLimitExceeded(
                    f"context_limit_exceeded: prompt={receipt['prompt_tokens']} + "
                    f"reserved_output={self.config.reserved_output_tokens} > "
                    f"context={self.config.context_window}"
                )
            request.extensions["manager_context_receipt"] = receipt
            receipt["inference_forwarded"] = True
        except Exception as exc:
            receipt["error_type"] = type(exc).__name__
            receipt["error_code"] = getattr(exc, "code", ManagerContextError.code)
            if isinstance(exc, ManagerContextError):
                raise
            raise ManagerContextError("Manager context preflight could not be verified") from exc

    async def response_hook(self, response: httpx.Response) -> None:
        await response.aread()
        receipt = response.request.extensions["manager_context_receipt"]
        receipt["http_status"] = response.status_code
        if response.status_code != 200:
            return
        count = response.json().get("usage", {}).get("prompt_tokens")
        receipt["provider_prompt_tokens"] = count
        if type(count) is not int or count != receipt["prompt_tokens"]:
            receipt["error_code"] = ManagerContextIntegrityError.code
            raise ManagerContextIntegrityError(
                "provider prompt usage differs from complete preflight"
            )
        await self.attest()
        receipt["integrity_verified"] = True
