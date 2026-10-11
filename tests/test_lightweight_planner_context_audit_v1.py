from scripts.audit_lightweight_planner_context_gate_v1 import schema_errors


def test_audit_rejects_missing_arguments_even_when_runtime_defaults_it():
    schema = {
        "type": "object",
        "properties": {"inputs": {"type": "array"}, "arguments": {"type": "object"}},
        "required": ["inputs", "arguments"],
        "additionalProperties": False,
    }
    arguments = {"inputs": ["synthetic-source"]}
    assert schema_errors(arguments, schema) == ["'arguments' is a required property"]
    assert arguments == {"inputs": ["synthetic-source"]}
    assert schema_errors({**arguments, "arguments": {}}, schema) == []
