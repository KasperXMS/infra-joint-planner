"""4090-only sequential formal queue. No retries or semantic outcome-based tuning."""

from __future__ import annotations

import argparse
import base64
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx
import yaml
from prepare_sdk_native_infra_worker_v1_3 import prepare

HOSTS = {"A4": "edge@192.168.0.104", "A5": "edge@192.168.0.105",
         "A28": "edge@192.168.0.128", "strong-4090": None}
CONDITIONS = ("fast-blind", "fast-aware", "slow-blind", "slow-aware")
SEMANTIC_FAILURE_CODES = frozenset({
    "phase_restricted", "artifact_not_materialized", "context_limit_exceeded",
    "semantic_validation_failed", "artifact_too_large",
})


def write_new(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def validate_cell(
    directory: Path, run_id: str, visibility: str,
    canonical_labels: tuple[str, ...] = ("Yes", "No"),
) -> dict[str, Any]:
    """Operational gates only. Wrong answers and budget/stopping failures are retained."""
    result = json.loads((directory / "runs" / run_id / "result.json").read_text())
    summary = json.loads((directory / "summary.json").read_text())
    tc = json.loads((directory / "tc-attestation.json").read_text())
    events = [json.loads(line) for line in (
        directory / "runs" / run_id / "trace.jsonl"
    ).read_text().split("\n") if line.strip()]
    diagnostics_path = directory / "runs" / run_id / "private/observer-diagnostics.jsonl"
    diagnostics = [json.loads(line) for line in diagnostics_path.read_text().split("\n")
                   if line.strip()]
    problems: list[str] = []
    if tc["cleanup_error"] is not None or tc["original_qdisc"] != tc["restored_qdisc"]:
        problems.append("tc restoration failure")
    if not summary["trace_summary"]["logical_privacy_pass"]:
        problems.append("logical privacy failure")
    if not diagnostics:
        problems.append("observer diagnostics missing")
    probe_errors = [probe for d in diagnostics for probe in d["probes"]
                    if not probe["probe_success"]]
    if probe_errors:
        problems.append("observer probe incident; requires audit")
    inputs = [e for e in events if e["event_type"] == "logical.reasoning.input"
              and e["payload"]["logical_agent_id"] == "manager"]
    profiles = [e for e in events if e["event_type"] == "logical.profile.predecision"]
    by_decision = {e["payload"]["decision_id"]: e for e in profiles}
    if not inputs:
        problems.append("Manager input provenance missing")
    for event in inputs:
        decision_id = event["payload"]["decision_id"]
        actual = event["payload"]["current_anonymous_profile"]
        before = by_decision.get(decision_id)
        if visibility == "aware":
            if before is None or actual != before["payload"]["profile"]:
                problems.append(f"profile mismatch: {decision_id}")
            elif events.index(before) >= events.index(event):
                problems.append(f"late profile: {decision_id}")
        elif before is not None or actual is not None:
            problems.append(f"Blind predecision profile leakage: {decision_id}")
    if not any(e["event_type"] in {"run.end", "run.failed"} for e in events):
        problems.append("terminal run event missing")
    if result["execution_completed"] and (
        result["final_answer"] not in canonical_labels or result["evaluation"] is None
    ):
        problems.append("completed terminal/evaluator contract inconsistent")
    failure = result.get("failure")
    for event in events:
        if event["event_type"] == "logical.observation" and not event["payload"]["succeeded"]:
            code = event["payload"]["failure_code"]
            if code not in SEMANTIC_FAILURE_CODES:
                problems.append(f"typed execution failure {code}; requires audit")
    if failure is not None:
        text = (failure.get("exception_type", "") + " " + failure.get("message", "")).lower()
        if any(term in text for term in (
            "readtimeout", "connecttimeout", "connection reset", "connectionerror",
            "provider", "blind verifier failed", "unrecoverable physical",
        )):
            problems.append("provider/runtime failure; requires audit")
    return {
        "validity": "audit_required" if problems else "operational_checks_pass",
        "problems": sorted(set(problems)), "probe_errors": probe_errors,
        "manager_inputs": len(inputs), "predecision_profiles": len(profiles),
        "completed": result["execution_completed"], "original_evaluation": result["evaluation"],
        "failure": failure,
    }


def remote_python(host: str, code: str) -> str:
    return subprocess.run(
        ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host,
         "python3 -c " + shlex.quote(code)],
        check=True, text=True, capture_output=True, timeout=60,
    ).stdout


def start_worker(root: Path, config: Path, agent: str, store: str) -> int:
    host = HOSTS[agent]
    app = root / "app" if host is None else Path("/mnt/ssd") / root.name / "app"
    target_config = config if host is None else app.parent / config.name
    log = root / "logs" / (config.stem + ".log") if host is None else app.parent / (
        config.stem + ".log"
    )
    if host is not None:
        subprocess.run(["scp", "-q", str(config), f"{host}:{target_config}"], check=True)
    payload = base64.b64encode(json.dumps({
        "app": str(app), "config": str(target_config), "log": str(log), "store": store,
    }).encode()).decode()
    code = (
        "import base64,json,os,subprocess; from pathlib import Path; "
        f"v=json.loads(base64.b64decode({payload!r})); "
        "assert not Path(v['store']).exists(), 'fresh store already exists'; "
        "Path(v['log']).parent.mkdir(parents=True,exist_ok=True); "
        "env=dict(os.environ,PYTHONPATH=v['app']+'/src',OLLAMA_API_KEY='ollama'); "
        "p=subprocess.Popen([v['app']+'/.venv/bin/python','-m','infra_joint.cli','worker',"
        "'--config',v['config']],cwd=v['app'],env=env,stdin=subprocess.DEVNULL,"
        "stdout=open(v['log'],'x'),stderr=subprocess.STDOUT,start_new_session=True); print(p.pid)"
    )
    if host is None:
        output = subprocess.run([sys.executable, "-c", code], check=True,
                                capture_output=True, text=True).stdout
    else:
        output = remote_python(host, code)
    return int(output.strip())


