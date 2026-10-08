"""Persisted-version-specific derived companion proof within the original group.

The frozen v1 reviewer continues to own its historical sidecars. The additive
proof binds the same admission, execution and schemas plus exact closed failure
companions. It neither modifies execution nor authorizes retry or feedback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import large_scale_resident_derived_field_review_v4 as companions
import large_scale_resident_phase2_derived_companion_review_v2 as ancestor
import large_scale_resident_phase2_derived_field_review_v1 as original
import large_scale_resident_phase2_native_field_review_v1 as initial
import large_scale_resident_phase2_native_renewed_environment_v1 as previous

import infra_joint.cli as worker_cli
import infra_joint.config as worker_settings
from infra_joint.control.provenance import provenance_sha256
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.experiments.attempt_ledger import Attempt, QueueLease

DIRECTORY = original.DIRECTORY
REASON = original.REASON
VERSION = "phase2-source-propagated-derived-field-companion-review-v3"
ANCESTOR_VERSION = ancestor.VERSION
OLD_VERSION = "metadata-bound-derived-record-field-proof-v1"
READ_LIMIT = 65_536
SOURCE_PATHS = (*companions.SOURCE_PATHS, "src/infra_joint/config.py", "src/infra_joint/cli.py")
WORKER_SOURCE_MODULES = (worker_cli, worker_settings)


def _object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError("exact evidence object required")
    return cast(dict[str, Any], value)


def _array(value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise RuntimeError("exact evidence array required")
    return cast(list[Any], value)


def sources() -> dict[str, str]:
    return {**previous.sources(), **original.sources(), **ancestor.sources(),
            Path(companions.__file__).name: previous.cadence.digest(Path(companions.__file__)),
            Path(__file__).name: previous.cadence.digest(Path(__file__))}


def read_limit_binding(root: Path, attempt: Attempt, directory: Path) -> dict[str, Any]:
    """Bind the serialized settings consumed by the unchanged Worker startup."""
    pids_path = directory / "worker-pids.json"
    pids = previous.read(pids_path)
    states = previous.read(directory / "private/worker-state-after.json")
    if not pids or set(pids) != set(states):
        raise RuntimeError("complete exact Worker process/config inventory required")
    settings: dict[str, Any] = {}
    for agent, pid in pids.items():
        path = root / "worker-configs" / (attempt.run_id + "-" + agent + ".yaml")
        start_path = directory / "worker-starts" / (agent + ".json")
        if (Path(agent).name != agent or not isinstance(pid, int) or isinstance(pid, bool)
                or pid < 1 or previous.read(start_path) != {"pid": pid}
                or path.is_symlink() or path.parent.is_symlink()
                or path.resolve().parent != root / "worker-configs"):
            raise RuntimeError("owned exact Worker startup binding required")
        config = vars(previous.frozen.frozen)["_yaml"](path)
        if config.get("max_read_artifact_bytes") != READ_LIMIT:
            raise RuntimeError("derived read-limit proof requires unchanged explicit 65536 setting")
        settings[agent] = {"worker_config_path": str(path),
                           "worker_config_file_sha256": previous.cadence.digest(path),
                           "worker_start_file_sha256": previous.cadence.digest(start_path),
                           "pid": pid, "max_read_artifact_bytes": READ_LIMIT}
    return {"worker_pids_file_sha256": previous.cadence.digest(pids_path),
            "settings": settings, "config_driven_startup_unchanged": True}


def proof(root: Path, attempt: Attempt, parent: Path, historical: Path) -> dict[str, Any]:
    directory = original.core.evidence(root, attempt)
    binding = read_limit_binding(root, attempt, directory)
    pure = SimpleNamespace(**{**vars(companions), "SOURCE_PATHS": SOURCE_PATHS})
    value = cast(dict[str, Any], previous.copied(original.proof, {
        "derived": pure, "sources": sources})(root, attempt, parent, historical))
    if (binding != read_limit_binding(root, attempt, directory)
            or not value.get("derived_field_proof")):
        raise RuntimeError("complete companion proof and immutable read-limit binding required")
    events = JsonlTraceWriter(directory / "runs" / attempt.run_id / "trace.jsonl").read_all()
    selected_wire = sdk_selected_tool_proof(directory / "private/api", events, value)
    return {**value, "version": VERSION, "worker_read_limit_binding": binding,
            "actual_selected_tool_wire_proof": selected_wire,
            "historical_derived_reviewer_unchanged": True}


def sdk_selected_tool_proof(api_root: Path, events: list[dict[str, Any]],
                            verified: dict[str, Any]) -> list[dict[str, Any]]:
    """Bind exact selected arguments to actual owner/provider tool responses.

    No prompt, query, answer or artifact body is copied to this metadata proof.
    Compare the raw selected arguments before defaults and output namespacing.
    """
    targets = {item["action_id"] for key in (
        "derived_field_proof", "read_artifact_limit_proof", "context_preflight_proof",
        "output_collision_proof") for item in verified[key]}
    targets.update(item["reserved_action_id"] for item in verified["output_collision_proof"])
    selected: dict[str, dict[str, Any]] = {}
    reasoning: dict[str, dict[str, Any]] = {}
    for event in events:
        if event["event_type"] == "logical.reasoning.input":
            payload = event["payload"]
            decision = payload.get("decision_id")
            if not isinstance(decision, str) or decision in reasoning:
                raise RuntimeError("unique exact logical reasoning inputs required")
            reasoning[decision] = payload
        if event["event_type"] != "logical.action.selected":
            continue
        payload = event["payload"]
        if payload.get("action_id") not in targets:
            continue
        identifier = payload["action_id"]
        if identifier in selected:
            raise RuntimeError("unique exact selected action evidence required")
        selected[identifier] = payload
    if set(selected) != targets or not targets:
        raise RuntimeError("every companion/field action requires its actual selected event")
    actual: dict[str, tuple[dict[str, Any], dict[str, Any], Path, Path, Path]] = {}
    usages = sorted(api_root.glob("*-usage.json"))
    seen: set[str] = set()
    for usage_path in usages:
        usage = previous.read(usage_path)
        call_id = usage.get("call_id")
        recipient = usage.get("recipient")
        if (not isinstance(call_id, str) or Path(call_id).name != call_id or call_id in seen
                or usage_path.name != call_id + "-usage.json" or usage.get("status") != 200
                or recipient not in {"manager", "specialist", "verifier"}):
            raise RuntimeError("unique successful owned provider receipts required")
        seen.add(call_id)
        request_path = api_root / (call_id + "-request.json")
        response_path = api_root / (call_id + "-response.json")
        request, response = previous.read(request_path), previous.read(response_path)
        choices = _array(response.get("choices", []))
        if len(choices) != 1:
            raise RuntimeError("one exact actual provider choice required")
        choice = _object(choices[0])
        calls = _array(_object(choice.get("message", {})).get("tool_calls") or [])
        for raw_call in calls:
            call = _object(raw_call)
            tool_id = call.get("id")
            candidates = [identifier for identifier in targets
                          if isinstance(tool_id, str) and identifier.endswith(":" + tool_id)]
            if not candidates:
                continue
            if len(candidates) != 1:
                raise RuntimeError("actual tool call ID requires one exact selected owner")
            identifier = candidates[0]
            payload = selected[identifier]
            owner = payload.get("logical_agent_id")
            decision = payload.get("decision_id")
            if not isinstance(owner, str) or not owner or not isinstance(decision, str):
                raise RuntimeError("selected action requires exact owner/decision identities")
            if identifier != owner + ":" + str(tool_id) or not decision.startswith(
                    owner + ":native-turn:"):
                raise RuntimeError("selected action/decision prefix must bind its exact SDK owner")
            expected_recipient = "manager" if owner == "manager" else "specialist"
            expected_agent = "manager" if owner == "manager" else "bounded_specialist"
            logical_input = reasoning.get(decision, {})
            items = _array(logical_input.get("input_items", []))
            if (recipient != expected_recipient or usage.get("agent_name") != expected_agent
                    or logical_input.get("logical_agent_id") != owner
                    or provenance_sha256(items) != logical_input.get("input_sha256")
                    or not items or not isinstance(_object(items[0]).get("content"), str)):
                raise RuntimeError("actual SDK recipient requires exact logical reasoning input")
            first_input = cast(str, _object(items[0])["content"])
            messages = _array(request.get("messages", []))
            user_texts: list[str] = []
            for raw_message in messages:
                message = _object(raw_message)
                if message.get("role") != "user":
                    continue
                content = message.get("content")
                if isinstance(content, str):
                    user_texts.append(content)
                elif isinstance(content, list):
                    for raw_block in cast(list[Any], content):
                        block = _object(raw_block)
                        if isinstance(block.get("text"), str):
                            user_texts.append(block["text"])
            if user_texts.count(first_input) != 1:
                raise RuntimeError("actual SDK request lacks its exact owner-bound initial input")
            if recipient == "specialist":
                try:
                    assignment = _object(_object(json.loads(first_input))["assignment"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise RuntimeError("specialist input requires its exact assignment") from exc
                if assignment.get("logical_agent_id") != owner:
                    raise RuntimeError("actual specialist assignment/owner drift")
            if identifier in actual or choice.get("finish_reason") != "tool_calls":
                raise RuntimeError("one untruncated actual provider tool call per action required")
            function = _object(call.get("function", {}))
            schemas = [_object(_object(tool).get("function", {}))
                       for tool in _array(request.get("tools", []))
                       if _object(_object(tool).get("function", {})).get("name")
                       == function.get("name")]
            arguments = function.get("arguments")
            if len(schemas) != 1 or not isinstance(arguments, str):
                raise RuntimeError("actual selected tool must use its exposed function schema")
            try:
                decoded = json.loads(arguments)
            except (TypeError, ValueError) as exc:
                raise RuntimeError("exact selected tool JSON required") from exc
            if (payload.get("logical_agent_id") != owner
                    or payload.get("operator") != function.get("name")
                    or payload.get("selected_tool_arguments") != decoded):
                raise RuntimeError("actual SDK tool arguments/owner differ from selected action")
            actual[identifier] = (usage, function, request_path, response_path, usage_path)
    if set(actual) != targets:
        raise RuntimeError("every field/companion selected action needs its actual SDK wire")
    return [{"action_id": identifier, "owner_agent_id": selected[identifier]["logical_agent_id"],
             "operator": selected[identifier]["operator"], "provider_call_id": values[0]["call_id"],
             "arguments_sha256": provenance_sha256(values[1]["arguments"]),
             "selected_event_sha256": provenance_sha256(selected[identifier]),
             "logical_input_sha256": reasoning[selected[identifier]["decision_id"]][
                 "input_sha256"],
             "request_file_sha256": previous.cadence.digest(values[2]),
             "response_file_sha256": previous.cadence.digest(values[3]),
             "usage_file_sha256": previous.cadence.digest(values[4])}
            for identifier, values in sorted(actual.items())]


def verify_sidecar(path: Path, attempt: Attempt) -> dict[str, Any]:
    """Dispatch exact historical versions unchanged; filter companions are additive."""
    if (path.is_symlink() or path.parent.is_symlink() or path.parent.name != DIRECTORY
            or path.name != attempt.run_id + ".json"):
        raise RuntimeError("owned exact versioned derived sidecar required")
    value = previous.read(path)
    if value.get("version") in {OLD_VERSION, ANCESTOR_VERSION}:
        return ancestor.verify_sidecar(path, attempt)
    if value.get("version") != VERSION:
        raise RuntimeError("unsupported derived proof version")
    if value != proof(path.parent.parent, attempt, Path(value["parent_control_path"]),
                      Path(value["historical_sidecar_path"])):
        raise RuntimeError("derived companion source/evidence proof drift")
    return value


def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
    # Same reason and immutable admission binding; no semantic answer alteration.
    return original.effective_admission(root, attempt)


def _preflight(value: dict[str, Any], expected: dict[str, dict[str, str]],
               path: Path, target: Attempt, candidate: dict[str, Any],
               schedule: tuple[Any, ...]) -> None:
    environment = import_module("large_scale_resident_phase2_derived_companion_environment_v3")
    candidate_sha = provenance_sha256(candidate)

    def digest(file: Path) -> str:
        if file == path and not file.exists():
            return candidate_sha
        return previous.cadence.digest(file)

    def verify(file: Path, attempt: Attempt) -> dict[str, Any]:
        if file == path and not file.exists() and attempt == target:
            return candidate
        return verify_sidecar(file, attempt)

    reviewer = SimpleNamespace(**{**globals(), "verify_sidecar": verify})
    cadence = SimpleNamespace(**{**vars(previous.cadence), "digest": digest})
    pairs = previous.copied(environment._review_pairs, {"derived": reviewer, "cadence": cadence})
    membership = previous.copied(environment.membership,
                                 {"_review_pairs": pairs, "cadence": cadence})
    groups = {**expected, "derived_field_sidecars": {
        **expected["derived_field_sidecars"], path.name: candidate_sha}}

    def checked(control: dict[str, Any], cells: tuple[Any, ...], sidecar: Path, *,
                require_dispatch_ready: bool) -> previous.EnvironmentLedger:
        ledger: previous.EnvironmentLedger = membership(
            {**control, **groups}, cells, sidecar,
            require_dispatch_ready=require_dispatch_ready)
        raw = {a.run_id: a for a in ledger.original_attempts}
        effective = {a.run_id: a for a in ledger.attempts}
        for pair in value["historical_reviews"]:
            old, reviewed = Attempt(**pair["raw"]), Attempt(**pair["effective"])
            if raw.get(old.run_id) != old or effective.get(old.run_id) != reviewed:
                raise RuntimeError("historical raw/effective derived preflight pair changed")
        if ledger.exclusion != (Attempt(**value["exclusion"]["raw"]),
                                Attempt(**value["exclusion"]["effective"])):
            raise RuntimeError("original environmental exclusion changed")
        return ledger

    full_control = previous.copied(environment.full_control, {"membership": checked})
    saved, cells = full_control(Path(value["control_path"]), Path(value["sidecar_path"]),
                                groups["derived_field_sidecars"],
                                groups["filtered_field_sidecars"],
                                groups["native_argument_sidecars"])
    if saved != value["parent"] or cells != schedule:
        raise RuntimeError("complete original parent/schedule changed during derived proof")


def create_review(manifest: Path, manifest_sha256: str, run_id: str,
                  historical: Path) -> dict[str, Any]:
    environment = import_module("large_scale_resident_phase2_derived_companion_environment_v3")
    previous.frozen.require_remote()
    root = previous.frozen.ROOT
    inactive = original.core.previous.gate.evidence.private.assert_inactive
    inactive(root)
    value = previous.read(manifest)

    def fence() -> None:
        if value.get("extension_version") == environment.VERSION:
            environment.fence(manifest, manifest_sha256, value)
        else:
            if (manifest.name != environment.PARENT_NAME
                    or manifest_sha256 != environment.PARENT_SHA):
                raise RuntimeError("initial derived companion requires pinned renewed001 authority")
            environment.ancestor.fence(manifest, manifest_sha256, value)

    fence()
    previous.environment.require_strata_stopped()
    directory = root / DIRECTORY
    path = directory / (run_id + ".json")
    if (Path(run_id).name != run_id or not run_id.startswith(root.name + "-phase2-")
            or directory.is_symlink() or path.exists() or path.is_symlink()):
        raise RuntimeError("owned exclusive derived companion sidecar required")
    journal = root / "phase2-attempts.jsonl"
    before = journal.read_bytes()
    expected = environment.inventory(value)
    with QueueLease(root / "queue-lease.json"):
        parent_path = Path(previous.read(Path(value["control_path"]))["parent_control_path"])
        schedule = original.core.previous.cells_from_gate(
            previous.read(Path(value["parent"]["gate_path"])))
        ledger, target = initial.pending_ledger(value, schedule, journal, run_id)
        candidate = proof(root, target, parent_path, historical)
        _preflight(value, expected, path, target, candidate, schedule)
        ledger.check_disk()
        fence()
        previous.environment.require_strata_stopped()
        inactive(root, allow_current_audit_lease=True)
        if journal.read_bytes() != before or environment.current_inventory() != expected:
            raise RuntimeError("review cannot change the original journal or inventory")
        directory.mkdir(exist_ok=True)
        previous.frozen.write_new(path, candidate)
        verify_sidecar(path, target)
        ledger.check_disk()
        delta = environment.extension_delta(expected, environment.current_inventory())
        exact_delta: dict[str, dict[str, str]] = {key: {} for key in environment.GROUPS}
        exact_delta["derived_field_sidecars"] = {path.name: previous.cadence.digest(path)}
        if journal.read_bytes() != before or delta != exact_delta:
            raise RuntimeError("creator may add only the exact target derived companion sidecar")
    inactive(root)
    return {"sidecar_path": str(path), "sha256": previous.cadence.digest(path),
            "creator_source_sha256": previous.cadence.digest(Path(__file__)),
            "parent_manifest_sha256": manifest_sha256,
            "original_journal_sha256": hashlib.sha256(before).hexdigest(),
            "confirmed_field_failures": len(candidate["derived_field_proof"]),
            "confirmed_read_limit_failures": len(candidate["read_artifact_limit_proof"]),
            "confirmed_output_collision_failures": len(candidate["output_collision_proof"]),
            "actual_manager_requests": len(candidate["actual_manager_schema_wire_proof"]),
            "retry": False, "new_store_or_corpus_body_decoded": False,
            "new_model_calls": 0, "atomic_execution_changed": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--historical-sidecar", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(create_review(args.manifest, args.manifest_sha256,
                                   args.run_id, args.historical_sidecar)))
