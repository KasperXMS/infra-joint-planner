"""Apply the recommended parser's XML parameter typing, without guided decoding.

Preserves function names, missing/extra arguments, invalid numeric strings, and
model decisions. The exact official decoder includes boolean fallback and
literal_eval behavior; raw and decoded responses must both be retained.
"""
import json

from qwen3_coder_parameter_decoder import Qwen3CoderParameterDecoder

decoder = Qwen3CoderParameterDecoder()


def decode_arguments(response, tools):
    definitions = {t["function"]["name"]: t["function"].get("parameters", {}).get("properties", {})
                   for t in tools or [] if t.get("type") == "function"}
    conversions = []
    for choice in response.get("choices", []):
        for call in choice.get("message", {}).get("tool_calls", []):
            function = call.get("function", {})
            arguments = function.get("arguments")
            if not isinstance(arguments, str):
                continue
            try:
                parsed = json.loads(arguments)
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(parsed, dict):
                continue
            schema = definitions.get(function.get("name"), {})
            for key, value in parsed.items():
                if not isinstance(value, str):
                    continue
                converted = decoder._convert_param_value(value, key, schema, function.get("name", ""))
                if type(converted) is not type(value) or converted != value:
                    conversions.append({"tool": function.get("name"), "argument": key,
                                        "source_type": type(value).__name__, "decoded_type": type(converted).__name__,
                                        "official_boolean_fallback": schema.get(key, {}).get("type") in ("boolean", "bool", "binary") and value.lower() not in ("true", "false"),
                                        "official_null_conversion": value.lower() == "null"})
                parsed[key] = converted
            function["arguments"] = json.dumps(parsed, ensure_ascii=False)
    return response, conversions