def stop_worker(root: Path, agent: str, pid: int) -> None:
    # Touch only the newly created process whose command line contains this deployment root.
    code = (
        "import os,signal; from pathlib import Path; "
        f"p=Path('/proc/{pid}/cmdline'); "
        "cmd=p.read_bytes().decode() if p.exists() else ''; "
        f"assert not cmd or {root.name!r} in cmd, 'PID ownership changed'; "
        f"os.kill({pid},signal.SIGTERM) if cmd else None"
    )
    host = HOSTS[agent]
    if host is None:
        subprocess.run([sys.executable, "-c", code], check=True)
    else:
        remote_python(host, code)


def main(args: argparse.Namespace) -> None:
    root = args.deployment_root.resolve()
    if sys.platform != "linux" or root.parent != Path("/home/super/xiaoming"):
        raise RuntimeError("formal queue must execute on strong-4090, never development PC")
    if not root.name.startswith("infra-aware-predecision-v1-"):
        raise RuntimeError("deployment root is outside the new experiment namespace")
    app = root / "app"
    journal = root / "queue.jsonl"
    with journal.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps({"event": "started", "pid": os.getpid()}) + "\n")
    for replicate in (1, 2, 3):
        for condition in CONDITIONS:
            cell = f"{condition}-r{replicate}"
            config = app / f"configs/experiments/infra-aware-predecision-v1-{cell}.yaml"
            value = yaml.safe_load(config.read_text())
            output = root / "evidence" / f"matrix-r{replicate}" / condition
            output.mkdir(parents=True, exist_ok=False)
            pids: dict[str, int] = {}
            with journal.open("a") as stream:
                stream.write(json.dumps({"event": "cell_started", "cell": cell}) + "\n")
            try:
                for agent in HOSTS:
                    worker_config = root / "worker-configs" / f"{cell}-{agent}.yaml"
                    prepare(config, agent, worker_config)
                    pids[agent] = start_worker(
                        root, worker_config, agent, value["fresh_worker_stores"][agent]
                    )
                write_new(output / "worker-pids.json", pids)
                initial_states: dict[str, Any] = {}
                for agent, url in value["worker_urls"].items():
                    for attempt in range(60):
                        try:
                            response = httpx.get(url + "/state", timeout=5)
                            response.raise_for_status()
                            state = response.json()
                            assert state["agent_id"] == agent
                            assert not state["artifacts"], "fresh store is polluted"
                            initial_states[agent] = state
                            break
                        except httpx.HTTPError:
                            if attempt == 59:
                                raise
                            time.sleep(1)
                write_new(output / "private/worker-state-before.json", initial_states)
                with (output / "console.log").open("x") as log:
                    completed = subprocess.run([
                        sys.executable, "scripts/run_sdk_native_infra_cell_with_tc_v1_3.py",
                        "--config", str(config), "--output", str(output),
                        "--multihop-corpus", str(args.corpus),
                        "--multihop-queries", str(args.queries),
                        "--api-key-file", str(args.api_key_file),
                    ], cwd=app, stdout=log, stderr=subprocess.STDOUT,
                        env={**os.environ, "PYTHONPATH": str(app / "src")})
                if completed.returncode != 0:
                    raise RuntimeError(
                        f"cell wrapper exit {completed.returncode}; inspect evidence"
                    )
                validation = validate_cell(output, value["run_id"], value["profile_visibility"])
                write_new(output / "lightweight-validation.json", validation)
                with journal.open("a") as stream:
                    stream.write(json.dumps({"event": "cell_finished", "cell": cell,
                                             "validation": validation}) + "\n")
                if validation["problems"]:
                    raise RuntimeError("cell requires operational audit; queue stopped")
            finally:
                shutdown_errors: list[str] = []
                for agent, pid in pids.items():
                    try:
                        stop_worker(root, agent, pid)
                    except Exception as error:
                        shutdown_errors.append(f"{agent}: {type(error).__name__}: {error}")
                if shutdown_errors:
                    write_new(output / "worker-shutdown-errors.json", shutdown_errors)
                    raise RuntimeError("Worker shutdown incomplete; queue stopped")
            # Let only the owned Worker shutdown complete before reusing the fixed ports.
            time.sleep(3)
    with journal.open("a") as stream:
        stream.write(json.dumps({"event": "completed", "cells": 12}) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--deployment-root", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--api-key-file", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        main(arguments)
    except BaseException as error:
        root = arguments.deployment_root
        write_new(root / "queue-failure.json", {
            "exception_type": type(error).__name__, "message": str(error),
        })
        raise
