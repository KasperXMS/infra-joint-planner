"""New resident-pool block over the same native runtime, methods and substrate.

No historical root/global patching, semantic repair or outcome-based resampling.
This controller only binds a new physical environment, stores and provenance.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from large_scale_admission_v1 import admit
from large_scale_execution_v1 import (
    RESIDENT_ROOT,
    TASK_FREEZE_SHA256,
    ResidentBlock,
    cell_config,
    execute_once,
    frozen,
)
from large_scale_execution_v1 import (
    ROOT as PREDECESSOR,
)
from large_scale_queue_v1 import (
    HISTORY,
    RULES,
    fallback_failure,
    schedule,
    worker_states,
)
from large_scale_repair_freeze_v1 import environment_fingerprint, verified_prices
from predecision_crossbenchmark_v1 import audit_artifact_persistence
from prepare_resident_worker_v1 import worker_config
from resident_model_pool_attestation_v1 import compare_residency, sha256
from run_predecision_matrix_v1 import HOSTS, remote_python, start_worker, stop_worker, write_new
from run_sdk_native_infra_cell_with_tc_v1_3 import DEFAULT_ENDPOINTS
from run_sdk_native_infra_cell_with_tc_v1_3 import run as run_shaped

from infra_joint.control.capabilities import (
    StaticCapabilityContract,
    build_static_capability_contract,
)
from infra_joint.control.provenance import provenance_sha256
from infra_joint.core.state import EnvironmentSpec
from infra_joint.experiments.attempt_ledger import AttemptLedger, QueueLease
from infra_joint.experiments.large_scale_protocol import GLOBAL_CAP, schedule_sha256
from infra_joint.operators.catalog import build_operator_catalog

ROOT = RESIDENT_ROOT
BLOCK = ResidentBlock()
APP = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "execution-freeze-001.json"
OLD_JOURNAL_SHA256 = "bddc83d7ef5230d3aca3c440602cea25bfd8be34bea6ceba47c3ce8746c0fb86"
PRIOR_SUBSTANTIVE_CELLS = 42
POOL_CONFIG = APP / BLOCK.environment_config
HARNESS = APP / BLOCK.harness_manifest


def require_remote() -> None:
    BLOCK.validate(ROOT)
    if APP.resolve() != (ROOT / "app").resolve():
        raise RuntimeError("resident controller must use its own explicitly frozen app")
    frozen.validate_runtime_import_root()


def reference() -> dict[str, Any]:
    pool = frozen._yaml(POOL_CONFIG)
    return {**frozen.protocol(), "worker_urls": pool["worker_urls"],
            "environment_config": BLOCK.environment_config,
            "harness_manifest": BLOCK.harness_manifest}


def remote_json(agent: str, code: str) -> dict[str, Any]:
    # Code and metadata only; all model/dataset payloads remain on remote nodes.
    app = APP if HOSTS[agent] is None else Path("/mnt/ssd") / ROOT.name / "app"
    payload = "import sys; sys.path.insert(0," + repr(str(app / "scripts")) + "); " + code
    if HOSTS[agent] is None:
        output = subprocess.run([sys.executable, "-c", payload], check=True,
                                capture_output=True, text=True, timeout=60).stdout
    else:
        output = remote_python(HOSTS[agent], payload)
    return json.loads(output)


def residency() -> dict[str, Any]:
    return {agent: remote_json(agent,
            "import json; from resident_model_pool_attestation_v1 import node_attestation; "
            f"print(json.dumps(node_attestation({agent!r})))") for agent in HOSTS}


def calibration_receipts() -> dict[str, Any]:
    expected = frozen._yaml(POOL_CONFIG)["calibration_receipts"]
    result = {}
    for agent in HOSTS:
        pool = ("/home/super/xiaoming/resident-model-pool-v1" if HOSTS[agent] is None
                else "/mnt/ssd/resident-model-pool-v1")
        code = (
            "import json,hashlib; from pathlib import Path; "
            f"root=Path({pool!r}); rows={{}}; "
            "\nfor kind,folder in [('core','core-audit-001'),('boundary','boundary-audit-001')]:"
            "\n p=root/'calibration'/folder/'receipt.json'; v=json.loads(p.read_text());"
            "\n assert v['passed'] and v['benchmark_cells']==0 and v['planner_calls']==0;"
            "\n rows[kind]=hashlib.sha256(p.read_bytes()).hexdigest()"
            "\nprint(json.dumps(rows))"
        )
        result[agent] = remote_json(agent, code)
        if result[agent] != expected[agent]:
            raise RuntimeError("calibrated actual deployment receipt drift")
    return result


def validate_harness_delta(parent: dict[str, Any], current: dict[str, Any]) -> None:
    expected = deepcopy(parent)
    expected["anonymous_model_contract"]["image_token_cost"] = 4096
    expected["static_capability_contract_sha256"] = (
        "1064a5e3446a1dbf0c99360751cc5e9604efa30cad9c548b650ac13d6963a4c0")
    if current != expected:
        raise RuntimeError("resident restart cannot tune semantic harness/models/tools/budgets")


def execution_freeze() -> dict[str, Any]:
    require_remote()
    if sha256(PREDECESSOR / "phase1-attempts.jsonl") != OLD_JOURNAL_SHA256:
        raise RuntimeError("predecessor evidence changed or its old queue resumed")
    validate_harness_delta(frozen._yaml(APP / "configs/experiments/"
                                       "infra-aware-predecision-v1-transport-receipts-patch2.yaml"),
                           frozen._yaml(HARNESS))
    old_app = PREDECESSOR / "app-execution-fa19e0b"
    old_sources = {str(p.relative_to(old_app)): sha256(p)
                   for p in (old_app / "src").rglob("*.py")}
    new_sources = {str(p.relative_to(APP)): sha256(p) for p in (APP / "src").rglob("*.py")}
    allowed = "src/infra_joint/experiments/large_scale_protocol.py"
    if ({p: h for p, h in old_sources.items() if p != allowed}
            != {p: h for p, h in new_sources.items() if p != allowed}):
        raise RuntimeError("resident restart changed the frozen physical/logical/method substrate")
    cells = schedule()  # Same frozen18 tasks/seed/condition order, different run/store IDs.
    if PRIOR_SUBSTANTIVE_CELLS + len(cells) > GLOBAL_CAP:
        raise RuntimeError("cumulative substantive budget exceeded")
    selection = PREDECESSOR / "preparation/task-freeze-002"
    manifest = json.loads((selection / "manifest.json").read_text())
    if sha256(selection / "manifest.json") != TASK_FREEZE_SHA256:
        raise RuntimeError("original task selection drift")
    _, pricing_sha = verified_prices(PREDECESSOR, APP)
    for path, digest in ((HISTORY / "cost-history.json", frozen.HISTORY_SHA256),
                         (HISTORY / "manifest.json", frozen.HISTORY_MANIFEST_SHA256),
                         (RULES, manifest["e_rules_manifest_sha256"])):
        if sha256(path) != digest:
            raise RuntimeError("shared pricing/history/rules freeze drift")
    ready = ROOT / "readiness/worker-surface-001"
    validation = json.loads((ready / "validation.json").read_text())
    shutdown = json.loads((ready / "shutdown-verified.json").read_text())
    if (not validation["passed"] or validation["workers"] != 4
            or validation["deployments"] != 5 or not shutdown["passed"]
            or not shutdown["old_journal_unchanged"]):
        raise RuntimeError("fresh Worker readiness proof is incomplete")
    environment = EnvironmentSpec.model_validate(frozen._yaml(POOL_CONFIG)["environment"])
    base = frozen.base_config(reference())
    operations = frozen._operations(base)
    capabilities = build_static_capability_contract(
        environment, build_operator_catalog(), operations)
    harness = frozen.load_harness(HARNESS)
    frozen.validate_harness(harness, environment, capabilities, operations)
    ready_capability = StaticCapabilityContract.model_validate_json(
        (ready / "static-capability.json").read_text())
    if frozen._capability_sha256(capabilities) != frozen._capability_sha256(ready_capability):
        raise RuntimeError("new actual Workers and shared static contract disagree")
    paths = [p for folder in ("src", "scripts", "configs") for p in (APP / folder).rglob("*")
             if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]
    return {"version": "large-scale-resident-execution-v1", "commit_sha": frozen._revision(),
            "source_sha256": {str(p.relative_to(APP)): sha256(p) for p in sorted(paths)},
            "task_selection_sha256": TASK_FREEZE_SHA256,
            "phase1_schedule_sha256": schedule_sha256(cells),
            "schedule_seed": manifest["schedule_seed"],
            "ordered_run_ids": [f"{ROOT.name}-{c.cell_id}-attempt1" for c in cells],
            "Phase_I_cells": len(cells), "predecessor_substantive_cells": PRIOR_SUBSTANTIVE_CELLS,
            "global_cap": GLOBAL_CAP, "maximum_complete_phase2_methods": 4,
            "old_journal_sha256": OLD_JOURNAL_SHA256,
            "pricing_sha256": pricing_sha, "history_sha256": frozen.HISTORY_SHA256,
            "history_manifest_sha256": frozen.HISTORY_MANIFEST_SHA256,
            "profile_matching": "unchanged exact execution-surface match; otherwise unknown",
            "old_27b_profile_reassigned_to_smaller_models": False,
            "rules_sha256": manifest["e_rules_manifest_sha256"],
            "calibration_receipts": calibration_receipts(),
            "readiness_sha256": {name: sha256(ready / name) for name in (
                "worker-states.json", "static-capability.json", "validation.json",
                "shutdown-verified.json")},
            "decoder": environment_fingerprint(PREDECESSOR),
            "harness_manifest_sha256": sha256(HARNESS),
            "capability_sha256": frozen._capability_sha256(capabilities),
            "semantic_tuning": False, "new_routing_method": False,
            "preserved_substrate_source_sha256": {
                p: h for p, h in old_sources.items() if p != allowed},
            "residency_required_before_and_after_every_cell": True}


def verify_freeze() -> str:
    saved = json.loads(FREEZE.read_text())
    if saved != execution_freeze():
        raise RuntimeError("new physical block/source/harness freeze drift")
    return provenance_sha256(saved)


async def with_workers(args: argparse.Namespace) -> None:
    config = frozen._yaml(args.config)
    pool = frozen._yaml(POOL_CONFIG)
    pids: dict[str, int] = {}
    before = residency()
    write_new(args.output / "private/residency-before.json", before)
    try:
        for agent in HOSTS:
            source = APP / "configs/experiments/workers/blind-3family-video-v1.3" / (
                f"worker-{agent.lower()}.yaml")
            worker = worker_config(pool, frozen._yaml(source), agent,
                                   Path(config["fresh_worker_stores"][agent]))
            path = ROOT / "worker-configs" / f"{config['run_id']}-{agent}.yaml"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as stream:
                yaml.safe_dump(worker.model_dump(mode="json"), stream, sort_keys=False)
            pids[agent] = start_worker(ROOT, path, agent, config["fresh_worker_stores"][agent])
            write_new(args.output / "worker-starts" / (agent + ".json"), {"pid": pids[agent]})
        write_new(args.output / "worker-pids.json", pids)
        write_new(args.output / "private/worker-state-before.json",
                  await worker_states(config, clean=True))
        try:
            await execute_once(args, block=BLOCK)
        finally:
            write_new(args.output / "private/worker-state-after.json",
                      await worker_states(config, clean=False))
        if (args.output / "runs" / config["run_id"] / "result.json").exists():
            write_new(args.output / "private/artifact-persistence.json",
                      audit_artifact_persistence(args.output, config["run_id"]))
    finally:
        errors, exited = [], {}
        for agent, pid in pids.items():
            try:
                stop_worker(ROOT, agent, pid)
                for _ in range(30):
                    code = ("from pathlib import Path; "
                            f"p=Path('/proc/{pid}/cmdline'); "
                            "v=p.read_bytes().decode() if p.exists() else ''; "
                            f"assert not v or {ROOT.name!r} in v; "
                            "import json; print(json.dumps({'live':bool(v)}))")
                    if not remote_json(agent, code)["live"]:
                        exited[agent] = True
                        break
                    await asyncio.sleep(1)
                else:
                    errors.append(f"{agent}:owned_worker_still_live")
            except Exception as error:
                errors.append(f"{agent}:{type(error).__name__}")
        write_new(args.output / "worker-shutdown.json", {
            "errors": errors, "verified_exited": len(exited) == len(pids),
            "owned_processes": pids, "exited": exited})
        after = residency()
        write_new(args.output / "private/residency-after.json", after)
        for agent in HOSTS:
            compare_residency(before[agent], after[agent])
            audit = remote_json(agent,
                "import json; from resident_model_pool_attestation_v1 import audit_log_interval; "
                f"print(json.dumps(audit_log_interval({before[agent]!r},{after[agent]!r})))")
            write_new(args.output / "private/residency-log-intervals" / (agent + ".json"), audit)
        write_new(args.output / "private/residency-validation.json", {
            "passed": True, "instances": 5, "startup_subtraction": False})
        if errors:
            raise RuntimeError("owned Worker cleanup failed; queue must stop")


async def attempt(args: argparse.Namespace) -> None:
    require_remote()
    try:
        verify_freeze()
        await run_shaped(args, execute_cell=with_workers)
    except BaseException as error:
        fallback_failure(args, error)
        raise


def run_queue() -> None:
    require_remote()
    cells = schedule()
    freeze_hash = verify_freeze()
    prices, _ = verified_prices(PREDECESSOR, APP)
    with QueueLease(ROOT / "queue-lease.json"):
        ledger = AttemptLedger(ROOT / "phase1-attempts.jsonl",
                               tuple(c.cell_id for c in cells), schedule_sha256(cells))
        if ledger.pending:
            raise RuntimeError("pending attempt requires actual-process reconciliation")
        for cell in cells:
            if cell.cell_id in ledger.completed_cells:
                continue
            verify_freeze()
            if PRIOR_SUBSTANTIVE_CELLS + len(ledger.completed_cells) >= GLOBAL_CAP:
                raise RuntimeError("cumulative substantive experiment cap reached")
            index = 1 + sum(a.cell_id == cell.cell_id for a in ledger.attempts)
            run_id = f"{ROOT.name}-{cell.cell_id}-attempt{index}"
            directory = ROOT / "evidence" / cell.cell_id / f"attempt{index}"
            ledger.reserve(cell.cell_id, run_id, freeze_hash)
            directory.mkdir(parents=True, exist_ok=False)
            config = cell_config(cell, run_id, reference(), root=ROOT)
            config_path = ROOT / "cell-configs" / (run_id + ".yaml")
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with config_path.open("x", encoding="utf-8") as stream:
                yaml.safe_dump(config, stream, sort_keys=False)
            with (directory / "console.log").open("x", encoding="utf-8") as log:
                process = subprocess.Popen([
                    sys.executable, str(Path(__file__).resolve()), "--attempt",
                    "--config", str(config_path), "--output", str(directory),
                ], stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ))
                write_new(directory / "process.json", {"pid": process.pid, "run_id": run_id})
                returncode = process.wait()
            write_new(directory / "process-exit.json", {"pid": process.pid,
                                                       "returncode": returncode})
            try:
                receipt = admit(directory, config, prices)
                if not json.loads((directory / "private/residency-validation.json")
                                  .read_text())["passed"]:
                    raise RuntimeError("residency measurement invalid")
            except Exception as error:
                receipt = {"disposition": "confounder", "reason": "admission_unverifiable",
                           "problems": [type(error).__name__]}
            if returncode and receipt["disposition"] == "valid":
                receipt.update(disposition="confounder", reason="wrapper_execution_error")
            write_new(directory / "admission.json", receipt)
            ledger.settle(run_id, receipt["disposition"], receipt["reason"],
                          provenance_sha256(receipt))
            if receipt["disposition"] != "valid":
                raise RuntimeError("attempt requires offline audit; no hidden retry/next cell")
        write_new(ROOT / "phase1-queue-completed.json", {
            "schedule_sha256": schedule_sha256(cells), "completed_cells": ledger.completed_cells,
            "attempt_count": len(ledger.attempts), "pruning_authorized": False,
            "next_required": "comprehensive private/recipient/failure audit before pruning"})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--queue", action="store_true")
    modes.add_argument("--attempt", action="store_true")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    args.deployment_root = ROOT
    args.execution_freeze = FREEZE
    args.endpoint_config = DEFAULT_ENDPOINTS
    args.cost_history = HISTORY / "cost-history.json"
    args.history_manifest = HISTORY / "manifest.json"
    args.rules_manifest = RULES
    args.api_key_file = Path("/home/super/xiaoming/blind_baseline_6task_v1/api_key.txt")
    if args.attempt and (args.config is None or args.output is None):
        parser.error("attempt requires a new config and evidence namespace")
    return args


if __name__ == "__main__":
    arguments = parse_args()
    require_remote()
    if arguments.freeze:
        write_new(FREEZE, execution_freeze())
        write_new(ROOT / "readiness/residency-at-freeze-001.json", residency())
    elif arguments.queue:
        run_queue()
    else:
        asyncio.run(attempt(arguments))
