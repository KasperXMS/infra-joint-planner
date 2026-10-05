"""Post-Phase-I private evidence diagnostics, never an execution/Agent input.

Read artifact bodies only after the resident queue/atomic actions are inactive.
Reuse exact document-ID/literal coverage without treating it as semantic truth.
Unannotated benchmarks and paraphrased evidence keep retention unknown.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

from cost_guidance_private_multihop_audit_v1 import coverage, scan_store, support_mapping
from large_scale_resident_snapshot_v1 import PREDECESSOR, ROOT, collect, sha256

from infra_joint.control.provenance import provenance_sha256

CORPUS = Path("/home/super/xiaoming/blind_baseline_6task_v1/data/corpus.json")
HOSTS = {"A4": "edge@192.168.0.104", "A5": "edge@192.168.0.105",
         "A28": "edge@192.168.0.128", "strong-4090": None}


def assert_inactive(root: Path, *, proc_root: Path = Path("/proc"),
                    allow_current_audit_lease: bool = False) -> None:
    """Account for this block's actual lease/process filenames, not old controllers."""
    handles = [root / "queue-lease.json", *root.glob("queue-process-*.json"),
               *root.glob("evidence/*/attempt*/process.json")]
    for handle in handles:
        if not handle.exists():
            continue
        pid = json.loads(handle.read_text())["pid"]
        if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
            raise RuntimeError("private audit process handle invalid")
        if (allow_current_audit_lease and handle.name == "queue-lease.json"
                and pid == os.getpid()):
            continue  # Only this auditor's lock, never an owned queue/atomic receipt.
        command = proc_root / str(pid) / "cmdline"
        if command.exists() and root.name.encode() in command.read_bytes():
            raise RuntimeError("private body audit requires inactive queue and atomic actions")


def scan_request(agent: str, request: dict[str, Any]) -> list[dict[str, Any]]:
    if agent not in HOSTS:
        raise RuntimeError("private scan unknown owning node")
    run_id = request["run_id"]
    expected = Path("/home/super" if agent == "strong-4090" else "/mnt/ssd") / (
        "heterogeneous-v1/artifacts") / ROOT.name / run_id / agent
    if (request["namespace"] != ROOT.name or Path(request["store_root"]) != expected
            or not run_id.startswith(ROOT.name + "-phase1-")
            or Path(run_id).name != run_id):
        raise RuntimeError("private scan must address exact frozen run/owner store")
    host = HOSTS[agent]
    if host is None:
        return scan_store(request)
    app = Path("/mnt/ssd") / ROOT.name / "app"
    remote = [str(app / ".venv/bin/python"), "-S",
              str(app / "scripts/cost_guidance_private_multihop_audit_v1.py"), "--scan-store"]
    value = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host,
                            shlex.join(remote)], input=json.dumps(request), text=True,
                           capture_output=True, check=True, timeout=60)
    return json.loads(value.stdout)


