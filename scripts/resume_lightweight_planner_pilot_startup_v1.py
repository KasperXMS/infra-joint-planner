"""Continue LPC-15..18 after a zero-model Worker initialization failure."""

import argparse
import ast
import asyncio
import json
import os
import signal
from datetime import datetime
from pathlib import Path
from time import monotonic

import agents
import lightweight_planner_pilot_v1 as pilot


def read(path):
    return json.loads(path.read_text())


async def main(args):
    root = pilot.ROOT
    freeze = read(root / "execution-freeze.json")
    files = read(root / "continuation-source-freeze.json")
    assert read(root / "matrix-stopped-002.json")["completed_cells"] == 14
    assert not (root / "STOP").exists() and not (root / "matrix-complete.json").exists()
    assert not (root / "startup-repair.json").exists()
    code = "scripts/lightweight_planner_pilot_v1.py"
    old = root / "worker-startup-repair-original-source.py"
    assert pilot.digest(old) == files[code]
    before, after = ast.parse(old.read_text()), ast.parse((pilot.APP / code).read_text())
    for first, second in zip(before.body, after.body, strict=True):
        if getattr(first, "name", None) != "start_owned_worker":
            assert ast.dump(first) == ast.dump(second)
    files[code] = pilot.digest(pilot.APP / code)
    assert all(pilot.digest(pilot.APP / p) == sha for p, sha in files.items())
    assert pilot.protected_hashes() == freeze["protected_sha256"]
    rows = [
        read(root / "cells" / c["cell_id"] / "sanitized-result.json")
        for c in freeze["ordered_cells"][:14]
    ]
    assert all(not row["system_problems"] for row in rows)
    out = root / "cells/LPC-15"
    assert not (out / "runs").exists() and not (out / "attempt-freeze.json").exists()
    assert not list(out.rglob("*-usage.json"))
    cleanup = read(out / "worker-shutdown.json")
    assert cleanup["owned_processes"] == {} and cleanup["verified_exited"]
    tc = read(out / "tc-attestation.json")
    assert tc["cleanup_error"] is None and tc["original_qdisc"] == tc["restored_qdisc"]
    saved = root / "initialization-failures/LPC-15-001"
    saved.parent.mkdir(exist_ok=True)
    assert out.resolve().is_relative_to(root.resolve())
    assert saved.resolve().is_relative_to(root.resolve()) and not saved.exists()
    out.rename(saved)
    (root / "cell-configs/LPC-15.yaml").rename(saved / "cell-config.yaml")
    (root / "worker-configs/lightweight-planner-competence-v1-formal-003-LPC-15-A4.yaml").rename(
        saved / "worker-A4.yaml"
    )
    pilot.write_new(
        root / "startup-repair.json",
        {
            "cell": "LPC-15",
            "model_requests_before_repair": 0,
            "task_started": False,
            "owned_workers_spawned": 0,
            "network_restored": True,
            "cause": (
                "transient Worker port bind failure before launch; follow-up plain bind succeeded"
            ),
            "time_wait_cause_inferred_not_captured": True,
            "fix": (
                "port availability socket uses SO_REUSEADDR, matching the existing Worker server"
            ),
            "model_reruns": 0,
            "completed_cells_retained": 14,
            "original_source_sha256": pilot.digest(old),
            "repaired_source_sha256": files[code],
            "only_worker_startup_changed": True,
        },
    )
    pilot.write_new(root / "startup-continuation-source-freeze.json", files)
    protocol = read(pilot.APP / "configs/experiments/lightweight-planner-competence-v1.json")
    pool = pilot.frozen._yaml(pilot.APP / protocol["infrastructure_design"]["model_pool_path"])
    pilot._load_control_plane_key(args.api_key_file, "DASHSCOPE_API_KEY")
    agents.set_tracing_disabled(True)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: (root / "STOP").touch(exist_ok=True))
    pilot.journal("worker_startup_recovered", cell="LPC-15", model_reruns=0)
    pilot.journal("continued", pid=os.getpid(), remaining_cells=4)
    started = json.loads((root / "journal.jsonl").read_text().splitlines()[0])["utc"]
    elapsed = (datetime.now().astimezone() - datetime.fromisoformat(started)).total_seconds()
    deadline = monotonic() + 91800 - elapsed
    try:
        for cell in protocol["order"][14:]:
            if (root / "STOP").exists() or monotonic() >= deadline:
                raise RuntimeError("administrative matrix stop/deadline")
            assert pilot.protected_hashes() == freeze["protected_sha256"]
            assert all(pilot.digest(pilot.APP / p) == sha for p, sha in files.items())
            pilot.journal("cell_started", cell=cell)
            row = await asyncio.wait_for(
                pilot.one_cell(cell, protocol, pool, freeze["protected_sha256"]), timeout=5100
            )
            rows.append(row)
            pilot.journal(
                "cell_finished",
                cell=cell["cell_id"],
                completed=row["completed"],
                score=row["original_evaluation"],
                schema_failures=row["schema_failures"],
                system_problems=row["system_problems"],
            )
            if row["system_problems"]:
                raise RuntimeError("system failure: " + ",".join(row["system_problems"]))
        pilot.write_new(
            root / "matrix-complete.json",
            {
                "cells": 18,
                "order_preserved": True,
                "semantic_retries": 0,
                "protected_history_unchanged": pilot.protected_hashes()
                == freeze["protected_sha256"],
                "reporting_continuation_retained_original_cell": "LPC-01",
                "zero_model_worker_initialization_repair": "LPC-15",
            },
        )
        pilot.journal("completed", cells=len(rows))
    except BaseException as exc:
        pilot.write_new(
            root / "matrix-stopped-003.json",
            {
                "type": type(exc).__name__,
                "message": str(exc),
                "completed_cells": len(rows),
                "historical_phase2_resumed": False,
            },
        )
        pilot.journal("stopped", exception=type(exc).__name__, completed_cells=len(rows))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key-file", type=Path, required=True)
    asyncio.run(main(parser.parse_args()))
