"""Append-only, zero-inference adjudication of the preserved Context Gate run."""

import argparse
import hashlib
import inspect
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

from infra_joint.experiments.manager_context import truncation_events


def schema_errors(arguments: object, schema: dict) -> list[str]:
    """Validate raw provider arguments; never fill defaults before auditing."""
    return [error.message for error in Draft202012Validator(schema).iter_errors(arguments)]


def audit(run: Path) -> dict:
    raw = json.loads((run / "receipt.json").read_text())
    protocol = json.loads((run / "protocol.json").read_text())
    delta = (run / "server-log-delta.txt").read_bytes()
    warnings = truncation_events(delta.decode(errors="replace"))
    capacity = raw["capacity"]
    allowed = [row for row in capacity if row["target"] <= 30720]
    rejected = [row for row in capacity if row["target"] > 30720]
    sdk = raw["native_smoke"]
    parallel = raw["sdk_parallel"]
    preflights = raw["preflight_receipts"]
    actual_tool_calls = []
    raw_schema_checks = []
    for index, row in enumerate(raw["provider_responses"], start=1):
        if row["phase"] != "sdk":
            continue
        request = json.loads((run / f"request-{index:02d}.json").read_bytes())
        response = json.loads((run / f"response-{index:02d}.json").read_bytes())
        schemas = {t["function"]["name"]: t["function"]["parameters"] for t in request["tools"]}
        for call in response["choices"][0]["message"].get("tool_calls", []):
            name = call["function"]["name"]
            args = json.loads(call["function"]["arguments"])
            errors = schema_errors(args, schemas[name])
            raw_schema_checks.append(
                {"request_index": index, "tool": name, "valid": not errors, "errors": errors}
            )
            actual_tool_calls.append(name)
    checks = {
        "run_has_no_execution_error": raw["error"] is None,
        "predeclared_targets_unchanged": protocol["targets_total_prompt_tokens"]
        == [8192, 16384, 24576, 30720, 30721, 42272],
        "four_context_tiers_complete": [r["target"] for r in allowed]
        == [8192, 16384, 24576, 30720],
        "four_context_tiers_integrity": all(
            r["passed"]
            and r["echo_correct"]
            and r["provider_prompt_tokens"] == r["target"] == r["preflight"]["prompt_tokens"]
            for r in allowed
        ),
        "two_overflows_rejected_before_inference": [r["target"] for r in rejected] == [30721, 42272]
        and all(
            r["passed"]
            and r["inference_requests"] == 0
            and r["error_code"] == "context_limit_exceeded"
            for r in rejected
        ),
        "accepted_preflights_verified": all(
            r.get("integrity_verified") is True for r in preflights if r["decision"] == "allow"
        ),
        "rejected_preflights_not_forwarded": all(
            r["inference_forwarded"] is False
            for r in preflights
            if r["decision"] == "context_limit_exceeded"
        ),
        "paired_legal_wire_identical": raw["paired_wire_passed"] is True
        and (run / "request-01.json").read_bytes() == (run / "request-02.json").read_bytes(),
        "log_delta_hash_matches": hashlib.sha256(delta).hexdigest()
        == raw["server_log_delta_sha256"],
        "no_actual_truncation": not warnings,
        "native_function_schema_validated": "read_artifact" in actual_tool_calls
        and "invoke_model" in actual_tool_calls
        and all(row["valid"] for row in raw_schema_checks),
        "native_failure_multiturn_terminal": sdk["native_protocol_passed"] is True
        and sdk["final_answer"] == "A"
        and sdk["usage"]["manager_turns"] >= 3,
        "fixed_strong_roles_isolated": sdk["role_isolation_passed"] is True
        and sdk["cloud_transport_attempts"] == 0,
        "real_sdk_parallel_semantics": parallel["passed"] is True
        and parallel["peak_concurrent_actions"] == 2
        and parallel["live_model_requests"] == 0,
        "skills_unchanged": raw["skills_sha256"]
        == protocol["skills_sha256"]
        == "d8b75f3ce6e76ab19fa16328acc7f4ffce56988ab5d6abd794c95866d9b1f422",
        "historical_journal_unchanged": raw["journal_sha256"]
        == protocol["journal_sha256"]
        == "e8e796e0b9bb2e3ebf1c2492c96138a20e05fca246bcb029c205f799339fa3a9",
        "no_formal_dispatch": raw["formal_execution_allowed"] is False
        and raw["formal_cells"] == 0
        and raw["historical_phase2_resumed"] is False,
    }
    return {
        "version": "manager-context-gate-1-independent-audit-v1",
        "utc": datetime.now(UTC).isoformat(),
        "gate1_passed": all(checks.values()),
        "checks": checks,
        "capacity": capacity,
        "native_smoke": sdk,
        "sdk_parallel": parallel,
        "actual_tool_calls": actual_tool_calls,
        "raw_schema_checks": raw_schema_checks,
        "truncation_events": warnings,
        "original_receipt_gate1_passed": raw["gate1_passed"],
        "original_receipt_sha256": hashlib.sha256((run / "receipt.json").read_bytes()).hexdigest(),
        "audit_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "log_parser_source_sha256": hashlib.sha256(
            Path(inspect.getfile(truncation_events)).read_bytes()
        ).hexdigest(),
        "adjudication": "Original receipt retained. The substring log parser misclassified "
        "truncated=0; corrected offline. Raw schema errors remain blocking, even when the "
        "existing native runtime supplies a default empty arguments object. No model rerun, "
        "schema repair, or acceptance relaxation.",
        "inference_requests_during_audit": 0,
        "formal_execution_allowed": False,
        "formal_cells": 0,
        "historical_phase2_resumed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    owner = Path("/home/super/xiaoming/lightweight-planner-competence-v1/context-repair-001")
    if (
        sys.platform != "linux"
        or args.run.resolve().parent != owner
        or (args.output.resolve().parent != owner)
    ):
        raise RuntimeError("audit must remain in the isolated controller evidence namespace")
    result = audit(args.run)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
