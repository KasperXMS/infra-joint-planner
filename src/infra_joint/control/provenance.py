"""Semantic request provenance, never provider-private reasoning or runtime state."""

import json
from hashlib import sha256
from typing import Any, cast

PROFILE_MESSAGE_PREFIX = "Current anonymous physical profile: "
_PRIVATE_PROVIDER_KEYS = frozenset({"reasoning", "reasoning_content", "encrypted_content"})


def semantic_input_items(items: list[object]) -> list[dict[str, Any]]:
    """Keep explicit SDK messages/tool records, omitting opaque reasoning items."""
    result: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            raw = cast(dict[str, Any], item)
        elif callable(getattr(item, "model_dump", None)):
            raw = cast(Any, item).model_dump(mode="json")
        else:
            continue
        if raw.get("type") == "reasoning":
            continue
        result.append(_without_private_reasoning(raw))
    return result


def _without_private_reasoning(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_private_reasoning(item)
            for key, item in cast(dict[str, Any], value).items()
            if key not in _PRIVATE_PROVIDER_KEYS
        }
    if isinstance(value, list):
        return [
            _without_private_reasoning(item)
            for item in cast(list[Any], value)
            if not isinstance(item, dict) or cast(dict[str, Any], item).get("type") != "reasoning"
        ]
    return value


def provenance_sha256(value: object) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def is_profile_message(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    value = cast(dict[str, Any], item)
    content = value.get("content")
    return value.get("role") == "user" and isinstance(content, str) and content.startswith(
        PROFILE_MESSAGE_PREFIX
    )


def blind_input_profile_findings(items: list[dict[str, Any]]) -> tuple[str, ...]:
    """Inspect actual SDK context, including accumulated logical tool results."""
    findings: list[str] = []
    for index, item in enumerate(items):
        if is_profile_message(item):
            findings.append(f"input item {index}: explicit dynamic profile message")
        if item.get("type") != "function_call_output":
            continue
        output = item.get("output")
        if not isinstance(output, str):
            continue
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            continue
        if (isinstance(parsed, dict)
                and cast(dict[str, Any], parsed).get("physical_profile") is not None):
            findings.append(f"input item {index}: tool-result dynamic physical profile")
    return tuple(findings)
