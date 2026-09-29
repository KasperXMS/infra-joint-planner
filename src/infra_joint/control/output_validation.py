from __future__ import annotations

import json
from collections.abc import Iterator
from typing import cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import Field

from infra_joint.core.base import ContractModel
from infra_joint.core.task import OutputContract, OutputFormat


class TerminalOutputValidation(ContractModel):
    valid: bool
    format: OutputFormat
    failure_code: str | None = Field(default=None, min_length=1)
    details: str = ""


def validate_terminal_output(
    answer: str,
    contract: OutputContract,
) -> TerminalOutputValidation:
    if contract.format == OutputFormat.CHOICE:
        valid = contract.choices is not None and answer in contract.choices
        return TerminalOutputValidation(
            valid=valid,
            format=contract.format,
            failure_code=None if valid else "invalid_choice_output",
            details="" if valid else "terminal answer is not a declared choice",
        )
    if contract.format == OutputFormat.SHORT_TEXT:
        valid = bool(answer.strip())
        return TerminalOutputValidation(
            valid=valid,
            format=contract.format,
            failure_code=None if valid else "invalid_short_text_output",
            details="" if valid else "terminal answer is empty",
        )
    try:
        parsed = json.loads(answer)
    except json.JSONDecodeError:
        return TerminalOutputValidation(
            valid=False,
            format=contract.format,
            failure_code="invalid_json_output",
            details="terminal answer is not valid JSON",
        )
    schema = contract.schema_definition
    if schema is None:
        return TerminalOutputValidation(
            valid=False,
            format=contract.format,
            failure_code="missing_output_schema",
            details="structured output contract has no schema",
        )
    errors = cast(
        Iterator[JsonSchemaValidationError],
        Draft202012Validator(schema).iter_errors(parsed),  # pyright: ignore[reportUnknownMemberType]
    )
    error = next(errors, None)
    return TerminalOutputValidation(
        valid=error is None,
        format=contract.format,
        failure_code=None if error is None else "output_schema_mismatch",
        details="" if error is None else f"terminal output schema mismatch: {error.message}",
    )
