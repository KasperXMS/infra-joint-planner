"""Append-only offline audit of false quote mutation guards; no model calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(root: Path) -> dict[str, Any]:
    journal = root / "phase1-attempts.jsonl"
    before = journal.read_bytes()
    records = [json.loads(line) for line in before.splitlines()]
    previous = "0" * 64
    for index, record in enumerate(records):
        assert record["sequence"] == index and record["previous_sha256"] == previous
        assert record["sha256"] == digest({k: v for k, v in record.items() if k != "sha256"})
        previous = record["sha256"]
    freeze = json.loads((root / "execution-freeze-001.json").read_text())
    source = root / "app/src/infra_joint/control/quote.py"
    assert file_digest(source) == freeze["source_sha256"]["src/infra_joint/control/quote.py"]
    code = """
import json
from infra_joint.control.contracts import ExecutionRequirements, LogicalModelAction
from infra_joint.control.quote import action_sha256
a = LogicalModelAction(action_id='a', owner_agent_id='manager', prompt='Synthetic.',
    requirements=ExecutionRequirements(modalities=frozenset({'text','image'})))
b = a.model_copy(deep=True)
print(json.dumps({'semantically_equal':a == b, 'hash_equal':action_sha256(a) == action_sha256(b),
    'original_requirements':a.requirements.model_dump(mode='json'),
    'copied_requirements':b.requirements.model_dump(mode='json')}))
"""
    replay = subprocess.run([sys.executable, "-c", code], check=True, capture_output=True,
                            text=True, env={**os.environ, "PYTHONHASHSEED": "33",
                                            "PYTHONPATH": str(root / "app/src")})
    reproduction = json.loads(replay.stdout)
    assert reproduction["semantically_equal"] and not reproduction["hash_equal"]
    settled = [r for r in records if r["event"] == "settled"]
    affected: list[dict[str, Any]] = []
    all_traces: dict[str, str] = {}
    protocol_summaries: list[dict[str, Any]] = []
    for ordinal, record in enumerate(settled, 1):
        run_id = record["run_id"]
        reservation = next(r for r in records if r["event"] == "reserved" and r["run_id"] == run_id)
        directory = (root / "evidence" / reservation["cell_id"]
                     / f"attempt{reservation['attempt_index']}")
        trace = directory / "runs" / run_id / "trace.jsonl"
        all_traces[run_id] = file_digest(trace)
        events = [json.loads(line) for line in trace.read_text().splitlines()]
        protocols = [e["payload"] for e in events
                     if e["event_type"] == "logical.cost_quote.run.end"]
        if protocols:
            assert len(protocols) == 1
            protocol_summaries.append({"settlement_ordinal": ordinal, "run_id": run_id,
                                       "trace_sha256": all_traces[run_id], **protocols[0]})
        failures = [(i, e["payload"]) for i, e in enumerate(events)
                    if e["event_type"] == "logical.cost_quote.rejected"
                    and e["payload"]["failure_code"] == "quoted_action_mutated"]
        if not failures:
            continue
        quotes = {e["payload"]["quote"]["quote_id"]: e["payload"] for e in events
                  if e["event_type"] == "logical.cost_quote.created"}
        calls: dict[str, tuple[dict[str, Any], Path]] = {}
        for path in sorted((directory / "private/api").glob("*-response.json")):
            raw = json.loads(path.read_text())
            for choice in raw.get("choices", []):
                for call in choice.get("message", {}).get("tool_calls", []) or []:
                    calls[call["id"]] = (call, path)
        receipts = []
        for index, failure in failures:
            control = next(e["payload"] for e in reversed(events[:index])
                           if e["event_type"] == "logical.cost_quote.control_timing"
                           and e["payload"]["operation"] == "authorize")
            assert control["succeeded"] is False
            quote_id = control["identifier"]
            created = quotes[quote_id]
            call_id = failure["action_id"].removeprefix("manager:")
            call, response_path = calls[call_id]
            assert call["function"]["name"] == "commit_quote"
            arguments = json.loads(call["function"]["arguments"])
            assert arguments == {"quote_id": quote_id}
            assert digest(created["action"]) == created["quote"]["action_sha256"]
            receipts.append({
                "quote_id": quote_id, "quoted_action_id": created["action"]["action_id"],
                "commit_call_id": call_id, "commit_only_supplied_quote_id": True,
                "requirements": created["action"].get("requirements"),
                "original_action_bytes_match_quote_hash": True,
                "response_file": str(response_path.relative_to(directory)),
                "response_sha256": file_digest(response_path),
            })
        affected.append({"settlement_ordinal": ordinal, "run_id": run_id,
                         "cell_id": reservation["cell_id"],
                         "settlement_sha256": record["sha256"],
                         "original_admission_sha256": file_digest(directory / "admission.json"),
                         "trace_sha256": all_traces[run_id], "false_mutation_receipts": receipts,
                         "protocol_summaries": protocols})
    assert journal.read_bytes() == before, "audit must bind one unchanged journal prefix"
    return {
        "version": "quote-runtime-confounder-review-v1",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "journal_sha256": hashlib.sha256(before).hexdigest(),
        "settled_attempts_audited": len(settled),
        "all_trace_sha256": all_traces, "frozen_quote_source_sha256": file_digest(source),
        "auditor_source_sha256": file_digest(Path(__file__)),
        "synthetic_frozen_source_reproduction": reproduction, "hash_seed": 33,
        "affected_attempts": affected,
        "quote_protocol_summaries": protocol_summaries,
        "false_mutation_failure_count": sum(len(a["false_mutation_receipts"]) for a in affected),
        "affected_methods": dict(Counter(a["cell_id"].rsplit("-", 1)[1] for a in affected)),
        "not_planner_action_mutation": True, "existing_evidence_modified": False,
        "formal_execution_changed": False, "planner_calls": 0, "model_inference_calls": 0,
        "historical_admissions_not_rewritten": True, "not_an_admission_waiver": True,
        "requires": ("generic integrity repair, full tests, new execution freeze "
                     "and affected-only reruns"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, ensure_ascii=False)
    print(json.dumps({"output": str(args.output), "sha256": file_digest(args.output),
                      "settled_attempts_audited": result["settled_attempts_audited"],
                      "affected": [{k: a[k] for k in ("settlement_ordinal", "cell_id")}
                                   for a in result["affected_attempts"]],
                      "false_mutation_failure_count": result["false_mutation_failure_count"]}))
