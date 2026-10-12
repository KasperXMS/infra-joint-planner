"""Validate synthetic Skill examples offline against the actual native tool schemas.

This does not load task data, run agents, invoke models, or execute operators.
Tokenizer lengths are intentionally unknown until measured with the deployed
Manager tokenizer; UTF-8 bytes and words are not substituted for token counts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from agents import Agent
from jsonschema import Draft202012Validator

from infra_joint.control.native_agents import SpecialistRequest, _native_tool_schema
from infra_joint.operators.builtin import invoke_model_spec, read_artifact_spec
from infra_joint.operators.media import media_operator_specs
from infra_joint.operators.retrieval import bm25_retrieve_spec
from infra_joint.operators.structured import structured_operator_specs

EXAMPLES = re.compile(
    r"<!-- tool-example: ([a-z][a-z0-9_]*) -->\s*```json\s*(.*?)\s*```", re.DOTALL
)
DEFAULT_SKILLS = (
    "configs/skills/planner-procedure-v1.md",
    "configs/skills/planner-atomic-sop-v1.md",
)


def validate(paths: list[Path]) -> dict[str, object]:
    specs = (
        invoke_model_spec(),
        read_artifact_spec(),
        bm25_retrieve_spec(),
        *structured_operator_specs(),
        *media_operator_specs(),
    )
    schemas = {spec.operator_id: _native_tool_schema(spec) for spec in specs}
    # Construct the same SDK as_tool wrapper used by native_agents, without
    # invoking it. The SDK may strengthen required fields for its strict schema.
    specialist_tool = Agent(name="offline-skill-schema-validator").as_tool(
        tool_name="consult_specialist",
        tool_description="Offline schema construction only.",
        parameters=SpecialistRequest,
    )
    schemas["consult_specialist"] = specialist_tool.params_json_schema
    validators = {}
    for name, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
        validators[name] = Draft202012Validator(schema)

    results: list[dict[str, object]] = []
    for path in paths:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        seen: set[str] = set()
        negatives = 0
        for name, encoded in EXAMPLES.findall(text):
            if name in seen:
                raise ValueError(f"Duplicate example for {name} in {path.name}")
            if name not in validators:
                raise ValueError(f"Unknown tool example {name} in {path.name}")
            seen.add(name)
            payload = json.loads(encoded)
            validators[name].validate(payload)
            if name == "consult_specialist":
                SpecialistRequest.model_validate(payload)
                required_key = "objective"
            else:
                required_key = "arguments"
            missing = {key: value for key, value in payload.items() if key != required_key}
            if validators[name].is_valid(missing):
                raise ValueError(f"Missing {required_key} unexpectedly accepted for {name}")
            negatives += 1
            if name != "consult_specialist":
                missing_inputs = {key: value for key, value in payload.items() if key != "inputs"}
                if validators[name].is_valid(missing_inputs):
                    raise ValueError(f"Missing inputs unexpectedly accepted for {name}")
                negatives += 1
        if seen != set(schemas):
            raise ValueError(f"Missing tool examples in {path.name}: {sorted(set(schemas) - seen)}")
        results.append(
            {
                "file": path.as_posix(),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "utf8_bytes": len(raw),
                "schema_valid_examples": len(seen),
                "missing_required_field_rejections": negatives,
                "token_count": None,
                "token_count_status": "pending_deployed_model_tokenizer_measurement",
            }
        )
    contract_hash = hashlib.sha256(
        json.dumps(schemas, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "status": "passed",
        "tool_schema_count": len(schemas),
        "native_tool_schemas_sha256": contract_hash,
        "files": results,
        "new_inference_calls": 0,
        "task_data_read": False,
        "scope": "Synthetic example JSON Schema validation only; not a model capability Gate.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skills", nargs="*", type=Path)
    args = parser.parse_args()
    paths = args.skills or [Path(path) for path in DEFAULT_SKILLS]
    print(json.dumps(validate(paths), indent=2))


if __name__ == "__main__":
    main()
