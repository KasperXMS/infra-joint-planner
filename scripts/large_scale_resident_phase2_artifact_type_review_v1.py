"""Exact offline model-artifact type review; no execution or admission rewrite."""

from __future__ import annotations

import argparse
import hashlib
import json
from importlib import import_module
from pathlib import Path
from typing import Any, cast

import large_scale_resident_model_artifact_type_review_v1 as pure
import large_scale_resident_phase2_derived_companion_review_v3 as ancestor
import large_scale_resident_phase2_derived_field_review_v1 as original
import large_scale_resident_phase2_native_field_review_v1 as initial
import large_scale_resident_phase2_native_renewed_environment_v1 as previous

from infra_joint.control import native_agents
from infra_joint.control.provenance import provenance_sha256
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.experiments.attempt_ledger import Attempt, QueueLease
from infra_joint.operators.structured import structured_operator_specs

DIRECTORY = original.DIRECTORY
REASON = original.REASON
VERSION = "phase2-source-bound-model-artifact-type-review-v1"
OLD_VERSIONS = frozenset({ancestor.VERSION, ancestor.ANCESTOR_VERSION, ancestor.OLD_VERSION})
SOURCE_PATHS = (
    *pure.SOURCE_PATHS,
    "src/infra_joint/config.py",
    "src/infra_joint/cli.py",
    "src/infra_joint/core/state.py",
)


def _object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError("exact evidence object required")
    return cast(dict[str, Any], value)


