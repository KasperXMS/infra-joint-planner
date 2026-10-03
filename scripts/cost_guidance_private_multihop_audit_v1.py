"""Post-execution private coverage audit, never imported by Agent/cost execution paths.

Run on4090 after the live queue is terminal. Artifact bodies are scanned on their
owning nodes; only scalar/structural coverage receipts return to the controller.
Private supporting annotations are never passed to a Planner or inference call.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

from infra_joint.benchmarks.multihop_rag import MultiHopCorpusDocument
from infra_joint.evaluation.trace import JsonlTraceWriter


def normalize(text: str) -> str:
    return " ".join(text.casefold().split())


def coverage(content: bytes, media_type: str, supports: list[dict[str, Any]]) -> dict[str, Any]:
    """Exact document-ID coverage and literal cues, not a semantic quality oracle."""
    text = content.decode("utf-8")
    value = json.loads(text) if media_type == "application/json" else None
    rows = value if isinstance(value, list) and all(isinstance(r, dict) for r in value) else []
    ids = {r.get("document_id") for r in rows if isinstance(r.get("document_id"), str)}
    identities_complete = (isinstance(value, list)
                           and all(isinstance(r, dict)
                                   and isinstance(r.get("document_id"), str) for r in value))
    bodies = [r["body"] for r in rows if isinstance(r.get("body"), str)]
    if not rows:
        bodies = [text]
    normalized = [normalize(body) for body in bodies]
    receipts = []
    for index, support in enumerate(supports):
        known = bool(support["document_ids"])
        matched = bool(ids.intersection(support["document_ids"]))
        retained = (matched if known and (matched or identities_complete) else None)
        receipts.append({
            "support_index": index, "document_identity_known": known,
            "support_document_retained": retained,
            "exact_fact_literal_present": any(normalize(support["fact"]) in body
                                                for body in normalized),
            "literal_absence_is_semantic_absence": False,
        })
    return {"record_count": len(rows), "distinct_document_ids": len(ids),
            "coverage": receipts, "document_presence_is_complete_fact_coverage": False}


def scan_store(request: dict[str, Any]) -> list[dict[str, Any]]:
    root = Path(request["store_root"]).resolve()
    prefix = ("/home/super/heterogeneous-v1/artifacts/", "/mnt/ssd/heterogeneous-v1/artifacts/")
    if (not root.is_dir() or not str(root).startswith(prefix)
            or request["namespace"] not in root.parts):
        raise RuntimeError("private scan outside exact existing experimental store")
    result = []
    for metadata in request["artifacts"]:
        key = hashlib.sha256(metadata["artifact_id"].encode()).hexdigest()
        path = root / (key + ".blob")
        if path.is_symlink() or path.resolve().parent != root:
            raise RuntimeError("artifact scan path escaped store")
        body = path.read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        if digest != metadata["sha256_hex"] or len(body) != metadata["size_bytes"]:
            raise RuntimeError("private audit artifact hash/size mismatch")
        result.append({"artifact_id": metadata["artifact_id"], "sha256": digest,
                       "size_bytes": len(body),
                       **coverage(body, metadata["media_type"], request["supports"])})
    return result


def support_mapping(private: dict[str, Any], corpus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for evidence in private["supporting_evidence"]:
        matched = [MultiHopCorpusDocument.model_validate(row).stable_id() for row in corpus
                   if all(row.get(key) == evidence.get(key) for key in ("url", "title", "source"))]
        result.append({"document_ids": matched, "fact": evidence["fact"]})
    return result


def assert_queue_inactive(root: Path, *, proc_root: Path = Path("/proc")) -> None:
    """Do not add artifact scans/load to a still-running experimental trajectory."""
    pids = set()
    for path in root.glob("controller*.json"):
        value = json.loads(path.read_text())
        if isinstance(value.get("pid"), int):
            pids.add(value["pid"])
    journal = root / "queue.jsonl"
    if journal.exists():
        for line in journal.open():
            record = json.loads(line)
            if isinstance(record.get("pid"), int):
                pids.add(record["pid"])
    for pid in pids:
        command = proc_root / str(pid) / "cmdline"
        if command.exists() and root.name.encode() in command.read_bytes():
            raise RuntimeError("private artifact audit requires inactive experimental controllers")


def audit_cell(directory: Path, root: Path, corpus_path: Path) -> dict[str, Any]:
    private_path = directory / "private/private-evaluation.json"
    private = json.loads(private_path.read_text(encoding="utf-8"))
    freeze = json.loads((directory / "freeze/manifest.json").read_text())
    expected = freeze["source_manifest"]["multihop_corpus"]["sha256"]
    if hashlib.sha256(corpus_path.read_bytes()).hexdigest() != expected:
        raise RuntimeError("private corpus source drift")
    supports = support_mapping(private, json.loads(corpus_path.read_text(encoding="utf-8")))
    run_id = freeze["run_id"]
    run = directory / "runs" / run_id
    result = json.loads((run / "result.json").read_text())
    events = JsonlTraceWriter(run / "trace.jsonl").read_all()
    states = json.loads((directory / "private/worker-state-after.json").read_text())
    import yaml

    config = yaml.safe_load((root / "cell-configs" / (directory.name + ".yaml")).read_text())
    from run_predecision_matrix_v1 import HOSTS

    from_by_id = {}
    for agent, state in states.items():
        for metadata in state["artifacts"]:
            from_by_id.setdefault(metadata["artifact_id"], (agent, metadata))
    actions = {e["payload"]["action"]["action_id"]: e["payload"]["action"] for e in events
               if e["event_type"] == "logical.action.prepared"}
    observations = {e["payload"]["action_id"]: e["payload"] for e in events
                    if e["event_type"] == "logical.observation"}
    terminal = next((e["payload"]["terminal_action_id"] for e in reversed(events)
                     if e["event_type"] == "logical.loop.end"), None)
    wanted = set()
    for action_id, action in actions.items():
        observation = observations.get(action_id)
        if observation and observation["succeeded"]:
            wanted.update(action.get("inputs", []))
            wanted.update(a["artifact_id"] for a in observation.get("produced_information", []))
    requests: dict[str, dict[str, Any]] = {}
    for artifact_id in sorted(wanted):
        agent, metadata = from_by_id[artifact_id]
        request = requests.setdefault(agent, {"store_root": config["fresh_worker_stores"][agent],
                                              "namespace": root.name, "supports": supports,
                                              "artifacts": []})
        request["artifacts"].append(metadata)
    scanned = {}
    for agent, request in requests.items():
        host = HOSTS[agent]
        if host is None:
            receipts = scan_store(request)
        else:
            app = Path("/mnt/ssd") / root.name / "app"
            remote = [str(app / ".venv/bin/python"),
                      str(app / "scripts" / Path(__file__).name), "--scan-store"]
            command = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host,
                       shlex.join(remote)]
            receipt = subprocess.run(command, input=json.dumps(request), text=True,
                                     capture_output=True, check=True, timeout=60)
            receipts = json.loads(receipt.stdout)
        scanned.update({r["artifact_id"]: r for r in receipts})
    paths = []
    for action_id, action in actions.items():
        observation = observations.get(action_id, {})
        entry = {"action_id": action_id, "operator": action.get("operator", "invoke_model"),
                 "owner": action["owner_agent_id"], "succeeded": observation.get("succeeded"),
                 "failure_code": observation.get("failure_code"),
                 "inputs": [{"artifact_id": a, "coverage": scanned[a]["coverage"]}
                            for a in action.get("inputs", []) if a in scanned],
                 "outputs": [{"artifact_id": a["artifact_id"],
                              "coverage": scanned[a["artifact_id"]]["coverage"]}
                             for a in observation.get("produced_information", [])
                             if a["artifact_id"] in scanned],
                 "is_terminal_source": action_id == terminal}
        if action.get("action_type") == "model":
            entry["prompt_literal_cues"] = coverage(
                action["prompt"].encode(), "text/plain", supports,
            )
        paths.append(entry)
    return {"run_id": run_id, "audit_only_not_agent_or_cost_input": True,
            "support_annotation_count": len(supports), "task_source_sha256": expected,
            "private_evaluation_sha256": hashlib.sha256(private_path.read_bytes()).hexdigest(),
            "trace_sha256": hashlib.sha256((run / "trace.jsonl").read_bytes()).hexdigest(),
            "result_sha256": hashlib.sha256((run / "result.json").read_bytes()).hexdigest(),
            "completed": result["execution_completed"],
            "original_evaluator_score": (result["evaluation"]["benchmark_score"]
                                         if result.get("evaluation") else None),
            "terminal_action_id": terminal, "artifact_coverage": list(scanned.values()),
            "action_evidence_paths": paths}


def main(args: argparse.Namespace) -> None:
    if args.scan_store:
        print(json.dumps(scan_store(json.load(sys.stdin))))
        return
    from cost_guidance_exploration_v1 import ensure_remote

    root = args.deployment_root.resolve()
    ensure_remote(root)
    assert_queue_inactive(root)
    if args.output.exists():
        raise FileExistsError("private analysis is append-only")
    value = audit_cell(args.cell, root, args.corpus)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"run_id": value["run_id"],
                      "audited_artifacts": len(value["artifact_coverage"]),
                      "support_count": value["support_annotation_count"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-store", action="store_true")
    parser.add_argument("--deployment-root", type=Path)
    parser.add_argument("--cell", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--corpus", type=Path, default=Path(
        "/home/super/xiaoming/blind_baseline_6task_v1/data/corpus.json"))
    main(parser.parse_args())
