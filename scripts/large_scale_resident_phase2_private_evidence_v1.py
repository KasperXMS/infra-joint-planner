"""Post-block held-out private diagnostics; never an Agent or cost input.

Preserves the historical PhaseI scanner, guards and evidence semantics. Only
exact PhaseII run/store addressing changes. The formal audit entrypoint rejects
partial blocks and live controllers/atomic processes before any body scan.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from types import FunctionType
from typing import Any

import large_scale_resident_phase2_snapshot_v1 as sources
import large_scale_resident_private_evidence_v1 as private

ROOT = private.ROOT


def scan_request(agent: str, request: dict[str, Any]) -> list[dict[str, Any]]:
    private.assert_inactive(ROOT)
    if agent not in private.HOSTS:
        raise RuntimeError("held-out private scan unknown owning node")
    run_id = request["run_id"]
    expected = Path("/home/super" if agent == "strong-4090" else "/mnt/ssd") / (
        "heterogeneous-v1/artifacts") / ROOT.name / run_id / agent
    if (request["namespace"] != ROOT.name or Path(request["store_root"]) != expected
            or not run_id.startswith(ROOT.name + "-phase2-")
            or Path(run_id).name != run_id):
        raise RuntimeError("held-out private scan requires exact PhaseII run/owner store")
    host = private.HOSTS[agent]
    if host is None:
        return private.scan_store(request)
    app = Path("/mnt/ssd") / ROOT.name / "app"
    remote = [str(app / ".venv/bin/python"), "-S",
              str(app / "scripts/cost_guidance_private_multihop_audit_v1.py"), "--scan-store"]
    value = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host,
                            shlex.join(remote)], input=json.dumps(request), text=True,
                           capture_output=True, check=True, timeout=60)
    return json.loads(value.stdout)


def audit_multihop(directory: Path, corpus_path: Path, private_source: Path) -> dict[str, Any]:
    private.assert_inactive(ROOT)
    original = private.audit_multihop
    namespace = {**original.__globals__, "scan_request": scan_request}
    bound = FunctionType(original.__code__, namespace, original.__name__,
                         original.__defaults__, original.__closure__)
    value: dict[str, Any] = bound(directory, corpus_path, private_source)
    private.assert_inactive(ROOT)
    return value


def audit_phase_two(root: Path = ROOT, predecessor: Path = private.PREDECESSOR,
                    corpus: Path = private.CORPUS) -> dict[str, Any]:
    private.assert_inactive(root)
    snapshot = sources.collect(root)
    if (not snapshot["phase2_complete"] or snapshot["pending_count"]
            or snapshot["confounded_attempts"] or snapshot["operational_excluded_attempts"]):
        raise RuntimeError("private held-out scan requires completed resolved PhaseII block")
    selected: list[tuple[dict[str, Any], dict[str, Any], Path]] = []
    for row in snapshot["rows"]:
        attempts = row["attempts"]
        if len(attempts) != 1 or attempts[0]["disposition"] != "valid":
            raise RuntimeError("held-out membership needs independently reviewed original view")
        attempt = attempts[0]
        directory = root / "evidence" / row["condition"]["cell_id"] / (
            "attempt" + str(attempt["attempt_index"]))
        if (attempt["execution_sha256"] != snapshot["execution_freeze_sha256"]
                or json.loads((directory / "worker-shutdown.json").read_text()).get(
                    "verified_exited") is not True):
            raise RuntimeError("private held-out scan requires exact source and exited Workers")
        selected.append((row, attempt, directory))
    if len(selected) != snapshot["scheduled_cells"]:
        raise RuntimeError("held-out private audit membership incomplete")
    records: list[dict[str, Any]] = []
    for row, attempt, directory in selected:
        private.assert_inactive(root)
        task = row["condition"]["task"]
        annotated = task["family"] == "multihop_rag"
        private_source = predecessor / "preparation/task-freeze-002" / (
            "multihop_rag-" + str(task["position"])) / "private-evaluation.json"
        records.append({
            "cell_id": row["condition"]["cell_id"], "run_id": attempt["run_id"],
            "execution_sha256": attempt["execution_sha256"],
            "benchmark_score": attempt["benchmark_score"],
            "coverage": audit_multihop(directory, corpus, private_source) if annotated else None,
            "unannotated_retention": None, "semantic_primary_cause": None,
            "primary_cause_requires_manual_private_audit": True,
        })
    private.assert_inactive(root)
    if private.sha256(root / "phase2-attempts.jsonl") != snapshot["journal_sha256"]:
        raise RuntimeError("private held-out membership changed during audit")
    scan_source = sys.modules[private.scan_store.__module__].__file__
    if scan_source is None:
        raise RuntimeError("held-out audit requires file-backed scanner source")
    paths = (Path(__file__), Path(private.__file__), Path(sources.__file__), Path(scan_source))
    return {
        "version": "resident-phase2-private-evidence-paths-v1", "records": records,
        "journal_sha256": snapshot["journal_sha256"],
        "control_file_sha256": snapshot["control_file_sha256"],
        "execution_freeze_sha256": snapshot["execution_freeze_sha256"],
        "source_sha256": {p.name: private.sha256(p) for p in paths},
        "semantic_audit_complete": False, "planner_or_model_calls": 0,
        "artifact_bodies_exported": False, "measured_execution_modified": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (sys.platform != "linux" or args.output.is_symlink()
            or args.output.resolve().parent != ROOT / "analysis"):
        raise RuntimeError("held-out private audit remains in its remote owned namespace")
    # Fail before private reads rather than overwrite or rerun an existing audit.
    if args.output.exists():
        raise FileExistsError("held-out private evidence audit is append-only")
    value = audit_phase_two()
    sources.queue.frozen.write_new(args.output, value)
    print(json.dumps({"audited_cells": len(value["records"]), "model_calls": 0,
                      "semantic_audit_complete": False}))