def audit_multihop(directory: Path, corpus_path: Path, private_source: Path) -> dict[str, Any]:
    """Artifact-store text stays on owning node; only bounded coverage returns."""
    attempt = json.loads((directory / "attempt-freeze.json").read_text())
    receipt = attempt["task_receipt"]
    if receipt["family"] != "multihop_rag":
        raise RuntimeError("support audit requires annotated MultiHop task")
    private_path = directory / "private/private-evaluation.json"
    private = json.loads(private_path.read_text())
    # The prepared file has a trailing newline; runtime copies use a different
    # JSON writer. Bind original file bytes, then compare parsed private values.
    if (sha256(private_source) != receipt["private_evaluation_sha256"]
            or provenance_sha256(private) != provenance_sha256(
                json.loads(private_source.read_text()))):
        raise RuntimeError("frozen private annotation drift")
    if sha256(corpus_path) != receipt["source"]["corpus_file_sha256"]:
        raise RuntimeError("private supporting corpus drift")
    supports = support_mapping(private, json.loads(corpus_path.read_text()))
    process = json.loads((directory / "process.json").read_text())
    run_id = process["run_id"]
    run = directory / "runs" / run_id
    result = json.loads((run / "result.json").read_text())
    admission = json.loads((directory / "admission.json").read_text())
    if provenance_sha256(result) != admission["result_sha256"]:
        raise RuntimeError("private audit result/admission drift")
    events = [json.loads(line) for line in (run / "trace.jsonl").open(encoding="utf-8")]
    states = json.loads((directory / "private/worker-state-after.json").read_text())
    placements: dict[str, tuple[str, dict[str, Any]]] = {}
    for agent, state in states.items():
        for metadata in state["artifacts"]:
            identifier = metadata["artifact_id"]
            if identifier in placements:
                previous = placements[identifier][1]
                if any(metadata[key] != previous[key]
                       for key in ("sha256_hex", "size_bytes", "media_type")):
                    raise RuntimeError("private replicated artifact metadata drift")
            placements.setdefault(identifier, (agent, metadata))
    actions = {e["payload"]["action"]["action_id"]: e["payload"]["action"] for e in events
               if e["event_type"] == "logical.action.prepared"}
    observations = {e["payload"]["action_id"]: e["payload"] for e in events
                    if e["event_type"] == "logical.observation"}
    terminal = next((e["payload"].get("terminal_action_id") for e in reversed(events)
                     if e["event_type"] == "logical.loop.end"), None)
    wanted = set()
    for identifier, action in actions.items():
        observation = observations.get(identifier)
        if observation and observation["succeeded"]:
            wanted.update(action.get("inputs", []))
            wanted.update(a["artifact_id"] for a in observation.get("produced_information", []))
    requests: dict[str, dict[str, Any]] = {}
    for identifier in sorted(wanted):
        if identifier not in placements:
            raise RuntimeError("successful information path missing persisted artifact")
        agent, metadata = placements[identifier]
        if metadata["media_type"] not in {"application/json", "text/plain"}:
            raise RuntimeError("unexpected nontext MultiHop evidence; no lossy conversion")
        request = requests.setdefault(agent, {
            "store_root": attempt["fresh_worker_stores"][agent], "namespace": ROOT.name,
            "run_id": run_id, "supports": supports, "artifacts": []})
        request["artifacts"].append(metadata)
    scanned = {}
    for agent, request in requests.items():
        values = scan_request(agent, request)
        expected = {a["artifact_id"]: a for a in request["artifacts"]}
        if len(values) != len(expected) or {v["artifact_id"] for v in values} != set(expected):
            raise RuntimeError("private scanner returned different artifact membership")
        if any(v["sha256"] != expected[v["artifact_id"]]["sha256_hex"]
               or v["size_bytes"] != expected[v["artifact_id"]]["size_bytes"] for v in values):
            raise RuntimeError("private scanner returned different artifact hash/size")
        scanned.update({v["artifact_id"]: v for v in values})
    paths = []
    for identifier, action in actions.items():
        observation = observations.get(identifier, {})
        entry = {
            "action_id": identifier, "operator": action.get("operator", "invoke_model"),
            "owner": action["owner_agent_id"], "succeeded": observation.get("succeeded"),
            "failure_code": observation.get("failure_code"),
            "is_terminal_source": identifier == terminal,
            "inputs": [{"artifact_id": a, "coverage": scanned[a]["coverage"]}
                       for a in action.get("inputs", []) if a in scanned],
            "outputs": [{"artifact_id": a["artifact_id"],
                         "coverage": scanned[a["artifact_id"]]["coverage"]}
                        for a in observation.get("produced_information", [])
                        if a["artifact_id"] in scanned],
        }
        if action.get("action_type") == "model":
            entry["prompt_literal_cues"] = coverage(
                action["prompt"].encode(), "text/plain", supports)
        paths.append(entry)
    return {
        "run_id": run_id, "support_annotation_count": len(supports),
        "unmapped_support_annotations": sum(not s["document_ids"] for s in supports),
        "private_evaluation_sha256": sha256(private_path),
        "trace_sha256": sha256(run / "trace.jsonl"),
        "result_sha256": sha256(run / "result.json"), "terminal_action_id": terminal,
        "artifact_coverage": list(scanned.values()), "action_evidence_paths": paths,
        "semantic_evidence_retention": None,
        "retention_unknown_reason": (
            "document identity/literal cues do not prove complete semantic facts"),
        "completed": result["execution_completed"],
        "audit_only_not_agent_or_cost_input": True, "model_calls": 0,
    }


def audit_phase_one(root: Path = ROOT, predecessor: Path = PREDECESSOR,
                    corpus: Path = CORPUS) -> dict[str, Any]:
    assert_inactive(root)
    snapshot = collect(root, predecessor)
    if (not snapshot["phase1_complete"] or snapshot["pending_count"]
            or snapshot["confounded_attempts"]):
        raise RuntimeError(
            "private Phase-I evidence scan requires completed resolved168-cell block")
    records = []
    for row in snapshot["rows"]:
        for attempt in row["attempts"]:
            if attempt["disposition"] != "valid":
                continue
            directory = root / "evidence" / row["condition"]["cell_id"] / (
                "attempt" + str(attempt["attempt_index"]))
            if not json.loads((directory / "worker-shutdown.json").read_text())["verified_exited"]:
                raise RuntimeError("private evidence scan requires verified Worker exits")
            # Recheck a concurrent queue restart before any body read/remote scan.
            assert_inactive(root)
            annotated = row["condition"]["task"]["family"] == "multihop_rag"
            private_source = predecessor / "preparation/task-freeze-002" / (
                "multihop_rag-" + str(row["condition"]["task"]["position"])) / (
                "private-evaluation.json")
            records.append({"cell_id": row["condition"]["cell_id"], "run_id": attempt["run_id"],
                            "benchmark_score": attempt["benchmark_score"],
                            "coverage": audit_multihop(directory, corpus, private_source)
                            if annotated else None,
                            "unannotated_retention": None,
                            "semantic_primary_cause": None,
                            "primary_cause_requires_manual_private_audit": True})
    assert_inactive(root)
    if sha256(root / "phase1-attempts.jsonl") != snapshot["journal_sha256"]:
        raise RuntimeError("private audit attempt membership changed")
    return {"version": "resident-private-evidence-paths-v1", "records": records,
            "journal_sha256": snapshot["journal_sha256"],
            "execution_freeze_sha256": snapshot["execution_freeze_sha256"],
            "collector_source_sha256": snapshot["collector_source_sha256"],
            "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "phase2_authorized": False, "semantic_audit_complete": False,
            "method_pruning_authorized": False, "planner_or_model_calls": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (sys.platform != "linux" or args.output.is_symlink()
            or args.output.resolve().parent != ROOT / "analysis"):
        raise RuntimeError("private evidence remains inside its4090 analysis namespace")
    if args.output.exists():
        raise FileExistsError("private evidence audit is append-only")
    value = audit_phase_one()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"audited_cells": len(value["records"]), "model_calls": 0,
                      "semantic_audit_complete": False, "phase2_authorized": False}))
