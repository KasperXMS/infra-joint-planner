"""Offline audit of existing evidence. No models, Workers, tc, or datasets are invoked.

The supplied reference is evaluation-private and used only by the secondary metric.
The input archive is never extracted or modified. Outputs require a NEW directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from importlib import import_module
from pathlib import Path
from typing import Any

from infra_joint.evaluation.trace_audit import (
    summarize_concurrency,
    summarize_cost,
    summarize_profiles,
)
from infra_joint.evaluation.yesno_audit import audit_yesno


def audit_run(events: list[dict[str, Any]], result: dict[str, Any]) -> dict[str, Any]:
    final_graph = next(
        (e["payload"] for e in reversed(events) if e["event_type"] == "workflow.graph.snapshot"),
        {"nodes": [], "edges": []},
    )
    nodes = {n["action_id"]: n for n in final_graph["nodes"]}
    decisions = [e for e in events if e["event_type"] == "logical.batch.started"]
    first_decision = decisions[0]["payload"]["decision_id"] if decisions else None
    first_actions = [
        aid
        for e in decisions
        if e["payload"]["decision_id"] == first_decision
        for aid in e["payload"]["action_ids"]
    ]
    first_bytes = sum(
        transfer["bytes_transferred"]
        for e in events
        if e["event_type"] == "physical.execution" and e["payload"]["action_id"] in first_actions
        for transfer in e["payload"].get("execution", {}).get("transfers", [])
    )
    first_profile = next(
        (
            {
                "step_id": e["step_id"],
                "timestamp": e["timestamp"],
                "action_id": e["payload"]["action_id"],
                "profile": e["payload"]["physical_profile"],
            }
            for e in events
            if e["event_type"] == "logical.observation"
            and isinstance(e["payload"].get("physical_profile"), dict)
        ),
        None,
    )
    verifications: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    for i, e in enumerate(events):
        if e["event_type"] == "logical.observation":
            observations.append(e)
        if e["event_type"] != "logical.verification":
            continue
        next_model = next(
            (
                later
                for later in events[i + 1 :]
                if later["event_type"] == "logical.observation"
                and nodes.get(later["payload"]["action_id"], {}).get("operator") == "invoke_model"
            ),
            None,
        )
        available = [
            {
                "step_id": o["step_id"],
                "action_id": o["payload"]["action_id"],
                "produced_information": o["payload"].get("produced_information", []),
                "inline_text": o["payload"].get("output", {}).get("text"),
            }
            for o in observations
            if o["payload"].get("succeeded")
        ]
        verifications.append(
            {
                **e["payload"],
                "step_id": e["step_id"],
                "timestamp": e["timestamp"],
                "exact_verifier_input": "unknown: not persisted in historical JSONL",
                "reconstructed_successful_observations": available,
                "next_model_observation": next_model,
            }
        )
    failures = [
        {"step_id": e["step_id"], "timestamp": e["timestamp"], **e["payload"]}
        for e in events
        if e["event_type"] == "logical.observation" and not e["payload"].get("succeeded")
    ]
    anomalies = []
    for failure in failures:
        if failure.get("failure_code") != "missing_input":
            continue
        node = nodes.get(failure["action_id"], {})
        for aid in node.get("inputs", []):
            producers = [
                {
                    "step_id": e["step_id"],
                    "timestamp": e["timestamp"],
                    "action_id": e["payload"]["action_id"],
                    "artifact": artifact,
                }
                for e in events
                if e["event_type"] == "logical.observation" and e["payload"].get("succeeded")
                for artifact in e["payload"].get("produced_information", [])
                if artifact["artifact_id"] == aid and e["timestamp"] < failure["timestamp"]
            ]
            if producers:
                anomalies.append({"artifact_id": aid, "producers": producers, "failure": failure})
    loop = result.get("loop") or {}
    return {
        "run_id": result["run_id"],
        "completion": result["execution_completed"],
        "raw_terminal_output": result.get("final_answer"),
        "original_evaluation": result.get("evaluation"),
        "failure": result.get("failure"),
        "cost": summarize_cost(events),
        "concurrency": summarize_concurrency(events),
        "profiles": summarize_profiles(events),
        "first_action": {
            "decision_id": first_decision,
            "actions": [nodes[a] for a in first_actions],
            "transfer_bytes": first_bytes,
            "first_observed_profile": first_profile,
            "initial_profile_in_manager_input": False,
            "initial_input_evidence": "native_agents.py:_manager_input; deterministic regression",
        },
        "verifier_sequence": verifications,
        "typed_failures": failures,
        "artifact_visibility_anomalies": anomalies,
        "graph_nodes": len(nodes),
        "graph_edges": len(final_graph["edges"]),
        "manager_turns": sum(
            e["event_type"] == "logical.reasoning.completed"
            and e["payload"].get("logical_agent_id") == "manager"
            for e in events
        ),
        "verifier_calls": len(verifications),
        "subagent_calls": sum(e["event_type"] == "logical.subagent.start" for e in events),
        "terminal_action_id": loop.get("terminal_action_id"),
        "logical_action_arguments_and_model_prompts": "unknown: not persisted historically",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--private-reference", choices=("yes", "no"), required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("audit requires a new output directory; overwrites are forbidden")
    archive_hash = hashlib.sha256(args.archive.read_bytes()).hexdigest()
    records = []
    hashes: dict[str, str] = {}
    with tarfile.open(args.archive, "r:gz") as archive:
        members = sorted(
            m.name
            for m in archive.getmembers()
            if m.isfile()
            and m.name.startswith(("matrix-r1/", "matrix-r2/", "matrix-r3/"))
            and m.name.endswith("/trace.jsonl")
        )
        if len(members) != 12:
            raise RuntimeError(f"expected exactly 12 formal traces, found {len(members)}")
        for name in members:
            raw: dict[str, bytes] = {}
            for member in (name, name.replace("trace.jsonl", "result.json")):
                stream = archive.extractfile(member)
                if stream is None:
                    raise RuntimeError(f"archive member missing: {member}")
                raw[member] = stream.read()
                hashes[member] = hashlib.sha256(raw[member]).hexdigest()
            events = [json.loads(line) for line in raw[name].splitlines() if line.strip()]
            result = json.loads(raw[name.replace("trace.jsonl", "result.json")])
            record = audit_run(events, result)
            record["condition"] = "/".join(name.split("/")[:2])
            record["source_trace"] = name
            record["secondary_audit_metric"] = audit_yesno(
                result.get("final_answer"),
                reference=args.private_reference,
            ).model_dump(mode="json")
            records.append(record)
    if len({r["run_id"] for r in records}) != 12:
        raise RuntimeError("formal run IDs must be unique")
    if hashlib.sha256(args.archive.read_bytes()).hexdigest() != archive_hash:
        raise RuntimeError("input evidence changed during analysis")
    args.output.mkdir(parents=True, exist_ok=False)
    payload = {
        "audit_version": "qwen-multihop-trace-audit-v1",
        "formal_benchmark_reruns": 0,
        "source_archive_sha256": archive_hash,
        "source_member_sha256": hashes,
        "analysis_source_sha256": {
            source.name: hashlib.sha256(source.read_bytes()).hexdigest()
            for source in (
                Path(__file__),
                Path(import_module(summarize_cost.__module__).__file__),
                Path(import_module(audit_yesno.__module__).__file__),
            )
        },
        "secondary_metric_notice": "post-hoc audit metric, not original benchmark score",
        "runs": records,
    }
    (args.output / "audit-v1.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "audit_path": str(args.output / "audit-v1.json"),
                "source_archive_sha256": archive_hash,
                "rows": [
                    {
                        "condition": r["condition"],
                        "completion": r["completion"],
                        "original": (r["original_evaluation"] or {}).get("benchmark_score"),
                        "canonical": r["secondary_audit_metric"],
                        "cost": r["cost"],
                        "concurrency": r["concurrency"],
                        "profiles": r["profiles"],
                        "first_operators": [a["operator"] for a in r["first_action"]["actions"]],
                        "first_bytes": r["first_action"]["transfer_bytes"],
                        "first_profile": r["first_action"]["first_observed_profile"],
                        "first_ready": next(
                            (
                                v["verification_index"]
                                for v in r["verifier_sequence"]
                                if v["status"] == "ready_for_synthesis"
                            ),
                            None,
                        ),
                        "ready_reason": next(
                            (
                                v["reason"]
                                for v in r["verifier_sequence"]
                                if v["status"] == "ready_for_synthesis"
                            ),
                            None,
                        ),
                    }
                    for r in records
                ],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
