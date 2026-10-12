"""Task-independent rules; dynamic selection reads observable event categories only."""
import json

RULES = {
    "execute": "Before computing a node, collect valid handles for every declared parent in the declared order. Read their numeric values and apply the node policy to choose the operation. Reuse valid artifacts instead of recomputing them. Continue until the root exists.",
    "schema": "On JSON or schema error, correct the action object's structure. Include name and arguments; use only the declared fields and field types. Do not invent tools or put parameters outside arguments. The rejected action had no tool side effects.",
    "dependency": "On dependency or stale-artifact errors, compare the selected handles' node names and validity with the requested node's ordered parents. Fetch missing sources or rebuild missing derived parents before retrying the node.",
    "refresh": "On a source update, retire every listed invalidated handle. Fetch the changed source again. Rebuild affected derived nodes using current parent handles, retaining unaffected valid artifacts. A previously chosen operation may change when input values change: re-evaluate each rebuilt node's policy. Then verify the new root.",
    "retry": "On transient_unavailable with retryable true, retry the same verify request within the remaining turn budget; this error supplies no evidence that artifacts need rebuilding.",
    "terminal": "When verify returns a receipt, submit the exact artifact and receipt pair immediately. Do not fetch, compute, or verify again in the submit phase. Receipt issuance certifies freshness and provenance only, so it does not substitute for choosing operations correctly.",
}
STATIC = "Procedural support (generic, reusable):\n" + "\n".join(RULES.values())


def local_rule(events: list[dict]) -> tuple[str, str]:
    if not events:
        key = "execute"
    else:
        obs = events[-1]["observation"]
        error = obs.get("error")
        if error in ("json_parse_failed", "schema_validation_failed"):
            key = "schema"
        elif error in ("dependency_mismatch", "invalid_or_stale_artifact", "unknown_node", "unknown_source"):
            key = "dependency"
        elif error == "source_updated":
            key = "refresh"
        elif error == "transient_unavailable":
            key = "retry"
        elif obs.get("status") == "verified" or error in ("phase_violation", "terminal_contract_failed"):
            key = "terminal"
        else:
            key = "execute"
    return key, RULES[key]


def support(condition, env) -> tuple[str, dict]:
    metadata = {"condition": condition, "oracle_access": False}
    if condition == "none":
        return "", metadata
    if condition == "static":
        return STATIC, metadata
    if condition == "local":
        key, text = local_rule(env.events)
        return "Currently relevant procedural support:\n" + text, {**metadata, "selected_rule": key}
    if condition == "ledger":
        return STATIC + "\nOBSERVATION-ONLY STATE PROJECTION=" + json.dumps(env.state_projection(), sort_keys=True), metadata
    raise ValueError(condition)
