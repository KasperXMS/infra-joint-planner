"""Pinned native parser/context for additional Managers; inference bytes untouched."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from infra_joint.experiments.manager_context import (
    ManagerContextConfig,
    ManagerContextError,
    OllamaManagerContextPreflight,
)


@dataclass(frozen=True)
class MultiscaleContextConfig(ManagerContextConfig):
    renderer: str = ""
    parser: str = ""
    disable_thinking: bool = False


class MultiscaleContextPreflight(OllamaManagerContextPreflight):
    async def attest(self):
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
        # Explicit provider-specific parser identity; no output repair or prompt edits.
        for field, value in [("RENDERER", c.renderer), ("PARSER", c.parser)]:
            actual = re.search(r"^" + field + r" (.+)$", show.get("modelfile", ""), re.M)
            if (actual[1] if actual else "") != value:
                raise ManagerContextError("Manager renderer/parser changed")

    async def _json(self, method, url, body=None):
        if body is not None and url.endswith("/api/chat") and self.config.disable_thinking:
            body = {**body, "think": False}
        return await super()._json(method, url, body)

    async def inspect(self, wire):
        # Ollama v0.34 maps OpenAI reasoning_effort:none to native think:false.
        # Copy only for native render/count; original inference bytes never change.
        copied = dict(wire)
        if self.config.disable_thinking:
            if copied.pop("reasoning_effort", None) != "none":
                raise ManagerContextError("expected frozen reasoning_effort:none")
        elif "reasoning_effort" in copied:
            raise ManagerContextError("unexpected reasoning mode")
        return await super().inspect(copied)
