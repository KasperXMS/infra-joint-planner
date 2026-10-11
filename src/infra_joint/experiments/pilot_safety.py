"""Administrative limits for the isolated competence pilot, outside Agent inputs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Any

import httpx
from jsonschema import Draft202012Validator


class PilotBudgetExceeded(RuntimeError):
    """A bounded cell outcome; never a reason to retry the cell."""


class PilotStopped(RuntimeError):
    """Administrative stop; do not dispatch another cell."""


@dataclass
class PilotRequestBudget:
    stop_file: Path
    deadline: float
    control_limit: int = 72
    physical_limit: int = 64
    helper_limit: int = 4096
    control_byte_limit: int = 128 * 1024 * 1024
    control_requests: int = 0
    physical_requests: int = 0
    helper_requests: int = 0
    control_bytes: int = 0

    def check(self) -> None:
        if self.stop_file.exists():
            raise PilotStopped("owned pilot STOP file is present")
        if monotonic() >= self.deadline:
            raise PilotBudgetExceeded("cell administrative deadline exceeded")

    async def control_hook(self, request: httpx.Request) -> None:
        await request.aread()
        self.check()
        size = len(request.content)
        # No await between checking and charging: atomic within the shared event loop.
        if self.control_requests >= self.control_limit:
            raise PilotBudgetExceeded("control HTTP request quota exhausted")
        if self.control_bytes + size > self.control_byte_limit:
            raise PilotBudgetExceeded("control serialized input byte budget exhausted")
        self.control_requests += 1
        self.control_bytes += size

    async def helper_hook(self, request: httpx.Request) -> None:
        del request
        self.check()
        if self.helper_requests >= self.helper_limit:
            raise PilotBudgetExceeded("context helper request quota exhausted")
        self.helper_requests += 1

    async def worker_hook(self, request: httpx.Request) -> None:
        if request.method != "POST" or request.url.path != "/execute/operator":
            return
        await request.aread()
        self.check()
        wire = json.loads(request.content)
        if wire["action"]["operator"] == "invoke_model":
            if self.physical_requests >= self.physical_limit:
                raise PilotBudgetExceeded("physical inference request quota exhausted")
            self.physical_requests += 1

    def receipt(self) -> dict[str, Any]:
        return {
            "control_requests": self.control_requests,
            "physical_requests": self.physical_requests,
            "helper_requests": self.helper_requests,
            "control_bytes": self.control_bytes,
            "limits": {
                "control_requests": self.control_limit,
                "physical_requests": self.physical_limit,
                "helper_requests": self.helper_limit,
                "control_bytes": self.control_byte_limit,
            },
        }


def strict_verifier_sdk(sdk: Any, sink: Any) -> Any:
    """Keep the Verifier source/settings unchanged; reject invalid raw verdict calls."""
    from types import SimpleNamespace

    original = sdk.__dict__["FunctionTool"]

    def construct(**kwargs: Any) -> object:
        if kwargs["name"] == "submit_verification":
            callback = kwargs["on_invoke_tool"]
            schema = kwargs["params_json_schema"]

            async def checked(context: object, raw: str) -> str:
                try:
                    value = json.loads(raw)
                    errors = [
                        e.message
                        for e in Draft202012Validator(schema).iter_errors(value)  # pyright: ignore[reportUnknownMemberType]
                    ]
                except (ValueError, TypeError) as exc:
                    errors = [f"invalid JSON: {type(exc).__name__}"]
                sink({"tool": "submit_verification", "valid": not errors, "errors": errors})
                if errors:
                    return json.dumps(
                        {
                            "succeeded": False,
                            "failure_code": "schema_validation_failed",
                            "failure_message": "; ".join(errors),
                        }
                    )
                return await callback(context, raw)

            kwargs["on_invoke_tool"] = checked
        return original(**kwargs)

    return SimpleNamespace(**{**sdk.__dict__, "FunctionTool": construct})
