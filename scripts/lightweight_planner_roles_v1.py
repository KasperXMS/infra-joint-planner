"""Manager-only model substitution for the unchanged SDK-native runtime.

This constructor facade neither executes an experiment nor changes prompts,
tools, settings, observations, scheduling, or SDK Runner behavior. Construct the
fixed Verifier separately with the original strong model. Meter each provider
with its own RawSDKAPIMeter; local monetary costs remain unknown.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any


def role_isolated_sdk(
    sdk: object,
    *,
    manager_model: object,
    specialist_model: object,
    manager_model_id: str,
    specialist_model_id: str,
    manager_meter: Any = None,
    specialist_meter: Any = None,
    root_agent_name: str = "manager",
) -> object:
    original = sdk.__dict__["Agent"]

    def construct(*args: Any, **kwargs: Any) -> object:
        name = kwargs.get("name")
        if name == root_agent_name:
            model, model_id, meter, recipient = (
                manager_model,
                manager_model_id,
                manager_meter,
                "manager",
            )
        elif name == "bounded_specialist":
            model, model_id, meter, recipient = (
                specialist_model,
                specialist_model_id,
                specialist_meter,
                "specialist",
            )
        else:
            raise ValueError(f"unrecognized native Agent role: {name!r}")
        kwargs["model"] = (
            model
            if meter is None
            else meter.model(model, recipient=recipient, agent_name=name, requested_model=model_id)
        )
        return original(*args, **kwargs)

    return SimpleNamespace(**{**sdk.__dict__, "Agent": construct})


def manager_instructions(base: str, *, skills: str | None = None) -> str:
    """B0/B1 preserve exact base bytes; B2 appends the entire frozen skill text."""
    if skills is None:
        return base
    if not skills.strip():
        raise ValueError("B2 requires nonempty frozen skills")
    return base + "\n\n" + skills


def gate_decision(
    receipt: dict[str, Any], *, context_receipt: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Assess the original strict smoke without weakening its historical predicate.

    This is deliberately insufficient to authorize dispatch: context, role,
    infrastructure and budget evidence need independent closure before Gate 2.
    """
    gaps: list[str] = []
    if receipt.get("error") is not None:
        gaps.append("synthetic_harness_or_provider_error")
    if receipt.get("passed_native_smoke") is not True:
        gaps.append("frozen_recovery_smoke_not_passed")
    if context_receipt is None:
        gaps.append("context_transport_not_audited")
    elif context_receipt.get("status") == 200 and context_receipt.get("server_truncation_lines"):
        gaps.append("silent_context_truncation")
    else:
        gaps.append("context_preflight_regression_not_closed")
    return {
        "native_terminal_observed": receipt.get("error") is None
        and receipt.get("final_answer") == "A",
        "strict_smoke_accepted": receipt.get("passed_native_smoke") is True
        and receipt.get("error") is None,
        "gaps": gaps,
        "full_context_stress_required": False,
        "model_must_choose_parallel_tools": False,
        "formal_execution_allowed": False,
        "interpretation": "readiness decision, not a benchmark competence score",
    }
