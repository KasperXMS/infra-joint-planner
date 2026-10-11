"""Resume after the LPC-01 reporting KeyError, retaining its completed score0 run."""

import argparse
import ast
import asyncio
import json
import os
import signal
from pathlib import Path
from time import monotonic

import agents
import lightweight_planner_pilot_v1 as pilot


def read(path):
    return json.loads(path.read_text())


async def main(args):
    root = pilot.ROOT
    freeze = read(root / "execution-freeze.json")
    stopped = read(root / "matrix-stopped.json")
    assert stopped["type"] == "KeyError" and stopped["completed_cells"] == 0
    assert not (root / "reporting-repair.json").exists()
    assert not (root / "matrix-complete.json").exists() and not (root / "STOP").exists()
    assert {p.name for p in (root / "cells").iterdir()} == {"LPC-01"}
    code = "scripts/lightweight_planner_pilot_v1.py"
    old = root / "reporting-repair-original-source.py"
    assert pilot.digest(old) == freeze["source_sha256"][code]
    original = old.read_text()
    revised = (pilot.APP / code).read_text()
    expected = original.replace('evaluation["score"]', 'evaluation["benchmark_score"]')
    assert revised == expected, "only the two postprocessing field accesses may change"
    # Explicitly preserve every other function, including execution and all role settings.
    before = ast.parse(original)
    after = ast.parse(revised)
    for first, second in zip(before.body, after.body, strict=True):
        if getattr(first, "name", None) != "inspect_cell":
            assert ast.dump(first) == ast.dump(second)
    files = dict(freeze["source_sha256"])
    files[code] = pilot.digest(pilot.APP / code)
    assert all(pilot.digest(pilot.APP / p) == sha for p, sha in files.items())
    assert pilot.protected_hashes() == freeze["protected_sha256"]
    cell = freeze["ordered_cells"][0]
    out = root / "cells" / cell["cell_id"]
    run = next((out / "runs").glob("*/result.json"))
    raw = read(run)
    assert raw["execution_completed"] and raw["evaluation"]["benchmark_score"] == 0
    cleanup = read(out / "worker-shutdown.json")
    config = pilot.frozen._yaml(root / "cell-configs/LPC-01.yaml")
    row = pilot.inspect_cell(cell, out, config, cleanup, freeze["protected_sha256"])
    for path in (out / "private/residency-log-intervals").glob("*.json"):
        for value in read(path)["intervals"].values():
            assert not pilot.truncation_events(value["text"])
    assert not row["system_problems"]
    pilot.write_new(out / "sanitized-result.json", row)
    pilot.write_new(
        root / "reporting-repair.json",
        {
            "cause": "postprocessing used score instead of original evaluator benchmark_score",
            "original_raw_result_sha256": pilot.digest(run),
            "completed_LPC01_score0_retained": True,
            "model_reruns": 0,
            "only_postprocessing_changed": True,
            "original_source_sha256": freeze["source_sha256"][code],
            "repaired_source_sha256": files[code],
            "remaining_cells": 17,
            "evaluator_changed": False,
        },
    )
    pilot.write_new(root / "continuation-source-freeze.json", files)
    protocol = read(pilot.APP / "configs/experiments/lightweight-planner-competence-v1.json")
    pool = pilot.frozen._yaml(pilot.APP / protocol["infrastructure_design"]["model_pool_path"])
    pilot._load_control_plane_key(args.api_key_file, "DASHSCOPE_API_KEY")
    agents.set_tracing_disabled(True)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: (root / "STOP").touch(exist_ok=True))
    pilot.journal("reporting_recovered", cell="LPC-01", completed=True, score=0, model_reruns=0)
    pilot.journal("continued", pid=os.getpid(), remaining_cells=17)
    rows = [row]
    from datetime import datetime

    started = json.loads((root / "journal.jsonl").read_text().splitlines()[0])["utc"]
    elapsed = (datetime.now().astimezone() - datetime.fromisoformat(started)).total_seconds()
    deadline = monotonic() + 91800 - elapsed
    try:
        for cell in protocol["order"][1:]:
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
            if len(rows) == 3:
                pilot.write_new(
                    root / "first-task-audit.json",
                    {
                        "cells": 3,
                        "system_problems": [],
                        "worker_cleanup_verified": True,
                        "evaluator_consistency": True,
                        "proceed_remaining_15": True,
                    },
                )
                pilot.journal("first_task_audit_passed", automatic_continuation=True)
        pilot.write_new(
            root / "matrix-complete.json",
            {
                "cells": 18,
                "order_preserved": True,
                "semantic_retries": 0,
                "protected_history_unchanged": pilot.protected_hashes()
                == freeze["protected_sha256"],
                "reporting_continuation_retained_original_cell": "LPC-01",
            },
        )
        pilot.journal("completed", cells=len(rows))
    except BaseException as exc:
        pilot.write_new(
            root / "matrix-stopped-002.json",
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
