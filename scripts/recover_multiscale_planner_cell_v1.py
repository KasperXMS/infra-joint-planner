"""Append reporting for the completed third cell; never rerun inference or tasks.

Run outside the frozen app with its original virtual environment. Full residency
snapshots and the original stop marker remain immutable. Only the GPU process-set
comparison is scoped to the four calibrated CUDA runner PIDs; every original
server/runner/target, log-prefix, reload, OOM, and truncation check remains active.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path("/home/super/xiaoming/multiscale-planner-evaluation-v1/run-001")
CELL_ID = "qwen35-4b-t5-plain"
CORE_CUDA_PIDS = frozenset({3763, 3764, 1130531, 1130540})
USER_AUTHORIZATION = (
    "Continue the authorized experiment with recorded external GPU contention; "
    "unrelated foreign processes are not ours and must never be paused or stopped."
)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scoped_snapshot(snapshot: dict) -> dict:
    """Return a copy; never redact or rewrite the saved full snapshot."""
    value = copy.deepcopy(snapshot)
    processes = value.get("gpu_compute_processes")
    if processes is not None:
        value["gpu_compute_processes"] = [
            row for row in processes if int(row["pid"]) in CORE_CUDA_PIDS
        ]
    return value


def gpu_change(before: dict, after: dict) -> dict:
    """Numeric process-set changes only; no command lines or private paths."""
    old = {(row["gpu_uuid"], int(row["pid"])) for row in before.get("gpu_compute_processes") or []}
    new = {(row["gpu_uuid"], int(row["pid"])) for row in after.get("gpu_compute_processes") or []}
    added = sorted(pid for _, pid in new - old if pid not in CORE_CUDA_PIDS)
    removed = sorted(pid for _, pid in old - new if pid not in CORE_CUDA_PIDS)
    return {
        "added_noncore_process_count": len(added),
        "removed_noncore_process_count": len(removed),
        "added_noncore_pids": added,
        "removed_noncore_pids": removed,
        "core_gpu_process_set_unchanged": {pair for pair in old if pair[1] in CORE_CUDA_PIDS}
        == {pair for pair in new if pair[1] in CORE_CUDA_PIDS},
        "external_processes_paused_stopped_or_modified": False,
    }


def main() -> None:
    assert sys.platform == "linux", "This helper reads original experiment-host evidence only"
    app = ROOT / "app"
    assert not Path(__file__).resolve().is_relative_to(app), "Keep the frozen app unchanged"
    sys.path[:0] = [str(app / "scripts"), str(app / "src")]
    import multiscale_planner_evaluation_v1 as driver

    driver.configure()
    pilot = driver.pilot
    assert driver.ROOT == ROOT and app == pilot.APP
    out = ROOT / "cells" / CELL_ID
    amendment_path = ROOT / "reporting-amendment.json"
    result_path = out / "sanitized-result.json"
    assert not amendment_path.exists(), "Recovery is append-only and may run once"
    assert not result_path.exists(), "Never overwrite an existing sanitized result"
    assert not (ROOT / "matrix-complete.json").exists()
    stopped_path = ROOT / "matrix-stopped.json"
    stopped = read(stopped_path)
    assert (
        stopped.get("type") == "CalledProcessError"
        and "audit_log_interval" in stopped.get("message", "")
        and stopped.get("completed_cells") == 2
    ), (
        "Only the documented third-cell GPU process-set stop is eligible"
    )
    freeze_path = ROOT / "execution-freeze.json"
    freeze = read(freeze_path)
    assert all(sha(app / path) == value for path, value in freeze["source_sha256"].items())
    assert pilot.protected_hashes() == freeze["protected_sha256"]

    protocol = read(app / "configs/experiments/lightweight-planner-competence-v1.json")
    starts = [
        item["cell"]
        for item in map(json.loads, (ROOT / "journal.jsonl").read_text().splitlines())
        if item.get("event") == "cell_started"
        and isinstance(item.get("cell"), dict)
        and item["cell"].get("cell_id") == CELL_ID
    ]
    assert len(starts) == 1, "The original cell must have exactly one recorded attempt"
    cell = starts[0]
    assert cell["candidate"] == "qwen35-4b" and cell["task_index"] == 5
    assert cell["group"] == "B1" and cell["skills"] is False
    expected = protocol["tasks"][4]
    assert all(cell[key] == expected[key] for key in ("family", "position"))
    config = pilot.frozen._yaml(ROOT / "cell-configs" / (CELL_ID + ".yaml"))
    raw_path = out / "runs" / config["run_id"] / "result.json"
    raw = read(raw_path)
    assert raw["execution_completed"] and raw["evaluation"]["benchmark_score"] == 1
    cleanup = read(out / "worker-shutdown.json")
    assert cleanup["drained"] and cleanup["verified_exited"] and not cleanup["errors"]
    tc = read(out / "tc-attestation.json")
    assert not tc["cleanup_error"] and tc["original_qdisc"] == tc["restored_qdisc"]

    snapshot_paths = [out / "private" / f"residency-{name}.json" for name in ("before", "after")]
    immutable_paths = [stopped_path, freeze_path, raw_path, *snapshot_paths]
    original_hashes = {str(path): sha(path) for path in immutable_paths}
    before, after = map(read, snapshot_paths)
    assert before.keys() == after.keys()
    changes = {}
    audit_hashes = {}
    for node in before:
        changes[node] = gpu_change(before[node], after[node])
        assert changes[node]["core_gpu_process_set_unchanged"], "Calibrated GPU runner set drift"
        scoped_before, scoped_after = scoped_snapshot(before[node]), scoped_snapshot(after[node])
        code = "import json; from resident_model_pool_attestation_v1 import audit_log_interval; "
        code += f"print(json.dumps(audit_log_interval({scoped_before!r},{scoped_after!r})))"
        audit = pilot.node_json(node, code)
        assert audit["passed"] and audit["model_calls"] == 0
        assert all(
            not pilot.truncation_events(value["text"]) for value in audit["intervals"].values()
        )
        audit_path = out / "private/residency-log-intervals" / (node + ".json")
        if audit_path.exists():
            original_audit = read(audit_path)
            assert original_audit["passed"] and original_audit["model_calls"] == 0
            assert all(
                not pilot.truncation_events(value["text"])
                for value in original_audit["intervals"].values()
            )
        else:
            pilot.write_new(audit_path, audit)
        audit_hashes[node] = sha(audit_path)
    assert sum(value["added_noncore_process_count"] for value in changes.values()) > 0

    # The failed old postprocessor did not save its Planner log start offset.
    # Preserve uncertainty outside the analyzer's *planner*log*interval*.json glob:
    # creating an empty interval would incorrectly report observed zero work.
    planner_log = ROOT / "planner-server.log"
    planner_unknown = {
        "observed": False,
        "known_model_service_ms": None,
        "runner_task_starts": None,
        "reason": (
            "Original third-cell Planner log start offset was not persisted "
            "before postprocessing stopped."
        ),
        "full_log_current_sha256": sha(planner_log) if planner_log.exists() else None,
        "full_log_current_bytes": planner_log.stat().st_size if planner_log.exists() else None,
        "whole_log_attributed_to_cell": False,
    }
    pilot.write_new(out / "private/planner-service-unobserved.json", planner_unknown)
    row = pilot.inspect_cell(cell, out, config, cleanup, freeze["protected_sha256"])
    assert not row["system_problems"], "All other original safety checks must pass"
    row["external_gpu_contention"] = {
        "process_set_changed_during_cell": True,
        "added_noncore_process_count": sum(
            v["added_noncore_process_count"] for v in changes.values()
        ),
        "removed_noncore_process_count": sum(
            v["removed_noncore_process_count"] for v in changes.values()
        ),
        "core_executor_identity_unchanged": True,
        "user_authorized_contended_continuation": True,
        "resource_timing_comparison_caution": True,
        "foreign_process_mutations": 0,
    }
    row["independent_planner_service_work"] = {
        "observed": False,
        "known_model_service_ms": None,
        "runner_task_starts": None,
    }
    row["reporting_recovery"] = {
        "original_stop_retained": True,
        "task_attempts": 1,
        "model_reruns": 0,
        "inference_requests": 0,
        "score_retained": 1,
        "unplanned_external_contention_flagged": True,
    }
    assert original_hashes == {str(path): sha(path) for path in immutable_paths}
    assert pilot.protected_hashes() == freeze["protected_sha256"]
    pilot.write_new(result_path, row)
    amendment = {
        "schema_version": 1,
        "utc": datetime.now(UTC).isoformat(),
        "cell_id": CELL_ID,
        "authorization": USER_AUTHORIZATION,
        "original_stop_retained": True,
        "original_stop_sha256": original_hashes[str(stopped_path)],
        "original_raw_result_sha256": original_hashes[str(raw_path)],
        "raw_execution_completed": True,
        "original_benchmark_score": 1,
        "task_reruns": 0,
        "model_inference_requests": 0,
        "postprocessing_only": True,
        "core_cuda_pid_allowlist": sorted(CORE_CUDA_PIDS),
        "gpu_comparison_change": (
            "Filter copied GPU process lists to calibrated core PIDs only; "
            "retain all full snapshots."
        ),
        "all_other_residency_log_oom_truncation_checks_retained": True,
        "external_gpu_changes": changes,
        "worker_cleanup_verified": True,
        "network_restored": True,
        "protected_history_unchanged": True,
        "independent_planner_service_work": planner_unknown,
        "helper_source_sha256": sha(Path(__file__)),
        "original_residency_helper_source_sha256": sha(
            app / "scripts/resident_model_pool_attestation_v1.py"
        ),
        "audit_files_sha256": audit_hashes,
        "immutable_original_files_sha256": original_hashes,
        "sanitized_result_sha256": sha(result_path),
        "semantic_prompt_skills_evaluator_scheduler_executor_changed": False,
    }
    pilot.write_new(amendment_path, amendment)
    print(
        json.dumps(
            {
                "cell_id": CELL_ID,
                "completed": True,
                "score": 1,
                "model_reruns": 0,
                "external_contention_recorded": True,
                "system_problems": row["system_problems"],
            }
        )
    )


if __name__ == "__main__":
    main()