def _array(value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise RuntimeError("exact evidence array required")
    return cast(list[Any], value)


def sources() -> dict[str, str]:
    return {
        **ancestor.sources(),
        Path(pure.__file__).name: previous.cadence.digest(Path(pure.__file__)),
        Path(__file__).name: previous.cadence.digest(Path(__file__)),
    }


def context_binding(root: Path, attempt: Attempt, directory: Path) -> dict[str, Any]:
    """Require explicit serialized envelopes, exact startup inventory and replicas."""
    pids = previous.read(directory / "worker-pids.json")
    states = previous.read(directory / "private/worker-state-after.json")
    if not pids or set(pids) != set(states):
        raise RuntimeError("complete exact Worker startup inventory required")
    config_path = previous.frozen.POOL_CONFIG
    config = vars(previous.frozen.frozen)["_yaml"](config_path)
    environment = _object(config.get("environment"))
    serialized = _array(environment.get("deployments"))
    deployments: dict[str, dict[str, Any]] = {}
    for item in serialized:
        raw = _object(item)
        if not isinstance(raw.get("deployment_id"), str):
            raise RuntimeError("exact serialized deployment identity required")
        identifier = raw["deployment_id"]
        if identifier in deployments:
            raise RuntimeError("unique environment deployments required")
        deployments[identifier] = raw
    settings: dict[str, Any] = {}
    costs: set[int] = set()
    matched: set[str] = set()
    for agent, pid in pids.items():
        path = root / "worker-configs" / (attempt.run_id + "-" + agent + ".yaml")
        start = directory / "worker-starts" / (agent + ".json")
        if (
            Path(agent).name != agent
            or not isinstance(pid, int)
            or isinstance(pid, bool)
            or pid < 1
            or previous.read(start) != {"pid": pid}
            or path.is_symlink()
            or path.parent.is_symlink()
            or path.resolve().parent != root / "worker-configs"
        ):
            raise RuntimeError("owned exact Worker startup/config required")
        worker = vars(previous.frozen.frozen)["_yaml"](path)
        raw_models = _object(worker.get("deployments"))
        state_models = _array(states[agent].get("deployments"))
        state_by_id = {_object(item)["deployment_id"]: _object(item) for item in state_models}
        if len(state_by_id) != len(state_models) or set(raw_models) != set(state_by_id):
            raise RuntimeError("Worker exposed/configured deployment inventory drift")
        envelopes: dict[str, Any] = {}
        for identifier, item in raw_models.items():
            model = _object(item)
            deployed = deployments.get(identifier)
            if deployed is None or deployed.get("agent_id") != agent:
                raise RuntimeError("Worker/environment deployment ownership drift")
            fields = ("context_window", "reserved_output_tokens", "image_token_cost")
            envelope: dict[str, Any] = {key: model.get(key) for key in fields}
            if (
                any(
                    not isinstance(v, int) or isinstance(v, bool) or v < 1
                    for v in envelope.values()
                )
                or any(
                    deployed.get(k) != v or state_by_id[identifier].get(k) != v
                    for k, v in envelope.items()
                )
                or model.get("model_id") != deployed.get("model_id")
                or model.get("model_id") != state_by_id[identifier].get("model_id")
                or sorted(model.get("modalities", [])) != sorted(deployed.get("modalities", []))
                or sorted(model.get("modalities", []))
                != sorted(state_by_id[identifier].get("modalities", []))
            ):
                raise RuntimeError("explicit context/image/reserve envelopes must agree")
            costs.add(envelope["image_token_cost"])
            matched.add(identifier)
            envelopes[identifier] = envelope
        settings[agent] = {
            "pid": pid,
            "worker_config_path": str(path),
            "worker_config_sha256": previous.cadence.digest(path),
            "worker_start_sha256": previous.cadence.digest(start),
            "deployments": envelopes,
        }
    if matched != set(deployments) or len(costs) != 1:
        raise RuntimeError("complete consistent explicit image context accounting required")
    return {
        "image_context_tokens": next(iter(costs)),
        "settings": settings,
        "formal_pool_config_path": str(config_path),
        "formal_pool_config_sha256": previous.cadence.digest(config_path),
        "worker_pids_sha256": previous.cadence.digest(directory / "worker-pids.json"),
        "worker_state_sha256": previous.cadence.digest(
            directory / "private/worker-state-after.json"
        ),
    }


def capability_wire_proof(
    api: Path,
    events: list[dict[str, Any]],
    verified: dict[str, Any],
    selected_wire: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Exact schema and prior successful InformationObjects visible at each misuse."""
    specs = [
        item for item in structured_operator_specs() if item.operator_id == "aggregate_artifacts"
    ]
    if len(specs) != 1:
        raise RuntimeError("one frozen aggregation primitive required")
    spec = specs[0]
    expected = {
        "name": spec.operator_id,
        "description": spec.description,
        "parameters": vars(native_agents)["_native_tool_schema"](spec),
        "strict": False,
    }
    producers = {item["action_id"] for item in verified["model_output_materialization_proof"]}
    observations = {
        event["payload"]["action_id"]: event["payload"]
        for event in events
        if event["event_type"] == "logical.observation"
        and event["payload"]["action_id"] in producers
    }
    if set(observations) != producers or any(
        not item.get("succeeded") for item in observations.values()
    ):
        raise RuntimeError("every model producer requires exact successful logical observation")
    wires = {item["action_id"]: item for item in selected_wire}
    result: list[dict[str, Any]] = []
    for failed in verified["artifact_type_misuse_proof"]:
        wire = wires[failed["action_id"]]
        request_path = api / (wire["provider_call_id"] + "-request.json")
        request = previous.read(request_path)
        functions = [
            tool.get("function")
            for tool in request.get("tools", [])
            if tool.get("function", {}).get("name") == "aggregate_artifacts"
        ]
        if functions != [expected]:
            raise RuntimeError(
                "actual aggregation SDK schema differs from frozen semantic contract"
            )
        seen: dict[str, dict[str, Any]] = {}
        for message in request.get("messages", []):
            if message.get("role") != "tool" or not isinstance(message.get("content"), str):
                continue
            try:
                content = json.loads(message["content"])
            except ValueError:
                continue
            if not isinstance(content, dict):
                continue
            content = _object(content)
            if content.get("action_id") not in producers:
                continue
            identifier = content["action_id"]
            observation = observations[identifier]
            if (
                identifier in seen
                or content.get("succeeded") is not True
                or content.get("owner_agent_id") != observation.get("owner_agent_id")
                or content.get("produced_information") != observation.get("produced_information")
                or content.get("output") != observation.get("output")
            ):
                raise RuntimeError("actual prior model tool result/InformationObject drift")
            seen[identifier] = content
        if set(seen) != producers:
            raise RuntimeError(
                "failing Agent must have every exact prior materialized model result"
            )
        result.append(
            {
                "action_id": failed["action_id"],
                "request_sha256": previous.cadence.digest(request_path),
                "function_schema_sha256": provenance_sha256(expected),
                "visible_model_outputs": [
                    {
                        "producer_action_id": identifier,
                        "information_sha256": provenance_sha256(item["produced_information"]),
                        "tool_result_sha256": provenance_sha256(item),
                    }
                    for identifier, item in sorted(seen.items())
                ],
            }
        )
    return result


def validate_context_proof(binding: dict[str, Any], verified: dict[str, Any]) -> None:
    """A reported rejection must agree with the actual complete deployment envelope."""
    envelopes = {
        tuple(
            model[key] for key in ("context_window", "reserved_output_tokens", "image_token_cost")
        )
        for worker in binding["settings"].values()
        for model in worker["deployments"].values()
    }
    if len(envelopes) != 1:
        raise RuntimeError("context companion needs one exact uniform deployment envelope")
    window, reserve, image_cost = next(iter(envelopes))
    for item in verified["context_preflight_proof"]:
        if (
            item.get("context_window") != window
            or item.get("reserved_output") != reserve
            or item.get("image_context_tokens") != image_cost
        ):
            raise RuntimeError("reported context rejection differs from actual deployment contract")


def proof(root: Path, attempt: Attempt, parent_path: Path) -> dict[str, Any]:
    if (
        parent_path.is_symlink()
        or parent_path.resolve().parent != root
        or not parent_path.name.startswith("phase2-control-freeze-")
    ):
        raise RuntimeError("owned original PhaseII parent required")
    saved = previous.read(parent_path)
    core = original.core
    if (
        saved["source_sha256"] != core.previous.source_bindings()
        or saved["execution_freeze_sha256"] != core.frozen.verify_freeze()
    ):
        raise RuntimeError("original parent/atomic source drift")
    directory = core.evidence(root, attempt)
    admission = previous.read(directory / "admission.json")
    if (
        attempt.disposition != "confounder"
        or attempt.reason != original.previous.field.GATE
        or admission.get("problems") != [original.previous.field.GATE]
        or admission.get("operational_incidents")
        or provenance_sha256(admission) != attempt.receipt_sha256
        or attempt.execution_sha256 != saved["execution_freeze_sha256"]
    ):
        raise RuntimeError("only exact original settled field gate can be reviewed")
    config = vars(core.frozen.frozen)["_yaml"](root / "cell-configs" / (attempt.run_id + ".yaml"))
    shutdown = previous.read(directory / "worker-shutdown.json")
    if (
        core.previous.previous.admission(directory, config, Path(saved["pricing_path"]))
        != admission
        or previous.read(directory / "process-exit.json")["returncode"] != 0
        or shutdown.get("verified_exited") is not True
        or shutdown.get("errors")
        or previous.read(directory / "private/residency-validation.json")["passed"] is not True
    ):
        raise RuntimeError("complete original admission/exit/residency must reproduce")
    tc = previous.read(directory / "tc-attestation.json")
    if tc["cleanup_error"] is not None or tc["original_qdisc"] != tc["restored_qdisc"]:
        raise RuntimeError("artifact proof cannot waive network cleanup")
    binding = context_binding(root, attempt, directory)
    events = JsonlTraceWriter(directory / "runs" / attempt.run_id / "trace.jsonl").read_all()
    roots = [
        e["payload"]
        for e in events
        if e["event_type"] == "logical.reasoning.input"
        and e["payload"]["logical_agent_id"] == "manager"
    ]
    if not roots:
        raise RuntimeError("actual root task view required")
    task = json.loads(roots[0]["input_items"][0]["content"])["task"]
    states = previous.read(directory / "private/worker-state-after.json")
    result = previous.read(directory / "runs" / attempt.run_id / "result.json")
    verified = pure.review(
        events, result, states, image_context_tokens=binding["image_context_tokens"]
    )
    validate_context_proof(binding, verified)
    actual = original.bindings.frozen_sources(root, attempt, SOURCE_PATHS)
    worker_freeze = root / "execution-freeze-003.json"
    contract = previous.read(worker_freeze)["source_sha256"]
    tested: dict[str, str] = {}
    for path in SOURCE_PATHS:
        module = import_module(path.removeprefix("src/").removesuffix(".py").replace("/", "."))
        if module.__file__ is None:
            raise RuntimeError("file-backed proof implementation required")
        tested[path] = previous.cadence.digest(Path(module.__file__))
        if (
            contract.get(path) != actual[path]
            or previous.cadence.digest(root / "app-input-cardinality-repair-003" / path)
            != actual[path]
        ):
            raise RuntimeError("actual Worker/atomic artifact implementation drift")
    if tested != actual:
        raise RuntimeError("tested rules must bind actual frozen execution sources")
    targets = [
        *verified["artifact_type_misuse_proof"],
        *verified["model_output_materialization_proof"],
    ]
    wire = ancestor.sdk_selected_tool_proof(
        directory / "private/api",
        events,
        {
            "derived_field_proof": targets,
            "context_preflight_proof": verified["context_preflight_proof"],
            "read_artifact_limit_proof": [],
            "output_collision_proof": [],
        },
    )
    capability_wire = capability_wire_proof(directory / "private/api", events, verified, wire)
    schema = original.previous.sdk_schema_proof(directory / "private/api", task)
    if len(schema) != len(roots) or binding != context_binding(root, attempt, directory):
        raise RuntimeError("exact every-turn task schema and immutable context binding required")
    reviewed: dict[str, Any] = {
        **admission,
        "disposition": "valid",
        "reason": REASON,
        "problems": [],
        "failure_class": "workflow_composition_artifact_media_type_misuse",
        "replacement_authorized": False,
    }
    return {
        **verified,
        "version": VERSION,
        "covered_original_findings": [original.previous.field.GATE],
        "reviewed_admission": reviewed,
        "reviewed_admission_sha256": provenance_sha256(reviewed),
        "run_id": attempt.run_id,
        "original_admission_sha256": attempt.receipt_sha256,
        "original_execution_sha256": attempt.execution_sha256,
        "parent_control_path": str(parent_path),
        "parent_control_file_sha256": previous.cadence.digest(parent_path),
        "worker_context_binding": binding,
        "actual_selected_tool_wire_proof": wire,
        "actual_artifact_capability_wire_proof": capability_wire,
        "actual_manager_schema_wire_proof": schema,
        "execution_sources_sha256": actual,
        "tested_transformation_sources_sha256": tested,
        "worker_freeze_file_sha256": previous.cadence.digest(worker_freeze),
        "reviewer_sources_sha256": sources(),
        "original_evidence_file_sha256": original.bindings.evidence_files(directory),
        "new_store_or_corpus_body_decoded": False,
        "online_feedback": False,
        "formal_execution_changed": False,
        "replacement_authorized": False,
    }


def verify_sidecar(path: Path, attempt: Attempt) -> dict[str, Any]:
    if (
        path.is_symlink()
        or path.parent.is_symlink()
        or path.parent.name != DIRECTORY
        or path.name != attempt.run_id + ".json"
    ):
        raise RuntimeError("owned exact versioned artifact type sidecar required")
    value = previous.read(path)
    if value.get("version") in OLD_VERSIONS:
        return ancestor.verify_sidecar(path, attempt)
    if value.get("version") != VERSION:
        raise RuntimeError("unsupported artifact type proof version")
    if value != proof(path.parent.parent, attempt, Path(value["parent_control_path"])):
        raise RuntimeError("artifact type source/evidence proof drift")
    return value


effective_admission = original.effective_admission


def _preflight(
    value: dict[str, Any],
    expected: dict[str, dict[str, str]],
    path: Path,
    target: Attempt,
    candidate: dict[str, Any],
    schedule: tuple[Any, ...],
) -> None:
    environment = import_module("large_scale_resident_phase2_artifact_type_environment_v1")

    def routed(_name: str) -> Any:
        return environment

    previous.copied(
        vars(ancestor)["_preflight"],
        {
            "import_module": routed,
            "verify_sidecar": verify_sidecar,
            "__name__": __name__,
        },
    )(value, expected, path, target, candidate, schedule)


def create_review(manifest: Path, manifest_sha256: str, run_id: str) -> dict[str, Any]:
    environment = import_module("large_scale_resident_phase2_artifact_type_environment_v1")
    previous.frozen.require_remote()
    root = previous.frozen.ROOT
    inactive = original.core.previous.gate.evidence.private.assert_inactive
    inactive(root)
    value = previous.read(manifest)

    def fence() -> None:
        if value.get("extension_version") == environment.VERSION:
            environment.fence(manifest, manifest_sha256, value)
        else:
            environment._initial_parent(manifest, manifest_sha256)
            environment.ancestor.fence(manifest, manifest_sha256, value)

    fence()
    previous.environment.require_strata_stopped()
    directory = root / DIRECTORY
    path = directory / (run_id + ".json")
    if (
        Path(run_id).name != run_id
        or not run_id.startswith(root.name + "-phase2-")
        or directory.is_symlink()
        or path.exists()
        or path.is_symlink()
    ):
        raise RuntimeError("owned exclusive artifact type sidecar required")
    journal = root / "phase2-attempts.jsonl"
    before = journal.read_bytes()
    expected = environment.inventory(value)
    with QueueLease(root / "queue-lease.json"):
        parent = Path(previous.read(Path(value["control_path"]))["parent_control_path"])
        schedule = original.core.previous.cells_from_gate(
            previous.read(Path(value["parent"]["gate_path"]))
        )
        ledger, target = initial.pending_ledger(value, schedule, journal, run_id)
        candidate = proof(root, target, parent)
        _preflight(value, expected, path, target, candidate, schedule)
        ledger.check_disk()
        fence()
        previous.environment.require_strata_stopped()
        inactive(root, allow_current_audit_lease=True)
        if journal.read_bytes() != before or environment.current_inventory() != expected:
            raise RuntimeError("review cannot change original journal or inventory")
        directory.mkdir(exist_ok=True)
        previous.frozen.write_new(path, candidate)
        verify_sidecar(path, target)
        ledger.check_disk()
        delta = environment.extension_delta(expected, environment.current_inventory())
        exact: dict[str, dict[str, str]] = {key: {} for key in environment.GROUPS}
        exact["derived_field_sidecars"] = {path.name: previous.cadence.digest(path)}
        if journal.read_bytes() != before or delta != exact:
            raise RuntimeError("creator may add only its exact same-group artifact type sidecar")
    inactive(root)
    return {
        "sidecar_path": str(path),
        "sha256": previous.cadence.digest(path),
        "parent_manifest_sha256": manifest_sha256,
        "creator_source_sha256": previous.cadence.digest(Path(__file__)),
        "original_journal_sha256": hashlib.sha256(before).hexdigest(),
        "confirmed_artifact_type_misuse_failures": len(candidate["artifact_type_misuse_proof"]),
        "confirmed_context_preflight_failures": len(candidate["context_preflight_proof"]),
        "actual_manager_requests": len(candidate["actual_manager_schema_wire_proof"]),
        "retry": False,
        "new_store_or_corpus_body_decoded": False,
        "new_model_calls": 0,
        "atomic_execution_changed": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    print(json.dumps(create_review(args.manifest, args.manifest_sha256, args.run_id)))
