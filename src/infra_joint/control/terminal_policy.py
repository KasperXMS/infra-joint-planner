"""Versioned terminal-policy boundary; Specialist adoption is design-only in v2."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from infra_joint.core.base import ContractModel


class TerminalPolicyConfig(ContractModel):
    schema_version: Literal["terminal-policy-v2"] = "terminal-policy-v2"
    mode: Literal["manager_owned", "explicit_specialist_adoption"] = "manager_owned"


class ExplicitSpecialistAdoption(ContractModel):
    schema_version: Literal["specialist-adoption-v1"] = "specialist-adoption-v1"
    manager_adoption_action_id: str = Field(min_length=1)
    specialist_call_id: str = Field(min_length=1)
    specialist_candidate_action_id: str = Field(min_length=1)
    candidate_output_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
