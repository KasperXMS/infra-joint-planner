"""Exact raw-provider malformed specialist arguments, never a retry waiver.

Keep the frozen SDK/Manager behavior. A malformed model-generated function call
may surface as SDK UserError; source-proved composition failure is not an outage.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import agents
import agents.strict_schema
import large_scale_resident_launch_review_v1 as previous
from agents.strict_schema import ensure_strict_json_schema
from pydantic import ValidationError

from infra_joint.control.native_agents import SpecialistRequest
from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt

DIRECTORY = previous.DIRECTORY
SEMANTIC_DIRECTORY = "native-specialist-json-adjudications"
REASON = "audited_native_specialist_invalid_model_json"
GATE = "terminal_failure_requires_system_audit"
methods, records, policy = previous.methods, previous.records, previous.policy
sha256 = previous.sha256


def review(original: dict[str, Any], api_root: Path,
           events: list[dict[str, Any]]) -> dict[str, Any]:
    terminal = original.get("terminal_failure") or {}
    if (original.get("disposition") != "confounder" or original.get("reason") != GATE
            or original.get("problems") != [GATE] or original.get("operational_incidents")
            or original.get("execution_completed") is not False
            or original.get("original_evaluation") is not None
            or original.get("api_audit", {}).get("problems")
            or terminal.get("code") != "control_plane_failed"
            or terminal.get("exception_type") != "UserError"
            or [e["payload"].get("failure") for e in events
                if e["event_type"] == "run.failed"] != [terminal]
            or not events or events[-1]["event_type"] != "run.failed"):
        raise RuntimeError("native argument review cannot waive other terminal/audit findings")
    usages = [json.loads(p.read_text()) for p in api_root.glob("*-usage.json")]
    if (not usages or len({u["call_id"] for u in usages}) != len(usages)
            or any(u["status"] != 200 for u in usages)):
        raise RuntimeError("native argument proof requires unique successful provider receipts")
    roots = [u for u in usages if u["recipient"] == "manager"]
    last = max(roots, key=lambda u: u["finished_utc"])
    if last["finished_utc"] != max(u["finished_utc"] for u in usages):
        raise RuntimeError("terminal argument failure must match the last root API call")
    request = json.loads((api_root / (last["call_id"] + "-request.json")).read_text())
    response = json.loads((api_root / (last["call_id"] + "-response.json")).read_text())
    schemas = [t["function"]["parameters"] for t in request["tools"]
               if t.get("function", {}).get("name") == "consult_specialist"]
    if schemas != [ensure_strict_json_schema(SpecialistRequest.model_json_schema())]:
        raise RuntimeError("actual specialist schema must match the unchanged static contract")
    choices = response.get("choices", [])
    if len(choices) != 1 or choices[0].get("finish_reason") != "tool_calls":
        raise RuntimeError("terminal model response must be an untruncated tool call")
    calls = choices[0]["message"].get("tool_calls") or []
    if not calls or len({c["id"] for c in calls}) != len(calls):
        raise RuntimeError("unique malformed specialist calls required")
    errors, proof = [], []
    for call in calls:
        function = call["function"]
        args = function["arguments"]
        if function["name"] != "consult_specialist" or not isinstance(args, str):
            raise RuntimeError("only actual raw specialist JSON syntax failures are reviewed")
        try:
            SpecialistRequest.model_validate_json(args)
        except ValidationError as error:
            if {e["type"] for e in error.errors()} != {"json_invalid"}:
                raise RuntimeError(
                    "valid JSON/schema/capability errors require another audit") from error
            errors.append("Error running tool consult_specialist: " + str(error))
        else:
            raise RuntimeError("valid specialist arguments cannot be waived by this proof")
        proof.append({"provider_call_id": last["call_id"], "tool_call_id": call["id"],
                      "arguments_sha256": provenance_sha256(args),
                      "arguments_bytes": len(args.encode()), "failure_type": "json_invalid"})
    if terminal.get("message") not in errors:
        raise RuntimeError("terminal exception must reproduce from the exact provider arguments")
    return {"native_argument_proof": proof, "reviewed_admission": {
        **original, "disposition": "valid", "reason": REASON, "problems": [],
        "failure_class": "workflow_composition_malformed_native_tool_json",
        "replacement_authorized": False}}


def verify_sidecar(path: Path, attempt: Attempt) -> dict[str, Any]:
    root = path.parent.parent
    value = json.loads(path.read_text())
    directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
    original = json.loads((directory / "admission.json").read_text())
    if (path.is_symlink() or path.parent.name != SEMANTIC_DIRECTORY
            or path.name != attempt.run_id + ".json" or value["run_id"] != attempt.run_id
            or attempt.disposition != "confounder" or attempt.reason != GATE
            or provenance_sha256(original) != attempt.receipt_sha256
            or value["original_admission_sha256"] != attempt.receipt_sha256
            or value["original_execution_sha256"] != attempt.execution_sha256
            or value["reviewer_source_sha256"] != sha256(Path(__file__))
            or value["original_evidence_file_sha256"] != methods.evidence_files(directory)):
        raise RuntimeError("native argument proof identity/source/evidence drift")
    native = sys.modules[SpecialistRequest.__module__].__file__
    if native is None or agents.__file__ is None or agents.strict_schema.__file__ is None:
        raise RuntimeError("actual native/SDK source files required")
    sdk_root = Path(agents.__file__).parent
    sources = (Path(native), sdk_root / "agent.py", sdk_root / "run_internal/tool_execution.py",
               Path(agents.strict_schema.__file__))
    expected = {str(p.resolve().relative_to(root.resolve())): sha256(p) for p in sources}
    if value["execution_sources_sha256"] != expected:
        raise RuntimeError("argument proof must bind the actual native and SDK source files")
    for relative, digest in value["execution_sources_sha256"].items():
        if sha256(previous.owned_file(root, relative)) != digest:
            raise RuntimeError("actual native/SDK argument execution source drift")
    events = [json.loads(line) for line in (
        directory / "runs" / attempt.run_id / "trace.jsonl").open(encoding="utf-8")]
    actual = review(original, directory / "private/api", events)
    if (actual != {k: value[k] for k in actual}
            or provenance_sha256(actual["reviewed_admission"])
            != value["reviewed_admission_sha256"]):
        raise RuntimeError("native argument proof cannot be reproduced")
    return value


class ProjectionAttemptLedger(previous.ProjectionAttemptLedger):
    @property
    def attempts(self) -> tuple[Attempt, ...]:
        result = []
        for attempt in super().attempts:
            path = self.path.parent / SEMANTIC_DIRECTORY / (attempt.run_id + ".json")
            if path.exists():
                value = verify_sidecar(path, attempt)
                attempt = replace(attempt, disposition="valid", reason=REASON,
                                  receipt_sha256=value["reviewed_admission_sha256"])
            result.append(attempt)
        return tuple(result)


def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
    if attempt.reason != REASON:
        return previous.effective_admission(root, attempt)
    value = json.loads((root / SEMANTIC_DIRECTORY / (attempt.run_id + ".json")).read_text())
    if value["reviewed_admission_sha256"] != attempt.receipt_sha256:
        raise RuntimeError("effective native argument admission drift")
    return value["reviewed_admission"]
